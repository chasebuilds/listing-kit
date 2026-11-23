"""Command line: build listing pages, validate files, check wording."""

from __future__ import annotations

import argparse
import json
import sys
from importlib import resources
from pathlib import Path

from . import __version__, fairhousing
from .build import SORTS, build_checker_page, build_site, copy_assets
from .config import ListingError, load_index_config, load_listing


def _cmd_build(args: argparse.Namespace) -> int:
    try:
        results = build_site(
            [Path(p) for p in args.files], Path(args.out), checker=args.checker,
            index_title=args.index_title, sort=args.sort,
            index_config=load_index_config(args.index_config) if args.index_config else None,
        )
    except ListingError as exc:
        print("The listing file has problems:", file=sys.stderr)
        for line in exc.problems:
            print(f"  - {line}", file=sys.stderr)
        return 2
    for r in results:
        print(f"built {r.slug} -> {r.out_dir / 'index.html'}")
        st = r.photo_stats
        if st:
            print(
                f"  photos: {st['photos']} files, {st['original_bytes'] // 1024} KB original; "
                f"{st['output_bytes'] // 1024} KB written in 2 to 3 WebP sizes each; "
                f"the 640 px copies alone total {st['phone_bytes'] // 1024} KB"
            )
        for f in r.warnings:
            print(
                f"  wording [{f.severity}] '{f.match}' ({f.rule_id}): {f.reason} Try: {f.suggest}"
            )
    if any(r.warnings for r in results):
        print("The wording notes above are a writing aid, not legal advice.")
    return 0


def _cmd_validate(args: argparse.Namespace) -> int:
    bad = 0
    for p in args.files:
        try:
            load_listing(p)
            print(f"ok   {p}")
        except ListingError as exc:
            bad += 1
            print(f"FAIL {p}")
            for line in exc.problems:
                print(f"  - {line}")
    return 1 if bad else 0


def _cmd_check(args: argparse.Namespace) -> int:
    if args.file:
        text = Path(args.file).read_text(encoding="utf-8")
    elif args.text:
        text = " ".join(args.text)
    else:
        text = sys.stdin.read()
    rules = fairhousing.load_rules(args.rules)
    packs = ("core", *args.pack)
    findings = fairhousing.check(text, rules, packs)
    if args.json:
        print(json.dumps([f.to_dict() for f in findings], indent=2))
    else:
        if not findings:
            print("No marked wording found. That does not mean the text is compliant.")
        for f in findings:
            print(f"[{f.severity}] '{f.match}'  ({f.category}, rule {f.rule_id})")
            print(f"    why: {f.reason}")
            print(f"    try: {f.suggest}")
        print("Writing aid, not legal advice.", file=sys.stderr)
    return 1 if fairhousing.flags(findings) and not args.no_fail else 0


def _cmd_checker_page(args: argparse.Namespace) -> int:
    out = Path(args.out)
    copy_assets(out)
    build_checker_page(out, assets_rel="assets/", home="https://github.com/chasebuilds/listing-kit")
    print(f"checker page -> {out / 'index.html'}")
    return 0


def _cmd_init(args: argparse.Namespace) -> int:
    dest = Path(args.file)
    if dest.exists():
        print(f"{dest} already exists; not overwriting", file=sys.stderr)
        return 1
    text = resources.files("listing_kit").joinpath("data/starter.yml").read_text("utf-8")
    dest.write_text(text, encoding="utf-8")
    print(f"wrote {dest}. Edit it, add your photos next to it, then run: listing-kit build {dest} -o site")
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="listing-kit",
        description="Single-property listing sites from YAML, plus a fair-housing wording checker.",
    )
    parser.add_argument("--version", action="version", version=f"listing-kit {__version__}")
    sub = parser.add_subparsers(dest="cmd", required=True)

    b = sub.add_parser("build", help="build a listing page (or several) from YAML")
    b.add_argument("files", nargs="+")
    b.add_argument("-o", "--out", required=True)
    b.add_argument("--checker", action="store_true", help="also write the in-page checker")
    b.add_argument("--index-title", default="My listings", help="title of the index page for several listings")
    b.add_argument("--index-config", help="YAML with title, intro and agent block for the index page")
    b.add_argument("--sort", choices=SORTS, default="file", help="order of cards on the index page")
    b.set_defaults(func=_cmd_build)

    v = sub.add_parser("validate", help="check listing files against the schema")
    v.add_argument("files", nargs="+")
    v.set_defaults(func=_cmd_validate)

    c = sub.add_parser("check", help="check description wording (text, --file, or stdin)")
    c.add_argument("text", nargs="*")
    c.add_argument("--file")
    c.add_argument("--rules", help="use your own rules YAML")
    c.add_argument(
        "--pack", action="append", default=[], choices=["local"],
        help="also run an opt-in rule pack: local = state/local law items (not federal)",
    )
    c.add_argument("--json", action="store_true")
    c.add_argument("--no-fail", action="store_true", help="exit 0 even when flags are found")
    c.set_defaults(func=_cmd_check)

    cp = sub.add_parser("checker-page", help="write only the in-page checker")
    cp.add_argument("-o", "--out", required=True)
    cp.set_defaults(func=_cmd_checker_page)

    i = sub.add_parser("init", help="write a starter listing YAML")
    i.add_argument("file", nargs="?", default="listing.yml")
    i.set_defaults(func=_cmd_init)

    args = parser.parse_args(argv)
    return int(args.func(args))


if __name__ == "__main__":
    raise SystemExit(main())
