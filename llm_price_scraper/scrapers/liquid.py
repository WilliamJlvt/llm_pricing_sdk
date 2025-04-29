import requests
import re
import sys
from bs4 import BeautifulSoup
from datetime import datetime

from llm_price_scraper.models import LLMModelPricing
from llm_price_scraper.utils import parse_context_window

class LiquidScraper:
    URL = "https://www.liquid.ai/liquid-foundation-models"
    PROVIDER = "liquid"

    # Map names found on page to keys used elsewhere (like HF data)
    MODEL_NAME_MAP = {
        "LFM-1B": "LFM-1.3B", # Assuming LFM-1B on page corresponds to 1.3B
        "LFM-3B": "LFM-3.1B", # Assuming LFM-3B on page corresponds to 3.1B
        "LFM-40B": "lfm-40b"   # Assuming LFM-40B on page corresponds to lfm-40b
    }

    @staticmethod
    def scrape():
        pricing_data = []
        updated_date = datetime.now().strftime("%Y-%m-%d")

        try:
            response = requests.get(LiquidScraper.URL)
            response.raise_for_status()
            soup = BeautifulSoup(response.content, "html.parser")

            # --- Find Model Sections and Extract Data ---
            # Heuristic: Look for benchmark tables or descriptions mentioning models and context
            
            # Find context length info first (seems consistent in tables)
            context_map = {}
            tables = soup.find_all('table')
            for table in tables:
                 header_row = table.find('thead').find('tr') if table.find('thead') else None
                 if not header_row: continue
                 
                 headers_text = [th.get_text(strip=True) for th in header_row.find_all('th')]
                 # Find context length column index
                 context_len_idx = -1
                 for idx, h in enumerate(headers_text):
                     if 'Context length' in h: 
                         context_len_idx = idx
                         break
                 if context_len_idx == -1: continue # Skip table if no context length column
                     
                 tbody = table.find('tbody')
                 if not tbody: continue
                 
                 for row in tbody.find_all('tr'):
                     cells = row.find_all('td')
                     if len(cells) > context_len_idx:
                         # Assume first cell is the model name for this table row
                         model_name_in_table = cells[0].get_text(strip=True)
                         context_str = cells[context_len_idx].get_text(strip=True)
                         
                         # Normalize model name if possible
                         normalized_model_name = model_name_in_table
                         if "LFM-1B" in normalized_model_name: normalized_model_name = "LFM-1B"
                         if "LFM-3B" in normalized_model_name: normalized_model_name = "LFM-3B"
                         if "LFM-40" in normalized_model_name: normalized_model_name = "LFM-40B"
                         
                         if normalized_model_name in LiquidScraper.MODEL_NAME_MAP and context_str and context_str != '-':
                             context_map[normalized_model_name] = context_str
                             # print(f"Found context for {normalized_model_name}: {context_str}")

            # Create entries for the models we expect, using found context
            for page_name, standard_name in LiquidScraper.MODEL_NAME_MAP.items():
                context_str = context_map.get(page_name)
                context_tokens = parse_context_window(context_str)
                
                pricing_data.append(LLMModelPricing(
                    model=standard_name, # Use the standardized name
                    provider=LiquidScraper.PROVIDER,
                    input_tokens_price=None, # Pricing not available here
                    output_tokens_price=None, # Pricing not available here
                    context=context_tokens,
                    max_output_tokens=None, # Not available here
                    source=LiquidScraper.URL,
                    updated=updated_date
                ))

        except requests.exceptions.RequestException as e:
            print(f"Error fetching Liquid AI models page: {e}", file=sys.stderr)
        except Exception as e:
            print(f"Error parsing Liquid AI models page: {e}", file=sys.stderr)

        # Filter out entries where context wasn't found (shouldn't happen with current logic)
        pricing_data = [p for p in pricing_data if p.context is not None]
        return pricing_data

# Example usage for testing:
# if __name__ == '__main__':
#     results = LiquidScraper.scrape()
#     print(f"Found {len(results)} models.")
#     for result in results:
#         print(result) 