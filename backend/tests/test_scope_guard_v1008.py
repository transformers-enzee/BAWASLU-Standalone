"""Optional officer correction must not be credited as automated AI success."""
import hashlib
from app.summary_readiness import validated_summary_buckets
from app.processing_hints import summarize_scoped_findings

def test_manual_correction_does_not_count_as_production_ai_summary():
 body='Ratusan massa meminta pertanggungjawaban Bawaslu atas Pemilu 2024.'
 quote='Ratusan massa meminta pertanggungjawaban Bawaslu'
 row={'text_content':body,'player_summaries':[{
   'player':'Public Concerns','summary':'The demonstrators demanded institutional accountability.',
   'source_quote':quote,'status':'AI_DRAFT_REQUIRES_HUMAN_REVIEW',
   'provenance':'OFFICER_SOURCE_REVIEW',
   'source_text_sha256':hashlib.sha256(body.encode()).hexdigest()}]}
 buckets=validated_summary_buckets(row)
 assert len(buckets['pipeline'])==0
 assert len(buckets['development'])==0
 assert len(buckets['unattributed'])==1

def test_manual_public_concern_does_not_claim_ai_verified_issue():
 body='Warga mempertanyakan pengawasan pemilu.'
 row={'id':'225','campaign_id':'1','relevance_label':'RELEVANT',
      'text_content':body,'potential_issues':[],
      'public_concern_signals':[{'evidence_quote':body,'status':'HUMAN_CONCERN_REVIEWED',
      'provenance':'OFFICER_SOURCE_REVIEW','legal_violation_confirmed':False}]}
 out=summarize_scoped_findings([row])
 assert out['intelligence_players']['Public Concerns']['count']==1
 assert out['intelligence_players']['Potential Violations']['count']==0
 assert out['narratives_verified']==0
 assert out['paid_provider_called'] is False
