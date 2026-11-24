"""Permission-scoped saved sources for the rebuilt assistant.

Only existing authoritative access-filtered application selectors are reused.
No legacy assistant prompts, router, reasoning, answer formatting or AI pipeline.
"""
import re
import logging
from urllib.parse import urlsplit

LOG=logging.getLogger(__name__)
STOP={"pada","yang","dengan","tentang","dalam","dari","untuk","apakah","bagaimana","sebuah",
      "tolong","mohon","terkait","mengenai","hasil","lalu","dapat","and","this","that",
      "with","from","have","what","who","where","which","please","about","latest",
      "recent","bawaslu","pemilu","pilkada","perkara","last","past","weeks","days"}
SOCIAL_IDS=re.compile(r"\bSOCIAL-(\d+)\b",re.I)
FORMAL_IDS=re.compile(r"\bINT-[\w:-]+\b",re.I)
PDF_IDS=re.compile(r"\bDOC-\d+-P\d+\b",re.I)


def terms(text):
    return {x for x in re.findall(r"[a-zA-ZÀ-ÿ0-9]{4,}",str(text or "").casefold())
            if x not in STOP}


def score(question,text):
    t=terms(question)
    if not t:return 0
    hay=str(text or "").casefold()
    return sum(3 if token in hay[:300] else 1 for token in t if token in hay)


def public_url(url):
    try:
        p=urlsplit(str(url or ""))
        return str(url)[:1600] if p.scheme=="https" and p.hostname and not p.username else ""
    except ValueError:
        return ""


def make(id,kind,title,excerpt,url="",published="",location="",verified=False,review=""):
    return {"id":str(id),"type":kind,"title":str(title or "Untitled source")[:170],
            "excerpt":str(excerpt or "")[:2200],"url":public_url(url),
            "published_at":str(published or "")[:32],"updated_at":"",
            "location":str(location or "")[:100] if verified else "",
            "location_verified":bool(verified),
            "review_status":str(review or "")[:80],
            "read_status":"SAVED_SNAPSHOT","basis":"FIXED_SAVED_SNAPSHOT",
            "reliability":("SAVED_SOCIAL_UNVERIFIED" if kind=="SAVED_SOCIAL" else
                           "SAVED_UPLOADED_PDF_NOT_CERTIFIED" if kind=="SAVED_LEGAL" else
                           "SAVED_OFFICER_RECORD_NOT_INDEPENDENTLY_VERIFIED"),
            "reason":"Authorized saved snapshot; not an independent live source check",
            "duplicate_of":""}


def dedupe(rows):
    """Mark URLs/text repetitions; never count reposts as corroborating cases."""
    seen={}
    for r in rows:
        p=urlsplit(r.get("url",""))
        key=((p.hostname or "").casefold(),p.path.rstrip("/").casefold()) if p.scheme=="https" else None
        if not key or not key[0]:
            # Very similar repeated saved texts are potential duplicates,
            # not confirmed same authors or coordinated behaviour.
            cleaned=" ".join(re.findall(r"\w+",r.get("excerpt","").casefold()))
            key=("body",cleaned[:200]) if len(cleaned)>=90 else None
        r["duplicate_of"]=seen.get(key,"") if key else ""
        if key and key not in seen:seen[key]=r["id"]
    return rows


