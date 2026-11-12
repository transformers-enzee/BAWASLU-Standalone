"""Conservative, evidence-first social platform policy triage for BAWASLU.

This is a source-text screening aid, not a platform moderation decision.
Political criticism, electoral allegations, adverse sentiment and mere
mention of policy terms are NOT evidence of a platform breach.

Officer must compare the original post, context, and current policy to decide
whether to report content to the relevant platform. Platform rules are also
independent of Indonesian electoral law.
"""
import re

# Official public entrypoints; recheck changes to specific policies with the
# providers before a formal moderation report. Entry points checked 2026-11-12;
# this does not establish any provider policy version as current.
PLATFORM_POLICIES = {
    "tiktok": ("TikTok", "https://www.tiktok.com/community-guidelines/en/"),
    "instagram": ("Instagram", "https://www.meta.com/safety/topics/safety-basics/policies/"),
    "facebook": ("Facebook", "https://www.meta.com/safety/topics/safety-basics/policies/"),
    "threads": ("Threads", "https://www.meta.com/safety/topics/safety-basics/policies/"),
    "twitter": ("X", "https://help.x.com/en/rules-and-policies/x-rules"),
    "youtube": ("YouTube", "https://support.google.com/youtube/answer/2802268?hl=en"),
    "reddit": ("Reddit", "https://redditinc.com/policies/reddit-rules"),
    "linkedin": ("LinkedIn", "https://www.linkedin.com/legal/professional-community-policies"),
    "telegram": ("Telegram", "https://telegram.org/tos"),
}
POLICY_LINK_CHECKED="2026-11-12"
# These URLs point to provider rules, NOT a verified policy version or
# a conclusion for an individual post. Community/private-channel applicability
# must be checked by a human before any enforcement report.
PLATFORM_POLICY_CAVEATS = {
    "reddit": "Subreddit community rules may additionally apply; sitewide rules are not a subreddit finding.",
    "telegram": "Telegram public-content rules may differ from private chat contexts; confirm visibility before reporting.",
    "linkedin": "Professional Community Policies require checking context and newsworthiness exceptions.",
}
PLATFORM_ALIASES = {
    "x":"twitter", "twitter-ai-search":"twitter", "twitter_ai_search":"twitter",
    "twitter.com":"twitter", "x.com":"twitter",
    "tiktok-ai-search":"tiktok",
    "instagram-ai-search":"instagram",
    "facebook-ai-search":"facebook",
    "youtube-ai-search":"youtube",
    "reddit-ai-search":"reddit",
    "linkedin-ai-search":"linkedin",
    "telegram-ai-search":"telegram",
    "telegram_public":"telegram",
}

# Very narrow, intentional calls to action rather than mere word mentions.
# These are triage *cues*, never an enforcement or legal finding.
_CUES = (
    ("DIRECT_THREAT", (
        r"\b(?:aku|saya|gue|gua|kami|kita)\s+(?:akan|mau|bakal)\s+(?:bunuh|tembak|serang|habisi)\b",
        r"\b(?:i|we)\s+(?:will|am going to|are going to)\s+(?:kill|shoot|attack|murder)\b",
        r"\b(?:ayo|mari|let'?s)\s+(?:bunuh|serang|habisi|kill|attack)\b",
    )),
    ("PERSONAL_INFORMATION", (
        r"\b(?:sebar(?:kan)?|bagikan|publikasikan|unggah|bocorkan)\s+(?:saja\s+)?(?:alamat rumah|nomor telepon pribadi|data pribadi|nomor ktp)\b",
        r"\b(?:post|publish|leak|share)\s+(?:their|his|her)\s+(?:home address|private phone|private data)\b",
    )),
    ("COORDINATED_HARASSMENT", (
        r"\b(?:ayo|mari|kita)\s+(?:serbu|banjiri|spam)\s+(?:akun|komentar|inbox|dm|kolom komentar)\b",
        r"\b(?:let'?s|everyone)\s+(?:raid|flood|spam)\s+(?:their|the|his|her)\s+(?:account|comments|inbox|dm)\b",
    )),
)
_COMPILED=tuple((category,tuple(re.compile(p,re.I) for p in patterns))
                for category,patterns in _CUES)
