"""Fair-housing wording checker. A writing aid, not legal advice."""

from __future__ import annotations

import json
import re
from dataclasses import asdict, dataclass
from functools import lru_cache
from importlib import resources
from pathlib import Path
from typing import Any

import yaml

WINDOW = 40
FLAG_SEVERITIES = ("avoid", "review")
# Curly quotes and en/em dashes become ASCII, one character for one character.
_FOLD = {0x2019: "'", 0x2018: "'", 0x201C: '"', 0x201D: '"', 0x2013: "-", 0x2014: "-"}


@dataclass(frozen=True)
class Finding:
    rule_id: str
    category: str
    severity: str
    start: int
    end: int
    match: str
    reason: str
    suggest: str
    basis: str

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def normalize(text: str) -> str:
    """Fold curly quotes and dashes one-to-one so match offsets stay valid in the original text."""
    return text.translate(_FOLD)  # str.translate accepts a dict keyed by code point


@lru_cache(maxsize=1)
def default_rules() -> tuple[dict[str, Any], ...]:
    text = resources.files("listing_kit").joinpath("data/rules.yml").read_text("utf-8")
    return tuple(load_rules_text(text))


def load_rules_text(text: str) -> list[dict[str, Any]]:
    data = yaml.safe_load(text)
    rules = data["rules"]
    seen = set()
    for rule in rules:
        if rule["id"] in seen:
            raise ValueError(f"duplicate rule id {rule['id']}")
        seen.add(rule["id"])
        re.compile(rule["pattern"], re.IGNORECASE)
    return rules


def load_rules(path: str | Path | None = None) -> list[dict[str, Any]]:
    if path is None:
        return list(default_rules())
    return load_rules_text(Path(path).read_text(encoding="utf-8"))


def rules_json(rules: list[dict[str, Any]] | None = None) -> str:
    """The same rules as JSON for the in-page checker."""
    keep = ("id", "category", "severity", "basis", "pattern", "unless", "reason", "suggest")
    rules = rules if rules is not None else list(default_rules())
    return json.dumps(
        {"window": WINDOW, "rules": [{k: r[k] for k in keep if k in r} for r in rules]},
        indent=1,
    )


def check(text: str, rules: list[dict[str, Any]] | None = None) -> list[Finding]:
    rules = rules if rules is not None else list(default_rules())
    folded = normalize(text)
    found: list[Finding] = []
    for rule in rules:
        pattern = re.compile(rule["pattern"], re.IGNORECASE)
        unless = [re.compile(u, re.IGNORECASE) for u in rule.get("unless", [])]
        for m in pattern.finditer(folded):
            if m.end() == m.start():
                continue
            lo, hi = max(0, m.start() - WINDOW), min(len(folded), m.end() + WINDOW)
            if any(u.search(folded[lo:hi]) for u in unless):
                continue
            found.append(
                Finding(
                    rule["id"],
                    rule["category"],
                    rule["severity"],
                    m.start(),
                    m.end(),
                    text[m.start() : m.end()],
                    rule["reason"],
                    rule["suggest"],
                    rule.get("basis", "judgment"),
                )
            )
    return sorted(found, key=lambda f: (f.start, f.rule_id))


def flags(findings: list[Finding]) -> list[Finding]:
    """Findings that count as a flag (avoid or review). Notes are style advice only."""
    return [f for f in findings if f.severity in FLAG_SEVERITIES]
