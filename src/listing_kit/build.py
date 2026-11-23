"""Turn listing YAML files into static pages."""

from __future__ import annotations

import html
import json
import re
import shutil
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any
from urllib.parse import quote
from zoneinfo import ZoneInfo

from jinja2 import Environment, FileSystemLoader, select_autoescape
from PIL import Image, ImageOps

from . import fairhousing
from .config import load_listing
from .ics import make_ics, to_utc
from .mortgage import monthly_payment

PKG = Path(__file__).parent
THEME_ACCENT = {"glass": "#8a3a1c", "heritage": "#1f3a6b", "coastal": "#0b6a78"}
THEME_BG = {"glass": "#f3eadf", "heritage": "#fffdf8", "coastal": "#ffffff"}
WIDTHS = (640, 1280, 1920)

env = Environment(
    loader=FileSystemLoader(PKG / "templates"),
    autoescape=select_autoescape(["html", "j2"]),
    trim_blocks=True,
    lstrip_blocks=True,
)


@dataclass
class BuildResult:
    slug: str
    out_dir: Path
    title: str
    theme: str
    thumb: str
    price: int
    address_line: str
    warnings: list[fairhousing.Finding] = field(default_factory=list)
    status: str = ""
    beds: int = 0
    baths: str = ""
    sqft: str = ""
    next_open: dict[str, str] | None = None
    photo_stats: dict[str, int] = field(default_factory=dict)


# ---------- small helpers ----------


def _lum(hex_color: str) -> float:
    r, g, b = (int(hex_color[i : i + 2], 16) / 255 for i in (1, 3, 5))

    def lin(c: float) -> float:
        return c / 12.92 if c <= 0.03928 else ((c + 0.055) / 1.055) ** 2.4

    return 0.2126 * lin(r) + 0.7152 * lin(g) + 0.0722 * lin(b)


def contrast(a: str, b: str) -> float:
    la, lb = sorted((_lum(a), _lum(b)), reverse=True)
    return (la + 0.05) / (lb + 0.05)


def readable_link(color: str, bg: str, ratio: float = 4.5) -> str:
    """Darken color toward black until it reads on bg at the given WCAG contrast ratio."""
    r, g, b = (int(color[i : i + 2], 16) for i in (1, 3, 5))
    for _ in range(40):
        current = f"#{r:02x}{g:02x}{b:02x}"
        if contrast(current, bg) >= ratio:
            return current
        r, g, b = (int(c * 0.93) for c in (r, g, b))
    return "#000000"


def ink_for(color: str) -> str:
    return "#ffffff" if contrast(color, "#ffffff") >= contrast(color, "#000000") else "#000000"


def money(n: float) -> str:
    return f"${n:,.0f}"


def number(n: float) -> str:
    return f"{n:,.0f}"


def baths_text(n: float) -> str:
    return str(int(n)) if float(n).is_integer() else str(n)


def _clock(dt: datetime) -> str:
    return f"{dt.hour % 12 or 12}:{dt.minute:02d} {'AM' if dt.hour < 12 else 'PM'}"


def _day(dt: datetime) -> str:
    return f"{dt.strftime('%A')}, {dt.strftime('%b')} {dt.day}"


def when_text(start: str, end: str, tz: str) -> str:
    zone = ZoneInfo(tz)
    s = to_utc(start, tz).astimezone(zone)
    e = to_utc(end, tz).astimezone(zone)
    abbr = s.strftime("%Z")
    if s.date() == e.date():
        return f"{_day(s)}, {_clock(s)} to {_clock(e)} {abbr}"
    return f"{_day(s)} {_clock(s)} to {_day(e)} {_clock(e)} {abbr}"


def json_for_script(obj: Any) -> str:
    """JSON that is safe inside a <script> element."""
    return json.dumps(obj, ensure_ascii=False).replace("<", "\\u003c").replace(">", "\\u003e")


# ---------- photos ----------


