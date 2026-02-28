"""
Data extraction utilities for NovaBoard Electronics Production Scheduling Agent.

Provides helper functions for safely extracting and transforming data from dictionaries.
"""

from typing import Any, Callable, Dict, Optional, TypeVar

T = TypeVar("T")


def safe_extract(data: Dict, key: str, default: T, type_converter: Optional[Callable] = None) -> T:
    """
    Safely extract and optionally convert a value from dict.

    Args:
        data: Dictionary to extract from
        key: Key to look up
        default: Default value if key is missing
        type_converter: Optional function to convert the value (e.g., int, str)

    Returns:
        Extracted value (optionally converted) or default if key is missing
    """
    try:
        value = data[key]
        return type_converter(value) if type_converter else value
    except KeyError:
        return default


def extract_phase_durations(process_lines: list) -> Dict[str, int]:
    """
    Build phase name -> duration mapping from process_lines.

    Args:
        process_lines: List of process line dictionaries from product details

    Returns:
        Dictionary mapping phase names to their durations in minutes
    """
    durations = {}
    for line in process_lines:
        name = safe_extract(line, "name", None)
        if not name:
            continue
        duration = safe_extract(line, "duration", 60, int)
        durations[name] = duration
    return durations
