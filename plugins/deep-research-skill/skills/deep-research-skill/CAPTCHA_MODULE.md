# CAPTCHA Module - Stealth-First CAPTCHA Handling

> **Version:** 1.0.0
> **Status:** Production-ready module for skill integration
> **Approach:** Stealth-first | Prevention > Detection > Solving

---

## 1. Philosophy

### Core Principles

1. **Stealth is the first line of defense.** CAPTCHA solving is a weapon of last resort, not a default strategy. Every CAPTCHA encountered represents a failure of prevention.
2. **Prevention beats reaction.** A properly configured stealth browser with residential proxies and human-like behavior patterns should bypass >90% of CAPTCHA triggers without ever engaging a solver.
3. **CAPTCHA solving is an expensive operational cost, not a technical solution.** Budget constraints must be enforced programmatically.
4. **Operational security is paramount.** All CAPTCHA-related activity must be logged, auditable, and bounded by hard cost thresholds.

### Decision Hierarchy

```
1. Official API available?
   YES -> Use API (NO browser automation)
   NO  -> Continue to #2

2. Alternative data source exists?
   YES -> Use alternative source
   NO  -> Continue to #3

3. Stealth browser + proxy bypass works?
   YES -> Extract normally
   NO  -> Continue to #4

4. CAPTCHA triggered despite prevention?
   YES -> Attempt: Primary solver -> Fallback chain
   NO  -> Normal extraction

5. Cost threshold exceeded?
   YES -> ABORT session, return partial data
   NO  -> Continue solving within budget
```

### Golden Rules

| Rule | Rationale |
|------|-----------|
| Never solve a CAPTCHA if an official API exists | APIs are cheaper, faster, and 100% legal |
| Never solve a CAPTCHA on the first request | Prevention layer must be exhausted first |
| Never solve without a cost ceiling | Runaway costs are a project risk |
| Never solve without audit logging | Legal defensibility requires documentation |
| Always try stealth before solving | Each solved CAPTCHA costs $0.00035-$0.003 |

---

## 2. Prevention Layer (Before CAPTCHA Appears)

### 2.1 CloakBrowser (Primary Browser Engine)

**CloakBrowser** is a hardened Chromium fork with 49 C++ patches applied at the browser engine level.

| Patch Category | Count | Purpose |
|---------------|-------|---------|
| Navigator object spoofing | 8 patches | Hide `webdriver`, `chrome.runtime`, plugin count |
| WebGL fingerprint randomization | 6 patches | Prevent GPU-based fingerprinting |
| Canvas noise injection | 4 patches | Defeat canvas fingerprinting |
| Font metrics normalization | 5 patches | Standardize measured font dimensions |
| Permission API override | 3 patches | Mask notification/clipboard permissions |
| `navigator.deviceMemory` | 2 patches | Report realistic RAM values |
| `hardwareConcurrency` | 2 patches | Report realistic CPU core counts |
| Chrome runtime patch | 2 patches | Remove `window.chrome` automation flags |
| WebDriver flag removal | 4 patches | Strip `navigator.webdriver=true` |
| Automation protocol patch | 3 patches | Disable DevTools protocol detection |
| Sandbox/iframe isolation | 4 patches | Prevent parent-frame inspection |
| Timing attack mitigation | 3 patches | Add jitter to `performance.now()` |
| Miscellaneous leaks | 5 patches | Plug edge-case detection vectors |

**Integration:**
```python
from cloakbrowser import CloakBrowser

browser = CloakBrowser(
    profile_id="research_session_001",
    proxy="socks5://user:pass@residential.proxy:1080",
    viewport={"width": 1920, "height": 1080},
    locale="en-US",
    timezone="America/New_York",
    # Apply all 49 patches
    stealth_mode=True
)
page = browser.new_page()
```

### 2.2 Obscura (Headless Rust, MCP-Native)

**Obscura** is a headless browser built in Rust, designed specifically for MCP (Model Context Protocol) tool integration. It is lighter than CloakBrowser and used for fast, single-request operations where full Chromium is unnecessary.

| Feature | Spec |
|---------|------|
| Engine | Custom WebKit-based (Rust) |
| Binary size | ~18 MB (vs ~150 MB Chromium) |
| Startup time | ~50 ms (vs ~800 ms Chromium) |
| JavaScript engine | QuickJS (no V8 fingerprint) |
| Protocol | MCP-native message passing |
| Anti-detection | Built-in header/JS spoofing |

**Use Obscura when:**
- Target is a lightweight site with basic bot detection
- Speed is prioritized over JavaScript complexity
- Running in resource-constrained environments
- Site checks only headers/basic JS (no WebGL/canvas fingerprinting)

**Use CloakBrowser when:**
- Target runs heavy JavaScript (React, Vue, SPA)
- Site employs advanced fingerprinting (WebGL, canvas, fonts)
- reCAPTCHA v3 (invisible scoring) is present

### 2.3 Residential Proxies

Rotating residential proxies are mandatory for any session that may encounter CAPTCHA triggers.

| Provider | Pool Size | Rotation | Protocols | Cost/GB |
|----------|-----------|----------|-----------|---------|
| Bright Data | 72M+ IPs | Per-request or sticky | HTTP, SOCKS5, HTTPS | $15/GB |
| Oxylabs | 100M+ IPs | Auto-rotation | HTTP, SOCKS5 | $15/GB |
| Smartproxy | 55M+ IPs | Sticky (1-30 min) | HTTP, HTTPS | $12.5/GB |
| PacketStream | 7M+ IPs | Per-request | HTTP, HTTPS | $1/GB |
| Webshare | 30M+ IPs | Sticky/rotating | HTTP, SOCKS5 | $4.5/GB |

**Best practices:**
- Use **sticky sessions** (same IP for 3-10 minutes) for multi-step flows
- Use **per-request rotation** for high-volume single-page requests
- Match proxy geolocation with `timezone` and `locale` settings in browser
- Maintain proxy quality score: block IPs that trigger CAPTCHA >2 times in 10 requests

```python
from proxy_rotator import ResidentialProxyPool

proxy_pool = ResidentialProxyPool(
    provider="brightdata",
    sticky_sessions=True,
    sticky_duration=300,  # 5 minutes
    geo_target="us",      # US-based IPs
    quality_threshold=0.8  # Min 80% clean rate
)

proxy = proxy_pool.get_proxy()
```

### 2.4 Request Rate Limiting

Human-like request patterns are critical for avoiding CAPTCHA triggers.

