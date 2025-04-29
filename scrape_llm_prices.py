import sys
import json
import os
import argparse
from collections import defaultdict
from datetime import datetime
from llm_price_scraper.utils import parse_context_window

try:
    from llm_price_scraper.scrapers import LlmPricingScraper, DataSources, LLMModelPricing
except ImportError:
    print("Error: llm-price-scraper package not found.", file=sys.stderr)
    print("Please install it using: pip install llm-price-scraper", file=sys.stderr)
    sys.exit(1)

# Check for command-line argument
if len(sys.argv) < 2:
    print("Usage: python3 scrape_llm_prices.py <DataSourceName | ALL>", file=sys.stderr)
    print("Example: python3 scrape_llm_prices.py DOCSBOT", file=sys.stderr)
    print("Example: python3 scrape_llm_prices.py ALL", file=sys.stderr)
    # Optionally list available sources if easily possible
    available_sources = [source.name for source in DataSources]
    print(f"Available sources: {', '.join(available_sources)}", file=sys.stderr)
    sys.exit(1)

target_source_name = sys.argv[1].upper()

# --- Configuration ---
# Lower number means higher priority. Assign priorities to sources.
# Sources not listed here will get a default priority (e.g., 99).
# Adjust these priorities based on which sources you trust most.
SOURCE_PRIORITIES = {
    DataSources.OPENAI: 1,
    DataSources.ANTHROPIC: 1,
    DataSources.GOOGLE: 1,
    DataSources.MISTRAL: 2,
    DataSources.META: 2,
    DataSources.COHERE: 2,
    DataSources.GROQ: 3,
    DataSources.AI21: 4,
    DataSources.BEDROCK: 5, # Often aggregates, potentially less direct pricing
    DataSources.DOCSBOT: 10, # Example: Lower priority for aggregators
    DataSources.AZURE: 3, # Example priority
    # Add other datasources as needed
}
DEFAULT_PRIORITY = 99

# --- Helper Functions ---

def get_source_priority(source_enum):
    """Gets the priority for a given DataSource enum member."""
    return SOURCE_PRIORITIES.get(source_enum, DEFAULT_PRIORITY)

def calculate_completeness_score(entry: LLMModelPricing) -> int:
    """Calculates a score based on the presence of key pricing fields."""
    score = 0
    if entry.input_tokens_price is not None:
        score += 1
    if entry.output_tokens_price is not None:
        score += 1
    if entry.context is not None and parse_context_window(entry.context) is not None:
        score += 1
    return score

def get_standardized_provider_key(provider_raw: str | None) -> str:
    """Standardizes provider names into consistent keys."""
    if not provider_raw:
        return "unknown_provider"
    
    provider_key = provider_raw.lower().strip().replace(" ", "_").replace("-", "_").replace(".", "").replace("(", "").replace(")", "").replace("/", "_")

    # Consolidate common provider names (centralized logic)
    if "openai" in provider_key: provider_key = "openai"
    elif "anthropic" in provider_key: provider_key = "anthropic"
    elif "google" in provider_key: provider_key = "google"
    elif "mistral" in provider_key: provider_key = "mistralai"
    elif "meta" in provider_key: provider_key = "meta"
    elif "cohere" in provider_key: provider_key = "cohere"
    elif "groq" in provider_key: provider_key = "groq"
    elif "ai21" in provider_key: provider_key = "ai21"
    elif "amazon" in provider_key or "bedrock" in provider_key: provider_key = "bedrock"
    elif "azure" in provider_key: provider_key = "azure"
    elif not provider_key: provider_key = "unknown_provider"
    
    return provider_key

def format_lua_value(value):
    """Formats a Python value into a Lua-compatible string."""
    if isinstance(value, str):
        # Basic escaping for Lua strings
        escaped_value = value.replace('\\', '\\\\').replace('"', '\\"')
        return f'"{escaped_value}"'
    elif isinstance(value, (int, float)):
        # Format floats precisely, avoid scientific notation for typical prices
        return f"{value:.8f}".rstrip('0').rstrip('.') if isinstance(value, float) else str(value)
    elif value is None:
        return "nil"
    else:
        # Fallback for other types (might need adjustment)
        return f'"{str(value)}"'

def convert_price_per_1m_to_1k(price_per_1m):
    """Converts price per 1M tokens to price per 1k tokens."""
    if price_per_1m is None:
        return None
    try:
        # Remove '$' if present and convert to float
        price_str = str(price_per_1m).replace('$', '').strip()
        # Handle potential ranges like "1.50 - 3.00" - take the lower value for now
        if '-' in price_str:
            price_str = price_str.split('-')[0].strip()
        price_float = float(price_str)
        return price_float / 1000.0
    except (ValueError, TypeError):
        print(f"-- Warning: Could not convert price '{price_per_1m}' to float.", file=sys.stderr)
        return None

