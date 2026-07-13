# Alvys API Documentation (Mintlify)

Alvys Public API and MCP documentation for [alvys.mintlify.io](https://alvys.mintlify.io/), published from this repo via the Mintlify GitHub App on every push to `main`.

This repo is the **Mintlify POC publish target** for the self-healing documentation loop ([backend#36139](https://github.com/alvysio/backend/pull/36139)). The workflow currently targets `alvysio/api-docs` (ReadMe); it will be retargeted here once this scaffold lands.

## Local development

Install the [Mintlify CLI](https://www.npmjs.com/package/mint):

```bash
npm i -g mint
```

Preview at the repo root (where `docs.json` lives):

```bash
mint dev
```

Open [http://localhost:3000](http://localhost:3000).

Validate configuration and OpenAPI:

```bash
mint validate
```

## Publishing

The Mintlify GitHub App is installed on `alvysio/docs`. Pushes to `main` auto-deploy to [alvys.mintlify.io](https://alvys.mintlify.io/).

## Repository layout

```
docs.json                 # Site config: branding, nav tabs, OpenAPI binding
index.mdx                 # Landing page
docs/                     # Guides (Documentation tab)
  getting-started.mdx
  authentication.mdx
  versioning.mdx
  base-url.mdx
openapi/
  alvys.json              # OpenAPI 3.0 spec — drives API Reference tab
ai-agents/                # MCP catalog (AI & Agents tab)
  mcp.mdx
  available-mcp-tools.mdx
changelog/
  index.mdx               # Release notes — agent prepends new entries here
logo/                     # light.svg / dark.svg (Alvys wordmarks)
AGENTS.md                 # Agent authoring rules for this repo
```

### Navigation tabs

| Tab | Source |
| --- | --- |
| **Documentation** | `index.mdx`, `docs/*.mdx` |
| **API Reference** | Auto-generated from `openapi/alvys.json` |
| **AI & Agents** | `ai-agents/*.mdx` |
| **Changelog** | `changelog/index.mdx` |

### Page format (Mintlify MDX)

Every page is an `.mdx` file with YAML frontmatter:

```mdx
---
title: "Page title"
description: "One-line summary for SEO and AI indexing"
---

Body in MDX. Use Mintlify components: Note, Warning, Tip, Card, CardGroup, Columns, Steps.
```

**Do not** use ReadMe-specific frontmatter (`excerpt`, `hidden`, `deprecated`, `metadata`, `next`, `api_config`).

### Changelog path

Self-healing agent: **prepend** new dated sections to `changelog/index.mdx` (newest first). Do not create separate changelog files unless we adopt Mintlify's multi-page changelog pattern later.

### MCP catalog path

- Overview: `ai-agents/mcp.mdx`
- Tool table: `ai-agents/available-mcp-tools.mdx`

When new MCP tools ship, update the domain tables in `available-mcp-tools.mdx` and cross-link from `mcp.mdx`.

### OpenAPI / API reference

Endpoint pages are **auto-generated** from `openapi/alvys.json`. To document a new endpoint:

1. Update `openapi/alvys.json` (synced from the Public API spec in `alvysio/api-docs/reference/alvys.json` today).
2. Mintlify regenerates pages on deploy — no per-endpoint MDX unless adding `x-mint: content` in the spec.

## ReadMe → Mintlify format deltas (for `docs-sync` retarget)

When porting content from `alvysio/api-docs` (ReadMe Git Sync):

| ReadMe (`api-docs`) | Mintlify (`docs`) |
| --- | --- |
| `docs/Documentation/*.md` | `docs/*.mdx` |
| `docs/AI & Agents/mcp/*.md` | `ai-agents/*.mdx` |
| `reference/Alvys/**/*.md` with `api:` frontmatter | Prefer OpenAPI in `openapi/alvys.json`; use `x-mint: content` for per-endpoint prose |
| `reference/_order.yaml`, `docs/**/_order.yaml` | `docs.json` navigation `tabs` / `groups` / `pages` |
| ReadMe `<Callout icon="…" theme="…">` | Mintlify `<Note>`, `<Warning>`, `<Tip>` (or `<Callout>` where supported) |
| ReadMe `<Cards>` / `<Card href="…">` | Mintlify `<CardGroup>` / `<Card>` |
| `docs.alvys.com/docs/authentication-1` slugs | `/docs/authentication` (drop numeric suffixes) |
| `excerpt` frontmatter | `description` frontmatter |
| Hosted ReadMe images (`files.readme.io/...`) | Re-host or replace; do not depend on ReadMe CDN long-term |
| Changelog in ReadMe | `changelog/index.mdx` prepend pattern |

### Agent write targets (post-retarget)

| Change type | File(s) |
| --- | --- |
| New guide | `docs/<slug>.mdx` + add to `docs.json` Documentation group |
| API endpoint | `openapi/alvys.json` |
| MCP tool | `ai-agents/available-mcp-tools.mdx` |
| Release note | Prepend to `changelog/index.mdx` |
| Nav change | `docs.json` only |

## AI indexing

Mintlify auto-hosts `/llms.txt` and `/llms-full.txt` on deploy. A curated `llms.txt` at the repo root overrides the auto-generated index when present.

## Related repos

- [`alvysio/api-docs`](https://github.com/alvysio/api-docs) — ReadMe Public API docs (current production at docs.alvys.com)
- [`alvysio/backend`](https://github.com/alvysio/backend) — self-healing docs workflow (PR #36139)
