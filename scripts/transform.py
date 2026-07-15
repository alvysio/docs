#!/usr/bin/env python3
"""Deterministic transformer: mirror/*.md (from docs.alvys.com) -> .mdx files
in the Mintlify repo. Preserves prose verbatim; converts ReadMe-specific
patterns into Mintlify components."""
import json
import os
import re
import shutil
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
MIRROR = ROOT / "mirror"
OUT_DOCS = ROOT / "docs"
OUT_REF = ROOT / "reference"
OUT_CHANGELOG = ROOT / "changelog"

# --------- helpers ---------

DOC_INDEX_BLOCK = re.compile(
    r"^> ## Documentation Index\n(?:> [^\n]*\n)+", re.MULTILINE
)

READMEIO_LINK = re.compile(
    r"https?://(?:docs\.alvys\.com|alvys\.readme\.io)((?:/docs|/reference|/changelog)[^\s\)#'\"]*)?"
)

BLOCKQUOTE_CALLOUT = re.compile(
    r"""^(?P<open>> \s*(?P<emoji>[📘ℹ️🚧⚠️❗✅💡🧪🔒🔐🎯📝📄📌🚀ℹ️🧠🛡️🔍]|[^A-Za-z0-9`> \n])\s*(?P<title>[^\n]*)\n)(?P<body>(?:> ?[^\n]*\n?)*)""",
    re.MULTILINE,
)

CALLOUT_TAG = re.compile(
    r"<Callout\s+([^>]*?)>(.*?)</Callout>", re.DOTALL
)
CALLOUT_ATTR = re.compile(r"""(\w+)\s*=\s*(?:"([^"]*)"|'([^']*)'|{([^}]*)})""")

EMOJI_TO_MINT = {
    "📘": "Info",
    "ℹ️": "Info",
    "💡": "Tip",
    "🧠": "Tip",
    "✅": "Tip",
    "🎯": "Tip",
    "⚠️": "Warning",
    "❗": "Warning",
    "🚧": "Warning",
    "🔒": "Note",
    "🔐": "Note",
    "🛡️": "Note",
    "🚀": "Note",
    "📝": "Note",
    "📄": "Note",
    "🔍": "Note",
    "🧪": "Note",
    "📌": "Note",
}

# Cards -> CardGroup mapping; icon "fa-home" -> "house"
FA_LEGACY_TO_MINT = {
    "fa-home": "house",
    "fa-question": "circle-question",
    "fa-book": "book",
    "fa-key": "key",
    "fa-lock": "lock",
    "fa-unlock": "lock-open",
    "fa-cog": "gear",
    "fa-gear": "gear",
    "fa-plug": "plug",
    "fa-code": "code",
    "fa-bolt": "bolt",
    "fa-rocket": "rocket",
    "fa-truck": "truck",
    "fa-users": "users",
    "fa-user": "user",
    "fa-shield": "shield",
    "fa-shield-alt": "shield-halved",
    "fa-envelope": "envelope",
    "fa-list": "list",
    "fa-tools": "screwdriver-wrench",
    "fa-wrench": "wrench",
    "fa-globe": "globe",
    "fa-chart-bar": "chart-column",
    "fa-file": "file",
    "fa-file-alt": "file-lines",
    "fa-search": "magnifying-glass",
    "fa-clipboard": "clipboard",
    "fa-clock": "clock",
    "fa-info": "circle-info",
    "fa-info-circle": "circle-info",
    "fa-exclamation-circle": "circle-exclamation",
    "fa-check": "check",
    "fa-check-circle": "circle-check",
    "fa-times-circle": "circle-xmark",
    "fa-arrow-right": "arrow-right",
    "fa-arrow-left": "arrow-left",
    "fa-play": "play",
    "fa-pause": "pause",
    "fa-warehouse": "warehouse",
    "fa-database": "database",
    "fa-share-alt": "share-nodes",
    "fa-cloud": "cloud",
    "fa-briefcase": "briefcase",
    "fa-comments": "comments",
    "fa-comment": "comment",
    "fa-star": "star",
    "fa-tag": "tag",
    "fa-tags": "tags",
    "fa-inbox": "inbox",
    "fa-hand-shake": "handshake",
}


def rewrite_links(text: str) -> str:
    """Rewrite absolute docs.alvys.com / alvys.readme.io links to root-relative,
    strip trailing #/ and .md extensions from internal doc/ref/changelog links.
    Leave other absolute URLs untouched."""

    def repl(m: re.Match) -> str:
        path = m.group(1) or "/"
        # Trim trailing #/
        path = path.replace("#/", "")
        # Strip .md
        path = re.sub(r"\.md(?=$|[?#])", "", path)
        return path

    text = READMEIO_LINK.sub(repl, text)
    return text


