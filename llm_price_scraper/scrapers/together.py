import requests
import re
import sys
from bs4 import BeautifulSoup
from datetime import datetime

from llm_price_scraper.models import LLMModelPricing
from llm_price_scraper.utils import parse_context_window

class TogetherScraper:
    URL = "https://docs.together.ai/docs/inference-models"
    # Provider mapping might be needed if names vary or need standardization
    PROVIDER_MAP = {
        "01.ai": "01.ai",
        "meta": "meta",
        "mistralai": "mistralai",
        "google": "google",
        "qwen": "qwen",
        "deepseek": "deepseek",
        "together": "together", # For their own models like RedPajama
        "nousresearch": "nousresearch",
        "upstage": "upstage",
        "snorkel ai": "snorkelai",
        "stanford": "stanford",
        "teknium": "teknium",
        "undi95": "undi95",
        "wizardlm": "wizardlm",
        "lm sys": "lmsys",
        "openchat": "openchat",
        "openorca": "openorca",
        "gryphe": "gryphe",
        "cognitivecomputations": "cognitivecomputations",
        "austism": "austism",
        "databricks": "databricks",
        "garage-baind": "garage-baind",
        "snowflake": "snowflake"
        # Add others as encountered
    }

    @staticmethod
    def scrape():
        pricing_data = []
        updated_date = datetime.now().strftime("%Y-%m-%d")

        try:
            response = requests.get(TogetherScraper.URL)
            response.raise_for_status()
            # Page might be long, parse all content
            soup = BeautifulSoup(response.content, "html.parser")

            # --- Find the Main Model Table --- 
            # Heuristic: Find the table containing model IDs like 'zero-one-ai/Yi-34B-Chat'
            # Often tables are within a specific content div
            content_area = soup.find('article') or soup.find('main') or soup # Find main content area
            if not content_area:
                raise Exception("Could not find main content area.")
            
            tables = content_area.find_all('table')
            if not tables:
                raise Exception(f"Could not locate any model tables on {TogetherScraper.URL}")

            processed_models = set() # Avoid duplicates if multiple tables

            for table in tables:
                tbody = table.find('tbody')
                if not tbody: continue

                # Find column indices (more robust than assuming fixed order)
                header_row = table.find('thead').find('tr') if table.find('thead') else table.find('tr')
                if not header_row: continue
                
                headers_text = [th.get_text(strip=True).lower() for th in header_row.find_all('th')]
                # Find indices - column names might vary, try common patterns
                provider_idx = -1
                model_id_idx = -1
                context_idx = -1

                # Try finding indices based on potential header names
                for idx, h in enumerate(headers_text):
                    if 'provider' in h or 'developer' in h : provider_idx = idx
                    # Model ID often contains '/', model name might not
                    if 'model id' in h or '/' in h or ('model' in h and provider_idx != idx): model_id_idx = idx 
                    if 'context' in h : context_idx = idx
                
                # Fallback if indices not found by name (use position - fragile)
                if provider_idx == -1: provider_idx = 0
                if model_id_idx == -1: model_id_idx = 2 # Guess based on observed structure
                if context_idx == -1: context_idx = 3 # Guess based on observed structure
                
                # Simple check if guessed indices seem valid
                max_idx = max(provider_idx, model_id_idx, context_idx)
                if max_idx >= len(headers_text): 
                     print(f"Warning: Could not reliably determine column indices for table, skipping.")
                     continue

                for row in tbody.find_all('tr'):
                    cells = row.find_all('td')
                    if len(cells) <= max_idx:
                         continue # Not enough cells

                    provider_str = cells[provider_idx].get_text(strip=True).lower()
                    model_id_str = cells[model_id_idx].get_text(strip=True)
                    context_str = cells[context_idx].get_text(strip=True)

                    # Use model ID as the primary identifier
                    model_name = model_id_str 
                    if not model_name or model_name in processed_models:
                        continue # Skip if no model ID or already processed
                        
                    # Map provider string to standardized key
                    provider = TogetherScraper.PROVIDER_MAP.get(provider_str, provider_str.replace(" ", "_"))
                    
                    context_tokens = parse_context_window(context_str)
                    max_output_tokens = None # Not available on this page
                    input_price = None # Not available on this page
                    output_price = None # Not available on this page

                    pricing_data.append(LLMModelPricing(
                        model=model_name,
                        provider=provider,
                        input_tokens_price=input_price,
                        output_tokens_price=output_price,
                        context=context_tokens,
                        max_output_tokens=max_output_tokens,
                        source=TogetherScraper.URL,
                        updated=updated_date
                    ))
                    processed_models.add(model_name)

        except requests.exceptions.RequestException as e:
            print(f"Error fetching Together AI models page: {e}", file=sys.stderr)
        except Exception as e:
            print(f"Error parsing Together AI models page: {e}", file=sys.stderr)

        return pricing_data

# Example usage for testing:
# if __name__ == '__main__':
#     results = TogetherScraper.scrape()
#     print(f"Found {len(results)} models.")
#     # Limit printing for brevity
#     for i, result in enumerate(results):
#         if i < 10:
#              print(result)
#         else:
#              print("... and more")
#              break 