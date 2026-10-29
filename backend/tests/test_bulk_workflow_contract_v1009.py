"""Bulk acceptance contracts: no fabricated officer decisions or pilot lineage."""
from app.processing_hints import (summarize_scoped_findings,exact_source_groups,
 emerging_narrative_candidates,attention_evidence_readiness,incident_location_cues)
from app.summary_readiness import validated_summary_buckets

def test_attention_positive_evidence_still_needs_human_validation():
 body='Warga melaporkan dugaan pelanggaran di Jawa Timur.'
 row={'id':'11','campaign_id':'3','text_content':body,'relevance_label':'RELEVANT',
      'potential_issues':[{'evidence_quote':'dugaan pelanggaran di Jawa Timur'}],
      'is_flagged':True,'flag_review_status':'FURTHER_INVESTIGATION'}
 report=summarize_scoped_findings([row])
 assert report['intelligence_players']['Needs Attention']['count']>=1
 att=attention_evidence_readiness(row)
 assert att['supported_quote_count']==1
 assert att['urgency']=='OFFICER_REQUESTED_FOLLOW_UP'
 assert att['legal_violation_confirmed'] is False

def test_summary_fingerprint_accepts_pipeline_not_development_sample():
 import hashlib
 body='Warga mempertanyakan kualitas pengawasan pemilu di TPS.'
 base={'status':'AI_DRAFT_REQUIRES_HUMAN_REVIEW','player':'Public Concerns',
       'source_quote':'Warga mempertanyakan kualitas pengawasan pemilu',
       'summary':'Residents requested clarification about supervision.',
       'source_text_sha256':hashlib.sha256(body.encode()).hexdigest()}
 b=validated_summary_buckets({'text_content':body,'player_summaries':[
   {**base,'provenance':'PRODUCTION_AI_PIPELINE'},
   {**base,'provenance':'GPT6_CHAT_GENERATED_QA_SAMPLE'},
   {**base,'provenance':'PRODUCTION_AI_PIPELINE','source_text_sha256':'outdated'}]})
 assert len(b['pipeline'])==1
 assert len(b['development'])==1

def test_duplicate_identity_is_source_text_not_duplicate_url():
 rows=[{'id':'1','campaign_id':'3','text_content':'Evidence A','canonical_url':'https://example.test/common'},
       {'id':'2','campaign_id':'3','text_content':'Evidence B','canonical_url':'https://example.test/common'}]
 assert exact_source_groups(rows)==[]

def test_no_accidental_incident_jurisdiction_from_profile_mentions():
 assert incident_location_cues('Petugas dari Jawa Timur menyebut pemilu di Jakarta.')==[]
 assert incident_location_cues('Laporan pelanggaran di Jawa Timur dilaporkan warga.')==['Jawa Timur']

def test_narrative_same_author_or_text_does_not_create_evidence():
 rows=[{'id':str(n),'campaign_id':'3','relevance_label':'RELEVANT','author_name':'one',
        'canonical_url':f'https://example.test/{n}','published_at':'2026-10-01',
        'text_content':'Warga mempertanyakan daftar pemilih '+str(n)} for n in range(3)]
 assert emerging_narrative_candidates(rows)==[]