def convert_readme_callouts(text: str) -> str:
    """Convert `> 📘 Title\n> body...` blocks into `<Info>...</Info>`."""

    lines = text.split("\n")
    out: list[str] = []
    i = 0
    while i < len(lines):
        line = lines[i]
        m = re.match(r"^>\s+(\S)(?:\s|\uFE0F)?\s*(.*)$", line)
        first_char = ""
        title_rest = ""
        # Match first non-space token after '> ' – if it's an emoji glyph
        strip = re.match(r"^>\s+(.*)$", line)
        if strip:
            content = strip.group(1)
            # detect emoji as first token
            m2 = re.match(r"^([\U0001F300-\U0001FAFF\u2600-\u27BF][\uFE0F]?)\s*(.*)$", content)
            if m2 and m2.group(1) in EMOJI_TO_MINT:
                emoji = m2.group(1)
                title_rest = m2.group(2)
                # Consume subsequent > lines as body
                body_lines: list[str] = []
                if title_rest.strip():
                    body_lines.append(title_rest.rstrip())
                j = i + 1
                while j < len(lines) and (lines[j].startswith("> ") or lines[j] == ">"):
                    body_lines.append(re.sub(r"^>\s?", "", lines[j]))
                    j += 1
                tag = EMOJI_TO_MINT[emoji]
                # Build MDX component
                body_text = "\n".join(body_lines).strip()
                # Indent multi-line body for readability
                out.append(f"<{tag}>")
                if body_text:
                    for bl in body_text.split("\n"):
                        out.append(f"  {bl}" if bl else "")
                out.append(f"</{tag}>")
                i = j
                continue
        out.append(line)
        i += 1
    return "\n".join(out)


def convert_readme_callout_tags(text: str) -> str:
    """Convert `<Callout icon="🚀" theme="...">body</Callout>` into a Mintlify tag."""

    def repl(m: re.Match) -> str:
        attrs = m.group(1)
        body = m.group(2)
        emoji = None
        theme = None
        for am in CALLOUT_ATTR.finditer(attrs):
            name = am.group(1)
            val = am.group(2) or am.group(3) or am.group(4)
            if name == "icon":
                emoji = val
            elif name == "theme":
                theme = val
        tag = EMOJI_TO_MINT.get(emoji or "", "Note")
        if theme:
            tl = theme.lower()
            if "warn" in tl:
                tag = "Warning"
            elif "info" in tl:
                tag = "Info"
            elif "tip" in tl or "success" in tl:
                tag = "Tip"
        # Strip inner ### headings that were part of the readme callout header
        body = re.sub(r"^\s*###\s+[^\n]*\n", "", body, count=1)
        body_stripped = body.strip("\n").rstrip()
        return f"<{tag}>\n  " + body_stripped.replace("\n", "\n  ") + f"\n</{tag}>"

    return CALLOUT_TAG.sub(repl, text)


def convert_readme_cards(text: str) -> str:
    """Convert ReadMe `<Cards columns={N}>...<Card icon="fa-home">...</Card></Cards>`
    into Mintlify `<CardGroup cols={N}>` + `<Card icon="house">`. Also transform
    `<li>[label](href)</li>` items inside cards into a proper markdown list."""

    # Cards wrapper
    text = re.sub(
        r"<Cards\s+columns\s*=\s*\{(\d+)\}\s*>",
        lambda m: f"<CardGroup cols={{{m.group(1)}}}>",
        text,
    )
    text = re.sub(r"</Cards\s*>", "</CardGroup>", text)

    # Icon rewriting: fa-home -> house
    def icon_rewrite(m: re.Match) -> str:
        raw = m.group(1)
        return f'icon="{FA_LEGACY_TO_MINT.get(raw, raw.replace("fa-", ""))}"'

    text = re.sub(r'icon="(fa-[a-z0-9-]+)"', icon_rewrite, text)

    # Convert <li>...</li> lines inside cards to markdown list items
    def fix_li(m: re.Match) -> str:
        inner = m.group(1).strip()
        return f"- {inner}"

    text = re.sub(r"<li>(.*?)</li>", fix_li, text)
    return text


def strip_openapi_definition_block(text: str) -> str:
    """Remove the trailing `# OpenAPI definition\n\n```json\n...\n``` ` block
    that appears in every ReadMe reference page. The prose above is what
    matters for reading; the JSON dump adds no visible value."""
    idx = text.find("\n# OpenAPI definition")
    if idx == -1:
        return text
    return text[:idx].rstrip() + "\n"


def normalize_code_fences(text: str) -> str:
    """`curl` isn't a real Prism language; rewrite to bash."""
    text = re.sub(r"^```curl(\s*$)", r"```bash\1", text, flags=re.MULTILINE)
    return text


