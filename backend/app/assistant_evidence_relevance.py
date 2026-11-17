"""Deterministic term-level relevance on already-authorized Assistant evidence.

A topical selection signal is never permission, factual verification, legal
authority or a full-population statistic. No IO, model calls or mutations.
"""
import json
import re
from collections import Counter
_WORD=re.compile(r"(?u)\b[\w]+(?:[-'][\w]+)*\b")

def _words(value):
    if isinstance(value,(dict,list,tuple)):
        value=json.dumps(value,ensure_ascii=False)
    return Counter(w.casefold() for w in _WORD.findall(str(value or "")))

def formal_source_term_score(terms,title,body,geography="",actors="",approved=None):
    """Prioritize title/content exact words; metadata can disambiguate.

    Status and verification labels are deliberately not inputs. These are
    categorical filters, not evidence of topical relevance.
    """
    q={str(t).casefold() for t in terms or [] if len(str(t))>=3}
    if not q:return 0
    title_words=_words(title);body_words=_words(body)
    geo_words=_words(geography);actor_words=_words(actors)
    approved_words=_words(approved)
    primary=sum(9 for t in q if t in title_words)+sum(6 for t in q if t in body_words)
    secondary=sum(3 for t in q if t in geo_words)+sum(3 for t in q if t in actor_words)
    secondary+=sum(2 for t in q if t in approved_words)
    return primary+secondary

def retrieval_scope_note(question,formal_count,social_count):
    """Description of selected, authorized sources, not corpus coverage."""
    if not (formal_count or social_count):return ""
    return (
       "RETRIEVAL SCOPE: The selected evidence contains "
       f"{formal_count} authorized Inbox record(s) and {social_count} authorized "
       "Social Listening post(s). These are selected records, NOT total campaign "
       "population, post volume, independent witnesses, incident prevalence or "
       "an exhaustive database search. Cite only sources that materially support "
       "the specific answer, not generic or merely recent posts. Identify missing "
       "actors, original content, jurisdiction, timestamps and corroboration "
       "when relevant, and give the officer a concrete next check rather than "
       "issuing a conclusive legal or policy finding."
    )
