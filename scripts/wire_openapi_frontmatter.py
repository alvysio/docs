#!/usr/bin/env python3
"""For every `/reference/*.mdx` page that maps 1:1 to an operation in
`openapi/alvys.json`, add an `openapi:` frontmatter directive pointing
at that operation. Mintlify then overlays the interactive playground
onto the existing prose page — no separate "API Playground" tab
required, and the source ReadMe URLs stay unchanged.

The mapping is derived from the source ReadMe slug pattern
`{method}_api-p-v-version-{path-with-dashes}` which the source spec
uses for every endpoint page."""
import json
import os
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
REF = ROOT / "reference"
SPEC_PATH = ROOT / "openapi" / "alvys.json"


def slug_of(method: str, path: str) -> str:
    """Reproduce ReadMe's slug convention:
    `{method}_api-p-v-version-{path-slug}` where the path has
    `/api/p/v{version}/` stripped, `/` replaced with `-`, and
    `{}` removed."""
    p = path.replace("/api/p/v{version}/", "api-p-v-version-")
    p = p.replace("/", "-").replace("{", "").replace("}", "")
    return f"{method.lower()}_{p}".lower()


def read_frontmatter(text: str) -> tuple[str, str]:
    """Return (frontmatter_yaml, body_text). Assumes the file starts
    with `---\n...\n---\n`."""
    m = re.match(r"---\n(.*?)\n---\n?(.*)", text, re.DOTALL)
    if not m:
        return "", text
    return m.group(1), m.group(2)


def main() -> None:
    spec = json.loads(SPEC_PATH.read_text())

    slug_to_op: dict[str, tuple[str, str]] = {}
    for path, ops in spec["paths"].items():
        for method, _ in ops.items():
            if method not in ("get", "post", "put", "patch", "delete"):
                continue
            slug_to_op[slug_of(method, path)] = (method.upper(), path)

    changed = 0
    skipped_prose_only: list[str] = []
    for mdx in sorted(REF.glob("*.mdx")):
        slug = mdx.stem.lower()
        text = mdx.read_text(encoding="utf-8")
        fm, body = read_frontmatter(text)

        if "openapi:" in fm:
            continue

        if slug not in slug_to_op:
            skipped_prose_only.append(mdx.name)
            continue

        method, path = slug_to_op[slug]
        directive = f'openapi: "{method} {path}"'

        new_fm = fm.rstrip("\n") + "\n" + directive
        new_text = f"---\n{new_fm}\n---\n{body}"
        mdx.write_text(new_text, encoding="utf-8")
        changed += 1

    print(f"Added openapi: directive to {changed} reference pages.")
    print(f"Skipped {len(skipped_prose_only)} prose-only pages: {skipped_prose_only}")


if __name__ == "__main__":
    main()