def model_to_dict(entry: LLMModelPricing):
    """Converts an LLMModelPricing object to a dictionary for JSON serialization."""
    input_cost_1k = convert_price_per_1m_to_1k(entry.input_tokens_price)
    output_cost_1k = convert_price_per_1m_to_1k(entry.output_tokens_price)
    context_tokens = parse_context_window(entry.context)
    return {
        "model": entry.model,
        # "provider": entry.provider, # Provider key is handled externally
        "input_cost_per_1k_tokens": input_cost_1k,
        "output_cost_per_1k_tokens": output_cost_1k,
        "context_window_tokens": context_tokens,
        "source": entry.source.name if isinstance(entry.source, DataSources) else entry.source, # Ensure source is string
        "updated": entry.updated
    }

def generate_lua_output(data: list[LLMModelPricing], filename: str, source_description: str):
    """Generates the Lua output file from the *merged and prioritized* pricing data."""
    print(f"-- Generating Lua output file: {filename}", file=sys.stderr)
    try:
        # Group data by provider (already merged, just need grouping for output format)
        provider_models = defaultdict(list)
        for entry in data:
            provider_key = get_standardized_provider_key(getattr(entry, 'provider', None))
            provider_models[provider_key].append(entry)

        with open(filename, 'w', encoding='utf-8') as f_out:
            f_out.write(f"-- Generated LLM Pricing Configuration (Lua Table)\\n")
            f_out.write("-- Prices are per 1k tokens\\n")
            f_out.write(f"-- Data source(s): {source_description}\\n") # Modified description
            f_out.write(f"-- Generated at: {datetime.now().isoformat()}\\n")
            f_out.write("\\n")
            f_out.write("return {\\n")

            provider_keys_sorted = sorted(provider_models.keys())
            for provider in provider_keys_sorted:
                models = provider_models[provider]
                f_out.write(f'    ["{provider}"] = {{ \\n')
                model_entries = {} # Use dict for model keys within provider

                for entry in models:
                    # Use a cleaned-up version of the model name for the Lua key
                    # NOTE: Since data is pre-merged, duplicates *shouldn't* happen here
                    # unless the merge logic kept multiple entries for the same provider/model (unlikely with current logic)
                    model_key_base = entry.model.strip().replace(".", "-").replace(":", "_").replace("/", "_")
                    if not model_key_base: continue
                    model_key = model_key_base

                    input_cost_1k = convert_price_per_1m_to_1k(entry.input_tokens_price)
                    output_cost_1k = convert_price_per_1m_to_1k(entry.output_tokens_price)
                    context_tokens = parse_context_window(entry.context)

                    # Construct Lua table entry
                    model_lua_parts = []
                    model_lua_parts.append(f'name = {format_lua_value(entry.model)}')
                    model_lua_parts.append(f'input_cost_per_1k_tokens = {format_lua_value(input_cost_1k)}')
                    model_lua_parts.append(f'output_cost_per_1k_tokens = {format_lua_value(output_cost_1k)}')
                    model_lua_parts.append(f'context_window_tokens = {format_lua_value(context_tokens)}')
                    source_str = entry.source.name if isinstance(entry.source, DataSources) else entry.source
                    model_lua_parts.append(f'-- Kept from source = {format_lua_value(source_str)}, updated = {format_lua_value(entry.updated)}') # Indicate winning source

                    model_lua_table = "{ " + ", ".join(model_lua_parts) + " }"
                    model_entries[model_key] = model_lua_table

                sorted_model_keys = sorted(model_entries.keys())
                for model_key in sorted_model_keys:
                     f_out.write(f'        ["{model_key}"] = {model_entries[model_key]},\\n')

                f_out.write("    },\\n")

            f_out.write("} -- End of the main Lua table\\n")

        print(f"-- Successfully wrote Lua configuration to {filename}", file=sys.stderr)

    except Exception as e:
        print(f"-- Error generating Lua file {filename}: {e}", file=sys.stderr)
        if os.path.exists(filename):
            try:
                os.remove(filename)
                print(f"-- Removed partial file {filename} due to error.", file=sys.stderr)
            except OSError as remove_err:
                print(f"-- Error removing partial file {filename}: {remove_err}", file=sys.stderr)

