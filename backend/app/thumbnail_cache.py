"""Best-effort, bounded and host-restricted cache for public provider thumbnails.
Only store image bytes if the image host is allowlisted, content type is image,
and the download finishes within size/time limits. No SocialCrawl API calls.
"""
import os
import base64
from urllib.parse import urlsplit
from urllib.request import build_opener, HTTPHandler, HTTPSHandler, Request
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

def cache_thumbnail(db,item,url):
    if not _allowed_image_host(url) or db.get(SocialMediaThumbnail,item.id): return False
    try:
        opener=build_opener(HTTPHandler(),HTTPSHandler())  # Redirects are not installed.
        request=Request(url,headers={'User-Agent':'Mozilla/5.0 (compatible; BAWASLU-thumbnail/1.0)','Accept':'image/*'})
        with opener.open(request,timeout=2.5) as response:
            if response.status!=200: return False
            content_type=response.headers.get_content_type().lower()
            if content_type not in ('image/jpeg','image/png','image/webp'): return False
            image=response.read(MAX_THUMBNAIL_BYTES+1)
            if not image or len(image)>MAX_THUMBNAIL_BYTES: return False
        db.add(SocialMediaThumbnail(result_id=item.id,media_type=content_type,image_data=image))
        return True
    except Exception:
        return False

def stored_thumbnail_uri(db,item):
    image=db.get(SocialMediaThumbnail,item.id)
    if image and image.image_data:
        return 'data:'+image.media_type+';base64,'+base64.b64encode(image.image_data).decode('ascii')
    return ''
