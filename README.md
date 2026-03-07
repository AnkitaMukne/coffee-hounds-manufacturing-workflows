# Coffee-Hounds-Manufacturing-Workflows

This is the submission code base for team `Coffee Hounds`'s submission to the [24h Physical AI Hackathon](https://archive.is/Imr6C) organised by [Forgis](https://www.forgis.com/), [Arke](https://www.arke.so/), [Google DeepMind](https://deepmind.google/), and [IBM Research](https://research.ibm.com/).

Our team worked on the challenge presented by Arke, which is about creating an intelligent agent scheduling manufacturing orders in a simulated factory. You can find more info on the challenge setup [here](https://archive.is/6TAy5).

## Our Solution

We solve the problem by running through six steps in our main loop:

1. Read open orders from `Arke`'s API - show what needs to be produced
2. Run planning policy and resolve conflicts using `Gemini`
3. Create production orders in `Arke`
4. Schedule phases with concrete start/end dates
5. Human-in-the-loop - present schedule via `Telegram` and get approval or jump back with modification instructions
6. Physical integration - advance production with real-time signals

We also have a video of the live demo available. Ping [@AnkitaMukne](https://github.com/AnkitaMukne) or [@mpoemsl](https://github.com/mpoemsl/) if you would like to see it!

### Setup

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


### Usage

Simply run the flow by calling `poetry run python src/run_flow.py` 🚀

### Dependencies

### Core Libraries
- **python-telegram-bot** (`^22.6`) - Telegram Bot API for sending messages and managing bot interactions
- **opencv-python** (`^4.13.0.92`) - Computer vision library for image processing and analysis
- **numpy** (`^2.1.3`) - Numerical computing library for array operations
- **pydantic** (`^2.12.5`) - Data validation and parsing using Python type annotations
- **httpx** (`^0.28.1`) - Async HTTP client library for making API requests
- **tqdm** (`^4.66.6`) - Progress bar utility for tracking long-running operations
- **python-dotenv** (`^1.2.1`) - Environment variable management from .env files

