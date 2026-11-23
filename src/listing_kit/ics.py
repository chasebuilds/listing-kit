"""Minimal RFC 5545 calendar file writer for open house events."""

from __future__ import annotations

from datetime import UTC, datetime
from zoneinfo import ZoneInfo


def escape_text(value: str) -> str:
    """Escape TEXT values: backslash, semicolon, comma and newlines (RFC 5545 3.3.11)."""
    return (
        value.replace("\\", "\\\\")
        .replace(";", "\\;")
        .replace(",", "\\,")
        .replace("\r\n", "\\n")
        .replace("\n", "\\n")
    )


def fold(line: str) -> str:
    """Fold a content line to at most 75 octets per physical line (RFC 5545 3.1)."""
    if len(line.encode("utf-8")) <= 75:
        return line
    parts: list[str] = []
    current = ""
    limit = 75
    for ch in line:
        if len((current + ch).encode("utf-8")) > limit:
            parts.append(current)
            current = ch
            limit = 74  # continuation lines start with one space
        else:
            current += ch
    parts.append(current)
    return "\r\n ".join(parts)


def to_utc(local: str, tz: str) -> datetime:
    """Parse 'YYYY-MM-DD HH:MM' (or with T) as wall time in tz and return UTC."""
    naive = datetime.fromisoformat(local.replace(" ", "T"))
    return naive.replace(tzinfo=ZoneInfo(tz)).astimezone(UTC)


def _stamp(dt: datetime) -> str:
    return dt.astimezone(UTC).strftime("%Y%m%dT%H%M%SZ")


def make_ics(
    *,
    uid: str,
    summary: str,
    start: str,
    end: str,
    tz: str,
    location: str = "",
    description: str = "",
    url: str = "",
    dtstamp: datetime | None = None,
) -> str:
    """Build one VEVENT calendar. Times are written in UTC so no VTIMEZONE is needed."""
    stamp = dtstamp or to_utc(start, tz)
    lines = [
        "BEGIN:VCALENDAR",
        "VERSION:2.0",
        "PRODID:-//Chase Builds//listing-kit//EN",
        "CALSCALE:GREGORIAN",
        "METHOD:PUBLISH",
        "BEGIN:VEVENT",
        f"UID:{uid}",
        f"DTSTAMP:{_stamp(stamp)}",
        f"DTSTART:{_stamp(to_utc(start, tz))}",
        f"DTEND:{_stamp(to_utc(end, tz))}",
        f"SUMMARY:{escape_text(summary)}",
    ]
    if location:
        lines.append(f"LOCATION:{escape_text(location)}")
    if description:
        lines.append(f"DESCRIPTION:{escape_text(description)}")
    if url:
        lines.append(f"URL:{url}")
    lines += ["END:VEVENT", "END:VCALENDAR"]
    return "\r\n".join(fold(line) for line in lines) + "\r\n"