| Parameter | Human Baseline | Bot Detection Threshold | Safe Setting |
|-----------|---------------|------------------------|--------------|
| Requests per minute (same domain) | 2-8 | 15+ | 8-12 |
| Time between page loads | 5-30 sec | <3 sec | 5-15 sec |
| Mouse movement speed | 200-800 px/sec | Instant teleport | 300-600 px/sec |
| Scroll behavior | Smooth, variable | Instant jumps | Smooth scroll |
| Form fill speed | 80-200 WPM | <50ms per field | 100-150 WPM |
| Session duration | 2-15 min | <30 sec | 3-10 min |
| Pages per session | 3-15 | 50+ | 5-20 |

```python
from human_emulator import HumanEmulator

emulator = HumanEmulator(
    base_delay=(500, 2000),      # 0.5-2s base delay between actions
    scroll_speed=(300, 600),     # px/sec
    typing_speed=(80, 150),      # WPM
    mouse_paths="bezier",        # Bezier curve mouse movement
    random_pauses=True           # Random 1-3s pauses
)

# Apply to page interactions
await emulator.click(page, "#submit-btn")
await emulator.type(page, "#search", "query text")
await emulator.scroll(page, amount=800)
```

### 2.5 User-Agent Rotation

| Strategy | Description | Use Case |
|----------|-------------|----------|
| Fixed matching | Match UA to browser version exactly | High-security targets |
| Rotating pool | Rotate among 50-100 realistic UAs | General research |
| OS correlation | Match UA `platform` with `navigator.platform` | Fingerprint-heavy sites |

**Recommended UA pool composition:**
- 60% Chrome on Windows 10/11 (most common real user)
- 20% Chrome on macOS
- 10% Safari on macOS
- 5% Firefox on Windows
- 5% Mobile (Chrome on Android)

```python
from ua_rotator import UARotator

ua = UARotator(
    pool_size=100,
    refresh_daily=True,
    # CloakBrowser automatically syncs UA with navigator object
    browser="chrome",
    os_weights={"windows": 0.6, "macos": 0.3, "linux": 0.1}
)
```

### 2.6 Prevention Effectiveness Targets

| Metric | Target | Measurement |
|--------|--------|-------------|
| CAPTCHA encounter rate | <5% of sessions | Sessions with any CAPTCHA / total sessions |
| Stealth bypass rate | >90% | Sessions without CAPTCHA / total sessions |
| Proxy trigger rate | <2% | CAPTCHAs triggered by proxy IP / total requests |
| Average cost per session | <$0.01 | Total CAPTCHA cost / total sessions |

---

## 3. Detection Layer

### 3.1 CAPTCHA Types Reference

| CAPTCHA Type | Provider | Difficulty | Detection Method | Prevalence |
|-------------|----------|------------|------------------|------------|
| **reCAPTCHA v2** (Checkbox) | Google | Medium | `iframe[src*="recaptcha"]` | Very High |
| **reCAPTCHA v2** (Invisible) | Google | High | `grecaptcha.execute()` calls | High |
| **reCAPTCHA v3** | Google | Very High | Score-based (0.1-0.9), no UI | Very High |
| **reCAPTCHA Enterprise** | Google | Very High | Enhanced risk analysis | High |
| **hCaptcha** | Intuition Machines | Medium | `iframe[src*="hcaptcha"]` | High |
| **Cloudflare Turnstile** | Cloudflare | Medium-High | `input[name="cf-turnstile-response"]` | Very High |
| **Cloudflare Challenge** | Cloudflare | Very High | Managed/Interactive challenge | Very High |
| **GeeTest v3** | GeeTest | Medium | `.geetest_*` CSS classes, canvas slider | Medium |
| **GeeTest v4** | GeeTest | High | `captcha_id` parameter | Medium |
| **FunCaptcha (Arkose)** | Arkose Labs | Very High | `iframe[src*="funcaptcha"]` | Medium |
| **KeyCAPTCHA** | KeyCAPTCHA | Medium | `s_s_c_*` parameters | Low |
| **AWS WAF CAPTCHA** | Amazon | Medium-High | `awswaf-captcha` div | Medium |
| **Image CAPTCHA** | Various | Low-Medium | `img[src*="captcha"]` | Low |
| **Slider CAPTCHA** | Various (Chinese) | Medium | Canvas-based slider puzzle | Medium |
| **Text CAPTCHA** | Various | Low | OCR-solvable text image | Low |

### 3.2 Detection Heuristics

#### DOM-Based Detection

```python
def detect_captcha_dom(page) -> list[str]:
    """
    Detect CAPTCHA presence via DOM selectors.
    Returns list of detected CAPTCHA types.
    """
    indicators = {
        'recaptcha_v2_checkbox': [
            '.g-recaptcha',
            'iframe[src*="google.com/recaptcha"]',
            'iframe[src*="recaptcha/api2"]',
            '#recaptcha-anchor'
        ],
        'recaptcha_v2_invisible': [
            'div[data-size="invisible"]',
            '.grecaptcha-badge'
        ],
        'recaptcha_v3': [
            # No visible DOM - detected via JS execution
        ],
        'hcaptcha': [
            'iframe[src*="hcaptcha.com"]',
            '.h-captcha',
            'div[data-hcaptcha-widget-id]'
        ],
        'cloudflare_turnstile': [
            'input[name="cf-turnstile-response"]',
            '.cf-turnstile',
            'iframe[src*="challenges.cloudflare"]'
        ],
        'cloudflare_challenge': [
            '#challenge-error-text',
            '#challenge-form',
            'input[name="cf_response"]',
            'title:has-text("Just a moment")'
        ],
        'geetest_v3': [
            '.geetest_radar_btn',
            '.geetest_canvas_img',
            '#captcha-box'
        ],
        'geetest_v4': [
            '.geetest_v4',
            '[data-captcha-id]'
        ],
        'funcaptcha': [
            'iframe[src*="funcaptcha.com"]',
            'iframe[src*="arkoselabs.com"]',
            '#FunCaptcha'
        ],
        'aws_waf': [
            '.awswaf-captcha',
            'div[data-waf-captcha]'
        ],
        'image_captcha': [
            'img[src*="captcha"]',
            'img[id*="captcha"]',
            'img[alt*="captcha" i]'
        ],
        'slider_captcha': [
            '.slider-captcha',
            '.slide-verify',
            'canvas[class*="slide"]'
        ]
    }

    detected = []
    for captcha_type, selectors in indicators.items():
        for selector in selectors:
            try:
                count = page.locator(selector).count()
                if count > 0:
                    detected.append(captcha_type)
                    break
            except:
                continue
    return detected
```

