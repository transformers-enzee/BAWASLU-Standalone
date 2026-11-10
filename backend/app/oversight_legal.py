"""Officer-facing legal review separate from social-platform moderation.

This is a grounded triage surface, never a legal verdict or an automated
takedown. Indonesian laws and platform rules require their own current sources.
"""
from collections import Counter
from fastapi import APIRouter,Depends,HTTPException
from sqlalchemy.orm import Session
from .db import get_db
from .auth import current_user
from .access import profile,has
from .models import User

router=APIRouter(prefix="/api/oversight",tags=["oversight-legal"])
STEPS={
  "id":[
    "Amankan URL asli, tanggal, tangkapan layar, konteks, dan riwayat bukti.",
    "Pastikan fakta, identitas pihak, locus kejadian, serta keaslian dokumen.",
    "Cocokkan dugaan dengan aturan pemilu yang berlaku beserta pasal, unsur, dan kewenangan.",
    "Tugaskan kajian hukum kepada petugas nasional/provinsi yang berwenang.",
    "Jika memenuhi syarat setelah verifikasi, ikuti prosedur pelaporan/penanganan resmi; evaluasi pelaporan platform secara terpisah."
  ],
  "en":[
    "Preserve original URLs, dates, screenshots, context and evidence chain.",
    "Verify facts, parties, incident location and original documentation.",
    "Compare the allegation with the current electoral law, its legal elements and authority.",
    "Assign legal assessment to the competent national or provincial officers.",
    "If substantiated, follow formal reporting/handling procedures; evaluate platform reporting separately."
  ]
}
def legal_snapshot(db,p):
    if not has(p,"view_intelligence"):
        raise HTTPException(403,"Oversight intelligence access required")
    from .campaigns import campaign_action
    from .processing_hints import source_hints
    from .assistant_knowledge import retrieve_knowledge
    result=campaign_action(db,p,"campaignIntelligenceInbox",{
        "paged":True,"page_size":80})
    records=result.get("findings") or []
    cases=[]
    suspect_count=0
    platforms=Counter()
    for row in records:
        source=str(row.get("text_content") or "")
        hints=source_hints(source)
        issue=bool(row.get("is_flagged") or row.get("potential_issues") or
                   hints.get("issue_screening",{}).get("needs_human_validation"))
        if not issue:continue
        suspect_count+=1
        platform=str(row.get("platform") or "Unknown")
        platforms[platform]+=1
        if len(cases)>=12:continue
        cases.append({
            "source_id":str(row.get("id")),
            "campaign_id":str(row.get("campaign_id") or ""),
            "source_url":row.get("canonical_url") or "",
            "excerpt":source[:330],"platform":platform,
            "candidate_signals":(row.get("candidate_signals") or [])[:3],
            "province_mentions":hints.get("province_mentions") or [],
            "incident_province_confirmed":row.get("incident_jurisdiction_verified") is True,
            "potential_violation_ai_signal":True,
            "human_flag_status":row.get("flag_review_status") or "UNREVIEWED",
            "legal_status":"REQUIRES_OFFICER_LEGAL_REVIEW",
            "platform_policy_status":"NOT_ASSESSED_AGAINST_CURRENT_PLATFORM_RULES",
            "follow_up_without_takedown":True
        })

    refs=retrieve_knowledge(db,p,"pelanggaran pemilu perbawaslu peraturan hukum aturan media sosial",3)
    return {"source":"AUTHORIZED_SAVED_INBOX_REVIEW_QUEUE",
        "review_queue":cases,
        "sampled_relevant_posts":len(records),
        "suspected_cases_in_sample":suspect_count,
        "counts_are_sample_only":True,
        "platforms":dict(platforms),
        "legal_references":[{"title":x["title"],"document_id":x["document_id"],"page":x["page"]}
                           for x in refs],
        "legal_verdict":"NONE",
        "platform_rule_verdict":"NONE",
        "legal_follow_up_steps":STEPS["id"],
        "notices":{
            "id":"Dugaan pelanggaran hukum tidak sama dengan pelanggaran pedoman komunitas platform. Takedown bukan penyelesaian proses hukum. Verifikasi peraturan resmi terkini, unsur, wewenang, bukti dan proses penanganan oleh petugas.",
            "en":"A suspected legal violation is not the same as a breach of platform community rules. A takedown is not a legal outcome. Authorized officers must verify current legal provisions, evidence and jurisdiction."
        },
        "paid_provider_called":False}

@router.get("/legal-summary")
def legal_summary(user:User=Depends(current_user),db:Session=Depends(get_db)):
    return legal_snapshot(db,profile(db,user))
