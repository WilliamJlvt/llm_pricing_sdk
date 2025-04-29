import datetime
import json
from llm_price_scraper.enums import DataSources
from llm_price_scraper.scrapers import LlmPricingScraper


def combine_models(sources):
    """
    Combine models from multiple sources into a single dictionary based on unique model names.

    Arguments:
        - sources (list): List of data sources to scrape from.

    Returns:
        - combined_models (list): List of unique models with their pricing info.
    """
    combined_models = {}

    # Loop over each data source
    for source in sources:
        print(f"Scraping source: {source}")
        try:
            # Scrape models from the source
            models = LlmPricingScraper.scrape(source)

            for model in models:
                # If model name is not already in the dictionary, add it
                if model.model not in combined_models:
                    combined_models[model.model] = {
                        "model": model.model,
                        "provider": model.provider,
                        "input_tokens_price": model.input_tokens_price,
                        "output_tokens_price": model.output_tokens_price,
                        "context": model.context,
                        "source": model.source,
                        "updated": model.updated
                    }

        except Exception as e:
            print(f"Error scraping source {source}: {e}")

    return list(combined_models.values())


def save_to_json(data, filename):
    """Saves the provided data into a JSON file."""
    with open(filename, 'w', encoding='utf-8') as json_file:
        json.dump(data, json_file, ensure_ascii=False, indent=4)
    print(f"Data successfully saved to {filename}")


if __name__ == "__main__":
    sources_to_scrape = [
        DataSources.DOCSBOT,
        DataSources.BOTGENUITY,
        DataSources.HUGGINGFACE,
        DataSources.GOOGLE,
        # DataSources.HUHUHANG, # Disabled
        # DataSources.OPENAI # Disabled
    ]

    combined_models = combine_models(sources_to_scrape)

    now = datetime.datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
    save_to_json(combined_models, f"combined_llm_pricing_models({now}).json")
