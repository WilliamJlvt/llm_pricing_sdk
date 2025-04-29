from llm_price_scraper.enums import DataSources
from llm_price_scraper.scrapers.botgenuity import BotgenuityScraper
from llm_price_scraper.scrapers.docsbot import DocsBotScraper
from llm_price_scraper.scrapers.huggingface import HuggingfaceScraper
from llm_price_scraper.scrapers.huhuhang import HuhuhangScraper
from llm_price_scraper.scrapers.openai import OpenaiScraper
from llm_price_scraper.scrapers.google import GoogleScraper

class LlmPricingScraper:
    @staticmethod
    def scrape(source: DataSources = DataSources.HUGGINGFACE):
        """
        Scrape the LLM pricing information from the specified source.

        :returns: A list of LLMModelPricing objects.
        """
        if source == DataSources.DOCSBOT:
            return DocsBotScraper.scrape()
        elif source == DataSources.BOTGENUITY:
            return BotgenuityScraper.scrape()
        elif source == DataSources.HUGGINGFACE:
            return HuggingfaceScraper.scrape()
        elif source == DataSources.GOOGLE:
            return GoogleScraper.scrape()
        elif source == DataSources.HUHUHANG:
            return HuhuhangScraper.scrape()
        elif source == DataSources.OPENAI:
            raise Exception(f"Source '{source}' is not supported.")
            # return OpenaiScraper.scrape()
        else:
            raise Exception(f"Source '{source}' is not supported.")
