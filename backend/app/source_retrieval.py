import ipaddress
import socket
from html.parser import HTMLParser
from urllib.parse import urljoin, urlparse

import httpx

MAX_BYTES=2*1024*1024
MAX_REDIRECTS=3
USER_AGENT='BAWASLU-Intelligence/0.1 source-retrieval'

def _validate_public_url(url):
    p=urlparse(str(url or '').strip())
    if p.scheme not in ('http','https') or not p.hostname:
        raise ValueError('Public HTTP(S) URL required')
    if p.username or p.password:
        raise ValueError('URLs containing credentials are not allowed')
    if p.port and p.port not in (80,443):
        raise ValueError('Only standard HTTP/HTTPS ports are allowed')
    host=p.hostname.rstrip('.')
    try:
        ips=[ipaddress.ip_address(host)]
    except ValueError:
        try:
            infos=socket.getaddrinfo(host,p.port or (443 if p.scheme=='https' else 80),type=socket.SOCK_STREAM)
        except socket.gaierror:
            raise ValueError('Source hostname could not be resolved')
        ips=list({ipaddress.ip_address(x[4][0]) for x in infos})
    if not ips or any(not ip.is_global for ip in ips):
        raise ValueError('Private, local, reserved, or non-public source addresses are not allowed')
    return p

class _ArticleParser(HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.title=[]
        self.paragraphs=[]
        self._in_title=False
        self._in_p=False
        self._skip=0
        self.meta={}
        self.canonical=''
        self.lang=''
    def handle_starttag(self,tag,attrs):
        a={str(k).lower():str(v or '') for k,v in attrs}
        t=tag.lower()
        if t=='html': self.lang=a.get('lang','')
        if t in ('script','style','noscript','svg'): self._skip+=1
        if t=='title': self._in_title=True
        if t=='p': self._in_p=True; self.paragraphs.append([])
        if t=='meta':
            key=(a.get('property') or a.get('name') or '').lower()
            val=a.get('content','').strip()
            if key and val and key not in self.meta: self.meta[key]=val
        if t=='link' and 'canonical' in a.get('rel','').lower():
            self.canonical=a.get('href','').strip()
    def handle_endtag(self,tag):
        t=tag.lower()
        if t=='title': self._in_title=False
        if t=='p': self._in_p=False
        if t in ('script','style','noscript','svg') and self._skip: self._skip-=1
    def handle_data(self,data):
        if self._skip: return
        txt=' '.join(data.split())
        if not txt: return
        if self._in_title: self.title.append(txt)
        if self._in_p and self.paragraphs: self.paragraphs[-1].append(txt)

def _extract_html(html,url):
    parser=_ArticleParser()
    parser.feed(html)
    meta=parser.meta
    title=(meta.get('og:title') or meta.get('twitter:title') or ' '.join(parser.title)).strip()
    source=(meta.get('og:site_name') or urlparse(url).hostname or '').removeprefix('www.')
    author=(meta.get('author') or meta.get('article:author') or '').strip()
    published=(meta.get('article:published_time') or meta.get('date') or meta.get('datepublished') or meta.get('publish_date') or '').strip()
    paragraphs=[' '.join(x).strip() for x in parser.paragraphs]
    paragraphs=[x for x in paragraphs if len(x)>=25]
    content='\n\n'.join(paragraphs)[:20000]
    if not content:
        content=(meta.get('description') or meta.get('og:description') or '').strip()[:20000]
    language=(parser.lang or meta.get('language') or '').split('-')[0].lower()
    pub_date=''; pub_time=''; precision='UNKNOWN'
    if published:
        clean=published.replace('Z','+00:00')
        try:
            from datetime import datetime
            dt=datetime.fromisoformat(clean)
            pub_date=dt.date().isoformat()
            if 'T' in published or ' ' in published:
                pub_time=dt.time().replace(tzinfo=None).isoformat(timespec='seconds')
                precision='EXACT'
            else:
                precision='DATE_ONLY'
        except Exception:
            if len(published)>=10 and published[4:5]=='-' and published[7:8]=='-':
                pub_date=published[:10]; precision='DATE_ONLY'
    canonical=urljoin(url,parser.canonical) if parser.canonical else ''
    return {
      'available':bool(title or content),
      'title':title[:3000],
      'original_content':content,
      'author':author[:255],
      'source_name':source[:255],
      'platform':'Web',
      'original_language_code':language[:20],
      'publication_date':pub_date,
      'publication_time':pub_time,
      'publication_time_precision':precision,
      'canonical_url':canonical[:2000],
    }

def fetch_public_source(url):
    original=str(url or '').strip()
    current=original
    headers={'User-Agent':USER_AGENT,'Accept':'text/html,application/xhtml+xml;q=0.9,*/*;q=0.1'}
    with httpx.Client(timeout=httpx.Timeout(12.0,connect=6.0),follow_redirects=False,headers=headers) as client:
        for hop in range(MAX_REDIRECTS+1):
            _validate_public_url(current)
            with client.stream('GET',current) as res:
                if res.status_code in (301,302,303,307,308):
                    if hop>=MAX_REDIRECTS: raise ValueError('Source redirected too many times')
                    location=res.headers.get('location')
                    if not location: raise ValueError('Source redirect did not include a destination')
                    current=urljoin(current,location)
                    continue
                if res.status_code>=400:
                    raise ValueError(f'Source returned HTTP {res.status_code}')
                content_type=(res.headers.get('content-type') or '').lower()
                if 'text/html' not in content_type and 'application/xhtml+xml' not in content_type:
                    raise ValueError('Source URL did not return an HTML page')
                chunks=[]; total=0
                for chunk in res.iter_bytes():
                    total+=len(chunk)
                    if total>MAX_BYTES: raise ValueError('Source page is too large to retrieve safely')
                    chunks.append(chunk)
                raw=b''.join(chunks)
                encoding=res.encoding or 'utf-8'
                try: html=raw.decode(encoding,errors='replace')
                except LookupError: html=raw.decode('utf-8',errors='replace')
                result=_extract_html(html,current)
                result.update({
                  'source_url':original,
                  'retrieved_url':current,
                  'retrieval_status':'CONTENT_RETRIEVED' if result['available'] else 'HTML_RETRIEVED_NO_ARTICLE_CONTENT',
                  'requires_manual_content':not result['available'],
                  'retrieval_method':'PUBLIC_HTML',
                })
                return result
    raise ValueError('Source retrieval failed')
