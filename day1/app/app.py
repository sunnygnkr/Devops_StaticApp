from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

import requests
from flask import Flask, render_template

try:
    from redgifs import API as RedgifsAPI
    from redgifs.const import Order
except ImportError:  # pragma: no cover - optional dependency fallback
    RedgifsAPI = None
    Order = None


app = Flask(__name__)

REDDIT_URL = "https://www.reddit.com/r/BollywoodMemes/new.json?limit=30"
REQUEST_TIMEOUT = 8
USER_AGENT = "BollywoodMemeWall/1.0"

FALLBACK_REDGIFS_LINKS = [
    {
        "title": "Redgifs latest search: bollywood",
        "url": "https://www.redgifs.com/browse?query=bollywood",
    },
    {
        "title": "Redgifs latest search: desi",
        "url": "https://www.redgifs.com/browse?query=desi",
    },
    {
        "title": "Redgifs latest search: india",
        "url": "https://www.redgifs.com/browse?query=india",
    },
]


def fetch_bollywood_memes(limit: int = 12) -> list[dict[str, str]]:
    headers = {"User-Agent": USER_AGENT}

    try:
        response = requests.get(REDDIT_URL, headers=headers, timeout=REQUEST_TIMEOUT)
        response.raise_for_status()
        payload = response.json()
    except requests.RequestException:
        return []

    items: list[dict[str, str]] = []

    for child in payload.get("data", {}).get("children", []):
        data = child.get("data", {})
        image_url = extract_reddit_image(data)

        if not image_url:
            continue

        items.append(
            {
                "title": data.get("title", "Bollywood meme"),
                "image_url": image_url,
                "post_url": f"https://www.reddit.com{data.get('permalink', '')}",
            }
        )

        if len(items) >= limit:
            break

    return items


def extract_reddit_image(post: dict[str, Any]) -> str | None:
    preview = post.get("preview", {})
    images = preview.get("images", [])

    if images:
        source = images[0].get("source", {})
        image_url = source.get("url")
        if image_url:
            return image_url.replace("&amp;", "&")

    url = post.get("url_overridden_by_dest") or post.get("url")
    if not isinstance(url, str):
        return None

    valid_suffixes = (".jpg", ".jpeg", ".png", ".webp", ".gif")
    if url.lower().endswith(valid_suffixes):
        return url

    return None


def fetch_redgifs_links(limit: int = 8) -> list[dict[str, str]]:
    if RedgifsAPI is None or Order is None:
        return FALLBACK_REDGIFS_LINKS

    try:
        api = RedgifsAPI().login()
        search_result = api.search(["bollywood", "desi", "india"], order=Order.LATEST, count=limit)
    except Exception:
        return FALLBACK_REDGIFS_LINKS

    links: list[dict[str, str]] = []
    seen: set[str] = set()

    for gif in getattr(search_result, "gifs", []) or []:
        url = getattr(gif, "url", None)
        title = getattr(gif, "title", None) or "Open on Redgifs"

        if not url or url in seen:
            continue

        links.append({"title": title, "url": url})
        seen.add(url)

        if len(links) >= limit:
            break

    return links or FALLBACK_REDGIFS_LINKS


@app.route("/")
def index():
    memes = fetch_bollywood_memes()
    redgifs_links = fetch_redgifs_links()

    return render_template(
        "index.html",
        memes=memes,
        redgifs_links=redgifs_links,
        updated_at=datetime.now(timezone.utc),
    )


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=True)
