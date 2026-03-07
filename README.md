# Coffee-Hounds-Manufacturing-Workflows

## Setup

1. Install `poetry` if not present yet: `curl -sSL https://install.python-poetry.org | python3 -`
2. Install requirements: `poetry install`
3. **Configure environment variables**:
   - Copy `.env.template` to `.env`: `cp .env.template .env`
   - Edit `.env` and fill in your actual credentials:
     - `TELEGRAM_BOT_TOKEN`: Your Telegram bot token
     - `TELEGRAM_CHAT_ID`: Your Telegram chat ID
     - `ARKE_TENANT`: Your Arke tenant URL
     - `ARKE_USERNAME`: Your Arke username
     - `ARKE_PASSWORD`: Your Arke password
     - `GEMINI_API_KEY`: Your Google Gemini API key
4. Run manual flow: `poetry run python src/run_flow.py`

## Dependencies

### Core Libraries
- **python-telegram-bot** (`^22.6`) - Telegram Bot API for sending messages and managing bot interactions
- **opencv-python** (`^4.13.0.92`) - Computer vision library for image processing and analysis
- **numpy** (`^2.1.3`) - Numerical computing library for array operations
- **pydantic** (`^2.12.5`) - Data validation and parsing using Python type annotations
- **httpx** (`^0.28.1`) - Async HTTP client library for making API requests
- **tqdm** (`^4.66.6`) - Progress bar utility for tracking long-running operations
- **python-dotenv** (`^1.2.1`) - Environment variable management from .env files

