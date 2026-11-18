"""Read-only administrator cross-module evidence; activity never implies acceptance."""
from sqlalchemy import text

MODULE_COUNTS_SQL="""SELECT
 (SELECT COUNT(*) FROM social_listening_results) AS collected_posts,
 (SELECT COUNT(*) FROM social_listening_results WHERE NULLIF(TRIM(text_content),'') IS NULL) AS missing_post_text,
 (SELECT COUNT(*) FROM monitoring_campaigns) AS campaigns,
 (SELECT COUNT(*) FROM campaign_evidence WHERE match_method!='WATCHLIST_ACCOUNT') AS ordinary_campaign_links,
 (SELECT COUNT(*) FROM campaign_evidence WHERE match_method='WATCHLIST_ACCOUNT') AS watchlist_links,
 (SELECT COUNT(*) FROM watchlist_items WHERE LOWER(type)='candidate' AND status='Active') AS active_candidate_registry_entries,
 (SELECT COUNT(*) FROM intelligence_items) AS intelligence_items,
 (SELECT COUNT(*) FROM assistant_knowledge_pdfs WHERE active=TRUE) AS active_knowledge_pdfs,
 (SELECT COUNT(*) FROM assistant_threads) AS assistant_threads,
 (SELECT COUNT(*) FROM case_assignments) AS officer_cases,
 (SELECT COUNT(*) FROM case_reports) AS officer_reports,
 (SELECT COUNT(*) FROM case_reports WHERE status='APPROVED') AS approved_reports,
 (SELECT COUNT(*) FROM ai_assessment_jobs WHERE state='PENDING') AS pending_ai_jobs,
 (SELECT COUNT(*) FROM ai_assessment_jobs WHERE state='PROCESSING') AS processing_ai_jobs,
 (SELECT COUNT(*) FROM ai_assessment_jobs WHERE state='COMPLETED') AS completed_ai_jobs,
 (SELECT COUNT(*) FROM ai_assessment_jobs WHERE state='SUPERSEDED_ASSESSED') AS superseded_ai_jobs,
 (SELECT COUNT(*) FROM campaign_evidence ce
  WHERE ce.match_method!='WATCHLIST_ACCOUNT'
   AND NOT EXISTS (SELECT 1 FROM evidence_assessments ea WHERE
    ea.campaign_id=ce.campaign_id AND ea.result_id=ce.result_id
    AND ea.id=(SELECT last.id FROM evidence_assessments last
      WHERE last.campaign_id=ce.campaign_id AND last.result_id=ce.result_id
      ORDER BY last.assessment_version DESC,last.id DESC LIMIT 1)
    AND UPPER(COALESCE(ea.relevance_label,'')) IN
     ('RELEVANT','IRRELEVANT','UNCERTAIN'))) AS monitoring_links_without_valid_latest_relevance
"""

def module_acceptance_evidence(db):
    counts={k:int(v or 0) for k,v in db.execute(text(MODULE_COUNTS_SQL)).mappings().one().items()}
    def row(name,observed,checks,notes):
        return {'module':name,'observed_records':int(observed),
                'data_presence':'OBSERVED' if observed else 'NOT_OBSERVED',
                'attention_codes':[code for code,active in checks if active],
                'acceptance_state':'REQUIRES_INDEPENDENT_UAT',
                'verification_scope':notes,'client_signoff_recorded':False}
    modules=[
        row('Social Listening',counts['collected_posts'],[
            ('SOURCE_TEXT_GAPS',counts['missing_post_text']>0),
            ('NO_CAMPAIGN_LINKS',counts['collected_posts']>0 and counts['ordinary_campaign_links']==0)],
            'Check crawl coverage, provider source integrity, campaign filters and cadence through authenticated UAT'),
        row('Candidate Watchlist',counts['active_candidate_registry_entries'],[],
            'Global candidate registry count is not the per-campaign two-slot watchlist limit'),
        row('Intelligence Inbox',counts['intelligence_items'],[],
            'Intelligence entries are not equivalent to all relevance-filtered social evidence'),
        row('Command Center',counts['ordinary_campaign_links'],[],
            'Saved evidence does not prove indicator accuracy, chart freshness or AI summary quality'),
        row('AI Assistant',counts['assistant_threads'],[
            ('NO_ACTIVE_KNOWLEDGE_PDFS',counts['assistant_threads']>0 and not counts['active_knowledge_pdfs'])],
            'Thread and knowledge-base counts do not prove source-grounded answer acceptance'),
        row('Officer Casework',counts['officer_cases'],[],
            'Assignment count does not prove authorized five-stage review completion'),
        row('Management Reporting',counts['officer_reports'],[],
            'Saved reports and workflow approval do not imply client acceptance or a legal outcome'),
        row('AI Assessment & Classification',counts['completed_ai_jobs'],[
            ('PENDING_ASSESSMENT_JOBS',counts['pending_ai_jobs']>0),
            ('PROCESSING_HISTORY_REVIEW',counts['processing_ai_jobs']>0),
            ('UNCLASSIFIED_MONITORING_LINKS',counts['monitoring_links_without_valid_latest_relevance']>0)],
            'Job state and latest relevance do not establish human-label accuracy or authorize paid processing')]
    return {'scope':'MAIN_DATABASE_AGGREGATE_ACCEPTANCE_EVIDENCE',
      'modules':modules,'module_count':len(modules),'counts':counts,
      'completion_percentages_supported':False,
      'release_readiness_certified':False,'formal_client_acceptance_recorded':False,
      'next_step':'Run authorized module-specific end-to-end UAT, keeping human acceptance separate from technical data presence.',
      'source_text_or_personal_identifiers_returned':False,
      'provider_requests':0,'database_writes':0}