def strip_docindex_and_h1(md: str) -> tuple[str, str]:
    md = DOC_INDEX_BLOCK.sub("", md, count=1).lstrip()
    # Extract first H1
    m = re.match(r"# +([^\n]+)\n", md)
    title = ""
    body = md
    if m:
        title = m.group(1).strip()
        body = md[m.end() :].lstrip("\n")
    return title, body


def yaml_escape(v: str) -> str:
    v = v.replace('\\', '\\\\').replace('"', "'")
    return v


def build_frontmatter(title: str, description: str | None = None, sidebar_title: str | None = None) -> str:
    lines = ["---"]
    if title:
        lines.append(f'title: "{yaml_escape(title)}"')
    if sidebar_title and sidebar_title != title:
        lines.append(f'sidebarTitle: "{yaml_escape(sidebar_title)}"')
    if description:
        # collapse whitespace and trim
        desc = re.sub(r"\s+", " ", description).strip()
        if len(desc) > 200:
            desc = desc[:197].rstrip() + "..."
        lines.append(f'description: "{yaml_escape(desc)}"')
    lines.append("---\n")
    return "\n".join(lines)


def escape_bare_angle_brackets(text: str) -> str:
    """Escape bare `<x>` placeholders in prose (outside code fences AND outside
    inline backticks)."""
    ALLOWED = re.compile(
        r"^/?(Info|Note|Tip|Warning|Card|CardGroup|Cards|Accordion|AccordionGroup|"
        r"Steps|Step|Tabs?|Frame|Icon|Tooltip|Update|Callout|ParamField|ResponseField|"
        r"CodeGroup|RequestExample|ResponseExample|Expandable|Snippet|br|em|strong|"
        r"code|table|thead|tbody|tr|td|th|kbd|sub|sup|hr|div|span|img|a|ul|ol|li|p)(\b|/|$)"
    )
    ANGLE_TOKEN = re.compile(r"<([^<>\s`][^<>]*?)>")

    def process_line(line: str) -> str:
        # Split by inline code spans (backticks) to preserve them
        parts = re.split(r"(`+[^`]*`+)", line)
        for i, part in enumerate(parts):
            if part.startswith("`"):
                continue

            def repl(m: re.Match) -> str:
                inner = m.group(1)
                if ALLOWED.match(inner):
                    return m.group(0)
                return f"`<{inner}>`"

            parts[i] = ANGLE_TOKEN.sub(repl, part)
        return "".join(parts)

    out_lines: list[str] = []
    in_fence = False
    for line in text.split("\n"):
        if line.startswith("```"):
            in_fence = not in_fence
            out_lines.append(line)
            continue
        if in_fence:
            out_lines.append(line)
            continue
        out_lines.append(process_line(line))
    return "\n".join(out_lines)


def normalize_br(text: str) -> str:
    return re.sub(r"<br\s*/?>", "<br />", text, flags=re.IGNORECASE)


def strip_readme_hash_slash(text: str) -> str:
    """Rewrite `](url#/)` -> `](url)` for links that end with #/ (ReadMe suffix)."""
    return re.sub(r"\]\(([^)\s]+?)#/([\)\s])", r"](\1\2", text)


# Per-page overrides that the transformer should apply on every re-run.
# Keyed by `source_path` (e.g. `docs/connecting-power-bi-to-alvys-public-api-guide`).
# Currently used to disambiguate parent pages whose title equals a nested-group
# label — Mintlify would otherwise render the sidebar as `Group > Group`
# (per mstack style-docs "Rename duplicated category landing pages with
# sidebarTitle: 'Overview'").
SIDEBAR_TITLE_OVERRIDES: dict[str, str] = {
    "docs/connecting-power-bi-to-alvys-public-api-guide": "Overview",
}


def _openapi_directive_for(source_path: str) -> str | None:
    """If `source_path` matches an operation in openapi/alvys.json, return an
    `openapi: "METHOD /path"` frontmatter directive so Mintlify renders the
    interactive playground on that page. Prose-only reference pages return
    None."""
    spec_path = ROOT / "openapi" / "alvys.json"
    if not spec_path.exists():
        return None
    if not source_path.startswith("reference/"):
        return None
    slug = source_path.split("/", 1)[1].lower()
    global _OPENAPI_SLUG_MAP
    if "_OPENAPI_SLUG_MAP" not in globals() or _OPENAPI_SLUG_MAP is None:
        import json as _j

        spec = _j.loads(spec_path.read_text())
        _OPENAPI_SLUG_MAP = {}
        for p, ops in spec.get("paths", {}).items():
            for method in ops:
                if method not in ("get", "post", "put", "patch", "delete"):
                    continue
                key = (
                    f"{method}_"
                    + p.replace("/api/p/v{version}/", "api-p-v-version-")
                    .replace("/", "-")
                    .replace("{", "")
                    .replace("}", "")
                ).lower()
                _OPENAPI_SLUG_MAP[key] = (method.upper(), p)
    match = _OPENAPI_SLUG_MAP.get(slug)
    if not match:
        return None
    method, path = match
    return f'openapi: "{method} {path}"'


