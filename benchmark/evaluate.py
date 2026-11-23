"""Score the wording checker on the labeled sentence sets and write BENCHMARK.md.

Run from the repo root:  py benchmark/evaluate.py
A sentence counts as flagged when the checker returns at least one 'avoid' or 'review' finding.
Style notes (such as for "master bedroom") are not flags.
"""

from __future__ import annotations

import sys
from collections import defaultdict
from dataclasses import dataclass
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "src"))

from listing_kit import fairhousing  # noqa: E402

SETS = {"dev": ROOT / "benchmark" / "dev.txt", "heldout": ROOT / "benchmark" / "heldout.txt"}


@dataclass
class Row:
    label: str
    group: str
    difficulty: str
    text: str
    flagged: bool
    notes: list[str]
    hits: list[str]


def load(path: Path) -> list[tuple[str, str, str, str]]:
    rows = []
    for line in path.read_text(encoding="utf-8").splitlines():
        if not line.strip() or line.startswith("#"):
            continue
        label, group, difficulty, text = line.split("|", 3)
        rows.append((label, group, difficulty, text))
    return rows


def run(path: Path) -> list[Row]:
    out = []
    for label, group, difficulty, text in load(path):
        findings = fairhousing.check(text)
        hard = fairhousing.flags(findings)
        out.append(
            Row(
                label, group, difficulty, text, bool(hard),
                [f.rule_id for f in findings if f.severity == "note"],
                sorted({f.rule_id for f in hard}),
            )
        )
    return out


def metrics(rows: list[Row]) -> dict[str, float]:
    tp = sum(1 for r in rows if r.label == "F" and r.flagged)
    fp = sum(1 for r in rows if r.label == "C" and r.flagged)
    fn = sum(1 for r in rows if r.label == "F" and not r.flagged)
    tn = sum(1 for r in rows if r.label == "C" and not r.flagged)
    precision = tp / (tp + fp) if tp + fp else float("nan")
    recall = tp / (tp + fn) if tp + fn else float("nan")
    f1 = 2 * precision * recall / (precision + recall) if tp else 0.0
    return {"n": len(rows), "tp": tp, "fp": fp, "fn": fn, "tn": tn,
            "precision": precision, "recall": recall, "f1": f1}


def pct(x: float) -> str:
    return "n/a" if x != x else f"{100 * x:.1f}%"


def table_row(name: str, m: dict[str, float]) -> str:
    return (
        f"| {name} | {int(m['n'])} | {int(m['tp'])} | {int(m['fp'])} | {int(m['fn'])} | "
        f"{int(m['tn'])} | {pct(m['precision'])} | {pct(m['recall'])} |"
    )


HEAD = "| Set | Sentences | TP | FP | FN | TN | Precision | Recall |\n|---|---|---|---|---|---|---|---|"


def report() -> str:
    results = {name: run(path) for name, path in SETS.items() if path.exists()}
    allrows = [r for rows in results.values() for r in rows]
    lines = [
        "# Benchmark",
        "",
        "Written by `benchmark/evaluate.py` from a real run. Do not edit by hand; re-run the script.",
        "",
        "What is measured: for each invented sentence, does the checker flag it (at least one `avoid` "
        "or `review` finding) when a person would say it should be flagged? Style notes such as the one for "
        "\"master bedroom\" are not flags.",
        "",
        "- **TP** flagged and should be. **FP** flagged but fine. **FN** missed. **TN** correctly left alone.",
        "- **Precision** = TP / (TP + FP). **Recall** = TP / (TP + FN).",
        "",
        "## Results",
        "",
        HEAD,
    ]
    for name, rows in results.items():
        lines.append(table_row(name, metrics(rows)))
    lines.append(table_row("**all**", metrics(allrows)))
    lines += [
        "",
        "`dev` is the set the rules were tuned on, so its numbers are optimistic. `heldout` was written after "
        "the rules were frozen and was not used to tune them. After its first run the only rule edits were "
        "relabeling the `basis` field and dropping \"sober\" from one pattern after reading the HUD memo "
        "(it treats \"sober\" as a lawful conduct rule); no number moved. The heldout row is the one to trust.",
        "",
        "## By difficulty (all sentences)",
        "",
        HEAD,
    ]
    for diff in ("std", "hard"):
        sub = [r for r in allrows if r.difficulty == diff]
        if sub:
            lines.append(table_row(diff, metrics(sub)))
    lines += ["", "`hard` marks sentences written to be tricky: paraphrases the rules cannot see and look-alikes that "
              "contain a risky word in a harmless sense.", "", "## By group (all sentences)", ""]
    lines += [
        "| Group | Sentences | Flagged | Not flagged |",
        "|---|---|---|---|",
    ]
    groups: dict[str, list[Row]] = defaultdict(list)
    for r in allrows:
        groups[r.group].append(r)
    for g, rows in groups.items():
        flagged = sum(1 for r in rows if r.flagged)
        lines.append(f"| {g} | {len(rows)} | {flagged} | {len(rows) - flagged} |")
    lines += ["", "Groups starting with a protected-class name hold sentences that should be flagged; "
              "`plain` and `tricky` hold sentences that should not.", ""]

    for title, pick in (
        ("Missed (should be flagged, was not)", lambda r: r.label == "F" and not r.flagged),
        ("False alarms (flagged, should not be)", lambda r: r.label == "C" and r.flagged),
    ):
        lines += [f"## {title}", ""]
        items = [(n, r) for n, rows in results.items() for r in rows if pick(r)]
        if not items:
            lines += ["None.", ""]
        for n, r in items:
            extra = f" (rules: {', '.join(r.hits)})" if r.hits else ""
            lines.append(f"- [{n}, {r.difficulty}] {r.text}{extra}")
        lines.append("")

    tricky = [r for r in allrows if r.label == "C" and r.group == "tricky"]
    with_note = [r for r in tricky if r.notes]
    lines += [
        "## Policy cases",
        "",
        f"{len(tricky)} clean sentences are deliberately tricky (\"family room\", \"single-family\", "
        f"\"master bedroom\", \"Church Street\", \"wheelchair accessible\", \"mom-and-pop\" and similar). "
        f"{sum(1 for r in tricky if not r.flagged)} of them are correctly left unflagged, and "
        f"{len(with_note)} carry a style note only.",
        "",
        "## Limits of this benchmark",
        "",
        "- The sentences are invented and were written by the same person who wrote the rules. "
        "Real listings are messier, so expect lower recall on real text.",
        "- The labels follow this project's documented policy (see `rules.yml`), which is a conservative "
        "reading, not a legal determination. A fair housing attorney may label some sentences differently.",
        "- Sentence counts are small, so a single sentence moves a percentage by about half a point. "
        "No confidence interval is given.",
        "",
    ]
    return "\n".join(lines)


def main() -> int:
    text = report()
    (ROOT / "BENCHMARK.md").write_text(text, encoding="utf-8", newline="")
    print(text.split("## By difficulty")[0])
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