#### JavaScript-Based Detection (for reCAPTCHA v3)

```python
def detect_recaptcha_v3(page) -> dict:
    """
    Detect reCAPTCHA v3 by checking for grecaptcha object
    and attempting to infer score threshold.
    """
    result = page.evaluate('''() => {
        if (typeof grecaptcha === 'undefined') {
            return { present: false };
        }
        return {
            present: true,
            version: typeof grecaptcha.render !== 'undefined' ? 'v2' : 'v3',
            sitekeys: (() => {
                const keys = [];
                document.querySelectorAll('[data-sitekey]').forEach(el => {
                    keys.push(el.getAttribute('data-sitekey'));
                });
                return keys;
            })(),
            badge_visible: !!document.querySelector('.grecaptcha-badge')
        };
    }''')
    return result
```

#### Response-Based Detection

```python
def detect_captcha_response(response) -> str | None:
    """
    Detect CAPTCHA from HTTP response characteristics.
    """
    # Cloudflare challenge page
    if response.status == 403 and 'cloudflare' in response.headers.get('server', '').lower():
        return 'cloudfire_challenge'

    # Check response body for CAPTCHA indicators
    body_indicators = {
        'recaptcha': ['g-recaptcha', 'google.com/recaptcha', 'recaptcha/api.js'],
        'hcaptcha': ['hcaptcha.com', 'data-hcaptcha-widget-id'],
        'turnstile': ['cf-turnstile-response', 'challenges.cloudflare'],
        'cloudflare_wait': ['Checking your browser', 'cf-browser-verification', 'jschl-answer'],
        'geetest': ['geetest_', 'gt.js', 'captcha-box'],
        'funcaptcha': ['funcaptcha', 'arkoselabs', 'FunCaptcha'],
    }

    body = response.text().lower()
    for captcha_type, indicators in body_indicators.items():
        if any(ind in body for ind in indicators):
            return captcha_type

    return None
```

### 3.3 Classification by Type

Once detected, CAPTCHA is classified for routing to the appropriate handler:

```python
from enum import Enum

class CaptchaType(Enum):
    RECAPTCHA_V2 = "recaptcha_v2"
    RECAPTCHA_V3 = "recaptcha_v3"
    RECAPTCHA_ENTERPRISE = "recaptcha_enterprise"
    HCAPTCHA = "hcaptcha"
    CLOUDFLARE_TURNSTILE = "cloudflare_turnstile"
    CLOUDFLARE_CHALLENGE = "cloudflare_challenge"
    GEETEST_V3 = "geetest_v3"
    GEETEST_V4 = "geetest_v4"
    FUNCAPTCHA = "funcaptcha"
    AWS_WAF = "aws_waf"
    IMAGE_CAPTCHA = "image_captcha"
    SLIDER_CAPTCHA = "slider_captcha"
    TEXT_CAPTCHA = "text_captcha"
    UNKNOWN = "unknown"

# Routing map: CAPTCHA type -> preferred solver method
SOLVER_ROUTING = {
    CaptchaType.RECAPTCHA_V2: "recaptcha",
    CaptchaType.RECAPTCHA_V3: "recaptcha",
    CaptchaType.RECAPTCHA_ENTERPRISE: "recaptcha",
    CaptchaType.HCAPTCHA: "hcaptcha",
    CaptchaType.CLOUDFLARE_TURNSTILE: "turnstile",
    CaptchaType.CLOUDFLARE_CHALLENGE: "cloudflare",  # May require proxy rotation
    CaptchaType.GEETEST_V3: "geetest",
    CaptchaType.GEETEST_V4: "geetest_v4",
    CaptchaType.FUNCAPTCHA: "funcaptcha",
    CaptchaType.AWS_WAF: "aws",
    CaptchaType.IMAGE_CAPTCHA: "normal",
    CaptchaType.SLIDER_CAPTCHA: "coordinates",
    CaptchaType.TEXT_CAPTCHA: "text",
}
```

---

## 4. Solving Layer (When Prevention Fails)

### 4.1 Fallback Chain

The solving layer uses a cascading fallback chain. Each provider is attempted in order until one succeeds or the chain is exhausted.

```
Priority 1: CapSolver      (fastest AI solver, best for common types)
     |
     v (timeout / failure)
Priority 2: SolveCaptcha   (best price/performance, pay-for-success)
     |
     v (timeout / failure)
Priority 3: Anti-Captcha   (most reliable, longest track record)
     |
     v (timeout / failure)
Priority 4: 2Captcha       (widest type coverage, human workers)
     |
     v (all exhausted)
ABORT: Return partial data, log failure, alert operator
```

```python
import logging
from dataclasses import dataclass
from typing import Optional, Callable

logger = logging.getLogger(__name__)

@dataclass
class SolverProvider:
    name: str
    solver: object          # Solver instance
    methods: dict           # CAPTCHA type -> method mapping
    priority: int           # Lower = higher priority
    timeout: int            # Seconds to wait before trying next
    cost_per_1k: float      # Cost per 1000 solves (for cost tracking)

class CaptchaFallbackChain:
    """
    Cascading CAPTCHA solver with fallback chain.
    Attempts each provider in priority order until success.
    """

    def __init__(self, providers: list[SolverProvider], cost_tracker: 'CostTracker'):
        self.providers = sorted(providers, key=lambda p: p.priority)
        self.cost_tracker = cost_tracker
        self.failure_log = []

    def solve(self, captcha_type: str, **kwargs) -> dict:
        """
        Attempt to solve CAPTCHA using fallback chain.
        Returns {'provider': str, 'token': str, 'cost': float} or raises.
        """
        for provider in self.providers:
            method_name = provider.methods.get(captcha_type)
            if not method_name:
                continue

            method = getattr(provider.solver, method_name, None)
            if not method:
                continue

            try:
                logger.info(f"Attempting {captcha_type} via {provider.name}...")
                result = method(**kwargs)

                if result and result.get('code'):
                    cost = provider.cost_per_1k / 1000
                    self.cost_tracker.log_solve(
                        provider=provider.name,
                        captcha_type=captcha_type,
                        cost=cost,
                        success=True
                    )
                    logger.info(f"CAPTCHA solved via {provider.name}")
                    return {
                        'provider': provider.name,
                        'token': result['code'],
                        'cost': cost,
                        'raw': result
                    }

            except Exception as e:
                logger.warning(f"Provider {provider.name} failed: {e}")
                self.failure_log.append({
                    'provider': provider.name,
                    'error': str(e),
                    'captcha_type': captcha_type
                })
                continue

        # All providers exhausted
        self.cost_tracker.log_solve(
            provider='all',
            captcha_type=captcha_type,
            cost=0,
            success=False
        )
        raise RuntimeError(f"All CAPTCHA providers exhausted for {captcha_type}")
```

