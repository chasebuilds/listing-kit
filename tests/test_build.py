import json
import re
from html.parser import HTMLParser
from pathlib import Path

import pytest
import yaml

from listing_kit import fairhousing
from listing_kit.build import build_site, contrast, readable_link
from listing_kit.mortgage import monthly_payment

ROOT = Path(__file__).resolve().parent.parent
MAPLE = ROOT / "examples" / "maple-court.yml"
ALDER = ROOT / "examples" / "alder-street.yml"


@pytest.fixture(scope="module")
def site(tmp_path_factory):
    out = tmp_path_factory.mktemp("site")
    build_site([MAPLE, ALDER], out, checker=True)
    return out


class Tags(HTMLParser):
    def __init__(self):
        super().__init__()
        self.tags = []

    def handle_starttag(self, tag, attrs):
        self.tags.append((tag, dict(attrs)))


def tags(path: Path):
    p = Tags()
    p.feed(path.read_text(encoding="utf-8"))
    return p.tags


def test_expected_files(site):
    for slug in ("maple-court", "alder-street"):
        for name in ("index.html", "flyer.html", "open-house-1.ics", "photos/og.jpg", "photos/thumb.webp"):
            assert (site / slug / name).is_file(), f"{slug}/{name}"
    assert (site / "index.html").is_file()
    assert (site / "checker" / "index.html").is_file()
    for asset in ("listing.js", "mortgage.js", "checker.js", "leaflet/leaflet.js", "leaflet/leaflet.css"):
        assert (site / "assets" / asset).is_file()


def test_two_listings_use_two_themes(site):
    a = (site / "maple-court" / "index.html").read_text(encoding="utf-8")
    b = (site / "alder-street" / "index.html").read_text(encoding="utf-8")
    assert "Georgia" in b and "Georgia" not in a


def test_page_basics_for_accessibility(site):
    page = site / "maple-court" / "index.html"
    tg = tags(page)
    html = next(a for t, a in tg if t == "html")
    assert html.get("lang") == "en"
    assert any(t == "meta" and a.get("name") == "viewport" for t, a in tg)
    assert [a for t, a in tg if t == "main"]
    assert sum(1 for t, _ in tg if t == "h1") == 1
    imgs = [a for t, a in tg if t == "img" and a.get("id") != "lb-img"]  # lightbox alt is set when opened
    assert imgs and all(a.get("alt") for a in imgs)
    assert all(a.get("width") and a.get("height") for a in imgs)
    for t, a in tg:
        if t == "input" and a.get("type") != "hidden":
            assert a.get("id"), a
    ids = {a["id"] for t, a in tg if "id" in a}
    labels = {a["for"] for t, a in tg if t == "label" and "for" in a}
    assert labels <= ids
    assert any(t == "a" and a.get("class") == "skip" for t, a in tg)


def test_open_graph_and_meta(site):
    tg = tags(site / "maple-court" / "index.html")
    og = {a["property"]: a["content"] for t, a in tg if t == "meta" and "property" in a}
    for key in ("og:title", "og:description", "og:image", "og:type"):
        assert og.get(key), key
    assert "Maple Court Craftsman" in og["og:title"] and "$489,000" in og["og:title"]
    assert any(t == "meta" and a.get("name") == "description" for t, a in tg)
    assert any(t == "meta" and a.get("name") == "twitter:card" for t, a in tg)


def test_og_image_is_absolute_when_site_url_is_set(tmp_path):
    data = yaml.safe_load(MAPLE.read_text(encoding="utf-8"))
    data["site_url"] = "https://example.com/homes/maple"
    data["photos"] = [{**p, "file": str(ROOT / "examples" / p["file"])} for p in data["photos"]]
    src = tmp_path / "l.yml"
    src.write_text(yaml.safe_dump(data), encoding="utf-8")
    build_site([src], tmp_path / "out")
    html = (tmp_path / "out" / "index.html").read_text(encoding="utf-8")
    assert 'content="https://example.com/homes/maple/photos/og.jpg"' in html
    assert 'rel="canonical" href="https://example.com/homes/maple/"' in html


def test_jsonld_is_valid_json(site):
    html = (site / "maple-court" / "index.html").read_text(encoding="utf-8")
    raw = re.search(r'<script type="application/ld\+json">(.*?)</script>', html, re.S).group(1)
    ld = json.loads(raw)
    assert ld["@type"] == "RealEstateListing" and ld["offers"]["price"] == 489000


def test_page_data_json_is_valid_and_safe(site):
    html = (site / "maple-court" / "index.html").read_text(encoding="utf-8")
    raw = re.search(r'id="listing-data">(.*?)</script>', html, re.S).group(1)
    data = json.loads(raw)
    assert data["map"]["approximate"] is True and len(data["photos"]) == 6
    assert data["lead"]["mode"] == "mailto"


