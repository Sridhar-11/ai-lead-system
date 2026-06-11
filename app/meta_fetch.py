"""
Meta Graph API - Fetch Comments & Messages from Instagram and Facebook
Requirements:
    pip install requests python-dotenv

Setup:
    1. Create a Meta App at https://developers.facebook.com/
    2. Add permissions: pages_read_engagement, pages_messaging,
       instagram_basic, instagram_manage_comments
    3. Generate a long-lived Page Access Token
    4. Set env vars or replace the constants below
"""

import os
import json
import requests
from datetime import datetime
from dotenv import load_dotenv

load_dotenv()

# ── Config ────────────────────────────────────────────────────────────────────
ACCESS_TOKEN    = os.getenv("META_ACCESS_TOKEN", "YOUR_PAGE_ACCESS_TOKEN")
FB_PAGE_ID      = os.getenv("FB_PAGE_ID",        "YOUR_FACEBOOK_PAGE_ID")
IG_USER_ID      = os.getenv("IG_USER_ID",         "YOUR_INSTAGRAM_USER_ID")
API_VERSION     = "v19.0"
BASE_URL        = f"https://graph.facebook.com/{API_VERSION}"
# ─────────────────────────────────────────────────────────────────────────────


def _get(endpoint: str, params: dict) -> dict:
    """GET helper — raises on HTTP or API error."""
    params["access_token"] = ACCESS_TOKEN
    resp = requests.get(f"{BASE_URL}/{endpoint}", params=params, timeout=15)
    resp.raise_for_status()
    data = resp.json()
    if "error" in data:
        raise RuntimeError(f"API error: {data['error']}")
    return data


def _paginate(endpoint: str, params: dict, key: str = "data") -> list:
    """Follow cursor-based pagination and collect all records."""
    results = []
    while True:
        data = _get(endpoint, params)
        results.extend(data.get(key, []))
        next_url = data.get("paging", {}).get("next")
        if not next_url:
            break
        # next_url already has the full URL; extract cursor
        cursor = data["paging"]["cursors"]["after"]
        params = dict(params, after=cursor)
    return results


# ── Facebook ──────────────────────────────────────────────────────────────────

def get_facebook_posts(limit: int = 10) -> list[dict]:
    """Return recent posts from the Facebook Page."""
    return _paginate(
        f"{FB_PAGE_ID}/posts",
        {"fields": "id,message,created_time,story", "limit": limit},
    )


def get_facebook_post_comments(post_id: str, limit: int = 50) -> list[dict]:
    """Return comments for a single Facebook post."""
    return _paginate(
        f"{post_id}/comments",
        {"fields": "id,message,from,created_time,like_count", "limit": limit},
    )


def get_all_facebook_comments(post_limit: int = 10) -> list[dict]:
    """Fetch comments across the most recent N posts."""
    posts    = get_facebook_posts(limit=post_limit)
    all_coms = []
    for post in posts:
        comments = get_facebook_post_comments(post["id"])
        for c in comments:
            c["post_id"]      = post["id"]
            c["post_message"] = post.get("message", post.get("story", ""))
        all_coms.extend(comments)
    return all_coms


def get_facebook_conversations(limit: int = 10) -> list[dict]:
    """Return recent Messenger conversations for the Page."""
    return _paginate(
        f"{FB_PAGE_ID}/conversations",
        {"fields": "id,snippet,updated_time,participants", "limit": limit},
    )


def get_facebook_messages(conversation_id: str, limit: int = 50) -> list[dict]:
    """Return messages inside a Messenger conversation."""
    return _paginate(
        f"{conversation_id}/messages",
        {"fields": "id,message,from,created_time,attachments", "limit": limit},
    )


def get_all_facebook_messages(convo_limit: int = 10) -> list[dict]:
    """Fetch messages across the most recent N conversations."""
    convos   = get_facebook_conversations(limit=convo_limit)
    all_msgs = []
    for conv in convos:
        messages = get_facebook_messages(conv["id"])
        for m in messages:
            m["conversation_id"] = conv["id"]
        all_msgs.extend(messages)
    return all_msgs