### 4.2 Pricing Comparison Table

| Service | reCAPTCHA v2 | reCAPTCHA v3 | Turnstile | hCaptcha | Image CAPTCHA | GeeTest | FunCaptcha | Model |
|---------|:------------:|:------------:|:---------:|:--------:|:-------------:|:-------:|:----------:|-------|
| **CapSolver** | $0.80/1K | $1.00/1K | $1.20/1K | $0.80/1K | $0.40/1K | $1.20/1K | $1.50/1K | AI/ML |
| **SolveCaptcha** | $0.55/1K | $0.80/1K | $0.80/1K | ~$1.00/1K | $0.35/1K | $0.80/1K | $2.99+/1K | Hybrid AI+Human |
| **Anti-Captcha** | $0.95/1K | $1.00/1K | $2.00/1K | ~$1.50/1K | $0.50/1K | $1.80/1K | $3.00/1K | Human workers |
| **2Captcha** | $1.00/1K | $1.45/1K | $1.45/1K | $1.00/1K | $0.50/1K | Supported | $2.00+/1K | Human workers |
| **DeathByCaptcha** | $2.89/1K | Supported | Supported | Supported | $1.39/1K | Supported | Limited | Hybrid |
| **CapMonster Cloud** | $0.50/1K | $0.50/1K | Supported | Supported | $0.20/1K | Supported | Limited | AI |

### 4.3 Speed & Success Rate Comparison

| Service | reCAPTCHA v2 | reCAPTCHA v3 | Turnstile | hCaptcha | Image | Uptime | Success Rate |
|---------|:----------:|:----------:|:-------:|:------:|:-----:|:------:|:------------:|
| **CapSolver** | 3-9 sec | <3 sec | <3 sec | 3-5 sec | <1 sec | 99.9% | ~99% |
| **SolveCaptcha** | 2-3 sec | 2 sec | 3 sec | 3 sec | 2 sec | 99.9% | ~95-99% |
| **Anti-Captcha** | 10 sec | 5 sec | 5 sec | 8 sec | 5 sec | 99.99% | ~99% |
| **2Captcha** | 13-20 sec | 20-60 sec | 10-30 sec | 10-20 sec | 5-15 sec | 99.9% | ~95-99% |
| **DeathByCaptcha** | 15-30 sec | 10-20 sec | 10-20 sec | 15-30 sec | 5-10 sec | 99.9% | 95-100% |
| **CapMonster Cloud** | 3-8 sec | 3-8 sec | 3-8 sec | 3-8 sec | <1 sec | 99.9% | ~97% |

### 4.4 Integration Code Examples

#### Playwright + CapSolver (Primary)

```python
import asyncio
from playwright.async_api import async_playwright
from capsolver import Capsolver

CAPSOLVER_API_KEY = "YOUR_CAPSOLVER_KEY"

capsolver = Capsolver(api_key=CAPSOLVER_API_KEY)

async def solve_captcha_playwright(page, captcha_type: str) -> str:
    """
    Detect and solve CAPTCHA on current Playwright page.
    Injects solution token and returns it.
    """
    url = page.url

    if captcha_type == "recaptcha_v2":
        # Extract sitekey
        sitekey = await page.evaluate('''() => {
            const el = document.querySelector('.g-recaptcha');
            return el ? el.dataset.sitekey : null;
        }''')

        if not sitekey:
            raise ValueError("reCAPTCHA v2 sitekey not found")

        # Solve via CapSolver
        result = capsolver.solve_recaptcha_v2(
            sitekey=sitekey,
            pageurl=url
        )
        token = result["gRecaptchaResponse"]

        # Inject token
        await page.evaluate(f'''
            document.getElementById("g-recaptcha-response").value = "{token}";
            if (typeof ___grecaptcha_cfg !== 'undefined') {{
                const clients = ___grecaptcha_cfg.clients;
                Object.values(clients).forEach(client => {{
                    if (client.callback) client.callback("{token}");
                }});
            }}
        ''')
        return token

    elif captcha_type == "turnstile":
        sitekey = await page.evaluate('''() => {
            const el = document.querySelector('input[name="cf-turnstile-response"]');
            return el ? el.dataset.sitekey : null;
        }''')

        result = capsolver.solve_turnstile(
            sitekey=sitekey,
            pageurl=url
        )
        token = result["token"]

        await page.evaluate(f'''
            document.querySelector('input[name="cf-turnstile-response"]').value = "{token}";
        ''')
        return token

    elif captcha_type == "hcaptcha":
        sitekey = await page.evaluate('''() => {
            const el = document.querySelector('.h-captcha');
            return el ? el.dataset.sitekey : null;
        }''')

        result = capsolver.solve_hcaptcha(
            sitekey=sitekey,
            pageurl=url
        )
        token = result["gRecaptchaResponse"]

        await page.evaluate(f'''
            document.querySelector('textarea[name="h-captcha-response"]').value = "{token}";
        ''')
        return token

    else:
        raise NotImplementedError(f"CAPTCHA type {captcha_type} not yet supported")


async def extract_with_fallback(page, captcha_chain: CaptchaFallbackChain):
    """Full extraction with CAPTCHA handling."""
    # 1. Check for CAPTCHA
    detected = detect_captcha_dom(page)
    if not detected:
        # Also check JS for invisible/v3
        v3_check = detect_recaptcha_v3(page)
        if v3_check.get('present') and v3_check.get('version') == 'v3':
            detected = ['recaptcha_v3']

    if not detected:
        # No CAPTCHA - proceed with extraction
        return await page.content()

    captcha_type = detected[0]
    print(f"CAPTCHA detected: {captcha_type}")

    # 2. Attempt solve via fallback chain
    url = page.url
    sitekey = await page.evaluate('''() => {
        const el = document.querySelector('[data-sitekey]');
        return el ? el.dataset.sitekey : null;
    }''')

    result = captcha_chain.solve(
        captcha_type=captcha_type,
        sitekey=sitekey,
        url=url
    )

    # 3. Inject token and continue
    token = result['token']
    await page.evaluate(f'''
        document.querySelector('[name*="captcha-response"]').value = "{token}";
    ''')

    # 4. Return page content after solve
    return await page.content()
```

#### Selenium + SolveCaptcha (Fallback)

