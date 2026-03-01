"""
Utility functions for NovaBoard Electronics Production Scheduling Agent.
"""

from datetime import datetime

from constants import PRODUCT_NAME_TO_CODE


def infer_product_code(product_name: str) -> str:
    """Infer product code from product name."""
    for k, v in PRODUCT_NAME_TO_CODE.items():
        if k.lower() in product_name.lower():
            return v
    return ""


def parse_deadline(iso: str) -> datetime:
    """Parse ISO datetime string to UTC datetime object."""
    return datetime.fromisoformat(iso.replace("Z", "+00:00"))


def format_utc_datetime(dt: datetime) -> str:
    """Format datetime as Z-suffixed UTC string (e.g., '2026-02-28T08:00:00Z')."""
    return dt.strftime("%Y-%m-%dT%H:%M:%SZ")
