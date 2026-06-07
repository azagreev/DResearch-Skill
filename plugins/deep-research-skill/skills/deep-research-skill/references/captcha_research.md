# Deep Research: SolveCaptcha-Python & CAPTCHA Solving Ecosystem

> **Date:** 2025-01-28
> **Researcher:** Claude Desktop Deep Research Skill
> **Scope:** CAPTCHA solving for automated research pipelines

---

## Table of Contents

1. [SolveCaptcha Python Library](#1-solvecaptcha-python-library)
2. [Pricing Analysis](#2-pricing-analysis)
3. [Performance Benchmarks](#3-performance-benchmarks)
4. [Alternative Services Comparison](#4-alternative-services-comparison)
5. [Integration with Research Pipeline](#5-integration-with-research-pipeline)
6. [Legal & Ethical Considerations](#6-legal--ethical-considerations)
7. [Code Examples](#7-code-examples)
8. [Recommendations](#8-recommendations)

---

## 1. SolveCaptcha Python Library

### 1.1 Overview

**Repository:** [github.com/solvercaptcha/solvecaptcha-python](https://github.com/solvercaptcha/solvecaptcha-python)

| Attribute | Value |
|-----------|-------|
| **Stars** | 152 |
| **Forks** | 8 |
| **License** | MIT |
| **Latest Version** | 1.0.2 (Apr 2025) |
| **Python Support** | Python 3 |
| **Install Command** | `pip3 install solvecaptcha-python` |

The library provides a Python SDK for the **SolveCaptcha API** - a hybrid AI + human CAPTCHA solving service. The codebase is lightweight (~750 lines in `solver.py`, ~120 lines in `api.py`) with minimal dependencies (`requests`).

### 1.2 Architecture

```
solvecaptcha/
|-- __init__.py          # Package exports
|-- api.py               # Low-level HTTP client (ApiClient)
|-- solver.py            # High-level solver (Solvecaptcha class)
```

**ApiClient** (`api.py`):
- Handles POST requests to `https://api.solvecaptcha.com/in.php`
- Handles GET requests to `https://api.solvecaptcha.com/res.php`
- Supports file uploads and base64-encoded images
- Raises `NetworkException` / `ApiException` on failures

**Solvecaptcha class** (`solver.py`):
- Unified interface for all CAPTCHA types
- Built-in polling loop with configurable interval (default: 10s)
- Configurable timeouts: 120s default, 600s for reCAPTCHA
- Supports callbacks (pingback URLs) for async result delivery

### 1.3 Supported CAPTCHA Types

| CAPTCHA Type | Method Name | Key Parameters |
|-------------|-------------|----------------|
| **Image CAPTCHA** (Normal) | `normal()` | `file` or `body` (base64) |
| **Text CAPTCHA** | `text()` | `text`, `lang` |
| **reCAPTCHA v2** | `recaptcha()` | `sitekey`, `url`, `version='v2'` |
| **reCAPTCHA v2 Invisible** | `recaptcha()` | `sitekey`, `url`, `invisible=1` |
| **reCAPTCHA v3** | `recaptcha()` | `sitekey`, `url`, `version='v3'` |
| **reCAPTCHA Enterprise** | `recaptcha()` | `sitekey`, `url`, `enterprise=1` |
| **Cloudflare Turnstile** | `turnstile()` | `sitekey`, `url` |
| **FunCaptcha (Arkose Labs)** | `funcaptcha()` | `publickey`, `url`, `surl` |
| **GeeTest v3** | `geetest()` | `gt`, `challenge`, `url` |
| **GeeTest v4** | `geetest_v4()` | `captcha_id`, `url` |
| **KeyCaptcha** | `keycaptcha()` | `s_s_c_user_id`, `s_s_c_session_id`, etc. |
| **Grid CAPTCHA** | `grid()` | `file` or `body`, `textinstructions` |
| **Click CAPTCHA** | `coordinates()` | `file` or `body`, `textinstructions` |
| **Canvas** | `canvas()` | `file` or `body`, `textinstructions` |
| **Rotate** | `rotate()` | `file` or `body` |

### 1.4 Core API Methods

```python
from solvecaptcha import Solvecaptcha

# Initialize
solver = Solvecaptcha(apiKey="YOUR_API_KEY")

# Check balance
balance = solver.balance()

# Solve any CAPTCHA (returns dict with 'code' and 'token')
result = solver.recaptcha(sitekey="6Ld...", url="https://example.com")
token = result["code"]

# Report incorrect solve (for refund)
solver.report(captcha_id)

# Custom configuration
solver = Solvecaptcha(
    apiKey="YOUR_API_KEY",
    defaultTimeout=120,        # Default: 120s
    recaptchaTimeout=600,      # Default: 600s
    pollingInterval=10,        # Default: 10s
    callback="https://your-callback.com/pingback",
    server="api.solvecaptcha.com"
)
```

### 1.5 Configuration Options

| Parameter | Default | Description |
|-----------|---------|-------------|
| `apiKey` | Required | Your SolveCaptcha API key |
| `softId` | 4844 | Software ID for referral tracking |
| `callback` | None | Pingback URL for async results |
| `defaultTimeout` | 120 | Default timeout (seconds) |
| `recaptchaTimeout` | 600 | reCAPTCHA-specific timeout |
| `pollingInterval` | 10 | Polling interval (seconds) |
| `server` | `api.solvecaptcha.com` | API endpoint |
| `extendedResponse` | None | Return extended response data |

### 1.6 Error Handling

Custom exception hierarchy:

```
SolverExceptions (base)
|-- ValidationException  # Invalid parameters
|-- NetworkException     # HTTP/connection errors
|-- ApiException         # API error responses
|-- TimeoutException     # Solve timeout exceeded
```

### 1.7 Async Support

The library supports async calls via callback (pingback) mechanism. Register a callback URL, and the API will POST the result when the CAPTCHA is solved.

### 1.8 Proxy Support

All CAPTCHA methods accept a `proxy` parameter:

```python
proxy = {'type': 'HTTPS', 'uri': 'login:password@IP_address:PORT'}
result = solver.recaptcha(sitekey="...", url="...", proxy=proxy)
```

---

## 2. Pricing Analysis

### 2.1 SolveCaptcha Pricing

| CAPTCHA Type | Price per 1,000 | Avg. Speed | Free Capacity/min |
|-------------|-----------------|------------|-------------------|
| **Image CAPTCHA** | $0.35 | 2 sec | 12,000 |
| **Text CAPTCHA** | $0.35 | 4 sec | 894 |
| **reCAPTCHA v2** | $0.55 | 3 sec | 11,273 |
| **reCAPTCHA v2 Callback** | $0.55 | 2 sec | 11,273 |
| **reCAPTCHA v2 Invisible** | $0.55 | 2 sec | 11,273 |
| **reCAPTCHA v3** | $0.80 | 2 sec | 757 |
| **reCAPTCHA Enterprise** | $0.55 | 3 sec | 483 |
| **Cloudflare Turnstile** | $0.80 | 3 sec | 2,883 |
| **GeeTest CAPTCHA** | $0.80 | 3 sec | 3,765 |
| **Amazon CAPTCHA** | $0.80 | 3 sec | 5,632 |
| **FunCaptcha (Arkose Labs)** | $2.99 - $50.00 | 18 sec | 578 |
| **ALTCHA** | $1.45 | 17 sec | 3,000 |
| **Friendly CAPTCHA** | $1.45 | 8 sec | 64 |
| **Tencent CAPTCHA** | $1.45 | 10 sec | 64 |
| **DataDome CAPTCHA** | $1.45 | 12 sec | 64 |
| **MTCaptcha** | $1.45 | 5 sec | 64 |
| **CaptchaFox** | $1.45 | 18 sec | 3,000 |
| **VK CAPTCHA** | $1.45 | 5 sec | 64 |
| **Lemin CAPTCHA** | $1.45 | 51 sec | 64 |
| **Temu CAPTCHA** | $1.00 | 16 sec | 3,000 |
| **Slider CAPTCHA** | $1.20 | 5 sec | 64 |

**Key pricing features:**
- **Pay only for successful solves** - no charge for failed attempts
- **Dynamic pricing** - influenced by server workload (ranges $0.50-$1.00 per 1K for standard captchas)
- **99.9% uptime guarantee**
- **No free tier** - minimum top-up required

### 2.2 Competitor Pricing Comparison

| Service | reCAPTCHA v2 | reCAPTCHA v3 | Turnstile | hCaptcha | Image CAPTCHA | Model |
|---------|-------------|--------------|-----------|----------|---------------|-------|
| **SolveCaptcha** | **$0.55/1K** | **$0.80/1K** | **$0.80/1K** | ~$1.00/1K | **$0.35/1K** | Hybrid AI+Human |
| **2Captcha** | $1.00-2.99/1K | $1.45-2.99/1K | $1.45/1K | $1.00-2.00/1K | $0.50-1.00/1K | Human workers |
| **Anti-Captcha** | $0.95-2.00/1K | $1.00-2.00/1K | $2.00/1K | ~$1.50/1K | $0.50-0.70/1K | Human workers |
| **CapSolver** | $0.80/1K | $1.00/1K | $1.20/1K | $0.80/1K | $0.40/1K | AI/ML |
| **DeathByCaptcha** | $2.89/1K | Supported | Supported | Supported | $1.39/1K | Hybrid |
| **AZcaptcha** | $1.00/1K | $1.00/1K | $1.00/1K | $1.00/1K | $1.00/1K | AI |
| **CapMonster Cloud** | $0.50-0.80/1K | $0.50-2.00/1K | Supported | Supported | $0.20/1K | AI |

### 2.3 Volume Discounts

| Service | Volume Discount |
|---------|----------------|
| SolveCaptcha | Dynamic pricing (lower when server load is low) |
| 2Captcha | Automatic discounts based on daily volume |
| Anti-Captcha | Automatic discounts based on daily spending |
| CapSolver | Package discounts up to 50% off pay-per-use |
| AZcaptcha | Unlimited plans starting at $24.9/month |

---

## 3. Performance Benchmarks

### 3.1 Solve Speed Comparison

| CAPTCHA Type | SolveCaptcha | 2Captcha | Anti-Captcha | CapSolver |
|-------------|--------------|----------|--------------|-----------|
| **reCAPTCHA v2** | 2-3 sec | 13-20 sec | 10 sec | 3-9 sec |
| **reCAPTCHA v3** | 2 sec | 20-60 sec | 5 sec | <3 sec |
| **Cloudflare Turnstile** | 3 sec | 10-30 sec | 5 sec | <3 sec |
| **Image CAPTCHA** | 2 sec | 5-15 sec | 5 sec | <1 sec |
| **FunCaptcha** | 18 sec | 15-60 sec | 5 sec | 5-10 sec |
| **GeeTest** | 3 sec | 10-20 sec | 5 sec | <5 sec |

### 3.2 Success Rates

| Service | Reported Success Rate | Notes |
|---------|----------------------|-------|
| SolveCaptcha | ~95-99% | Hybrid AI + human fallback |
| 2Captcha | ~95-99% | Human workers |
| Anti-Captcha | ~99% | Long-running service (since 2007) |
| CapSolver | ~99% | AI-powered |
| DeathByCaptcha | 95-100% | Hybrid model |

### 3.3 Uptime & Reliability

| Service | Uptime Claim | Workers | Free Capacity |
|---------|-------------|---------|---------------|
| SolveCaptcha | 99.9% | AI + Human | 11,273/min (reCAPTCHA v2) |
| 2Captcha | 99.9% | Human pool | Varies by time of day |
| Anti-Captcha | 99.99% | 1,000+ workers | 1,000/min |
| CapSolver | 99.9% | AI (unlimited) | Unlimited |
| DeathByCaptcha | 99.9% | Hybrid | Good |

### 3.4 Rate Limits

- **SolveCaptcha**: Limited by account balance; no explicit rate limits
- **2Captcha**: Depends on worker availability; may return `ERROR_NO_SLOT_AVAILABLE`
- **Anti-Captcha**: High concurrency supported
- **CapSolver**: 100M+ monthly requests capacity

---

## 4. Alternative Services Comparison

### 4.1 Feature Matrix

| Feature | SolveCaptcha | 2Captcha | Anti-Captcha | CapSolver | DeathByCaptcha |
|---------|-------------|----------|-------------|-----------|----------------|
| **Since** | ~2022 | 2012 | 2007 | ~2021 | 2007 |
| **Technology** | Hybrid (AI+Human) | Human workers | Human workers | AI/ML | Hybrid (AI+Human) |
| **reCAPTCHA v2** | $0.55/1K | $1.00+/1K | $0.95+/1K | $0.80/1K | $2.89/1K |
| **reCAPTCHA v3** | $0.80/1K | $1.45+/1K | $1.00+/1K | $1.00/1K | Supported |
| **Cloudflare Turnstile** | $0.80/1K | $1.45/1K | $2.00/1K | $1.20/1K | Supported |
| **FunCaptcha** | $2.99+/1K | $2.00+/1K | $3.00/1K | $1.50/1K | Limited |
| **GeeTest** | $0.80/1K | Supported | $1.80/1K | $1.20/1K | Supported |
| **hCaptcha** | ~$1.00/1K | $1.00+/1K | Supported | $0.80/1K | Supported |
| **AWS WAF** | $0.80/1K | Supported | $2.00/1K | $2.00/1K | Limited |
| **Image CAPTCHA** | $0.35/1K | $0.50+/1K | $0.50+/1K | $0.40/1K | $1.39/1K |
| **Pay for success only** | Yes | No | No | Yes | No |
| **Python SDK** | Yes (official) | Yes (official) | Yes (official) | Yes (community) | Yes |
| **Async support** | Yes (callbacks) | Limited | Yes | Yes | Limited |
| **Browser extensions** | No | Yes | Yes | No | No |
| **Trustpilot Rating** | 4.0 (4 reviews) | N/A | 4.8 (200+ reviews) | N/A | N/A |

### 4.2 Strengths & Weaknesses

#### SolveCaptcha
**Strengths:**
- **Lowest pricing** on the market ($0.55/1K for reCAPTCHA v2)
- Hybrid AI+human approach (AI first, human fallback)
- Pay only for successful solves
- Clean, well-documented Python SDK
- Fast solve times for common CAPTCHA types
- MIT license (open source SDK)

**Weaknesses:**
- Smaller/newer player (fewer reviews)
- Dated dashboard UI
- Limited analytics on usage
- FunCaptcha pricing is volatile ($2.99-$50/1K)
- No browser extension

#### 2Captcha
**Strengths:**
- Widest CAPTCHA type coverage
- Large human worker pool
- Official SDKs for Python, Node.js, PHP
- Browser extensions available
- Long track record (since 2012)
- Good for novel/unusual CAPTCHA types

**Weaknesses:**
- Slower solve times (human-dependent)
- Pay even for unsuccessful attempts
- Variable pricing
- No Turnstile support (pure human model)

#### Anti-Captcha
**Strengths:**
- **Most reliable** (operating since 2007)
- 99.99% uptime
- High Trustpilot rating (4.8/5)
- Browser extensions for Chrome, Firefox, Safari
- Good documentation
- Crypto payment options

**Weaknesses:**
- Higher pricing than SolveCaptcha/CapSolver
- Human-dependent speed
- No pay-for-success model

#### CapSolver
**Strengths:**
- **Fastest AI solving** (sub-5 seconds)
- Excellent Cloudflare support
- Unlimited scalability (AI-based)
- Pay for success only
- Modern JSON API
- 2Captcha API compatible

**Weaknesses:**
- AI limitations with novel CAPTCHA types
- Higher pricing than SolveCaptcha for some types
- Community SDKs (not official)
- Requires quality proxies for best results

#### DeathByCaptcha
**Strengths:**
- Hybrid model (speed + accuracy)
- 17+ years in business
- Multiple API compatibility (2Captcha, Anti-Captcha)
- 24/7 support

**Weaknesses:**
- Higher pricing ($2.89/1K for reCAPTCHA)
- Limited documentation
- Smaller capacity

---

## 5. Integration with Research Pipeline

### 5.1 When to Use CAPTCHA Solving in Research

CAPTCHA solving should be considered a **last resort** in research pipelines. Use it when:

1. **Target data is critical** and no alternative sources exist
2. **Public API is unavailable** or insufficient
3. **CAPTCHA appears sporadically** (not on every request)
4. **Rate limiting without CAPTCHA** has been exhausted
5. **Legal review confirms** the target is public data (no ToS violation)

**Avoid CAPTCHA solving when:**
- Official APIs are available
- Data can be obtained from alternative sources
- Target site explicitly prohibits automation in ToS
- Volume is very high (cost becomes prohibitive)
- CAPTCHA appears on every request (indicates strong anti-bot protection)

### 5.2 Integration Architecture

```
Research Pipeline with CAPTCHA Solving:

[Research Agent] --> [Browser (Playwright/Selenium)] --> [Target Website]
                                 |
                                 v (CAPTCHA detected)
                        [CAPTCHA Detector]
                                 |
                    +------------+------------+
                    |                         |
                    v                         v
            [Try anti-bot bypass]     [Fallback: CAPTCHA Solver]
            (Stealth, proxies)        (SolveCaptcha/2Captcha/CapSolver)
                    |                         |
                    +------------+------------+
                                 |
                                 v
                        [Inject token/solution]
                                 |
                                 v
                        [Continue extraction]
```

### 5.3 CAPTCHA Detection Strategy

```python
# CAPTCHA detection patterns
def detect_captcha(page):
    """Detect common CAPTCHA indicators on page"""
    indicators = {
        'recaptcha_v2': page.locator('.g-recaptcha, iframe[src*="recaptcha"]').count() > 0,
        'recaptcha_v3': 'grecaptcha' in page.content(),
        'turnstile': page.locator('input[name="cf-turnstile-response"]').count() > 0,
        'hcaptcha': page.locator('iframe[src*="hcaptcha"]').count() > 0,
        'funcaptcha': page.locator('iframe[src*="funcaptcha"]').count() > 0,
        'image_captcha': page.locator('img[src*="captcha"], img[id*="captcha"]').count() > 0,
    }
    return [k for k, v in indicators.items() if v]
```

### 5.4 Integration with Browserbase / Cloud Browsers

For cloud browser providers (Browserbase, Bright Data, etc.):

1. **Use built-in CAPTCHA solving** if available (some providers offer it)
2. **Extract CAPTCHA parameters** from the cloud browser session
3. **Send to solver API** from your orchestration layer
4. **Inject the token** back into the cloud browser

```python
# Browserbase + SolveCaptcha integration example
async def solve_with_browserbase(page, solver):
    # Detect CAPTCHA
    captcha_type = detect_captcha(page)
    
    if 'recaptcha_v2' in captcha_type:
        # Extract sitekey
        sitekey = await page.eval_on_selector(
            '.g-recaptcha', 
            'el => el.dataset.sitekey'
        )
        
        # Solve via API
        result = solver.recaptcha(sitekey=sitekey, url=page.url)
        
        # Inject token
        await page.evaluate(f'''
            document.getElementById("g-recaptcha-response").value = "{result["code"]}";
        ''')
        
        # Trigger callback
        await page.evaluate('grecaptcha.callback()')
```

### 5.5 Fallback Chain Strategy

Implement a cascading fallback for reliability:

```python
class CaptchaSolverChain:
    """Multi-provider CAPTCHA solving with fallback"""
    
    def __init__(self, providers):
        """
        providers: list of (name, solver_instance, priority)
        """
        self.providers = sorted(providers, key=lambda x: x[2])
    
    def solve(self, captcha_type, **kwargs):
        for name, solver, _ in self.providers:
            try:
                if captcha_type == 'recaptcha':
                    result = solver.recaptcha(**kwargs)
                elif captcha_type == 'turnstile':
                    result = solver.turnstile(**kwargs)
                # ... etc
                
                if result and result.get('code'):
                    return {'provider': name, 'result': result}
                    
            except Exception as e:
                logger.warning(f"Provider {name} failed: {e}")
                continue
        
        raise Exception("All CAPTCHA providers exhausted")
```

**Recommended fallback order:**
1. **CapSolver** - Fastest, AI-based (for common types)
2. **SolveCaptcha** - Best price/performance ratio
3. **Anti-Captcha** - Most reliable fallback
4. **2Captcha** - Widest type coverage

### 5.6 Cost-Benefit Analysis

| Scenario | Cost/1K requests | Recommendation |
|----------|-----------------|----------------|
| Low-volume research (<100 CAPTCHAs/month) | ~$0.05-0.20 | Use any provider, cost is negligible |
| Medium volume (1K-10K/month) | $0.55-8.00 | SolveCaptcha or CapSolver |
| High volume (100K+/month) | $50-800 | CapSolver packages or AZcaptcha unlimited |
| Sporadic CAPTCHAs (<10/month) | ~$0.01 | Just top up minimum balance |

**Decision tree:**
```
Is there an official API?
  YES --> Use official API
  NO  --> Is the data available elsewhere?
            YES --> Use alternative source
            NO  --> Does the site allow scraping?
                      YES --> Use anti-bot bypass first
                      NO  --> STOP (legal risk)
                            |
                            v (if legally cleared)
                      CAPTCHA encountered?
                        YES --> Try stealth browser
                        NO  --> Normal extraction
                              |
                              v (CAPTCHA still appears)
                        Solve via API
                              |
                              v
                        Track cost vs. data value
```

---

## 6. Legal & Ethical Considerations

### 6.1 Legal Framework

#### United States

**Computer Fraud and Abuse Act (CFAA) - 18 U.S.C. § 1030:**
- CAPTCHA bypassing may be interpreted as "exceeding authorized access"
- The landmark case *hiQ Labs v. LinkedIn* (2022) established some protections for scraping public data
- However, circumventing access controls (CAPTCHAs) creates legal risk
- Violating Terms of Service is generally a **civil matter**, not criminal

**Digital Millennium Copyright Act (DMCA):**
- Anti-circumvention provisions could theoretically apply
- Ticketmaster v. RMG Technologies set precedent for CAPTCHA circumvention claims
- Individual use for research has different risk profile than commercial service

**Key case law:**
| Case | Outcome | Relevance |
|------|---------|-----------|
| *hiQ Labs v. LinkedIn* (2022) | Scraping public data is legal | Protects scraping of public profiles |
| *United States v. Nosal* (2012) | Violating ToS can be criminal | Risk for systematic circumvention |
| *Ticketmaster v. RMG* | Default judgment against bypass tool | DMCA applies to CAPTCHA circumvention tools |

#### European Union

**GDPR (General Data Protection Regulation):**
- Applies to data collection regardless of method (automated or manual)
- Must have lawful basis for processing personal data
- Data minimization principle applies

**EU Digital Services Act (DSA):**
- Requires transparency in automated data collection
- May require consent for certain types of scraping

### 6.2 Terms of Service Implications

Nearly all websites' Terms of Service explicitly:
- **Prohibit automated access** and CAPTCHA circumvention
- Reserve the right to block automated traffic
- Disclaim liability for blocking access

**SolveCaptcha's own ToS** states:
> "You agree to use SolveCaptcha service for **research purposes only**."

This is a critical limitation - the service itself restricts usage to research.

### 6.3 Ethical Guidelines

**Recommended ethical framework:**

1. **Respect robots.txt** directives
2. **Minimize server load** - use rate limiting, cache results
3. **Collect only necessary data** - data minimization
4. **Use official APIs** when available
5. **Consider accessibility** - CAPTCHA solving can help users with disabilities
6. **Document your usage** - maintain audit trail
7. **Seek legal counsel** for high-volume or sensitive use cases

### 6.4 Risk Mitigation Strategies

| Risk Level | Mitigation |
|-----------|-----------|
| **Low** | Scraping public data, low volume, respecting rate limits |
| **Medium** | Using CAPTCHA solving for research, moderate volume |
| **High** | Systematic circumvention, high volume, sensitive data |

**Best practices:**
- Limit CAPTCHA solving to **public, non-personal data**
- Maintain **audit logs** of all CAPTCHA solves
- Implement **cost tracking** to prevent runaway spending
- Use **prevention first** (stealth browsers, proxies) before CAPTCHA solving
- Consider **rotating providers** to avoid dependency

### 6.5 When NOT to Use CAPTCHA Solving

- Sites with **explicit anti-scraping** policies and legal enforcement
- **Financial services** (banking, trading platforms)
- **Healthcare data** (HIPAA-covered entities)
- **Government services** without authorization
- **Ticketing sites** (strong legal precedent against circumvention)
- Any site where data is **not publicly available**

---

## 7. Code Examples

### 7.1 Basic Integration with Playwright

```python
import asyncio
from playwright.async_api import async_playwright
from solvecaptcha import Solvecaptcha

# Initialize solver
solver = Solvecaptcha(apiKey="YOUR_SOLVECAPTCHA_API_KEY")

async def solve_recaptcha_v2(page):
    """Solve reCAPTCHA v2 on current page"""
    # Extract sitekey
    sitekey = await page.eval_on_selector(
        '.g-recaptcha',
        'el => el.dataset.sitekey'
    )
    
    if not sitekey:
        raise ValueError("No reCAPTCHA found on page")
    
    # Solve via API
    result = solver.recaptcha(
        sitekey=sitekey,
        url=page.url,
        version='v2'
    )
    
    # Inject token
    await page.evaluate(f'''
        document.getElementById("g-recaptcha-response").innerHTML = "{result["code"]}";
    ''')
    
    # Submit form
    await page.click('#submit-btn')
    
    return result

async def main():
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        page = await browser.new_page()
        
        await page.goto('https://example.com/form')
        
        # Check for CAPTCHA
        has_captcha = await page.locator('.g-recaptcha').count() > 0
        
        if has_captcha:
            result = await solve_recaptcha_v2(page)
            print(f"CAPTCHA solved: {result['code'][:20]}...")
        
        # Continue with extraction
        data = await page.content()
        
        await browser.close()

if __name__ == '__main__':
    asyncio.run(main())
```

### 7.2 Integration with Selenium

```python
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from solvecaptcha import Solvecaptcha

solver = Solvecaptcha(apiKey="YOUR_SOLVECAPTCHA_API_KEY")

def solve_recaptcha_selenium(driver):
    """Solve reCAPTCHA v2 in Selenium session"""
    # Find reCAPTCHA element
    recaptcha = driver.find_element(By.CLASS_NAME, 'g-recaptcha')
    sitekey = recaptcha.get_attribute('data-sitekey')
    
    # Solve
    result = solver.recaptcha(
        sitekey=sitekey,
        url=driver.current_url,
        version='v2'
    )
    
    # Inject token
    driver.execute_script(f'''
        document.getElementById("g-recaptcha-response").innerHTML = "{result['code']}";
    ''')
    
    # Trigger validation
    driver.execute_script('___grecaptcha_cfg.clients[0].callback()')
    
    return result['code']

# Usage
driver = webdriver.Chrome()
driver.get('https://example.com')

# Solve CAPTCHA if present
try:
    token = solve_recaptcha_selenium(driver)
    print(f"Solved! Token: {token[:20]}...")
except Exception as e:
    print(f"No CAPTCHA or error: {e}")

driver.quit()
```

### 7.3 Cloudflare Turnstile

```python
from solvecaptcha import Solvecaptcha

solver = Solvecaptcha(apiKey="YOUR_API_KEY")

def solve_turnstile(page_url, sitekey):
    """Solve Cloudflare Turnstile"""
    result = solver.turnstile(
        sitekey=sitekey,
        url=page_url,
        # Optional: proxy
        # proxy={'type': 'HTTPS', 'uri': 'user:pass@host:port'}
    )
    return result['code']

# Usage with Playwright
async def bypass_turnstile(page):
    sitekey = await page.eval_on_selector(
        'input[name="cf-turnstile-response"]',
        'el => el.dataset.sitekey'
    )
    
    token = solve_turnstile(page.url, sitekey)
    
    await page.evaluate(f'''
        document.querySelector('input[name="cf-turnstile-response"]').value = "{token}";
    ''')
```

### 7.4 Image CAPTCHA

```python
from solvecaptcha import Solvecaptcha

solver = Solvecaptcha(apiKey="YOUR_API_KEY")

# From file
result = solver.normal(file='path/to/captcha.png')
print(f"Solved: {result['code']}")

# From base64
import base64
with open('captcha.png', 'rb') as f:
    b64 = base64.b64encode(f.read()).decode()

result = solver.normal(body=b64)
print(f"Solved: {result['code']}")

# With options
result = solver.normal(
    file='captcha.png',
    phrase=0,          # 0 = one word, 1 = two+ words
    numeric=4,         # Must contain both numbers AND letters
    minLen=5,
    maxLen=10,
    language='en'
)
```

### 7.5 Error Handling & Retry Logic

```python
import time
import logging
from solvecaptcha import Solvecaptcha
from solvecaptcha.solver import (
    SolverExceptions, 
    ValidationException,
    NetworkException, 
    ApiException,
    TimeoutException
)

logger = logging.getLogger(__name__)

class RobustCaptchaSolver:
    """CAPTCHA solver with retry logic and error handling"""
    
    def __init__(self, api_key, max_retries=3, backoff_factor=2):
        self.solver = Solvecaptcha(apiKey=api_key)
        self.max_retries = max_retries
        self.backoff_factor = backoff_factor
    
    def solve_with_retry(self, method, **kwargs):
        """Solve CAPTCHA with exponential backoff retry"""
        for attempt in range(1, self.max_retries + 1):
            try:
                result = method(**kwargs)
                
                if result and result.get('code'):
                    logger.info(f"CAPTCHA solved on attempt {attempt}")
                    return result
                    
            except ValidationException as e:
                logger.error(f"Invalid parameters: {e}")
                raise  # Don't retry - fix the code
                
            except (NetworkException, ApiException) as e:
                logger.warning(f"Attempt {attempt} failed: {e}")
                if attempt < self.max_retries:
                    wait = self.backoff_factor ** attempt
                    logger.info(f"Retrying in {wait}s...")
                    time.sleep(wait)
                    
            except TimeoutException as e:
                logger.warning(f"Timeout on attempt {attempt}: {e}")
                if attempt < self.max_retries:
                    time.sleep(5)
                    
        raise Exception(f"Failed to solve CAPTCHA after {self.max_retries} attempts")
    
    def solve_recaptcha(self, **kwargs):
        return self.solve_with_retry(self.solver.recaptcha, **kwargs)
    
    def solve_turnstile(self, **kwargs):
        return self.solve_with_retry(self.solver.turnstile, **kwargs)
    
    def solve_image(self, **kwargs):
        return self.solve_with_retry(self.solver.normal, **kwargs)

# Usage
robust_solver = RobustCaptchaSolver(api_key="YOUR_KEY")

try:
    result = robust_solver.solve_recaptcha(
        sitekey="6Ld...",
        url="https://example.com"
    )
    print(f"Success: {result['code']}")
except Exception as e:
    logger.error(f"All retries exhausted: {e}")
```

### 7.6 Multi-Provider Fallback

```python
import logging
from solvecaptcha import Solvecaptcha

logger = logging.getLogger(__name__)

class MultiProviderSolver:
    """CAPTCHA solver with provider fallback chain"""
    
    PROVIDERS = {
        'solvecaptcha': {
            'factory': lambda key: Solvecaptcha(apiKey=key),
            'methods': {
                'recaptcha': lambda s, **kw: s.recaptcha(**kw),
                'turnstile': lambda s, **kw: s.turnstile(**kw),
                'image': lambda s, **kw: s.normal(**kw),
            }
        },
        # Add other providers similarly
    }
    
    def __init__(self, provider_configs):
        """
        provider_configs: dict of {name: api_key}
        Priority is determined by dict order (Python 3.7+)
        """
        self.providers = []
        for name, api_key in provider_configs.items():
            config = self.PROVIDERS.get(name)
            if config:
                solver = config['factory'](api_key)
                self.providers.append((name, solver, config['methods']))
    
    def solve(self, captcha_type, **kwargs):
        """Try each provider in order until one succeeds"""
        for name, solver, methods in self.providers:
            method = methods.get(captcha_type)
            if not method:
                continue
                
            try:
                result = method(solver, **kwargs)
                if result and result.get('code'):
                    logger.info(f"Solved via {name}")
                    return {
                        'provider': name,
                        'token': result['code'],
                        'raw': result
                    }
            except Exception as e:
                logger.warning(f"Provider {name} failed: {e}")
                continue
        
        raise Exception("All providers exhausted")

# Usage
multi = MultiProviderSolver({
    'solvecaptcha': 'KEY_1',
    # 'twocaptcha': 'KEY_2',
    # 'anticaptcha': 'KEY_3',
})

result = multi.solve('recaptcha', sitekey='6Ld...', url='https://example.com')
print(f"Solved by {result['provider']}: {result['token'][:20]}...")
```

### 7.7 Async Integration Pattern

```python
import asyncio
from solvecaptcha import Solvecaptcha

solver = Solvecaptcha(apiKey="YOUR_KEY")

async def solve_async(sitekey, page_url):
    """Non-blocking CAPTCHA solve using asyncio.to_thread"""
    loop = asyncio.get_event_loop()
    
    # Run blocking solver in thread pool
    result = await loop.run_in_executor(
        None,  # Default executor
        lambda: solver.recaptcha(sitekey=sitekey, url=page_url)
    )
    
    return result['code']

# Usage in async pipeline
async def research_pipeline(urls):
    tasks = []
    for url in urls:
        task = asyncio.create_task(process_page(url))
        tasks.append(task)
    
    results = await asyncio.gather(*tasks, return_exceptions=True)
    return results

async def process_page(url):
    # ... load page, detect CAPTCHA ...
    token = await solve_async(sitekey='6Ld...', page_url=url)
    # ... inject token, extract data ...
    return {'url': url, 'token': token}
```

### 7.8 Cost Tracking & Budgeting

```python
import json
from pathlib import Path
from datetime import datetime

class CostTracker:
    """Track CAPTCHA solving costs across sessions"""
    
    def __init__(self, log_file='captcha_costs.jsonl'):
        self.log_file = Path(log_file)
        self.session_costs = []
    
    def log_solve(self, provider, captcha_type, cost, success=True):
        """Log a CAPTCHA solve event"""
        entry = {
            'timestamp': datetime.utcnow().isoformat(),
            'provider': provider,
            'type': captcha_type,
            'cost_usd': cost,
            'success': success
        }
        
        self.session_costs.append(entry)
        
        # Append to log file
        with open(self.log_file, 'a') as f:
            f.write(json.dumps(entry) + '\n')
    
    def get_session_stats(self):
        """Get cost statistics for current session"""
        total = sum(e['cost_usd'] for e in self.session_costs)
        by_type = {}
        for e in self.session_costs:
            by_type[e['type']] = by_type.get(e['type'], 0) + e['cost_usd']
        
        return {
            'total_cost': round(total, 4),
            'solve_count': len(self.session_costs),
            'avg_cost': round(total / len(self.session_costs), 6) if self.session_costs else 0,
            'by_type': by_type
        }

# Pricing map (cost per solve, approximate)
PRICING = {
    'recaptcha_v2': 0.00055,    # $0.55/1000
    'recaptcha_v3': 0.00080,    # $0.80/1000
    'turnstile': 0.00080,       # $0.80/1000
    'image': 0.00035,           # $0.35/1000
    'geetest': 0.00080,         # $0.80/1000
    'funcaptcha': 0.00299,      # $2.99/1000
}

# Usage
tracker = CostTracker()

# After each solve
tracker.log_solve('solvecaptcha', 'recaptcha_v2', PRICING['recaptcha_v2'])

# Get stats
print(tracker.get_session_stats())
```

---

## 8. Recommendations

### 8.1 For Deep Research Skill

**Primary Recommendation: SolveCaptcha**

| Criterion | Score | Notes |
|-----------|-------|-------|
| **Price** | 5/5 | Lowest on market ($0.55/1K reCAPTCHA v2) |
| **Speed** | 4/5 | 2-3 seconds for common types |
| **Reliability** | 4/5 | Hybrid AI+human, pay for success |
| **SDK Quality** | 4/5 | Clean Python SDK, MIT license |
| **Type Coverage** | 4/5 | All major types supported |
| **Documentation** | 3.5/5 | Good but could be more detailed |

**When to use each provider:**

| Scenario | Recommended Provider | Why |
|----------|---------------------|-----|
| Cost-sensitive research | **SolveCaptcha** | Lowest price, pay for success |
| Cloudflare-heavy sites | **CapSolver** | Best Turnstile support, fastest |
| Unusual CAPTCHA types | **2Captcha** | Widest type coverage (human workers) |
| Maximum reliability | **Anti-Captcha** | 99.99% uptime since 2007 |
| Very high volume | **AZcaptcha** | Unlimited plans available |

### 8.2 Implementation Strategy

1. **Phase 1: Prevention**
   - Use stealth browsers (Playwright with stealth plugins)
   - Rotate quality residential proxies
   - Implement human-like behavior patterns

2. **Phase 2: Detection**
   - Implement CAPTCHA detection in pipeline
   - Log frequency and types encountered

3. **Phase 3: Solving (if needed)**
   - Integrate SolveCaptcha as primary provider
   - Implement fallback chain (CapSolver -> Anti-Captcha)
   - Track costs per research session

4. **Phase 4: Optimization**
   - Analyze cost vs. data value
   - Switch providers based on CAPTCHA type
   - Consider batching requests to minimize solves

### 8.3 Cost Budget Template

| Research Session | Estimated CAPTCHAs | Cost (SolveCaptcha) | Fallback Budget |
|-----------------|-------------------|---------------------|-----------------|
| Small (< 50 pages) | 0-5 | $0.00-0.004 | $0.01 |
| Medium (50-500 pages) | 5-50 | $0.003-0.04 | $0.05 |
| Large (500-5000 pages) | 50-500 | $0.03-0.40 | $0.50 |
| Extensive (5000+ pages) | 500+ | $0.40+ | $1.00+ |

### 8.4 Final Checklist

Before using CAPTCHA solving in research:

- [ ] Confirmed no official API exists
- [ ] Confirmed data is publicly available
- [ ] Reviewed target site's Terms of Service
- [ ] Confirmed legal compliance (jurisdiction-specific)
- [ ] Implemented anti-bot bypass first
- [ ] Set up cost tracking and budget limits
- [ ] Implemented fallback provider chain
- [ ] Added error handling and retry logic
- [ ] Documented usage for audit trail
- [ ] Have legal counsel contact for high-risk cases

---

## Appendix A: Quick Reference

### SolveCaptcha API Endpoints

| Endpoint | Method | Purpose |
|----------|--------|---------|
| `https://api.solvecaptcha.com/in.php` | POST | Submit CAPTCHA |
| `https://api.solvecaptcha.com/res.php` | GET | Retrieve result |
| `https://api.solvecaptcha.com/res.php?action=getbalance` | GET | Check balance |
| `https://api.solvecaptcha.com/res.php?action=reportbad` | GET | Report incorrect solve |

### Common Error Codes

| Error Code | Meaning | Action |
|-----------|---------|--------|
| `ERROR_NO_SLOT_AVAILABLE` | High server load | Retry with backoff |
| `ERROR_ZERO_BALANCE` | Insufficient funds | Top up account |
| `ERROR_CAPTCHA_UNSOLVABLE` | CAPTCHA too difficult | Try different provider |
| `ERROR_WRONG_USER_KEY` | Invalid API key | Check configuration |
| `ERROR_TOO_BIG_CAPTCHA` | Image too large | Resize or compress |

### Useful Resources

- [SolveCaptcha Python SDK](https://github.com/solvercaptcha/solvecaptcha-python)
- [SolveCaptcha API Docs](https://solvecaptcha.com/captcha-solver-api)
- [SolveCaptcha Pricing](https://solvecaptcha.com/price)
- [2Captcha API Docs](https://2captcha.com/2captcha-api)
- [CapSolver Docs](https://docs.capsolver.com/)
- [Anti-Captcha Docs](https://anti-captcha.com/apidoc)

---

*Report generated by Claude Desktop Deep Research Skill*
*Last updated: 2025-01-28*