```python
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from solvecaptcha import Solvecaptcha

SOLVECAPTCHA_KEY = "YOUR_SOLVECAPTCHA_KEY"
solver = Solvecaptcha(apiKey=SOLVECAPTCHA_KEY)

def solve_recaptcha_selenium(driver):
    """Solve reCAPTCHA v2 in active Selenium session."""
    # Extract sitekey
    recaptcha = driver.find_element(By.CLASS_NAME, 'g-recaptcha')
    sitekey = recaptcha.get_attribute('data-sitekey')
    current_url = driver.current_url

    # Solve
    result = solver.recaptcha(sitekey=sitekey, url=current_url, version='v2')
    token = result['code']

    # Inject token
    driver.execute_script(f'''
        document.getElementById("g-recaptcha-response").innerHTML = "{token}";
        // Trigger callback if exists
        if (typeof ___grecaptcha_cfg !== 'undefined') {{
            Object.values(___grecaptcha_cfg.clients).forEach(c => {{
                if (c.callback) c.callback("{token}");
            }});
        }}
    ''')

    return token

def solve_turnstile_selenium(driver):
    """Solve Cloudflare Turnstile in active Selenium session."""
    turnstile_input = driver.find_element(
        By.CSS_SELECTOR,
        'input[name="cf-turnstile-response"]'
    )
    sitekey = turnstile_input.get_attribute('data-sitekey')

    result = solver.turnstile(sitekey=sitekey, url=driver.current_url)
    token = result['code']

    driver.execute_script(f'''
        document.querySelector('input[name="cf-turnstile-response"]').value = "{token}";
    ''')

    return token
```

#### Anti-Captcha Integration (Fallback #3)

```python
import anticaptcha

ANTICAPTCHA_KEY = "YOUR_ANTICAPTCHA_KEY"

class AntiCaptchaWrapper:
    """Wrapper for Anti-Captcha API."""

    def __init__(self, api_key: str):
        self.api_key = api_key

    def solve_recaptcha_v2(self, sitekey: str, pageurl: str, invisible: bool = False) -> str:
        task = anticaptcha.NoCaptchaTaskProxylessTask(
            website_url=pageurl,
            website_key=sitekey,
            is_invisible=invisible
        )
        job = anticaptcha.AntiCaptchaTask(self.api_key)
        job.createTask(task)
        job.join(max_time=120)
        return job.get_solution_response()

    def solve_image(self, image_base64: str) -> str:
        task = anticaptcha.ImageToTextTask(image_base64)
        job = anticaptcha.AntiCaptchaTask(self.api_key)
        job.createTask(task)
        job.join(max_time=60)
        return job.get_solution_text()
```

---

## 5. Cost Tracking

### 5.1 Per-Session CAPTCHA Budget

Every research session has a hard CAPTCHA budget. When the budget is exceeded, the session aborts with partial data.

```python
import json
import logging
from pathlib import Path
from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional

logger = logging.getLogger(__name__)

@dataclass
class CaptchaBudget:
    """
    Budget configuration for CAPTCHA spending.
    Enforced per-session.
    """
    max_total_cost: float = 1.00        # Maximum $ per session
    max_solves: int = 50                # Maximum CAPTCHA solves per session
    max_cost_per_solve: float = 0.01    # Abort if single solve exceeds this
    alert_threshold: float = 0.50       # Log warning at 50% of budget
    hard_abort: bool = True             # If True, raise exception on budget exceeded

@dataclass
class CostTracker:
    """
    Tracks CAPTCHA solving costs across sessions.
    Enforces budget constraints.
    """
    budget: CaptchaBudget = field(default_factory=CaptchaBudget)
    log_file: str = "captcha_costs.jsonl"

    # Internal state
    _session_cost: float = field(default=0.0, repr=False)
    _solve_count: int = field(default=0, repr=False)
    _costs: list = field(default_factory=list, repr=False)

    def __post_init__(self):
        self.log_path = Path(self.log_file)

    def log_solve(self, provider: str, captcha_type: str, cost: float, success: bool = True):
        """
        Log a CAPTCHA solve event and enforce budget.
        Raises BudgetExceededError if budget is exceeded and hard_abort=True.
        """
        entry = {
            "timestamp": datetime.utcnow().isoformat() + "Z",
            "provider": provider,
            "type": captcha_type,
            "cost_usd": round(cost, 6),
            "success": success,
            "session_total": round(self._session_cost + cost, 6),
            "solve_number": self._solve_count + 1
        }

        # Write to log file
        with open(self.log_path, 'a') as f:
            f.write(json.dumps(entry) + '\n')

        self._costs.append(entry)

        if success:
            self._session_cost += cost
            self._solve_count += 1

            # Check budget constraints
            if cost > self.budget.max_cost_per_solve:
                msg = f"Single solve cost ${cost:.4f} exceeds max ${self.budget.max_cost_per_solve:.4f}"
                logger.error(msg)
                if self.budget.hard_abort:
                    raise BudgetExceededError(msg)

            if self._session_cost >= self.budget.max_total_cost:
                msg = f"Session CAPTCHA budget exhausted: ${self._session_cost:.4f} / ${self.budget.max_total_cost:.4f}"
                logger.error(msg)
                if self.budget.hard_abort:
                    raise BudgetExceededError(msg)

            if self._solve_count >= self.budget.max_solves:
                msg = f"Max CAPTCHA solves reached: {self._solve_count} / {self.budget.max_solves}"
                logger.error(msg)
                if self.budget.hard_abort:
                    raise BudgetExceededError(msg)

            # Alert at threshold
            if self._session_cost >= self.budget.alert_threshold:
                logger.warning(
                    f"CAPTCHA budget at {self._session_cost/self.budget.max_total_cost*100:.0f}%: "
                    f"${self._session_cost:.4f} / ${self.budget.max_total_cost:.4f}"
                )

    def get_session_stats(self) -> dict:
        """Return current session cost statistics."""
        by_type = {}
        by_provider = {}
        for entry in self._costs:
            if entry['success']:
                t = entry['type']
                p = entry['provider']
                by_type[t] = by_type.get(t, 0) + entry['cost_usd']
                by_provider[p] = by_provider.get(p, 0) + entry['cost_usd']

        return {
            "total_cost_usd": round(self._session_cost, 6),
            "solve_count": self._solve_count,
            "avg_cost_per_solve": round(self._session_cost / max(self._solve_count, 1), 6),
            "budget_used_pct": round(self._session_cost / self.budget.max_total_cost * 100, 2),
            "by_type": {k: round(v, 6) for k, v in by_type.items()},
            "by_provider": {k: round(v, 6) for k, v in by_provider.items()},
            "remaining_budget": round(self.budget.max_total_cost - self._session_cost, 6)
        }

    def can_afford(self, estimated_cost: float) -> bool:
        """Check if session can afford another solve."""
        return (self._session_cost + estimated_cost <= self.budget.max_total_cost and
                self._solve_count < self.budget.max_solves)


class BudgetExceededError(RuntimeError):
    """Raised when CAPTCHA budget is exceeded and hard_abort=True."""
    pass
```

