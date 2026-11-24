"""Claim-level evidence review and independent-source classification."""
from urllib.parse import urlsplit

KNOWN_STATUSES={"PRIMARY_SOURCE_REPORTED","INDEPENDENTLY_CORROBORATED",
                "ATTRIBUTED_ALLEGATION","CONFLICTING","INFERRED","UNRESOLVED"}


def verify_claims(rows,records):
    eligible={r["id"]:r for r in records if r.get("read_status") in ("READ","SAVED_SNAPSHOT")}
    output=[]
    seen=set()
    for row in (rows if isinstance(rows,list) else [])[:30]:
        if not isinstance(row,dict):continue
        text=str(row.get("claim") or "").strip()[:700]
        if not text or text.casefold() in seen:continue
        seen.add(text.casefold())
        ids=list(dict.fromkeys(x for x in (row.get("source_ids") or [])
                                if isinstance(x,str) and x in eligible))[:5]
        source_hosts={urlsplit(eligible[s].get("url") or "").hostname for s in ids
                      if eligible[s].get("read_status")=="READ" and eligible[s].get("url")}
        status=str(row.get("status") or "UNRESOLVED").upper()
        if status not in KNOWN_STATUSES:status="UNRESOLVED"
        if not ids and status not in ("INFERRED","UNRESOLVED"):
            status="UNRESOLVED"
        if status=="INDEPENDENTLY_CORROBORATED" and len(source_hosts)<2:
            status="PRIMARY_SOURCE_REPORTED" if any(eligible[s].get("kind")=="OFFICIAL" and
                    eligible[s].get("read_status")=="READ" for s in ids) else "UNRESOLVED"
        if status=="PRIMARY_SOURCE_REPORTED" and not any(eligible[s].get("kind")=="OFFICIAL" and
                    eligible[s].get("read_status")=="READ" for s in ids):
            status="ATTRIBUTED_ALLEGATION" if ids else "UNRESOLVED"
        # A saved snapshot is never independently certified by retrieval.
        if status=="INDEPENDENTLY_CORROBORATED" and any(eligible[s].get("kind")=="SAVED_RECORD" for s in ids):
            status="UNRESOLVED"
        output.append({"claim":text,"source_ids":ids,"status":status,
                       "caveat":str(row.get("caveat") or "")[:300],
                       "officer_authenticated":False})
    return output
