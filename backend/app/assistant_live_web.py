"""Fresh public-web page verification for both SmartRadar assistant routes.

Uses the already-approved OpenAI web-search provider for discovery, then opens
returned HTTPS pages under strict address, redirect, size and timeout limits.
A search citation alone is NEVER classified as a page read.
"""
import ipaddress
import json
import re
import socket
from datetime import datetime, timezone
from html.parser import HTMLParser
from urllib.parse import urlsplit

import httpx
from .assistant_web_first import safe_web_urls

SOURCE_PRESETS={
    "WEB_ONLY":{"smartRadar":False,"publicWeb":True,"legalReferences":False,"attachments":False},
    "WEB_SMARTRADAR":{"smartRadar":True,"publicWeb":True,"legalReferences":True,"attachments":False},
    "SMARTRADAR_ONLY":{"smartRadar":True,"publicWeb":False,"legalReferences":True,"attachments":False},
}
SOURCE_MODES=(*SOURCE_PRESETS,"CUSTOM")
RECENT=re.compile(r"\b(today|tonight|yesterday|latest|recent|current|this week|this month|past \d+ "
    r"(?:days?|weeks?|months?)|last \d+ (?:days?|weeks?|months?)|"
    r"hari ini|kemarin|terbaru|terkini|pekan ini|minggu ini|bulan ini|"
    r"\d+ (?:hari|minggu|bulan) terakhir|sejak|jadwal|ditunda|postponed|"
    r"rescheduled|upcoming|breaking|perkembangan|conversation trend|tren)\b",re.I)
EVENT=re.compile(r"\b(scheduled|schedule|hearing|election|session|court|"
    r"putusan|sidang|jadwal|pemilihan|pengunduran|penetapan|"
    r"postponed|rescheduled|ditunda|tanggal|deadline)\b",re.I)
META_DATE_KEYS={"article:published_time","article:modified_time","datepublished",
    "datemodified","pubdate","publish-date","date","dc.date","dc.date.issued"}
USER_AGENT="BAWASLU-SmartRadar-SourceVerification/1.0 (public pages only)"
MAX_DOWNLOAD=225_000


def source_mode_sources(mode):
    if mode not in SOURCE_PRESETS:
        raise ValueError("Choose Web only, Web + SmartRadar, or SmartRadar only")
    return dict(SOURCE_PRESETS[mode])


def recent_research(question):
    return bool(RECENT.search(str(question or "")))


def search_plan(question,as_of=None):
    """Explicit Indonesian + English discovery and newest-update verification."""
    q=str(question or "").strip()[:900]
    date=as_of or datetime.now(timezone.utc).date().isoformat()
    check=bool(EVENT.search(q)) or recent_research(q)
    return {
        "queries":[f"{q} Indonesia sumber resmi berita terbaru {date}",
                   f"{q} latest official news update {date}"],
        "freshness_query":(f"{q} perkembangan terbaru koreksi penundaan jadwal "
                           f"latest update correction postponed rescheduled {date}" if check else ""),
        "freshness_check_requested":check,
        "as_of":date,
    }


def _global_dns(host):
    try:
        answers=socket.getaddrinfo(host,443,type=socket.SOCK_STREAM)
        ips={ipaddress.ip_address(row[4][0].split('%')[0]) for row in answers}
        return bool(ips) and all(ip.is_global for ip in ips)
    except (socket.gaierror,ValueError,TypeError,OSError):
        return False


def _safe_page_url(value):
    safe=safe_web_urls([value])
    if not safe:return False
    parsed=urlsplit(safe[0])
    host=(parsed.hostname or "").strip().lower()
    return (not host.endswith(".local") and not host.endswith(".internal")
            and not host.endswith(".home") and _global_dns(host))


class _Article(HTMLParser):
    """Extract genuine page paragraphs and header metadata, never execute scripts."""
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.skip=0
        self.capture=[]
        self.paragraphs=[]
        self.title=[]
        self.headings=[]
        self.meta={}
        self.time_dates=[]
        self.in_title=False
        self.in_p=0
        self.in_h=0
        self.in_main=0
        self.in_article=0
        self.current=[]
        self.current_kind=""
    def handle_starttag(self,tag,attrs):
        a=dict(attrs)
        if tag in ("script","style","svg","noscript","nav","footer","header","form"):
            self.skip+=1
            return
        if self.skip:return
        if tag=="meta":
            key=(a.get("property") or a.get("name") or "").casefold()
            val=(a.get("content") or "").strip()
            if key and val and len(val)<350:self.meta[key]=val
        if tag=="article":self.in_article+=1
        if tag=="main":self.in_main+=1
        if tag=="title":self.in_title=True;self.current=[];self.current_kind="title"
        if tag in ("p","h1","h2") and self.in_p==0 and self.in_h==0:
            self.current=[];self.current_kind="p" if tag=="p" else "h";self.capture.append(tag)
            if tag=="p":self.in_p=1
            else:self.in_h=1
        if tag=="time" and a.get("datetime"):
            self.time_dates.append(a["datetime"][:40])
    def handle_endtag(self,tag):
        if tag in ("script","style","svg","noscript","nav","footer","header","form") and self.skip:
            self.skip-=1;return
        if self.skip:return
        if tag=="title" and self.in_title:
            title=" ".join(" ".join(self.current).split())
            if title:self.title.append(title[:200])
            self.in_title=False;self.current=[]
        if self.capture and tag==self.capture[-1]:
            text=" ".join(" ".join(self.current).split())
            if tag=="p" and len(text)>=45:self.paragraphs.append((text[:1000],bool(self.in_article or self.in_main)))
            if tag in ("h1","h2") and text:self.headings.append(text[:180])
            self.capture.pop();self.current=[]
            if tag=="p":self.in_p=0
            else:self.in_h=0
        if tag=="article" and self.in_article:self.in_article-=1
        if tag=="main" and self.in_main:self.in_main-=1
    def handle_data(self,value):
        if self.skip:return
        if self.in_title or self.in_p or self.in_h:self.current.append(value)


