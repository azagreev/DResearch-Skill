# LEGAL_METHODS.md — 100% Legal Paywall Bypass Methods

> **Purpose:** Methods that are fully legal to use — no circumvention of technological protection measures, no ToS violations beyond standard browser access.
> **Status:** Approved for inclusion in Deep Research Skill
> **Last Updated:** 2025

---

## Table of Contents

1. [wallabag](#1-wallabag)
2. [Archive.today / Archive.is / Archive.ph](#2-archivetoday)
3. [Wayback Machine (archive.org)](#3-wayback-machine)
4. [Reader Mode](#4-reader-mode)
5. [Library Access](#5-library-access)
6. [Open Access (Academic)](#6-open-access)
7. [RSS Feeds](#7-rss-feeds)
8. [Newsletter Archives](#8-newsletter-archives)

---

## 1. wallabag

### Overview

| Property | Value |
|----------|-------|
| **Repository** | `wallabag/wallabag` |
| **License** | MIT |
| **Language** | PHP |
| **Stars** | 10k+ |
| **Legal basis** | Uses your own subscription credentials — fully compliant |

**wallabag** is a self-hosted read-it-later application that can fetch full articles from paywalled sources **using your own subscription credentials**. The credentials are encrypted in the database. Because you are accessing content through a valid paid subscription, this method is 100% legal.

### How It Works

1. You deploy wallabag on your own server
2. Configure site credentials for publications you subscribe to
3. wallabag logs in on your behalf and extracts the full article text
4. Returns clean, readable article content via API or web UI

### Supported Sites (Paywall-Compatible)

| Site | Domain | Version Required |
|------|--------|-----------------|
| The Economist | economist.com | 2.3+ |
| Le Monde | lemonde.fr | 2.3+ |
| Le Monde Diplomatique | monde-diplomatique.fr | 2.3+ |
| Le Figaro | lefigaro.fr | 2.3+ |
| Mediapart | mediapart.fr | 2.2+ |
| LWN.net | lwn.net | 2.3+ |
| Courrier International | courrierinternational.com | 2.3+ |
| Arret sur Images | arretsurimages.net | 2.2+ |
| Alternatives Economiques | alternatives-economiques.fr | 2.3+ |
| Canard PC | canardpc.com | 2.3+ |
| GameKult | gamekult.com | 2.3+ |
| Le Point | lepoint.fr | 2.3+ |
| Next INpact | nextinpact.com | 2.2+ |
| Reflets.info | reflets.info | 2.3+ |

### Deployment

```bash
# Docker (recommended)
docker run -p 80:80 -d \
  -v /opt/wallabag/data:/var/www/wallabag/data \
  -v /opt/wallabag/images:/var/www/wallabag/web/assets/images \
  --name wallabag \
  wallabag/wallabag:latest

# Docker Compose with PostgreSQL
# See: https://github.com/wallabag/docker
```

### Configuration

1. Go to **Internal settings** → **Paywall credentials**
2. Add credentials for each site you have a subscription to:
   - Select site from dropdown
   - Enter username/email and password
   - Save (credentials are encrypted at rest)

### API Usage

```bash
# Get OAuth2 token
curl -X POST "http://localhost/token" \
  -d "grant_type=password" \
  -d "client_id=YOUR_CLIENT_ID" \
  -d "client_secret=YOUR_SECRET" \
  -d "username=YOUR_USER" \
  -d "password=YOUR_PASS"

# Save an article (wallabag will use stored credentials)
curl -X POST "http://localhost/api/entries.json" \
  -H "Authorization: Bearer TOKEN" \
  -d "url=https://economist.com/article/example"

# Retrieve article content
curl "http://localhost/api/entries/ENTRY_ID.json" \
  -H "Authorization: Bearer TOKEN"
```

### Integration Code Example

```python
import requests
from urllib.parse import quote

class WallabagClient:
    def __init__(self, base_url: str, client_id: str, client_secret: str,
                 username: str, password: str):
        self.base_url = base_url.rstrip("/")
        self.token = self._authenticate(client_id, client_secret,
                                         username, password)

    def _authenticate(self, client_id, client_secret, username, password):
        r = requests.post(f"{self.base_url}/oauth/v2/token", data={
            "grant_type": "password",
            "client_id": client_id,
            "client_secret": client_secret,
            "username": username,
            "password": password
        })
        return r.json()["access_token"]

    def fetch_article(self, url: str) -> dict:
        """Fetch article using stored paywall credentials."""
        headers = {"Authorization": f"Bearer {self.token}"}
        # Create entry (wallabag fetches with credentials)
        r = requests.post(
            f"{self.base_url}/api/entries.json",
            headers=headers,
            data={"url": url}
        )
        entry = r.json()
        return {
            "title": entry.get("title"),
            "content": entry.get("content"),  # Full HTML
            "text": entry.get("content"),     # Clean text extracted
            "source_url": entry.get("url"),
            "language": entry.get("language"),
        }

# Usage
client = WallabagClient(
    base_url="http://localhost",
    client_id="WALLABAG_CLIENT_ID",
    client_secret="WALLABAG_SECRET",
    username="your_username",
    password="your_password"
)

article = client.fetch_article("https://www.economist.com/leaders/...")
print(article["content"])
```

### Limitations

- Requires **active paid subscriptions** for each paywall site
- Setup effort: moderate (self-hosted deployment)
- Credential management required
- Not all paywall sites supported (see list above)
- Content extraction quality varies by site

---

## 2. Archive.today / Archive.is / Archive.ph

### Overview

| Property | Value |
|----------|-------|
| **URLs** | `https://archive.today`, `https://archive.is`, `https://archive.ph` |
| **Type** | On-demand web archiving service |
| **Legal basis** | Public archive snapshots — no circumvention |
| **Cost** | Free |

Archive.today creates snapshots of web pages on demand. Because it archives pages as a third-party service and presents a static snapshot, it often bypasses paywalls that rely on JavaScript-based dynamic loading. Using public archives is completely legal.

### How It Works

1. Archive.today fetches the requested URL (often with search-bot-like access)
2. Creates a static snapshot of the page
3. Serves the snapshot without JavaScript, paywall scripts, or dynamic checks
4. You view the archived version — no circumvention on your part

### Coverage

| Category | Examples |
|----------|----------|
| Major financial news | WSJ, FT, Bloomberg, Economist |
| General news | NYT, Washington Post, The Atlantic |
| Specialized | HBR, MIT Technology Review, Wired |
| Regional | Le Monde, The Guardian, Der Spiegel |

Archive.today often succeeds where Wayback Machine fails because it creates fresh snapshots with each request and uses varied fetch strategies.

### How to Use

**Web (manual):**
```
https://archive.today/https://ARTICLE_URL
```

**On-demand archiving:**
1. Go to `https://archive.today`
2. Paste the article URL in the form
3. Submit and wait for the snapshot
4. View the archived page

**Direct access to latest snapshot:**
```bash
# Note: archive.today has anti-bot protection
curl "https://archive.today/latest/https://example.com/article"
# May return 403 — use headless browser for automation
```

### Integration Code Example

```python
import requests
from urllib.parse import quote

class ArchiveTodayClient:
    """Archive.today access via simple HTTP requests.
    Note: Archive.today has anti-bot protection; browser automation
    may be needed for some use cases. Direct /latest/ access works
    for already-archived pages."""

    DOMAINS = ["archive.today", "archive.is", "archive.ph"]

    def __init__(self, domain: str = "archive.today"):
        self.domain = domain

    def get_snapshot_url(self, target_url: str) -> str:
        """Return URL of archived snapshot (may need browser to access)."""
        encoded = quote(target_url, safe="")
        return f"https://{self.domain}/latest/{encoded}"

    def fetch_snapshot(self, target_url: str) -> dict:
        """Try to fetch archived snapshot. Returns HTML content."""
        snapshot_url = self.get_snapshot_url(target_url)
        # Use a standard browser User-Agent
        headers = {
            "User-Agent": (
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/120.0.0.0 Safari/537.36"
            )
        }
        resp = requests.get(snapshot_url, headers=headers, timeout=30)
        if resp.status_code == 200:
            return {
                "url": snapshot_url,
                "content": resp.text,
                "status": "success"
            }
        return {"url": snapshot_url, "content": None,
                "status": f"failed:{resp.status_code}"}

# Usage
archive = ArchiveTodayClient()
result = archive.fetch_snapshot("https://ft.com/content/article-id")
if result["status"] == "success":
    print(result["content"][:2000])
```

### Limitations

- **Anti-bot protection** — blocks many automated requests; may need headless browser
- **No official API** — all access is through web interface
- **On-demand archiving takes time** — 10-60 seconds for new snapshots
- **Some sites blocked** — archive.today itself may be blocked in certain regions
- **Not 100% coverage** — some heavily paywalled articles may not archive fully

---

## 3. Wayback Machine (archive.org)

### Overview

| Property | Value |
|----------|-------|
| **Service** | Internet Archive Wayback Machine |
| **API** | `https://web.archive.org/web/2/<URL>` |
| **CDX API** | `https://web.archive.org/cdx/search/cdx` |
| **Legal basis** | Public digital library — fully legal |
| **Cost** | Free |

The Wayback Machine is a digital archive of the World Wide Web. It periodically crawls and saves snapshots of web pages. Accessing archived content is completely legal and is a core function of the Internet Archive as a nonprofit digital library.

### How It Works

1. Wayback Machine crawlers periodically scan the web (including paywalled sites, as they often allow search bots)
2. Snapshots are stored with timestamps
3. You access the stored snapshot — a static HTML copy
4. Paywall JavaScript doesn't execute in the archived version

### Coverage

| Site Category | Coverage Level | Notes |
|---------------|---------------|-------|
| Major news | High | NYT, Guardian, BBC articles often archived |
| Financial press | Medium | FT, WSJ — some articles, not all |
| Blogs / Opinion | Very High | Near-complete coverage |
| Academic | Medium | Many open-access papers archived |

### API Endpoints

```bash
# Check if URL is archived (CDX API)
curl "https://web.archive.org/cdx/search/cdx" \
  -G --data-urlencode "url=ft.com/article" \
  -d "output=json" \
  -d "limit=1"

# Get latest snapshot
curl -L "https://web.archive.org/web/2/https://ft.com/article"

# Get snapshot closest to specific date
curl -L "https://web.archive.org/web/20240115/https://ft.com/article"

# Get oldest snapshot
curl -L "https://web.archive.org/web/0/https://ft.com/article"

# Save page now (create new snapshot)
curl -X POST "https://web.archive.org/save/https://example.com/article"
```

### CDX API Response Format

```json
[
  ["urlkey", "timestamp", "original", "mimetype", "statuscode",
   "digest", "length"],
  ["ft.com/article", "20240115123456", "https://ft.com/article",
   "text/html", "200", "ABC123...", "45231"]
]
```

### Integration Code Example

```python
import requests
from urllib.parse import quote
from datetime import datetime

class WaybackMachineClient:
    """Legal access to Wayback Machine snapshots."""

    CDX_URL = "https://web.archive.org/cdx/search/cdx"
    SNAPSHOT_URL = "https://web.archive.org/web/{timestamp}/{url}"

    def check_availability(self, url: str) -> list[dict]:
        """Check if URL has archived snapshots. Returns list of snapshots."""
        params = {
            "url": url,
            "output": "json",
            "collapse": "timestamp:8",  # One per day
        }
        resp = requests.get(self.CDX_URL, params=params, timeout=30)
        if resp.status_code != 200:
            return []

        data = resp.json()
        if len(data) < 2:
            return []

        headers = data[0]
        snapshots = []
        for row in data[1:]:
            snapshot = dict(zip(headers, row))
            snapshots.append({
                "timestamp": snapshot.get("timestamp"),
                "status": snapshot.get("statuscode"),
                "url": self.SNAPSHOT_URL.format(
                    timestamp=snapshot["timestamp"],
                    url=quote(snapshot["original"], safe="")
                ),
                "date": datetime.strptime(
                    snapshot["timestamp"], "%Y%m%d%H%M%S"
                ) if len(snapshot.get("timestamp", "")) == 14 else None
            })
        return snapshots

    def fetch_latest(self, url: str) -> dict:
        """Fetch the latest available snapshot."""
        snapshots = self.check_availability(url)
        if not snapshots:
            return {"status": "not_archived", "content": None}

        latest = max(snapshots, key=lambda x: x["timestamp"])
        resp = requests.get(latest["url"], timeout=30)
        if resp.status_code == 200:
            return {
                "status": "success",
                "snapshot_url": latest["url"],
                "snapshot_date": latest["date"],
                "content": resp.text,
            }
        return {"status": f"fetch_failed:{resp.status_code}", "content": None}

    def save_page_now(self, url: str) -> dict:
        """Request archiving of a new page (takes time)."""
        save_url = f"https://web.archive.org/save/{url}"
        resp = requests.post(save_url, timeout=60)
        return {
            "status": resp.status_code,
            "url": save_url if resp.status_code == 200 else None
        }

# Usage
wbm = WaybackMachineClient()

# Check availability
snaps = wbm.check_availability("https://www.ft.com/content/article-id")
for s in snaps[-3:]:
    print(f"  {s['date']}: {s['url']}")

# Fetch latest
result = wbm.fetch_latest("https://www.ft.com/content/article-id")
if result["status"] == "success":
    print(result["content"][:2000])
```

### Limitations

- **Coverage gaps** — not all articles are archived
- **Freshness** — snapshots may be hours or days old
- **Speed** — slower than direct access; CDN helps
- **Dynamic content** — JavaScript-heavy pages may not archive well
- ** robots.txt blocks** — some sites block Wayback Machine crawlers

---

## 4. Reader Mode

### Overview

| Property | Value |
|----------|-------|
| **Type** | Built-in browser feature |
| **Browsers** | Firefox, Safari, Edge, Chrome (via flags/extensions) |
| **Legal basis** | Reads already-downloaded content — no circumvention |
| **Cost** | Free |

Reader Mode is a browser feature that strips away clutter (ads, navigation, paywall overlays) and presents a clean reading view. It works by parsing the **already downloaded** HTML and applying a stylesheet — it does not bypass any server-side access control.

### How It Works

1. Browser loads the page (you see the paywall overlay)
2. Reader Mode parses the DOM for article content (`<article>`, `.article-body`, etc.)
3. Extracts the text that was already loaded (often hidden behind CSS overlays)
4. Renders clean, readable version

**Important:** Reader Mode only works when the article content exists in the HTML but is hidden by CSS/JS overlays. It does NOT work for server-side hard paywalls where content is never sent to the browser.

### Coverage

| Site Type | Effectiveness | Notes |
|-----------|--------------|-------|
| Soft paywalls (CSS overlay) | High | Content loaded but hidden |
| Metered paywalls | Medium | May show content if article limit not reached |
| Hard paywalls | None | Content not in HTML at all |
| JavaScript-loaded paywalls | Low | Reader Mode can't execute JS |

### How to Use

**Firefox:**
- URL bar icon (lines icon) or `F9`
- Or add `about:reader?url=` prefix: `about:reader?url=https://example.com/article`

**Safari:**
- Reader button in address bar (appears on compatible pages)

**Edge:**
- Immersive Reader: `F9` or menu button

**Chrome:**
- Enable flag: `chrome://flags/#enable-reader-mode`
- Or install "Reader Mode" extension

**Direct URL (Firefox):**
```
about:reader?url=https://example.com/article
```

### Integration Code Example

```python
import requests
from html.parser import HTMLParser
import re

class ReaderModeExtractor:
    """Python implementation of Reader Mode content extraction.
    Uses Mozilla Readability algorithm principles."""

    def __init__(self):
        self.candidates = []

    def extract(self, url: str) -> dict:
        """Fetch page and extract article content."""
        headers = {
            "User-Agent": (
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/120.0.0.0 Safari/537.36"
            )
        }
        resp = requests.get(url, headers=headers, timeout=30)
        resp.raise_for_status()

        content = self._parse(resp.text)
        return {
            "url": url,
            "title": content.get("title", ""),
            "text": content.get("text", ""),
            "html": content.get("html", ""),
            "method": "reader_mode"
        }

    def _parse(self, html: str) -> dict:
        """Simple content extraction — for production use
        Mozilla's readability.js or trafilatura library."""
        # Extract title
        title_match = re.search(r'<title[^>]*>(.*?)</title>', html, re.I)
        title = title_match.group(1) if title_match else ""

        # Look for common article containers
        article_patterns = [
            r'<article[^>]*>(.*?)</article>',
            r'<div[^>]*class="[^"]*article[^"]*"[^>]*>(.*?)</div>',
            r'<div[^>]*class="[^"]*story[^"]*"[^>]*>(.*?)</div>',
            r'<div[^>]*class="[^"]*content[^"]*"[^>]*>(.*?)</div>',
        ]

        for pattern in article_patterns:
            match = re.search(pattern, html, re.I | re.DOTALL)
            if match:
                article_html = match.group(1)
                # Strip tags for plain text
                text = re.sub(r'<[^>]+>', ' ', article_html)
                text = re.sub(r'\s+', ' ', text).strip()
                return {"title": title, "text": text,
                        "html": article_html}

        return {"title": title, "text": "", "html": ""}

# Better alternative: use Mozilla Readability via Node.js
# or Python libraries: newspaper3k, trafilatura, readability-lxml

# Production-quality extraction with trafilatura:
# pip install trafilatura

def extract_with_trafilatura(url: str) -> dict:
    """Production-ready Reader Mode extraction."""
    from trafilatura import fetch_url, extract

    downloaded = fetch_url(url)
    if not downloaded:
        return {"status": "failed", "text": None}

    result = extract(downloaded, output_format="json",
                     include_comments=False,
                     include_tables=True)
    return result or {"status": "no_content", "text": None}

# Usage
# article = extract_with_trafilatura("https://example.com/article")
# print(article["text"])
```

### Recommended Libraries

| Library | Language | Quality |
|---------|----------|---------|
| `trafilatura` | Python | High — best standalone |
| `readability-lxml` | Python | Medium |
| `newspaper3k` | Python | Medium |
| `mozilla/readability` | JavaScript | High — reference implementation |
| `readability.js` | Node.js | High |

### Limitations

- Only works when content exists in HTML
- Does NOT bypass server-side hard paywalls
- JavaScript-rendered content may not be available
- Quality varies by site structure
- Some sites actively block Reader Mode detection

---

## 5. Library Access

### Overview

| Property | Value |
|----------|-------|
| **Services** | PressReader, Libby (OverDrive), Kanopy |
| **Access** | Free with library card |
| **Legal basis** | Licensed institutional access — fully legal |
| **Cost** | Free (library membership) |

Many public and university libraries subscribe to premium news databases. With a valid library card, you can access full content from WSJ, FT, Economist, NYT, and hundreds of other publications at no cost.

### How It Works

1. Library pays for institutional subscription to news databases
2. Patrons authenticate with library card number
3. Access full content through library's licensed platforms
4. Some offer remote access; others require in-library use

### Services

#### PressReader

| Feature | Details |
|---------|---------|
| **Coverage** | 7,000+ newspapers and magazines |
| **Includes** | WSJ, FT, Economist, NYT, Washington Post, The Guardian |
| **Access** | Web, iOS, Android |
| **Remote** | Most libraries allow remote login |

**How to use:**
1. Get a library card from your local public library
2. Go to your library's website → Digital Resources → PressReader
3. Log in with card number
4. Search and read full publications

**Direct (with library login):**
```
https://www.pressreader.com/catalog/newspapers
```

#### Libby (OverDrive)

- Primarily for e-books and audiobooks
- Some libraries offer magazine access (including The Economist)
- Free app: iOS, Android, web

#### ProQuest / EBSCOhost

- Academic-focused
- Full text of many newspapers and journals
- Typically requires university affiliation

### Integration Code Example

```python
import requests
from urllib.parse import urlencode

class LibraryAccessClient:
    """Access premium content through library subscriptions.
    This is a wrapper pattern — actual access varies by library system."""

    def __init__(self, library_code: str, card_number: str, pin: str):
        """
        library_code: Your library's OverDrive/PressReader code
        card_number: Library card number
        pin: Library card PIN/password
        """
        self.library_code = library_code
        self.card_number = card_number
        self.pin = pin
        self.session = requests.Session()

    def authenticate_pressreader(self) -> bool:
        """Authenticate with PressReader through library SSO."""
        # Flow varies by library — typically:
        # 1. Visit PressReader via library proxy
        # 2. Redirect to library login
        # 3. Receive authentication token
        # 4. Access granted

        auth_url = (
            f"https://www.pressreader.com/"
            f"account/librarysignin?library={self.library_code}"
        )
        login_data = {
            "libraryCardNumber": self.card_number,
            "pin": self.pin
        }
        resp = self.session.post(auth_url, data=login_data)
        return resp.status_code == 200 and "signout" in resp.text.lower()

    def search_article(self, query: str, publication: str = None) -> list[dict]:
        """Search for articles within PressReader."""
        params = {"q": query}
        if publication:
            params["publication"] = publication

        search_url = "https://www.pressreader.com/search"
        resp = self.session.get(search_url, params=params)
        # Parse results (HTML scraping or API if available)
        return self._parse_results(resp.text)

    def _parse_results(self, html: str) -> list[dict]:
        """Parse search results from HTML."""
        # Implementation depends on PressReader's HTML structure
        return []

# Usage
# lib = LibraryAccessClient(library_code="nycpl",
#                           card_number="123456789",
#                           pin="1234")
# if lib.authenticate_pressreader():
#     results = lib.search_article("inflation", "The Economist")
```

### Limitations

- **Requires library card** — must be a member of a participating library
- **Geographic restrictions** — content availability varies by country/region
- **Session-based** — typically requires periodic re-authentication
- **No direct API** — most platforms are web-only, requiring scraping
- **Concurrent user limits** — some libraries have caps
- **Not automatable** — designed for human readers, not bulk access

---

## 6. Open Access (Academic)

### Overview

| Property | Value |
|----------|-------|
| **Services** | Unpaywall, DOAJ, OpenAlex, PubMed Central, arXiv |
| **Type** | Legally open academic publications |
| **Legal basis** | Open Access movement — publisher-authorized free access |
| **Cost** | Free |

Open Access (OA) is a publishing model that makes research articles freely available. Millions of academic papers are legally accessible without subscription. For deep research involving academic sources, this is the primary legal pathway.

### Services

#### Unpaywall

| Feature | Details |
|---------|---------|
| **API** | `https://api.unpaywall.org/v2/{doi}` |
| **Coverage** | 30+ million open access articles |
| **Type** | Finds legal OA versions of paywalled papers |
| **Rate limit** | 100,000 requests/day (free) |

**How to use:**
```bash
# Find OA version by DOI
curl "https://api.unpaywall.org/v2/10.1038/s41586-021-03819-2?email=your@email.com"
```

#### DOAJ (Directory of Open Access Journals)

| Feature | Details |
|---------|---------|
| **URL** | `https://doaj.org` |
| **API** | `https://doaj.org/api/v3/` |
| **Coverage** | 20,000+ OA journals |
| **Search** | Full-text search available |

#### OpenAlex

| Feature | Details |
|---------|---------|
| **URL** | `https://openalex.org` |
| **API** | `https://api.openalex.org` |
| **Coverage** | 250M+ scholarly works |
| **Type** | Open alternative to Microsoft Academic Graph |

#### PubMed Central (PMC)

| Feature | Details |
|---------|---------|
| **URL** | `https://www.ncbi.nlm.nih.gov/pmc` |
| **Coverage** | 10M+ biomedical articles |
| **API** | E-utilities API |
| **Type** | Full-text biomedical and life sciences |

### Integration Code Example

```python
import requests
from urllib.parse import quote

class OpenAccessClient:
    """Unified client for Open Access academic APIs."""

    def __init__(self, email: str):
        """Email required by Unpaywall's polite pool."""
        self.email = email

    def unpaywall_lookup(self, doi: str) -> dict:
        """Find OA version of article by DOI."""
        url = f"https://api.unpaywall.org/v2/{quote(doi)}"
        resp = requests.get(url, params={"email": self.email}, timeout=30)
        if resp.status_code == 200:
            data = resp.json()
            best_oa = data.get("best_oa_location")
            return {
                "doi": doi,
                "title": data.get("title"),
                "is_oa": data.get("is_oa"),
                "oa_url": best_oa.get("url_for_pdf")
                          or best_oa.get("url")
                          if best_oa else None,
                "published": data.get("published_date"),
                "journal": data.get("journal_name"),
            }
        return {"doi": doi, "is_oa": False, "oa_url": None}

    def openalex_search(self, query: str, limit: int = 10) -> list[dict]:
        """Search OpenAlex for works."""
        url = "https://api.openalex.org/works"
        params = {
            "search": query,
            "per_page": limit,
            "filter": "has_pdf:true",
            "mailto": self.email,
        }
        resp = requests.get(url, params=params, timeout=30)
        if resp.status_code != 200:
            return []

        results = []
        for work in resp.json().get("results", []):
            oa_info = work.get("open_access", {})
            results.append({
                "id": work.get("id"),
                "title": work.get("title"),
                "doi": work.get("doi"),
                "is_oa": oa_info.get("is_oa"),
                "oa_url": oa_info.get("oa_url"),
                "cited_by": work.get("cited_by_count"),
                "publication_year": work.get("publication_year"),
            })
        return results

    def pmc_search(self, query: str, limit: int = 10) -> list[dict]:
        """Search PubMed Central."""
        # Step 1: Search for IDs
        search_url = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils/esearch.fcgi"
        search_resp = requests.get(search_url, params={
            "db": "pmc",
            "term": query,
            "retmax": limit,
            "retmode": "json"
        }, timeout=30)
        ids = search_resp.json().get("esearchresult", {}).get("idlist", [])

        if not ids:
            return []

        # Step 2: Fetch summaries
        summary_url = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils/esummary.fcgi"
        summary_resp = requests.get(summary_url, params={
            "db": "pmc",
            "id": ",".join(ids),
            "retmode": "json"
        }, timeout=30)

        results = []
        uids = summary_resp.json().get("result", {}).get("uids", [])
        for uid in uids:
            doc = summary_resp.json()["result"].get(uid, {})
            results.append({
                "pmcid": f"PMC{uid}",
                "title": doc.get("title"),
                "url": f"https://www.ncbi.nlm.nih.gov/pmc/articles/PMC{uid}/",
            })
        return results

# Usage
oa = OpenAccessClient(email="researcher@example.com")

# Find OA version of a paper
result = oa.unpaywall_lookup("10.1038/s41586-021-03819-2")
print(f"OA URL: {result['oa_url']}")

# Search OpenAlex
works = oa.openalex_search("machine learning healthcare", limit=5)
for w in works:
    print(f"{w['title']} — {w['oa_url']}")
```

### Limitations

- **Academic focus** — primarily scholarly articles, not news
- **Coverage varies** — not all papers have OA versions
- **Embargo periods** — some OA versions delayed 6-24 months
- **Preprint vs. published** — arXiv/SSRN versions may differ from final
- **No news content** — for journalism, use other methods

---

## 7. RSS Feeds

### Overview

| Property | Value |
|----------|-------|
| **Type** | Content syndication format |
| **Format** | RSS 2.0, Atom |
| **Legal basis** | Publisher-provided feeds — authorized distribution |
| **Cost** | Free |

Many news sites provide RSS/Atom feeds that contain full article text without paywall restrictions. RSS was designed for content syndication, and publishers use it to distribute their content to aggregators.

### How It Works

1. Sites generate RSS feeds with recent articles
2. Feed often contains full text or extended summaries
3. RSS readers fetch the feed directly — no paywall JavaScript executes
4. Full content available in XML format

### Finding RSS Feeds

| Site | Feed URL Pattern |
|------|-----------------|
| The Guardian | `https://www.theguardian.com/section/rss` |
| NYT | `https://rss.nytimes.com/services/xml/rss/nyt/Section.xml` |
| FT | `https://www.ft.com/rss/home` |
| BBC | `https://feeds.bbci.co.uk/news/rss.xml` |
| Reuters | `https://www.reutersagency.com/feed/?taxonomy...` |
| Ars Technica | `https://feeds.arstechnica.com/arstechnica/index` |
| Hacker News | `https://news.ycombinator.com/rss` |
| Reddit | `https://www.reddit.com/r/subreddit/.rss` |

**Finding feeds programmatically:**
```bash
# Look for <link rel="alternate" type="application/rss+xml"> in HTML
curl -s "https://example.com" | grep -i "rss+xml" | head -5
```

### Integration Code Example

```python
import feedparser
import requests
from bs4 import BeautifulSoup

class RSSFeedClient:
    """Fetch articles via RSS feeds — often bypasses paywall."""

    def __init__(self):
        self.session = requests.Session()
        self.session.headers.update({
            "User-Agent": (
                "Mozilla/5.0 (compatible; RSS Reader Bot/1.0; "
                "+http://example.com/bot)"
            )
        })

    def discover_feed(self, url: str) -> list[str]:
        """Discover RSS feeds on a website."""
        resp = self.session.get(url, timeout=30)
        soup = BeautifulSoup(resp.text, "html.parser")

        feeds = []
        for link in soup.find_all("link", attrs={"type": "application/rss+xml"}):
            href = link.get("href")
            if href:
                feeds.append(requests.compat.urljoin(url, href))
        for link in soup.find_all("link", attrs={"type": "application/atom+xml"}):
            href = link.get("href")
            if href:
                feeds.append(requests.compat.urljoin(url, href))
        return feeds

    def fetch_feed(self, feed_url: str) -> list[dict]:
        """Parse RSS/Atom feed and return entries."""
        parsed = feedparser.parse(feed_url)

        entries = []
        for entry in parsed.entries:
            content = entry.get("content", [{}])[0].get("value", "") \
                      if "content" in entry else entry.get("summary", "")

            entries.append({
                "title": entry.get("title", ""),
                "link": entry.get("link", ""),
                "published": entry.get("published", ""),
                "summary": entry.get("summary", ""),
                "content": content,  # Often full text!
                "authors": [a.get("name") for a in entry.get("authors", [])],
            })
        return entries

    def fetch_full_text(self, feed_url: str) -> list[dict]:
        """Fetch feed and return articles with full content."""
        entries = self.fetch_feed(feed_url)
        full_text_entries = []

        for entry in entries:
            # If feed has full content, use it
            if entry["content"] and len(entry["content"]) > 500:
                full_text_entries.append(entry)
                continue

            # Otherwise try to fetch original page
            try:
                resp = self.session.get(entry["link"], timeout=30)
                soup = BeautifulSoup(resp.text, "html.parser")

                # Try common article selectors
                article = (
                    soup.find("article")
                    or soup.find(class_=re.compile("article|story|content"))
                    or soup.find("main")
                )
                if article:
                    entry["content"] = article.get_text(separator="\n\n")
                    full_text_entries.append(entry)
            except Exception:
                continue

        return full_text_entries

import re  # noqa: E402 — needed for fetch_full_text

# Usage
rss = RSSFeedClient()

# Discover and fetch
feeds = rss.discover_feed("https://arstechnica.com")
if feeds:
    articles = rss.fetch_feed(feeds[0])
    for a in articles[:3]:
        print(f"{a['title']}: {a['link']}")
        if a['content']:
            print(f"  Content preview: {a['content'][:300]}...")
```

### Limitations

- **Feed content varies** — some feeds have full text, others only summaries
- **Feed rate limits** — don't poll too frequently
- **Not all sites offer RSS** — some have removed feeds
- **Authentication** — some premium feeds require API keys
- **Freshness** — RSS reflects published articles, not breaking updates

---

## 8. Newsletter Archives

### Overview

| Property | Value |
|----------|-------|
| **Type** | Publisher-provided email newsletter archives |
| **Access** | Public web pages |
| **Legal basis** | Publisher makes these freely available |
| **Cost** | Free |

Many publications offer email newsletters that contain full article summaries or complete articles. These newsletters often have public web archives that are freely accessible without paywall, even when the original article is behind one.

### How It Works

1. Publication sends newsletter with article content via email
2. Newsletter has a web version (public URL)
3. Web version often contains full text without paywall
4. Archive pages list past newsletters

### Common Newsletter Platforms

| Platform | Archive Pattern | Notes |
|----------|----------------|-------|
| **Substack** | `substack.com/archive` | Full posts often free |
| **Mailchimp** | `usX.campaign-archive.com` | Archive pages public |
| **ConvertKit** | `creator.ck.page` | Often full content |
| **Ghost** | `site.com/archive` | Full content |
| **Beehiiv** | `name.beehiiv.com` | Free tier content |
| **Buttondown** | `buttondown.email/archive` | Full archives |

### Finding Newsletter Archives

```bash
# Substack — archives are usually public
curl "https://author.substack.com/archive"

# Look for archive link on publication website
# Common patterns: /newsletter, /archive, /emails
```

### Integration Code Example

```python
import requests
from bs4 import BeautifulSoup
from urllib.parse import urljoin

class NewsletterArchiveClient:
    """Fetch articles from newsletter archives."""

    def __init__(self):
        self.session = requests.Session()
        self.session.headers.update({
            "User-Agent": (
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/120.0.0.0 Safari/537.36"
            )
        })

    def fetch_substack_archive(self, subdomain: str) -> list[dict]:
        """Fetch posts from a Substack archive."""
        archive_url = f"https://{subdomain}.substack.com/archive"
        resp = self.session.get(archive_url, timeout=30)
        soup = BeautifulSoup(resp.text, "html.parser")

        posts = []
        # Substack uses <a class="post-preview"> or similar
        for link in soup.find_all("a", href=re.compile(r"/p/")):
            post_url = urljoin(archive_url, link["href"])
            title = link.get_text(strip=True)
            if title and post_url not in [p["url"] for p in posts]:
                posts.append({"title": title, "url": post_url})

        # Fetch full content for each post
        results = []
        for post in posts[:10]:  # Limit to first 10
            try:
                content = self._fetch_substack_post(post["url"])
                results.append({**post, "content": content})
            except Exception:
                results.append({**post, "content": None})

        return results

    def _fetch_substack_post(self, url: str) -> str:
        """Fetch full text of a Substack post."""
        resp = self.session.get(url, timeout=30)
        soup = BeautifulSoup(resp.text, "html.parser")

        # Substack article content
        article = (
            soup.find("div", class_="available-content")
            or soup.find("article")
            or soup.find("div", class_="body")
        )
        return article.get_text(separator="\n\n") if article else ""

    def fetch_mailchimp_archive(self, archive_url: str) -> list[dict]:
        """Fetch issues from a Mailchimp campaign archive."""
        resp = self.session.get(archive_url, timeout=30)
        soup = BeautifulSoup(resp.text, "html.parser")

        issues = []
        for link in soup.find_all("a", class_="campaign"):
            issue_url = link.get("href", "")
            title = link.get_text(strip=True)
            if issue_url and title:
                issues.append({"title": title, "url": issue_url})

        return issues

    def search_newsletter_content(self, site_url: str) -> list[dict]:
        """Discover and fetch newsletter content from a site."""
        resp = self.session.get(site_url, timeout=30)
        soup = BeautifulSoup(resp.text, "html.parser")

        # Look for newsletter signup or archive links
        newsletter_links = []
        for link in soup.find_all("a", href=True):
            href = link["href"].lower()
            text = link.get_text(strip=True).lower()
            if any(k in href or k in text for k in
                   ["newsletter", "subscribe", "archive", "email"]):
                full_url = urljoin(site_url, link["href"])
                newsletter_links.append({
                    "text": link.get_text(strip=True),
                    "url": full_url
                })

        return newsletter_links

import re  # noqa: E402

# Usage
client = NewsletterArchiveClient()

# Fetch Substack
posts = client.fetch_substack_archive("paulgraham")
for p in posts[:3]:
    print(f"{p['title']}: {p['url']}")

# Search for newsletter links
links = client.search_newsletter_content("https://example.com")
```

### Limitations

- **Incomplete** — newsletters may have summaries, not full articles
- **Discovery** — finding archives can be manual
- **Platform-specific** — each newsletter platform has different structure
- **Not all publishers** — some don't offer public archives
- **Format** — email HTML can be messy to parse

---

## Summary Comparison

| Method | Coverage | Ease of Use | Speed | Best For |
|--------|----------|-------------|-------|----------|
| **wallabag** | Your subscriptions only | Medium | Fast | Full access to paid content you own |
| **Archive.today** | All web content | Easy | Medium | Breaking news, any site |
| **Wayback Machine** | Most major sites | Easy | Slow | Historical content |
| **Reader Mode** | Soft paywalls only | Very easy | Fast | Quick reading, soft paywalls |
| **Library Access** | Institutional | Medium | Medium | Free access to premium content |
| **Open Access** | Academic papers | Easy | Fast | Research, scholarly articles |
| **RSS Feeds** | Feed-enabled sites | Easy | Fast | Regular monitoring, full-text feeds |
| **Newsletter Archives** | Newsletter publishers | Medium | Medium | Opinions, analysis, niche content |

## Recommended Priority Order

```
1. wallabag (if you have subscription) → full content, fastest
2. Archive.today → on-demand snapshot, highest success rate
3. Wayback Machine → free, reliable for older content
4. RSS Feeds → full text often in feed, great for monitoring
5. Reader Mode → quick, no setup, soft paywalls only
6. Open Access → academic research
7. Newsletter Archives → niche/opinion content
8. Library Access → premium content via institutional login
```

---

> **Disclaimer:** These methods are legal because they either (a) use your own subscriptions, (b) access publicly available archives, (c) read content already sent to your browser, or (d) use publisher-authorized distribution channels. Always respect publishers' Terms of Service and copyright law.
