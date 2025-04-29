import requests
import re
import sys
from bs4 import BeautifulSoup
from datetime import datetime

from llm_price_scraper.models import LLMModelPricing
from llm_price_scraper.utils import parse_price

class ReplicateScraper:
    # Using the review site as it has a structured table for LLM token prices
    URL = "https://aicoulddothat.net/tools/replicate-pricing-review-alternatives/"
    PROVIDER_NAME = "replicate" # Models run on Replicate, providers vary

    @staticmethod
    def scrape():
        pricing_data = []
        updated_date = datetime.now().strftime("%Y-%m-%d")

        try:
            response = requests.get(ReplicateScraper.URL)
            response.raise_for_status()
            soup = BeautifulSoup(response.content, "html.parser")

            # --- Find the Language Model Pricing Table ---
            # Heuristic: Look for a table with specific headers like "Pricing (per 1M tokens input)" and "Model"
            target_header_texts = ["pricing (per 1m tokens input)", "model"]
            llm_table = None
            all_tables = soup.find_all('table')

            for table in all_tables:
                headers = [th.get_text(strip=True).lower() for th in table.find_all('th')]
                # Check if *all* target headers are present in this table's headers
                if all(target_header in headers for target_header in target_header_texts):
                    llm_table = table
                    break

            if not llm_table:
                raise Exception(f"Could not locate the specific LLM pricing table on {ReplicateScraper.URL}. Searched {len(all_tables)} tables.")

            tbody = llm_table.find('tbody')
            if not tbody:
                raise Exception("LLM table found, but no tbody element.")

            # --- Determine Column Indices --- 
            headers = [th.get_text(strip=True).lower() for th in llm_table.find_all('th')]
            try:
                # Use exact header text from the source page
                price_idx = headers.index("pricing (per 1m tokens input)")
                model_idx = headers.index("model")
                # Note: This table only lists input price explicitly
            except ValueError as e:
                raise Exception(f"Could not find expected column headers in LLM table: {e}. Headers found: {headers}")

            processed_models = set()

            # --- Process Rows ---
            for row in tbody.find_all('tr'):
                cells = row.find_all('td')
                if len(cells) <= max(model_idx, price_idx):
                    continue

                price_str = cells[price_idx].get_text(strip=True)
                model_name = cells[model_idx].get_text(strip=True)

                if not model_name or model_name in processed_models:
                    continue

                # Parse price - assuming it's the input price
                # The table doesn't specify output, so we'll assume it's the same or leave it None
                # Price format seems to be like "$0.05"
                match = re.match(r'\$?([\d\.]+)', price_str)
                if not match:
                    print(f"Warning: Could not parse price '{price_str}' for model '{model_name}'. Skipping.", file=sys.stderr)
                    continue
                
                input_price = parse_price(match.group(1))
                # Assume output price is the same as input if not specified
                output_price = input_price 

                # Context/Max Tokens not available on this pricing table
                context_tokens = None
                max_output_tokens = None

                pricing_data.append(LLMModelPricing(
                    model=model_name,
                    provider=ReplicateScraper.PROVIDER_NAME,
                    input_tokens_price=input_price,
                    output_tokens_price=output_price,
                    context=context_tokens,
                    max_output_tokens=max_output_tokens,
                    source=ReplicateScraper.URL, # Cite the source page
                    updated=updated_date
                ))
                processed_models.add(model_name)

        except requests.exceptions.RequestException as e:
            print(f"Error fetching Replicate pricing review page: {e}", file=sys.stderr)
        except Exception as e:
            print(f"Error parsing Replicate pricing review page: {e}", file=sys.stderr)
            import traceback
            traceback.print_exc()

        return pricing_data

# Example usage for testing:
# if __name__ == '__main__':
#     results = ReplicateScraper.scrape()
#     print(f"Found {len(results)} Replicate LLM pricing entries.")
#     for result in results:
#         print(result) 