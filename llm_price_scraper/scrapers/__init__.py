from llm_price_scraper.enums import DataSources
from llm_price_scraper.scrapers.botgenuity import BotgenuityScraper
from llm_price_scraper.scrapers.docsbot import DocsBotScraper
from llm_price_scraper.scrapers.huggingface import HuggingfaceScraper
from llm_price_scraper.scrapers.huhuhang import HuhuhangScraper
from llm_price_scraper.scrapers.openai import OpenaiScraper
from llm_price_scraper.scrapers.google import GoogleScraper
from llm_price_scraper.scrapers.anthropic import AnthropicScraper
from llm_price_scraper.scrapers.groq import GroqScraper
from llm_price_scraper.scrapers.cohere import CohereScraper
from llm_price_scraper.scrapers.mistral import MistralScraper
from llm_price_scraper.scrapers.amazon import AmazonScraper
from llm_price_scraper.scrapers.liquid import LiquidScraper
from llm_price_scraper.scrapers.reka import RekaScraper
from llm_price_scraper.scrapers.xai import XAIScraper
from llm_price_scraper.scrapers.together import TogetherScraper
from llm_price_scraper.scrapers.fireworks import FireworksScraper
from llm_price_scraper.scrapers.replicate import ReplicateScraper
from llm_price_scraper.scrapers.anyscale import AnyscaleScraper
from llm_price_scraper.scrapers.databricks import DatabricksScraper

class LlmPricingScraper:
    @staticmethod
    def scrape(source: DataSources = DataSources.HUGGINGFACE):
        """
        Scrape the LLM pricing information from the specified source.
        Note: Some scrapers might not retrieve pricing (e.g., Groq, Mistral, Liquid, Together) 
              or context/max tokens (e.g., Amazon, Cohere, Reka, XAI).

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
        elif source == DataSources.ANTHROPIC:
            return AnthropicScraper.scrape()
        elif source == DataSources.GROQ:
            return GroqScraper.scrape()
        elif source == DataSources.COHERE:
            return CohereScraper.scrape()
        elif source == DataSources.MISTRAL:
            return MistralScraper.scrape()
        elif source == DataSources.AMAZON:
            return AmazonScraper.scrape()
        elif source == DataSources.LIQUID:
            return LiquidScraper.scrape()
        elif source == DataSources.REKA:
            return RekaScraper.scrape()
        elif source == DataSources.XAI:
            return XAIScraper.scrape()
        elif source == DataSources.TOGETHER:
            return TogetherScraper.scrape()
        elif source == DataSources.FIREWORKS:
            return FireworksScraper.scrape()
        elif source == DataSources.REPLICATE:
            return ReplicateScraper.scrape()
        elif source == DataSources.ANYSCALE:
            return AnyscaleScraper.scrape()
        elif source == DataSources.DATABRICKS:
            return DatabricksScraper.scrape()
        elif source == DataSources.HUHUHANG:
            raise Exception(f"Source '{source}' is currently disabled.")
        elif source == DataSources.OPENAI:
            raise Exception(f"Direct scraping for '{source}' is currently disabled (use aggregate sources).")
        else:
            raise Exception(f"Source '{source}' is not supported or recognized.")
