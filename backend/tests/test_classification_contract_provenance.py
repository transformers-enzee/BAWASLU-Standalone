from app.processing_hints import classification_contract, summarize_scoped_findings

def test_source_hints_not_misrepresented_as_paid_topic_classification():
    row={'id':'11','campaign_id':'9','text_content':'Pemilu dan KPU melakukan pengawasan',
         'relevance_label':'RELEVANT','candidate_signals':[]}
    result=classification_contract(row)
    assert result['topic_status']=='NOT_AI_CLASSIFIED'
    assert result['topics']==[]
    assert 'Electoral Operations' in result['topic_keyword_hints_unverified']
    assert result['candidate_classification']=='NO_CANDIDATE'
    assert result['incident_jurisdiction_verified'] is False

def test_reused_saved_topic_and_identity_have_source_provenance():
    row={'id':'11','campaign_id':'9','text_content':'Pemilu dan KPU melakukan pengawasan',
         'relevance_label':'RELEVANT','candidate_signals':['Known Name'],
         'canonical_candidate_ids':['candidate:7'],'candidate_classification':'MATCHED',
         'topic_labels':['Electoral Operations'],'incident_jurisdiction_verified':True}
    result=classification_contract(row)
    assert result['topic_status']=='SAVED_AI_CLASSIFICATION'
    assert result['topics']==['Electoral Operations']
    assert result['canonical_candidate_ids']==['candidate:7']
    assert result['incident_jurisdiction_verified'] is True

def test_empty_findings_are_valid_no_paid_processing():
    summary=summarize_scoped_findings([])
    assert summary['visible_relevant_count']==0
    assert summary['incident_clusters_verified']==0
    assert summary['narratives_verified']==0
    assert summary['paid_provider_called'] is False
