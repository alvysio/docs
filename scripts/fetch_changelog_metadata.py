#!/usr/bin/env python3
"""Fetch per-slug created_at + type from each ReadMe changelog page's
embedded state and cache them at
scripts/_sitemap-cache/changelog-metadata.json. Run this once whenever
new changelog entries appear on docs.alvys.com so
`scripts/build_changelog.py` picks up correct publish dates and
Added/Fixed/Improved chips."""
import json
import re
import time
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
CACHE = ROOT / "scripts" / "_sitemap-cache" / "changelog-metadata.json"
SITEMAP = "https://docs.alvys.com/sitemap.xml"


def fetch(url: str) -> str:
    req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
    with urllib.request.urlopen(req, timeout=20) as r:
        return r.read().decode("utf-8", errors="replace")


def main() -> None:
    xml = fetch(SITEMAP)
    slugs = [
        u.rsplit("/", 1)[-1]
        for u in re.findall(r"<loc>([^<]+)</loc>", xml)
        if "/changelog/" in u
    ]
    print(f"Fetching metadata for {len(slugs)} entries...")

    results: dict[str, dict] = {}
    for i, slug in enumerate(slugs):
        try:
            html = fetch(f"https://docs.alvys.com/changelog/{slug}")
        except Exception as e:
            results[slug] = {"error": str(e)}
            continue
        idx = html.find(f'"slug":"{slug}"')
        window = html[max(0, idx - 2000) : idx + 500] if idx >= 0 else ""
        cm = re.search(r'"created_at":"([^"]+)"', window)
        tm = re.search(r'"type":"([^"]+)"', window)
        results[slug] = {
            "created_at": cm.group(1) if cm else None,
            "type": tm.group(1) if tm else None,
        }
        if i % 5 == 0:
            print(f"  {i}/{len(slugs)}: {slug} -> {results[slug]}")
        time.sleep(0.15)

    CACHE.parent.mkdir(parents=True, exist_ok=True)
    CACHE.write_text(json.dumps(results, indent=2), encoding="utf-8")
    print(f"Wrote {CACHE}")


if __name__ == "__main__":
    main()
