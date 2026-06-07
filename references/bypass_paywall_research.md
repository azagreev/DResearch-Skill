# Deep Research Skill: Paywall Bypass Tools Research

> **Research Date:** 2025  
> **Purpose:** Evaluate tools and techniques for accessing premium content (WSJ, FT, Economist, etc.) for AI-powered deep research  
> **Status:** For research and educational purposes only

---

## Table of Contents

1. [Executive Summary](#1-executive-summary)
2. [Bypass Paywalls Chrome (Primary Reference)](#2-bypass-paywalls-chrome-primary-reference)
3. [Other GitHub Repositories](#3-other-github-repositories)
4. [Self-Hosted Solutions](#4-self-hosted-solutions)
5. [Archive-Based Approaches](#5-archive-based-approaches)
6. [Browser Automation Tools](#6-browser-automation-tools)
7. [Legal & Ethical Considerations](#7-legal--ethical-considerations)
8. [Integration Recommendations for Deep Research Skill](#8-integration-recommendations-for-deep-research-skill)
9. [Appendix: Supported Sites Reference](#9-appendix-supported-sites-reference)

---

## 1. Executive Summary

This report evaluates paywall bypass tools for integration into a "Deep Research Skill" for Claude Desktop. The research covers browser extensions, self-hosted proxies, archive services, and headless browser automation.

### Key Findings

| Finding | Impact |
|---------|--------|
| **Bypass Paywalls Chrome** was DMCA-banned by GitHub in August 2024 | Original repo unavailable; forks exist but are legally risky |
| **Ladder** (self-hosted proxy) is the most mature open-source alternative | 8k+ stars, active Go-based project with rulesets |
| **Archive.today** + **Wayback Machine** are the most legally safe methods | High reliability for news content, no circumvention |
| **FlareSolverr** + **Ladder** can handle Cloudflare-protected sites | Adds latency but effective for bot detection |
| **CloakBrowser/Obscura** represent state-of-the-art anti-detection | Useful for sites with advanced fingerprinting |
| **Wallabag** with credentials is the only fully legal paywall access method | Requires actual subscription credentials |
| **DMCA Section 1201** makes most bypass tools illegal in the US | Tools that circumvent TPM are legally hazardous |

### Recommended Fallback Chain

```
1. wallabag (with credentials) → 2. archive.today → 3. Wayback Machine → 
4. Ladder (self-hosted) → 5. CloakBrowser/Obscura (headless)
```

---

## 2. Bypass Paywalls Chrome (Primary Reference)

### 2.1 Overview

**Repository:** `iamadamdev/bypass-paywalls-chrome` (now banned on GitHub)  
**License:** MIT (originally)  
**Status:** DMCA takedown by News Media Alliance (NMA) in August 2024  
**Mirrors:** Available on GitFlic, GitLab, and various forks

### 2.2 Architecture

The extension uses **Manifest V2/V3** with the following components:

```
manifest.json          → Extension configuration, site permissions
src/js/background.js   → Service worker: request interception, header modification
src/js/contentScript.js→ DOM manipulation, paywall removal
src/js/sites.js        → Site-specific bypass rules (160+ domains)
```

### 2.3 How It Works

| Technique | Mechanism | Effectiveness |
|-----------|-----------|---------------|
| **User-Agent Spoofing** | Replaces browser UA with Googlebot/Bingbot | High for soft paywalls |
| **Cookie Clearing** | Removes tracking cookies on page load | High for metered paywalls |
| **Referrer Spoofing** | Sets referer to Google, Facebook, or Twitter | Medium |
| **General Paywall Bypass** | Blocks common paywall JavaScript files | Medium |
| **AMP Page Redirect** | Redirects to AMP version of article | Medium |
| **JSON Text Loading** | Loads article text from JSON endpoint | Site-specific |
| **Cookie Remover** | One-click cookie clearing for unsupported sites | Manual |
| **DOM Manipulation** | Removes paywall overlays via content script | Medium |

### 2.4 Technical Details

**Content Script Execution:**
- Runs at `document_start` or `document_idle` depending on site
- Modifies DOM to remove paywall elements (`.paywall`, `.overlay`, etc.)
- Injects CSS to unhide article content

**Background Script:**
- Intercepts HTTP requests via `webRequest` API (MV2) or `declarativeNetRequest` (MV3)
- Modifies headers: `User-Agent`, `Referer`, `X-Forwarded-For`
- Clears cookies for target domains after page load

**Site Configuration (sites.js):**
```javascript
// Example entry structure (inferred from documentation)
{
  domain: "wsj.com",
  allowCookies: true,
  userAgent: "googlebot",
  referer: "facebook",
  regexCleanup: ["<div class=\"paywall\">"],
  amp: true
}
```

### 2.5 Supported Sites (160+ domains)

**Tier 1 — Major Financial/Business (High Priority for Research):**

| Site | Domain | Method | Status |
|------|--------|--------|--------|
| Wall Street Journal | wsj.com | Googlebot UA + cookie clear | Working |
| Financial Times | ft.com | Referrer spoof + UA | Working |
| The Economist | economist.com | Cookie clear + general bypass | Working |
| Bloomberg | bloomberg.com | UA spoofing | Working |
| Harvard Business Review | hbr.org | Googlebot UA | Working |
| MIT Technology Review | technologyreview.com | General bypass | Working |

**Tier 2 — Major News:**

| Site | Domain | Notes |
|------|--------|-------|
| The New York Times | nytimes.com | Metered paywall |
| The Washington Post | washingtonpost.com | Soft paywall |
| The Atlantic | theatlantic.com | Works well |
| The New Yorker | newyorker.com | Consistent |
| Wired | wired.com | General bypass |

**Full list available in Appendix A.**

### 2.6 Limitations

1. **Hard Paywalls**: Premium-only content (account-required) cannot be bypassed
2. **JavaScript-dependent paywalls**: Some sites load content dynamically post-auth
3. **Fingerprinting**: Advanced sites detect UA spoofing via JS fingerprinting
4. **Legal Risk**: Tool itself is a DMCA violation (circumventing TPM)
5. **Maintenance**: Requires constant updates as sites change detection methods
6. **Login required**: Cannot bypass paywalls requiring active subscription login

### 2.7 Adaptability for AI Agents

| Aspect | Assessment |
|--------|------------|
| **Extract as library** | Possible — core logic is JS, can be ported to Node/Python |
| **Headless integration** | Content scripts can run in Puppeteer/Playwright |
| **Header modification** | Easily replicable in any HTTP client |
| **Cookie management** | Standard in browser automation tools |
| **Maintenance burden** | HIGH — requires active ruleset updates |
| **Legal risk** | HIGH — DMCA circumvention |

**Conclusion:** The *techniques* are valuable for an AI agent, but using the extension *as-is* is not recommended due to legal risks. Re-implementing the header/cookie techniques in a research context may be defensible.

---

## 3. Other GitHub Repositories

### 3.1 Comparative Table

| Repository | Language | Type | Status | Stars | Pros | Cons |
|------------|----------|------|--------|-------|------|------|
| **bypass-paywalls-chrome** | JS | Browser Ext | Banned (DMCA) | 3.8k (was) | Most comprehensive, 160+ sites | Illegal, unmaintained |
| **bypass-paywalls-clean** | JS | Browser Ext | Active forks | 2k+ | Weekly updates, Firefox support | Same legal issues |
| **bypass-paywalls-chrome-clean-magnolia1234** | JS | Browser Ext | Active | 1k+ | Custom sites, cookie remover | DMCA risk |
| **Ladder** | Go | Self-hosted proxy | Active | 8k+ | Rulesets, API, CORS removal | Requires hosting |
| **13ft** | Python | Self-hosted | Active | 500+ | Simple, Googlebot spoofing | Less mature than Ladder |
| **SMRY.ai** | JS/TS | Web service | Active | 200+ | AI summaries, multi-method | Requires API key |
| **wallabag** | PHP | Self-hosted app | Active | 10k+ | Legal (with credentials), full content | Requires subscription |
| **article-paywall-bypass** | JS | Chrome Ext | Stale | 100 | Simple WSJ/NYT/FT/Bloomberg | Very limited |

### 3.2 Key Forks and Alternatives

**Bypass Paywalls Clean (BPC)**
- Repository: `magnolia1234/bypass-paywalls-chrome-clean`
- More aggressive updates than original
- Supports custom sites with regex rules
- Blocked from Chrome Web Store
- Weekly releases with new site support

**13ft**
- Repository: `wasi-master/13ft`
- Simple Python Flask server
- Multi-source fallback approach
- Spoofs GoogleBot, uses archive.org
- Docker available

---

## 4. Self-Hosted Solutions

### 4.1 Ladder (Recommended)

**Repository:** `everywall/ladder`  
**Language:** Go  
**License:** GPL-3.0  
**Stars:** 8k+

#### Architecture

```
sequenceDiagram
    client->>+ladder: GET /https://example.com/article
    ladder-->>ladder: Apply RequestModifications (ruleset)
    ladder->>+website: GET article (modified headers)
    website->>-ladder: 200 OK (full content)
    ladder-->>ladder: Apply ResultModifications (injections)
    ladder->>-client: 200 OK (clean article)
```

#### Features

| Feature | Description |
|---------|-------------|
| **Rulesets** | YAML-based domain-specific rules |
| **Header Modification** | Custom User-Agent, X-Forwarded-For, Referer, CSP |
| **CORS Removal** | Strips CORS headers for API proxy usage |
| **HTML Injection** | Inject/remove CSS, JS, HTML elements |
| **FlareSolverr Integration** | Cloudflare bypass support |
| **API Endpoints** | `/api/URL` for JSON, `/raw/URL` for HTML |
| **Basic Auth** | Protect public instances |
| **TOR Support** | Optional TOR proxy routing |

#### Ruleset Configuration

```yaml
# Example ruleset.yaml
- domain: example.com
  headers:
    user-agent: "Mozilla/5.0 (compatible; Googlebot/2.1; +http://www.google.com/bot.html)"
    referer: "https://www.google.com"
    x-forwarded-for: "66.249.66.1"
  regexRules:
    - match: '<script[^>]*src="/paywall\.js"[^>]*></script>'
      replace: ""
  injections:
    - position: head
      append: |
        <style>.paywall-overlay { display: none !important; }</style>
    
- domain: cloudflare-site.com
  useFlareSolverr: true
  headers:
    user-agent: "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
```

#### Deployment

```bash
# Docker (simple)
docker run -p 8080:8080 -d \
  --env RULESET=https://raw.githubusercontent.com/everywall/ladder-rules/main/ruleset.yaml \
  --name ladder ghcr.io/everywall/ladder:latest

# Docker Compose (with FlareSolverr)
curl https://raw.githubusercontent.com/everywall/ladder/main/docker-compose.yaml -o docker-compose.yaml
docker-compose up -d

# Binary
./ladder -r https://raw.githubusercontent.com/everywall/ladder-rules/main/ruleset.yaml
```

#### API Usage

```bash
# Fetch article as JSON
curl -X GET "http://localhost:8080/api/https://www.ft.com/article"

# Fetch raw HTML
curl -X GET "http://localhost:8080/raw/https://www.wsj.com/article"

# Browser access
open "http://localhost:8080/https://www.economist.com/article"
```

#### Assessment for AI Agents

| Criterion | Rating | Notes |
|-----------|--------|-------|
| Reliability | ★★★★☆ | Ruleset-dependent, community-maintained |
| Speed | ★★★★★ | Go-based, very fast |
| Legal risk | ★★★☆☆ | Self-hosted = lower risk; still circumvention |
| Maintenance | ★★★☆☆ | Requires ruleset updates |
| Integration | ★★★★★ | Clean API, JSON output |
| Cost | ★★★★★ | Free, self-hosted |

### 4.2 13ft

**Repository:** `wasi-master/13ft`  
**Language:** Python (Flask)  
**Approach:** GoogleBot impersonation + multi-source fallback

```bash
# Docker
docker run -d -p 5000:5000 wasimaster/13ft:latest

# Access
curl "http://localhost:5000/article?url=https://example.com/article"
```

**Pros:** Simple, lightweight  
**Cons:** Less mature than Ladder, fewer configuration options

### 4.3 Wallabag (Legal Option)

**Repository:** `wallabag/wallabag`  
**Language:** PHP  
**License:** MIT  
**Stars:** 10k+

**Key Feature:** Can access paywalled content using *your own subscription credentials*:

```php
// Site credentials are encrypted in database
// Supports: The Economist, Le Monde, Mediapart, LWN.net, etc.
```

**Supported Paywall Sites with Credentials:**
- Alternatives Economiques
- Arret sur Images
- Canard PC
- Courrier International
- GameKult
- Le Figaro, Le Monde, Le Monde Diplomatique
- Le Point
- LWN.net
- Mediapart
- Next INpact
- Reflets.info
- The Economist

**Pros:** Fully legal (you have subscription), self-hosted, excellent content extraction  
**Cons:** Requires actual paid subscriptions

---

## 5. Archive-Based Approaches

### 5.1 Wayback Machine (archive.org)

**API:** `https://web.archive.org/web/2/<URL>`  
**CDX API:** `https://web.archive.org/cdx/search/cdx?url=<URL>&output=json`

#### How It Works
- Archives crawl as search bots, storing full article text
- Strips dynamic paywall JavaScript
- Returns static HTML snapshot

#### API Examples

```bash
# Check if URL is archived
curl "https://web.archive.org/cdx/search/cdx?url=ft.com/article&output=json"

# Get archived snapshot
curl -L "https://web.archive.org/web/2/https://ft.com/article"

# Get oldest snapshot
curl -L "https://web.archive.org/web/0/https://ft.com/article"

# Get snapshot closest to date
curl -L "https://web.archive.org/web/20240101/https://ft.com/article"

# Save page now
curl -X POST "https://web.archive.org/save/https://example.com/article"
```

#### Assessment

| Criterion | Rating | Notes |
|-----------|--------|-------|
| Reliability | ★★★★☆ | Many major articles archived |
| Speed | ★★★☆☆ | Can be slow; CDN helps |
| Legal risk | ★★★★★ | Completely legal |
| Coverage | ★★★☆☆ | Not all articles archived |
| Freshness | ★★☆☆☆ | May be hours/days behind |

### 5.2 Archive.today / Archive.is / Archive.ph

**URLs:**
- `https://archive.today`
- `https://archive.is`
- `https://archive.ph`

**Features:**
- On-demand archiving (creates snapshot on request)
- JavaScript-free output
- Often bypasses paywalls that Wayback Machine doesn't
- No API — requires browser automation or form submission

```bash
# Direct access to archived page
curl "https://archive.today/latest/https://example.com/article"

# Note: Archive.today has anti-bot protection
# Best accessed via headless browser or Ladder proxy
```

#### Assessment

| Criterion | Rating | Notes |
|-----------|--------|-------|
| Reliability | ★★★★★ | Best archive for paywalled content |
| Speed | ★★★☆☆ | Requires on-demand archiving |
| Legal risk | ★★★★★ | Completely legal |
| Coverage | ★★★★☆ | Creates snapshot on demand |
| Anti-bot | N/A | Blocks automated access |

### 5.3 Google Cache

**URL:** `https://webcache.googleusercontent.com/search?q=cache:<URL>`

**Note:** Google has reduced cache availability; many publishers now disable caching.

### 5.4 Other Archives

| Service | URL | Notes |
|---------|-----|-------|
| **GhostArchive** | ghostarchive.org | Growing alternative |
| **MementoWeb** | mementoweb.org | Aggregates multiple archives |
| **UK Web Archive** | webarchive.org.uk | UK-focused |
| **Stanford Web Archive** | webarchive.stanford.edu | Academic focus |

### 5.5 Archive Comparison

| Service | Coverage | Freshness | API | Paywall Bypass | Legal |
|---------|----------|-----------|-----|----------------|-------|
| Wayback Machine | ★★★★☆ | ★★☆☆☆ | Yes | ★★★☆☆ | ✅ Legal |
| Archive.today | ★★★★☆ | ★★★★★ | No | ★★★★★ | ✅ Legal |
| Google Cache | ★★☆☆☆ | ★★★☆☆ | No | ★★☆☆☆ | ✅ Legal |
| GhostArchive | ★★☆☆☆ | ★★★☆☆ | Limited | ★★★☆☆ | ✅ Legal |

---

## 6. Browser Automation Tools

### 6.1 CloakBrowser (Top-Tier Anti-Detection)

**Repository:** `CloakHQ/CloakBrowser`  
**Type:** Custom Chromium build with C++ patches  
**License:** MIT

#### Key Features
- **58 source-level C++ patches** for WebGL, canvas, audio, fonts, GPU, screen
- **`humanize=True`** — human-like mouse curves, keyboard timing
- **0.9 reCAPTCHA v3 score** (server-verified)
- Passes Cloudflare Turnstile, FingerprintJS, BrowserScan
- Drop-in Playwright/Puppeteer replacement

```python
# Python usage
from cloakbrowser import launch

browser = launch(
    proxy="http://user:pass@residential-proxy:port",
    geoip=True,
    headless=False,
    humanize=True,
)
page = browser.new_page()
page.goto("https://wsj.com/article")
content = page.content()
```

```javascript
// JavaScript usage
import { launch } from 'cloakbrowser';

const browser = await launch({
    proxy: 'http://proxy:port',
    geoip: true,
    humanize: true
});
const page = await browser.newPage();
await page.goto('https://ft.com/article');
```

#### Detection Test Results

| Detection Service | CloakBrowser | Standard Playwright |
|-------------------|--------------|---------------------|
| Bot.Sannysoft | ✅ Pass | ❌ Fail |
| Pixelscan | ✅ Pass | ❌ Fail |
| BrowserScan | ✅ Pass | ❌ Fail |
| Cloudflare WAF | ✅ Partial | ❌ Fail |

### 6.2 Obscura (Lightweight Alternative)

**Repository:** `h4ckf0r0day/obscura`  
**Type:** Rust-based V8 headless browser  
**License:** Apache 2.0

#### Specifications

| Metric | Obscura | Headless Chrome |
|--------|---------|-----------------|
| Memory | 30 MB | 200+ MB |
| Binary Size | 70 MB | 300+ MB |
| Page Load | 85 ms | ~500 ms |
| Startup | Instant | ~2s |
| Anti-detect | Built-in | None |

#### MCP Server for AI Agents

Obscura includes a Model Context Protocol (MCP) server:

```bash
# Start MCP server for Claude Desktop
obscura mcp

# Claude Desktop config
{
  "mcpServers": {
    "obscura": {
      "command": "obscura",
      "args": ["mcp"]
    }
  }
}
```

**Available MCP Tools:**
- `browser_navigate` — Navigate to URL
- `browser_snapshot` — Get page content
- `browser_click` / `browser_fill` / `browser_type` — Interactions
- `browser_evaluate` — Execute JavaScript
- `browser_network_requests` — List network requests

### 6.3 FlareSolverr (Cloudflare Bypass)

**Purpose:** Bypass Cloudflare and DDoS-Guard challenges  
**Integration:** Works with Ladder, or standalone

```bash
# Docker
docker run -d \
  --name flaresolverr \
  -p 8191:8191 \
  ghcr.io/flaresolverr/flaresolverr:latest

# API usage
curl -L -X POST 'http://localhost:8191/v1' \
  -H 'Content-Type: application/json' \
  -d '{
    "cmd": "request.get",
    "url": "https://example.com",
    "maxTimeout": 60000
  }'
```

### 6.4 Comparison Matrix

| Tool | Type | Memory | Anti-Detect | CDP | MCP | Best For |
|------|------|--------|-------------|-----|-----|----------|
| **CloakBrowser** | Chromium build | ~200 MB | ★★★★★ | Yes | No | Maximum stealth, hard targets |
| **Obscura** | Rust V8 | ~30 MB | ★★★★☆ | Yes | Yes | AI agents, high concurrency |
| **Playwright** | Standard | ~200 MB | None | Yes | No | General automation |
| **Puppeteer** | Standard | ~200 MB | Minimal | Yes | No | Chrome-specific |
| **FlareSolverr** | Selenium | ~400 MB | Cloudflare only | No | No | Cloudflare bypass |

### 6.5 Headless Browser Tricks for Paywalls

```python
# Playwright with paywall bypass techniques
from playwright.sync_api import sync_playwright

with sync_playwright() as p:
    browser = p.chromium.launch(
        headless=True,
        args=['--disable-blink-features=AutomationControlled']
    )
    context = browser.new_context(
        user_agent='Mozilla/5.0 (compatible; Googlebot/2.1; +http://www.google.com/bot.html)',
        viewport={'width': 1920, 'height': 1080},
        java_script_enabled=True
    )
    
    # Clear cookies before each request
    context.clear_cookies()
    
    page = context.new_page()
    
    # Set referer
    page.set_extra_http_headers({
        'Referer': 'https://www.google.com/search?q=article'
    })
    
    page.goto('https://wsj.com/article')
    content = page.content()
```

---

## 7. Legal & Ethical Considerations

### 7.1 US Legal Framework

#### Digital Millennium Copyright Act (DMCA) — Section 1201

> *"No person shall circumvent a technological measure that effectively controls access to a work protected under this title."*

**Impact on Tools:**
- **Bypass Paywalls Chrome** was explicitly targeted under DMCA §1201
- News Media Alliance (NMA) filed complaint in August 2024
- GitHub removed 3,879 repositories containing the tool
- **Circumvention of technological protection measures (TPMs)** is the key violation

#### Computer Fraud and Abuse Act (CFAA)

- Bypassing paywalls may constitute "unauthorized access" to computer systems
- Criminal penalties possible (though rarely enforced against individual users)
- More likely to target tool distributors than end users

#### Copyright Infringement

- Accessing content without authorization may violate copyright
- Fair use doctrine may apply for research/educational purposes
- Transformative use (summarization, analysis) strengthens fair use argument

### 7.2 International Considerations

| Jurisdiction | Relevant Law | Key Points |
|--------------|--------------|------------|
| **United States** | DMCA §1201, CFAA | Circumvention illegal; criminal penalties possible |
| **EU** | Copyright Directive Art. 6 | Similar anti-circumvention provisions |
| **Canada** | Copyright Act §41 | Technological Protection Measures (TPMs) prohibited |
| **UK** | Copyright, Designs and Patents Act | Circumvention of "effective technological measures" |

### 7.3 Legal vs. Illegal Methods

| Method | Legal Status | Risk Level |
|--------|-------------|------------|
| **Archive.org / Archive.today** | ✅ Legal | None |
| **Wallabag with own credentials** | ✅ Legal | None |
| **Reader mode** | ✅ Legal | None |
| **Google Cache** | ✅ Legal | None |
| **Library access (PressReader)** | ✅ Legal | None |
| **User-Agent switching** | ⚠️ Gray area | Low-Medium |
| **Cookie clearing** | ⚠️ Gray area | Low |
| **Bypass Paywalls extension** | ❌ Illegal (DMCA) | High for distributors |
| **Ladder proxy** | ❌ Illegal (DMCA) | Medium |
| **13ft** | ❌ Illegal (DMCA) | Medium |
| **Credential sharing** | ❌ Illegal | High |

### 7.4 Terms of Service Violations

All major publishers explicitly prohibit paywall circumvention in their ToS:

> *"You may not circumvent, disable, or otherwise interfere with security-related features of the Services."* — WSJ Terms

**Note:** ToS violations are civil matters, not criminal. Publishers can:
- Block IP addresses
- Terminate accounts
- Pursue civil litigation (rare for individual users)

### 7.5 Ethical Considerations

1. **Journalism funding**: Paywalls support investigative journalism
2. **Information access**: Restricted access may harm research and education
3. **Selective enforcement**: Publishers often tolerate limited bypass for SEO/social sharing
4. **Fair use**: Research, commentary, and transformative use are protected

### 7.6 Recommendations for Legal Compliance

1. **Prefer archives** (Wayback Machine, Archive.today) — completely legal
2. **Use wallabag with credentials** — fully compliant
3. **Library access** — many libraries provide free access to WSJ, FT, Economist
4. **Free article allowances** — many sites offer 3-5 free articles/month
5. **Subscribe to essential sources** — support quality journalism
6. **Document fair use purpose** — research, analysis, transformative use

---

## 8. Integration Recommendations for Deep Research Skill

### 8.1 Recommended Fallback Chain

```
┌─────────────────────────────────────────────────────────────────┐
│                    PAYWALL BYPASS PIPELINE                       │
├─────────────────────────────────────────────────────────────────┤
│                                                                  │
│  STEP 1: LEGAL METHODS (Always Try First)                        │
│  ├── Wallabag (with credentials if available)                    │
│  ├── Archive.today (on-demand snapshot)                          │
│  └── Wayback Machine (existing snapshots)                        │
│                                                                  │
│  STEP 2: AUTOMATED EXTRACTION (If legal methods fail)            │
│  ├── Ladder (self-hosted proxy with ruleset)                     │
│  └── General UA spoof + cookie clear                             │
│                                                                  │
│  STEP 3: HEADLESS BROWSER (For hard targets)                     │
│  ├── Obscura (MCP-native, anti-detect)                           │
│  └── CloakBrowser (maximum stealth)                              │
│                                                                  │
│  STEP 4: CONTENT EXTRACTION (From retrieved HTML)                │
│  ├── Readability.js / Mozilla Readability                        │
│  └── Custom extraction rules                                     │
│                                                                  │
└─────────────────────────────────────────────────────────────────┘
```

### 8.2 Priority / Reliability / Cost Matrix

| Tool | Priority | Reliability | Cost | Speed | Legal Risk | Best For |
|------|----------|-------------|------|-------|------------|----------|
| **Wallabag** | P1 | ★★★★★ | Free* | Fast | None | Paid subs you own |
| **Archive.today** | P1 | ★★★★★ | Free | Medium | None | Breaking news |
| **Wayback Machine** | P2 | ★★★★☆ | Free | Slow | None | Historical content |
| **Ladder** | P3 | ★★★★☆ | Free | Fast | Medium | API integration |
| **Obscura** | P4 | ★★★★☆ | Free | Fast | Medium | AI agent native |
| **CloakBrowser** | P4 | ★★★★★ | Free | Medium | Medium | Maximum stealth |
| **FlareSolverr** | P5 | ★★★☆☆ | Free | Slow | Medium | Cloudflare sites |

*Wallabag free; subscription credentials required for paywall content

### 8.3 Proposed Integration Architecture

```python
# Pseudo-code for Deep Research Skill integration

class PaywallBypassPipeline:
    def __init__(self):
        self.ladder = LadderClient("http://localhost:8080")
        self.wallabag = WallabagClient(url, client_id, secret)
        self.obscura = ObscuraMCPClient()  # MCP native
        
    async def fetch_article(self, url: str) -> Article:
        # Step 1: Try wallabag (if credentials available)
        if self.wallabag.has_credentials_for(url):
            return await self.wallabag.fetch(url)
            
        # Step 2: Try archives (legal, reliable)
        for archive in [archive_today, wayback_machine]:
            result = await archive.fetch(url)
            if result:
                return result
                
        # Step 3: Try Ladder proxy
        result = await self.ladder.fetch(url)
        if result and not result.has_paywall:
            return result
            
        # Step 4: Headless browser with anti-detection
        return await self.obscura.fetch(url, stealth=True)
```

### 8.4 Implementation Steps

1. **Phase 1 — Legal Foundation:**
   - Deploy Wallabag instance
   - Configure credentials for key subscriptions (WSJ, FT, Economist)
   - Integrate Archive.today and Wayback Machine APIs

2. **Phase 2 — Automation Layer:**
   - Deploy Ladder with comprehensive ruleset
   - Build API wrapper for pipeline orchestration
   - Add content extraction (Readability.js)

3. **Phase 3 — Advanced Bypass:**
   - Integrate Obscura MCP for headless browsing
   - Add CloakBrowser for maximum stealth targets
   - Implement retry/fallback logic

4. **Phase 4 — Monitoring:**
   - Track success rates per source
   - Alert on ruleset failures
   - Maintain legal compliance log

### 8.5 Configuration Template

```yaml
# deep-research-skill/paywall-config.yaml

# Phase 1: Legal methods (always try first)
legal_sources:
  wallabag:
    enabled: true
    url: "http://wallabag:8080"
    client_id: "${WALLABAG_CLIENT_ID}"
    client_secret: "${WALLABAG_SECRET}"
    credentials:
      - site: "economist.com"
        username: "${ECONOMIST_USER}"
        password: "${ECONOMIST_PASS}"
      - site: "wsj.com"
        username: "${WSJ_USER}"
        password: "${WSJ_PASS}"
        
  archives:
    archive_today:
      enabled: true
      prioritize: true
    wayback_machine:
      enabled: true
      cdx_api: "https://web.archive.org/cdx/search/cdx"

# Phase 2: Proxy bypass
proxy:
  ladder:
    enabled: true
    url: "http://ladder:8080"
    ruleset_url: "https://raw.githubusercontent.com/everywall/ladder-rules/main/ruleset.yaml"
    flaresolverr_host: "http://flaresolverr:8191"
    allowed_domains:
      - "wsj.com"
      - "ft.com"
      - "economist.com"
      - "bloomberg.com"

# Phase 3: Headless browser
headless:
  obscura:
    enabled: true
    mcp_command: "obscura"
    mcp_args: ["mcp", "--stealth"]
  cloakbrowser:
    enabled: false  # Enable for maximum stealth
    proxy: "${RESIDENTIAL_PROXY}"
    humanize: true

# Content extraction
extraction:
  readability:
    enabled: true
  custom_selectors:
    "wsj.com": ".wsj-article-body"
    "ft.com": ".article__content"
    "economist.com": ".article__body-text"

# Logging & compliance
compliance:
  log_all_requests: true
  fair_use_purpose: "research and analysis"
  max_articles_per_source_per_day: 100
  retention_days: 30
```

---

## 9. Appendix: Supported Sites Reference

### 9.1 Bypass Paywalls Chrome — Full Supported List

**Financial/Business:**
- Adweek, American Banker, Barron's, Bloomberg, Bloomberg Quint, Business Insider, Caixin, Chemical & Engineering News, Crain's Chicago Business, Financial News, Financial Times, First Things, Fortune, Glassdoor, Handelsblatt, Harvard Business Review, Investors Chronicle, L.A. Business Journal, L'Echo, Les Echos, MIT Sloan Management Review, Nikkei Asian Review, Quartz, Seeking Alpha, Statista, Tech in Asia, The Business Journals, The Economist, The Globe and Mail, The Wall Street Journal, TheMarker, Towards Data Science, Wired

**Major News:**
- Algemeen Dagblad, Baltimore Sun, Central Western Daily, Chicago Tribune, Corriere Della Sera, Daily Press, De Groene Amsterdammer, De Tijd, De Volkskrant, DeMorgen, Denver Post, Eindhovens Dagblad, El Pais, Examiner, Foreign Policy, Genomeweb, Haaretz, Harper's Magazine, Hartford Courant, Herald Sun, Het Financieel Dagblad, Il Manifesto, Inc.com, La Nación, La Repubblica, La Stampa, La Tercera, Le Devoir, Le Parisien, London Review of Books, Los Angeles Times, Medium, Mountain View Voice, NRC Handelsblad, NT News, National Post, Neue Zürcher Zeitung, New York Magazine, New Zealand Herald, Orange County Register, Orlando Sentinel, Palo Alto Online, Parool, Quora, SOFREP, San Diego Union Tribune, San Francisco Chronicle, Scientific American, SunSentinel, The Advertiser, The Advocate, The Age, The American Interest, The Athletic, The Atlantic, The Australian, The Canberra Times, The Courier, The Courier Mail, The Daily Telegraph, The Diplomat, The Hindu, The Irish Times, The Japan Times, The Kansas City Star, The Mercury News, The Nation, The New Statesman, The New York Times, The New Yorker, The News-Gazette, The Philadelphia Inquirer, The Saturday Paper, The Seattle Times, The Spectator, The Sydney Morning Herald, The Telegraph, The Times, The Toronto Star, The Washington Post, The Wrap, Times Literary Supplement, Trouw, Vanity Fair, Vrij Nederland, Winston-Salem Journal

**Specialized:**
- Dynamed Plus, Encyclopedia Britannica, Loeb Classical Library

### 9.2 Wallabag Paywall-Compatible Sites

| Site | Version Required |
|------|-----------------|
| Alternatives Economiques | 2.3+ |
| Arret sur Images | 2.2+ |
| Canard PC | 2.3+ |
| Courrier International | 2.3+ |
| GameKult | 2.3+ |
| Le Figaro | 2.3+ |
| Le Monde | 2.3+ |
| Le Monde Diplomatique | 2.3+ |
| Le Point | 2.3+ |
| LWN.net | 2.3+ |
| Mediapart | 2.2+ |
| Next INpact | 2.2+ |
| Reflets.info | 2.3+ |
| The Economist | 2.3+ |

---

## 10. Quick Reference Card

### 10.1 One-Liner Commands

```bash
# Archive.today (web)
https://archive.today/https://ARTICLE_URL

# Wayback Machine (web)
https://web.archive.org/web/2/https://ARTICLE_URL

# Ladder API (if deployed)
curl http://localhost:8080/api/https://ARTICLE_URL

# Wallabag API
# Requires auth flow — see wallabag API docs

# Obscura CLI
obscura fetch https://ARTICLE_URL --dump text

# CloakBrowser (Python)
python -c "from cloakbrowser import launch; b=launch(); p=b.new_page(); p.goto('URL'); print(p.content())"
```

### 10.2 Decision Tree

```
Do you have a subscription?
├── YES → Use Wallabag (fully legal, full content)
└── NO → Is it archived?
    ├── YES → Use Archive.today or Wayback Machine
    └── NO → Is it a soft paywall?
        ├── YES → Try cookie clearing + Reader Mode
        └── NO → Is it Cloudflare-protected?
            ├── YES → Use Ladder + FlareSolverr
            └── NO → Use headless browser (Obscura/CloakBrowser)
```

---

## References

1. `iamadamdev/bypass-paywalls-chrome` — GitHub (banned)
2. `everywall/ladder` — https://github.com/everywall/ladder
3. `everywall/ladder-rules` — https://github.com/everywall/ladder-rules
4. `wasi-master/13ft` — https://github.com/wasi-master/13ft
5. `wallabag/wallabag` — https://github.com/wallabag/wallabag
6. `CloakHQ/CloakBrowser` — https://github.com/CloakHQ/CloakBrowser
7. `h4ckf0r0day/obscura` — https://github.com/h4ckf0r0day/obscura
8. FlareSolverr — https://github.com/FlareSolverr/FlareSolverr
9. `caffo/SMRY` — https://github.com/caffo/SMRY
10. DMCA Section 1201 — 17 U.S.C. § 1201
11. News Media Alliance DMCA Complaint, August 2024
12. Web Archive APIs — https://archive.org/help/wayback_api.php

---

> **Disclaimer:** This research is provided for educational and research purposes only. The use of paywall bypass tools may violate terms of service and applicable law in your jurisdiction. Always prioritize legal methods (archives, library access, subscriptions) and respect content creators' rights.
