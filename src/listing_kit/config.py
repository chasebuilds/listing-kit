"""Load and validate a listing YAML file."""

from __future__ import annotations

import json
import re
from importlib import resources
from pathlib import Path
from typing import Any
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

import yaml
from jsonschema import Draft202012Validator

DEFAULTS: dict[str, Any] = {
    "theme": "glass",
    "status": "For sale",
    "timezone": "America/New_York",
    "features": [],
    "open_houses": [],
    "lead": {"mode": "mailto"},
    "mortgage": {
        "down_payment_pct": 20,
        "rate_pct": 6.5,
        "term_years": 30,
        "tax_rate_pct": 1.1,
        "insurance_per_year": 1400,
    },
}


class ListingError(ValueError):
    """Raised with every problem found in a listing file, one per line."""

    def __init__(self, problems: list[str]):
        self.problems = problems
        super().__init__("\n".join(problems))


def schema() -> dict[str, Any]:
    text = resources.files("listing_kit").joinpath("data/listing.schema.json").read_text("utf-8")
    return json.loads(text)


def slugify(text: str) -> str:
    return re.sub(r"[^a-z0-9]+", "-", text.lower()).strip("-") or "listing"


def schema_problems(data: Any) -> list[str]:
    validator = Draft202012Validator(schema())
    out = []
    for err in sorted(validator.iter_errors(data), key=lambda e: list(e.absolute_path)):
        where = ".".join(str(p) for p in err.absolute_path) or "(top level)"
        out.append(f"{where}: {err.message}")
    return out


def semantic_problems(data: dict[str, Any], base: Path | None) -> list[str]:
    problems = []
    tz = data.get("timezone", DEFAULTS["timezone"])
    try:
        ZoneInfo(tz)
    except (ZoneInfoNotFoundError, ValueError):
        problems.append(f"timezone: unknown time zone '{tz}'")
    else:
        from .ics import to_utc

        for i, oh in enumerate(data.get("open_houses", [])):
            try:
                if to_utc(oh["end"], tz) <= to_utc(oh["start"], tz):
                    problems.append(f"open_houses.{i}: end must be after start")
            except ValueError as exc:
                problems.append(f"open_houses.{i}: {exc}")
    if base is not None:
        for i, photo in enumerate(data.get("photos", [])):
            if not (base / photo["file"]).is_file():
                problems.append(f"photos.{i}.file: '{photo['file']}' not found next to the YAML file")
    return problems


def finish(data: dict[str, Any]) -> dict[str, Any]:
    """Apply defaults and derive the slug."""
    out = {**DEFAULTS, **data}
    out["mortgage"] = {**DEFAULTS["mortgage"], **data.get("mortgage", {})}
    out["lead"] = {**DEFAULTS["lead"], **data.get("lead", {})}
    out.setdefault("slug", slugify(out["title"]))
    return out


def validate(data: Any, base: Path | None = None) -> list[str]:
    problems = schema_problems(data)
    if not problems and isinstance(data, dict):
        problems += semantic_problems(data, base)
    return problems


def load_listing(path: str | Path, *, check_files: bool = True) -> dict[str, Any]:
    path = Path(path)
    data = yaml.safe_load(path.read_text(encoding="utf-8"))
    problems = validate(data, path.parent if check_files else None)
    if problems:
        raise ListingError(problems)
    listing = finish(data)
    listing["_base"] = path.parent
    return listing


INDEX_SCHEMA: dict[str, Any] = {
    "type": "object",
    "required": ["title"],
    "additionalProperties": False,
    "properties": {
        "title": {"type": "string", "minLength": 1, "maxLength": 120},
        "intro": {"type": "string", "maxLength": 600},
        "agent": {
            "type": "object",
            "required": ["name"],
            "additionalProperties": False,
            "properties": {
                "name": {"type": "string", "minLength": 1},
                "brokerage": {"type": "string"},
                "phone": {"type": "string"},
                "email": {"type": "string", "pattern": "^[^@\\s]+@[^@\\s]+\\.[^@\\s]+$"},
            },
        },
    },
}


def load_index_config(path: str | Path) -> dict[str, Any]:
    """Load the optional 'my listings' page settings: title, intro and the agent block."""
    data = yaml.safe_load(Path(path).read_text(encoding="utf-8"))
    validator = Draft202012Validator(INDEX_SCHEMA)
    problems = [
        f"{'.'.join(str(p) for p in e.absolute_path) or '(top level)'}: {e.message}"
        for e in sorted(validator.iter_errors(data), key=lambda e: list(e.absolute_path))
    ]
    if problems:
        raise ListingError(problems)
    return data
