"""Fresh, independent, public-only search and source reader for Unified AI.

Approved provider: existing configured OpenAI Responses web_search. No private
SmartRadar excerpts, conversation history, or officer identity in discovery.
All URLs are checked before bounded HTTPS retrieval; snippets are never treated
as page text. Pages that cannot be read remain visible in the research audit.
"""
import io
import ipaddress
import json
import logging
import os
import re
import socket
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone
from html.parser import HTMLParser
from urllib.parse import urljoin, urlsplit

import httpx

LOG=logging.getLogger(__name__)
OFFICIAL=("bawaslu.go.id","kpu.go.id","dkpp.go.id","mkri.id",
          "mahkamahagung.go.id","peraturan.bpk.go.id","mpr.go.id",
          "jdihn.go.id","setneg.go.id","kemendagri.go.id","go.id")
MAX_BYTES=1_600_000
MAX_RESULTS=8


def official(url):
    host=(urlsplit(str(url or "")).hostname or "").lower().rstrip(".")
    return any(host==x or host.endswith("."+x) for x in OFFICIAL)


def safe_url(url):
    if not isinstance(url,str) or len(url)>1800:return False
    try:
        p=urlsplit(url)
        host=(p.hostname or "").lower()
        if p.scheme!="https" or not host or p.username or p.password or p.port not in (None,443):
            return False
        if host in ("localhost","0.0.0.0") or host.endswith((".local",".internal",".home",".localhost")):
            return False
        try:
            return ipaddress.ip_address(host).is_global
        except ValueError:
            return "." in host and not host.endswith(".invalid")
    except ValueError:
        return False


def addresses(host):
    try:
        ips={str(ipaddress.ip_address(row[4][0].split("%")[0]))
             for row in socket.getaddrinfo(host,443,type=socket.SOCK_STREAM)}
        return sorted(ips) if ips and all(ipaddress.ip_address(x).is_global for x in ips) else []
    except (socket.gaierror,OSError,ValueError,TypeError):
        return []


