# Alvys documentation

Documentation site for the Alvys Public API, MCP server, and Help Center, built on [Mintlify](https://mintlify.com) and published to [alvys.mintlify.io](https://alvys.mintlify.io/).

For authoring conventions, repository layout, and the self-healing `docs-sync` handoff, see [`AGENTS.md`](AGENTS.md).

---

## Access control (authenticated docs)

Some pages are gated so that only certain signed-in users can see them. This section explains **how that gating is wired end to end** and **how to change it** — read it before you add a `groups:` frontmatter or touch the Auth0 login flow.

> [!IMPORTANT]
> Access control spans **three systems**: the Auth0 login Action (in `infra-setup`), the Mintlify dashboard OAuth config, and page frontmatter in this repo. A change is only complete when all three agree. Tracked under **SCA-5275**.

### How a user gets their groups

```
Browser → Mintlify (OAuth) → Auth0 `mintlify` client → TokenClaims post-login Action
                                                              │
                                    stamps ID-token claim:    ▼
                         https://alvys.com/claims/app/groups = ["authenticated", "alvys_employees", ...]
                                                              │
        Mintlify reads that claim (Token claims → Source: id_token) ▼
                         user.groups = [...]  →  page `groups:` frontmatter decides visibility
```

1. A reader signs in through Mintlify's OAuth flow, which uses a **dedicated confidential Auth0 client** named `mintlify` (not the `user_web` SPA — that client has no secret and can't be used for a server-side code exchange).
2. Auth0's **`TokenClaims` post-login Action** runs. For the Mintlify client it stamps a single namespaced array claim on the **ID token**:

   **`https://alvys.com/claims/app/groups`**

3. Mintlify is configured (dashboard → Authentication → OAuth → **Token claims**) to read that claim, with **Source = `id_token`**, and exposes it as `user.groups`.
4. Each page's `groups:` frontmatter is checked against `user.groups`. A user must be in **at least one** listed group; otherwise the page 404s.

### The groups we emit

The Action derives the array from the user's Alvys tenants (via the internal `GetInternalUser` enrichment call). Values:

| Group | Meaning | Example |
| --- | --- | --- |
| `authenticated` | Every signed-in docs user (always present) | `authenticated` |
| `alvys_employees` | Any `@alvys.com` user — internal-only docs | `alvys_employees` |
| `ccd:<CompanyCode>` | One per tenant company code — per-tenant docs | `ccd:ACME` |
| `role:<Role>` | One per distinct tenant role | `role:Admin` |
| `tier:<Tier>` | One per distinct tenant subscription tier | `tier:growth` |

> [!NOTE]
> The claim is a single combined array so a page can be gated on any dimension (employee, tenant, role, tier) from one claim — Mintlify maps exactly one claim path to groups. It **fails open** to `authenticated` (plus `alvys_employees` for staff) if the enrichment call is unavailable, so a login is never blocked by an API blip.

### How to gate a page

Add `groups:` to the page frontmatter — the user needs one of the listed groups:

```mdx
---
title: "Internal runbook"
groups: ["alvys_employees"]
---
```

Gate to a specific tenant, or to admins of any tenant:

```mdx
---
groups: ["ccd:ACME", "role:Admin"]
---
```

Other visibility controls:

- **A page with no `groups:`** is visible to every authenticated user.
- **`public: true`** in frontmatter makes a page viewable without signing in (needed only under *partial* authentication).
- A whole nav group can be gated or made public in [`docs.json`](docs.json).

### How to change the group taxonomy

The group values are produced by the Auth0 Action, **not** in this repo. To add, rename, or change a group:

1. Edit the `handleMintlifyLogin` function in **`infra-setup`**:
   - `auth0/alvys-prod/actions/token-claims.js`
   - `auth0/alvys-qa/actions/token-claims.js` (keep both in sync)
2. `terraform plan` **QA first**, apply, verify, then prod — per the auth0 stack convention.
3. If you introduce a group value, update the table above and any `groups:` frontmatter that should use it.

The claim name and Mintlify's Token-claims mapping must stay identical — changing the claim path requires a matching change in the Mintlify dashboard.

### How to validate

Sign in and open the debug page **in a browser**:

**`/debug/whoami`** ([debug/whoami.mdx](debug/whoami.mdx))

It renders the live `user` object — confirm `groups` contains what you expect.

> [!WARNING]
> Validate on the **rendered** page only. The `.md` / `llms.txt` export (e.g. `alvys.mintlify.site/debug/whoami.md`) is static markdown and **never evaluates** the MDX expressions, so it always shows "no user in scope" regardless of auth. That is not a bug.

### Configuration checklist (one-time, per environment)

Auth flow only works when all of these are in place:

- [ ] `mintlify` Auth0 client provisioned (`infra-setup` — already done for prod/qa under SCA-5275)
- [ ] `TokenClaims` Action deployed with the Mintlify branch (`infra-setup` PR — stamps `…/app/groups`)
- [ ] `mintlify` client **secret** pulled from Auth0 → key vault → Mintlify dashboard
- [ ] Mintlify dashboard → Authentication → OAuth configured: authorization/token URLs, client id + secret, and **Token claims** = `https://alvys.com/claims/app/groups`, **Source** = `id_token`
- [ ] Verified on rendered `/debug/whoami` while logged in

### Where things live

| Concern | Location |
| --- | --- |
| Auth0 `mintlify` client | `infra-setup` → `auth0/modules/tenant/applications.tf` |
| Groups-claim logic | `infra-setup` → `auth0/alvys-{prod,qa}/actions/token-claims.js` (`handleMintlifyLogin`) |
| Claim name | `https://alvys.com/claims/app/groups` |
| Mintlify OAuth + Token-claims mapping | Mintlify dashboard (not in git) |
| Page gating | `groups:` frontmatter in `*.mdx`; nav groups in `docs.json` |
| Debug / validation | `debug/whoami.mdx` → `/debug/whoami` |
