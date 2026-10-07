import json

def loads(v, fallback):
    if not v: return fallback
    try: return json.loads(v)
    except Exception: return fallback

def iso(dt): return dt.isoformat() if dt else ''

def intelligence(x):
    return {
      'id':str(x.id),'intelligence_id':x.intelligence_id,'title':x.title,'original_content':x.original_content,
      'original_language':x.original_language,'original_language_code':x.original_language_code,'english_translation':x.english_translation,
      'future_indonesian_translation':x.future_indonesian_translation,'ai_summary':x.ai_summary,'ai_analysis':x.ai_analysis,
      'ai_suggestions':loads(x.ai_suggestions_json,{}),'ai_geography':loads(x.ai_geography_json,{}),'proposed_geography':loads(x.proposed_geography_json,{}),
      'geographic_mismatch_review':loads(x.geographic_mismatch_review_json,{}),'source_type':x.source_type,'ingestion_method':x.ingestion_method,
      'observed_publisher_handle':x.observed_publisher_handle,'provider_source_metadata':loads(x.provider_source_metadata_json,{}),'source_identity':loads(x.source_identity_json,{}),
      'entity_relationships':loads(x.entity_relationships_json,[]),'source_id':x.source_id,'source_url':x.source_url,'source_name':x.source_name,
      'platform':x.platform,'author':x.author,'publication_datetime':x.publication_datetime,'publication_date':x.publication_date,
      'publication_time_precision':x.publication_time_precision,'collection_datetime':x.collection_datetime,'owned_channel':loads(x.owned_channel_json,{}),
      'related_entities':loads(x.related_entities_json,[]),'related_topics':loads(x.related_topics_json,[]),'jurisdiction_type':x.jurisdiction_type,
      'jurisdiction_confirmed':x.jurisdiction_confirmed,'jurisdiction_confirmed_by':x.jurisdiction_confirmed_by,'jurisdiction_confirmed_at':x.jurisdiction_confirmed_at,
      'jurisdiction_source':x.jurisdiction_source,'province':x.province,'regency_city':x.regency_city,'province_code':x.province_code,'regency_city_code':x.regency_city_code,
      'geographic_assignments':loads(x.geographic_assignments_json,[]),'location_text':x.location_text,'potential_issue_category':x.potential_issue_category,
      'analyst_notes':x.analyst_notes,'reason':x.reason,'evidence_state':x.evidence_state,'evidence_type':x.evidence_type,'verification_status':x.verification_status,
      'intelligence_extraction':loads(x.intelligence_extraction_json,{}),'supervision_screening':loads(x.supervision_screening_json,{}),'review_status':x.review_status,
      'confidence':x.confidence,'priority':x.priority,'assigned_reviewer':x.assigned_reviewer,'review_notes':x.review_notes,'validated_at':x.validated_at,
      'duplicate_of':x.duplicate_of,'duplicate_resolution':x.duplicate_resolution,'merged_into':x.merged_into,'watchlist_id':x.watchlist_id,
      'created_date':iso(x.created_at),'updated_date':iso(x.updated_at)
    }

def watchlist(x): return {'id':str(x.id),'name':x.name,'type':x.type,'description':x.description,'province':x.province,'regency_city':x.regency_city,'related_election':x.related_election,'related_entity':x.related_entity,'related_topics':loads(x.related_topics_json,[]),'priority':x.priority,'status':x.status,'notes':x.notes,'created_date':iso(x.created_at),'updated_date':iso(x.updated_at)}
def source_account(x): return {'id':str(x.id),'watchlist_id':str(x.watchlist_id),'platform':x.platform,'url':x.url,'handle':x.handle,'province':x.province,'regency_city':x.regency_city}
def relationship(x): return {'id':str(x.id),'from_id':str(x.from_id),'to_id':str(x.to_id),'relationship_type':x.relationship_type,'province':x.province}
def evidence_file(x): return {'id':str(x.id),'intelligence_item_id':str(x.intelligence_item_id),'file_uri':x.file_uri,'original_filename':x.original_filename,'file_type':x.file_type,'uploaded_by':x.uploaded_by,'uploaded_at':x.uploaded_at,'related_entity':x.related_entity,'related_location':x.related_location,'description':x.description,'evidence_state':x.evidence_state}
def audit_event(x): return {'id':str(x.id),'subject_type':x.subject_type,'subject_id':x.subject_id,'action':x.action,'actor_id':x.actor_id,'actor_name':x.actor_name,'changes':loads(x.changes_json,{}),'occurred_at':x.occurred_at,'created_date':x.occurred_at}