### 5.2 Cost Accumulation Tracking

```python
# Pricing map: cost per individual solve (USD)
PRICING_PER_SOLVE = {
    # CapSolver (Priority 1)
    'capsolver_recaptcha_v2':    0.00080,   # $0.80 / 1000
    'capsolver_recaptcha_v3':    0.00100,   # $1.00 / 1000
    'capsolver_turnstile':       0.00120,   # $1.20 / 1000
    'capsolver_hcaptcha':        0.00080,   # $0.80 / 1000
    'capsolver_image':           0.00040,   # $0.40 / 1000
    'capsolver_geetest':         0.00120,   # $1.20 / 1000

    # SolveCaptcha (Priority 2)
    'solvecaptcha_recaptcha_v2': 0.00055,   # $0.55 / 1000
    'solvecaptcha_recaptcha_v3': 0.00080,   # $0.80 / 1000
    'solvecaptcha_turnstile':    0.00080,   # $0.80 / 1000
    'solvecaptcha_hcaptcha':     0.00100,   # ~$1.00 / 1000
    'solvecaptcha_image':        0.00035,   # $0.35 / 1000
    'solvecaptcha_geetest':      0.00080,   # $0.80 / 1000
    'solvecaptcha_funcaptcha':   0.00299,   # $2.99 / 1000

    # Anti-Captcha (Priority 3)
    'anticaptcha_recaptcha_v2':  0.00095,   # $0.95 / 1000
    'anticaptcha_recaptcha_v3':  0.00100,   # $1.00 / 1000
    'anticaptcha_turnstile':     0.00200,   # $2.00 / 1000
    'anticaptcha_hcaptcha':      0.00150,   # ~$1.50 / 1000
    'anticaptcha_image':         0.00050,   # $0.50 / 1000
    'anticaptcha_geetest':       0.00180,   # $1.80 / 1000
    'anticaptcha_funcaptcha':    0.00300,   # $3.00 / 1000

    # 2Captcha (Priority 4)
    'twocaptcha_recaptcha_v2':   0.00100,   # $1.00 / 1000
    'twocaptcha_recaptcha_v3':   0.00145,   # $1.45 / 1000
    'twocaptcha_turnstile':      0.00145,   # $1.45 / 1000
    'twocaptcha_hcaptcha':       0.00100,   # $1.00 / 1000
    'twocaptcha_image':          0.00050,   # $0.50 / 1000
}
```

### 5.3 Budget Templates by Session Size

| Session Type | Pages | Est. CAPTCHAs | Max Budget | Fallback Budget | Max Solves |
|-------------|-------|---------------|------------|-----------------|------------|
| Small | <50 | 0-5 | $0.01 | $0.005 | 10 |
| Medium | 50-500 | 5-50 | $0.05 | $0.02 | 30 |
| Large | 500-5000 | 50-500 | $0.50 | $0.20 | 100 |
| Extensive | 5000+ | 500+ | $2.00 | $0.50 | 500 |

```python
def get_budget_for_session(pages: int) -> CaptchaBudget:
    """Return appropriate budget for session size."""
    if pages < 50:
        return CaptchaBudget(max_total_cost=0.01, max_solves=10)
    elif pages < 500:
        return CaptchaBudget(max_total_cost=0.05, max_solves=30)
    elif pages < 5000:
        return CaptchaBudget(max_total_cost=0.50, max_solves=100)
    else:
        return CaptchaBudget(max_total_cost=2.00, max_solves=500)
```

---

## 6. Legal Disclaimer

### 6.1 DMCA / CFAA Risk Assessment

| Jurisdiction | Relevant Law | Risk Level | Key Precedent |
|-------------|-------------|------------|---------------|
| **United States** | CFAA (18 U.S.C. 1030) | **HIGH** | *hiQ Labs v. LinkedIn* (2022) - scraping public data is legal, but circumventing access controls (CAPTCHA) may be "exceeding authorized access" |
| **United States** | DMCA Anti-Circumvention | **MEDIUM** | *Ticketmaster v. RMG Technologies* - CAPTCHA circumvention tools can violate DMCA |
| **European Union** | GDPR | **MEDIUM** | Applies to data collection method; lawful basis required for personal data |
| **European Union** | Digital Services Act | **MEDIUM** | Transparency requirements for automated collection |
| **Global** | Various computer crime statutes | **VARIABLE** | Most jurisdictions have laws against unauthorized access |

### 6.2 Terms of Service Implications

**Nearly all websites explicitly prohibit:**
- Automated access and scraping
- CAPTCHA circumvention
- Use of bots, crawlers, or automation tools
- Bypassing technical access controls

**SolveCaptcha's own Terms of Service state:**
> "You agree to use SolveCaptcha service for **research purposes only**."

### 6.3 Risk Categories & Recommendations

| Risk Level | Scenario | Recommendation |
|-----------|----------|----------------|
| **LOW** | Public data, low volume, respecting rate limits, no CAPTCHA solving needed | Proceed with standard stealth measures |
| **MEDIUM** | CAPTCHA solving required for research, moderate volume, public non-personal data | Implement full audit logging, cost tracking, legal review |
| **HIGH** | Systematic CAPTCHA circumvention, high volume, sensitive/personal data, financial sites | **Do not proceed without legal counsel** |

### 6.4 Prohibited Targets

The following target categories **must not** be engaged with CAPTCHA solving:

- **Financial services** (banking, trading platforms, payment processors)
- **Healthcare data** (HIPAA-covered entities, medical records)
- **Government services** (without explicit authorization)
- **Ticketing sites** (strong legal precedent against circumvention)
- **Social media personal data** (GDPR/privacy law risk)
- **Educational records** (FERPA-covered in US)
- **Any site where data is not publicly available**

### 6.5 Audit Log Requirements

All CAPTCHA-related activity **must** be logged with the following fields:

