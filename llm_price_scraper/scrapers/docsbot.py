import requests
from bs4 import BeautifulSoup
from datetime import datetime
from llm_price_scraper.models import LLMModelPricing
from llm_price_scraper.utils import parse_context_window


class DocsBotScraper:
    @staticmethod
    def scrape():
        url = "https://docsbot.ai/tools/gpt-openai-api-pricing-calculator"
        response = requests.get(url)

        if response.status_code != 200:
            raise Exception(
                f"Failed to fetch data from {url}. Status code: {response.status_code}")

        soup = BeautifulSoup(response.content, "html.parser")

        table = soup.find("table")
        if not table:
            raise Exception("No table found on the page.")

        rows = []
        for tr in table.find("tbody").find_all("tr"):
            cells = tr.find_all("td")

            if len(cells) >= 7:
                provider = cells[0].text.strip()

                model_td = cells[1]
                model_name = model_td.text.strip()
                model_name_div = model_td.find("div")
                if model_name_div:
                    # Use the <div> inside the <td> to get the accurate model name
                    model_name = model_name_div.text.strip()
                else:
                    # If no <div> is found, use the text content of the <td>
                    model_name = model_name

                context_str = cells[2].text.strip()
                context_window = parse_context_window(context_str)

                input_tokens_price = cells[3].text.strip().replace("$", "")
                output_tokens_price = cells[4].text.strip().replace("$", "")
                updated = datetime.now().strftime("%Y-%m-%d")

                pricing_info = LLMModelPricing(
                    model=model_name,
                    provider=provider,
                    input_tokens_price=float(
                        input_tokens_price) if input_tokens_price else 0.0,
                    output_tokens_price=float(
                        output_tokens_price) if output_tokens_price else 0.0,
                    context=context_window,
                    source=url,
                    updated=updated
                )

                rows.append(pricing_info)

        return rows
