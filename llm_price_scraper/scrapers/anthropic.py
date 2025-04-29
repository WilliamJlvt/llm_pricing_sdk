import requests
import re
import sys
from bs4 import BeautifulSoup
from datetime import datetime

from llm_price_scraper.models import LLMModelPricing
from llm_price_scraper.utils import parse_context_window

# Helper to safely convert string to int, handling None and non-numeric
def safe_int_convert(value_str):
    if value_str is None:
        return None
    try:
        # Remove commas, 'K' (assume thousands), etc.
        cleaned_str = str(value_str).replace(',', '').replace('K', '000').strip()
        return int(cleaned_str)
    except (ValueError, TypeError):
        print(f"Warning: Could not convert '{value_str}' to integer.", file=sys.stderr)
        return None

# Helper to parse cost string like "$3.00 / $15.00"
def parse_anthropic_cost(cost_str):
    if cost_str is None or '/' not in cost_str:
        return None, None
    try:
        parts = cost_str.split('/')
        input_cost_str = parts[0].replace('$', '').strip()
        output_cost_str = parts[1].replace('$', '').strip()
        input_cost = float(input_cost_str)
        output_cost = float(output_cost_str)
        return input_cost, output_cost
    except (ValueError, TypeError, IndexError) as e:
        print(f"Warning: Could not parse cost string '{cost_str}': {e}", file=sys.stderr)
        return None, None

class AnthropicScraper:
    URL = "https://docs.anthropic.com/claude/docs/models-overview"
    PROVIDER = "anthropic"

    @staticmethod
    def scrape():
        pricing_data = []
        updated_date = datetime.now().strftime("%Y-%m-%d") # Page doesn't show update date easily

        try:
            response = requests.get(AnthropicScraper.URL)
            response.raise_for_status()
            soup = BeautifulSoup(response.content, "html.parser")

            # Find the comparison table (heuristic: look for h3 containing 'Model comparison table')
            comparison_header = soup.find('h3', string=re.compile(r'Model comparison table', re.IGNORECASE))
            if not comparison_header:
                raise Exception("Could not find the model comparison table header.")

            table = comparison_header.find_next_sibling('table')
            if not table:
                raise Exception("Could not find the table element after the header.")

            # --- Extract Model Names and Column Indices from Header ---
            header_row = table.find('thead').find('tr') if table.find('thead') else table.find('tr')
            if not header_row:
                 raise Exception("Could not find header row in table.")

            models_in_header = []
            for idx, th in enumerate(header_row.find_all('th')):
                if idx == 0: continue # Skip first 'Feature' column
                model_name = th.get_text(strip=True)
                # Basic cleanup (might need more specific rules if names vary)
                if 'Claude 3.7' in model_name: model_name = 'Claude 3.7 Sonnet'
                elif 'Claude 3.5 Haiku' in model_name: model_name = 'Claude 3.5 Haiku'
                elif 'Claude 3.5 Sonnet' in model_name: model_name = 'Claude 3.5 Sonnet'
                elif 'Claude 3 Opus' in model_name: model_name = 'Claude 3 Opus'
                elif 'Claude 3 Haiku' in model_name: model_name = 'Claude 3 Haiku'
                # Add more specific mappings if needed based on actual table variations
                models_in_header.append({"name": model_name, "index": idx})

            if not models_in_header:
                 raise Exception("No models found in table header.")

            # --- Initialize Data Structure for Models ---
            model_data = {m["name"]: {"context": None, "max_output": None, "input_cost": None, "output_cost": None} for m in models_in_header}

            # --- Extract Data from Table Body Rows ---
            tbody = table.find('tbody')
            if not tbody:
                raise Exception("Could not find table body.")

            for row in tbody.find_all('tr'):
                cells = row.find_all(['td', 'th']) # Feature name might be in th or td
                if not cells: continue

                feature_name = cells[0].get_text(strip=True)
                data_cells = cells[1:] # The rest are data cells corresponding to models

                if re.search(r'Context window', feature_name, re.IGNORECASE):
                    for model_info in models_in_header:
                        col_idx = model_info["index"] - 1 # Adjust index because we skipped first cell
                        if col_idx < len(data_cells):
                            model_data[model_info["name"]]["context"] = data_cells[col_idx].get_text(strip=True)

                elif re.search(r'Max output', feature_name, re.IGNORECASE):
                     for model_info in models_in_header:
                        col_idx = model_info["index"] - 1
                        if col_idx < len(data_cells):
                           model_data[model_info["name"]]["max_output"] = data_cells[col_idx].get_text(strip=True)

                elif re.search(r'Cost.*per Million Tokens', feature_name, re.IGNORECASE): # Match cost row
                    for model_info in models_in_header:
                        col_idx = model_info["index"] - 1
                        if col_idx < len(data_cells):
                            cost_str = data_cells[col_idx].get_text(strip=True)
                            input_cost, output_cost = parse_anthropic_cost(cost_str)
                            model_data[model_info["name"]]["input_cost"] = input_cost
                            model_data[model_info["name"]]["output_cost"] = output_cost

            # --- Process Collected Data and Create Objects ---
            for name, data in model_data.items():
                context_tokens = parse_context_window(data["context"]) # Use existing util
                max_output_tokens = safe_int_convert(data["max_output"])

                # Only add if we have price info
                if data["input_cost"] is not None or data["output_cost"] is not None:
                    pricing_data.append(LLMModelPricing(
                        model=name,
                        provider=AnthropicScraper.PROVIDER,
                        input_tokens_price=data["input_cost"],
                        output_tokens_price=data["output_cost"],
                        context=context_tokens,
                        max_output_tokens=max_output_tokens,
                        source=AnthropicScraper.URL,
                        updated=updated_date
                    ))
                else:
                     print(f"-- Info: Skipping Anthropic model '{name}' as no pricing found.", file=sys.stderr)

        except requests.exceptions.RequestException as e:
            print(f"Error fetching Anthropic pricing page: {e}", file=sys.stderr)
        except Exception as e:
            print(f"Error parsing Anthropic pricing page: {e}", file=sys.stderr)

        return pricing_data

# Example usage for testing:
# if __name__ == '__main__':
#     results = AnthropicScraper.scrape()
#     for result in results:
#         print(result) 