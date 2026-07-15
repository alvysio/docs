#!/usr/bin/env python3
"""Merge per-endpoint OpenAPI JSON fragments extracted from every
`mirror/reference/*.md` file into a single `openapi/alvys.json` spec
that Mintlify's playground can render."""
import json
import os
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
MIRROR = ROOT / "mirror" / "reference"
OUT = ROOT / "openapi" / "alvys.json"

BLOCK_START = re.compile(r"^# OpenAPI definition\s*\n+```json\s*\n", re.MULTILINE)


def extract_json_block(text: str) -> dict | None:
    """Extract the trailing ` ```json {...} ``` ` block after the
    `# OpenAPI definition` heading."""
    m = BLOCK_START.search(text)
    if not m:
        return None
    start = m.end()
    end = text.find("\n```", start)
    if end == -1:
        return None
    raw = text[start:end]
    return json.loads(raw)


def deep_merge(a: dict, b: dict, path: str = "") -> None:
    """Merge b into a; last write wins on conflicting scalar keys."""
    for k, v in b.items():
        if k in a and isinstance(a[k], dict) and isinstance(v, dict):
            deep_merge(a[k], v, f"{path}.{k}")
        else:
            a[k] = v


def main() -> None:
    merged: dict = {
        "openapi": "3.0.1",
        "info": {
            "title": "Alvys",
            "description": (
                "Alvys provides a robust set of REST APIs to allow you to "
                "integrate Alvys into virtually any platform. These APIs "
                "cover most of Alvys' major product areas with additional "
                "endpoints being added regularly based on customer requests."
            ),
            "contact": {
                "name": "Alvys Support",
                "url": "https://www.alvys.com/resources/contact/",
            },
            "version": "v1",
        },
        "servers": [
            {"url": "https://integrations.alvys.com", "description": "Public API Server"},
            {"url": "https://api.alvys.com/", "description": "Public API Server"},
        ],
        "paths": {},
        "components": {"schemas": {}, "securitySchemes": {}},
        "security": [{"Public": []}],
    }

    consumed = 0
    tag_counts: dict[str, int] = {}
    for md in sorted(MIRROR.glob("*.md")):
        text = md.read_text(encoding="utf-8")
        spec = extract_json_block(text)
        if spec is None:
            continue
        consumed += 1
        for path, ops in spec.get("paths", {}).items():
            existing = merged["paths"].setdefault(path, {})
            for method, op in ops.items():
                existing[method] = op
                for tag in op.get("tags", []):
                    tag_counts[tag] = tag_counts.get(tag, 0) + 1
        schemas = spec.get("components", {}).get("schemas", {})
        for name, schema in schemas.items():
            merged["components"]["schemas"][name] = schema
        sec = spec.get("components", {}).get("securitySchemes", {})
        for name, s in sec.items():
            merged["components"]["securitySchemes"].setdefault(name, s)

    # Derive tags[] from tag_counts with a friendly description each. The
    # source spec uses PascalCase tag names ("DispatchPreferences"); expand
    # them to display labels ("Dispatch Preferences") without renaming the
    # tag key so the auto-generated URL path remains lowercased-PascalCase.
    tag_labels = {
        "DispatchPreferences": "Dispatch preferences endpoints for reading dispatch rules and preferences.",
    }
    default_desc = {
        "Carriers": "Read carrier records, search carriers, and manage carrier documents.",
        "Customers": "Create, read, update, delete, and search customer records.",
        "Deductions": "Create one-time deductions and search or delete existing deduction records.",
        "Drivers": "Read driver records, search drivers and driver events, and manage driver documents.",
        "Fuel": "Read and search fuel transactions.",
        "Invoices": "Read invoices, create carrier invoices, and record carrier and customer payments.",
        "Loads": "Read, update, search loads, and manage load documents and notes.",
        "Locations": "Read and search company location details.",
        "Maintenance": "Read and search maintenance records.",
        "Tenders": "Create, accept, reject, cancel, update, and search inbound EDI tenders.",
        "Tolls": "Read and search toll transactions.",
        "Trailers": "Read trailers, search trailer events, and manage trailer documents.",
        "Trips": "Read, search trips, manage trip documents, and record stop appointments, arrivals, and departures.",
        "Trucks": "Read trucks, search truck events, and manage truck documents.",
        "Users": "List and search users.",
        "Visibility": "Read inbound and outbound visibility history and search outbound visibility errors.",
        "Webhooks": (
            "Create, read, update, delete, enable, disable, verify, test, and rotate secrets for "
            "webhook subscriptions; read event types, delivery logs, and health metrics."
        ),
    }
    merged["tags"] = [
        {
            "name": t,
            "description": tag_labels.get(t) or default_desc.get(t, f"{t} endpoints"),
        }
        for t in sorted(tag_counts.keys())
    ]

    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(merged, indent=2), encoding="utf-8")
    print(f"Consumed {consumed} fragments; wrote {OUT} with {len(merged['paths'])} paths, {len(merged['tags'])} tags.")
    for t, n in sorted(tag_counts.items()):
        print(f"  {t}: {n}")


if __name__ == "__main__":
    main()
