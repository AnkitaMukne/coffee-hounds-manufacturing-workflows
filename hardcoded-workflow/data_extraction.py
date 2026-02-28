"""
Utility functions for safely extracting and converting data from API responses.
"""

from typing import Callable, Dict, Optional, TypeVar

T = TypeVar("T")


def safe_extract(data: Dict, key: str, default: T, type_converter: Optional[Callable] = None) -> T:
    """Safely extract and optionally convert a value from a dict."""
    try:
        value = data[key]
        return type_converter(value) if type_converter else value
    except (KeyError, TypeError, ValueError):
        return default