def collect(db,grant,question,selected,window=None):
    """Strictly opt-in and officer-scoped. Never used by Web-only requests."""
    if not (selected.get("smartRadar") or selected.get("legalReferences")):
        return [],[]
    warnings=[];rows=[]
    ids_social=set(SOCIAL_IDS.findall(question))
    ids_formal={x.upper() for x in FORMAL_IDS.findall(question)}
    ids_pdf={x.upper() for x in PDF_IDS.findall(question)}
    if selected.get("smartRadar"):
        from app.domain import list_intelligence
        records=list_intelligence(db,grant)
        matches=[]
        for item in records:
            rid=str(getattr(item,"intelligence_id","") or "")
            if not rid:continue
            explicit=bool(ids_formal)
            if explicit and rid.upper() not in ids_formal:continue
            s=score(question," ".join(str(getattr(item,f,"") or "")[:350] for f in
                ("title","original_content","source_name","source_type")))
            if explicit or s>0:matches.append((s,item))
        matches.sort(key=lambda pair:pair[0],reverse=True)
        selected_formal=matches[:8]
        found={str(x.intelligence_id).upper() for _,x in selected_formal}
        if ids_formal-found:warnings.append("One or more named Intelligence records are outside your authorized scope or unavailable.")
        for _,r in selected_formal:
            rows.append(make(r.intelligence_id,"SAVED_INTELLIGENCE",
                r.title or r.intelligence_id,r.original_content or r.title,
                getattr(r,"source_url",""),getattr(r,"publication_datetime","") or
                getattr(r,"publication_date",""),getattr(r,"province",""),
                getattr(r,"jurisdiction_confirmed",False) is True,
                getattr(r,"verification_status","") or getattr(r,"review_status","")))
        try:
            from app.campaigns import campaign_action
            result=campaign_action(db,grant,"campaignIntelligenceInbox",{})
            saved=result.get("findings") or []
            matches=[]
            for row in saved:
                ident=str(row.get("id") or "")
                if not ident:continue
                if ids_social and ident not in ids_social:continue
                text=str(row.get("text_content") or "")
                s=score(question,text)
                if ids_social or s>0:matches.append((s,row))
            matches.sort(key=lambda pair:pair[0],reverse=True)
            chosen=matches[:10]
            found_social={str(r.get("id")) for _,r in chosen}
            if ids_social-found_social:
                warnings.append("One or more named Social Listening records are unavailable in your authorized saved corpus.")
            for _,r in chosen:
                rows.append(make("SOCIAL-"+str(r["id"]),"SAVED_SOCIAL",
                    "Saved social post · "+str(r.get("platform") or "source"),
                    r.get("text_content") or "",r.get("canonical_url"),
                    r.get("published_at"),"",False,"UNVERIFIED_ALLEGATION_NOT_LEGAL_FACT"))
        except PermissionError:
            warnings.append("Your role does not permit saved Social Listening source access.")
        except Exception:
            # No authorization bypass or self-elevating fallback.
            db.rollback()
            LOG.exception("UNIFIED_AI_SAVED_SOCIAL_UNAVAILABLE")
            warnings.append("Saved Social Listening could not be retrieved.")
    if selected.get("legalReferences"):
        try:
            # The PDF knowledge library's officer scope check is reused as
            # read-only storage infrastructure, not as assistant reasoning.
            from app.assistant_knowledge import retrieve_chat_knowledge
            pages=retrieve_chat_knowledge(db,grant,question,limit=5,semantic=False) or []
            found_pdf=set()
            for r in pages:
                rid=str(r.get("record_id") or "")
                if not rid or (ids_pdf and rid.upper() not in ids_pdf):continue
                title=str(r.get("title") or "")
                excerpt=str(r.get("source_excerpt") or "")
                # A sample/simulated document must never be admitted as a
                # current legal authority even if the user selected legal docs.
                if re.search(r"(sample|simulasi|simulation|contoh dummy)",title+" "+excerpt[:150],re.I):
                    warnings.append("A simulated/sample PDF was excluded from legal evidence.")
                    continue
                found_pdf.add(rid.upper())
                rows.append(make(rid,"SAVED_LEGAL",title+" · page "+str(r.get("page") or ""),
                    excerpt,r.get("source_url"),r.get("legal_effective_date"),
                    "",False,r.get("review_status") or "LEGAL_CURRENTNESS_NOT_CERTIFIED"))
            if ids_pdf-found_pdf:
                warnings.append("Some named legal PDF pages could not be used within your authorized scope.")
        except PermissionError:
            warnings.append("Legal/reference library access is not authorised.")
        except Exception:
            db.rollback()
            LOG.exception("UNIFIED_AI_SAVED_LEGAL_UNAVAILABLE")
            warnings.append("Authorized reference pages could not be retrieved.")
    for row in rows:
        if window:
            value=row.get("published_at","")[:10]
            row["within_period"]=(window["start"]<=value<=window["end"]) if re.match(r"\d{4}-\d\d-\d\d",value) else None
    return dedupe(rows),warnings