def process_photos(listing: dict[str, Any], out: Path) -> tuple[list[dict[str, Any]], dict[str, int]]:
    """Resize each photo to WebP at 640, 1280 and up to 1920 pixels wide (never upscaled).

    Re-encoding drops EXIF data, including any GPS position, from what gets published.
    Returns the template data and byte counts: original files, the phone-size copies, and all copies.
    """
    base: Path = listing["_base"]
    pdir = out / "photos"
    if pdir.exists():
        shutil.rmtree(pdir)
    pdir.mkdir(parents=True)
    result = []
    stats = {"photos": 0, "original_bytes": 0, "phone_bytes": 0, "output_bytes": 0}
    for i, photo in enumerate(listing["photos"], 1):
        stats["original_bytes"] += (base / photo["file"]).stat().st_size
        stats["photos"] += 1
        with Image.open(base / photo["file"]) as raw:
            img = ImageOps.exif_transpose(raw).convert("RGB")
        variants: list[tuple[int, str, tuple[int, int]]] = []
        for width in sorted({w for w in WIDTHS if w < img.width} | {min(img.width, WIDTHS[-1])}):
            scaled = img if width >= img.width else img.resize(
                (width, round(img.height * width / img.width)), Image.Resampling.LANCZOS
            )
            name = f"p{i}-{scaled.width}.webp"
            scaled.save(pdir / name, "WEBP", quality=78, method=4)
            variants.append((scaled.width, f"photos/{name}", scaled.size))
            stats["output_bytes"] += (pdir / name).stat().st_size
        stats["phone_bytes"] += (out / variants[0][1]).stat().st_size
        small = variants[0]
        mid = ([v for v in variants if v[0] <= 1280] or variants)[-1]
        large = variants[-1]
        srcset = ", ".join(f"{path} {w}w" for w, path, _ in variants)
        result.append(
            {
                "alt": photo["alt"],
                "caption": photo.get("caption", ""),
                "w640": small[1],
                "w1280": mid[1],
                "large": large[1],
                "srcset": srcset,
                "w": mid[2][0],
                "h": mid[2][1],
            }
        )
        if i == 1:
            card = ImageOps.fit(img, (1200, 630), Image.Resampling.LANCZOS, centering=(0.5, 0.5))
            card.save(pdir / "og.jpg", "JPEG", quality=82, optimize=True, progressive=True)
            thumb = ImageOps.fit(img, (480, 320), Image.Resampling.LANCZOS)
            thumb.save(pdir / "thumb.webp", "WEBP", quality=75)
    return result, stats


# ---------- one listing ----------


def copy_assets(out_root: Path) -> None:
    dest = out_root / "assets"
    if dest.exists():
        shutil.rmtree(dest)
    shutil.copytree(PKG / "static", dest)


