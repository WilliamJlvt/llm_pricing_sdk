from setuptools import setup, find_packages

setup(
    name="llm_price_scraper",
    version="1.0.4",
    packages=find_packages(),
    install_requires=[
        "requests>=2.32.3",
        "beautifulsoup4>=4.12.3"
    ],
    author="WilliamJlvt",
    description="A simple Python SDK to scrape and retrieve pricing information for Large Language Models (LLMs) from an external webpage, with structured models for easy integration and usage.",
    author_email="william.jolivet@epitech.eu",
    long_description=open('README.md').read(),
    long_description_content_type='text/markdown',
    url="https://github.com/WilliamJlvt/llm_price_scraper",
    python_requires='>=3.6',
)
