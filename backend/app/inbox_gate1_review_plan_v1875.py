"""BAWASLU Human Gate 1: selective, evidence-grounded information QA.

A social signal is not a proven violation. Missing dates, candidates,
jurisdictions and provider engagement metrics must not become officer
assignments merely because the provider returned an empty field.
No external recovery, autonomous legal finding, or canonical mutation here.
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
EMPTY_VALUES=frozenset(("", "[]", "{}", "null", "none", "unknown", "unclassified",
                       "not applicable", "n/a"))
EXPLICIT_EVENT_ROLES=frozenset(("INCIDENT","INCIDENT_LOCATION","EVENT","EVENT_LOCATION",
    "ALLEGED_INCIDENT","ALLEGED_EVENT","EXPLICIT_INCIDENT"))
HISTORICAL_CONTEXT=frozenset(("HISTORICAL","PAST","ARCHIVAL","ARCHIVED"))
CURRENT_CONTEXT=frozenset(("CURRENT","ONGOING","ACTIVE","RECENT"))


def decode(raw):
    if isinstance(raw,(list,dict)):
        return raw
    if not isinstance(raw,str):
        return raw
    value=raw.strip()
    if value.startswith(("{","[")):
        try:
            return json.loads(value)
        except (ValueError,TypeError):
            return raw
    return raw


def populated(value):
    if value is None:
        return False
    value=decode(value)
    if isinstance(value,dict):
        return any(populated(v) for v in value.values())
    if isinstance(value,list):
        return any(populated(v) for v in value)
    return bool(str(value).strip()) and str(value).strip().lower() not in EMPTY_VALUES


def signal_items(value):
    value=decode(value)
    if isinstance(value,dict):
        for key in ("signals","items","categories"):
            if isinstance(value.get(key),list):
                return value[key]
        return [value]
    if isinstance(value,list):
        return value
    return []


def time_context(fields):
    """Only use an explicit time_context value. Never invent an incident date."""
    for item in signal_items((fields.get("potential_issue_categories") or {}).get("effective")):
        if not isinstance(item,dict):
            continue
        raw=str(item.get("time_context") or "").strip().upper()
        if raw:
            return raw
    return ""


def event_location_mentioned(fields):
    """An account/profile location is not an event jurisdiction."""
    for field in ("geographic_context","potential_issue_categories"):
        for signal in signal_items((fields.get(field) or {}).get("effective")):
            if not isinstance(signal,dict):
                continue
            role=str(signal.get("location_basis") or signal.get("location_role") or
                     signal.get("role") or "").strip().upper()
            explicit=bool(signal.get("is_incident_location") is True or
                          role in EXPLICIT_EVENT_ROLES)
            if explicit and any(populated(signal.get(k)) for k in
                     ("place","location","jurisdiction","province","city",
                      "location_name","incident_location")):
                return True
    return False


def missing_tasks(fields, *, relevance="", sentiment=""):
    """Assign only unresolved material gaps, never guesses or legal conclusions.

    The absence of a named actor, precise date or jurisdiction is not a defect
    unless explicit incident evidence establishes why it is needed.
    """
    def value(key):
        return (fields.get(key) or {}).get("effective","")
    def documented(key):
        return (fields.get(key) or {}).get("mode")=="UNAVAILABLE"
    tasks=[]
    def add(key, reason, priority="P2", area="verification"):
        if not populated(value(key)) and not documented(key):
            tasks.append({"field":key,"reason":reason,"priority":priority,
                          "area":area,"status":"NEEDS_OFFICER_VERIFICATION",
                          "suggested_value":None})
    relevant=str(relevance or "").strip().upper() not in ("","IRRELEVANT")
    alleged=populated(value("potential_issue_categories"))
    if relevant and not populated(value("canonical_url")):
        add("canonical_url","Original source link is missing; verify evidence provenance.","P1")
    if relevant and not populated(value("text_content")) and not populated(value("transcript")):
        add("text_content","No source text or transcript is available for contextual review.","P1")
    # Only request a jurisdiction when a structured source signal *explicitly*
    # locates the alleged event, rather than merely listing an author's region.
    if alleged and event_location_mentioned(fields):
        add("incident_jurisdiction",
            "Source evidence explicitly mentions an event location; confirm the incident jurisdiction.",
            "P1","jurisdiction")
    # Historical does not imply an incident date. Even a current allegation
    # only needs a chronology if the saved source explicitly flags its timing.
    context=time_context(fields)
    if alleged and context in CURRENT_CONTEXT and not populated(value("incident_date")):
        if not populated(value("published_at")):
            add("published_at",
                "A current or ongoing allegation has no source publication date; confirm its timing.",
                "P2","timeline")
    if relevant and str(sentiment or "").strip().upper() in ("UNCLASSIFIED","UNKNOWN","UNASSESSED"):
        add("sentiment","Sentiment assessment is unclassified.","P2","narrative")
    # Evidence quality is an AI assessment, not a missing provider value.
    # Do not require a manual quality label solely because one was not saved.
    return tasks[:8]


def review_framework(fields, tasks=None):
    tasks=tasks or []
    required={task["area"] for task in tasks}
    context=time_context(fields)
    result=[]
    for area in AREAS:
        available=any(populated((fields.get(f) or {}).get("effective")) for f in area["fields"])
        state="NEEDS_COMPLETION" if area["id"] in required else ("AVAILABLE" if available else "NOT_IDENTIFIED")
        if area["id"]=="jurisdiction" and not available and area["id"] not in required:
            state="NOT_ESTABLISHED"
        if area["id"]=="timeline" and not available and context in HISTORICAL_CONTEXT:
            state="CONTEXT_ONLY"
        if area["id"]=="verification" and not available and area["id"] not in required:
            state="NOT_ASSESSED"
        result.append({**area,"available":available,"state":state,
                       "requires_officer_completion":area["id"] in required})
    return result
