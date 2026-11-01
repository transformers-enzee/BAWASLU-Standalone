"""Safe, cross-platform attribution recovery for saved social listening evidence.

Uses ONLY author metadata belonging to the actual captured post/comment. Never
assigns an author's identity based on similar text, a parent post, domain, AI
guessing, or an unrelated account. No external requests or AI/provider credits.
"""
import json
import re
from urllib.parse import urlparse

MISSING = {"", "-", "—", "unknown", "n/a", "none", "null", "anonymous",
           "not available", "unavailable", "not specified", "no name"}
RESERVED = {"www", "m", "mobile", "web", "p", "reel", "reels", "posts", "post",
            "watch", "video", "videos", "shorts", "story", "stories", "channel",
            "status", "search", "home", "explore", "profile", "user", "i"}
ALIASES = {"twitter-ai-search": "twitter", "x": "twitter",
           "tiktok-hashtag": "tiktok", "instagram-hashtag": "instagram",
           "youtube-hashtag": "youtube"}


def clean_name(value):
    if not isinstance(value, (str, int)):
        return ""
    name = re.sub(r"\s+", " ", str(value)).strip()[:255]
    if name.casefold() in MISSING or name.strip("@").casefold() in MISSING:
        return ""
    if "://" in name or re.fullmatch(r"(?:www\.)?[a-z0-9_-]+\.(?:com|net|org|id)", name, re.I):
        return ""
    if name.casefold() in RESERVED or re.fullmatch(r"[0-9]{5,}", name):
        return ""
    return name


def clean_handle(value):
    handle = clean_name(value)
    if not handle:
        return ""
    handle = handle.lstrip("@")
    if not re.fullmatch(r"[a-zA-Z0-9._-]{2,60}", handle) or handle.casefold() in RESERVED:
        return ""
    return "@" + handle


def is_comment(content_type, raw=None):
    raw = raw if isinstance(raw, dict) else {}
    kind = " ".join(str(x or "") for x in
                    (content_type, raw.get("record_type"), raw.get("content_type"),
                     raw.get("type")))
    return "comment" in kind.casefold() or "reply" in kind.casefold()


def _dict(value):
    return value if isinstance(value, dict) else {}


def _loads(value):
    if isinstance(value, dict):
        return value
    try:
        parsed = json.loads(value or "{}")
    except (TypeError, ValueError):
        return {}
    return parsed if isinstance(parsed, dict) else {}


def _person(source):
    source = _dict(source)
    name = clean_name(source.get("display_name") or source.get("name") or
                      source.get("full_name") or source.get("channel_title"))
    handle = clean_handle(source.get("username") or source.get("handle") or
                          source.get("screen_name") or "")
    return name or handle, handle


def _url_handle(url, platform):
    """Only URLs that identify a *post author*, never a page hosting a comment."""
    platform = ALIASES.get(str(platform or "").lower(), str(platform or "").lower())
    try:
        parsed = urlparse(url or "")
        host = (parsed.hostname or "").casefold()
        path = parsed.path
        if parsed.scheme != "https":
            return ""
        if platform == "tiktok" and host.endswith("tiktok.com"):
            m = re.match(r"^/@([A-Za-z0-9._-]+)/video/", path, re.I)
        elif platform == "threads" and host.endswith("threads.com"):
            m = re.match(r"^/@([A-Za-z0-9._-]+)/post/", path, re.I)
        elif platform == "twitter" and host in ("x.com", "twitter.com", "www.x.com", "www.twitter.com"):
            m = re.match(r"^/([A-Za-z0-9_]+)/status/[0-9]+", path, re.I)
        else:
            return ""
        return clean_handle(m.group(1)) if m else ""
    except (ValueError, IndexError):
        return ""