def generate_json_output(data: list[LLMModelPricing], filename: str, source_description: str):
    """Generates the JSON output file from the *merged and prioritized* pricing data."""
    print(f"-- Generating JSON output file: {filename}", file=sys.stderr)
    output_structure = {
        "metadata": {
            "source_description": source_description,
            "generated_at": datetime.now().isoformat(),
            "price_unit": "USD per 1k tokens"
        },
        "models": defaultdict(dict) # Group by provider -> model name
    }

    try:
        # Group data by provider (already merged, just need grouping for output format)
        for entry in data:
            provider_key = get_standardized_provider_key(getattr(entry, 'provider', None))
            model_name = entry.model.strip()
            if not model_name: continue

            model_dict = model_to_dict(entry)
            # Indicate the source that won the merge
            model_dict['winning_source'] = entry.source.name if isinstance(entry.source, DataSources) else entry.source
            
            # Since data is pre-merged, we just assign it directly
            output_structure["models"][provider_key][model_name] = model_dict

        # Convert defaultdict back to dict for cleaner JSON output
        output_structure["models"] = dict(output_structure["models"])
        # Sort providers and models within providers for consistent output
        sorted_providers = sorted(output_structure["models"].keys())
        sorted_output_structure = {"metadata": output_structure["metadata"], "models": {}}
        for provider in sorted_providers:
            sorted_models = sorted(output_structure["models"][provider].keys())
            sorted_output_structure["models"][provider] = {model: output_structure["models"][provider][model] for model in sorted_models}
        
        output_structure = sorted_output_structure

        with open(filename, 'w', encoding='utf-8') as f_out:
            json.dump(output_structure, f_out, ensure_ascii=False, indent=4)

        print(f"-- Successfully wrote JSON configuration to {filename}", file=sys.stderr)

    except Exception as e:
        print(f"-- Error generating JSON file {filename}: {e}", file=sys.stderr)
        if os.path.exists(filename):
            try:
                os.remove(filename)
                print(f"-- Removed partial file {filename} due to error.", file=sys.stderr)
            except OSError as remove_err:
                print(f"-- Error removing partial file {filename}: {remove_err}", file=sys.stderr)

