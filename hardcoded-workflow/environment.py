import os

from dotenv import load_dotenv

load_dotenv()  # reads variables from a .env file and sets them in os.environ

def _get_required_env(key: str) -> str:
    """Get required environment variable or raise an exception."""
    value = os.getenv(key)
    if value is None:
        raise ValueError(f"Required environment variable '{key}' is not set. Please check your .env file.")
    return value

# Telegram Configuration
TELEGRAM_BOT_TOKEN = _get_required_env("TELEGRAM_BOT_TOKEN")
TELEGRAM_CHAT_ID = _get_required_env("TELEGRAM_CHAT_ID")
TELEGRAM_POLL_TIMEOUT = int(os.getenv("TELEGRAM_POLL_TIMEOUT", "600"))

# Arke API Configuration
ARKE_TENANT = _get_required_env("ARKE_TENANT")
ARKE_USERNAME = _get_required_env("ARKE_USERNAME")
ARKE_PASSWORD = _get_required_env("ARKE_PASSWORD")

# Gemini API Configuration
GEMINI_API_KEY = _get_required_env("GEMINI_API_KEY")