def test_script_breakout_is_escaped(tmp_path):
    data = yaml.safe_load(MAPLE.read_text(encoding="utf-8"))
    data["title"] = "Bad </script><script>alert(1)</script> title"
    data["photos"] = [{**p, "file": str(ROOT / "examples" / p["file"])} for p in data["photos"]]
    src = tmp_path / "l.yml"
    src.write_text(yaml.safe_dump(data), encoding="utf-8")
    build_site([src], tmp_path / "out")
    html = (tmp_path / "out" / "index.html").read_text(encoding="utf-8")
    assert "<script>alert(1)</script>" not in html


def test_open_house_links_and_ics_files(site):
    html = (site / "maple-court" / "index.html").read_text(encoding="utf-8")
    assert 'href="open-house-1.ics"' in html and 'href="open-house-2.ics"' in html
    assert "Saturday, Dec 5, 1:00 PM to 3:00 PM EST" in html
    ics = (site / "maple-court" / "open-house-1.ics").read_text(encoding="utf-8")
    assert "DTSTART:20261205T180000Z" in ics
    alder = (site / "alder-street" / "index.html").read_text(encoding="utf-8")
    assert "11:00 AM to 1:00 PM CST" in alder


def test_mortgage_widget_inputs_and_estimate_label(site):
    html = (site / "maple-court" / "index.html").read_text(encoding="utf-8")
    for field in ("m-price", "m-down", "m-rate", "m-years", "m-tax", "m-ins"):
        assert f'id="{field}"' in html
    assert "estimate only" in html.lower()
    est = monthly_payment(489000, 20, 6.5, 30, 0.9, 1500)
    assert f"${est['total']:,.0f} / month" in html


def test_lead_form_works_without_a_backend(site):
    html = (site / "maple-court" / "index.html").read_text(encoding="utf-8")
    assert "action=\"mailto:" not in html  # a mailto form action is flagged as insecure by Lighthouse
    assert "<noscript>" in html and "mailto:riley@example.com" in html


def test_endpoint_lead_form(tmp_path):
    data = yaml.safe_load(MAPLE.read_text(encoding="utf-8"))
    data["lead"] = {"mode": "endpoint", "endpoint": "https://forms.example.com/f/abc"}
    data["photos"] = [{**p, "file": str(ROOT / "examples" / p["file"])} for p in data["photos"]]
    src = tmp_path / "l.yml"
    src.write_text(yaml.safe_dump(data), encoding="utf-8")
    build_site([src], tmp_path / "out")
    html = (tmp_path / "out" / "index.html").read_text(encoding="utf-8")
    assert 'action="https://forms.example.com/f/abc"' in html and 'method="post"' in html


def test_map_and_attribution(site):
    html = (site / "maple-court" / "index.html").read_text(encoding="utf-8")
    assert 'id="map"' in html and "OpenStreetMap contributors" in html
    js = (site / "assets" / "listing.js").read_text(encoding="utf-8")
    assert "tile.openstreetmap.org" in js and "openstreetmap.org/copyright" in js


def test_single_listing_builds_at_the_root(tmp_path):
    build_site([MAPLE], tmp_path)
    assert (tmp_path / "index.html").is_file() and (tmp_path / "assets" / "listing.js").is_file()
    html = (tmp_path / "index.html").read_text(encoding="utf-8")
    assert 'src="assets/listing.js"' in html


def test_flyer_is_printable(site):
    html = (site / "maple-court" / "flyer.html").read_text(encoding="utf-8")
    assert "@page" in html and "@media print" in html and "Print this flyer" in html


def test_responsive_photos_are_smaller_than_the_original(site):
    photos = site / "maple-court" / "photos"
    assert (photos / "p1-640.webp").stat().st_size < (photos / "p1-1280.webp").stat().st_size


def test_links_stay_readable_on_every_theme():
    for color, bg in (("#b4552d", "#f3eadf"), ("#ffcc00", "#ffffff"), ("#1f3a6b", "#fffdf8")):
        assert contrast(readable_link(color, bg), bg) >= 4.5


def test_no_em_dash_in_built_output(site):
    for path in site.rglob("*"):
        if path.suffix in {".html", ".js", ".ics", ".css"} and "leaflet" not in path.parts:
            assert chr(0x2014) not in path.read_text(encoding="utf-8"), path


def test_sample_listings_pass_their_own_wording_check():
    for path in (MAPLE, ALDER):
        data = yaml.safe_load(path.read_text(encoding="utf-8"))
        text = " ".join([data["title"], data["description"], *data["features"]])
        assert fairhousing.flags(fairhousing.check(text)) == [], path.name


def test_duplicate_slugs_are_refused(tmp_path):
    with pytest.raises(ValueError, match="slug"):
        build_site([MAPLE, MAPLE], tmp_path)
