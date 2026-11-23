from datetime import UTC, datetime

from listing_kit.ics import escape_text, fold, make_ics, to_utc


def make(**over):
    args = dict(
        uid="x@listing-kit", summary="Open house: Test", start="2026-12-05 13:00",
        end="2026-12-05 15:00", tz="America/New_York", location="1 Main St, Town, NC 28000",
        description="Ring the bell.",
    )
    args.update(over)
    return make_ics(**args)


def fields(text):
    out = {}
    for line in text.split("\r\n"):
        if ":" in line and not line.startswith(" "):
            k, v = line.split(":", 1)
            out.setdefault(k, v)
    return out


def test_structure_and_crlf():
    text = make()
    assert text.startswith("BEGIN:VCALENDAR\r\nVERSION:2.0\r\n")
    assert text.endswith("END:VEVENT\r\nEND:VCALENDAR\r\n")
    assert "\n" not in text.replace("\r\n", "")
    f = fields(text)
    assert f["UID"] == "x@listing-kit"
    assert f["SUMMARY"] == "Open house: Test"


def test_winter_time_converts_to_utc():
    f = fields(make())
    assert f["DTSTART"] == "20261205T180000Z"  # EST is UTC-5
    assert f["DTEND"] == "20261205T200000Z"


def test_summer_time_uses_daylight_offset():
    f = fields(make(start="2026-06-13 13:00", end="2026-06-13 15:00", tz="America/Chicago"))
    assert f["DTSTART"] == "20260613T180000Z"  # CDT is UTC-5


def test_end_after_start_and_utc_type():
    s, e = to_utc("2026-12-05 13:00", "America/New_York"), to_utc("2026-12-05 15:00", "America/New_York")
    assert e > s and s.tzinfo is UTC


def test_text_escaping():
    assert escape_text("a, b; c\\d\ne") == "a\\, b\\; c\\\\d\\ne"
    f = fields(make(location="1 Main St, Town; NC"))
    assert f["LOCATION"] == "1 Main St\\, Town\\; NC"


def test_long_lines_fold_at_75_octets_and_unfold_back():
    long = "x" * 200
    text = make(description=long)
    for physical in text.split("\r\n"):
        assert len(physical.encode("utf-8")) <= 75
    unfolded = text.replace("\r\n ", "")
    assert f"DESCRIPTION:{long}" in unfolded


def test_fold_does_not_split_multibyte_characters():
    line = "DESCRIPTION:" + "é" * 100
    folded = fold(line)
    assert all(len(p.encode("utf-8")) <= 75 for p in folded.split("\r\n"))
    assert folded.replace("\r\n ", "") == line


def test_dtstamp_override():
    stamp = datetime(2026, 1, 2, 3, 4, 5, tzinfo=UTC)
    assert fields(make(dtstamp=stamp))["DTSTAMP"] == "20260102T030405Z"


def test_url_line_only_when_given():
    assert "URL:" not in make()
    assert "URL:https://example.com/x/" in make(url="https://example.com/x/")
