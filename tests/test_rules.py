import json

import pytest

from listing_kit import fairhousing
from listing_kit.cli import main

CATEGORIES = {
    "race_color", "religion", "sex", "disability", "familial_status",
    "national_origin", "steering", "local_law",
}
SEVERITIES = {"avoid", "review", "note"}
BASES = {"statute", "hud-1995-memo", "hud-part-109", "judgment"}

# One sentence per rule that must trigger it. Adding a rule without an entry here fails the test below.
EXAMPLES = {
    "no-children": "No kids allowed.",
    "child-free": "A child-free building.",
    "adults-only": "Adults only community.",
    "no-families": "No single parents.",
    "age-restricted": "A 55+ community with a pool.",
    "perfect-for-people": "Perfect for young couples.",
    "people-adjective": "Retired buyers will like it.",
    "family-targeting": "Room for a growing family.",
    "family-friendly": "A family-friendly street.",
    "raise-a-family": "A great place to raise a family.",
    "no-disabled": "Not suitable for wheelchair users.",
    "able-bodied": "Able-bodied tenants only.",
    "must-be-able": "Must be able to climb stairs.",
    "no-assistance-animals": "No service animals.",
    "no-pets": "No pets.",
    "handicap-term": "Handicap accessible bathroom.",
    "religion-occupant": "A Christian home.",
    "no-religion": "No Muslims.",
    "worship-proximity": "Walking distance to church.",
    "god-fearing": "God-fearing neighbors.",
    "race-occupant": "White tenants preferred.",
    "no-group": "No foreigners.",
    "language-citizenship": "English speaking tenants only.",
    "ethnic-term": "An ethnic area.",
    "demographic-area": "An integrated neighborhood.",
    "bad-area": "A rough part of town.",
    "subjective-area": "A safe neighborhood.",
    "exclusive-area": "An exclusive neighborhood.",
    "restricted-area": "A restricted community.",
    "traditional-area": "A traditional neighborhood.",
    "right-kind-of-people": "The right kind of people live here.",
    "quality-people": "Nice neighbors all around.",
    "class-people": "A working class neighborhood.",
    "upscale-area": "An upscale neighborhood.",
    "school-quality": "Great schools nearby.",
    "sex-occupant": "Female roommate wanted.",
    "no-lgbt": "No gays or lesbians.",
    "bachelor-pad": "A bachelor pad downtown.",
    "man-cave": "A man cave in the basement.",
    "spouse-targeting": "Your wife will love the kitchen.",
    "his-and-hers": "His and hers closets.",
    "master-bedroom": "The master bedroom has a view.",
    "in-law-suite": "A mother-in-law suite.",
    "maids-quarters": "Maid's quarters off the kitchen.",
    "source-of-income": "No Section 8.",
    "income-source-job": "Income must come from a job.",
    "all-race-area": "An all white street.",
    "who-will-love": "Singles and couples will feel at home.",
    "active-people": "Ideal for active people.",
    "fit-in": "The kind of area where you will fit in.",
}


def test_every_rule_has_a_valid_shape():
    rules = fairhousing.load_rules()
    ids = [r["id"] for r in rules]
    assert len(ids) == len(set(ids))
    for r in rules:
        assert r["category"] in CATEGORIES, r["id"]
        assert r["severity"] in SEVERITIES, r["id"]
        assert r["basis"] in BASES, r["id"]
        assert r["reason"].strip() and r["suggest"].strip(), r["id"]
        assert chr(0x2014) not in r["reason"] + r["suggest"], r["id"]


def test_every_rule_has_an_example_and_the_example_triggers_it():
    rules = fairhousing.load_rules()
    assert {r["id"] for r in rules} == set(EXAMPLES)
    for rule_id, sentence in EXAMPLES.items():
        hit = {f.rule_id for f in fairhousing.check(sentence, packs=("core", "local"))}
        assert rule_id in hit, f"{rule_id} did not fire on: {sentence}"