def source_candidate(platform, content_type, raw_value, identity_value,
                     observed_handle="", canonical_url=""):
    raw = _loads(raw_value)
    identity = _loads(identity_value)
    comment = is_comment(content_type, raw)
    # Explicit comment author fields are safe for comments. Parent post author
    # and "Account" columns are NOT the commenter.
    if comment:
        for key in ("comment", "reply", "post_comment"):
            display, handle = _person(_dict(raw.get(key)).get("author"))
            if display:
                return display, handle, "comment_author_metadata"
        # A raw, explicitly comment-shaped record may have its own author field.
        if str(raw.get("type") or raw.get("record_type") or "").lower() in ("comment", "reply"):
            for source in (raw.get("author"), raw.get("user")):
                display, handle = _person(source)
                if display:
                    return display, handle, "direct_comment_metadata"
        return "", "", "comment_identity_unavailable"

    post = _dict(raw.get("post"))
    for source in (post.get("author"), raw.get("author"),
                   _dict(raw.get("source_items", [{}])[0]).get("author")
                   if isinstance(raw.get("source_items"), list) and raw.get("source_items") else None,
                   identity.get("author"),
                   raw.get("owner")):
        display, handle = _person(source)
        if display:
            return display, handle, "post_author_metadata"
    # URL handle is only safe for specific post permalink forms (not article
    # publisher, Facebook parent post, commenter, or an arbitrary domain).
    url_handle = _url_handle(canonical_url, platform)
    if url_handle:
        return url_handle, url_handle, "post_permalink_handle"
    # A stored observed handle is usable only when it agrees with a supported
    # post URL. Never accept "youtube.com" as a personal username.
    stored_handle = clean_handle(observed_handle)
    if stored_handle and url_handle and stored_handle.casefold() == url_handle.casefold():
        return stored_handle, stored_handle, "observed_post_handle"
    return "", "", "source_author_unavailable"


def display_author(item):
    """Safe display text and provenance; never infer someone's legal identity."""
    name = clean_name(getattr(item, "author_name", ""))
    if name:
        return name, "SAVED_PROVIDER_LABEL"
    raw = _loads(getattr(item, "raw_payload_json", "{}"))
    comment = is_comment(getattr(item, "content_type", ""), raw)
    found, _, reason = source_candidate(
        getattr(item, "platform", ""), getattr(item, "content_type", ""),
        raw, getattr(item, "source_identity_json", "{}"),
        getattr(item, "observed_handle", ""),
        getattr(item, "canonical_url", ""))
    if found:
        return found, reason
    platform = ALIASES.get(str(getattr(item, "platform", "") or "").lower(),
                           str(getattr(item, "platform", "") or "").lower())
    shown = {"tiktok":"TikTok","instagram":"Instagram","youtube":"YouTube",
             "facebook":"Facebook","twitter":"X","threads":"Threads",
             "reddit":"Reddit","linkedin":"LinkedIn","online_news":"News"}.get(platform,"Source")
    return (shown + " commenter" if comment else shown + " author unavailable"), "NOT_PROVIDED"


def recover_saved_author(item):
    """Only improves empty/placeholder fields. Idempotent; avoids overwriting humans."""
    if clean_name(getattr(item, "author_name", "")):
        return False, "already_named"
    name, handle, reason = source_candidate(
        getattr(item, "platform", ""), getattr(item, "content_type", ""),
        getattr(item, "raw_payload_json", "{}"),
        getattr(item, "source_identity_json", "{}"),
        getattr(item, "observed_handle", ""),
        getattr(item, "canonical_url", ""))
    if not name:
        return False, reason
    item.author_name = name[:255]
    if handle and not clean_handle(getattr(item, "observed_handle", "")):
        item.observed_handle = handle[:255]
    identity = _loads(getattr(item, "source_identity_json", "{}"))
    identity["author_attribution"] = {
        "method": reason, "status": "SOURCE_OBSERVED_NOT_IDENTITY_VERIFIED",
        "subject": "comment" if is_comment(getattr(item,"content_type",""),_loads(getattr(item,"raw_payload_json","{}"))) else "post",
        "paid_provider_called": False
    }
    item.source_identity_json = json.dumps(identity, ensure_ascii=False)
    return True, reason
