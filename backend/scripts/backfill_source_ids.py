"""Guarded canonical ID backfill for already-promoted Social Listening records.

Dry-run by default:
    cd backend && python -m scripts.backfill_source_ids
Commit only after inspecting dry-run output:
    cd backend && python -m scripts.backfill_source_ids --apply

Uses the explicit, existing social_listening_results.promoted_intelligence_id FK,
not URL guesses, content matching, or name similarity. Never overwrites nonblank IDs.
"""
import argparse
import json
from sqlalchemy import text
from app.db import SessionLocal
from app.source_ids import canonical_source_id

FIND = text("""
 SELECT s.id AS source_row_id, i.id AS intelligence_id, i.source_id
 FROM social_listening_results s
 JOIN intelligence_items i ON i.id=s.promoted_intelligence_id
 WHERE s.promoted_intelligence_id IS NOT NULL
 ORDER BY s.id
""")

UPDATE = text("""
 UPDATE intelligence_items
 SET source_id=:canonical
 WHERE id=:intelligence_id
   AND (source_id IS NULL OR TRIM(source_id)='')
""")

def run(session, apply=False, expected_missing=None):
    # Serialize apply runs: the existing relationship and source ID must not change
    # between selecting a proposal and committing it.
    if apply and session.bind.dialect.name=="postgresql":
        session.execute(text("LOCK TABLE social_listening_results, intelligence_items IN SHARE ROW EXCLUSIVE MODE"))
    rows=list(session.execute(FIND).mappings())
    proposals=[]
    conflicts=[]
    already=[]
    for row in rows:
        reference=canonical_source_id("social", row["source_row_id"])
        existing=(row["source_id"] or "").strip()
        if existing==reference:
            already.append(row["intelligence_id"])
        elif existing:
            conflicts.append(row["intelligence_id"])
        else:
            proposals.append((row["intelligence_id"],reference))
    if apply and conflicts:
        session.rollback()
        raise RuntimeError("Conflicting populated source IDs detected; refusing all updates")
    if apply and expected_missing is not None and len(proposals)!=expected_missing:
        session.rollback()
        raise RuntimeError("Backfill changed since preview; no updates applied")
    if apply and len({item[0] for item in proposals})!=len(proposals):
        session.rollback()
        raise RuntimeError("Multiple sources point at one Intelligence record; no updates applied")
    updated=0
    if apply:
        for intelligence_id,reference in proposals:
            result=session.execute(UPDATE,{"intelligence_id":intelligence_id,"canonical":reference})
            if result.rowcount != 1:
                session.rollback()
                raise RuntimeError("Concurrent change detected; backfill rolled back")
            updated+=1
        session.commit()
    return {"linked":len(rows),"already_correct":len(already),
            "conflicting_nonblank_ids":len(conflicts),
            "eligible_missing_ids":len(proposals),
            "updated":updated,"mode":"apply" if apply else "dry_run"}

def main():
    parser=argparse.ArgumentParser()
    parser.add_argument("--apply",action="store_true",help="Commit validated updates (dry-run by default)")
    args=parser.parse_args()
    with SessionLocal() as session:
        report=run(session,args.apply)
        print(json.dumps(report,indent=2))
        if report["conflicting_nonblank_ids"]:
            raise SystemExit("Conflict review required")

if __name__=="__main__":
    main()