def build_listing(
    listing: dict[str, Any], out: Path, *, assets_rel: str = "assets/"
) -> BuildResult:
    out.mkdir(parents=True, exist_ok=True)
    tz = listing["timezone"]
    theme = listing["theme"]
    agent = listing["agent"]
    addr = listing["address"]
    address_line = f"{addr['street']}, {addr['city']}, {addr['region']} {addr['postal_code']}"
    site_url = listing.get("site_url", "").rstrip("/")
    photos, photo_stats = process_photos(listing, out)

    accent = agent.get("brand_color") or THEME_ACCENT[theme]
    link = readable_link(accent, THEME_BG[theme])

    mort = listing["mortgage"]
    est = monthly_payment(
        listing["price"], mort["down_payment_pct"], mort["rate_pct"], mort["term_years"],
        mort["tax_rate_pct"], mort["insurance_per_year"], listing.get("hoa_monthly", 0),
    )

    open_houses = []
    for n, oh in enumerate(listing["open_houses"], 1):
        s, e = to_utc(oh["start"], tz), to_utc(oh["end"], tz)
        ics_name = f"open-house-{n}.ics"
        (out / ics_name).write_text(
            make_ics(
                uid=f"{listing['slug']}-open-house-{n}@listing-kit",
                summary=f"Open house: {listing['title']}",
                start=oh["start"],
                end=oh["end"],
                tz=tz,
                location=address_line,
                description=oh.get("note", "") or f"Open house at {address_line}.",
                url=f"{site_url}/" if site_url else "",
            ),
            encoding="utf-8",
            newline="",
        )
        fmt = "%Y%m%dT%H%M%SZ"
        gcal = (
            "https://calendar.google.com/calendar/render?action=TEMPLATE"
            f"&text={quote('Open house: ' + listing['title'])}"
            f"&dates={s.strftime(fmt)}/{e.strftime(fmt)}"
            f"&location={quote(address_line)}"
        )
        open_houses.append(
            {
                "when": when_text(oh["start"], oh["end"], tz),
                "note": oh.get("note", ""),
                "ics": ics_name,
                "gcal": gcal,
                "end_iso": e.strftime("%Y-%m-%dT%H:%M:%SZ"),
            }
        )

    paragraphs = [p.strip() for p in re.split(r"\n\s*\n", listing["description"]) if p.strip()]
    description_plain = " ".join(paragraphs)
    meta_description = (
        f"{listing['beds']} bed, {baths_text(listing['baths'])} bath home, "
        f"{number(listing['sqft'])} sq ft, {money(listing['price'])}. "
        + description_plain[:140].rsplit(" ", 1)[0]
    )
    og_image = f"{site_url}/photos/og.jpg" if site_url else "photos/og.jpg"

    jsonld = {
        "@context": "https://schema.org",
        "@type": "RealEstateListing",
        "name": listing["title"],
        "description": description_plain,
        "url": site_url + "/" if site_url else None,
        "image": og_image,
        "offers": {"@type": "Offer", "price": listing["price"], "priceCurrency": "USD"},
        "about": {
            "@type": "SingleFamilyResidence",
            "numberOfBedrooms": listing["beds"],
            "numberOfBathroomsTotal": listing["baths"],
            "floorSize": {"@type": "QuantitativeValue", "value": listing["sqft"], "unitCode": "FTK"},
            "address": {
                "@type": "PostalAddress",
                "streetAddress": addr["street"],
                "addressLocality": addr["city"],
                "addressRegion": addr["region"],
                "postalCode": addr["postal_code"],
            },
            "geo": {
                "@type": "GeoCoordinates",
                "latitude": listing["location"]["lat"],
                "longitude": listing["location"]["lng"],
            },
        },
    }
    jsonld = {k: v for k, v in jsonld.items() if v is not None}

    loc = listing["location"]
    map_cfg = {
        "lat": loc["lat"],
        "lng": loc["lng"],
        "zoom": loc.get("zoom", 15),
        "approximate": loc.get("approximate", False),
    }
    lead = listing["lead"]
    mode = lead["mode"]
    page_data = {
        "title": listing["title"],
        "address": address_line,
        "assets": assets_rel,
        "accent": accent,
        "map": map_cfg,
        "photos": [{"large": p["large"], "alt": p["alt"], "caption": p["caption"]} for p in photos],
        "lead": {"mode": mode, "email": agent["email"], "endpoint": lead.get("endpoint", "")},
        "mortgage": {"hoaMonthly": listing.get("hoa_monthly", 0)},
    }
    name_parts = agent["name"].split()
    initials = (name_parts[0][0] + (name_parts[-1][0] if len(name_parts) > 1 else "")).upper()

    css = "\n".join(
        (PKG / "themes" / f"{n}.css").read_text("utf-8") for n in (theme, "base")
    )
    ctx = {
        "title": listing["title"],
        "address_line": address_line,
        "status": listing["status"],
        "notice": listing.get("notice", ""),
        "price": listing["price"],
        "price_fmt": money(listing["price"]),
        "beds": listing["beds"],
        "baths_fmt": baths_text(listing["baths"]),
        "sqft_fmt": number(listing["sqft"]),
        "ppsf_fmt": money(listing["price"] / listing["sqft"]),
        "lot_sqft": listing.get("lot_sqft"),
        "lot_fmt": number(listing["lot_sqft"]) if listing.get("lot_sqft") else "",
        "year_built": listing.get("year_built"),
        "hoa_monthly": listing.get("hoa_monthly"),
        "hoa_fmt": money(listing.get("hoa_monthly", 0)),
        "paragraphs": paragraphs,
        "features": listing["features"],
        "photos": photos,
        "open_houses": open_houses,
        "agent": agent,
        "initials": initials,
        "phone_digits": "+1" + re.sub(r"\D", "", agent.get("phone", ""))[-10:],
        "map": map_cfg,
        "lead": lead,
        "form_action": "#" if mode == "mailto" else lead["endpoint"],
        "mortgage": mort,
        "initial_total": f"{money(est['total'])} / month",
        "est": {
            "loan": money(est["loan"]),
            "pi": money(est["principal_interest"]),
            "tax": money(est["tax"]),
            "ins": money(est["insurance"]),
            "hoa": money(est["hoa"]),
        },
        "accent": accent,
        "accent_ink": ink_for(accent),
        "link": link,
        "css": css,
        "canonical": site_url + "/" if site_url else "",
        "og_image": og_image,
        "meta_description": html.unescape(meta_description),
        "jsonld": json_for_script(jsonld),
        "page_data": json_for_script(page_data),
        "assets": assets_rel,
    }
    (out / "index.html").write_text(env.get_template("listing.html.j2").render(**ctx), "utf-8")
    (out / "flyer.html").write_text(env.get_template("flyer.html.j2").render(**ctx), "utf-8")

    findings = fairhousing.flags(
        fairhousing.check(" ".join([listing["title"], listing["description"], *listing["features"]]))
    )
    return BuildResult(
        listing["slug"], out, listing["title"], theme, "photos/thumb.webp",
        listing["price"], address_line, findings,
        status=listing["status"],
        beds=listing["beds"],
        baths=baths_text(listing["baths"]),
        sqft=number(listing["sqft"]),
        next_open=(
            {"when": open_houses[0]["when"], "end": open_houses[0]["end_iso"]} if open_houses else None
        ),
        photo_stats=photo_stats,
    )


