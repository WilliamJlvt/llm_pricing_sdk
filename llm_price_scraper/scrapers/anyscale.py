import requests
import re
import sys
from bs4 import BeautifulSoup
from datetime import datetime

from llm_price_scraper.models import LLMModelPricing
from llm_price_scraper.utils import parse_price

class AnyscaleScraper:
    URL = "https://www.anyscale.com/blog/anyscale-endpoints-embedding-endpoint-llama-2-70b-fine-tuning-and-improved-sign-up-experience"
    PROVIDER_NAME = "anyscale"

    @staticmethod
    def scrape():
        pricing_data = []
        updated_date = datetime.now().strftime("%Y-%m-%d")
        processed_models = set()

        try:
            response = requests.get(AnyscaleScraper.URL)
            response.raise_for_status()
            soup = BeautifulSoup(response.content, "html.parser")

            # --- Find the Fine-tuned Model Inference Pricing Table ---
            inference_table = None
            # Heuristic: Find h3 tag with the specific text and get the next table
            h3_tag = soup.find('h3', id="fine-tuned-model-inference-pricing") # Check if the ID exists
            if not h3_tag:
                 # Fallback: Find h3 containing the text
                 h3_tag = soup.find('h3', string=re.compile(r"Fine-tuned model inference Pricing", re.IGNORECASE))

            if h3_tag:
                inference_table = h3_tag.find_next_sibling('table')

            if not inference_table:
                print(f"Warning: Could not locate the specific Fine-tuned model inference pricing table on {AnyscaleScraper.URL}. Trying alternative search.", file=sys.stderr)
                # Alternative: Find any table with the expected single price column header
                all_tables = soup.find_all('table')
                for table in all_tables:
                     headers = [th.get_text(strip=True).lower() for th in table.find_all('th')]
                     if "price ($/m tokens)" in headers and len(headers) == 2:
                          # Check if first cell of first row looks like a model name
                          tbody = table.find('tbody')
                          if tbody and tbody.find('tr') and tbody.find('tr').find('td'):
                              first_cell_text = tbody.find('tr').find('td').get_text(strip=True).lower()
                              if 'llama' in first_cell_text: # Good heuristic for this specific table
                                  inference_table = table
                                  break
            
            if not inference_table:
                 print(f"Error: Could not locate the Fine-tuned model inference pricing table on {AnyscaleScraper.URL} even with alternatives.", file=sys.stderr)
            else:
                tbody = inference_table.find('tbody')
                if not tbody:
                    print(f"Error: Fine-tuned inference table found, but no tbody element.", file=sys.stderr)
                else:
                    headers = [th.get_text(strip=True).lower() for th in inference_table.find_all('th')]
                    try:
                        model_idx = headers.index("model")
                        price_idx = headers.index("price ($/m tokens)")
                    except ValueError as e:
                        print(f"Error: Could not find expected column headers in fine-tuned inference table: {e}. Headers found: {headers}", file=sys.stderr)
                        tbody = None # Prevent processing if headers wrong

                    if tbody: # Proceed only if tbody and headers were found
                        for row in tbody.find_all('tr'):
                            cells = row.find_all('td')
                            if len(cells) <= max(model_idx, price_idx):
                                continue

                            model_name = cells[model_idx].get_text(strip=True)
                            price_str = cells[price_idx].get_text(strip=True)
                            
                            # Add suffix to indicate it's fine-tuned pricing
                            model_name_display = f"{model_name} (fine-tuned inference)"

                            if not model_name or model_name_display in processed_models:
                                continue

                            price = parse_price(price_str)
                            if price is None:
                                print(f"Warning: Could not parse price '{price_str}' for model '{model_name_display}'. Skipping.", file=sys.stderr)
                                continue
                            
                            # Assume same price for input/output as only one is listed
                            input_price = price
                            output_price = price
                            context_tokens = None
                            max_output_tokens = None

                            pricing_data.append(LLMModelPricing(
                                model=model_name_display,
                                provider=AnyscaleScraper.PROVIDER_NAME,
                                input_tokens_price=input_price,
                                output_tokens_price=output_price,
                                context=context_tokens,
                                max_output_tokens=max_output_tokens,
                                source=AnyscaleScraper.URL,
                                updated=updated_date
                            ))
                            processed_models.add(model_name_display)

            # --- Extract Embedding Model Pricing --- 
            # Heuristic: Find paragraph mentioning 'gte-large' and its price
            embedding_model_name = "thenlper/gte-large"
            embedding_price = None
            # Search for the specific text mentioning the model and price
            pattern = re.compile(r"gte-large.*developers can access it at \$?([\d\.]+)\/MTokens", re.IGNORECASE | re.DOTALL)
            match = soup.find(string=pattern)
            if match:
                 price_match = pattern.search(match)
                 if price_match:
                     embedding_price = parse_price(price_match.group(1))
            else:
                 # Broader search if specific string not found
                 paragraphs = soup.find_all('p')
                 for p in paragraphs:
                     text = p.get_text()
                     if embedding_model_name in text.lower():
                          price_match = re.search(r'\$?([\d\.]+)\/MTokens', text, re.IGNORECASE)
                          if price_match:
                              embedding_price = parse_price(price_match.group(1))
                              break 
            
            if embedding_price is not None and embedding_model_name not in processed_models:
                 pricing_data.append(LLMModelPricing(
                    model=embedding_model_name,
                    provider=AnyscaleScraper.PROVIDER_NAME,
                    input_tokens_price=embedding_price, # Embedding is input only
                    output_tokens_price=0.0, # Explicitly zero for output
                    context=None, # N/A for embedding
                    max_output_tokens=None, # N/A for embedding
                    source=AnyscaleScraper.URL,
                    updated=updated_date
                 ))
                 processed_models.add(embedding_model_name)
            elif embedding_model_name not in processed_models:
                 print(f"Warning: Could not find embedding model price for '{embedding_model_name}' on {AnyscaleScraper.URL}", file=sys.stderr)


        except requests.exceptions.RequestException as e:
            print(f"Error fetching Anyscale blog page: {e}", file=sys.stderr)
        except Exception as e:
            print(f"Error parsing Anyscale blog page: {e}", file=sys.stderr)
            import traceback
            traceback.print_exc()

        return pricing_data

# Example usage for testing:
# if __name__ == '__main__':
#     results = AnyscaleScraper.scrape()
#     print(f"Found {len(results)} Anyscale pricing entries from blog post.")
#     for result in results:
#         print(result) 