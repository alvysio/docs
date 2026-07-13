# Alvys API documentation — agent instructions

Documentation site for the Alvys Public API and MCP server, built on [Mintlify](https://mintlify.com).

## About this project

- **Publish target:** [alvys.mintlify.io](https://alvys.mintlify.io/) (Mintlify POC)
- **Pages:** MDX with YAML `title` and `description` frontmatter
- **Config:** `docs.json` (branding, navigation tabs, OpenAPI binding)
- **API reference:** Auto-generated from `openapi/alvys.json` — do not hand-author endpoint MDX unless adding `x-mint: content` in the spec

Install the Mintlify skill for component reference:

```bash
npx skills add https://mintlify.com/docs
```

## Terminology

- **Public API** — REST API at `https://integrations.alvys.com/api/p/v{version}/`
- **MCP server** — Model Context Protocol gateway at `https://mcp.alvys.com/mcp`
- **Scope** — OAuth permission in `{resource}:{action}` form (e.g. `load:read`)
- **Tenant** — Alvys company; resolved from the token, never from user/agent input

## Repository conventions

| Area | Path |
| --- | --- |
| Guides | `docs/*.mdx` |
| MCP | `ai-agents/*.mdx` |
| Changelog | `changelog/index.mdx` (prepend new entries) |
| OpenAPI spec | `openapi/alvys.json` |
| Navigation | `docs.json` |

## Style preferences

- Active voice, second person ("you")
- Sentence case for headings
- Bold for UI elements: Click **Settings**
- Code formatting for file names, commands, paths, and identifiers
- Use `<Note>`, `<Warning>`, and `<Tip>` for callouts — not ReadMe-style emoji blockquotes

## Content boundaries

- Document only the **Public API** and **MCP** surfaces — not internal Alvys admin UI or private endpoints
- Do not document unreleased write endpoints as available; match scope table caveats in Authentication
- MCP write tools are disabled during beta — mark them Write tier in the catalog

## Self-healing agent handoff

When the backend `docs-sync` workflow retargets from `alvysio/api-docs` to this repo:

1. **Changelog:** prepend to `changelog/index.mdx`
2. **MCP tools:** update tables in `ai-agents/available-mcp-tools.mdx`
3. **Guides:** add or edit `docs/<slug>.mdx`; register in `docs.json`
4. **Endpoints:** update `openapi/alvys.json` (source of truth today: `alvysio/api-docs/reference/alvys.json`)
5. **ReadMe deltas:** see README § "ReadMe → Mintlify format deltas"

## Mintlify MCP (optional)

- Content MCP: `https://mcp.mintlify.com`
- Docs MCP: `https://www.mintlify.com/docs/mcp`
