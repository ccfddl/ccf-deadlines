"""Derive a conference's opening date without inventing unpublished days."""

import re
from datetime import date


MONTHS = {
    name: number
    for number, names in enumerate((
        ("jan", "january"), ("feb", "february"), ("mar", "march"),
        ("apr", "april"), ("may",), ("jun", "june"), ("jul", "july"),
        ("aug", "august"), ("sep", "sept", "september"),
        ("oct", "october"), ("nov", "november"), ("dec", "december"),
    ), start=1)
    for name in names
}


def conference_opening(edition: dict) -> str | None:
    """Return the earliest announced first day at 08:00 in the edition timezone."""
    raw = str(edition.get("date") or "").strip()
    years = re.findall(r"\b(\d{4})\b", raw)
    fallback_year = int(years[-1]) if years else edition.get("year")
    if not isinstance(fallback_year, int):
        return None
    days = []
    # Multiple sessions/locations can be listed out of order. Range endpoints
    # aren't separate openings; consider only the start of each session.
    for session in re.split(r"\band\b|(?<=\)),\s*", raw, flags=re.IGNORECASE):
        session = session.strip()
        iso = re.match(r"^(\d{4})-(\d{2})-(\d{2})\b", session)
        if iso:
            year, month, day = map(int, iso.groups())
        else:
            match = re.match(r"^([A-Za-z]+)\.?\s+(\d{1,2})\b", session)
            if match:
                month_name, day = match.groups()
            else:
                match = re.match(r"^(\d{1,2})\s+([A-Za-z]+)\.?\b", session)
                if not match:
                    continue
                day, month_name = match.groups()
            month = MONTHS.get(month_name.lower())
            if month is None:
                continue
            session_years = re.findall(r"\b(\d{4})\b", session)
            year = int(session_years[0]) if session_years else fallback_year
            day = int(day)
        try:
            days.append(date(year, month, day))
        except ValueError:
            continue
    return f"{min(days).isoformat()} 08:00:00" if days else None


def with_conference_openings(conferences: list) -> list:
    return [{**conference, "confs": [
        {**edition, "opening": conference_opening(edition)}
        for edition in conference["confs"]
    ]} for conference in conferences]
