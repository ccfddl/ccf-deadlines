"""CCFDDL CLI - Conference Deadline Tracker."""

__version__ = "0.2.0"
__author__ = "0x4f5da2"

from ccfddl.utils import load_mapping, get_timezone, reverse_index, format_duration, parse_datetime_with_tz
from ccfddl.models import (
    Conference,
    ConferenceYear,
    Timeline,
    Rank,
    Category,
    CATEGORIES,
    VALID_SUBS,
    get_category_by_sub,
    get_all_subs,
    is_valid_sub,
)
from ccfddl.fetch import fetch_conferences, process_conference_deadlines, filter_results, extract_alpha_id
from ccfddl.output import output_table, output_json, list_categories, format_colored_duration

__all__ = [
    "__version__",
    "__author__",
    "load_mapping",
    "get_timezone",
    "reverse_index",
    "format_duration",
    "parse_datetime_with_tz",
    "Conference",
    "ConferenceYear",
    "Timeline",
    "Rank",
    "Category",
    "CATEGORIES",
    "VALID_SUBS",
    "get_category_by_sub",
    "get_all_subs",
    "is_valid_sub",
    "fetch_conferences",
    "process_conference_deadlines",
    "filter_results",
    "extract_alpha_id",
    "output_table",
    "output_json",
    "list_categories",
    "format_colored_duration",
]
