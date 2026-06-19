# BUG: skill unusable on claude.ai web — safety banner + stale version

> **Filed:** 2026-06-17 · **Reporter:** @azagreev · **Status:** RESOLVED — root cause corrected by experiment (see UPDATE)
> **Severity:** was "high"; downgraded — the banner is expected by-design behavior, not a defect

## UPDATE 2026-06-17 — verified root cause (supersedes RC-A below)

**Experiment:** the user packaged the **current** skill (which still contains ALL the bypass
content — `CAPTCHA_MODULE.md`, `captcha_research.md`, `bypass_paywall_research.md`, the
`solver.recaptcha(...)` snippet) into a zip and uploaded it directly via Claude Desktop
Customize → Skill. **Result: no banner; skill works.**

**Conclusion:** the "malicious conversation content" banner is **NOT triggered by the skill's
content.** It is the **standard Anthropic marketplace-trust warning** shown for *any*
third-party marketplace plugin ("Plugins installed from marketplaces are not controlled by
Anthropic… cannot verify that they will work as intended or that they won't change"). It is
tied to the **marketplace install/use route**, not to what the skill bundles. This is
**by-design, not a defect** — it cannot and should not be "fixed" by editing skill content.

→ **RC-A (below: bypass content → banner) is REFUTED.** Removing the CAPTCHA/paywall content
is therefore *not* a banner fix. (It may still be done later on two independent grounds — it
cannot execute on the apps, and per assistant policy it won't be maintained — but that is an
optional cleanup, not this bug's fix.)

→ **Workaround / fix that works today:** distribute via the **release zip** (direct
Customize → Skill upload). This both avoids the marketplace-trust banner *and* sidesteps the
stale-cache "old version" issue (RC-B) — the zip is always the current build. Asset:
`deep-research-skill-v1.5.0.zip` on the v1.5.0 GitHub release.

This is a textbook win for verifying the causal model before acting (pre-mortem T1).

---

## Original analysis (pre-experiment — RC-A now refuted, kept for the record)

## Symptom (as reported)

On claude.ai (web/desktop), the user cannot use the `deep-research-skill` plugin:

1. **An OLD version of the skill installs**, even though `main` is at v1.5.0.
2. When the user tries to run a prompt, claude.ai shows a red caution banner:
   > "Use caution before running this prompt. Malicious conversation content could
   > trick Claude into attempting harmful actions or sharing your data."

Screenshot context: the app's "Customize the deep-research-skill plugin for me based
on my company" compose box, with the caution banner underneath. (The "Claude Fable 5
is currently unavailable" line is an unrelated model-availability notice.)

## Repro

1. On claude.ai web/desktop, install `deep-research-skill` from the marketplace.
2. Observe the installed version is behind `main` (v1.5.0).
3. Open the plugin / start a prompt → red "malicious conversation content" banner.

## Investigation — facts gathered

| Check | Result |
|---|---|
| Version consistency on `main` | **Uniform v1.5.0** (`plugin.json`, `engine/__init__.py`, `SKILL.md`, `SKILL.master.md`). The repo is NOT inconsistent. |
| SKILL.md size | 54 KB / 738 lines. No documented hard cap for the apps (docs silent) — not a confirmed blocker. |
| Non-standard frontmatter keys (`version`, `runtime`, `requires_mcp`, `min_claude_version`) | **Ruled out** — unknown frontmatter keys are silently ignored (per Claude docs). |
| Bundled payload | 156 files, 51 `.py`, `engine/`, `tests/`, `.pytest_cache/`. Hygiene issue (tests/cache should not ship) but not the banner cause. |
| Host artifacts | `hooks/settings.example.json` — inert opt-in template (OK). |
| **Bypass / evasion content** | **`CAPTCHA_MODULE.md`** (CAPTCHA solver chains, residential proxies, "bypass >90% of CAPTCHA triggers"), **`references/captcha_research.md`** (26 bypass/solve matches), **`references/bypass_paywall_research.md`** (paywall bypass, anti-detect browsers CloakBrowser/Obscura, Cloudflare bypass via FlareSolverr), **`SKILL.master.md:2341`** literal `solver.recaptcha(sitekey="6Ld...")`. Also captcha/anti-detect bits in `browserbase_research.md`, `cost_matrix_full.md`, `tool_matrix.md`. |

External grounding:
- Stale-version class: Claude Code marketplace cache is not git-fetched before version
  compare — [#46081](https://github.com/anthropics/claude-code/issues/46081),
  [#16866](https://github.com/anthropics/claude-code/issues/16866),
  [#35752](https://github.com/anthropics/claude-code/issues/35752). Docs are silent on the
  apps specifically, but the behavior is analogous; force-refresh = uninstall/reinstall or
  `marketplace update`.
- Safety principle: Claude is designed to **respect** CAPTCHA / bot-detection, not bypass
  it ([Claude Code security](https://code.claude.com/docs/en/security)); the community
  marketplace runs automated safety screening.

## Root cause

**Two independent causes behind one report:**

- **RC-A (the blocker — banner):** The shipped skill bundles explicit **access-control
  circumvention** material — CAPTCHA solving, anti-bot/anti-fingerprint evasion, and
  paywall bypass — including runnable solver code. claude.ai's safety classifier flags this
  content as "malicious," surfacing the caution banner and making the skill unusable. This
  also violates the assistant's own operating policy (bypassing CAPTCHA / bot-detection is
  prohibited; circumventing access controls is disallowed).

- **RC-B (the "old version"):** Marketplace cache staleness on the client, not a repo
  problem (`main` is uniformly v1.5.0). Operational fix, not a code change.

## Fix plan

**For RC-A (code/content — the real fix):**
1. Remove the bypass-oriented files from the shipped skill:
   - `CAPTCHA_MODULE.md`
   - `references/captcha_research.md`
   - `references/bypass_paywall_research.md`
2. Scrub CAPTCHA-solver / anti-detect / paywall-bypass passages (incl. the live
   `solver.recaptcha(...)` snippet) from `SKILL.master.md`, `SKILL.md`,
   `references/browserbase_research.md`, `references/cost_matrix_full.md`,
   `references/tool_matrix.md`, and fix any dangling links to the deleted files.
3. Replace with the compliant stance (already implied by the module's own decision
   hierarchy): **if a source requires CAPTCHA / login / paywall, treat it as inaccessible —
   prefer the official API, an open/archive mirror, or an alternative authoritative source.**
4. Drop `.pytest_cache/` (and reconsider shipping `tests/`) from the bundle; add to
   `.gitignore` / packaging ignore.
5. Re-run engine suite + trust scorecard; version bump (ritual: 7 files + CHANGELOG +
   TECHDEBT) → v1.5.1 (or v1.6.0 if treated as scope change); `/code-review` → merge →
   release.

**For RC-B (operational — user side):**
- Force the app to refetch: uninstall the plugin, refresh/re-add the marketplace, reinstall;
  confirm the installed version reads v1.5.x. (No repo change required; consider documenting
  this in README troubleshooting.)

## Open questions
- Treat the CAPTCHA/paywall removal as patch (v1.5.1) or minor (v1.6.0)?
- Keep `tests/`+`engine/` in the shipped bundle (prose-only fallback doesn't need them on
  the apps), or split a lean "apps" build from the full "CLI" build?
