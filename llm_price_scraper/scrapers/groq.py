import requests
import re
import sys
from bs4 import BeautifulSoup
from datetime import datetime

from llm_price_scraper.models import LLMModelPricing
from llm_price_scraper.utils import parse_price

# Re-use safe_int_convert logic if needed, or adapt for Groq's format
def safe_int_convert_groq(value_str):
    if value_str is None or value_str.strip() == '-':
        return None
    try:
        # Remove commas, 'K' (assume thousands), etc.
        cleaned_str = str(value_str).replace(',', '').replace('K', '000').strip()
        return int(cleaned_str)
    except (ValueError, TypeError):
        print(f"Warning: Could not convert '{value_str}' to integer.", file=sys.stderr)
        return None

class GroqScraper:
    URL = "https://groq.com/pricing/"
    PROVIDER_NAME = "groq" # Groq hosts models from various providers but bills under 'groq'

    @staticmethod
    def scrape():
        pricing_data = []
        updated_date = datetime.now().strftime("%Y-%m-%d")

        try:
            response = requests.get(GroqScraper.URL)
            response.raise_for_status()
            soup = BeautifulSoup(response.content, "html.parser")

            # Find the main content area containing the tables
            # The specific structure might be within a div or main element
            content_area = soup.find('main') or soup.body 
            if not content_area:
                raise Exception("Could not find main content area.")

            # --- Find the LLM Pricing Table ---
            llm_table = None
            all_tables = content_area.find_all('table')
            
            # Heuristic: Find the table with headers like "Input Token Price", "Output Token Price"
            target_headers = ["input token price", "output token price"]
            for table in all_tables:
                headers = [th.get_text(strip=True).lower() for th in table.find_all('th')]
                if all(h in headers for h in target_headers):
                    llm_table = table
                    break # Found the LLM table

            if not llm_table:
                raise Exception(f"Could not locate the specific LLM pricing table on {GroqScraper.URL}")

            tbody = llm_table.find('tbody')
            if not tbody: 
                raise Exception("LLM table found, but no tbody element.")

            # --- Determine Column Indices ---
            headers = [th.get_text(strip=True).lower() for th in llm_table.find_all('th')]
            try:
                model_idx = headers.index("ai model")
                input_price_idx = headers.index("input token price(per million tokens)")
                output_price_idx = headers.index("output token price(per million tokens)")
            except ValueError as e:
                raise Exception(f"Could not find expected column headers in LLM table: {e}. Headers found: {headers}")

            processed_models = set()

            # --- Process Rows ---
            for row in tbody.find_all('tr'):
                cells = row.find_all('td')
                if len(cells) <= max(model_idx, input_price_idx, output_price_idx):
                    continue # Skip rows that don't have enough cells

                model_name_raw = cells[model_idx].get_text(strip=True)
                input_price_str = cells[input_price_idx].get_text(strip=True)
                output_price_str = cells[output_price_idx].get_text(strip=True)

                # Clean model name (sometimes context size like '8k' is included)
                # We might want to keep it or parse it out later. For now, keep raw.
                model_name = model_name_raw
                
                # Attempt to extract the primary price (before parenthesis)
                input_price_match = re.match(r'\$?([\d\.]+)', input_price_str)
                output_price_match = re.match(r'\$?([\d\.]+)', output_price_str)

                if not input_price_match or not output_price_match:
                     print(f"Warning: Could not parse prices for model '{model_name}'. Input: '{input_price_str}', Output: '{output_price_str}'. Skipping.", file=sys.stderr)
                     continue

                input_price = parse_price(input_price_match.group(1))
                output_price = parse_price(output_price_match.group(1))

                # Context window and max tokens are not available on this page
                context_tokens = None
                max_output_tokens = None

                if model_name and model_name not in processed_models:
                    pricing_data.append(LLMModelPricing(
                        model=model_name,
                        provider=GroqScraper.PROVIDER_NAME,
                        input_tokens_price=input_price,
                        output_tokens_price=output_price,
                        context=context_tokens,
                        max_output_tokens=max_output_tokens,
                        source=GroqScraper.URL,
                        updated=updated_date
                    ))
                    processed_models.add(model_name)

        except requests.exceptions.RequestException as e:
            print(f"Error fetching Groq pricing page: {e}", file=sys.stderr)
        except Exception as e:
            print(f"Error parsing Groq pricing page: {e}", file=sys.stderr)
            import traceback
            traceback.print_exc()

        return pricing_data

# Example usage for testing:
# if __name__ == '__main__':
#     results = GroqScraper.scrape()
#     print(f"Found {len(results)} Groq LLM pricing entries.")
#     # Limit printing for brevity
#     limit = 10
#     for i, result in enumerate(results):
#          print(result)
#          if i >= limit -1:
#              print(f"... and {len(results) - limit} more.")
#              break 