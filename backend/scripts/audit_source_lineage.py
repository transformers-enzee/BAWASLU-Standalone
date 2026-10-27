"""Read-only BAWASLU staging evidence/ID coverage audit.

Run in a configured staging environment:
    cd backend && python -m scripts.audit_source_lineage

Prints aggregate counts only, no URLs/content/accounts or credentials.
No OpenAI/SocialCrawl calls and no database writes.
"""
import json
from sqlalchemy import text
from app.db import SessionLocal

QUERIES = {
 "social_source_posts": """
    SELECT COUNT(*) AS total,
      COALESCE(SUM(CASE WHEN canonical_url IS NULL OR TRIM(canonical_url)='' THEN 1 ELSE 0 END),0) AS missing_url,
      COALESCE(SUM(CASE WHEN platform IS NULL OR TRIM(platform)='' THEN 1 ELSE 0 END),0) AS missing_platform,
      COALESCE(SUM(CASE WHEN published_at IS NULL OR TRIM(published_at)='' THEN 1 ELSE 0 END),0) AS missing_publication,
      COALESCE(SUM(CASE WHEN text_content IS NULL OR TRIM(text_content)='' THEN 1 ELSE 0 END),0) AS missing_content,
      COALESCE(SUM(CASE WHEN (observed_handle IS NULL OR TRIM(observed_handle)='')
                             AND (author_name IS NULL OR TRIM(author_name)='') THEN 1 ELSE 0 END),0) AS missing_account,
      COALESCE(SUM(CASE WHEN provider_result_id IS NULL OR TRIM(provider_result_id)='' THEN 1 ELSE 0 END),0) AS missing_provider_id
    FROM social_listening_results""",
 "intelligence": """
    SELECT COUNT(*) AS total,
      COALESCE(SUM(CASE WHEN source_url IS NULL OR TRIM(source_url)='' THEN 1 ELSE 0 END),0) AS missing_url,
      COALESCE(SUM(CASE WHEN platform IS NULL OR TRIM(platform)='' THEN 1 ELSE 0 END),0) AS missing_platform,
      COALESCE(SUM(CASE WHEN (publication_datetime IS NULL OR TRIM(publication_datetime)='')
                             AND (publication_date IS NULL OR TRIM(publication_date)='') THEN 1 ELSE 0 END),0) AS missing_publication,
      COALESCE(SUM(CASE WHEN original_content IS NULL OR TRIM(original_content)='' THEN 1 ELSE 0 END),0) AS missing_content,
      COALESCE(SUM(CASE WHEN (observed_publisher_handle IS NULL OR TRIM(observed_publisher_handle)='')
                             AND (author IS NULL OR TRIM(author)='') THEN 1 ELSE 0 END),0) AS missing_account,
      COALESCE(SUM(CASE WHEN source_id IS NULL OR TRIM(source_id)='' THEN 1 ELSE 0 END),0) AS missing_source_id
    FROM intelligence_items""",
 "promotion_lineage": """
    SELECT COUNT(*) AS promoted,
      COALESCE(SUM(CASE WHEN i.id IS NULL THEN 1 ELSE 0 END),0) AS broken_intelligence_fk,
      COALESCE(SUM(CASE WHEN i.source_id IS NULL OR TRIM(i.source_id)='' THEN 1 ELSE 0 END),0) AS missing_canonical_id,
      COALESCE(SUM(CASE WHEN i.source_id IS NOT NULL AND TRIM(i.source_id)<>''
                       AND i.source_id <> ('social:' || CAST(s.id AS TEXT)) THEN 1 ELSE 0 END),0) AS conflicting_canonical_id
    FROM social_listening_results s
    LEFT JOIN intelligence_items i ON i.id=s.promoted_intelligence_id
    WHERE s.promoted_intelligence_id IS NOT NULL""",
 "candidate_tracking": """
    SELECT COUNT(*) AS candidates,
      COALESCE(SUM(CASE WHEN status='Active' THEN 1 ELSE 0 END),0) AS active_candidates
    FROM watchlist_items WHERE LOWER(type)='candidate'""",
 "account_evidence": """
    SELECT COUNT(*) AS mappings
    FROM watchlist_account_evidence""",
 "pilot_smart_radar": """
    SELECT COUNT(*) AS total,
      COALESCE(SUM(CASE WHEN source_url IS NULL OR TRIM(source_url)='' THEN 1 ELSE 0 END),0) AS missing_url,
      COALESCE(SUM(CASE WHEN platform IS NULL OR TRIM(platform)='' THEN 1 ELSE 0 END),0) AS missing_platform,
      COALESCE(SUM(CASE WHEN published_at_raw IS NULL OR TRIM(published_at_raw)='' THEN 1 ELSE 0 END),0) AS missing_publication,
      COALESCE(SUM(CASE WHEN message_original IS NULL OR TRIM(message_original)='' THEN 1 ELSE 0 END),0) AS missing_content,
      COALESCE(SUM(CASE WHEN account_raw IS NULL OR TRIM(account_raw)='' THEN 1 ELSE 0 END),0) AS missing_account,
      COALESCE(SUM(CASE WHEN pilot_post_id IS NULL OR TRIM(pilot_post_id)='' THEN 1 ELSE 0 END),0) AS missing_pilot_id
    FROM pilot_smart_radar.source_posts"""
}

def audit(session):
    report={}
    for key, sql in QUERIES.items():
        try:
            row=session.execute(text(sql)).mappings().one()
            report[key]={name:int(value or 0) for name,value in row.items()}
        except Exception:
            # A missing pilot schema should be reported, not silently treated
            # as an empty batch. Roll back failed reads to keep session usable.
            session.rollback()
            report[key]={"state":"unavailable"}
    report["canonical_id_status"]="NAMESPACED_SOURCE_IDS_DEFINED: social:<saved social result id>, radar:<saved pilot post id>, candidate:<saved watchlist registry id>. Cross-module backfill and staging verification required."
    return report

def main():
    with SessionLocal() as session:
        print(json.dumps(audit(session),indent=2,sort_keys=True))

if __name__ == "__main__":
    main()
