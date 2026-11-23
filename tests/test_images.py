import re
from pathlib import Path

import pytest
import yaml
from PIL import Image

from listing_kit.build import WIDTHS, build_site

ROOT = Path(__file__).resolve().parent.parent
MAPLE = ROOT / "examples" / "maple-court.yml"


def make_photo(path: Path, width: int, height: int, gps: bool = False) -> Path:
    img = Image.effect_noise((width, height), 40).convert("RGB")
    if gps:
        exif = Image.Exif()
        exif[0x8825] = {1: "N", 2: (35.0, 35.0, 0.0), 3: "W", 4: (82.0, 33.0, 0.0)}  # GPSInfo
        exif[0x010F] = "TestCam"
        img.save(path, "JPEG", exif=exif)
    else:
        img.save(path, "JPEG")
    return path


def build_with_photos(tmp_path: Path, sizes: list[tuple[int, int]], gps: bool = False):
    data = yaml.safe_load(MAPLE.read_text(encoding="utf-8"))
    photos = []
    for i, (w, h) in enumerate(sizes, 1):
        p = make_photo(tmp_path / f"src{i}.jpg", w, h, gps)
        photos.append({"file": str(p), "alt": f"Test photo {i}"})
    data["photos"] = photos
    src = tmp_path / "listing.yml"
    src.write_text(yaml.safe_dump(data), encoding="utf-8")
    out = tmp_path / "out"
    results = build_site([src], out)
    return out, results[0]


def img_tags(html: str):
    return [dict(re.findall(r'([\w-]+)="([^"]*)"', m)) for m in re.findall(r"<img [^>]*>", html)]


def test_big_photo_gets_three_sizes_and_is_not_upscaled(tmp_path):
    out, _ = build_with_photos(tmp_path, [(3000, 400)])
    names = {p.name for p in (out / "photos").glob("p1-*.webp")}
    assert names == {f"p1-{w}.webp" for w in WIDTHS}
    widths = {w: Image.open(out / "photos" / f"p1-{w}.webp").width for w in WIDTHS}
    assert widths == {w: w for w in WIDTHS}


def test_small_photo_is_never_upscaled(tmp_path):
    out, _ = build_with_photos(tmp_path, [(500, 333)])
    files = list((out / "photos").glob("p1-*.webp"))
    assert [f.name for f in files] == ["p1-500.webp"]
    assert Image.open(files[0]).width == 500


def test_mid_size_photo_gets_its_own_width_as_the_top_size(tmp_path):
    out, _ = build_with_photos(tmp_path, [(1600, 300)])
    assert sorted(p.name for p in (out / "photos").glob("p1-*.webp")) == ["p1-1280.webp", "p1-1600.webp", "p1-640.webp"]


def test_srcset_lists_widths_in_order_and_matches_the_files(tmp_path):
    out, _ = build_with_photos(tmp_path, [(3000, 400)])
    html = (out / "index.html").read_text(encoding="utf-8")
    tag = img_tags(html)[1]  # the first gallery image
    entries = [e.split() for e in tag["srcset"].split(", ")]
    widths = [int(w[:-1]) for _, w in entries]
    assert widths == sorted(widths) == list(WIDTHS)
    for path, w in entries:
        assert Image.open(out / path).width == int(w[:-1])


def test_every_image_has_width_and_height_that_match_its_file(tmp_path):
    out, _ = build_with_photos(tmp_path, [(3000, 400), (2400, 300)])
    html = (out / "index.html").read_text(encoding="utf-8")
    for tag in img_tags(html):
        if tag.get("id") == "lb-img":
            continue
        with Image.open(out / tag["src"]) as im:
            assert (int(tag["width"]), int(tag["height"])) == im.size, tag["src"]


def test_first_image_is_eager_and_the_rest_are_lazy(tmp_path):
    out, _ = build_with_photos(tmp_path, [(1600, 300)] * 3)
    html = (out / "index.html").read_text(encoding="utf-8")
    tags = [t for t in img_tags(html) if t.get("id") != "lb-img"]
    hero, gallery = tags[0], tags[1:]
    assert hero.get("fetchpriority") == "high" and "loading" not in hero
    assert "loading" not in gallery[0]  # same file as the hero, already cached
    assert all(t.get("loading") == "lazy" for t in gallery[1:])
    assert all(t.get("decoding") == "async" for t in gallery)
    assert "rel=\"preload\"" in html


def test_gps_and_camera_metadata_are_not_published(tmp_path):
    out, _ = build_with_photos(tmp_path, [(1600, 300)], gps=True)
    src = Image.open(tmp_path / "src1.jpg")
    assert src.getexif().get(0x010F) == "TestCam"  # the input really had metadata
    for f in (out / "photos").iterdir():
        with Image.open(f) as im:
            assert not im.getexif(), f.name
            assert "exif" not in im.info, f.name


def test_stats_show_the_phone_set_is_smaller_than_the_originals(tmp_path):
    _, result = build_with_photos(tmp_path, [(3000, 400)] * 2)
    st = result.photo_stats
    assert st["photos"] == 2
    assert 0 < st["phone_bytes"] < st["output_bytes"]
    assert st["phone_bytes"] < st["original_bytes"]


def test_stale_photos_are_removed_on_rebuild(tmp_path):
    out, _ = build_with_photos(tmp_path, [(1600, 300)] * 3)
    assert (out / "photos" / "p3-1280.webp").exists()
    build_with_photos(tmp_path, [(1600, 300)])
    assert not (out / "photos" / "p3-1280.webp").exists()


def test_link_preview_image_is_1200_by_630(tmp_path):
    out, _ = build_with_photos(tmp_path, [(3000, 400)])
    assert Image.open(out / "photos" / "og.jpg").size == (1200, 630)


def test_example_photos_shrink(tmp_path):
    results = build_site([MAPLE], tmp_path)
    st = results[0].photo_stats
    assert st["phone_bytes"] * 4 < st["original_bytes"]


@pytest.mark.parametrize("bad", [0, -1])
def test_unreadable_photo_gives_a_clear_error(tmp_path, bad):
    data = yaml.safe_load(MAPLE.read_text(encoding="utf-8"))
    broken = tmp_path / "broken.jpg"
    broken.write_bytes(b"not an image")
    data["photos"] = [{"file": str(broken), "alt": "x"}]
    src = tmp_path / "l.yml"
    src.write_text(yaml.safe_dump(data), encoding="utf-8")
    with pytest.raises(Exception, match="cannot identify image"):
        build_site([src], tmp_path / "out")
