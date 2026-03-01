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
4. Run manual flow: `poetry run python src/run_manual_flow.py`
