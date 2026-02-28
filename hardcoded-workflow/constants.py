"""
Configuration constants for NovaBoard Electronics Production Scheduling Agent.
"""

from datetime import datetime, timezone

# API Configuration
BASE_URL = "https://hackathon33.arke.so"
USERNAME = "arke"
PASSWORD = "arke"

# Scheduling Configuration
TODAY = datetime.now(timezone.utc)
MINS_PER_DAY = 480

# Telegram Configuration
TELEGRAM_BOT_TOKEN = "8391945774:AAGCryNT_t-ePLJcFI2lrNZTqVm8gBH9RQk"
TELEGRAM_CHAT_ID = "-1003833527945"
TELEGRAM_POLL_TIMEOUT = 30  # seconds

# BOM: total minutes per unit, keyed by product code
# Source: mission briefing (SMT + Reflow + THT + AOI + Test + Coating + Pack)
BOM_MINS_PER_UNIT = {
    "PCB-IND-100": 147,
    "MED-300": 279,
    "IOT-200": 63,
    "AGR-400": 144,
    "PCB-PWR-500": 75,
}

PRODUCT_NAME_TO_CODE = {
    "Industrial Control Board": "PCB-IND-100",
    "Medical Monitor PCB": "MED-300",
    "IoT Sensor Board": "IOT-200",
    "AgriBot Control PCB": "AGR-400",
    "Power Management PCB": "PCB-PWR-500",
}
