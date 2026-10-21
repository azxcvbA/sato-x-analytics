#!/usr/bin/env python3
"""Build 24h/48h observed milestone metrics. No interpolation or fabricated values."""
import json
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
WINDOW_SECONDS = 90 * 60
FIELDS = ("views", "likes", "retweets", "replies", "quotes", "bookmarks")

def parse_date(value):
    try:
        dt = datetime.fromisoformat(str(value).replace("Z", "+00:00"))
        return dt.replace(tzinfo=timezone.utc) if dt.tzinfo is None else dt.astimezone(timezone.utc)
    except (ValueError, TypeError):
        try:
            from email.utils import parsedate_to_datetime
            dt = parsedate_to_datetime(value)
            return dt.astimezone(timezone.utc)
        except (ValueError, TypeError):
            return None

def main():
    data = json.loads((ROOT / "data.json").read_text(encoding="utf-8"))
    history_file = ROOT / "metric-history.json"
    history = json.loads(history_file.read_text(encoding="utf-8")) if history_file.exists() else {}
    posts = history.get("posts", {})
    output = []
    for tweet in data.get("tweets", []):
        tid = str(tweet.get("id", ""))
        created = parse_date(tweet.get("created_at"))
        if not created or not tid:
            continue
        samples = posts.get(tid, {}).get("samples", [])
        row = {"id": tid, "url": tweet.get("url"), "text": tweet.get("text", ""),
               "created_at": created.isoformat(), "milestones": {}}
        for hours in (24, 48):
            target = created.timestamp() + hours * 3600
            eligible = []
            for sample in samples:
                at = parse_date(sample.get("at"))
                if at is None:
                    continue
                offset = at.timestamp() - target
                if abs(offset) <= WINDOW_SECONDS and any(type(sample.get(k)) is int for k in ("views", "likes")):
                    eligible.append((abs(offset), 0 if offset >= 0 else 1, at, sample))
            if eligible:
                _, _, at, sample = min(eligible, key=lambda item: (item[0], item[1]))
                row["milestones"][str(hours)] = {
                    "observed_at": at.isoformat(),
                    "offset_minutes": round((at.timestamp() - target) / 60, 1),
                    **{k: sample[k] for k in FIELDS if type(sample.get(k)) is int and sample[k] >= 0}
                }
            else:
                row["milestones"][str(hours)] = None
        output.append(row)
    result = {"version": 1, "tolerance_minutes": 90,
              "generated_at": datetime.now(timezone.utc).isoformat(), "posts": output}
    dest = ROOT / "milestone-metrics.json"
    rendered = json.dumps(result, ensure_ascii=False, indent=2) + "\n"
    if not dest.exists() or dest.read_text(encoding="utf-8") != rendered:
        dest.write_text(rendered, encoding="utf-8")
    print("Milestone rows:", len(output), "24h:", sum(bool(r["milestones"]["24"]) for r in output),
          "48h:", sum(bool(r["milestones"]["48"]) for r in output))

if __name__ == "__main__":
    main()
