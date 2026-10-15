"""Best-effort, bounded and host-restricted cache for public provider thumbnails.
Only store image bytes if the image host is allowlisted, content type is image,
and the download finishes within size/time limits. No SocialCrawl API calls.
"""
import os
import base64
from urllib.parse import urlsplit
from urllib.request import build_opener, HTTPHandler, HTTPSHandler, HTTPRedirectHandler, Request
from urllib.error import HTTPError, URLError
from socket import timeout as SocketTimeout
from urllib.parse import parse_qs
from time import time
from .models import SocialMediaThumbnail

MAX_THUMBNAIL_BYTES=256000
HOST_SUFFIXES=('tiktokcdn.com','tiktokcdn-us.com','fbcdn.net','cdninstagram.com')

def _allowed_image_host(url):
    try:
        parsed=urlsplit(url)
        host=(parsed.hostname or '').lower()
        return parsed.scheme=='https' and not parsed.username and not parsed.password and parsed.port in (None,443) and any(host==suffix or host.endswith('.'+suffix) for suffix in HOST_SUFFIXES)
    except ValueError:
        return False

class RejectRedirect(HTTPRedirectHandler):
    def redirect_request(self,req,fp,code,msg,headers,newurl):
        return None

def cache_thumbnail_diagnostic(db,item,url):
    """Return a safe reason code, never an original signed URL or token."""
    if db.get(SocialMediaThumbnail,item.id): return 'already_saved'
    if not url: return 'no_valid_url'
    if not _allowed_image_host(url): return 'unsupported_host'
    try:
        expiry=parse_qs(urlsplit(url).query).get('x-expires',[])
        if expiry and int(expiry[0])<=time()+60: return 'expired_url'
    except (ValueError,OverflowError): return 'invalid_expiry'
    try:
        opener=build_opener(HTTPHandler(),HTTPSHandler(),RejectRedirect())
        request=Request(url,headers={'User-Agent':'Mozilla/5.0 (compatible; BAWASLU-thumbnail/1.0)','Accept':'image/*'})
        with opener.open(request,timeout=2.5) as response:
            if response.status!=200: return 'unexpected_status'
            media=response.headers.get_content_type().lower()
            if media not in ('image/jpeg','image/png','image/webp'): return 'unsupported_content_type'
            data=response.read(MAX_THUMBNAIL_BYTES+1)
            if not data: return 'empty_image'
            if len(data)>MAX_THUMBNAIL_BYTES: return 'image_too_large'
        db.add(SocialMediaThumbnail(result_id=item.id,media_type=media,image_data=data))
        return 'saved'
    except HTTPError as exc:
        if exc.code in (301,302,303,307,308): return 'redirect_blocked'
        if exc.code in (401,403): return 'access_denied'
        if exc.code in (404,410): return 'not_found_or_expired'
        if exc.code==429: return 'rate_limited'
        return 'http_error'
    except (URLError,SocketTimeout,TimeoutError): return 'network_or_timeout'
    except Exception: return 'download_error'

def cache_thumbnail(db,item,url):
    return cache_thumbnail_diagnostic(db,item,url)=='saved'

def stored_thumbnail_uri(db,item):
    image=db.get(SocialMediaThumbnail,item.id)
    if image and image.image_data:
        return 'data:'+image.media_type+';base64,'+base64.b64encode(image.image_data).decode('ascii')
    return ''
