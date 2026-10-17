#!/usr/bin/env python3
"""Append real timestamped metric snapshots from data.json, without inventing history.

Use after refresh.py. Only append when metrics changed, or when a first sample
is needed. Same metric values at later observation times are intentionally not
added: source freshness is not guaranteed just because a workflow ran.
"""
from __future__ import annotations
import json
import pathlib
from datetime import datetime, timezone

ROOT = pathlib.Path(__file__).resolve().parents[1]
SOURCE = ROOT / "data.json"
DEST = ROOT / "metric-history.json"
FIELDS = ("views", "likes", "retweets", "replies", "quotes", "bookmarks")
MAX_POSTS = 200
MAX_SAMPLES_PER_POST = 1200


def utc_date(value: str | None):
    if not value:
        return None
    try:
        dt = datetime.fromisoformat(value.replace("Z", "+00:00"))
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        return dt.astimezone(timezone.utc)
    except (TypeError, ValueError):
        return None


def main():
    data = json.loads(SOURCE.read_text(encoding="utf-8"))
    existing = json.loads(DEST.read_text(encoding="utf-8")) if DEST.exists() else {}
    history = existing.get("posts", {})
    if not isinstance(history, dict):
        history = {}

    refresh_at = utc_date(data.get("last_metric_refresh_at"))
    # This is the actual metric observation timestamp, not the GitHub job run time.
    # Never treat the 2026-10-14 export as a new observation on 2026-10-17.
    timestamp = refresh_at or utc_date(data.get("exported_at"))
    if not timestamp:
        print("No valid source measurement time; not recording fabricated history")
        return
    observed = timestamp.isoformat(timespec="seconds").replace("+00:00", "Z")

    # Selection by public metric counts; preserve already-tracked posts in history.
    tweets = sorted(
        (t for t in data.get("tweets", []) if str(t.get("id", "")).isdigit()),
        key=lambda t: int(t.get("views") or 0),
        reverse=True,
    )[:MAX_POSTS]

    written = 0
    for t in tweets:
        tid = str(t["id"])
        metrics = {k: int(t[k]) for k in FIELDS
                   if type(t.get(k)) is int and t[k] >= 0}
        if not metrics:
            continue
        # Prefer the exact per-post time from a successful metric request.
        # For older exported data, the dataset-wide refresh is only an
        # approximate first observation; never fabricate finer granularity.
        item_time = utc_date(t.get("metric_observed_at")) or timestamp
        item_observed = item_time.isoformat(timespec="seconds").replace("+00:00", "Z")
        record = history.setdefault(tid, {
            "text": t.get("text", "")[:250],
            "url": t.get("url", f"https://x.com/sattoa_ball/status/{tid}"),
            "samples": [],
        })
        record["text"] = t.get("text", "")[:250]
        record["url"] = t.get("url", record.get("url", ""))
        samples = record.setdefault("samples", [])

        if samples:
            last = samples[-1]
            last_time = utc_date(last.get("at"))
            if last_time and item_time <= last_time:
                continue  # never manufacture a backwards/duplicate measurement
            if not t.get("metric_observed_at") and all(last.get(k) == v for k, v in metrics.items()):
                continue  # unchanged + no confirmed new sample; avoid a fake flat period
        samples.append({"at": item_observed, **metrics})
        if len(samples) > MAX_SAMPLES_PER_POST:
            del samples[:-MAX_SAMPLES_PER_POST]
        written += 1

    result = {"version": 1, "posts": history}
    rendered = json.dumps(result, ensure_ascii=False, indent=2) + "\n"
    if not DEST.exists() or rendered != DEST.read_text(encoding="utf-8"):
        DEST.write_text(rendered, encoding="utf-8")
    print(f"Recorded {written} fresh snapshots at {observed}. "
          f"Tracked posts: {len(history)}")


if __name__ == "__main__":
    main()
