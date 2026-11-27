"""BAWASLU Gate 1 v187.5: contextual information-review tasks.

Deterministic and audit-only: do not infer allegations, jurisdiction, actors,
dates, publication eligibility or AI confidence. These rules surface possible
gaps; they do not generate replacement values or fetch external evidence.
"""
import json

AREAS = (
    {"id":"violation","priority":"P1","fields":("potential_issue_categories",),"title":"Potential violations"},
    {"id":"actors","priority":"P1","fields":("candidate_names","political_parties","organizations"),"title":"Candidates and involved parties"},
    {"id":"jurisdiction","priority":"P1","fields":("incident_jurisdiction","geographic_context"),"title":"Incident jurisdiction"},
    {"id":"relevance","priority":"P2","fields":("relevance",),"title":"Election relevance"},
    {"id":"verification","priority":"P2","fields":("evidence_quality","verification_gaps"),"title":"Evidence verification"},
    {"id":"timeline","priority":"P2","fields":("incident_chronology",),"title":"Incident and timeline"},
    {"id":"narrative","priority":"P2","fields":("topic_labels","narrative","public_concerns","sentiment"),"title":"Public narrative and issues"},
    {"id":"attention","priority":"P2","fields":("review_priority",),"title":"Attention and follow-up"},
)
EMPTY_VALUES=frozenset(("","[]","{}","null","none","unknown","unclassified","not applicable","n/a"))


def populated(value):
    if value is None:
        return False
    raw=str(value).strip()
    if raw.lower() in EMPTY_VALUES:
        return False
    if raw[:1] in "[{":
        try:
            obj=json.loads(raw)
            return bool(obj) and not (isinstance(obj,dict) and not any(bool(v) for v in obj.values()))
        except (ValueError,TypeError):
            pass
    return bool(raw)


def missing_tasks(fields, *, relevance="", sentiment=""):
    """Find material gaps ONLY when source/assessment context makes them relevant.

    No candidate mentioned is valid; no jurisdiction for general commentary is
    valid; no engagement metric or transcript is never an officer assignment.
    """
    def item(key):
        row=fields.get(key) or {}
        return row.get("effective","")
    def previously_documented(key):
        return (fields.get(key) or {}).get("mode")=="UNAVAILABLE"
    tasks=[]
    def add(field,reason,priority="P2",area="verification"):
        if not populated(item(field)) and not previously_documented(field):
            tasks.append({"field":field,"reason":reason,"priority":priority,
                          "area":area,"status":"NEEDS_OFFICER_VERIFICATION",
                          "suggested_value":None})
    alleged=populated(item("potential_issue_categories"))
    relevant=str(relevance or "").upper() not in ("IRRELEVANT","")
    if relevant and not populated(item("canonical_url")):
        add("canonical_url","Original source URL is missing; provenance may need confirmation.","P1")
    if relevant and not populated(item("text_content")) and not populated(item("transcript")):
        add("text_content","Neither source text nor transcription is available to verify the content.","P1")
    if alleged:
        add("incident_jurisdiction","A possible election issue is recorded, but the incident jurisdiction is not supported by a saved assessment.","P1","jurisdiction")
        if not populated(item("incident_date")):
            add("incident_chronology","A possible election issue lacks a supported incident chronology.","P2","timeline")
        if not populated(item("published_at")):
            add("published_at","Publication date is unavailable for an item with a possible election issue.","P2","timeline")
        if not populated(item("evidence_quality")):
            add("evidence_quality","Evidence quality should be assessed before using an allegation.","P1","verification")
    if relevant and str(sentiment or "").upper() in ("UNCLASSIFIED","UNKNOWN","UNASSESSED"):
        add("sentiment","The saved sentiment assessment is not classified.","P2","narrative")
    return tasks[:8]


def review_framework(fields):
    return [{**area,"available":any(populated((fields.get(field) or {}).get("effective"))
                                       for field in area["fields"])}
            for area in AREAS]
