import re
from datetime import datetime

from llm_price_scraper.utils import fetch_ts_file
from llm_price_scraper.models import LLMModelPricing


class HuggingfaceScraper:
    @staticmethod
    def scrape():
        url = "https://huggingface.co/spaces/Presidentlin/llm-pricing-calculator/resolve/main/src/lib/data.ts"

        provider_regex = re.compile(r"provider: '(.*?)',")
        uri_regex = re.compile(r"uri: '(.*?)',")
        models_regex = re.compile(r"\{ name: '(.*?)', inputPrice: ([\d.]+), outputPrice: ([\d.]+) \}")

        providers = []

        content = fetch_ts_file(url)
        provider_blocks = content.split('},\n  {')

        for block in provider_blocks:
            provider_match = provider_regex.search(block)
            uri_match = uri_regex.search(block)

            if provider_match and uri_match:
                provider_name = provider_match.group(1)
                provider_uri = uri_match.group(1)
                models = models_regex.findall(block)

                for model in models:
                    model_name, input_price, output_price = model
                    pricing_data = LLMModelPricing(
                        model=model_name,
                        provider=provider_name,
                        input_tokens_price=float(input_price) if input_price else 0.0,
                        output_tokens_price=float(output_price) if output_price else 0.0,
                        context="",
                        source=provider_uri,
                        updated=str(datetime.now().date())
                    )
                    providers.append(pricing_data)

        return providers
