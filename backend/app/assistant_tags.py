"""Evidence-checked assistant tags, not confirmed legal findings or jurisdictions."""
import re
from .processing_hints import source_hints, normalize_candidate_signals, CANDIDATE_ALIASES

TAG_TYPES=("CANDIDATE","PROVINCE","SUSPECTED_VIOLATION","BAWASLU_ISSUE","ELECTORAL_ISSUE")
UI_KEYS=(
 "findings_heading","finding_label","needs_review","verification_heading","review_notice",
 "implications_heading","limitations_heading","public_sources",
 "tags_heading","tags_notice","candidate","province","suspected_violation",
 "bawaslu_issue","electoral_issue","province_mention","suspected_only",
 "stats_heading","stats_intro","sample_note","posts","engagement","platforms",
 "date_range","sentiment_heading","platform_volume","daily_activity",
 "platform_engagement","topics_heading","coverage_notice","sources_heading",
 "sources_intro","original_source","source_engagement","prepare_from_source",
 "action_title","action_intro","steps_title","sources_action_heading",
 "prepare_task","open_source","prepare_review_title","not_saved_notice",
 "department_label","team_label","officer_label","case_title_label",
 "primary_source_label","close","preview_draft","hide_draft",
 "summary_label","confirm_notice","submit_action","officer_only",
 "no_sources","no_extra_ai","workspace_mine","workspace_open","workspace_reports",
 "work_prompt","work_priorities","work_assign","work_report",
 "department_suggestion","province_safety","draft_details_note","campaign_label",
)
TAG_SCHEMA={
 "type":"array","items":{"type":"object","properties":{
     "type":{"type":"string","enum":list(TAG_TYPES)},
     "label":{"type":"string"},
     "evidence_ids":{"type":"array","items":{"type":"string"}},
     "evidence_quote":{"type":"string"},
     "explanation":{"type":"string"},
     "confidence":{"type":"string","enum":["HIGH","MEDIUM","LOW"]}
 },"required":["type","label","evidence_ids","evidence_quote","explanation","confidence"],
 "additionalProperties":False}
}
UI_SCHEMA={
 "type":"array","items":{"type":"object","properties":{
     "key":{"type":"string","enum":list(UI_KEYS)},
     "value":{"type":"string"}
 },"required":["key","value"],"additionalProperties":False}
}

def _text(row):
    return str(row.get("source_excerpt") or row.get("title") or "")

def _contains(text,term):
    return bool(term) and bool(re.search(r"(?<!\w)"+re.escape(str(term).casefold())+r"(?!\w)",str(text).casefold()))

def _allowed(type_,label,row):
    body=_text(row)
    folded=body.casefold()
    topics=[str(t).casefold() for t in row.get("topic_labels") or []]
    hints=source_hints(body)
    if type_=="CANDIDATE":
        names=normalize_candidate_signals(row.get("candidate_signals") or [])
        if any(label.casefold()==name.casefold() for name in names):
            return True
        if _contains(body,label):
            return True
        # A known alias must visibly appear in text, not merely be suggested
        # by the language model.
        for canonical,aliases in CANDIDATE_ALIASES.items():
            if label.casefold()==canonical.casefold():
                return any(_contains(body,a) for a in aliases)
        return False
    if type_=="PROVINCE":
        found=set(hints.get("province_mentions") or [])
        return any(label.casefold()==p.casefold() for p in found)
    if type_=="SUSPECTED_VIOLATION":
        return bool(row.get("potential_issues")) or bool(hints["issue_screening"]["needs_human_validation"]) or any(
            _contains(folded,word) for word in ("dugaan","pelanggaran","sengketa","intimidasi","kecurangan","money politics","vote buying","alleged violation"))
    if type_=="BAWASLU_ISSUE":
        return "bawaslu" in folded or any("bawaslu" in topic for topic in topics)
    if type_=="ELECTORAL_ISSUE":
        return any(_contains(folded,term) for term in ("pemilu","pilkada","kpu","pencalonan","pengawasan pemilu","daftar pemilih",
              "pemilihan","election","electoral","voter registration","ballot")) or any(
              "electoral" in topic for topic in topics)
    return False

