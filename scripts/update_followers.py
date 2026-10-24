#!/usr/bin/env python3
"""Fetch @sattoa_ball followers through the official X API.
Requires repository Actions secret X_BEARER_TOKEN. Never logs the token.
"""
import json, os, time, urllib.request, urllib.error, urllib.parse
from datetime import datetime, timezone
from pathlib import Path

TOKEN=os.environ.get("X_BEARER_TOKEN","").strip()
if not TOKEN: raise SystemExit("X_BEARER_TOKEN secret is missing. Configure it in GitHub Settings > Secrets and variables > Actions.")
BASE="https://api.x.com/2"
DATA=Path("followers.json")
STATE=Path("followers-progress.json")
now=datetime.now(timezone.utc).isoformat()
def call(path, params=None):
    url=BASE+path+(("?"+urllib.parse.urlencode(params)) if params else "")
    for attempt in range(4):
        req=urllib.request.Request(url,headers={"Authorization":"Bearer "+TOKEN,"User-Agent":"sato-x-analytics/1.0"})
        try:
            with urllib.request.urlopen(req,timeout=40) as res: return json.load(res)
        except urllib.error.HTTPError as e:
            message=e.read().decode("utf-8","replace")[:400]
            if e.code in (429,500,502,503,504) and attempt<3:
                time.sleep(min(60,5*(2**attempt)));continue
            raise RuntimeError("X API HTTP %s: %s"%(e.code,message))
    raise RuntimeError("X API failed")
def read(path,default):
    try:return json.loads(path.read_text(encoding="utf-8"))
    except (FileNotFoundError,ValueError):return default
old=read(DATA,{"users":[]})
existing={str(u.get("id")):u for u in old.get("users",[]) if u.get("id")}
state=read(STATE,{})
if not state.get("cursor"):
    # Begin a fresh scan; preserve first_seen dates from previous scans.
    state={"cursor":None,"pages":0,"scanned":0,"started_at":now}
user=call("/users/by/username/sattoa_ball")
uid=user["data"]["id"]
max_pages=max(1,min(100,int(os.environ.get("MAX_PAGES","100"))))
cursor=state.get("cursor")
complete=False
for page in range(max_pages):
    params={"max_results":1000,"user.fields":"public_metrics,profile_image_url,created_at,verified,protected"}
    if cursor:params["pagination_token"]=cursor
    response=call("/users/"+uid+"/followers",params)
    users=response.get("data",[])
    for u in users:
        k=str(u["id"])
        metrics=u.get("public_metrics",{})
        prior=existing.get(k,{})
        existing[k]={
            "id":k,"username":u.get("username",""),"name":u.get("name",""),
            "followers_count":metrics.get("followers_count"),
            "following_count":metrics.get("following_count"),
            "profile_image_url":u.get("profile_image_url",""),
            "first_seen":prior.get("first_seen",now),
            "account_created_at":u.get("created_at",""),
            "protected":u.get("protected",False)
        }
    state["pages"]+=1
    state["scanned"]+=len(users)
    next_cursor=response.get("meta",{}).get("next_token")
    cursor=next_cursor
    state["cursor"]=cursor
    if not next_cursor:
        complete=True
        break
# Sort only for stable JSON; browser owns interactive ranking.
result={"account":"sattoa_ball","updated_at":now,"scan_complete":complete,
        "scan_started_at":state["started_at"],
        "users":sorted(existing.values(),key=lambda x:x.get("username","").lower())}
DATA.write_text(json.dumps(result,ensure_ascii=False,separators=(",",":")),encoding="utf-8")
if complete:
    STATE.unlink(missing_ok=True)
else:
    STATE.write_text(json.dumps(state,ensure_ascii=False),encoding="utf-8")
print("Saved %d accounts; complete=%s; pages=%d"%(len(existing),complete,state["pages"]))