# ── Instagram ─────────────────────────────────────────────────────────────────

def get_instagram_media(limit: int = 10) -> list[dict]:
    """Return recent Instagram media (posts / reels / stories)."""
    return _paginate(
        f"{IG_USER_ID}/media",
        {"fields": "id,caption,media_type,timestamp,permalink", "limit": limit},
    )


def get_instagram_comments(media_id: str, limit: int = 50) -> list[dict]:
    """Return comments for a single Instagram media object."""
    return _paginate(
        f"{media_id}/comments",
        {"fields": "id,text,username,timestamp,like_count,replies", "limit": limit},
    )


def get_all_instagram_comments(media_limit: int = 10) -> list[dict]:
    """Fetch comments across the most recent N Instagram posts."""
    media    = get_instagram_media(limit=media_limit)
    all_coms = []
    for item in media:
        comments = get_instagram_comments(item["id"])
        for c in comments:
            c["media_id"]      = item["id"]
            c["media_caption"] = item.get("caption", "")
        all_coms.extend(comments)
    return all_coms


def get_instagram_messages(limit: int = 20) -> list[dict]:
    """
    Return Instagram Direct messages (requires instagram_manage_messages
    permission — available only to approved apps / Meta Business Suite).
    """
    conversations = _paginate(
        f"{IG_USER_ID}/conversations",
        {"platform": "instagram", "fields": "id,participants,updated_time", "limit": limit},
    )
    all_msgs = []
    for conv in conversations:
        messages = _paginate(
            f"{conv['id']}/messages",
            {"fields": "id,message,from,created_time", "limit": 50},
        )
        for m in messages:
            m["conversation_id"] = conv["id"]
        all_msgs.extend(messages)
    return all_msgs


# ── Save helpers ──────────────────────────────────────────────────────────────

def save_json(data: list[dict], filename: str) -> None:
    with open(filename, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False, default=str)
    print(f"  Saved {len(data)} records → {filename}")


# ── Main ──────────────────────────────────────────────────────────────────────

def main():
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    print("=" * 55)
    print("  Meta Graph API — Comments & Messages Fetcher")
    print("=" * 55)

    # ── Facebook comments ─────────────────────────────────
    print("\n[Facebook] Fetching post comments …")
    try:
        fb_comments = get_all_facebook_comments(post_limit=10)
        print(f"  Found {len(fb_comments)} comments")
        save_json(fb_comments, f"facebook_comments_{ts}.json")
    except Exception as e:
        print(f"  ERROR: {e}")

    # ── Facebook messages ─────────────────────────────────
    print("\n[Facebook] Fetching Messenger messages …")
    try:
        fb_messages = get_all_facebook_messages(convo_limit=10)
        print(f"  Found {len(fb_messages)} messages")
        save_json(fb_messages, f"facebook_messages_{ts}.json")
    except Exception as e:
        print(f"  ERROR: {e}")

    # ── Instagram comments ────────────────────────────────
    print("\n[Instagram] Fetching post comments …")
    try:
        ig_comments = get_all_instagram_comments(media_limit=10)
        print(f"  Found {len(ig_comments)} comments")
        save_json(ig_comments, f"instagram_comments_{ts}.json")
    except Exception as e:
        print(f"  ERROR: {e}")

    # ── Instagram DMs ─────────────────────────────────────
    print("\n[Instagram] Fetching Direct Messages …")
    try:
        ig_messages = get_instagram_messages(limit=20)
        print(f"  Found {len(ig_messages)} messages")
        save_json(ig_messages, f"instagram_messages_{ts}.json")
    except Exception as e:
        print(f"  ERROR (DMs need instagram_manage_messages permission): {e}")

    print("\nDone.")


if __name__ == "__main__":
    main()