def validate_model_tags(proposals,evidence):
    """Allow only quoted, matching, authorized source-linked suggestions."""
    by_id={str(e.get("record_id")):e for e in evidence if isinstance(e,dict)}
    if not isinstance(proposals,list):
        return []
    out=[]
    seen=set()
    for value in proposals[:32]:
        if not isinstance(value,dict):
            continue
        kind=str(value.get("type") or "").upper()
        label=" ".join(str(value.get("label") or "").split())[:100]
        quote=" ".join(str(value.get("evidence_quote") or "").split())[:260]
        explanation=" ".join(str(value.get("explanation") or "").split())[:260]
        confidence=str(value.get("confidence") or "LOW").upper()
        if kind not in TAG_TYPES or not label or len(quote)<4 or confidence not in ("HIGH","MEDIUM","LOW"):
            continue
        ids=value.get("evidence_ids") or []
        valid=[]
        for rid in ids[:6] if isinstance(ids,list) else []:
            row=by_id.get(rid)
            if not row:
                continue
            comparable=" ".join(_text(row).split()).casefold()
            if quote.casefold() not in comparable:
                continue
            if not _allowed(kind,label,row):
                continue
            valid.append(rid)
        if not valid:
            continue
        key=(kind,label.casefold())
        if key in seen:
            continue
        seen.add(key)
        out.append({"type":kind,"label":label,"source_ids":valid[:3],
                    "evidence_quote":quote,"explanation":explanation,
                    "confidence":confidence,"verified":False,
                    "status":"AI_SUGGESTED_REQUIRES_OFFICER_REVIEW",
                    "context":"PROVINCE_MENTION_ONLY" if kind=="PROVINCE" else
                        "SUSPECTED_ONLY" if kind=="SUSPECTED_VIOLATION" else "SOURCE_SIGNAL"})
        if len(out)>=18:
            break
    return out

def fallback_tags(evidence):
    """Read-only, bounded fallback from saved signals and original text."""
    proposals=[]
    for row in evidence[:24]:
        if not isinstance(row,dict) or not row.get("record_id"):
            continue
        text=_text(row)
        if not text:
            continue
        rid=str(row["record_id"])
        hints=source_hints(text)
        names=normalize_candidate_signals(row.get("candidate_signals") or [])
        for name in names[:3]:
            if _allowed("CANDIDATE",name,row):
                proposals.append(("CANDIDATE",name,rid))
        if not names:
            for canonical,aliases in CANDIDATE_ALIASES.items():
                if any(_contains(text,alias) for alias in aliases):
                    proposals.append(("CANDIDATE",canonical,rid))
        for province in (hints.get("province_mentions") or [])[:4]:
            proposals.append(("PROVINCE",province,rid))
        if _allowed("SUSPECTED_VIOLATION","Requires review",row):
            proposals.append(("SUSPECTED_VIOLATION","Requires review",rid))
        if _allowed("BAWASLU_ISSUE","Institutional issues",row):
            proposals.append(("BAWASLU_ISSUE","Institutional issues",rid))
        if _allowed("ELECTORAL_ISSUE","Electoral operations",row):
            proposals.append(("ELECTORAL_ISSUE","Electoral operations",rid))
    found={}
    for kind,label,rid in proposals:
        key=(kind,label.casefold())
        if key not in found:
            found[key]={"type":kind,"label":label,"source_ids":[],
                "evidence_quote":"","explanation":"","confidence":"LOW",
                "verified":False,"status":"AI_OR_RULE_HINT_REQUIRES_REVIEW",
                "context":"PROVINCE_MENTION_ONLY" if kind=="PROVINCE" else
                          "SUSPECTED_ONLY" if kind=="SUSPECTED_VIOLATION" else "SOURCE_SIGNAL"}
        if len(found[key]["source_ids"])<3 and rid not in found[key]["source_ids"]:
            found[key]["source_ids"].append(rid)
    return list(found.values())[:18]

def combined_tags(model_tags,evidence):
    result=validate_model_tags(model_tags,evidence)
    seen={(x["type"],x["label"].casefold()) for x in result}
    for item in fallback_tags(evidence):
        key=(item["type"],item["label"].casefold())
        if key not in seen:
            result.append(item)
            seen.add(key)
        if len(result)>=18:
            break
    return result

def validate_ui_labels(rows):
    """Display translations are model-generated but not executable markup."""
    if not isinstance(rows,list):
        return {}
    labels={}
    for obj in rows[:len(UI_KEYS)]:
        if not isinstance(obj,dict):
            continue
        key=obj.get("key")
        value=obj.get("value")
        if key not in UI_KEYS or not isinstance(value,str):
            continue
        text=" ".join(value.split())[:120]
        if text and "<" not in text and ">" not in text and "{" not in text:
            labels[key]=text
    return labels
