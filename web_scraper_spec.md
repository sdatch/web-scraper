# Web Content Scraper — Project Specification

## 1. Project Overview

**Objective:** Build a configurable web scraper to extract content from company-owned brand websites and populate a centralized content library.

**Approach:** Config-driven architecture where each brand/site is defined as a configuration block, with a shared scraping engine that adapts to different CMS platforms and rendering strategies.

**Primary Language:** Python 3.11+

---

## 2. Global Configuration

### 2.1 Output & Storage

| Setting | Value |
|---|---|
| Output format | `[json]` |
| Storage destination | `[local filesystem]` |
| Storage path | `C:\Users\ghubl\projects\web_scraper\output` |
| File naming convention | `[{brand}_{content_type}_{date}_{slug}.json]` |

### 2.2 Default Crawl Behavior

These defaults apply to all sites unless overridden at the site level.

| Setting | Default |
|---|---|
| Max crawl depth | `10` |
| Request delay (seconds) | `8` |
| Max concurrent requests | `3` |
| Request timeout (seconds) | `30` |
| Retry count on failure | `3` |
| Respect robots.txt | `[no]` |
| User-Agent string | `Mozilla/5.0 (X11; Linux x86_64; rv:140.0) Gecko/20100101 Firefox/140.0` |

### 2.3 Scrape Mode

| Setting | Value |
|---|---|
| Mode | `[full]` |
| Change detection strategy (if incremental) | `[Last-Modified header | content hash | sitemap lastmod | ___]` |
| State file / tracking location | `C:\Users\ghubl\projects\web_scraper\state` |

### 2.4 Logging & Monitoring

| Setting | Value |
|---|---|
| Log destination | `[file]` |
| Log level | `[INFO]` |
| Log file path (if file) | `C:\Users\ghubl\projects\web_scraper\logs` |
| Alert on failure | `[no]` |

---

## 3. Content Model

Define the fields to extract. Mark each as **required** or **optional**. Add or remove rows as needed.

| Field Name | Type | Required | Notes |
|---|---|---|---|
| `title` | string | yes | Page/article title |
| `body` | string (HTML or markdown) | yes | Main content body |
| `summary` | string | no | Excerpt or meta description |
| `author` | string | no | |
| `publish_date` | datetime | yes | ISO 8601 format |
| `modified_date` | datetime | no | |
| `url` | string | yes | Canonical source URL |
| `brand` | string | yes | Populated from site config |
| `content_type` | string | yes | e.g., article, whitepaper, FAQ |
| `categories` | list[insurance, risk, finance, technology] | no | |
| `tags` | list[insurance, risk, finance, compliance, policy, claim, technology, insuretech, personal, commercial] | no | |
| `images` | list[object] | no | `{url, alt_text, caption}` |
| `metadata` | dict | no | Any additional structured data |
| `_scraped_at` | datetime | yes | Timestamp of extraction |
| `_content_hash` | string | yes | For dedup / change detection |

### 3.1 Content Library Schema Mapping (if applicable)

If the content library has a specific schema, define the mapping here:

```
# scraper field -> content library field
title          -> library_title
body           -> library_body_html
publish_date   -> library_published
...
```

---

## 4. Site Configurations

Copy this block for each brand/site. Site-level settings override globals from Section 2.

### Site: [Brand Name]

#### 4.1 Site Identity

| Setting | Value |
|---|---|
| Brand name | `Insurance Thought Leadership (ITL)` |
| Base URL | `https://www.insurancethoughtleadership.com/` |
| CMS platform | `[Drupal]` |
| Rendering type | `[hybrid]` |

#### 4.2 Authentication (if required)

| Setting | Value |
|---|---|
| Auth required | `[no]` |
| Auth method | `[none]` |

#### 4.3 Crawl Targets

Define which URL paths to include and exclude.

**Include patterns:**
```
# Glob or regex patterns for URLs to scrape
/innovation-technology/*
/insurance-risk/*
/blog/*
/resources/whitepapers/*
/news/*
```

**Exclude patterns:**
```
# Glob or regex patterns for URLs to skip
/blog/tag/*
/blog/author/*
/search*
*.pdf
/advertise/*

**Entry points** (seed URLs or sitemap):
```
# Where to start crawling
https://www.insurancethoughtleadership.com/
# or
https://www.insurancethoughtleadership.com/innovation-technology
# or
https://www.insurancethoughtleadership.com/insurance-risk

#### 4.4 Crawl Behavior Overrides

Leave blank to use global defaults from Section 2.2.

| Setting | Override Value |
|---|---|
| Max crawl depth | `___` |
| Request delay (seconds) | `___` |
| Requires headless browser | `[yes | no]` |
| Custom headers | `___` |
| Pagination strategy | `[next-link | page-param | infinite-scroll | API endpoint | none]` |
| Pagination selector/param | `___` |

#### 4.5 Content Extraction Selectors

Define CSS selectors, XPath, or JSON paths for extracting each content field from this site's pages.

| Content Field | Selector | Notes |
|---|---|---|
| `title` | `___` | e.g., `h1.article-title` |
| `body` | `___` | e.g., `div.article-content` |
| `author` | `___` | |
| `publish_date` | `___` | Note the date format if non-standard |
| `categories` | `___` | |
| `tags` | `___` | |
| `images` | `___` | |
| `summary` | `___` | |


#### 4.6 Site-Specific Notes

```
Any quirks, known issues, or special handling for this site.
e.g., "Lazy-loads images via JavaScript — need headless browser for image URLs"
e.g., "Blog uses React hydration — initial HTML contains content, no JS execution needed"
e.g., "Has an undocumented JSON API at /api/v1/posts that may be easier than scraping"
```

---

## 5. Error Handling

| Scenario | Behavior |
|---|---|
| HTTP 404 | `[log and skip]` |
| HTTP 429 (rate limited) | `[exponential backoff]` |
| HTTP 5xx | `[retry 3 times with backoff]` |
| Connection timeout | `[retry 3 times]` |
| CAPTCHA detected | `[log and skip]` |
| Parsing failure (missing required field) | `[save partial]` |
| Duplicate content detected | `[skip]` |

---

## 6. Infrastructure & Deployment

| Setting | Value |
|---|---|
| Preferred HTTP library | `[requests]` |
| Preferred HTML parser | `[beautifulsoup4]` |
| Headless browser (if needed) | `[playwright]` |
| Scraping framework | `[scrapy]` |
| Run mode | `[CLI tool]` |
| Containerized | `[no]` |
| Python dependency management | `[pip + requirements.txt]` |

---

## 7. Deduplication Strategy

| Setting | Value |
|---|---|
| Dedup key | `[url + content_hash]` |
| Dedup scope | `[per-brand]` |
| On duplicate found | `[update if changed]` |

---

## 8. Testing & Validation

| Requirement | Details |
|---|---|
| Unit tests | `[yes]` — cover parsing logic, selectors, output format |
| Integration tests | `[yes]` — end-to-end against a live or mocked site |
| Sample validation | After scraping, validate 5 random pages for accuracy |
| Expected page counts per site | `[ITL ~300, III: ~1000, IASA: ~250, IAUM: ~250]` |

---

## 9. Phased Rollout Plan

| Phase | Scope | Goal |
|---|---|---|
| Phase 1 | Single pilot site: `https://www.insurancethoughtleadership.com/` | Prove out core engine, selectors, output pipeline |
| Phase 2 | Add `3` additional sites | Validate config-driven approach scales |
| Phase 3 | All `4` sites | Full production rollout |
| Phase 4 | Incremental mode + scheduling | Ongoing automated content sync |

---

```
