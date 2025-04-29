import sys
import json
import os
import argparse
from collections import defaultdict
from datetime import datetime
from llm_price_scraper.utils import parse_context_window

try:
    from llm_price_scraper.scrapers import LlmPricingScraper, DataSources
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

def model_to_dict(entry):
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
        "source": entry.source,
        "updated": entry.updated
    }

def generate_lua_output(data, filename, source_description):
    """Generates the Lua output file from the processed pricing data."""
    print(f"-- Generating output file: {filename}", file=sys.stderr)
    try:
        # Group data by provider
        provider_models = defaultdict(list)
        for entry in data:
            provider_key = entry.provider.lower().strip().replace(" ", "_").replace("-", "_").replace(".", "").replace("(", "").replace(")", "").replace("/", "_")
            if "openai" in provider_key: provider_key = "openai"
            elif "anthropic" in provider_key: provider_key = "anthropic"
            elif "google" in provider_key: provider_key = "google"
            elif "mistral" in provider_key: provider_key = "mistralai"
            elif "meta" in provider_key: provider_key = "meta"
            elif "cohere" in provider_key: provider_key = "cohere"
            if not provider_key: provider_key = "unknown_provider"
            provider_models[provider_key].append(entry)

        with open(filename, 'w', encoding='utf-8') as f_out:
            f_out.write(f"-- Generated LLM Pricing Configuration (Lua Table)\n")
            f_out.write("-- Prices are per 1k tokens\n")
            f_out.write(f"-- Data source: {source_description}\n")
            f_out.write("\n")
            f_out.write("return {\n")

            provider_keys_sorted = sorted(provider_models.keys())
            for provider in provider_keys_sorted:
                models = provider_models[provider]
                f_out.write(f'    ["{provider}"] = {{ \n')
                model_entries = {}

                for entry in models:
                    model_key = entry.model.strip().replace(".", "-")
                    if not model_key or model_key in model_entries:
                        continue

                    input_cost_1k = convert_price_per_1m_to_1k(entry.input_tokens_price)
                    output_cost_1k = convert_price_per_1m_to_1k(entry.output_tokens_price)
                    context_tokens = parse_context_window(entry.context)

                    # Construct Lua table entry for the model
                    model_lua_parts = []
                    model_lua_parts.append(f'name = {format_lua_value(entry.model)}')
                    model_lua_parts.append(f'input_cost_per_1k_tokens = {format_lua_value(input_cost_1k)}')
                    model_lua_parts.append(f'output_cost_per_1k_tokens = {format_lua_value(output_cost_1k)}')
                    model_lua_parts.append(f'context_window_tokens = {format_lua_value(context_tokens)}')
                    model_lua_parts.append(f'-- source = {format_lua_value(entry.source)}, updated = {format_lua_value(entry.updated)}')

                    model_lua_table = "{ " + ", ".join(model_lua_parts) + " }"
                    model_entries[model_key] = model_lua_table

                sorted_model_keys = sorted(model_entries.keys())
                for model_key in sorted_model_keys:
                     f_out.write(f'        ["{model_key}"] = {model_entries[model_key]},\n')

                f_out.write("    },\n")

            f_out.write("} # End of the main Lua table\n")

        print(f"-- Successfully wrote Lua configuration to {filename}", file=sys.stderr)

    except Exception as e:
        print(f"-- Error generating Lua file {filename}: {e}", file=sys.stderr)
        if os.path.exists(filename):
            try:
                os.remove(filename)
                print(f"-- Removed partial file {filename} due to error.", file=sys.stderr)
            except OSError as remove_err:
                print(f"-- Error removing partial file {filename}: {remove_err}", file=sys.stderr)