def _date(value):
    raw=str(value or "")[:40].strip()
    return raw[:10] if re.match(r"^\d{4}-\d{2}-\d{2}",raw) else ""


def parse_public_html(content,uri):
    parser=_Article()
    try:parser.feed(content[:MAX_DOWNLOAD])
    except (ValueError,AssertionError):return None
    primary=[text for text,main in parser.paragraphs if main]
    paragraphs=primary if sum(len(x) for x in primary)>=240 else [p[0] for p in parser.paragraphs]
    text=" ".join(paragraphs)
    if len(text)<250:return None
    title=(parser.meta.get("og:title") or parser.meta.get("twitter:title") or
           next(iter(parser.headings),None) or next(iter(parser.title),None) or urlsplit(uri).hostname or "")
    published=next((_date(parser.meta.get(key)) for key in (
        "article:published_time","datepublished","pubdate","publish-date",
        "dc.date","dc.date.issued","date") if _date(parser.meta.get(key))),"")
    modified=next((_date(parser.meta.get(key)) for key in (
        "article:modified_time","datemodified") if _date(parser.meta.get(key))),"")
    return {"title":title[:180],"published_at":published or next(
        (_date(t) for t in parser.time_dates if _date(t)),""),
        "updated_at":modified,"excerpt":text[:2600]}


def _read_one(row,client):
    url=row["url"]
    status="INACCESSIBLE"
    doc=None
    reason="Page could not be opened"
    if not _safe_page_url(url):
        reason="Unsafe or unresolved public address"
    else:
        try:
            with client.stream("GET",url,headers={"Accept":"text/html,application/xhtml+xml",
                    "User-Agent":USER_AGENT},follow_redirects=False) as response:
                peer_stream=response.extensions.get("network_stream")
                peer=(peer_stream.get_extra_info("server_addr") if peer_stream else None)
                if not peer or not ipaddress.ip_address(str(peer[0]).split('%')[0]).is_global:
                    reason="Public peer address could not be verified"
                elif response.status_code>=300:
                    reason=("Page redirected; redirect not followed" if response.status_code<400
                            else "HTTP "+str(response.status_code))
                elif "html" not in response.headers.get("content-type","").casefold():
                    reason="Unsupported page type; no HTML content was read"
                else:
                    parts=[];size=0
                    for piece in response.iter_bytes(chunk_size=8192):
                        size+=len(piece)
                        if size>MAX_DOWNLOAD:break
                        parts.append(piece)
                    html=b"".join(parts).decode(response.encoding or "utf-8",errors="replace")
                    doc=parse_public_html(html,url)
                    if doc:status="READ";reason="Page text retrieved and parsed"
                    else:reason="Page HTML lacked sufficient readable article text"
        except (httpx.HTTPError,ValueError,UnicodeError,OSError):
            reason="Page retrieval failed"
    if not doc and row.get("snippet"):
        status="SNIPPET_ONLY"
    return {**row,"status":status,"reason":reason,
            "title":(doc or {}).get("title") or row.get("title") or urlsplit(url).hostname or "Public source",
            "published_at":(doc or {}).get("published_at") or _date(row.get("published_at")),
            "updated_at":(doc or {}).get("updated_at") or _date(row.get("updated_at")),
            "excerpt":(doc or {}).get("excerpt") or (row.get("snippet") or "")[:500]}


def verify_public_pages(research,fetcher=None,max_pages=5):
    """Read returned public pages before AI synthesis. Injectable for no-network tests."""
    if not isinstance(research,dict):return None
    citations=research.get("sources") or [{"url":url} for url in research.get("urls",[])]
    rows=[];seen=set()
    for source in citations:
        if not isinstance(source,dict):continue
        url=source.get("url")
        if not isinstance(url,str) or url not in safe_web_urls([url]) or url in seen:continue
        seen.add(url)
        rows.append({"url":url,"title":str(source.get("title") or "")[:180],
                     "snippet":str(source.get("snippet") or "")[:500],
                     "published_at":_date(source.get("published_at")),
                     "updated_at":_date(source.get("updated_at"))})
    if fetcher:
        pages=[fetcher(row) for row in rows[:max_pages]]
    else:
        with httpx.Client(timeout=httpx.Timeout(7.0,connect=3.0),
                          trust_env=False,follow_redirects=False) as client:
            pages=[_read_one(row,client) for row in rows[:max_pages]]
    read=[p for p in pages if p.get("status")=="READ"]
    read.sort(key=lambda p:(p.get("updated_at") or p.get("published_at") or "0000-00-00"),reverse=True)
    # Provider summary is a lead, never a claim source for model synthesis.
    excerpts="\n\n".join(f"READ PUBLIC PAGE: {p['title']} ({p.get('published_at') or 'date unknown'}"
        f"; updated {p.get('updated_at') or 'unknown'}): {p['url']}\n{p.get('excerpt','')}"
        for p in read)
    return {**research,
        "provider_summary":str(research.get("summary") or "")[:2200],
        "summary":excerpts[:10500],
        "pages":pages,
        "urls":[p["url"] for p in read],
        "read_count":len(read),
        "search_status":"READ_SOURCES_AVAILABLE" if read else "NO_READABLE_PUBLIC_PAGES",
        "retrieved_at":datetime.now(timezone.utc).isoformat()}
