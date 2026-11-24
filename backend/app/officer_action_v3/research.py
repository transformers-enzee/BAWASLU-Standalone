"""Independent public research with page-read audit, plus scoped saved snapshots."""
import ipaddress
import json
import re
import socket
from html.parser import HTMLParser
from urllib.parse import urlsplit
import httpx
from .contracts import safe_public_query, utc_now

OFFICIAL = ("bawaslu.go.id","kpu.go.id","dkpp.go.id","mkri.id",
            "mahkamahagung.go.id","mpr.go.id","peraturan.bpk.go.id",
            "setneg.go.id","go.id")
MAX_PAGES = 6
MAX_BYTES = 180_000
MAX_EXCERPT = 2400

def allowed_url(uri):
    if not isinstance(uri,str) or len(uri)>1800:return False
    try:
        u=urlsplit(uri)
        host=(u.hostname or "").lower().rstrip(".")
        return (u.scheme=="https" and u.port in (None,443) and
                u.username is None and u.password is None and bool(host) and
                host not in ("localhost","0.0.0.0") and
                not host.endswith((".local",".internal",".test",".localhost")) and
                not any(c in uri for c in ("\n","\r","\t")))
    except ValueError:return False

def is_official(uri):
    host=(urlsplit(uri).hostname or "").lower()
    return any(host==domain or host.endswith("."+domain) for domain in OFFICIAL)

def global_dns(host):
    try:
        answers=socket.getaddrinfo(host,443,type=socket.SOCK_STREAM)
        addrs=[ipaddress.ip_address(a[4][0].split("%")[0]) for a in answers]
        return bool(addrs) and all(addr.is_global for addr in addrs)
    except (socket.gaierror,ValueError,OSError):
        return False

