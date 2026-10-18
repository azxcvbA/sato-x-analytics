#!/usr/bin/env python3
"""Save a single daily profile snapshot near 23:00 JST. Missing data is not invented."""
import json
import pathlib
import urllib.request
from datetime import datetime, timezone, timedelta

ROOT = pathlib.Path(__file__).resolve().parents[1]
FILE = ROOT / "profile-history.json"
JST = timezone(timedelta(hours=9))
now = datetime.now(timezone.utc)
today = now.astimezone(JST).strftime("%Y-%m-%d")
data = json.loads(FILE.read_text(encoding="utf-8")) if FILE.exists() else {"version": 1, "daily": []}
req = urllib.request.Request("https://api.fxtwitter.com/2/profile/sattoa_ball",
                             headers={"User-Agent": "SatoXAnalytics/2.0", "Accept": "application/json"})
try:
    with urllib.request.urlopen(req, timeout=25) as response:
        payload = json.load(response)
    user = payload.get("user") if payload.get("code") == 200 else None
    if not isinstance(user, dict):
        raise ValueError("Profile API did not return a valid user")
    followers, following = user.get("followers"), user.get("following")
    if type(followers) is not int or type(following) is not int or followers < 0 or following < 0:
        raise ValueError("Profile API returned invalid counts")
    row = {"date": today, "followers": followers, "following": following,
           "observed_at": now.isoformat(), "source": "fxtwitter"}
except Exception as exc:
    print("Profile fetch failed, preserving existing history:", repr(exc))
    raise SystemExit(0)

existing = [x for x in data.get("daily", []) if x.get("date") != today]
existing.append(row)
existing.sort(key=lambda x: x["date"])
FILE.write_text(json.dumps({"version": 1, "daily": existing}, ensure_ascii=False, indent=2)+"\n", encoding="utf-8")
print("Saved profile counts:", row)