_OPENAPI_SLUG_MAP: dict | None = None


def transform(mirror_path: Path, out_path: Path, category: str, source_path: str) -> dict:
    src = mirror_path.read_text(encoding="utf-8")

    title, body = strip_docindex_and_h1(src)

    if category == "reference":
        body = strip_openapi_definition_block(body)

    # Rewrite absolute links and hash-slash suffix before other transforms
    body = rewrite_links(body)
    body = strip_readme_hash_slash(body)

    body = convert_readme_callout_tags(body)
    body = convert_readme_callouts(body)
    body = convert_readme_cards(body)
    body = normalize_code_fences(body)
    body = escape_bare_angle_brackets(body)
    body = normalize_br(body)

    # Collapse consecutive blank lines to a max of 2
    body = re.sub(r"\n{3,}", "\n\n", body).strip() + "\n"

    # First paragraph as description candidate only if it looks like a real lead
    description = None
    # We deliberately omit description to match source ReadMe (no visible subtitle)

    sidebar_title = SIDEBAR_TITLE_OVERRIDES.get(source_path)
    fm = build_frontmatter(title, description=description, sidebar_title=sidebar_title)
    directive = _openapi_directive_for(source_path)
    if directive:
        # Append the openapi directive inside the frontmatter block.
        fm = fm.rstrip("\n").removesuffix("---").rstrip("\n") + "\n" + directive + "\n---\n"

    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(fm + "\n" + body, encoding="utf-8")

    return {
        "source_url": None,  # filled in by caller
        "normalized_path": str(out_path.relative_to(ROOT)).removesuffix(".mdx"),
        "source_h1": title,
        "converted_file": str(out_path.relative_to(ROOT)),
        "nav_section": category,
        "status": "done",
        "notes": "",
    }


def main() -> None:
    # Clean output dirs so re-runs are deterministic
    for d in (OUT_DOCS, OUT_REF, OUT_CHANGELOG):
        if d.exists():
            shutil.rmtree(d)

    manifest: list[dict] = []
    urls_map = {}
    for line in open("/tmp/urls-map.tsv"):
        src, fn = line.rstrip("\n").split("\t")
        urls_map[fn.removesuffix(".md")] = src

    for md in sorted(MIRROR.rglob("*.md")):
        rel = md.relative_to(MIRROR)
        parts = rel.parts
        # docs/* -> guides/*.mdx
        # reference/* -> reference/*.mdx
        # changelog/* -> changelog/*.mdx
        if parts[0] == "docs":
            out = OUT_DOCS / rel.with_suffix(".mdx").relative_to("docs")
            category = "docs"
            source_path = f"docs/{rel.stem}"
        elif parts[0] == "reference":
            out = OUT_REF / rel.with_suffix(".mdx").relative_to("reference")
            category = "reference"
            source_path = f"reference/{rel.stem}"
        elif parts[0] == "changelog":
            # Changelog entries are consolidated into a single Mintlify-native
            # `<Update>`-based `changelog.mdx` by `scripts/build_changelog.py`
            # (per https://mintlify.com/docs/create/changelogs). This
            # transformer still records the source URL for the parity manifest
            # so `/changelog/<slug>` sources trace to `changelog.mdx`, but it
            # does not emit an individual `changelog/<slug>.mdx` file.
            source_path = f"changelog/{rel.stem}"
            manifest.append(
                {
                    "source_url": urls_map.get(source_path, ""),
                    "source_path": source_path,
                    "normalized_path": "changelog",
                    "source_h1": rel.stem.replace("-", " ").title(),
                    "converted_file": "changelog.mdx",
                    "nav_section": "changelog",
                    "status": "done",
                    "notes": "Consolidated into changelog.mdx as an <Update> block; original URL redirects to /changelog.",
                }
            )
            continue
        else:
            continue

        row = transform(md, out, category, source_path)
        row["source_url"] = urls_map.get(source_path, "")
        row["source_path"] = source_path
        manifest.append(row)

    (ROOT / "parity-manifest.json").write_text(
        json.dumps(manifest, indent=2), encoding="utf-8"
    )
    print(f"Converted {len(manifest)} pages.")


if __name__ == "__main__":
    main()
