from enum import Enum

class DataSources(Enum):
    DOCSBOT = "docsbot"  # Most likely to be used
    BOTGENUITY = "botgenuity"
    HUGGINGFACE = "huggingface"
    GOOGLE = "google"
    ANTHROPIC = "anthropic"
    GROQ = "groq"
    COHERE = "cohere"
    MISTRAL = "mistralai" # Use consistent provider key
    AMAZON = "amazon"
    LIQUID = "liquid"
    REKA = "reka"
    XAI = "xai"
    TOGETHER = "together"
    FIREWORKS = "fireworks"
    REPLICATE = "replicate"
    ANYSCALE = "anyscale"
    DATABRICKS = "databricks"
    # HUHUHANG = "huhuhang" # Disabled
    # OPENAI = "openai" # Disabled