# ---------- checker page and demo index ----------


def build_checker_page(out: Path, *, assets_rel: str = "../assets/", home: str = "../") -> None:
    out.mkdir(parents=True, exist_ok=True)
    page = env.get_template("checker.html.j2").render(
        css=(PKG / "themes" / "site.css").read_text("utf-8"),
        assets=assets_rel,
        home=home,
        rules=json_for_script(json.loads(fairhousing.rules_json())),
        sample=SAMPLE_TEXT,
    )
    (out / "index.html").write_text(page, encoding="utf-8")


SAMPLE_TEXT = (
    "Charming 3 bedroom home in an exclusive neighborhood. Perfect for young couples, "
    "with a master bedroom, a big family room and no kids next door. "
    "Walking distance to church and great schools. The kitchen has a gas range, "
    "quartz counters and a walk-in pantry."
)


SORTS = ("file", "price-asc", "price-desc", "title")


def build_site(
    paths: list[Path],
    out: Path,
    *,
    checker: bool = False,
    index_title: str = "My listings",
    index_config: dict[str, Any] | None = None,
    sort: str = "file",
    check_files: bool = True,
) -> list[BuildResult]:
    """Build one page per listing. Several listings also get an index page ("my listings")."""
    if sort not in SORTS:
        raise ValueError(f"sort must be one of {', '.join(SORTS)}")
    out.mkdir(parents=True, exist_ok=True)
    listings = [load_listing(p, check_files=check_files) for p in paths]
    slugs = [x["slug"] for x in listings]
    if len(set(slugs)) != len(slugs):
        raise ValueError("two listings share a slug; set 'slug:' in the YAML")
    copy_assets(out)
    results = []
    if len(listings) == 1:
        results.append(build_listing(listings[0], out))
    else:
        for item in listings:
            results.append(build_listing(item, out / item["slug"], assets_rel="../assets/"))
        write_index(results, out, index_title, index_config or {}, sort, checker)
    if checker:
        build_checker_page(out / "checker")
    return results


def write_index(
    results: list[BuildResult], out: Path, title: str, config: dict[str, Any], sort: str, checker: bool
) -> None:
    ordered = list(results)
    if sort == "price-asc":
        ordered.sort(key=lambda r: r.price)
    elif sort == "price-desc":
        ordered.sort(key=lambda r: -r.price)
    elif sort == "title":
        ordered.sort(key=lambda r: r.title.lower())
    agent = config.get("agent")
    if agent:
        agent = {**agent, "phone_digits": "+1" + re.sub(r"\D", "", agent.get("phone", ""))[-10:]}
    counts: dict[str, int] = {}
    for r in ordered:
        counts[r.status] = counts.get(r.status, 0) + 1
    page_title = config.get("title", title)
    intro = config.get("intro", "")
    html_out = env.get_template("index.html.j2").render(
        css=(PKG / "themes" / "site.css").read_text("utf-8"),
        title=page_title,
        intro=intro,
        description=intro or f"{len(ordered)} listings, each with photos, a map, open house times and a contact form.",
        agent=agent,
        statuses=[{"name": k, "count": v} for k, v in counts.items()],
        footer="Equal Housing Opportunity. Made with listing-kit by Chase Builds.",
        items=[
            {
                "slug": r.slug, "title": r.title, "theme": r.theme, "price": money(r.price),
                "address": r.address_line, "thumb": f"{r.slug}/{r.thumb}", "status": r.status,
                "beds": r.beds, "baths": r.baths, "sqft": r.sqft, "next_open": r.next_open,
            }
            for r in ordered
        ],
        checker=checker,
    )
    (out / "index.html").write_text(html_out, "utf-8")
