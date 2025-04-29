import requests
import re
import sys
from bs4 import BeautifulSoup
from datetime import datetime

from llm_price_scraper.models import LLMModelPricing

# Helper to convert price per 1k tokens to per 1M tokens
def convert_1k_to_1m_price(price_1k_str):
    if price_1k_str is None or not isinstance(price_1k_str, str):
        return None
    try:
        # Remove currency symbols, commas etc.
        cleaned_str = price_1k_str.replace('$', '').replace(',', '').strip()
        if cleaned_str.lower() == 'n/a':
            return None
        price_1k = float(cleaned_str)
        return price_1k * 1000.0
    except (ValueError, TypeError):
        print(f"Warning: Could not convert price string '{price_1k_str}' to float.", file=sys.stderr)
        return None

class AmazonScraper:
    URL = "https://aws.amazon.com/bedrock/pricing/"
    PROVIDER = "amazon"

    @staticmethod
    def scrape():
        pricing_data = []
        updated_date = datetime.now().strftime("%Y-%m-%d") # Page doesn't have obvious update date

        try:
            response = requests.get(AmazonScraper.URL)
            response.raise_for_status()
            # It's a very long page, parse the whole thing
            soup = BeautifulSoup(response.content, "html.parser")

            # --- Find the Amazon Section/Tables ---
            # Heuristic: Find an element identifying the Amazon provider section
            # This might be complex due to tabs/dynamic content structure
            # Let's try finding tables preceded by headers containing "Amazon"
            amazon_headers = soup.find_all(['h2', 'h3', 'h4'], string=re.compile(r'Amazon (Titan|Nova)', re.IGNORECASE))
            if not amazon_headers:
                # Fallback: Look for divs/sections that might contain the tables
                # This requires more inspection if the simple header search fails
                print(f"Warning: Could not find specific Amazon headers on {AmazonScraper.URL}. Attempting broader table search.", file=sys.stderr)
                # As a very broad fallback, just find all tables and check rows, but this is risky
                all_tables = soup.find_all('table') 
            else:
                all_tables = []
                for header in amazon_headers:
                     # Find tables directly following the header
                     table = header.find_next_sibling('table')
                     if table:
                         all_tables.append(table)
                     # Sometimes tables are nested, try finding within parent's siblings
                     parent = header.find_parent()
                     if parent:
                          table = parent.find_next_sibling('table')
                          if table and table not in all_tables:
                              all_tables.append(table)
            
            if not all_tables:
                raise Exception(f"Could not locate any pricing tables potentially for Amazon models on {AmazonScraper.URL}")

            processed_models = set() # Avoid duplicates if tables overlap

            for table in all_tables:
                tbody = table.find('tbody')
                if not tbody: continue
                
                # Determine column indices (Input/Output prices)
                header_row = table.find('thead').find('tr') if table.find('thead') else table.find('tr')
                if not header_row: continue
                headers_text = [th.get_text(strip=True).lower() for th in header_row.find_all('th')]
                
                model_idx = -1
                input_idx = -1
                output_idx = -1
                
                # Find indices - column names might vary slightly
                for idx, h in enumerate(headers_text):
                    if 'model' in h: model_idx = idx
                    if 'input' in h and 'token' in h: input_idx = idx
                    if 'output' in h and 'token' in h: output_idx = idx
                
                # Need at least model name and one price column
                if model_idx == -1 or (input_idx == -1 and output_idx == -1):
                    # print(f"-- Info: Skipping table, couldn't find necessary columns (model, input/output price).")
                    continue 

                for row in tbody.find_all('tr'):
                    cells = row.find_all('td')
                    if len(cells) <= max(model_idx, input_idx, output_idx):
                         continue # Not enough cells

                    model_name = cells[model_idx].get_text(strip=True)
                    # Skip rows that are headers within tbody or footnotes
                    if not model_name or model_name.startswith('*'): continue 
                    # Skip models already processed (if multiple tables list same model)
                    if model_name in processed_models: continue
                        
                    input_price_1k_str = cells[input_idx].get_text(strip=True) if input_idx != -1 else None
                    output_price_1k_str = cells[output_idx].get_text(strip=True) if output_idx != -1 else None
                    
                    input_price_1m = convert_1k_to_1m_price(input_price_1k_str)
                    output_price_1m = convert_1k_to_1m_price(output_price_1k_str)
                    
                    # Only add if we have at least one price and it seems like an Amazon model
                    # (This is weak filtering based on header found earlier, might need refinement)
                    if input_price_1m is not None or output_price_1m is not None:
                         # Attempt basic check if this model likely belongs to Amazon based on name
                         if 'titan' in model_name.lower() or 'nova' in model_name.lower(): 
                             pricing_data.append(LLMModelPricing(
                                 model=model_name,
                                 provider=AmazonScraper.PROVIDER,
                                 input_tokens_price=input_price_1m,
                                 output_tokens_price=output_price_1m,
                                 context=None, # Not available in these tables
                                 max_output_tokens=None, # Not available in these tables
                                 source=AmazonScraper.URL,
                                 updated=updated_date
                             ))
                             processed_models.add(model_name)
                        # else: 
                        #    print(f"-- Info: Skipping row for model '{model_name}' as it might not be an Amazon model based on name.")

        except requests.exceptions.RequestException as e:
            print(f"Error fetching Amazon Bedrock pricing page: {e}", file=sys.stderr)
        except Exception as e:
            print(f"Error parsing Amazon Bedrock pricing page: {e}", file=sys.stderr)

        return pricing_data

# Example usage for testing:
# if __name__ == '__main__':
#     results = AmazonScraper.scrape()
#     print(f"Found {len(results)} Amazon models.")
#     for result in results:
#         print(result) 