class Reader(HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.skip=0;self.active=[];self.text=[];self.title="";self.meta={};self.current=[]
    def handle_starttag(self,tag,attrs):
        attrs=dict(attrs)
        if tag in ("script","style","svg","noscript","footer","nav","form"):
            self.skip+=1;return
        if self.skip:return
        if tag=="meta":
            key=(attrs.get("property") or attrs.get("name") or "").casefold()
            if key and attrs.get("content"):self.meta[key]=attrs["content"][:250]
        if tag in ("p","h1","h2","title"):
            self.active.append(tag);self.current=[]
    def handle_endtag(self,tag):
        if tag in ("script","style","svg","noscript","footer","nav","form"):
            if self.skip:self.skip-=1
            return
        if self.skip:return
        if self.active and tag==self.active[-1]:
            text=" ".join(" ".join(self.current).split())
            if tag=="title" and text and not self.title:self.title=text[:180]
            elif tag in ("h1","h2") and text and not self.title:self.title=text[:180]
            elif tag=="p" and len(text)>=35:self.text.append(text[:1300])
            self.active.pop();self.current=[]
    def handle_data(self,data):
        if not self.skip and self.active:self.current.append(data)

def date_from_meta(meta,keys):
    for key in keys:
        value=meta.get(key,"")[:10]
        if re.fullmatch(r"\d{4}-\d{2}-\d{2}",value):return value
    return ""

def parse_html(blob,url):
    parser=Reader()
    try:parser.feed(blob.decode("utf-8",errors="replace"))
    except (ValueError,AssertionError):return None
    excerpt=" ".join(parser.text)[:MAX_EXCERPT]
    if len(excerpt)<240:return None
    meta=parser.meta
    return {"title":(meta.get("og:title") or parser.title or urlsplit(url).hostname or "Public article")[:180],
            "published_at":date_from_meta(meta,["article:published_time","datepublished","date","pubdate","dc.date"]),
            "updated_at":date_from_meta(meta,["article:modified_time","datemodified"]),
            "excerpt":excerpt}

def read_page(url, snippet="", title=""):
    row={"url":url,"title":str(title or "")[:180],"read_status":"INACCESSIBLE",
         "published_at":"","updated_at":"","excerpt":"","snippet":str(snippet or "")[:350],
         "reason":"Unable to read page"}
    if not allowed_url(url) or not global_dns(urlsplit(url).hostname or ""):
        row["reason"]="Non-public or unresolved URL"
        return row
    try:
        with httpx.Client(timeout=httpx.Timeout(7,connect=3),trust_env=False,follow_redirects=False) as client:
            with client.stream("GET",url,headers={"Accept":"text/html","User-Agent":"SmartRadar-Officer-Decision-Research/1.0"},
                               follow_redirects=False) as response:
                peer=response.extensions.get("network_stream")
                addr=peer.get_extra_info("server_addr") if peer else None
                if not addr or not ipaddress.ip_address(str(addr[0]).split("%")[0]).is_global:
                    row["reason"]="Public peer not verified"
                elif response.status_code != 200:
                    row["reason"]="HTTP "+str(response.status_code)+" (redirects not followed)"
                elif "html" not in response.headers.get("content-type","").lower():
                    row["reason"]="Non-HTML result"
                else:
                    chunks=[];n=0
                    for part in response.iter_bytes(chunk_size=8192):
                        n+=len(part)
                        if n>MAX_BYTES:break
                        chunks.append(part)
                    page=parse_html(b"".join(chunks),url)
                    if page:
                        row.update(page);row["read_status"]="READ";row["reason"]="Article body retrieved"
                    else:row["reason"]="No sufficient article body available"
    except (httpx.HTTPError,OSError,ValueError,UnicodeError):
        row["reason"]="Page retrieval failed"
    if row["read_status"]!="READ" and row["snippet"]:
        row["read_status"]="SNIPPET_ONLY"
        row["excerpt"]=row["snippet"]
    return row

def _response_text(payload):
    pieces=[]
    for item in payload.get("output") or []:
        if item.get("type")=="message":
            for p in item.get("content") or []:
                if isinstance(p,dict) and p.get("type") in ("output_text","text"):
                    pieces.append(str(p.get("text") or ""))
    return "\n".join(pieces).strip()

def public_research(question,key,model,base,recent=False):
    """One approved OpenAI live web-search call; no private records passed."""
    if not key or not safe_public_query(question):
        return {"status":"NOT_AVAILABLE" if not key else "PRIVATE_QUERY_BLOCKED",
                "sources":[],"queries":[],"as_of":utc_now()}
    from datetime import datetime,timezone
    today=datetime.now(timezone.utc).date().isoformat()
    bilingual=[f"{question} Indonesia pengumuman resmi terbaru {today}",
               f"{question} English latest official source {today}"]
    if recent:bilingual.append(f"{question} update koreksi penundaan jadwal postponed rescheduled {today}")
    directions=("Public-source discovery only. Search the actual web now, first official Indonesian "
                "institutions and published notices, then independent original reporting. "
                "Search Bahasa Indonesia and English as relevant. Check the date of publication "
                "against the date of the event; for pending schedules check official corrections, "
                "postponements, and newer statements. Return concise search findings and citation links. "
                "Do not present social-media trend statistics without comparable sampling data. "
                "Research queries: "+"; ".join(bilingual))
    try:
        resp=httpx.post(base.rstrip("/")+"/responses",
            headers={"Authorization":"Bearer "+key,"Content-Type":"application/json"},
            json={"model":model,"store":False,"tools":[{"type":"web_search"}],
                  "tool_choice":"required","include":["web_search_call.action.sources"],
                  "max_output_tokens":1350,
                  "input":[{"role":"system","content":directions},
                           {"role":"user","content":question}]},
            timeout=httpx.Timeout(45,connect=8))
        resp.raise_for_status();data=resp.json()
        completed=[o for o in data.get("output",[]) if o.get("type")=="web_search_call" and o.get("status")=="completed"]
        if not completed:return {"status":"NO_SEARCH_COMPLETED","sources":[],"queries":bilingual,"as_of":utc_now()}
        found=[]
        for action in completed:
            for src in (action.get("action") or {}).get("sources",[]):
                if isinstance(src,dict) and allowed_url(src.get("url")):found.append(src)
        for message in data.get("output",[]):
            for item in message.get("content",[]) if isinstance(message.get("content"),list) else []:
                for note in item.get("annotations",[]) if isinstance(item,dict) else []:
                    if note.get("type")=="url_citation" and allowed_url(note.get("url")):
                        found.append({"url":note["url"],"title":note.get("title",""),"snippet":""})
        unique={}
        for src in found:
            u=src.get("url")
            if u and u not in unique:unique[u]=src
        ranked=sorted(unique.values(),key=lambda r:(not is_official(r["url"])))
        pages=[read_page(src["url"],src.get("snippet",""),src.get("title","")) for src in ranked[:MAX_PAGES]]
        ids=[]
        for i,p in enumerate(pages,1):
            p["id"]="P-"+str(i);p["kind"]="OFFICIAL" if is_official(p["url"]) else "PUBLIC_REPORT"
            ids.append(p)
        return {"status":"READ" if any(p["read_status"]=="READ" for p in ids) else "UNREAD_ONLY",
                "sources":ids,"queries":bilingual,"as_of":utc_now(),
                "provider_excerpt":_response_text(data)[:700]}
    except (httpx.HTTPError,ValueError,TypeError,KeyError):
        return {"status":"SEARCH_FAILED","sources":[],"queries":bilingual,"as_of":utc_now()}

def saved_records(db,grant,question,limit=7):
    """New direct, permission-scoped data adaptor; never calls old assistant retrieval."""
    from app.domain import list_intelligence
    words={w for w in re.findall(r"[a-zA-ZÀ-ÿ]{4,}",question.casefold())
           if w not in {"what","about","yang","dalam","these","with","from","this"}}
    ranked=[]
    for record in list_intelligence(db,grant):
        title=str(record.title or "")
        content=str(record.original_content or "")
        corpus=(title+" "+content[:1100]).casefold()
        score=sum(2 if word in title.casefold() else 1 for word in words if word in corpus)
        if score:
            ranked.append((score,record))
    ranked.sort(key=lambda x:x[0],reverse=True)
    results=[]
    for _,rec in ranked[:limit]:
        results.append({"id":"R-"+str(len(results)+1),"kind":"SAVED_RECORD","title":str(rec.title or "")[:180],
                        "url":str(rec.source_url or "")[:1800] if allowed_url(rec.source_url) else "",
                        "published_at":str(rec.publication_date or "")[:32],
                        "excerpt":str(rec.original_content or "")[:1500],
                        "read_status":"SAVED_SNAPSHOT",
                        "record_id":str(rec.intelligence_id or "")[:64],
                        "review_status":"Officer verification not implied"})
    return results