def generate_json_output(data, filename, source_description):
    """Generates the JSON output file (prices per 1k tokens)."""
    print(f"-- Generating JSON output file: {filename}", file=sys.stderr)
    output_structure = {
        "metadata": {
            "source_description": source_description,
            "generated_at": datetime.now().isoformat(),
            "price_unit": "USD per 1k tokens"
        },
        "models": defaultdict(dict) # Group by provider
    }

    try:
        # Group data by provider and model
        provider_models = defaultdict(list)
        for entry in data:
            provider_key = entry.provider.lower().strip().replace(" ", "_").replace("-", "_").replace(".", "").replace("(", "").replace(")", "").replace("/", "_")
            # Consolidate provider keys
            if "openai" in provider_key: provider_key = "openai"
            elif "anthropic" in provider_key: provider_key = "anthropic"
            elif "google" in provider_key: provider_key = "google"
            elif "mistral" in provider_key: provider_key = "mistralai"
            elif "meta" in provider_key: provider_key = "meta"
            elif "cohere" in provider_key: provider_key = "cohere"
            if not provider_key: provider_key = "unknown_provider"
            provider_models[provider_key].append(entry)

        # Convert to dictionary structure for JSON
        for provider, models in provider_models.items():
            for entry in models:
                 # Use original model name as the key within the provider
                 model_dict = model_to_dict(entry)
                 output_structure["models"][provider][entry.model] = model_dict

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
    available_source_names = [source.name for source in DataSources]
    parser = argparse.ArgumentParser(description="Scrape LLM pricing data and output as Lua or JSON.")
    parser.add_argument("source", 
                        help=f"The data source to scrape, or ALL. Available: {', '.join(available_source_names)}",
                        metavar="DataSourceName|ALL")
    parser.add_argument("-f", "--format", 
                        choices=['json', 'lua'], 
                        default='json', 
                        help="Output format (default: json)")
    args = parser.parse_args()

    target_source_input = args.source.upper()
    output_format = args.format.lower()
    
    # Determine output function and file extension
    if output_format == 'lua':
        generate_output_func = generate_lua_output
        file_extension = "lua"
    else: # Default to JSON
        generate_output_func = generate_json_output
        file_extension = "json"

    # Process ALL or single source
    if target_source_input == "ALL":
        print("-- Scraping all available providers --", file=sys.stderr)
        all_pricing_data = []
        available_sources_enum = list(DataSources)
        
        for source_enum in available_sources_enum:
            source_name = source_enum.name
            print(f"-- Scraping data from {source_name}...", file=sys.stderr)
            try:
                pricing_data = LlmPricingScraper.scrape(source_enum)
                print(f"-- Scraped {len(pricing_data)} entries from {source_name}.", file=sys.stderr)
                all_pricing_data.extend(pricing_data)
            except Exception as e:
                print(f"-- Error scraping source {source_name}: {e}", file=sys.stderr)
                print(f"-- Skipping {source_name} and continuing...", file=sys.stderr)
        
        print(f"-- Merging results from {len(available_sources_enum)} sources...", file=sys.stderr)
        combined_models_dict = {}
        for entry in all_pricing_data:
            if entry.model not in combined_models_dict:
                 combined_models_dict[entry.model] = entry
        
        merged_data = list(combined_models_dict.values())
        print(f"-- Total unique models found: {len(merged_data)}", file=sys.stderr)

        output_filename = f"COMBINED_LLM_PRICING.{file_extension}"
        generate_output_func(merged_data, output_filename, "All enabled sources")

    else:
        # Handle single source request
        target_source_name = target_source_input # Keep the name for messages/filename
        try:
            data_source_enum = getattr(DataSources, target_source_name)
        except AttributeError:
            print(f"Error: Invalid DataSource '{args.source}'.", file=sys.stderr)
            print(f"Available sources: {', '.join(available_source_names)}", file=sys.stderr)
            sys.exit(1)

        print(f"-- Scraping single provider: {target_source_name}...", file=sys.stderr)
        try:
            pricing_data = LlmPricingScraper.scrape(data_source_enum)
            print(f"-- Scraped {len(pricing_data)} entries.", file=sys.stderr)
            output_filename = f"{target_source_name}.{file_extension}"
            generate_output_func(pricing_data, output_filename, target_source_name)
        except Exception as e:
            print(f"-- Error scraping or processing source {target_source_name}: {e}", file=sys.stderr)
            sys.exit(1)
# End of file 