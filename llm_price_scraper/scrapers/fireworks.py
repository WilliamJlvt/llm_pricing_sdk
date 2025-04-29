import requests
import re
import sys
from bs4 import BeautifulSoup
from datetime import datetime

from llm_price_scraper.models import LLMModelPricing
from llm_price_scraper.utils import parse_context_window, parse_price

class FireworksScraper:
    URL = "https://fireworks.ai/pricing"
    PROVIDER_NAME = "fireworks" # Fireworks hosts models from various providers

    @staticmethod
    def scrape():
        pricing_data = []
        updated_date = datetime.now().strftime("%Y-%m-%d")

        try:
            response = requests.get(FireworksScraper.URL)
            response.raise_for_status()
            soup = BeautifulSoup(response.content, "html.parser")

            # Find pricing tables - might need refinement based on actual structure
            # Look for tables within the main content area
            content_area = soup.find('main') or soup.body # Adjust selector if needed
            if not content_area:
                raise Exception("Could not find main content area.")
                
            tables = content_area.find_all('table')
            if not tables:
                raise Exception(f"Could not locate any pricing tables on {FireworksScraper.URL}")

            processed_models = set()

            for table in tables:
                tbody = table.find('tbody')
                if not tbody: continue

                rows = tbody.find_all('tr')
                if not rows: continue

                # Infer headers or assume structure - check first row's cells
                header_texts = [th.get_text(strip=True).lower() for th in table.find_all('th')]
                
                # Indices will vary based on table structure
                model_idx = -1
                price_idx = -1
                
                # --- Try to identify columns based on header text ---
                # This part needs careful adjustment based on the *actual* table headers
                # Example guesses:
                for i, h in enumerate(header_texts):
                    if 'model' in h or 'base model' in h or 'parameter count' in h:
                        model_idx = i
                    if '$/1m tokens' in h or '$/step' in h or '$/audio min' in h or '$ / 1m tokens' in h: # Handle variations
                        price_idx = i
                
                # --- Fallback/Refinement if headers aren't clear ---
                # If indices are still -1, we might need to inspect the first data row
                # or assume a fixed structure (less robust)
                if model_idx == -1 or price_idx == -1:
                    # Try assuming based on first row structure if headers were unclear
                    first_row_cells = rows[0].find_all('td')
                    if len(first_row_cells) >= 2:
                        # Check if the first cell looks like a model name/link and second looks like a price
                        if first_row_cells[0].find('a') or 'b ' in first_row_cells[0].get_text(strip=True).lower(): # Heuristic for model names
                            model_idx = 0
                        if '$' in first_row_cells[1].get_text(strip=True): # Heuristic for price
                            price_idx = 1
                        # Adjust indices if more columns exist (e.g., separate input/output)
                        if len(first_row_cells) > 2 and '$' in first_row_cells[2].get_text(strip=True):
                           # Assume input price is idx 1, output idx 2? Needs verification.
                           pass # We'll handle split prices later

                    if model_idx == -1 or price_idx == -1:
                       print(f"Warning: Could not reliably determine columns for a table on {FireworksScraper.URL}. Headers: {header_texts}. Skipping table.", file=sys.stderr)
                       continue # Skip this table if columns are ambiguous

                # --- Process rows ---
                for row in rows:
                    cells = row.find_all('td')
                    if len(cells) <= max(model_idx, price_idx):
                        continue

                    model_name_raw = cells[model_idx].get_text(strip=True)
                    price_str_raw = cells[price_idx].get_text(strip=True)

                    # Extract model name - might be inside a link
                    model_link = cells[model_idx].find('a')
                    model_name = model_link.get_text(strip=True) if model_link else model_name_raw
                    
                    # Handle tiered pricing description (e.g., "16.1B+")
                    if 'b+' in model_name.lower() or 'b - ' in model_name.lower() or 'parameter count' in model_name_raw.lower():
                         # Label these generically, or skip if we only want specific models
                         # For now, let's prepend "Tier: "
                         model_name = f"Tier: {model_name}"

                    if not model_name or model_name in processed_models:
                        continue

                    input_price = None
                    output_price = None

                    # Check for separate input/output prices within the price cell or adjacent cells
                    # Example: "$3.00 input, $8.00 output" or separate columns
                    price_str_lower = price_str_raw.lower()
                    if 'input' in price_str_lower and 'output' in price_str_lower:
                        # Attempt to parse split prices like "$A input, $B output"
                        input_match = re.search(r'([\d\.]+)\s*input', price_str_lower)
                        output_match = re.search(r'([\d\.]+)\s*output', price_str_lower)
                        if input_match and output_match:
                            input_price = parse_price(input_match.group(1))
                            output_price = parse_price(output_match.group(2))
                        else:
                           # Fallback if regex fails, try simple split
                           parts = re.split(r',|\s+', price_str_raw)
                           if len(parts) >= 4 and 'input' in parts[1].lower() and 'output' in parts[3].lower():
                               input_price = parse_price(parts[0])
                               output_price = parse_price(parts[2])
                           else:
                               print(f"Warning: Could not parse split input/output price: {price_str_raw}", file=sys.stderr)
                               # Try parsing as a single price as fallback
                               price = parse_price(price_str_raw)
                               input_price = price
                               output_price = price
                    elif len(cells) > price_idx + 1 and '$' in cells[price_idx + 1].get_text(strip=True):
                        # Check if the *next* cell also contains a price (potential output price column)
                        input_price = parse_price(price_str_raw)
                        output_price = parse_price(cells[price_idx + 1].get_text(strip=True))
                    else:
                        # Assume single price for both input and output
                        price = parse_price(price_str_raw)
                        input_price = price
                        output_price = price

                    # Context window and max tokens are not typically on pricing pages
                    context_tokens = None
                    max_output_tokens = None

                    pricing_data.append(LLMModelPricing(
                        model=model_name,
                        provider=FireworksScraper.PROVIDER_NAME,
                        input_tokens_price=input_price,
                        output_tokens_price=output_price,
                        context=context_tokens,
                        max_output_tokens=max_output_tokens,
                        source=FireworksScraper.URL,
                        updated=updated_date
                    ))
                    processed_models.add(model_name)

        except requests.exceptions.RequestException as e:
            print(f"Error fetching Fireworks AI pricing page: {e}", file=sys.stderr)
        except Exception as e:
            print(f"Error parsing Fireworks AI pricing page: {e}", file=sys.stderr)
            import traceback
            traceback.print_exc() # More detailed error for debugging

        return pricing_data

# Example usage for testing:
# if __name__ == '__main__':
#     results = FireworksScraper.scrape()
#     print(f"Found {len(results)} Fireworks pricing entries.")
#     for result in results:
#         print(result) 