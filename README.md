# LLM Price Scraper
LLM Price Scraper is a Python package designed to scrape and organize pricing information for large language models (LLMs) from various web sources.

**Supported Data Sources:**

*   **OPENAI:** Official OpenAI pricing page.
*   **ANTHROPIC:** Official Anthropic pricing page.
*   **GOOGLE:** Google AI Platform pricing.
*   **MISTRAL:** Official Mistral AI pricing.
*   **META:** Meta Llama models (often via aggregators).
*   **COHERE:** Official Cohere pricing.
*   **GROQ:** GroqCloud pricing page.
*   **AI21:** AI21 Labs pricing.
*   **BEDROCK:** AWS Bedrock pricing (often aggregates multiple providers).
*   **AZURE:** Azure OpenAI Service pricing.
*   **DOCSBOT:** <https://docsbot.ai/tools/gpt-openai-api-pricing-calculator> (Aggregator)
*   **BOTGENUITY:** <https://www.botgenuity.com/tools/llm-pricing> (Aggregator)
*   **HUGGINGFACE:** Data extracted from <https://huggingface.co/spaces/hf-llm-leaderboard/pricing> (Aggregator)
*(Note: Availability and accuracy depend on the source sites/APIs remaining stable.)*

## Installation

You can install the package using pip:
```bash
# From PyPI (if published)
# pip install llm-price-scraper

# Or directly from GitHub
pip install git+https://github.com/WilliamJlvt/llm_price_scraper.git

# Or clone and install locally for development:
git clone https://github.com/WilliamJlvt/llm_price_scraper.git
cd llm_price_scraper
pip install -e .
```

## Python Usage

Once installed, you can import and use the scraper in your Python code:

```python
from llm_price_scraper.scrapers import LlmPricingScraper, DataSources, LLMModelPricing

# --- Get data from a specific source ---
print("\n--- Scraping OpenAI ---")
try:
    openai_data: list[LLMModelPricing] = LlmPricingScraper.scrape(DataSources.OPENAI)
    if openai_data:
        print(openai_data[0]) 
        # Output includes model, provider, input_tokens_price (per 1M), output_tokens_price (per 1M), context, source, updated
    else:
        print("No data found for OpenAI.")
except Exception as e:
    print(f"Error scraping OpenAI: {e}")


# --- Get data from Google ---
print("\n--- Scraping Google ---")
try:
    google_data = LlmPricingScraper.scrape(DataSources.GOOGLE)
    if google_data:
        print(google_data[0])
    else:
        print("No data found for Google.")
except Exception as e:
    print(f"Error scraping Google: {e}")
```

## Command-Line Script Usage (`scrape_llm_prices.py`)

A utility script `scrape_llm_prices.py` is included in the root directory for convenient command-line scraping and output generation. It converts prices to **USD per 1k tokens** by default.

**Basic Usage:**

```bash
# Scrape a single source (outputs to ./<SourceName>_prices.json by default)
python scrape_llm_prices.py OPENAI
python scrape_llm_prices.py GOOGLE

# Scrape multiple specific sources (outputs multiple files by default)
python scrape_llm_prices.py OPENAI GOOGLE ANTHROPIC

# Scrape ALL available sources (outputs multiple files by default)
python scrape_llm_prices.py ALL
```

**Output Options:**

*   **Output Format (`-f`, `--format`):**
    *   Specify the output format: `json` (default) or `lua`.
    *   Example: `python scrape_llm_prices.py OPENAI -f lua`
*   **Output Directory (`-o`, `--output-dir`):**
    *   Specify the directory to save output file(s). Defaults to the current directory (`.`).
    *   Example: `python scrape_llm_prices.py ALL -o ./pricing_data`
*   **Output Mode (`--output-mode`):**
    *   Controls output when scraping multiple sources (either via `ALL` or listing multiple names).
    *   `multiple` (default): Saves each scraped source to its own file (e.g., `OPENAI_prices.json`, `GOOGLE_prices.json`).
    *   `single`: Merges results from all specified *and successfully scraped* sources into one file.
        *   Example (Multiple): `python scrape_llm_prices.py OPENAI GOOGLE` -> `OPENAI_prices.json`, `GOOGLE_prices.json`
        *   Example (Single): `python scrape_llm_prices.py OPENAI GOOGLE --output-mode single` -> `OPENAI_GOOGLE_prices.json`
        *   Example (ALL - Single): `python scrape_llm_prices.py ALL --output-mode single` -> `ALL_llm_prices.json`

