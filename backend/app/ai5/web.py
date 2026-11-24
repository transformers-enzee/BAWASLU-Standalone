"""General-topic live public search for AI-5.

Independent of election-specific search prompts. Uses the application's
public HTTPS reader for bounded read/safe redirect checks and explicitly
separates READ pages from snippets and inaccessible leads.
"""
import os
import re
import secrets
from datetime import datetime,timezone
from concurrent.futures import ThreadPoolExecutor
import httpx
from app.unified_ai.web import safe_url,read_page,official
from app.unified_ai.contract import safe_for_public

RECENT=re.compile(r"\b(latest|today|current|recent|this week|this month|"
                  r"terbaru|terkini|hari ini|minggu ini|update|news|berita|"
                  r"202[5-9]|202\d|yesterday|kemarin|last \d+|past \d+)\b",re.I)
MAX_PAGES=8


def needs_recent(question):
    return bool(RECENT.search(question or ""))


def _source_rows(payload):
    out={}
    calls=[]
    for item in payload.get("output",[]):
        if not isinstance(item,dict):continue
        if item.get("type")=="web_search_call" and item.get("status")=="completed":
            calls.append(item)
            for row in (item.get("action") or {}).get("sources") or []:
                if isinstance(row,dict) and safe_url(row.get("url")):
                    out.setdefault(row["url"],{"url":row["url"],
                        "title":str(row.get("title") or "")[:180],
                        "snippet":str(row.get("snippet") or "")[:450],
                        "published_at":str(row.get("published_at") or row.get("date") or "")[:30]})
        if item.get("type")=="message":
            for part in item.get("content",[]):
                if not isinstance(part,dict):continue
                for note in part.get("annotations",[]):
                    if note.get("type")=="url_citation" and safe_url(note.get("url")):
                        out.setdefault(note["url"],{"url":note["url"],
                            "title":str(note.get("title") or "")[:180],
                            "snippet":"","published_at":""})
    return calls,list(out.values())


def discover(question,key,model,base,as_of,newest=False):
    scope=("Recheck the newest corrections, updates, dates, cancellations and "
           "superseding publications; do not rely on older conflicting results. "
           if newest else
           "Find relevant original articles, primary publications, credible "
           "research and official resources. ")
    instructions=(
      "AI-5 is a GENERAL RESEARCH assistant, not restricted to election oversight. "
      "Today: "+as_of+". "+scope+
      "Search in the language of the question and another language where helpful. "
      "Use the web_search tool and provide attributable URLs. Never invent links, "
      "publication dates or numbers. Primary research and original reporting "
      "should take precedence where available; official BAWASLU/KPU/JDIH/courts "
      "matter for election/legal topics but not unrelated ones. "
      "This is a source-discovery step only; application opens pages separately."
    )
    body={"model":model,"store":False,"tools":[{"type":"web_search"}],
          "tool_choice":"required","include":["web_search_call.action.sources"],
          "max_output_tokens":1800,
          "input":[{"role":"system","content":instructions},
                   {"role":"user","content":question}]}
    try:
        with httpx.Client(timeout=httpx.Timeout(45,connect=7)) as client:
            response=client.post(base.rstrip("/")+"/responses",
               headers={"Authorization":"Bearer "+key,"Content-Type":"application/json"},
               json=body)
        if response.status_code>=400:return {"status":"PROVIDER_HTTP_"+str(response.status_code),"rows":[]}
        payload=response.json()
        calls,rows=_source_rows(payload)
        return {"status":("FOUND" if rows else
                "NO_ATTRIBUTABLE_URLS" if calls else "WEB_SEARCH_NOT_EXECUTED"),"rows":rows}
    except httpx.TimeoutException:return {"status":"TIMEOUT","rows":[]}
    except httpx.HTTPError:return {"status":"NETWORK_ERROR","rows":[]}
    except (ValueError,KeyError,TypeError):return {"status":"INVALID_PROVIDER_RESPONSE","rows":[]}


def research(question,key,model,base,as_of,recent=None):
    now=datetime.now(timezone.utc).isoformat()
    if not safe_for_public(question):
        return {"status":"PUBLIC_QUERY_BLOCKED","sources":[],"as_of":now,"attempts":[],
                "warning":"Private identifiers must not be sent to public search."}
    if not key:return {"status":"SEARCH_NOT_CONFIGURED","sources":[],"as_of":now,"attempts":[]}
    if os.getenv("BAWASLU_ASSISTANT_WEB_SEARCH","true").lower() in ("off","false","no","0"):
        return {"status":"SEARCH_DISABLED","sources":[],"as_of":now,"attempts":[]}
    search_model=(os.getenv("OPENAI_WEB_SEARCH_MODEL") or model).strip()
    recent=needs_recent(question) if recent is None else recent
    stages=[("public search",False)]+([("newest corrections",True)] if recent else [])
    batches=[(name,discover(question,key,search_model,base,as_of,check)) for name,check in stages]
    candidates={};attempts=[]
    for name,resp in batches:
        attempts.append({"phase":name,"status":resp["status"],"discovered":len(resp["rows"])})
        for row in resp["rows"]:
            candidates.setdefault(row["url"].split("#")[0],row)
    sources=list(candidates.values())[:MAX_PAGES]
    with ThreadPoolExecutor(max_workers=4) as pool:
        pages=list(pool.map(read_page,sources))
    pages.sort(key=lambda x:(x.get("updated_at") or x.get("published_at") or "",
                             x.get("type")=="PUBLIC_OFFICIAL"),reverse=True)
    token=secrets.token_hex(3).upper()
    for i,row in enumerate(pages,1):
        row["id"]=f"WEB-{token}-{i}"
        row.setdefault("duplicate_of","")
        row["basis"]="LIVE_PUBLIC_LOOKUP"
        row["reliability"]=("PUBLIC_OFFICIAL_READ_NOT_ADJUDICATED"
              if row["type"]=="PUBLIC_OFFICIAL" else "PUBLIC_REPORT_READ_NOT_VERIFIED")
        row["consulted_at"]=now
    n=sum(x["read_status"]=="READ" for x in pages)
    return {"status":("READ_SOURCES_AVAILABLE" if n else
                      "SNIPPET_ONLY" if any(x["read_status"]=="SNIPPET_ONLY" for x in pages) else
                      "NO_READABLE_PAGES" if pages else
                      next((v["status"] for _,v in batches if v["status"]!="FOUND"),"NO_ATTRIBUTABLE_URLS")),
            "sources":pages,"as_of":now,"attempts":attempts,"read_count":n}
