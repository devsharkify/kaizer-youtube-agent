# ============================================================
# SCRAPER — Fetches RSS, returns only articles WITH images
# ============================================================

import requests, re, logging
from config import RSS_FEEDS, STORIES_PER_BULLETIN

log = logging.getLogger("scraper")

def extract_image(item: dict) -> str:
    """Try every possible RSS field to find an image URL."""
    img = (
        item.get("thumbnail") or
        item.get("media:thumbnail") or
        item.get("media:content") or
        item.get("enclosure") or ""
    )
    if not img:
        for field in ["description", "content:encoded", "content"]:
            html = item.get(field, "")
            m = re.search(r'<img[^>]+src=["\'](https?[^"\']+)["\']', html, re.I)
            if m:
                img = m.group(1)
                break
    return img.strip() if isinstance(img, str) else ""

def fetch_stories() -> list[dict]:
    """Fetch RSS feeds, return articles that have images, up to STORIES_PER_BULLETIN."""
    stories = []
    for url in RSS_FEEDS:
        if len(stories) >= STORIES_PER_BULLETIN:
            break
        try:
            r = requests.get(url, timeout=10)
            data = r.json()
            for item in data.get("items", []):
                if len(stories) >= STORIES_PER_BULLETIN:
                    break
                img = extract_image(item)
                if img and len(img) > 10:
                    stories.append({
                        "title":   item.get("title", "").strip(),
                        "snippet": re.sub(r"<[^>]+>", "", item.get("description", ""))[:200],
                        "image":   img,
                        "source":  data.get("feed", {}).get("title", "News"),
                        "link":    item.get("link", ""),
                    })
                    log.info(f"  ✓ [{len(stories)}] {item.get('title','')[:60]}")
        except Exception as e:
            log.warning(f"Feed error {url[:50]}: {e}")
    log.info(f"Scraper: {len(stories)} stories with images")
    return stories