**Merging Logic (`--output-mode single`):**

When merging data into a single file, the script handles potential duplicate entries (same provider/model name from different sources) using the following logic:
1.  **Source Priority:** Entries from sources defined with higher priority (lower number) in the `SOURCE_PRIORITIES` dictionary within the script are preferred.
2.  **Data Completeness:** If sources have the same priority, entries with more complete data (defined input price, output price, and context window) are preferred.
3.  **First Encountered:** If both priority and completeness are equal, the first entry encountered during processing is kept.

The resulting merged file will contain only the "best" entry found for each unique provider/model combination based on this logic.

**Listing Available Sources:**

Run the script with `-h` or `--help` to see the full list of options and available source names.

```bash
python scrape_llm_prices.py --help
```

### Example Output (`.json` format, prices per 1k tokens)

**Multiple Files Mode (e.g., `OPENAI_prices.json`):**

```json
{
    "metadata": {
        "source_description": "OPENAI",
        "generated_at": "2024-07-27T15:30:00.123456",
        "price_unit": "USD per 1k tokens"
    },
    "models": {
        "openai": {
            "gpt-4o": {
                "model": "gpt-4o",
                "input_cost_per_1k_tokens": 0.005,
                "output_cost_per_1k_tokens": 0.015,
                "context_window_tokens": 128000,
                "source": "OPENAI",
                "updated": "2024-07-26"
            },
            "gpt-4-turbo": {
                "model": "gpt-4-turbo",
                "input_cost_per_1k_tokens": 0.01,
                "output_cost_per_1k_tokens": 0.03,
                "context_window_tokens": 128000,
                "source": "OPENAI",
                "updated": "2024-07-26"
            }
            // ... other OpenAI models
        }
    }
}
```

**Single File Mode (e.g., `ALL_llm_prices.json`):**

Note the `winning_source` field indicating which source provided the data after merging.

```json
{
    "metadata": {
        "source_description": "All sources (merged by priority)",
        "generated_at": "2024-07-27T15:35:00.987654",
        "price_unit": "USD per 1k tokens"
    },
    "models": {
        "openai": {
            "gpt-4o": {
                "model": "gpt-4o",
                "input_cost_per_1k_tokens": 0.005,
                "output_cost_per_1k_tokens": 0.015,
                "context_window_tokens": 128000,
                "source": "OPENAI", // Original source enum/name
                "updated": "2024-07-26",
                "winning_source": "OPENAI" // Source that won the merge
            }
            // ... other OpenAI models (potentially from different winning sources)
        },
        "anthropic": {
            "claude-3-5-sonnet-20240620": {
                "model": "claude-3-5-sonnet-20240620",
                "input_cost_per_1k_tokens": 0.003,
                "output_cost_per_1k_tokens": 0.015,
                "context_window_tokens": 200000,
                "source": "ANTHROPIC",
                "updated": "2024-07-25",
                "winning_source": "ANTHROPIC"
             }
            // ... other Anthropic models
        },
        "google": {
             "gemini-1.5-pro-latest": {
                "model": "gemini-1.5-pro-latest",
                "input_cost_per_1k_tokens": 0.0035, // Example price
                "output_cost_per_1k_tokens": 0.0105, // Example price
                "context_window_tokens": 1000000,
                "source": "GOOGLE",
                "updated": "2024-07-24",
                "winning_source": "GOOGLE"
            }
            // ... other Google models
        }
        // ... other providers
    }
}
```

### Error Handling
Both the Python library and the command-line script will print error messages to standard error (`stderr`) if scraping fails for a specific source.

When scraping multiple sources, errors for one source will not stop the scraping of others.

## Contributing
Contributions, bug reports, and feature requests are welcome! Feel free to submit a pull request or open an issue on GitHub.

## License
This project is licensed under the MIT License - see the LICENSE file for details.