class Article(HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.skip=0;self.current_tag="";self.current=[]
        self.paragraphs=[];self.title=[];self.meta={};self.times=[]
    def handle_starttag(self,tag,attrs):
        if tag in ("script","style","svg","noscript","nav","footer","form"):
            self.skip+=1;return
        if self.skip:return
        values=dict(attrs)
        if tag=="meta":
            name=(values.get("property") or values.get("name") or "").lower()
            if name:self.meta[name]=(values.get("content") or "")[:200]
        if tag=="time" and values.get("datetime"):
            self.times.append(values["datetime"][:35])
        if tag in ("p","h1","h2","h3","li","td","th","title"):
            if not self.current_tag:
                self.current_tag=tag;self.current=[]
    def handle_data(self,data):
        if not self.skip and self.current_tag:self.current.append(data)
    def handle_endtag(self,tag):
        if tag in ("script","style","svg","noscript","nav","footer","form") and self.skip:
            self.skip-=1;return
        if self.skip:return
        if tag==self.current_tag:
            value=" ".join(" ".join(self.current).split())
            if tag=="title" and value:self.title.append(value[:170])
            elif len(value)>=28:self.paragraphs.append(value[:1100])
            self.current_tag="";self.current=[]


def date(value):
    text=str(value or "")
    match=re.match(r"^\d{4}-\d\d-\d\d",text)
    return match.group(0) if match else ""


def parse_html(raw,url):
    parser=Article()
    try:parser.feed(raw.decode("utf-8",errors="replace"))
    except (ValueError,AssertionError,UnicodeError):return None
    excerpt=" ".join(parser.paragraphs)[:9000]
    if len(excerpt)<190:return None
    meta=parser.meta
    published=next((date(meta.get(k)) for k in
        ("article:published_time","datepublished","pubdate","dc.date","date")
        if date(meta.get(k))),"") or next((date(x) for x in parser.times if date(x)),"")
    updated=next((date(meta.get(k)) for k in ("article:modified_time","datemodified")
                  if date(meta.get(k))),"")
    title=(meta.get("og:title") or meta.get("twitter:title") or
           next(iter(parser.title),"") or urlsplit(url).hostname or "Public page")
    return {"excerpt":excerpt,"title":title[:170],
            "published_at":published,"updated_at":updated,"document_type":"HTML"}


def parse_pdf(raw,url):
    try:
        from pypdf import PdfReader
        reader=PdfReader(io.BytesIO(raw),strict=False)
        text=" ".join((page.extract_text() or "") for page in reader.pages[:8])[:9000]
        if len(text)<190:return None
        return {"title":urlsplit(url).path.rsplit("/",1)[-1][:170],
                "excerpt":text,"published_at":"","updated_at":"",
                "document_type":"PDF_PARTIAL_FIRST_EIGHT_PAGES"}
    except (ImportError,ValueError,TypeError,KeyError,IndexError,OSError):
        return None


def read_page(source,client_factory=None):
    """Read a bounded public HTTPS source. Resolve + pin a public address per hop."""
    url=source["url"]
    result={"url":url,"title":str(source.get("title") or "")[:170],
            "snippet":str(source.get("snippet") or "")[:500],"read_status":"INACCESSIBLE",
            "excerpt":"","published_at":date(source.get("published_at")),
            "updated_at":"","document_type":"","reason":"Page unavailable"}
    current=url
    for hop in range(4):
        if not safe_url(current):
            result["reason"]="Unsafe or unsupported public URL/redirect";break
        parsed=urlsplit(current)
        ips=addresses(parsed.hostname)
        if not ips:
            result["reason"]="Public DNS resolution failed or returned a private address";break
        address=ips[0]
        host=parsed.hostname
        authority=("["+address+"]") if ":" in address else address
        pinned="https://"+authority+(parsed.path or "/")+("?" + parsed.query if parsed.query else "")
        try:
            factory=client_factory or (lambda:httpx.Client(timeout=httpx.Timeout(9,connect=3),
                                     trust_env=False,follow_redirects=False))
            with factory() as client:
                request=client.build_request("GET",pinned,headers={
                    "Host":host,"Accept":"text/html,application/xhtml+xml,application/pdf",
                    "User-Agent":"SmartRadar-Unified-AI/1.0"},
                    extensions={"sni_hostname":host})
                response=client.send(request,stream=True,follow_redirects=False)
                try:
                    if response.status_code in (301,302,303,307,308):
                        location=response.headers.get("location")
                        if not location:
                            result["reason"]="Redirect without target";break
                        current=urljoin(current,location)
                        result["reason"]="Exceeded redirect limit";continue
                    if response.status_code!=200:
                        result["reason"]="HTTP "+str(response.status_code);break
                    kind=response.headers.get("content-type","").lower()
                    if not any(x in kind for x in ("html","pdf")):
                        result["reason"]="Unsupported source format";break
                    data=bytearray()
                    for chunk in response.iter_bytes(chunk_size=8192):
                        data.extend(chunk)
                        if len(data)>MAX_BYTES:raise ValueError("Source too large")
                    content=(parse_pdf(bytes(data),current) if "pdf" in kind
                             else parse_html(bytes(data),current))
                    if not content:
                        result["reason"]="No sufficiently readable source text";break
                    result.update(content)
                    result["read_status"]="READ"
                    result["resolved_url"]=current
                    result["reason"]="Source content retrieved and parsed"
                    break
                finally:response.close()
        except (httpx.HTTPError,OSError,ValueError,UnicodeError):
            result["reason"]="Public page request failed"
            break
    if result["read_status"]!="READ" and result["snippet"]:
        result["read_status"]="SNIPPET_ONLY"
    result["type"]="PUBLIC_OFFICIAL" if official(result.get("resolved_url") or url) else "PUBLIC_REPORT"
    result["basis"]="LIVE_PUBLIC_LOOKUP"
    result["location_verified"]=False
    return result


def output_text(payload):
    return "\n".join(str(part.get("text") or "") for item in payload.get("output",[])
         if item.get("type")=="message" for part in item.get("content",[])
         if isinstance(part,dict) and part.get("type")=="output_text").strip()


def discovery(question,key,model,base,as_of,freshness=False):
    """Always require a real provider web_search invocation and URL attribution."""
    scope=("Find the newest official corrections, changed schedules, postponements, "
           "updated rulings and original publication dates for this developing topic."
           if freshness else
           "Find the original official records and reputable primary reporting. "
           "Search in Bahasa Indonesia and English where relevant.")
    system=(
        "Public-only election oversight research; no saved SmartRadar data. Today in Indonesia: "+as_of+". "
        +scope+" Search both Indonesian and English terms when useful. "
        "Use the web_search tool. Prefer direct official BAWASLU, KPU, MK, DKPP, "
        "JDIH and original publisher links. News and social claims are not legal verdicts. "
        "Do not invent URLs, statutes, dates, reach figures or social-media population counts. "
        "Concisely summarise cited evidence; the application separately opens and reads source pages."
    )
    request={"model":model,"store":False,"tools":[{"type":"web_search"}],
             "tool_choice":"required","include":["web_search_call.action.sources"],
             "max_output_tokens":2600,
             "input":[{"role":"system","content":system},{"role":"user","content":question}]}
    try:
        with httpx.Client(timeout=httpx.Timeout(48,connect=8)) as client:
            response=client.post(base.rstrip("/")+"/responses",
                headers={"Authorization":"Bearer "+key,"Content-Type":"application/json"},
                json=request)
        if response.status_code>=400:
            return {"status":"PROVIDER_HTTP_"+str(response.status_code),"rows":[],"queries":[]}
        payload=response.json()
        calls=[o for o in payload.get("output",[])
               if isinstance(o,dict) and o.get("type")=="web_search_call" and o.get("status")=="completed"]
        if not calls:
            return {"status":("PROVIDER_INCOMPLETE" if payload.get("status")=="incomplete"
                              else "WEB_SEARCH_NOT_EXECUTED"),"rows":[],"queries":[]}
        urls={};queries=[]
        for call in calls:
            action=call.get("action") or {}
            values=action.get("queries") or action.get("query") or []
            if isinstance(values,str):values=[values]
            queries.extend(x[:170] for x in values if isinstance(x,str))
            for row in action.get("sources") or []:
                if isinstance(row,dict) and safe_url(row.get("url")):
                    urls.setdefault(row["url"],{
                        "url":row["url"],"title":str(row.get("title") or "")[:170],
                        "snippet":str(row.get("snippet") or "")[:500],
                        "published_at":date(row.get("published_at") or row.get("date"))})
        for item in payload.get("output",[]):
            for part in item.get("content",[]) if isinstance(item.get("content"),list) else []:
                for note in part.get("annotations",[]) if isinstance(part,dict) else []:
                    if isinstance(note,dict) and note.get("type")=="url_citation" and safe_url(note.get("url")):
                        urls.setdefault(note["url"],{
                            "url":note["url"],"title":str(note.get("title") or "")[:170],
                            "snippet":"","published_at":""})
        return {"status":"DISCOVERED" if urls else "NO_ATTRIBUTABLE_URLS",
                "rows":list(urls.values())[:20],"queries":queries[:12]}
    except httpx.TimeoutException:
        return {"status":"PROVIDER_TIMEOUT","rows":[],"queries":[]}
    except httpx.HTTPError:
        return {"status":"PROVIDER_NETWORK_ERROR","rows":[],"queries":[]}
    except (ValueError,TypeError,KeyError):
        return {"status":"PROVIDER_INVALID_RESPONSE","rows":[],"queries":[]}


def canonical(url):
    p=urlsplit(url)
    return ((p.hostname or "").lower(),p.path.rstrip("/").casefold())


def run(question,config,key,model,base):
    now=datetime.now(timezone.utc).isoformat()
    if not config["sources"]["publicWeb"]:
        return {"status":"NOT_SELECTED","sources":[],"queries":[],"as_of":now,"attempts":[]}
    from .contract import safe_for_public
    if not safe_for_public(question):
        return {"status":"PUBLIC_QUERY_BLOCKED","sources":[],"queries":[],"as_of":now,
                "attempts":[{"phase":"public search","status":"PRIVATE_QUERY_BLOCKED"}]}
    if not key:
        return {"status":"PROVIDER_NOT_CONFIGURED","sources":[],"queries":[],"as_of":now,"attempts":[]}
    if os.getenv("BAWASLU_ASSISTANT_WEB_SEARCH","true").lower() in ("false","no","off","0"):
        return {"status":"SEARCH_DISABLED","sources":[],"queries":[],"as_of":now,"attempts":[]}
    model=(os.getenv("OPENAI_WEB_SEARCH_MODEL") or model).strip()
    phases=[("discovery",False)]+([("newest updates/corrections",True)] if config["recent"] else [])
    responses=[(name,discovery(question,key,model,base,config["as_of"],fresh)) for name,fresh in phases]
    unique={};queries=[]
    for name,batch in responses:
        queries.extend(batch["queries"])
        for row in batch["rows"]:
            unique.setdefault(canonical(row["url"]),row)
    # Prefer direct official records before secondary reporting, while
    # preserving newer notices and the superseded ones for comparison.
    candidates=sorted(unique.values(),key=lambda x:(
        not official(x["url"]),-(int((date(x.get("published_at")) or "0000")[:4]))))[:MAX_RESULTS]
    with ThreadPoolExecutor(max_workers=4) as pool:
        pages=list(pool.map(read_page,candidates))
    pages.sort(key=lambda x:(x.get("updated_at") or x.get("published_at") or "",
                             x["type"]=="PUBLIC_OFFICIAL"),reverse=True)
    for i,p in enumerate(pages,1):
        p["id"]="WEB-"+str(i)
        p["duplicate_of"]=""
        p["reliability"]="OFFICIAL_PUBLICATION_UNVERIFIED" if p["type"]=="PUBLIC_OFFICIAL" else "ATTRIBUTED_REPORT_UNVERIFIED"
        if config.get("window"):
            refdate=p.get("updated_at") or p.get("published_at") or ""
            p["within_period"]=(config["window"]["start"]<=refdate<=config["window"]["end"]) if refdate else None
    read=sum(p["read_status"]=="READ" for p in pages)
    status=("READ_SOURCES_AVAILABLE" if read else
            "SNIPPET_ONLY" if any(p["read_status"]=="SNIPPET_ONLY" for p in pages) else
            "NO_READABLE_PUBLIC_PAGES" if pages else
            next((b["status"] for _,b in responses if b["status"]!="DISCOVERED"),"NO_ATTRIBUTABLE_URLS"))
    return {"status":status,"sources":pages,"queries":list(dict.fromkeys(queries))[:20],
            "as_of":now,"read_count":read,
            "attempts":[{"phase":name,"status":b["status"],"discovered":len(b["rows"])}
                        for name,b in responses]}