# A reported threat (news story, warning, court discussion, official statement)
# is not evidence the *reporting account* threatened anyone.
_REPORTING_CONTEXT=re.compile(
    r"\b(?:diberitakan|dilaporkan|melaporkan|pemberitaan|mengutip|"
    r"ancaman|dituduh|diduga|menurut|dikutip|pernyataan|berita|"
    r"reported|alleged|according to|quotes?|quoted|news report|"
    r"police say|police said|warnings?)\b",re.I
)
_NEGATED_CONTEXT=re.compile(
    r"\b(?:jangan|tidak boleh|dilarang|hindari|stop|prevent|avoid|"
    r"do not|don't|never)\b",re.I
)
CATEGORY_LABELS={
    "DIRECT_THREAT":{"id":"Indikasi ajakan/ancaman kekerasan",
                     "en":"Possible threat or call for violence"},
    "PERSONAL_INFORMATION":{"id":"Ajakan menyebarkan data pribadi",
                            "en":"Possible call to expose private information"},
    "COORDINATED_HARASSMENT":{"id":"Ajakan mengerahkan pelecehan terkoordinasi",
                              "en":"Possible coordinated harassment call"},
}
ACTION_LABELS={
    "DIRECT_THREAT":{"id":"Simpan bukti dan periksa apakah ancaman ditujukan kepada pihak tertentu serta konteks asli.",
                     "en":"Preserve evidence; examine the target, intent, and full original context."},
    "PERSONAL_INFORMATION":{"id":"Periksa apakah informasi pribadi benar-benar disebar tanpa izin; jangan ulangi datanya dalam laporan terbuka.",
                            "en":"Check for non-consensual exposure of private data; do not repeat private details in public reports."},
    "COORDINATED_HARASSMENT":{"id":"Periksa target, ajakan, bukti koordinasi, serta pengecualian bagi kritik politik.",
                              "en":"Check the target, incitement, coordination evidence, and protections for political criticism."},
}

def normalize_platform(platform):
    raw=str(platform or "").strip().lower()
    return PLATFORM_ALIASES.get(raw,raw)

def screen_platform_text(platform, source_text):
    """Return review-only categories with no legal or platform violation verdict."""
    platform_id=normalize_platform(platform)
    policy=PLATFORM_POLICIES.get(platform_id)
    text=str(source_text or "")[:12000]
    matches=[]
    for category,patterns in _COMPILED:
        if any(rule.search(text) for rule in patterns):
            matches.append(category)
    context=bool(_REPORTING_CONTEXT.search(text) or _NEGATED_CONTEXT.search(text))
    if not policy:
        status="POLICY_NOT_CONFIGURED"
    elif not text.strip():
        status="INSUFFICIENT_SOURCE"
    elif not matches:
        status="NO_DIRECT_SIGNAL_IDENTIFIED"
    elif context:
        status="CONTEXT_REVIEW_REQUIRED"
    else:
        status="REVIEW_INDICATED"
    return {
        "platform":policy[0] if policy else str(platform or "Unknown"),
        "platform_key":platform_id,
        "policy_url":policy[1] if policy else None,
        "policy_url_checked_on":POLICY_LINK_CHECKED if policy else None,
        "status":status,
        "review_categories":matches,
        "category_labels":{key:CATEGORY_LABELS[key] for key in matches},
        "recommended_checks":[ACTION_LABELS[key] for key in matches],
        "source_text_only":True,
        "platform_violation_confirmed":False,
        "legal_violation_confirmed":False,
        "policy_version_verified":False,
        "context_required":bool(matches),
        "policy_scope_note": PLATFORM_POLICY_CAVEATS.get(platform_id,
             "Check the current provider rules and relevant content context."),
        "policy_link_is_official_entrypoint_only": bool(policy),
        "political_criticism_is_not_a_violation":True,
    }

def review_platform_post(row):
    """Augment a saved, authorized Inbox row; do not infer identity or guilt."""
    result=screen_platform_text(row.get("platform"),row.get("text_content"))
    result.update({
        "source_id":str(row.get("id") or ""),
        "campaign_id":str(row.get("campaign_id") or ""),
        "source_url":str(row.get("canonical_url") or ""),
        "excerpt":str(row.get("text_content") or "")[:230],
        "human_review_status":row.get("flag_review_status") or "UNREVIEWED",
    })
    return result
