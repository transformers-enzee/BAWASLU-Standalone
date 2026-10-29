"""No-credit real acceptance status contracts: don't claim unverified success."""
import hashlib
from app.summary_readiness import validated_summary_buckets
from app.qa_saved_accuracy import QUERY

def test_12_rejects_spoofed_pipeline_provenance():
 body='Observed post with a source quote of adequate length for testing.'
 real={'source_quote':'source quote of adequate length','summary':'An officer must independently review this evidence.',
       'status':'AI_DRAFT_REQUIRES_HUMAN_REVIEW','provenance':'PRODUCTION_AI_PIPELINE',
       'source_text_sha256':hashlib.sha256(body.encode()).hexdigest()}
 assert len(validated_summary_buckets({'text_content':body,'player_summaries':[real]})['pipeline'])==1
 assert len(validated_summary_buckets({'text_content':body,'player_summaries':[{**real,'source_text_sha256':'f'*64}]})['pipeline'])==0

def test_14_benchmark_never_infers_completion_from_cached_scores():
 query=str(QUERY).lower()
 assert 'qa_ai_assessments' in query
 assert 'qa_imported_human_categories' in query
 assert 'count(*)' in query
 assert 'holdout' in query
