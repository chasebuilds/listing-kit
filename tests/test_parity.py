"""The in-page JavaScript checker and mortgage math must agree with the Python versions."""

import json
import shutil
import subprocess
from pathlib import Path

import pytest

from listing_kit import fairhousing
from listing_kit.mortgage import monthly_payment

ROOT = Path(__file__).resolve().parent.parent
NODE = shutil.which("node")
pytestmark = pytest.mark.skipif(NODE is None, reason="node is not installed")


def sentences():
    out = []
    for name in ("dev.txt", "heldout.txt"):
        for line in (ROOT / "benchmark" / name).read_text(encoding="utf-8").splitlines():
            if line.strip() and not line.startswith("#"):
                out.append(line.split("|", 3)[3])
    out += ["It’s a safe neighborhood – Perfect for young couples.", "", "plain text"]
    return out


def run_node(payload):
    proc = subprocess.run(
        [NODE, str(ROOT / "tests" / "parity.cjs")],
        input=json.dumps(payload), capture_output=True, text=True, encoding="utf-8", check=True,
    )
    return json.loads(proc.stdout)


def test_checker_js_matches_python_on_every_sentence():
    texts = sentences()
    rules = json.loads(fairhousing.rules_json())
    for packs in (["core"], ["core", "local"]):
        js = run_node({"op": "check", "rules": rules, "texts": texts, "packs": packs})
        for text, got in zip(texts, js, strict=True):
            want = [[f.rule_id, f.start, f.end, f.severity] for f in fairhousing.check(text, packs=tuple(packs))]
            assert got == want, (packs, text)


def test_mortgage_js_matches_python():
    cases = [
        dict(price=489000, downPct=20, ratePct=6.5, years=30, taxRatePct=0.9, insurancePerYear=1500, hoaMonthly=0),
        dict(price=725000, downPct=15, ratePct=6.25, years=30, taxRatePct=1.8, insurancePerYear=2100, hoaMonthly=85),
        dict(price=300000, downPct=0, ratePct=0, years=15, taxRatePct=0, insurancePerYear=0, hoaMonthly=0),
    ]
    js = run_node({"op": "mortgage", "cases": cases})
    for case, got in zip(cases, js, strict=True):
        want = monthly_payment(
            case["price"], case["downPct"], case["ratePct"], case["years"],
            case["taxRatePct"], case["insurancePerYear"], case["hoaMonthly"],
        )
        for key in want:
            assert got[key] == pytest.approx(want[key], rel=1e-9), key
