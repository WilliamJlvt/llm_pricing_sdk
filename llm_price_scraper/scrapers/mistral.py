import requests
import re
import sys
from bs4 import BeautifulSoup
from datetime import datetime

from llm_price_scraper.models import LLMModelPricing
from llm_price_scraper.utils import parse_price

class MistralScraper:
    # Using the third-party Acorn Labs article as it has a structured pricing section
    URL = "https://www.acorn.io/resources/learning-center/mistral-ai/"
    PROVIDER_NAME = "mistralai" # Standardized provider name

    @staticmethod
    def scrape():
        pricing_data = []
        updated_date = datetime.now().strftime("%Y-%m-%d")
        processed_models = set()

        try:
            response = requests.get(MistralScraper.URL)
            response.raise_for_status()
            soup = BeautifulSoup(response.content, "html.parser")

            # --- Find the Pricing Section --- 
            # Heuristic: Find the h2 tag with id="mistral-ai-pricing"
            pricing_header = soup.find('h2', id='mistral-ai-pricing')
            if not pricing_header:
                 # Fallback: Find h2 containing the text
                 pricing_header = soup.find('h2', string=re.compile(r"Mistral AI Pricing", re.IGNORECASE))

            if not pricing_header:
                raise Exception(f"Could not find the 'Mistral AI Pricing' section header on {MistralScraper.URL}")

            # --- Extract Prices from Text/Lists Following the Header ---
            # The pricing isn't in a single table, but in description lists/paragraphs following subheaders (h4)
            current_element = pricing_header.find_next_sibling()
            
            while current_element and current_element.name != 'h2': # Stop if we hit the next main section
                if current_element.name == 'h4':
                    # Look for pricing points within the text following this h4
                    subsection_content = []
                    sibling = current_element.find_next_sibling()
                    while sibling and sibling.name != 'h4' and sibling.name != 'h2':
                         if sibling.name == 'ul': # Handle bullet points
                              list_items = sibling.find_all('li')
                              for item in list_items:
                                   text = item.get_text(strip=True)
                                   # Example: "Mistral Nemo: The cost... is $0.3 per 1M tokens each."
                                   # Example: "Mistral Large 2: ... $3 per 1M tokens for input and $9 per 1M tokens for output."
                                   # Example: "Mistral Embed: ... $0.01 per 1M tokens for both input and output."
                                   # Example: "Legacy Models ... Mistral 7B: Both input and output are priced at $0.25 per 1M tokens."
                                   # Example: "Mixtral 8x22B: Priced at $2 per 1M tokens for input and $6 per 1M tokens for output."
                                   
                                   model_match = re.match(r"([\w\s\.\-]+):", text)
                                   if model_match:
                                       model_name = model_match.group(1).strip()
                                       model_key = model_name # Use the full name as key
                                       
                                       if model_key in processed_models:
                                           continue

                                       input_price = None
                                       output_price = None

                                       # Pattern 1: "$... per 1M tokens each"
                                       price_each_match = re.search(r'\$?([\d\.]+)\s*per\s*1M\s*tokens\s*each', text, re.IGNORECASE)
                                       # Pattern 2: "$... per 1M tokens for input and $... per 1M tokens for output"
                                       price_split_match = re.search(r'\$?([\d\.]+)\s*per\s*1M\s*tokens\s*for\s*input\s*and\s*\$?([\d\.]+)\s*per\s*1M\s*tokens\s*for\s*output', text, re.IGNORECASE)
                                       # Pattern 3: "$... per 1M tokens for both input and output"
                                       price_both_match = re.search(r'\$?([\d\.]+)\s*per\s*1M\s*tokens\s*for\s*both\s*input\s*and\s*output', text, re.IGNORECASE)
                                       # Pattern 4: "Both input and output are priced at $... per 1M tokens"
                                       price_both_alt_match = re.search(r'both\s*input\s*and\s*output\s*are\s*priced\s*at\s*\$?([\d\.]+)\s*per\s*1M\s*tokens', text, re.IGNORECASE)
                                       # Pattern 5: "costs $... per 1M tokens for input and output"
                                       price_io_single_match = re.search(r'costs\s*\$?([\d\.]+)\s*per\s*1M\s*tokens\s*for\s*input\s*and\s*output', text, re.IGNORECASE)
                                       # Pattern 6: Fine-tuning: "$... per 1M tokens, with an additional storage fee..."
                                       fine_tune_match = re.search(r'fine-tuning\s*costs\s*\$?([\d\.]+)\s*per\s*1M\s*tokens', text, re.IGNORECASE)
                                        
                                       if price_each_match:
                                           price = parse_price(price_each_match.group(1))
                                           input_price = price
                                           output_price = price
                                       elif price_split_match:
                                           input_price = parse_price(price_split_match.group(1))
                                           output_price = parse_price(price_split_match.group(2))
                                       elif price_both_match:
                                           price = parse_price(price_both_match.group(1))
                                           input_price = price
                                           output_price = price
                                       elif price_both_alt_match:
                                           price = parse_price(price_both_alt_match.group(1))
                                           input_price = price
                                           output_price = price
                                       elif price_io_single_match:
                                           price = parse_price(price_io_single_match.group(1))
                                           input_price = price
                                           output_price = price
                                       elif fine_tune_match:
                                            # We are scraping inference prices, skip fine-tuning entries for now
                                             print(f"-- Info: Skipping fine-tuning cost entry for '{model_name}'", file=sys.stderr)
                                             continue
                                       else:
                                           print(f"Warning: Could not extract price pattern for '{model_name}' from text: {text}", file=sys.stderr)
                                           continue
                                           
                                       if input_price is not None and output_price is not None:
                                            pricing_data.append(LLMModelPricing(
                                                model=model_name,
                                                provider=MistralScraper.PROVIDER_NAME,
                                                input_tokens_price=input_price,
                                                output_tokens_price=output_price,
                                                context=None, # Context info not in this pricing section
                                                max_output_tokens=None, # Max tokens not here either
                                                source=MistralScraper.URL,
                                                updated=updated_date
                                            ))
                                            processed_models.add(model_key)
                               
                         elif sibling.name == 'p': # Handle paragraph text (less likely for structured prices here)
                              pass # Ignore paragraphs in this specific structure
                         
                         sibling = sibling.find_next_sibling()
                
                current_element = current_element.find_next_sibling()
            
            if not pricing_data:
                 print(f"Warning: No pricing data extracted from the expected structure on {MistralScraper.URL}", file=sys.stderr)

        except requests.exceptions.RequestException as e:
            print(f"Error fetching Mistral pricing article page: {e}", file=sys.stderr)
        except Exception as e:
            print(f"Error parsing Mistral pricing article page: {e}", file=sys.stderr)
            import traceback
            traceback.print_exc()

        return pricing_data

# Example usage for testing:
# if __name__ == '__main__':
#     results = MistralScraper.scrape()
#     print(f"Found {len(results)} Mistral pricing entries from Acorn Labs article.")
#     for result in results:
#         print(result) 