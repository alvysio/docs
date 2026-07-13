#!/usr/bin/env python3
"""Build a single `changelog.mdx` page in Mintlify's native format
(one `<Update>` component per source changelog entry).

Reads the raw ReadMe `mirror/changelog/*.md` corpus, applies the same
Mintlify-conversion normalizations that `scripts/transform.py` runs on
docs and reference pages, and pairs each entry with its true `created_at`
timestamp + ReadMe `type` (Added / Fixed / Improved / ...) captured in
`scripts/_sitemap-cache/changelog-metadata.json`."""
import json
import os
import re
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
MIRROR = ROOT / "mirror" / "changelog"
OUT = ROOT / "changelog.mdx"
CACHE_DIR = ROOT / "scripts" / "_sitemap-cache"
METADATA = CACHE_DIR / "changelog-metadata.json"

sys.path.insert(0, str(ROOT / "scripts"))
from transform import (  # noqa: E402
    strip_docindex_and_h1,
    rewrite_links,
    strip_readme_hash_slash,
    convert_readme_callout_tags,
    convert_readme_callouts,
    convert_readme_cards,
    normalize_code_fences,
    escape_bare_angle_brackets,
    normalize_br,
)

# Legacy sitemap-lastmod cache — kept as a fallback for entries the metadata
# cache doesn't cover. sitemap.xml `lastmod` is the *modified-at* timestamp
# from ReadMe, so it clusters everything around the last bulk re-index date
# (June 2026 in this project); use `created_at` from the entry state where
# available.
LEGACY_LASTMODS = CACHE_DIR / "changelog-lastmods.json"


def load_metadata() -> dict[str, dict]:
    """Load per-slug metadata (created_at + ReadMe entry type) fetched from
    each source page's embedded state. Fetching lives in
    scripts/fetch_changelog_metadata.py so this build script stays offline."""
    if METADATA.exists():
        return json.loads(METADATA.read_text())
    return {}


def load_lastmods() -> dict[str, str]:
    if LEGACY_LASTMODS.exists():
        return json.loads(LEGACY_LASTMODS.read_text())
    return {}


def parse_iso(ts: str) -> datetime | None:
    if not ts:
        return None
    try:
        return datetime.fromisoformat(ts.replace("Z", "+00:00"))
    except ValueError:
        return None


TAG_RULES = [
    # (regex tested against slug+title, tag label)
    (re.compile(r"webhook", re.I), "Webhooks"),
    (re.compile(r"tender", re.I), "Tenders"),
    (re.compile(r"visibility|tracking", re.I), "Visibility"),
    (re.compile(r"carrier", re.I), "Carriers"),
    (re.compile(r"customer", re.I), "Customers"),
    (re.compile(r"invoice|payment", re.I), "Invoices"),
    (re.compile(r"deduction", re.I), "Deductions"),
    (re.compile(r"driver", re.I), "Drivers"),
    (re.compile(r"trip", re.I), "Trips"),
    (re.compile(r"\bload", re.I), "Loads"),
    (re.compile(r"truck|trailer|fleet", re.I), "Fleet"),
    (re.compile(r"fuel|toll", re.I), "Financials"),
    (re.compile(r"maintenance", re.I), "Maintenance"),
    (re.compile(r"dispatch", re.I), "Dispatch"),
    (re.compile(r"user|access|scope|permission|auth|token", re.I), "Authentication"),
    (re.compile(r"docs|documentation|guide|template|power[- ]?bi|google", re.I), "Documentation"),
]

# ReadMe changelog `type` field → capitalized Mintlify tag label. Mirrors
# what ReadMe renders as a colored chip above each entry title.
README_TYPE_TO_TAG = {
    "added": "Added",
    "fixed": "Fixed",
    "improved": "Improved",
    "changed": "Changed",
    "removed": "Removed",
    "deprecated": "Deprecated",
}


def derive_tags(slug: str, title: str, body: str, readme_type: str | None = None) -> list[str]:
    """Return up-to-3 tag chips. Always leads with the ReadMe `type` chip
    (Added/Fixed/Improved/...) when it is set to a real value, so the
    Mintlify sidebar filter surfaces the same primary categorization the
    source ReadMe changelog does. Falls back to entity tags derived from
    the slug/title text."""
    haystack = f"{slug} {title}"
    tags: list[str] = []
    seen: set[str] = set()
    if readme_type:
        primary = README_TYPE_TO_TAG.get(readme_type.lower())
        if primary:
            tags.append(primary)
            seen.add(primary)
    for pat, tag in TAG_RULES:
        if pat.search(haystack) and tag not in seen:
            tags.append(tag)
            seen.add(tag)
    return tags[:3] if tags else ["Public API"]


