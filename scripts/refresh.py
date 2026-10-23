#!/usr/bin/env python3
"""Refresh public @sattoa_ball posts from FxTwitter's unofficial API.

Best effort only: no X login or API key; never delete stored posts or
overwrite existing metrics with missing values.
"""
import json
import os
import pathlib
import time
import urllib.error
import urllib.parse
import urllib.request
import xml.etree.ElementTree as ET
import re
from datetime import datetime, timezone

ROOT = pathlib.Path(__file__).resolve().parents[1]
DATA_FILE = ROOT / "data.json"
HANDLE = "sattoa_ball"
API = "https://api.fxtwitter.com/2"
METRICS = {"likes": "likes", "reposts": "retweets", "replies": "replies",
           "quotes": "quotes", "bookmarks": "bookmarks", "views": "views"}
PAGES = 3
OLDER_PER_RUN = 2


def request(path, params=None):
    url = API + path
    if params:
        url += "?" + urllib.parse.urlencode(params)
    req = urllib.request.Request(
        url,
        headers={"User-Agent": "SatoXAnalytics/2.0 (public-data-refresh)",
                 "Accept": "application/json"},
    )
    with urllib.request.urlopen(req, timeout=20) as response:
        payload = json.load(response)
    if not isinstance(payload, dict) or payload.get("code") != 200:
        raise ValueError("FxTwitter response code: " + str(payload.get("code")))
    return payload


def convert(post):
    if not isinstance(post, dict) or post.get("type") != "status":
        return None
    ident = str(post.get("id", ""))
    author = post.get("author")
    if not ident.isdigit() or not isinstance(author, dict):
        return None
    if str(author.get("screen_name", "")).lower() != HANDLE:
        return None
    created = post.get("created_at")
    if not isinstance(created, str) or not created:
        return None
    kind = "reply" if post.get("replying_to") else "quote" if post.get("quote") else "tweet"
    item = {
        "id": ident,
        "url": "https://x.com/" + HANDLE + "/status/" + ident,
        "type": kind,
        "created_at": created,
        "author": HANDLE,
        "author_name": author.get("name") or "さとボール",
        "author_id": str(author.get("id") or ""),
        "text": post.get("text") or "",
        "media": post.get("media") or [],
    }
    for field, target in METRICS.items():
        val = post.get(field)
        if isinstance(val, (int, float)) and not isinstance(val, bool) and val >= 0:
            item[target] = int(val)
    return item



def fallback_posts():
    """Discover recent IDs from public RSS; verify each via status API."""
    ids = []
    for host in ("rsshub.app", "rsshub.rssforever.com"):
        url = "https://" + host + "/twitter/user/" + HANDLE
        try:
            req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
            with urllib.request.urlopen(req, timeout=15) as response:
                root = ET.fromstring(response.read(2000000))
            for node in root.findall(".//item"):
                for link in (node.findtext("link") or "", node.findtext("guid") or ""):
                    match = re.search(r"/status(?:es)?/(\d{10,25})", link)
                    if match and match.group(1) not in ids:
                        ids.append(match.group(1))
            print("RSS discovery found", len(ids), "IDs")
            if ids:
                break
        except Exception as exc:
            print("RSS discovery failed:", url, repr(exc))
    return ids[:80]


def main():
    data = json.loads(DATA_FILE.read_text(encoding="utf-8"))
    rows = data["tweets"]
    indexed = {str(row["id"]): row for row in rows if row.get("id")}
    original_ids = set(indexed)
    fetched = []
    timeline_ok = False
    cursor = None
    seen_cursors = set()

    for page in range(PAGES):
        try:
            payload = request(
                "/profile/" + HANDLE + "/statuses",
                {"count": 20, **({"cursor": cursor} if cursor else {})},
            )
        except Exception as exc:
            print("Timeline request failed:", repr(exc))
            break
        results = payload.get("results")
        if not isinstance(results, list):
            print("Timeline results missing; skipping page")
            break
        timeline_ok = True
        fetched.extend(results)
        print("Timeline page", page + 1, "posts", len(results))
        if not results:
            break
        known = sum(str(p.get("id")) in original_ids for p in results if isinstance(p, dict))
        if page >= 1 and known >= len(results) * 0.9:
            break
        cursor = (payload.get("cursor") or {}).get("bottom")
        if not cursor or cursor in seen_cursors:
            break
        seen_cursors.add(cursor)
        time.sleep(1)


    if not timeline_ok:
        print("WARNING: timeline endpoint unavailable; attempting RSS fallback")
        for ident in fallback_posts():
            if ident in original_ids:
                continue
            try:
                status = request("/status/" + ident).get("status")
                if isinstance(status, dict):
                    fetched.append(status)
            except Exception as exc:
                print("Fallback status failed:", ident, repr(exc))
            time.sleep(0.3)
        if not any((converted := convert(p)) and converted["id"] not in original_ids for p in fetched):
            print("WARNING: no new posts recovered; new-post collection degraded")

    # Check a rotating slice of older posts to keep their engagement updated.
    # Avoid checking the same post twice in a single run.
    recent_ids = {str(p.get("id")) for p in fetched if isinstance(p, dict)}
    older = [ident for ident in indexed if ident not in recent_ids]
    interval = int(datetime.now(timezone.utc).timestamp() // 600)
    if older:
        start = (interval * OLDER_PER_RUN) % len(older)
        selection = (older + older)[start:start + min(OLDER_PER_RUN, len(older))]
        for ident in selection:
            try:
                status = request("/status/" + ident).get("status")
                if isinstance(status, dict):
                    fetched.append(status)
            except Exception as exc:
                print("Older post skipped", ident, repr(exc))
            time.sleep(0.4)

    added = 0
    changed = 0
    for raw in fetched:
        incoming = convert(raw)
        if incoming is None:
            continue
        ident = incoming["id"]
        # Store a per-post observation time only when an actual view count was
        # received. Otherwise later snapshots must not pretend views were sampled.
        if "views" in incoming:
            incoming["metric_observed_at"] = datetime.now(timezone.utc).isoformat()
        if ident not in indexed:
            rows.append(incoming)
            indexed[ident] = incoming
            added += 1
        else:
            row = indexed[ident]
            dirty = False
            if "metric_observed_at" in incoming:
                row["metric_observed_at"] = incoming["metric_observed_at"]
                dirty = True
            for field in METRICS.values():
                if field in incoming and row.get(field) != incoming[field]:
                    row[field] = incoming[field]
                    dirty = True
            if not row.get("text") and incoming["text"]:
                row["text"] = incoming["text"]
                dirty = True
            if dirty:
                changed += 1

    print("New posts:", added, "metric updates:", changed)
    if added or changed:
        rows.sort(key=lambda row: row.get("created_at") or "", reverse=True)
        data["count"] = len(rows)
        data["exported_at"] = datetime.now(timezone.utc).isoformat()
        data["last_metric_refresh_at"] = datetime.now(timezone.utc).isoformat()
        DATA_FILE.write_text(
            json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
        )
    elif not fetched:
        print("No usable API response; previous data preserved.")


if __name__ == "__main__":
    main()
