# LLM Price Scraper
LLM Price Scraper is a Python package designed to scrape and organize pricing information for large language models (LLMs) from various web sources.

**Supported Data Sources:**

*   **DocsBot:** <https://docsbot.ai/tools/gpt-openai-api-pricing-calculator>
*   **Botgenuity:** <https://www.botgenuity.com/tools/llm-pricing>
*   **Hugging Face:** Data extracted from <https://huggingface.co/spaces/Presidentlin/llm-pricing-calculator/resolve/main/src/lib/data.ts>
*   **Google:** <https://ai.google.dev/gemini-api/docs/pricing>

*(Note: Other sources like huhuhang and direct OpenAI scraping are currently disabled due to source availability or scraping challenges.)*

## Installation

You can install the package using pip:
```bash
pip install .
# Or for development:
pip install -e .
```
*(Alternatively, if published)*
```bash
# pip install llm-price-scraper 
```

## Python Usage

Once installed, you can import and use the scraper in your Python code:

```python
from llm_price_scraper.scrapers import LlmPricingScraper, DataSources

# --- Get data from a specific source ---
print("\n--- Scraping DocsBot ---")
docsbot_data = LlmPricingScraper.scrape(DataSources.DOCSBOT)

# Print the first entry (if any)
if docsbot_data:
    print(docsbot_data[0]) 
    # Output includes model, provider, input_tokens_price (per 1M), output_tokens_price (per 1M), context, source, updated
else:
    print("No data found for DocsBot.")

# --- Get data from Google ---
print("\n--- Scraping Google ---")
google_data = LlmPricingScraper.scrape(DataSources.GOOGLE)
if google_data:
    print(google_data[0])
else:
    print("No data found for Google.")
    
# --- Get data from Hugging Face (Default if no source specified) ---
print("\n--- Scraping Hugging Face (Default) ---")
hf_data = LlmPricingScraper.scrape() # Defaults to HUGGINGFACE
if hf_data:
    print(hf_data[0])
else:
    print("No data found for Hugging Face.")
```

## Command-Line Script Usage (`examples/scrape_cli.py`)

A utility script `examples/scrape_cli.py` is included for convenient command-line scraping and output generation.

**Basic Usage:**

```bash
# Navigate to the project root directory first

# Scrape a single source (outputs to <SourceName>.json by default, prices per 1M tokens)
python3 examples/scrape_cli.py DOCSBOT
python3 examples/scrape_cli.py GOOGLE

# Scrape all available sources and merge (outputs to COMBINED_LLM_PRICING.json by default, prices per 1M tokens)
python3 examples/scrape_cli.py ALL
```

**Specifying Output Format and Price Unit:**

*   Use the `--format` or `-f` option to specify the output format (`json` or `lua`). JSON is the default.
*   Use the `--unit` or `-u` option to specify the price unit (`1m` for per Million tokens, `1k` for per Thousand tokens). `1m` is the default.

```bash
# Output DOCSBOT data as Lua, prices per 1k tokens
python3 examples/scrape_cli.py DOCSBOT --format lua --unit 1k

# Output combined data as Lua, prices per 1M tokens (default unit)
python3 examples/scrape_cli.py ALL -f lua -u 1m 

# Output Google data as JSON, prices per 1k tokens
python3 examples/scrape_cli.py GOOGLE -f json -u 1k
```

**Available Sources for Script:**

Run the script without arguments to see the list of currently enabled sources:
```bash
python3 examples/scrape_cli.py
```

### Example Output (`.json` format, default unit: 1m)

The JSON output (`COMBINED_LLM_PRICING.json` or `<SourceName>.json`) contains metadata and models grouped by provider:

```json
{
    "metadata": {
        "source_description": "All enabled sources", // or specific source name
        "generated_at": "2024-10-28T12:00:00.123456",
        "price_unit": "USD per 1m tokens"
    },
    "models": {
        "google": {
            "Gemini 1.5 Pro": {
                "model": "Gemini 1.5 Pro",
                "input_cost_per_1k_tokens": 0.00125,
                "output_cost_per_1k_tokens": 0.005,
                "context_window_tokens": 128000,
                "source": "https://ai.google.dev/gemini-api/docs/pricing",
                "updated": "2025-04-21"
            },
            // ... other Google models
        },
        "anthropic": {
            "claude-3-haiku": {
                "model": "claude-3-haiku",
                "input_cost_per_1k_tokens": 0.00025,
                "output_cost_per_1k_tokens": 0.00125,
                "context_window_tokens": 200000,
                "source": "https://www.botgenuity.com/tools/llm-pricing",
                "updated": "2024-12-20"
             },
            // ... other Anthropic models (from various sources)
        },
        // ... other providers
    }
}
```

### Error Handling
Both the Python library and the command-line script will print error messages to standard error (`stderr`) if scraping fails for a specific source.

When using `ALL` in the script, errors for one source will not stop the scraping of others.

## Contributing
Contributions, bug reports, and feature requests are welcome! Feel free to submit a pull request or open an issue on GitHub.

## License
This project is licensed under the MIT License - see the LICENSE file for details.
