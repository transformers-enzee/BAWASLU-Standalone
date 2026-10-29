from app.processing_hints import classification_contract,summarize_scoped_findings

def test_saved_player_contract_reused_without_inventing_verified_evidence():
    row={'id':'10','campaign_id':'2','text_content':'Warga mempertanyakan daftar pemilih',
      'relevance_label':'RELEVANT','candidate_signals':[],
      'topic_labels':['Electoral Operations'],
      'public_concern_signals':[{'evidence_quote':'Warga mempertanyakan daftar pemilih'}],
      'attention_assessment':{'urgency':'LOW','status':'AI_ASSESSMENT_UNVERIFIED'},
      'player_summaries':[{'player':'Public Concerns','summary':'Residents asked questions'}]}
    result=classification_contract(row)
    assert result['candidate_classification']=='NO_CANDIDATE'
    assert result['public_concern_signals']==row['public_concern_signals']
    assert result['attention_assessment']==row['attention_assessment']
    assert result['player_summary_drafts']==row['player_summaries']
    assert result['source_evidence_verified'] is False

def test_draft_summaries_cannot_verify_incident():
    row={'id':'10','campaign_id':'2','text_content':'Warga mempertanyakan daftar pemilih',
      'relevance_label':'RELEVANT','potential_issues':[],
      'player_summaries':[{'player':'Public Concerns',
        'status':'AI_DRAFT_REQUIRES_HUMAN_REVIEW',
        'summary':'Public discussion','source_quote':'Warga mempertanyakan daftar pemilih'}]}
    result=summarize_scoped_findings([row])
    assert result['incident_clusters_verified']==0
    assert result['narratives_verified']==0
    assert result['paid_provider_called'] is False