def read_entry(path: Path) -> tuple[str, str]:
    """Read `mirror/changelog/<slug>.md` and run the same conversion
    pipeline the doc/reference transformer uses, then split the leading
    H1 as the title from the rest of the body."""
    src = path.read_text(encoding="utf-8")
    title, body = strip_docindex_and_h1(src)
    body = rewrite_links(body)
    body = strip_readme_hash_slash(body)
    body = convert_readme_callout_tags(body)
    body = convert_readme_callouts(body)
    body = convert_readme_cards(body)
    body = normalize_code_fences(body)
    body = escape_bare_angle_brackets(body)
    body = normalize_br(body)
    body = re.sub(r"\n{3,}", "\n\n", body).strip()
    return title, body


def format_label(dt: datetime | None) -> str:
    """Render a Mintlify-style date label like `June 19, 2026`."""
    if not dt:
        return "Undated"
    return dt.strftime("%B %-d, %Y") if os.name == "posix" else dt.strftime("%B %d, %Y")


def format_time_suffix(dt: datetime) -> str:
    """Render a compact time suffix like `9:37 AM` used to disambiguate
    Mintlify `<Update>` labels when two entries share the same day."""
    h = dt.strftime("%-I") if os.name == "posix" else dt.strftime("%#I")
    return f'{h}:{dt.strftime("%M %p")}'


def indent(text: str, prefix: str = "  ") -> str:
    """Indent every line for readability inside the <Update> body."""
    return "\n".join((prefix + line) if line else "" for line in text.split("\n"))


def main() -> None:
    metadata = load_metadata()
    lastmods = load_lastmods()  # legacy fallback

    entries: list[tuple[datetime | None, str, str, str, list[str], str | None]] = []
    for f in sorted(MIRROR.glob("*.md")):
        slug = f.stem
        title, body = read_entry(f)
        meta = metadata.get(slug) or {}
        # Prefer the source's real `created_at` timestamp (from the entry's
        # embedded state), which is the actual publication date. Fall back
        # to sitemap `lastmod` only when the metadata cache is missing it —
        # `lastmod` reflects bulk re-index dates and clusters all entries
        # around a small handful of days.
        dt = parse_iso(meta.get("created_at") or lastmods.get(slug, ""))
        readme_type = (meta.get("type") or "").lower() or None
        if readme_type == "none":
            readme_type = None
        tags = derive_tags(slug, title, body, readme_type=readme_type)
        entries.append((dt, slug, title, body, tags, readme_type))

    entries.sort(key=lambda e: (e[0] or datetime(1970, 1, 1, tzinfo=timezone.utc)), reverse=True)

    lines: list[str] = []
    lines.append("---")
    lines.append('title: "Changelog"')
    lines.append('description: "Product updates and announcements for the Alvys Public API."')
    lines.append("rss: true")
    lines.append("---")
    lines.append("")

    # Mintlify's <Update label> must be unique because it becomes the
    # anchor. When two entries share the same day, disambiguate with the
    # entry's UTC time-of-day (e.g. `June 19, 2026 · 9:37 AM`) rather
    # than a slug in parentheses. Compute the count up front so we can
    # add the time suffix on both entries of a colliding pair — not just
    # the later one — for consistency.
    date_counts: dict[str, int] = {}
    for dt, *_ in entries:
        date_counts[format_label(dt)] = date_counts.get(format_label(dt), 0) + 1

    for dt, slug, title, body, tags, _rt in entries:
        label = format_label(dt)
        if date_counts.get(label, 0) > 1 and dt is not None:
            label = f"{label} · {format_time_suffix(dt)}"

        tags_repr = "[" + ", ".join(f'"{t}"' for t in tags) + "]"

        lines.append(f"{{/* source: /changelog/{slug} */}}")
        lines.append(f'<Update label="{label}" description="{title}" tags={{{tags_repr}}}>')
        lines.append(indent(body))
        lines.append("</Update>")
        lines.append("")

    OUT.write_text("\n".join(lines))
    print(f"Wrote {OUT} with {len(entries)} <Update> blocks.")


if __name__ == "__main__":
    main()
