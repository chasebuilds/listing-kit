import copy
from pathlib import Path

import pytest
import yaml

from listing_kit import config
from listing_kit.cli import main

ROOT = Path(__file__).resolve().parent.parent
EXAMPLES = sorted(p for p in (ROOT / "examples").glob("*.yml") if p.name != "index.yml")


def base():
    return yaml.safe_load((ROOT / "examples" / "maple-court.yml").read_text(encoding="utf-8"))


@pytest.mark.parametrize("path", EXAMPLES, ids=lambda p: p.name)
def test_example_files_are_valid(path):
    listing = config.load_listing(path)
    assert listing["slug"] and listing["theme"] in {"glass", "heritage", "coastal"}


def test_there_are_two_examples_in_different_themes():
    themes = {config.load_listing(p)["theme"] for p in EXAMPLES}
    assert len(EXAMPLES) >= 2 and len(themes) >= 2


def test_starter_file_is_valid_without_photos():
    text = (ROOT / "src" / "listing_kit" / "data" / "starter.yml").read_text(encoding="utf-8")
    assert config.validate(yaml.safe_load(text)) == []


@pytest.mark.parametrize(
    "field",
    ["title", "address", "price", "beds", "baths", "sqft", "description", "photos", "agent", "location"],
)
def test_required_fields(field):
    data = base()
    del data[field]
    problems = config.validate(data)
    assert any(field in p for p in problems), problems


def mutate(fn):
    data = copy.deepcopy(base())
    fn(data)
    return config.validate(data)


def test_rejects_bad_values():
    assert mutate(lambda d: d.update(price=-5))
    assert mutate(lambda d: d.update(price="a lot"))
    assert mutate(lambda d: d.update(baths=2.3))
    assert mutate(lambda d: d.update(theme="neon"))
    assert mutate(lambda d: d.update(slug="Has Spaces"))
    assert mutate(lambda d: d["agent"].update(email="not-an-email"))
    assert mutate(lambda d: d["agent"].update(brand_color="red"))
    assert mutate(lambda d: d["location"].update(lat=91))
    assert mutate(lambda d: d.update(photos=[]))
    assert mutate(lambda d: d["photos"][0].pop("alt"))
    assert mutate(lambda d: d["open_houses"][0].update(start="Saturday at one"))
    assert mutate(lambda d: d.update(surprise=True))


def test_endpoint_mode_needs_an_https_endpoint():
    assert mutate(lambda d: d.update(lead={"mode": "endpoint"}))
    assert mutate(lambda d: d.update(lead={"mode": "endpoint", "endpoint": "http://x.test/f"}))
    assert not mutate(lambda d: d.update(lead={"mode": "endpoint", "endpoint": "https://x.test/f"}))


def test_open_house_end_must_follow_start():
    def fn(d):
        d["open_houses"] = [{"start": "2026-12-05 15:00", "end": "2026-12-05 13:00"}]

    assert any("end must be after start" in p for p in mutate(fn))


def test_unknown_timezone_is_reported():
    assert any("time zone" in p for p in mutate(lambda d: d.update(timezone="Mars/Olympus")))


def test_missing_photo_file_is_reported(tmp_path):
    data = base()
    (tmp_path / "l.yml").write_text(yaml.safe_dump(data), encoding="utf-8")
    with pytest.raises(config.ListingError) as err:
        config.load_listing(tmp_path / "l.yml")
    assert any("not found" in p for p in err.value.problems)


def test_all_problems_are_reported_together():
    data = base()
    data["price"] = -1
    data["agent"]["email"] = "x"
    assert len(config.validate(data)) >= 2


def test_defaults_are_applied():
    listing = config.load_listing(EXAMPLES[0])
    assert listing["mortgage"]["term_years"] and listing["lead"]["mode"] in {"mailto", "endpoint"}
    assert listing["timezone"]


def test_cli_validate(capsys):
    assert main(["validate", *map(str, EXAMPLES)]) == 0
    assert "ok" in capsys.readouterr().out


def test_cli_validate_reports_failure(tmp_path, capsys):
    bad = tmp_path / "bad.yml"
    bad.write_text("title: x\n", encoding="utf-8")
    assert main(["validate", str(bad)]) == 1
    assert "FAIL" in capsys.readouterr().out
