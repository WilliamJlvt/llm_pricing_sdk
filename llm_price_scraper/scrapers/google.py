import requests
from bs4 import BeautifulSoup
from datetime import datetime
import re
import sys # Import sys for stderr

from llm_price_scraper.models import LLMModelPricing
from llm_price_scraper.utils import parse_context_window

# Helper function to clean price strings
def clean_google_price(price_str):
    if price_str is None or not isinstance(price_str, str):
        return None
    
    # Remove currency symbols, annotations like (text/image/video)
    price_str = price_str.split('$')[-1] # Take part after last $
    price_str = re.sub(r'\s*\(.*\)', '', price_str) # Remove text in parentheses
    
    # Handle tiered pricing (e.g., "1.25, prompts <= 128k tokens") -> take the base price
    price_str = price_str.split(',')[0].strip()
    
    # Handle "Non-thinking: $0.60 Thinking: $3.50" -> take non-thinking for output
    if "Non-thinking:" in price_str:
        match = re.search(r"Non-thinking:\s*([\d.]+)", price_str, re.IGNORECASE)
        if match:
            price_str = match.group(1)
    
    try:
        return float(price_str)
    except ValueError:
        # print(f"Warning: Could not convert price string '{price_str}' to float.", file=sys.stderr)
        return None

class GoogleScraper:
    @staticmethod
    def scrape():
        url = "https://ai.google.dev/gemini-api/docs/pricing"
        pricing_data = []
        update_date_str = datetime.now().strftime("%Y-%m-%d") # Default update date

        try:
            response = requests.get(url)
            response.raise_for_status()
            soup = BeautifulSoup(response.content, "html.parser")

            # Find update date first
            footer_info = soup.find("p", string=re.compile(r"Last updated:", re.IGNORECASE))
            if footer_info:
                match = re.search(r"(\d{4}-\d{2}-\d{2})", footer_info.text)
                if match:
                    update_date_str = match.group(1)

            # Find all model sections (typically starting with H2)
            # This is approximate, might need adjustment if page structure changes
            model_headers = soup.find_all('h2')
            
            for header in model_headers:
                model_name_raw = header.get_text(strip=True)
                # Filter out non-model headers
                if not re.search(r'(Gemini|Imagen|Veo|Gemma|Text Embedding)', model_name_raw, re.IGNORECASE):
                    continue
                
                # Simplify common model names
                model_name = model_name_raw.replace(" Preview", "").replace("Google AI Studio", "").strip()
                # Specific cleanups if needed:
                if "Gemini 1.5 Flash-8B" in model_name: model_name = "Gemini 1.5 Flash 8B"
                if "Text Embedding 004" in model_name : model_name = "text-embedding-004"

                # Find the pricing table associated with this header
                table = header.find_next_sibling('table')
                if not table:
                    # print(f"Warning: No table found for model '{model_name_raw}'", file=sys.stderr)
                    continue

                input_price_1m = None
                output_price_1m = None

                rows = table.find_all('tr')
                for row in rows[1:]: # Skip header row
                    cells = row.find_all('td')
                    if len(cells) > 2:
                        row_header = cells[0].get_text(strip=True).lower()
                        paid_tier_cell = cells[2] # Paid Tier is usually the 3rd column (index 2)
                        paid_tier_text = paid_tier_cell.get_text(strip=True)
                        
                        if "input price" in row_header:
                            input_price_1m = clean_google_price(paid_tier_text)
                        elif "output price" in row_header:
                             # Special handling for 2.5 Flash output with Thinking
                            if "Gemini 2.5 Flash" in model_name and "Non-thinking:" in paid_tier_text:
                                match = re.search(r"Non-thinking:\s*\$?([\d.]+)", paid_tier_text, re.IGNORECASE)
                                if match:
                                     output_price_1m = clean_google_price(match.group(1))
                                else: 
                                     output_price_1m = clean_google_price(paid_tier_text) # fallback
                            else:
                                output_price_1m = clean_google_price(paid_tier_text)

                # Find context window info in the text between H2 and table
                context_window = None
                description_tag = header.find_next_sibling('p') # Assume context is in the paragraph after h2
                if description_tag:
                    context_str_match = re.search(r"(\d+(?:\.\d+)?\s*(?:million|M|k)?)\s*token context window", description_tag.get_text(), re.IGNORECASE)
                    if context_str_match:
                        context_window = parse_context_window(context_str_match.group(1))
                    else: # Fallback check directly in header text itself for some models
                        context_str_match = re.search(r"(\d+(?:\.\d+)?\s*(?:million|M|k)?)\s*token context window", model_name_raw, re.IGNORECASE)
                        if context_str_match:
                            context_window = parse_context_window(context_str_match.group(1))
                
                # Only add if we found pricing info
                if input_price_1m is not None or output_price_1m is not None:
                     pricing_data.append(LLMModelPricing(
                         model=model_name,
                         provider="google",
                         input_tokens_price=input_price_1m, # Already per 1M
                         output_tokens_price=output_price_1m, # Already per 1M
                         context=context_window,
                         source=url,
                         updated=update_date_str
                    ))
                # else:
                #     print(f"-- Info: Skipping model '{model_name}' as no pricing found in table.", file=sys.stderr)

        except requests.exceptions.RequestException as e:
            print(f"Error fetching Google pricing page: {e}", file=sys.stderr)
        except Exception as e:
            print(f"Error parsing Google pricing page for {model_name_raw if 'model_name_raw' in locals() else 'Unknown Model'}: {e}", file=sys.stderr)
        
        # Filter out models without any price info if any slipped through
        pricing_data = [p for p in pricing_data if p.input_tokens_price is not None or p.output_tokens_price is not None]
        return pricing_data 