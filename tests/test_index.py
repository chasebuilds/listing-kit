import re
from pathlib import Path

import pytest
import yaml

from listing_kit.build import build_site, write_index
from listing_kit.cli import main
from listing_kit.config import ListingError, load_index_config

ROOT = Path(__file__).resolve().parent.parent
EX = ROOT / "examples"
THREE = [EX / "maple-court.yml", EX / "alder-street.yml", EX / "harbor-lane.yml"]


@pytest.fixture(scope="module")
def built(tmp_path_factory):
    out = tmp_path_factory.mktemp("idx")
    results = build_site(THREE, out, checker=True, index_config=load_index_config(EX / "index.yml"))
    return out, results


@pytest.fixture(scope="module")
def site(built):
    return built[0]


def cards(html: str):
    return re.findall(r'<article class="card" data-status="([^"]*)">(.*?)</article>', html, re.S)


def test_index_lists_every_listing_with_links(site):
    html = (site / "index.html").read_text(encoding="utf-8")
    found = cards(html)
    assert len(found) == 3
    for slug in ("maple-court", "alder-street", "harbor-lane"):
        assert f'href="{slug}/"' in html and f'href="{slug}/flyer.html"' in html
        assert (site / slug / "photos" / "thumb.webp").is_file()


def test_cards_show_price_status_and_facts(site):
    html = (site / "index.html").read_text(encoding="utf-8")
    by_status = {status: body for status, body in cards(html)}
    assert "$342,000" in by_status["Pending"] and "2 bed | 1 bath | 1,120 sq ft" in by_status["Pending"]
    assert "For sale" in by_status
    assert "Open house: Saturday, Dec 5" in html


def test_agent_block_and_title_come_from_the_index_config(site):
    html = (site / "index.html").read_text(encoding="utf-8")
    assert "<title>Listings by Riley Example</title>" in html
    assert 'href="mailto:riley@example.com"' in html and 'href="tel:+15550100142"' in html
    assert "Sample Realty Group" in html


def test_status_filter_exists_when_statuses_differ(site):
    html = (site / "index.html").read_text(encoding="utf-8")
    assert 'id="filters"' in html and 'data-status="Pending"' in html and "aria-pressed" in html
    assert "All (3)" in html and "Pending (1)" in html and "For sale (2)" in html


def test_no_filter_when_all_listings_share_a_status(built, tmp_path):
    write_index(built[1][:2], tmp_path, "t", {}, "file", False)
    assert 'id="filters"' not in (tmp_path / "index.html").read_text(encoding="utf-8")


def test_checker_link_on_index_only_when_built(built, tmp_path):
    assert 'href="checker/"' in (built[0] / "index.html").read_text(encoding="utf-8")
    write_index(built[1], tmp_path, "t", {}, "file", False)
    assert 'href="checker/"' not in (tmp_path / "index.html").read_text(encoding="utf-8")


def order(html: str):
    return re.findall(r'<h2><a href="([a-z-]+)/">', html)


@pytest.mark.parametrize(
    ("sort", "expected"),
    [
        ("file", ["maple-court", "alder-street", "harbor-lane"]),
        ("price-asc", ["harbor-lane", "maple-court", "alder-street"]),
        ("price-desc", ["alder-street", "maple-court", "harbor-lane"]),
        ("title", ["alder-street", "harbor-lane", "maple-court"]),
    ],
)
def test_sort_orders(built, tmp_path, sort, expected):
    write_index(built[1], tmp_path, "t", {}, sort, False)
    assert order((tmp_path / "index.html").read_text(encoding="utf-8")) == expected


def test_bad_sort_is_refused(tmp_path):
    with pytest.raises(ValueError, match="sort"):
        build_site(THREE, tmp_path, sort="newest")


def test_single_listing_has_no_index_page(tmp_path):
    build_site([THREE[0]], tmp_path)
    assert 'id="cards"' not in (tmp_path / "index.html").read_text(encoding="utf-8")


def test_index_config_validation(tmp_path):
    bad = tmp_path / "i.yml"
    bad.write_text("intro: no title here\n", encoding="utf-8")
    with pytest.raises(ListingError):
        load_index_config(bad)
    bad.write_text("title: ok\nsurprise: 1\n", encoding="utf-8")
    with pytest.raises(ListingError):
        load_index_config(bad)
    bad.write_text("title: ok\nagent: {name: A, email: nope}\n", encoding="utf-8")
    with pytest.raises(ListingError):
        load_index_config(bad)
    assert load_index_config(EX / "index.yml")["agent"]["name"] == "Riley Example"


def test_text_in_the_index_config_is_escaped(built, tmp_path):
    cfg = tmp_path / "i.yml"
    cfg.write_text(yaml.safe_dump({"title": "A <b>bold</b> move"}), encoding="utf-8")
    write_index(built[1], tmp_path, "t", load_index_config(cfg), "file", False)
    html = (tmp_path / "index.html").read_text(encoding="utf-8")
    assert "<b>bold</b>" not in html and "&lt;b&gt;" in html


def test_cli_builds_the_index_with_flags(tmp_path, capsys):
    out = tmp_path / "site"
    code = main(
        ["build", *map(str, THREE), "-o", str(out), "--index-config", str(EX / "index.yml"), "--sort", "price-desc"]
    )
    assert code == 0
    text = capsys.readouterr().out
    assert "photos: 6 files" in text and "built harbor-lane" in text
    assert order((out / "index.html").read_text(encoding="utf-8"))[0] == "alder-street"


def test_dates_in_cards_hide_when_past_script_present(site):
    html = (site / "index.html").read_text(encoding="utf-8")
    assert "data-end=" in html and "Date.now()" in html
