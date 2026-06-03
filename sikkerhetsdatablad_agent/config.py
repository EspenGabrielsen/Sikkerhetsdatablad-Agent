import os
from dotenv import load_dotenv

load_dotenv()

# PROVIDER: openai | azure | deepseek  (standard: openai)
PROVIDER: str = os.getenv("PROVIDER", "openai").lower()

# Standard OpenAI
OPENAI_API_KEY: str = os.getenv("OPENAI_API_KEY", "")
OPENAI_MODEL: str = os.getenv("OPENAI_MODEL", "gpt-4o")

# Azure OpenAI
AZURE_OPENAI_API_KEY: str = os.getenv("AZURE_OPENAI_API_KEY", "")
AZURE_OPENAI_ENDPOINT: str = os.getenv("AZURE_OPENAI_ENDPOINT", "")
AZURE_OPENAI_DEPLOYMENT: str = os.getenv("AZURE_OPENAI_DEPLOYMENT", "gpt-4o")
AZURE_OPENAI_API_VERSION: str = os.getenv(
    "AZURE_OPENAI_API_VERSION", "2024-08-01-preview"
)

# DeepSeek
DEEPSEEK_API_KEY: str = os.getenv("DEEPSEEK_API_KEY", "")
DEEPSEEK_MODEL: str = os.getenv("DEEPSEEK_MODEL", "deepseek-chat")
DEEPSEEK_BASE_URL: str = "https://api.deepseek.com"


def get_openai_client():
    """Returnerer riktig OpenAI-kompatibel klient basert på PROVIDER."""
    from openai import AzureOpenAI, OpenAI

    if PROVIDER == "azure":
        if not AZURE_OPENAI_API_KEY or not AZURE_OPENAI_ENDPOINT:
            raise ValueError(
                "PROVIDER=azure men AZURE_OPENAI_API_KEY og/eller AZURE_OPENAI_ENDPOINT mangler i .env"
            )
        return AzureOpenAI(
            api_key=AZURE_OPENAI_API_KEY,
            azure_endpoint=AZURE_OPENAI_ENDPOINT,
            api_version=AZURE_OPENAI_API_VERSION,
        )
    elif PROVIDER == "deepseek":
        if not DEEPSEEK_API_KEY:
            raise ValueError("DEEPSEEK_API_KEY mangler i .env")
        return OpenAI(
            api_key=DEEPSEEK_API_KEY,
            base_url=DEEPSEEK_BASE_URL,
        )
    else:  # openai (standard)
        if not OPENAI_API_KEY:
            raise ValueError("OPENAI_API_KEY mangler i .env")
        return OpenAI(api_key=OPENAI_API_KEY)


def get_model_name() -> str:
    if PROVIDER == "azure":
        return AZURE_OPENAI_DEPLOYMENT
    if PROVIDER == "deepseek":
        return DEEPSEEK_MODEL
    return OPENAI_MODEL
