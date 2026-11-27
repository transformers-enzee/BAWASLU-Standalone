"""v187.1 deterministic source-field diagnostics for Gate 1.

These are non-authoritative saved-data checks: never rewrite provider payload,
AI labels, officer overrides, or infer a geographical jurisdiction.
"""
from urllib.parse import urlsplit

PLATFORM_HOSTS = {
    "youtube": ("youtube.com", "youtu.be"),
    "facebook": ("facebook.com", "fb.watch"),
    "instagram": ("instagram.com",),
    "tiktok": ("tiktok.com",),
    "x": ("x.com", "twitter.com"),
}
KNOWN_PLATFORMS = frozenset((*PLATFORM_HOSTS, "twitter", "threads", "telegram", "other"))


def platform_from_url(url):
    try:
        host = (urlsplit(url or "").hostname or "").lower().rstrip(".")
    except ValueError:
        return ""
    for platform, hosts in PLATFORM_HOSTS.items():
        if any(host == domain or host.endswith("." + domain) for domain in hosts):
            return platform
    return ""


def quality_hints(fields, source):
    """Return evidence-based hints only; no guessed values or auto-corrections."""
    def current(field):
        row = fields.get(field) or {}
        return str(row.get("effective") or "").strip()

    hints = []
    platform = current("platform").lower()
    url = current("canonical_url") or str(getattr(source, "canonical_url", "") or "")
    linked_platform = platform_from_url(url)
    if platform and (platform.startswith("@") or platform.startswith("http") or
                     platform not in KNOWN_PLATFORMS):
        hints.append({
            "field": "platform",
            "message": "The saved platform looks like an account handle or unknown platform. Check the original source mapping.",
            "suggested_value": linked_platform if linked_platform and linked_platform != platform else "",
            "basis": "Recognized source URL domain" if linked_platform else "Saved-value format only",
            "code": "POSSIBLE_PLATFORM_MAPPING_ERROR",
        })
    elif linked_platform and platform and platform not in (linked_platform, "twitter" if linked_platform == "x" else linked_platform):
        hints.append({
            "field": "platform",
            "message": "The saved platform differs from the platform indicated by the source URL. Check before correcting.",
            "suggested_value": linked_platform,
            "basis": "Recognized source URL domain",
            "code": "PLATFORM_URL_DISAGREEMENT",
        })
    for field in ("province", "city", "country"):
        value = current(field)
        if value and (value.lower() in KNOWN_PLATFORMS or value.startswith("@")):
            hints.append({
                "field": field,
                "message": "This location contains a platform or account value rather than a supported location. Do not infer a jurisdiction.",
                "suggested_value": "",
                "basis": "Saved-value format only",
                "code": "POSSIBLE_GEOGRAPHY_MAPPING_ERROR",
            })
    return hints[:5]
