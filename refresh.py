"""Best-effort FREE refresh for *already-known* posts via unofficial public endpoint.
Does not discover new posts. Missing fields remain untouched. No login or credentials.
External service can stop working at any time. Failures never delete stored data.
"""
import json, os, pathlib, time, urllib.request
from datetime import datetime, timezone
P = pathlib.Path(__file__).resolve().parents[1] / 'data.json'
data = json.loads(P.read_text(encoding='utf-8'))
if os.getenv('SATO_ENABLE_UNOFFICIAL_REFRESH') != '1':
    print('Unofficial refresh disabled. Set repository variable SATO_ENABLE_UNOFFICIAL_REFRESH=1 to opt in.')
    raise SystemExit(0)
# For safety, only recent known posts; avoids hundreds of requests/hour.
posts = sorted((x for x in data.get('tweets',[]) if x.get('author')=='sattoa_ball' and x.get('id')), key=lambda x:x.get('created_at',''), reverse=True)[:20]
changed=0; success=0
for t in posts:
    url=f'https://api.fxtwitter.com/sattoa_ball/status/{t["id"]}'
    try:
        req=urllib.request.Request(url,headers={'User-Agent':'SatoXAnalytics/1.0 (+personal dashboard)','Accept':'application/json'})
        with urllib.request.urlopen(req,timeout=8) as res: body=json.load(res)
        tw=body.get('tweet') or {}
        if str(tw.get('id',''))!=str(t['id']): continue
        success+=1
        # FxTwitter's public response may not contain bookmarks or views.
        for src,dst in [('likes','likes'),('retweets','retweets'),('replies','replies'),('views','views'),('bookmarks','bookmarks')]:
            val=tw.get(src)
            if isinstance(val,int) and not isinstance(val,bool) and val>=0 and t.get(dst)!=val:
                t[dst]=val;changed+=1
    except Exception as exc: print('Skipped',t['id'],type(exc).__name__,str(exc)[:100])
    time.sleep(.25)
print('Successful post lookups:',success,'Changed metrics:',changed)
if changed:
    data['last_metric_refresh_at']=datetime.now(timezone.utc).isoformat()
    P.write_text(json.dumps(data,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
