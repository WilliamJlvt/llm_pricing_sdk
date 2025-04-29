import requests
import re
import sys
from bs4 import BeautifulSoup
from datetime import datetime

from llm_price_scraper.models import LLMModelPricing

# Helper function to extract price from Reka's format
def extract_reka_price(text):
    match = re.search(r'\$?([\d.]+)\s*/\s*1M\s*(input|output)\s*tokens', text, re.IGNORECASE)
    if match:
        try:
            return float(match.group(1))
        except (ValueError, TypeError):
            return None
    return None

class RekaScraper:
    URL = "https://www.reka.ai/reka-api"
    PROVIDER = "reka"

    @staticmethod
    def scrape():
        pricing_data = []
        updated_date = datetime.now().strftime("%Y-%m-%d")

        try:
            response = requests.get(RekaScraper.URL)
            response.raise_for_status()
            soup = BeautifulSoup(response.content, "html.parser")

            # --- Find the Pricing Section --- 
            # Heuristic: Find h2 with text "Our Pricing"
            pricing_header = soup.find('h2', string=re.compile(r'Our Pricing', re.IGNORECASE))
            if not pricing_header:
                 # Fallback: Look for section containing model names
                 pricing_header = soup.find(string="Reka Spark") # Find first model name
                 if pricing_header:
                      pricing_section = pricing_header.find_parent() # Assume parent holds the section
                 else:
                     raise Exception("Could not find the pricing section header or content.")
            else:
                 # Find the container for the pricing blocks, likely a sibling or parent's sibling
                 pricing_section = pricing_header.find_next_sibling() 
                 if not pricing_section:
                      parent = pricing_header.find_parent()
                      if parent:
                           pricing_section = parent.find_next_sibling()
                 
            if not pricing_section:
                 raise Exception("Could not find the container element for pricing blocks.")

            # --- Iterate Through Model Pricing Blocks --- 
            # Heuristic: Look for h3/h4 for model names within the section
            # Note: The exact structure might vary
            model_blocks = pricing_section.find_all(['h2', 'h3', 'h4'], string=re.compile(r'Reka (Spark|Flash|Core)', re.IGNORECASE))
            
            if not model_blocks:
                 # Try finding divs that contain the model names if headers aren't direct
                 model_blocks = pricing_section.find_all('div') # Less precise

            for block in model_blocks:
                model_name_tag = block if block.name in ['h2','h3','h4'] else block.find(['h2','h3','h4'], string=re.compile(r'Reka (Spark|Flash|Core)', re.IGNORECASE))
                if not model_name_tag: continue
                
                model_name = model_name_tag.get_text(strip=True)
                input_price = None
                output_price = None

                # Find price strings associated with this block
                # Search within the block itself or its immediate siblings/children
                search_area = block if block.name not in ['h2','h3','h4'] else block.find_parent() # Adjust search scope
                if not search_area: continue
                
                price_texts = search_area.find_all(string=re.compile(r'tokens', re.IGNORECASE))
                
                for text in price_texts:
                    price_str = text.strip()
                    if "input tokens" in price_str.lower():
                        input_price = extract_reka_price(price_str)
                    elif "output tokens" in price_str.lower():
                        output_price = extract_reka_price(price_str)
                
                # Only add if we found pricing
                if input_price is not None or output_price is not None:
                    pricing_data.append(LLMModelPricing(
                        model=model_name,
                        provider=RekaScraper.PROVIDER,
                        input_tokens_price=input_price, # Already per 1M
                        output_tokens_price=output_price, # Already per 1M
                        context=None, # Not available
                        max_output_tokens=None, # Not available
                        source=RekaScraper.URL,
                        updated=updated_date
                    ))

        except requests.exceptions.RequestException as e:
            print(f"Error fetching Reka API pricing page: {e}", file=sys.stderr)
        except Exception as e:
            print(f"Error parsing Reka API pricing page: {e}", file=sys.stderr)

        return pricing_data

# Example usage for testing:
# if __name__ == '__main__':
#     results = RekaScraper.scrape()
#     print(f"Found {len(results)} models.")
#     for result in results:
#         print(result) 