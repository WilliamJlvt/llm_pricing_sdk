import requests
import re
import sys
from bs4 import BeautifulSoup
from datetime import datetime

from llm_price_scraper.models import LLMModelPricing
# Note: We are storing DBU/1M tokens, not USD. Conversion needed separately.
# from llm_price_scraper.utils import parse_price 

# Helper to parse DBU values, handling 'n/a'
def parse_dbu_value(value_str):
    if value_str is None or value_str.strip().lower() == 'n/a':
        return None
    try:
        # Remove commas if any
        cleaned_str = str(value_str).replace(',', '').strip()
        return float(cleaned_str)
    except (ValueError, TypeError):
        print(f"Warning: Could not convert '{value_str}' to float DBU value.", file=sys.stderr)
        return None

class DatabricksScraper:
    URL = "https://www.databricks.com/product/pricing/foundation-model-serving"
    PROVIDER_NAME = "databricks"

    @staticmethod
    def scrape():
        pricing_data = []
        updated_date = datetime.now().strftime("%Y-%m-%d")
        processed_models = set()

        try:
            response = requests.get(DatabricksScraper.URL)
            response.raise_for_status()
            soup = BeautifulSoup(response.content, "html.parser")

            # --- Find the Foundation Model Serving Table ---
            # Heuristic: Find table preceded by h2 with id="foundation-model-serving-dbu-rates-and-throughput"
            # or find table with specific column headers
            target_header = soup.find(['h2', 'h3'], id=re.compile(r"foundation-model-serving-dbu-rates", re.IGNORECASE))
            pricing_table = None
            if target_header:
                 # Find the next table sibling or descendant table
                 pricing_table = target_header.find_next('table')

            if not pricing_table:
                 # Fallback: Find table by column headers
                 print(f"Warning: Could not find table by header ID, searching by column names...", file=sys.stderr)
                 all_tables = soup.find_all('table')
                 target_cols = ["model", "dbu / 1m input tokens (global)", "dbu / 1m output tokens (global)"]
                 for table in all_tables:
                     headers = [th.get_text(strip=True).lower().replace('\n', ' ').strip() for th in table.find_all('th')]
                     # Normalize header text a bit
                     headers_norm = [re.sub(r'\s+', ' ', h) for h in headers]
                     if all(col in headers_norm for col in target_cols):
                          pricing_table = table
                          print(f"Found table via column names.", file=sys.stderr)
                          break
            
            if not pricing_table:
                raise Exception(f"Could not locate the Foundation Model Serving pricing table on {DatabricksScraper.URL}")

            tbody = pricing_table.find('tbody')
            if not tbody:
                raise Exception("Pricing table found, but no tbody element.")

            # --- Determine Column Indices --- 
            headers_raw = [th.get_text(strip=True).lower().replace('\n', ' ').strip() for th in pricing_table.find_all('th')]
            headers = [re.sub(r'\s+', ' ', h) for h in headers_raw]
            
            try:
                model_idx = headers.index("model")
                input_dbu_idx = headers.index("dbu / 1m input tokens (global)")
                output_dbu_idx = headers.index("dbu / 1m output tokens (global)")
            except ValueError as e:
                raise Exception(f"Could not find expected column headers in pricing table: {e}. Headers found: {headers}")

            # --- Process Rows --- 
            current_category = "Unknown"
            for row in tbody.find_all('tr'):
                 # Check if the row is a category header (single cell spanning columns, strong tag)
                 header_cell = row.find('td')
                 if header_cell and header_cell.get('colspan') and header_cell.find('strong'):
                     current_category = header_cell.get_text(strip=True)
                     continue # Skip category rows
                 
                 cells = row.find_all('td')
                 if len(cells) <= max(model_idx, input_dbu_idx, output_dbu_idx):
                     continue # Skip rows that don't have enough cells for the required columns

                 model_name = cells[model_idx].get_text(strip=True)
                 input_dbu_str = cells[input_dbu_idx].get_text(strip=True)
                 output_dbu_str = cells[output_dbu_idx].get_text(strip=True)

                 if not model_name or model_name in processed_models:
                     continue

                 # Skip non-model rows if any sneak in
                 if input_dbu_str == '' and output_dbu_str == '':
                      continue
                      
                 input_dbu = parse_dbu_value(input_dbu_str)
                 output_dbu = parse_dbu_value(output_dbu_str)
                 
                 # Handle embedding models where output price isn't applicable (set to 0?)
                 # BGE and GTE list n/a for output.
                 if output_dbu is None and input_dbu is not None and ('bge' in model_name.lower() or 'gte' in model_name.lower()):
                     output_dbu = 0.0

                 # Only add if we have at least one valid price
                 if input_dbu is not None or output_dbu is not None:
                     # Add category tag if useful (e.g., "Llama 3 70B (Legacy Models)")
                     model_display_name = f"{model_name} ({current_category})" if current_category != "Unknown" else model_name
                     
                     pricing_data.append(LLMModelPricing(
                         model=model_display_name,
                         provider=DatabricksScraper.PROVIDER_NAME,
                         input_tokens_price=input_dbu, # Storing DBU/1M tokens
                         output_tokens_price=output_dbu, # Storing DBU/1M tokens
                         context=None, # Not available on pricing page
                         max_output_tokens=None, # Not available on pricing page
                         source=DatabricksScraper.URL,
                         updated=updated_date,
                         notes="Prices in DBU/1M tokens. Requires DBU-to-USD conversion."
                     ))
                     processed_models.add(model_name)
                 else:
                      print(f"Warning: Could not parse valid DBU prices for model '{model_name}'. Input: '{input_dbu_str}', Output: '{output_dbu_str}'. Skipping.", file=sys.stderr)


        except requests.exceptions.RequestException as e:
            print(f"Error fetching Databricks pricing page: {e}", file=sys.stderr)
        except Exception as e:
            print(f"Error parsing Databricks pricing page: {e}", file=sys.stderr)
            import traceback
            traceback.print_exc()

        return pricing_data

# Example usage for testing:
# if __name__ == '__main__':
#     results = DatabricksScraper.scrape()
#     print(f"Found {len(results)} Databricks Foundation Model pricing entries (in DBUs).")
#     for result in results:
#         print(result) 