```json
{
    "timestamp": "2025-01-28T14:30:00Z",
    "session_id": "research_session_001",
    "target_url": "https://example.com/page",
    "target_domain": "example.com",
    "captcha_type": "recaptcha_v2",
    "detection_method": "dom_selector",
    "prevention_used": ["cloakbrowser", "residential_proxy", "rate_limiting"],
    "solver_provider": "CapSolver",
    "solve_success": true,
    "solve_duration_ms": 4200,
    "cost_usd": 0.00080,
    "session_cumulative_cost": 0.00420,
    "ip_address": "[REDACTED]",
    "proxy_country": "US",
    "user_agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36...",
    "legal_review_status": "approved",
    "data_classification": "public",
    "retention_days": 90
}
```

**Retention:** Logs must be retained for minimum 90 days.

### 6.6 Pre-Flight Legal Checklist

Before any CAPTCHA-solving session:

- [ ] Confirmed no official API exists for the target data
- [ ] Confirmed target data is **publicly available** (no authentication required)
- [ ] Confirmed data is **non-personal** (no GDPR/privacy implications)
- [ ] Reviewed target site's Terms of Service
- [ ] Confirmed target is not in the **prohibited categories** list
- [ ] Prevention layer (stealth + proxy) has been attempted and documented
- [ ] Cost tracking and budget limits are configured
- [ ] Audit logging is enabled and writing to persistent storage
- [ ] Fallback to alternative data sources is available
- [ ] Session has a unique ID for traceability

---

## 7. Integration with Research Pipeline

### 7.1 Trigger Conditions

The CAPTCHA module is triggered only under specific conditions:

```
[Research Pipeline Flow]

1. User Query Received
        |
        v
2. Tool Router determines data sources
        |
        v
3. Browser tool loads target page
        |
        +---> Page loads normally? --> Extract data --> Done
        |
        +---> CAPTCHA detected? --> TRIGGER CAPTCHA MODULE
        |       |
        |       v
        |   4. Prevention Layer
        |       - Already applied (CloakBrowser + proxy)
        |       - If not applied, apply and retry
        |       |
        |       v
        |   5. CAPTCHA still present?
        |       |
        |       +---> No CAPTCHA after retry? --> Extract data
        |       |
        |       +---> CAPTCHA persists? --> Solving Layer
        |               |
        |               v
        |           6. Fallback Chain
        |               - CapSolver --> SolveCaptcha --> Anti-Captcha
        |               |
        |               v
        |           7. Cost check
        |               - Within budget? --> Inject token --> Extract data
        |               - Budget exceeded? --> ABORT --> Partial data
        |
        +---> Hard block / IP ban? --> Fallback sources
```

### 7.2 Tool Router Integration

```python
class CaptchaToolModule:
    """
    CAPTCHA handling module for Tool Router integration.
    Implements the ToolModule protocol.
    """

    def __init__(self, config: dict):
        self.budget = CaptchaBudget(**config.get('budget', {}))
        self.cost_tracker = CostTracker(budget=self.budget)
        self.fallback_chain = self._build_fallback_chain(config, self.cost_tracker)
        self.prevention = PreventionLayer(config.get('prevention', {}))

    def _build_fallback_chain(self, config, tracker) -> CaptchaFallbackChain:
        providers = []
        # CapSolver (Priority 1)
        if 'capsolver_key' in config:
            from capsolver import Capsolver
            providers.append(SolverProvider(
                name="CapSolver",
                solver=Capsolver(api_key=config['capsolver_key']),
                methods={
                    'recaptcha_v2': 'solve_recaptcha_v2',
                    'recaptcha_v3': 'solve_recaptcha_v3',
                    'turnstile': 'solve_turnstile',
                    'hcaptcha': 'solve_hcaptcha',
                    'image_captcha': 'solve_image',
                },
                priority=1,
                timeout=30,
                cost_per_1k=0.80
            ))
        # SolveCaptcha (Priority 2)
        if 'solvecaptcha_key' in config:
            from solvecaptcha import Solvecaptcha
            providers.append(SolverProvider(
                name="SolveCaptcha",
                solver=Solvecaptcha(apiKey=config['solvecaptcha_key']),
                methods={
                    'recaptcha_v2': 'recaptcha',
                    'recaptcha_v3': 'recaptcha',
                    'turnstile': 'turnstile',
                    'hcaptcha': 'hcaptcha',
                    'image_captcha': 'normal',
                    'geetest_v3': 'geetest',
                    'geetest_v4': 'geetest_v4',
                    'funcaptcha': 'funcaptcha',
                },
                priority=2,
                timeout=60,
                cost_per_1k=0.55
            ))
        # Anti-Captcha (Priority 3)
        if 'anticaptcha_key' in config:
            import anticaptcha
            providers.append(SolverProvider(
                name="Anti-Captcha",
                solver=anticaptcha.AntiCaptchaTask(config['anticaptcha_key']),
                methods={
                    'recaptcha_v2': 'solve_and_return_solution',
                    'recaptcha_v3': 'solve_and_return_solution',
                    'image_captcha': 'solve_and_return_solution',
                },
                priority=3,
                timeout=120,
                cost_per_1k=0.95
            ))
        return CaptchaFallbackChain(providers, tracker)

    async def handle(self, context: 'ToolContext') -> 'ToolResult':
        """
        Handle CAPTCHA detection and solving for current page.
        Called by Tool Router when CAPTCHA is detected.
        """
        page = context.browser_page
        session_id = context.session_id

        # 1. Double-check prevention layer
        if not self.prevention.is_applied(page):
            await self.prevention.apply(page)
            # Retry after prevention
            await asyncio.sleep(2)
            detected = detect_captcha_dom(page)
            if not detected:
                return ToolResult.success(await page.content())

        # 2. Classify CAPTCHA
        captcha_types = detect_captcha_dom(page)
        if not captcha_types:
            v3_info = detect_recaptcha_v3(page)
            if v3_info.get('present'):
                captcha_types = ['recaptcha_v3']
            else:
                return ToolResult.success(await page.content())

        captcha_type = captcha_types[0]

        # 3. Check budget
        est_cost = PRICING_PER_SOLVE.get(f'capsolver_{captcha_type}', 0.001)
        if not self.cost_tracker.can_afford(est_cost):
            logger.error(f"CAPTCHA budget exhausted for session {session_id}")
            return ToolResult.partial(
                data=await page.content(),
                reason="captcha_budget_exhausted",
                stats=self.cost_tracker.get_session_stats()
            )

        # 4. Attempt solve
        try:
            url = page.url
            sitekey = await page.evaluate('''() => {
                const el = document.querySelector('[data-sitekey]');
                return el ? el.dataset.sitekey : null;
            }''')

            result = self.fallback_chain.solve(
                captcha_type=captcha_type,
                sitekey=sitekey,
                url=url
            )

            # 5. Inject token
            await self._inject_token(page, captcha_type, result['token'])

            return ToolResult.success(await page.content())

        except BudgetExceededError:
            return ToolResult.partial(
                data=await page.content(),
                reason="budget_exceeded",
                stats=self.cost_tracker.get_session_stats()
            )
        except Exception as e:
            logger.error(f"CAPTCHA solve failed: {e}")
            return ToolResult.partial(
                data=await page.content(),
                reason=f"solve_failed: {str(e)}",
                stats=self.cost_tracker.get_session_stats()
            )

    async def _inject_token(self, page, captcha_type: str, token: str):
        """Inject solved token into page."""
        injectors = {
            'recaptcha_v2': f'''
                document.getElementById("g-recaptcha-response").value = "{token}";
                if (typeof ___grecaptcha_cfg !== 'undefined') {{
                    Object.values(___grecaptcha_cfg.clients).forEach(c => {{
                        if (c.callback) c.callback("{token}");
                    }});
                }}
            ''',
            'recaptcha_v3': f'''
                document.getElementById("g-recaptcha-response").value = "{token}";
            ''',
            'turnstile': f'''
                document.querySelector('input[name="cf-turnstile-response"]').value = "{token}";
            ''',
            'hcaptcha': f'''
                document.querySelector('textarea[name="h-captcha-response"]').value = "{token}";
            ''',
        }
        script = injectors.get(captcha_type, '')
        if script:
            await page.evaluate(script)
```

