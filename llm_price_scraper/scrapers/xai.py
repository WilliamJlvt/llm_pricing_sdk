import requests
import re
import sys
from bs4 import BeautifulSoup
from datetime import datetime

from llm_price_scraper.models import LLMModelPricing
from llm_price_scraper.utils import parse_context_window

# Helper to safely convert price string like $3.00 to float
def safe_price_float(price_str):
    if price_str is None or not isinstance(price_str, str) or price_str.strip() == '-':
        return None
    try:
        cleaned_str = price_str.replace('$', '').strip()
        return float(cleaned_str)
    except (ValueError, TypeError):
        print(f"Warning: Could not convert price string '{price_str}' to float.", file=sys.stderr)
        return None

class XAIScraper:
    URL = "https://x.ai/api"
    PROVIDER = "xai"

    @staticmethod
    def scrape():
        pricing_data = []
        updated_date = datetime.now().strftime("%Y-%m-%d")

        try:
            response = requests.get(XAIScraper.URL)
            response.raise_for_status()
            soup = BeautifulSoup(response.content, "html.parser")

            # --- Find the Pricing Table --- 
            # Heuristic: Find h2 "Models and pricing" then the next table
            pricing_header = soup.find(['h2', 'h3'], string=re.compile(r'Models and pricing', re.IGNORECASE))
            if not pricing_header:
                raise Exception("Could not find the 'Models and pricing' section header.")

            table = pricing_header.find_next_sibling('table')
            if not table:
                # Try finding table within parent's siblings if structure is nested
                parent = pricing_header.find_parent()
                if parent:
                    table = parent.find_next_sibling('table')
                if not table:
                    raise Exception("Could not find the pricing table after the header.")

            # --- Parse Table --- 
            tbody = table.find('tbody')
            if not tbody:
                raise Exception("Could not find table body (tbody)." )

            # Find column indices (more robust than assuming fixed order)
            header_row = table.find('thead').find('tr') if table.find('thead') else table.find('tr')
            if not header_row: raise Exception("Could not find header row.")
            
            headers_text = [th.get_text(strip=True).lower() for th in header_row.find_all('th')]
            try:
                model_idx = headers_text.index('model')
                context_idx = headers_text.index('context window')
                input_idx = headers_text.index('text input') # Assuming text input price column
                output_idx = headers_text.index('output')
            except ValueError:
                raise Exception(f"Could not find expected columns in table header: {headers_text}")

            for row in tbody.find_all('tr'):
                cells = row.find_all('td')
                if len(cells) <= max(model_idx, context_idx, input_idx, output_idx):
                    continue # Skip incomplete rows

                # Extract model name - might have extra text like "New"
                model_name_cell = cells[model_idx]
                model_name = model_name_cell.find(string=True, recursive=False).strip() # Get direct text
                if not model_name: # Fallback if name is nested
                    model_name = model_name_cell.get_text(strip=True)
                
                # Clean up potential extra markers like "New"
                model_name = re.sub(r'\s+New$', '', model_name).strip()
                
                context_str = cells[context_idx].get_text(strip=True)
                input_price_str = cells[input_idx].get_text(strip=True)
                output_price_str = cells[output_idx].get_text(strip=True)

                # Ignore image generation models for now as they have different pricing units
                if "image" in model_name.lower():
                    continue

                context_tokens = parse_context_window(context_str)
                input_price_1m = safe_price_float(input_price_str)
                output_price_1m = safe_price_float(output_price_str)

                # Only add if we have model name and some pricing info
                if model_name and (input_price_1m is not None or output_price_1m is not None):
                    pricing_data.append(LLMModelPricing(
                        model=model_name,
                        provider=XAIScraper.PROVIDER,
                        input_tokens_price=input_price_1m,
                        output_tokens_price=output_price_1m,
                        context=context_tokens,
                        max_output_tokens=None, # Not available
                        source=XAIScraper.URL,
                        updated=updated_date
                    ))

        except requests.exceptions.RequestException as e:
            print(f"Error fetching XAI API page: {e}", file=sys.stderr)
        except Exception as e:
            print(f"Error parsing XAI API page: {e}", file=sys.stderr)

        return pricing_data

# Example usage for testing:
# if __name__ == '__main__':
#     results = XAIScraper.scrape()
#     print(f"Found {len(results)} models.")
#     for result in results:
#         print(result) 