import requests
import re
import sys
from bs4 import BeautifulSoup
from datetime import datetime

from llm_price_scraper.models import LLMModelPricing

# Helper to extract price from the structure found on Cohere's page
def extract_cohere_price(price_div):
    if not price_div:
        return None
    # Expecting structure like <div> <span>$</span> <span>2.50</span> ... </div>
    price_span = price_div.find('span', string=re.compile(r'[\d.]+$'))
    if price_span:
        try:
            return float(price_span.get_text(strip=True))
        except (ValueError, TypeError):
            return None
    return None

class CohereScraper:
    URL = "https://cohere.com/pricing"
    PROVIDER = "cohere"

    @staticmethod
    def scrape():
        pricing_data = []
        updated_date = datetime.now().strftime("%Y-%m-%d")

        try:
            response = requests.get(CohereScraper.URL)
            response.raise_for_status()
            soup = BeautifulSoup(response.content, "html.parser")

            # --- Find the Generative Models Section ---
            # Heuristic: Find h2 with text "Generative Models"
            gen_models_header = soup.find('h2', string=re.compile(r'Generative Models', re.IGNORECASE))
            if not gen_models_header:
                raise Exception("Could not find the 'Generative Models' section header.")

            # Find the container holding the model cards (this might need adjustment based on actual structure)
            # Assuming models follow the header, perhaps in sibling divs
            model_container = gen_models_header.find_next_sibling() # Adjust if needed
            if not model_container:
                 raise Exception("Could not find container for model cards after header.")
            
            # --- Iterate Through Model Cards (Adjust selector based on inspection) ---
            # This is a guess - needs verification with actual page structure
            # Assuming each model is in a div with specific class or structure following the h2
            # Let's try finding divs that contain an h3 for the model name
            model_blocks = model_container.find_all('div', recursive=False) # Look for direct children first
            if not model_blocks:
                model_blocks = gen_models_header.find_next_siblings('div') # Try siblings if not in container
            
            current_model_name = None
            input_price = None
            output_price = None
            
            # Iterate through potential blocks looking for model names and prices
            # This logic is highly dependent on the exact HTML structure
            for block in soup.find_all(True): # Iterate all tags to find structure
                # Find Model Name (likely h3 or similar)
                if block.name in ['h3', 'h4'] and block.parent.name != 'a': # Basic check for model name heading
                     potential_name = block.get_text(strip=True)
                     # Filter out non-model headings
                     if potential_name and any(m in potential_name for m in ["Command A", "Command R+", "Command R", "Fine-tuned", "Command R7B"]):
                        # If we found a new model name and had data for previous one, save it
                        if current_model_name and (input_price is not None or output_price is not None):
                            pricing_data.append(LLMModelPricing(
                                model=current_model_name,
                                provider=CohereScraper.PROVIDER,
                                input_tokens_price=input_price,
                                output_tokens_price=output_price,
                                context=None, # Not available on this page
                                max_output_tokens=None, # Not available on this page
                                source=CohereScraper.URL,
                                updated=updated_date
                            ))
                        
                        # Reset for the new model
                        current_model_name = potential_name
                        # Handle specific cases like "Fine-tuned Model Command R"
                        if "Fine-tuned Model" in current_model_name:
                           if "Command R" in current_model_name:
                               current_model_name = "Command R Fine-tuned"
                           # Add other fine-tuned bases if necessary
                        
                        input_price = None
                        output_price = None
                        # print(f"Found model: {current_model_name}")

                # Find Input Price
                # Heuristic: Look for text "Input" followed by a price div
                if block.name == 'div' and "Input" in block.get_text() and "/ 1M tokens" in block.get_text():
                     price_val = extract_cohere_price(block)
                     if price_val is not None:
                         input_price = price_val
                         # print(f"  Input price: {input_price}")
                         continue # Move to next block
                
                # Find Output Price
                # Heuristic: Look for text "Output" followed by a price div
                if block.name == 'div' and "Output" in block.get_text() and "/ 1M tokens" in block.get_text():
                     price_val = extract_cohere_price(block)
                     if price_val is not None:
                          output_price = price_val
                          # print(f"  Output price: {output_price}")
                          # If we found output price, assume block is done, trigger save on next model name find
                          continue # Move to next block
                          
            # Add the last found model after the loop ends
            if current_model_name and (input_price is not None or output_price is not None):
                 pricing_data.append(LLMModelPricing(
                     model=current_model_name,
                     provider=CohereScraper.PROVIDER,
                     input_tokens_price=input_price,
                     output_tokens_price=output_price,
                     context=None, # Not available on this page
                     max_output_tokens=None, # Not available on this page
                     source=CohereScraper.URL,
                     updated=updated_date
                 ))
                 
        except requests.exceptions.RequestException as e:
            print(f"Error fetching Cohere pricing page: {e}", file=sys.stderr)
        except Exception as e:
            print(f"Error parsing Cohere pricing page: {e}", file=sys.stderr)

        # Filter out entries where both prices are None (shouldn't happen with current logic but safety)
        pricing_data = [p for p in pricing_data if p.input_tokens_price is not None or p.output_tokens_price is not None]
        return pricing_data

# Example usage for testing:
# if __name__ == '__main__':
#     results = CohereScraper.scrape()
#     print(f"Found {len(results)} models.")
#     for result in results:
#         print(result) 