@pytest.mark.parametrize(
    "text",
    [
        "The family room has a gas fireplace.",
        "A single-family home on a corner lot.",
        "A multi-family building with four units.",
        "Large family-size kitchen.",
        "A big family room with a bar.",
        "Wheelchair accessible entrance and a roll-in shower.",
        "No stairs and step-free entry.",
        "On Church Street, two blocks from the square.",
        "Near Temple University.",
        "Mom-and-pop shops line the street.",
        "The exclusive listing agent will show it.",
        "Mature oak trees shade the yard.",
        "Zoned for Lincoln Elementary.",
        "Walking distance to the park and the library.",
        "Italian marble and Mexican tile.",
        "Black granite counters and white oak floors.",
        "Near Indian Hills Park.",
    ],
)
def test_clean_policy_cases_are_not_flagged(text):
    assert fairhousing.flags(fairhousing.check(text)) == []


def test_master_bedroom_is_a_note_not_a_flag():
    found = fairhousing.check("The master bedroom has a walk-in closet.")
    assert [f.severity for f in found] == ["note"]
    assert fairhousing.flags(found) == []


def test_hits_point_at_the_right_text_even_with_curly_quotes():
    text = "It’s lovely. Perfect for young couples – really."
    found = fairhousing.check(text)
    hit = next(f for f in found if f.rule_id == "perfect-for-people")
    assert text[hit.start : hit.end] == "Perfect for young couples"
    assert hit.match == "Perfect for young couples"


def test_unless_window_removes_a_hit():
    assert fairhousing.flags(fairhousing.check("Close to the church and the park.")) != []
    assert fairhousing.flags(fairhousing.check("Close to Church Street and the park.")) == []


@pytest.mark.parametrize(
    "text",
    [
        "An all white street with great curb appeal.",
        "We cannot accommodate the handicapped.",
        "Applicants must be born in this country.",
        "Not far from the bad side of town.",
        "Singles and couples will feel at home in the lofts.",
        "Mentally sound tenants only.",
        "Homosexuals need not apply.",
    ],
)
def test_documented_misses_from_version_1_0_are_now_caught(text):
    assert fairhousing.flags(fairhousing.check(text))


@pytest.mark.parametrize(
    "text",
    [
        "The kitchen is all white with black hardware.",
        "All-white cabinets and a white quartz island.",
        "A husband and wife team of contractors did the remodel.",
        "The seller's mother kept the garden.",
        "See the neighborhood map in the packet for nearby churches.",
        "Sober living rules apply: no alcohol on the property.",
    ],
)
def test_new_rules_do_not_flag_look_alikes(text):
    assert fairhousing.flags(fairhousing.check(text)) == []


def test_local_pack_is_off_by_default_and_opt_in():
    text = "No Section 8 and income must come from a job."
    assert fairhousing.check(text) == []
    found = fairhousing.check(text, packs=("core", "local"))
    assert {f.rule_id for f in found} == {"source-of-income", "income-source-job"}


def test_local_pack_rules_are_marked_not_federal():
    local = [r for r in fairhousing.load_rules() if r.get("pack") == "local"]
    assert local and all(r["category"] == "local_law" for r in local)
    assert all("not federal" in r["reason"] for r in local)
    assert all(r.get("pack", "core") == "core" for r in fairhousing.load_rules() if r["category"] != "local_law")


def test_matching_is_case_insensitive():
    assert fairhousing.flags(fairhousing.check("NO KIDS"))


def test_custom_rules_file(tmp_path):
    rules = tmp_path / "r.yml"
    rules.write_text(
        "rules:\n  - id: x\n    category: sex\n    severity: avoid\n    basis: judgment\n"
        "    pattern: 'zebra'\n    reason: r\n    suggest: s\n",
        encoding="utf-8",
    )
    found = fairhousing.check("a zebra", fairhousing.load_rules(rules))
    assert [f.rule_id for f in found] == ["x"]


def test_rules_json_round_trips():
    data = json.loads(fairhousing.rules_json())
    assert data["window"] == fairhousing.WINDOW
    assert len(data["rules"]) == len(fairhousing.load_rules())


def test_cli_exit_codes(capsys):
    assert main(["check", "Perfect for young couples."]) == 1
    assert main(["check", "Perfect for young couples.", "--no-fail"]) == 0
    assert main(["check", "Three bedrooms and a deck."]) == 0
    assert main(["check", "No Section 8."]) == 0
    assert main(["check", "No Section 8.", "--pack", "local"]) == 1
    capsys.readouterr()
    assert main(["check", "No kids.", "--json", "--no-fail"]) == 0
    out = json.loads(capsys.readouterr().out)
    assert out[0]["rule_id"] == "no-children"
