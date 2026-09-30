"""Natural language date extraction and normalization using dateparser."""

import re
from datetime import datetime, timedelta
from typing import Optional, Tuple
import dateparser


class DateExtractor:
    """Extracts and normalizes natural language deadlines relative to meeting date."""

    # Targeted patterns for natural language dates
    DATE_PATTERNS = [
        re.compile(r"\bby\s+(tomorrow(?:\s+afternoon|\s+morning|\s+evening)?)\b", re.IGNORECASE),
        re.compile(r"\bby\s+(today(?:\s+afternoon|\s+morning|\s+evening|(?:\s+before\s+\d+\s*(?:am|pm)?))?)\b", re.IGNORECASE),
        re.compile(r"\b(?:by|before|on)\s+(next\s+(?:monday|tuesday|wednesday|thursday|friday|saturday|sunday))\b", re.IGNORECASE),
        re.compile(r"\b(?:by|before|on)\s+((?:this\s+)?(?:monday|tuesday|wednesday|thursday|friday|saturday|sunday))\b", re.IGNORECASE),
        re.compile(r"\b(?:by|before)\s+(the\s+end\s+of\s+(?:next\s+)?week)\b", re.IGNORECASE),
        re.compile(r"\b(?:by|before)\s+(the\s+end\s+of\s+(?:the\s+)?month)\b", re.IGNORECASE),
        re.compile(r"\b(?:within|in)\s+(\d+\s+(?:days?|weeks?|months?))\b", re.IGNORECASE),
        re.compile(r"\bby\s+((?:january|february|march|april|may|june|july|august|september|october|november|december)\s+\d{1,2}(?:st|nd|rd|th)?)\b", re.IGNORECASE),
        re.compile(r"\b(tomorrow|today)\b", re.IGNORECASE),
        re.compile(r"\b(friday|monday|tuesday|wednesday|thursday|saturday|sunday)\b", re.IGNORECASE),
    ]

    def extract_due_date(self, text: str, reference_date: Optional[datetime] = None) -> Tuple[str, str]:
        """
        Extract date string and normalized YYYY-MM-DD.
        Returns:
            Tuple of (display_text, normalized_date_iso)
            Defaults to ("Unknown", "Unknown") if no deadline is present.
        """
        if not reference_date:
            # Default to reference meeting date (2026-09-23)
            reference_date = datetime(2026, 9, 23, 10, 0, 0)

        date_settings = {
            "RELATIVE_BASE": reference_date,
            "PREFER_DATES_FROM": "future",
            "RETURN_AS_TIMEZONE_AWARE": False
        }

        # Check explicit patterns
        for pattern in self.DATE_PATTERNS:
            match = pattern.search(text)
            if match:
                raw_match = match.group(1) if match.lastindex else match.group(0)
                cleaned_match = raw_match.strip()
                
                # Special cases for idiomatic business deadlines
                if "end of next week" in cleaned_match.lower():
                    # Friday of next week
                    days_ahead = (4 - reference_date.weekday() + 7) % 7 + 7
                    target_dt = reference_date + timedelta(days=days_ahead)
                    return cleaned_match, target_dt.strftime("%Y-%m-%d")

                if "end of the month" in cleaned_match.lower() or "end of month" in cleaned_match.lower():
                    # Next month start minus 1 day
                    next_month = reference_date.replace(day=28) + timedelta(days=4)
                    target_dt = next_month - timedelta(days=next_month.day)
                    return cleaned_match, target_dt.strftime("%Y-%m-%d")

                # Parse with dateparser
                parsed_dt = dateparser.parse(cleaned_match, settings=date_settings)
                if parsed_dt:
                    # If parsed date is earlier than reference date for days of the week, push forward 1 week
                    if parsed_dt.date() < reference_date.date():
                        parsed_dt = parsed_dt + timedelta(days=7)
                    return cleaned_match, parsed_dt.strftime("%Y-%m-%d")

        return "Unknown", "Unknown"