# --- Main Execution Logic ---
if __name__ == "__main__":
    # Argument Parsing
    available_source_names = sorted([source.name for source in DataSources]) # Sort for consistent help message
    parser = argparse.ArgumentParser(description="Scrape LLM pricing data and output as Lua or JSON.")
    parser.add_argument("source",
                        nargs='+', # Allow one or more source names
                        help=f"One or more data sources to scrape (e.g., OPENAI GOOGLE), or ALL. Available: {', '.join(available_source_names)}",
                        metavar="DataSourceName")
    parser.add_argument("-f", "--format",
                        choices=['json', 'lua'],
                        default='json',
                        help="Output format (default: json)")
    parser.add_argument("--output-mode",
                        choices=['multiple', 'single'],
                        default='multiple',
                        help="Output mode when multiple sources are specified: 'multiple' files (default) or a 'single' combined file.")
    # Add an output directory argument
    parser.add_argument("-o", "--output-dir",
                        default=".", # Default to current directory
                        help="Directory to save the output file(s).")

    args = parser.parse_args()

    # Process source input
    target_source_inputs = [s.upper() for s in args.source]
    scrape_all_sources = "ALL" in target_source_inputs

    output_format = args.format.lower()
    # Output mode applies if scraping all or multiple specific sources
    output_mode = args.output_mode.lower()
    output_dir = args.output_dir

    # Create output directory if it doesn't exist
    os.makedirs(output_dir, exist_ok=True)
    print(f"-- Output directory: {os.path.abspath(output_dir)}", file=sys.stderr)

    # Determine output function and file extension
    if output_format == 'lua':
        generate_output_func = generate_lua_output
        file_extension = "lua"
    else: # Default to JSON
        generate_output_func = generate_json_output
        file_extension = "json"

    # Determine which sources to scrape
    sources_to_scrape = []
    if scrape_all_sources:
        print("-- Scraping ALL available providers --", file=sys.stderr)
        sources_to_scrape = list(DataSources)
    else:
        print(f"-- Scraping specified providers: {', '.join(target_source_inputs)} --", file=sys.stderr)
        invalid_sources = []
        for source_name in target_source_inputs:
            try:
                data_source_enum = getattr(DataSources, source_name)
                sources_to_scrape.append(data_source_enum)
            except AttributeError:
                invalid_sources.append(source_name)
        
        if invalid_sources:
            print(f"Error: Unknown data source(s): {', '.join(invalid_sources)}.", file=sys.stderr)
            print(f"Available sources: {', '.join(available_source_names)}", file=sys.stderr)
            sys.exit(1)
        
        if not sources_to_scrape: # Should not happen if validation works, but safety check
             print("Error: No valid sources specified.", file=sys.stderr)
             sys.exit(1)

    # --- Scraping and Output Generation --- 
    all_scraped_data = [] # Temp storage for all raw scraped data before merging
    sources_processed_count = 0
    sources_error_count = 0
    sources_scraped_names = [] # Keep track of successfully scraped sources for single file name

    print(f"-- Output mode: {output_mode} --", file=sys.stderr)

    for source_enum in sources_to_scrape:
        source_name = source_enum.name
        print(f"--- Scraping data from {source_name}... ---", file=sys.stderr)
        try:
            pricing_data: list[LLMModelPricing] = LlmPricingScraper.scrape(source_enum)
            print(f"-- Scraped {len(pricing_data)} entries from {source_name}.", file=sys.stderr)
            sources_processed_count += 1
            sources_scraped_names.append(source_name)

            if output_mode == 'multiple':
                if pricing_data: # Only generate file if data was found
                    output_filename = os.path.join(output_dir, f"{source_name}_prices.{file_extension}")
                    generate_output_func(pricing_data, output_filename, source_name)
                else:
                     print(f"-- No pricing data found for {source_name}. Skipping file generation.", file=sys.stderr)
            else: # output_mode == 'single' - collect data for merging later
                all_scraped_data.extend(pricing_data)

        except Exception as e:
            sources_error_count += 1
            print(f"!! Error scraping source {source_name}: {e}", file=sys.stderr)
            print(f"!! Skipping {source_name} and continuing...", file=sys.stderr)

    print(f"--- Finished scraping. Processed: {sources_processed_count}, Errors: {sources_error_count} ---", file=sys.stderr)

    # --- Merging Logic (only for output_mode == 'single') ---
    if output_mode == 'single':
        if all_scraped_data:
            print(f"-- Merging results from {sources_processed_count} successful sources using priority+completeness...", file=sys.stderr)
            merged_models = {} # Key: (provider_key, model_name), Value: LLMModelPricing object
            
            for entry in all_scraped_data:
                model_name = getattr(entry, 'model', None)
                if not model_name or not isinstance(model_name, str) or not model_name.strip():
                    # print(f"-- Skipping entry with missing or invalid model name: {entry}", file=sys.stderr)
                    continue # Skip entries without a valid model name
                model_name = model_name.strip()

                provider_key = get_standardized_provider_key(getattr(entry, 'provider', None))
                merge_key = (provider_key, model_name)

                current_priority = get_source_priority(entry.source)
                current_score = calculate_completeness_score(entry)

                if merge_key not in merged_models:
                    # First time seeing this provider/model combo
                    merged_models[merge_key] = entry
                else:
                    # Compare with existing entry for this provider/model
                    existing_entry = merged_models[merge_key]
                    existing_priority = get_source_priority(existing_entry.source)
                    existing_score = calculate_completeness_score(existing_entry)

                    if current_priority < existing_priority:
                        # New entry has higher priority
                        merged_models[merge_key] = entry
                    elif current_priority == existing_priority and current_score > existing_score:
                        # Same priority, but new entry is more complete
                        merged_models[merge_key] = entry
                    # Else (current_priority > existing_priority OR (same priority and current_score <= existing_score)):
                    # Keep the existing entry

            merged_data = list(merged_models.values())
            print(f"-- Merged down to {len(merged_data)} unique models after applying priority.", file=sys.stderr)

            # Determine filename and source description for single output
            if scrape_all_sources:
                base_filename = "ALL_llm_prices"
                source_desc = "All sources (merged by priority)"
            else:
                # Create a filename based on the successfully scraped sources
                # Sort names for consistency
                sorted_scraped_names = sorted(sources_scraped_names)
                # Keep filename reasonably short if many sources are listed
                if len(sorted_scraped_names) > 3:
                    base_filename = f"{'_'.join(sorted_scraped_names[:3])}_etc_prices"
                else:
                    base_filename = f"{'_'.join(sorted_scraped_names)}_prices"
                source_desc = f"Specified sources: {', '.join(sorted_scraped_names)} (merged by priority)"
                
            output_filename = os.path.join(output_dir, f"{base_filename}.{file_extension}")
            generate_output_func(merged_data, output_filename, source_desc)
        else:
            print("-- No data collected from any specified source for single file output.", file=sys.stderr)

    print("-- Script finished.", file=sys.stderr)
# End of file 