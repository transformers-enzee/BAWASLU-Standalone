import ipaddress
import json
import re
import socket
from html.parser import HTMLParser
from urllib.parse import urljoin, urlparse

import httpx

MAX_BYTES=2*1024*1024
MAX_REDIRECTS=3
USER_AGENT='BAWASLU-Intelligence/0.1 source-retrieval'
ARTICLE_TYPES={'article','newsarticle','reportagenewsarticle','analysisnewsarticle','blogposting','report'}

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
        self._jsonld_depth=0
        self._jsonld_buffer=[]
        self.jsonld=[]
        self.meta={}
        self.canonical=''
        self.lang=''
    def handle_starttag(self,tag,attrs):
        a={str(k).lower():str(v or '') for k,v in attrs}
        t=tag.lower()
        if t=='html':
            self.lang=a.get('lang','')
        if t=='script' and 'ld+json' in a.get('type','').lower():
            self._jsonld_depth+=1
            self._jsonld_buffer=[]
            return
        if t in ('script','style','noscript','svg'):
            self._skip+=1
        if t=='title':
            self._in_title=True
        if t=='p':
            self._in_p=True
            self.paragraphs.append([])
        if t=='meta':
            key=(a.get('property') or a.get('name') or '').lower()
            val=a.get('content','').strip()
            if key and val and key not in self.meta:
                self.meta[key]=val
        if t=='link' and 'canonical' in a.get('rel','').lower():
            self.canonical=a.get('href','').strip()
    def handle_endtag(self,tag):
        t=tag.lower()
        if t=='script' and self._jsonld_depth:
            raw=''.join(self._jsonld_buffer).strip()
            if raw:
                try:
                    self.jsonld.append(json.loads(raw))
                except Exception:
                    pass
            self._jsonld_depth-=1
            self._jsonld_buffer=[]
            return
        if t=='title':
            self._in_title=False
        if t=='p':
            self._in_p=False
        if t in ('script','style','noscript','svg') and self._skip:
            self._skip-=1
    def handle_data(self,data):
        if self._jsonld_depth:
            self._jsonld_buffer.append(data)
            return
        if self._skip:
            return
        txt=' '.join(data.split())
        if not txt:
            return
        if self._in_title:
            self.title.append(txt)
        if self._in_p and self.paragraphs:
            self.paragraphs[-1].append(txt)

def _jsonld_nodes(value):
    if isinstance(value,list):
        for item in value:
            yield from _jsonld_nodes(item)
    elif isinstance(value,dict):
        yield value
        graph=value.get('@graph')
        if graph is not None:
            yield from _jsonld_nodes(graph)

def _type_names(node):
    value=node.get('@type') if isinstance(node,dict) else None
    if isinstance(value,list):
        return {str(x).lower() for x in value}
    return {str(value).lower()} if value else set()

def _article_jsonld(parser):
    nodes=[]
    for block in parser.jsonld:
        nodes.extend(_jsonld_nodes(block))
    articles=[n for n in nodes if _type_names(n) & ARTICLE_TYPES]
    candidates=articles or nodes
    return candidates[0] if candidates else {}

def _author_name(value):
    if isinstance(value,str):
        return value.strip()
    if isinstance(value,dict):
        return str(value.get('name') or value.get('alternateName') or '').strip()
    if isinstance(value,list):
        names=[_author_name(x) for x in value]
        return ', '.join(x for x in names if x)
    return ''

def _publisher_name(value):
    if isinstance(value,str):
        return value.strip()
    if isinstance(value,dict):
        return str(value.get('name') or '').strip()
    return ''

def _detect_language(content,declared=''):
    text=' '+re.sub(r'[^a-zA-Z\u00C0-\u024F]+',' ',str(content or '').lower())+' '
    id_markers=[' yang ',' dan ',' dengan ',' untuk ',' dari ',' pada ',' sebagai ',' tidak ',' dalam ',' adalah ',' juga ',' kepada ',' telah ',' akan ',' karena ',' pemilu ',' bawaslu ']
    en_markers=[' the ',' and ',' with ',' for ',' from ',' this ',' that ',' not ',' are ',' is ',' was ',' election ',' article ',' news ']
    id_score=sum(text.count(x) for x in id_markers)
    en_score=sum(text.count(x) for x in en_markers)
    if id_score>=3 and id_score>en_score:
        return 'id'
    if en_score>=3 and en_score>id_score:
        return 'en'
    d=str(declared or '').split('-')[0].lower()
    if d in ('id','in'):
        return 'id'
    if d:
        return d
    return ''