### 7.3 Fallback to Alternative Sources

When CAPTCHA solving fails or budget is exceeded, the pipeline falls back to alternative data sources:

```python
class AlternativeSourceRouter:
    """
    Routes to alternative data sources when CAPTCHA blocks primary target.
    Priority order defined by data quality and availability.
    """

    ALTERNATIVES = {
        'news_article': ['rss_feed', 'news_api', 'archive_org'],
        'product_data': ['merchant_api', 'data_aggregator', 'public_feed'],
        'academic_paper': ['arxiv', 'pubmed_api', 'semantic_scholar'],
        'social_media': ['official_api', 'embed_endpoint', 'nitter_alternative'],
        'financial_data': ['yahoo_finance_api', 'alpha_vantage', 'sec_edgar'],
    }

    async def get_alternative(self, primary_source: str, query: dict) -> Optional[dict]:
        """Attempt to retrieve data from alternative sources."""
        alternatives = self.ALTERNATIVES.get(primary_source, [])
        for alt in alternatives:
            try:
                result = await self.query_source(alt, query)
                if result:
                    logger.info(f"Alternative source {alt} succeeded for {primary_source}")
                    return result
            except Exception as e:
                logger.warning(f"Alternative {alt} failed: {e}")
                continue
        return None
```

### 7.4 Session Cleanup

When a session ends (successfully, aborted, or failed), cleanup is performed:

```python
async def cleanup_captcha_session(session_id: str, cost_tracker: CostTracker, browser):
    """
    Perform cleanup after CAPTCHA-involved session.
    Ensures no state leaks between sessions.
    """
    stats = cost_tracker.get_session_stats()

    # 1. Log final stats
    logger.info(f"Session {session_id} CAPTCHA stats: {json.dumps(stats)}")

    # 2. Write session summary to audit log
    audit_entry = {
        "event": "session_cleanup",
        "session_id": session_id,
        "timestamp": datetime.utcnow().isoformat() + "Z",
        "captcha_stats": stats,
        "budget_exceeded": stats['total_cost_usd'] >= cost_tracker.budget.max_total_cost,
    }
    with open('captcha_audit.jsonl', 'a') as f:
        f.write(json.dumps(audit_entry) + '\n')

    # 3. Clear browser state
    await browser.clear_cookies()
    await browser.clear_local_storage()
    await browser.clear_cache()

    # 4. Rotate proxy (if session was CAPTCHA-heavy)
    if stats['solve_count'] > 5:
        logger.info(f"Rotating proxy after {stats['solve_count']} CAPTCHA solves")
        await browser.rotate_proxy()

    # 5. Report metrics
    metrics.gauge("captcha.session_cost", stats['total_cost_usd'])
    metrics.counter("captcha.solve_count", stats['solve_count'])
    if stats['total_cost_usd'] > 0:
        metrics.histogram("captcha.cost_per_session", stats['total_cost_usd'])
```

### 7.5 Integration Summary

| Pipeline Stage | CAPTCHA Module Action | Abort Condition |
|---------------|----------------------|-----------------|
| Query received | No action | - |
| Source selected | Check if source is CAPTCHA-prone | Source in prohibited list |
| Page load | Prevention layer applied | - |
| CAPTCHA detected | Classify type, check budget | Budget exceeded |
| Solve attempted | Fallback chain execution | All providers fail |
| Token injected | Resume extraction | Token rejected |
| Data extracted | Log costs, cleanup | - |
| Session end | Cleanup, proxy rotation | - |

---

## Appendix: Quick Reference Card

### Provider API Keys Setup

```python
# Required environment variables
CAPSOLVER_API_KEY="cap-xxxxxxxxxxxxxxxx"
SOLVECAPTCHA_API_KEY="xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx"
ANTICAPTCHA_API_KEY="xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx"
TWOCAPTCHA_API_KEY="xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx"

# Or pass directly to module config
CAPTCHA_CONFIG = {
    "capsolver_key": "cap-xxxxxxxxxxxxxxxx",
    "solvecaptcha_key": "xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx",
    "anticaptcha_key": "xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx",
    "budget": {
        "max_total_cost": 1.00,
        "max_solves": 50,
        "hard_abort": True
    },
    "prevention": {
        "cloakbrowser": True,
        "proxy_pool": "brightdata",
        "rate_limiting": True,
        "human_emulation": True
    }
}
```

### Emergency Stop

```python
# Immediately abort all CAPTCHA solving
def emergency_stop():
    """Kill switch for CAPTCHA operations."""
    global CAPTCHA_ENABLED
    CAPTCHA_ENABLED = False
    logger.critical("CAPTCHA module EMERGENCY STOP activated")
```

### Debug Mode

```python
# Enable debug logging for CAPTCHA module
logging.getLogger("captcha").setLevel(logging.DEBUG)

# Dry-run mode (detect but don't solve)
CAPTCHA_DRY_RUN = True  # Logs detections, skips solving
```

---

*Module version: 1.0.0*
*Based on research: captcha_research.md (2025-01-28)*
*Approach: Stealth-first | Prevention > Detection > Solving*
