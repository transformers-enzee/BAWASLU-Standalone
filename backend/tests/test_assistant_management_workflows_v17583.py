"""First-phase Management/Operations AI contracts: deterministic, zero API calls."""
import pytest
from app.assistant_workflows import (
    normalize_workflow_request,source_consultation,structured_findings,
    workflow_system_directive,retrieval_question_for_revision,drafting_notice,
)


def test_explicit_source_categories_and_two_ai_modes():
    cfg=normalize_workflow_request({'workflowMode':'STRATEGY_DRAFTING',
          'sourceSelection':{'smartRadar':True,'publicWeb':False,'legalReferences':True}})
    assert cfg['workflow']=='STRATEGY_DRAFTING'
    assert cfg['explicit'] is True
    assert cfg['sources']['publicWeb'] is False
    assert normalize_workflow_request({})['sources']=={
        'smartRadar':True,'publicWeb':False,'legalReferences':True}
    for invalid in (
        {'workflowMode':'EXECUTION'},
        {'sourceSelection':{'smartRadar':False,'publicWeb':False,'legalReferences':False}},
        {'sourceSelection':{'smartRadar':'true'}},
        {'sourceSelection':{'unknown':True}},
    ):
        with pytest.raises(ValueError):
            normalize_workflow_request(invalid)


def test_consulted_labels_reflect_only_retrieved_sources():
    records=[
      {'record_id':'SOCIAL-740','record_type':'SOCIAL_LISTENING'},
      {'record_id':'INT-2026-0111','record_type':'FORMAL_INTELLIGENCE'},
      {'record_id':'DOC-3-P2','record_type':'PDF_KNOWLEDGE'},
    ]
    sources={'smartRadar':True,'publicWeb':True,'legalReferences':True}
    result=source_consultation(sources,records,
          ['SOCIAL-740','DOC-3-P2'],public_urls=['https://example.org/official'])
    saved,web,pdf=result
    assert saved['status']=='CONSULTED' and saved['basis']=='FIXED_SAVED_SNAPSHOT'
    assert saved['selected_count']==2
    assert saved['cited_source_ids']==['SOCIAL-740']
    assert web['basis']=='LIVE_PUBLIC_LOOKUP' and web['urls']==['https://example.org/official']
    assert pdf['status']=='CONSULTED'
    assert pdf['cited_source_ids']==['DOC-3-P2']
    assert 'not independently certified' in pdf['warning']
    no_web=source_consultation(sources,records,[],[])[1]
    assert no_web['status']=='SELECTED_NOT_CONSULTED'
    assert no_web['basis']=='NOT_CONSULTED'
    disabled=source_consultation({'smartRadar':False,'publicWeb':False,'legalReferences':True},records,[],[])[0]
    assert disabled['status']=='NOT_SELECTED'
    simulated=source_consultation({'smartRadar':True},records,[],[],environment='SIMULATED')[0]
    assert simulated['basis']=='SIMULATED_DEMO'


def test_findings_require_valid_citations_and_do_not_upgrade_allegations():
    records=[
      {'record_id':'SOCIAL-740','record_type':'SOCIAL_LISTENING'},
      {'record_id':'DOC-3-P2','record_type':'PDF_KNOWLEDGE'},
    ]
    findings={'observations':[
      'A social post alleges a document issue [SOCIAL-740].',
      'An uploaded PDF discusses procedure [DOC-3-P2].',
      'An unsupported statement names [SOCIAL-999].',
      'A plausible trend without validated citations.',
    ]}
    result=structured_findings(findings,records,['SOCIAL-740','DOC-3-P2'])
    assert result[0]['source_ids']==['SOCIAL-740']
    assert result[0]['evidence_class']=='REPORTED_ALLEGATION_OR_OBSERVATION'
    assert result[0]['support_status']=='SOURCE_LINKED_NOT_FACT_VERIFIED'
    assert result[1]['evidence_class']=='DOCUMENTARY_REFERENCE_REQUIRES_AUTHORITY_CHECK'
    assert result[2]['source_ids']==[] and result[2]['support_status']=='NO_VALIDATED_CITATION'
    assert result[3]['requires_officer_review'] is True


def test_memo_revision_returns_to_original_substantive_user_question():
    history=[
      {'role':'user','text':'Analisis temuan sosial terkait BAWASLU Bandung'},
      {'role':'assistant','text':'Prior AI answer is not primary source evidence'},
      {'role':'user','text':'Write a memo for leadership'},
      {'role':'assistant','text':'Draft memo'},
    ]
    assert retrieval_question_for_revision(
        'Turn the preceding findings into an email draft','Write a memo for leadership',history
    )=='Analisis temuan sosial terkait BAWASLU Bandung'
    assert retrieval_question_for_revision('Research this new issue','irrelevant',history)=='Research this new issue'


def test_management_planning_never_authorizes_legal_actions():
    strategy=workflow_system_directive('STRATEGY_DRAFTING')
    assert 'DRAFT ONLY' in strategy
    assert 'owner' in strategy.casefold()
    assert 'review checkpoint' in strategy
    assert 'Never send a message' in strategy
    research=workflow_system_directive('RESEARCH')
    assert 'duplicate' in research
    assert 'inference' in research
    assert drafting_notice('STRATEGY_DRAFTING')=='DRAFT_ONLY_STAFF_REVIEW_AND_SEND'