def _published_parts(published):
    pub_date=''
    pub_time=''
    precision='UNKNOWN'
    if published:
        clean=str(published).strip().replace('Z','+00:00')
        try:
            from datetime import datetime
            dt=datetime.fromisoformat(clean)
            pub_date=dt.date().isoformat()
            if 'T' in str(published) or ' ' in str(published):
                pub_time=dt.time().replace(tzinfo=None).isoformat(timespec='seconds')
                precision='EXACT'
            else:
                precision='DATE_ONLY'
        except Exception:
            value=str(published).strip()
            if len(value)>=10 and value[4:5]=='-' and value[7:8]=='-':
                pub_date=value[:10]
                precision='DATE_ONLY'
    return pub_date,pub_time,precision

def _extract_html(html,url):
    parser=_ArticleParser()
    parser.feed(html)
    meta=parser.meta
    article=_article_jsonld(parser)

    jsonld_title=str(article.get('headline') or article.get('name') or '').strip()
    title=(jsonld_title or meta.get('og:title') or meta.get('twitter:title') or ' '.join(parser.title)).strip()

    jsonld_source=_publisher_name(article.get('publisher'))
    source=(jsonld_source or meta.get('og:site_name') or urlparse(url).hostname or '').removeprefix('www.')

    jsonld_author=_author_name(article.get('author'))
    author=(jsonld_author or meta.get('author') or meta.get('article:author') or '').strip()

    published=(article.get('datePublished') or article.get('dateCreated') or meta.get('article:published_time') or meta.get('date') or meta.get('datepublished') or meta.get('publish_date') or '')
    published=str(published or '').strip()

    paragraphs=[' '.join(x).strip() for x in parser.paragraphs]
    paragraphs=[x for x in paragraphs if len(x)>=25]
    paragraph_content='\n\n'.join(paragraphs)[:20000]
    jsonld_body=str(article.get('articleBody') or '').strip()[:20000]
    if jsonld_body and (not paragraph_content or len(jsonld_body)>len(paragraph_content)*0.65):
        content=jsonld_body
    else:
        content=paragraph_content
    if not content:
        content=(meta.get('description') or meta.get('og:description') or str(article.get('description') or '')).strip()[:20000]

    declared_language=(article.get('inLanguage') or parser.lang or meta.get('language') or '')
    language=_detect_language(content or title,declared_language)

    pub_date,pub_time,precision=_published_parts(published)
    canonical_value=str(article.get('url') or parser.canonical or '').strip()
    canonical=urljoin(url,canonical_value) if canonical_value else ''

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
                    if hop>=MAX_REDIRECTS:
                        raise ValueError('Source redirected too many times')
                    location=res.headers.get('location')
                    if not location:
                        raise ValueError('Source redirect did not include a destination')
                    current=urljoin(current,location)
                    continue
                if res.status_code>=400:
                    raise ValueError(f'Source returned HTTP {res.status_code}')
                content_type=(res.headers.get('content-type') or '').lower()
                if 'text/html' not in content_type and 'application/xhtml+xml' not in content_type:
                    raise ValueError('Source URL did not return an HTML page')
                chunks=[]
                total=0
                for chunk in res.iter_bytes():
                    total+=len(chunk)
                    if total>MAX_BYTES:
                        raise ValueError('Source page is too large to retrieve safely')
                    chunks.append(chunk)
                raw=b''.join(chunks)
                encoding=res.encoding or 'utf-8'
                try:
                    html=raw.decode(encoding,errors='replace')
                except LookupError:
                    html=raw.decode('utf-8',errors='replace')
                result=_extract_html(html,current)
                result.update({
                  'source_url':original,
                  'retrieved_url':current,
                  'retrieval_status':'CONTENT_RETRIEVED' if result['available'] else 'HTML_RETRIEVED_NO_ARTICLE_CONTENT',
                  'requires_manual_content':not result['available'],
                  'retrieval_method':'PUBLIC_HTML_JSONLD',
                })
                return result
    raise ValueError('Source retrieval failed')
