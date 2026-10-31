"""Build 73.6: integration-style review persistence and audit regression, no paid providers."""
from unittest.mock import MagicMock, patch
import pytest
from app import campaigns
from app.models import MonitoringCampaign, CampaignEvidence, SocialListeningResult, EvidenceAssessment, IssueCategory, EvidenceReview

def setup_review(permission=True, linked=True):
    db=MagicMock()
    campaign=MonitoringCampaign(id=1,name='Test campaign')
    item=SocialListeningResult(id=2,text_content='Warga melaporkan dugaan pembagian uang kepada pemilih.')
    assessment=EvidenceAssessment(id=3,campaign_id=1,result_id=2,assessment_version=1,
        relevance_label='RELEVANT',potential_issue_signals_json='[{"category_id":7,"evidence_quote":"pembagian uang kepada pemilih"}]')
    original=assessment.potential_issue_signals_json
    db.get.side_effect=lambda cls,id:campaign if cls is MonitoringCampaign else item
    def query(cls):
        q=MagicMock()
        if cls is CampaignEvidence:
            q.filter.return_value.first.return_value=object() if linked else None
            q.filter_by.return_value.first.return_value=object() if linked else None
        if cls is EvidenceAssessment:q.filter_by.return_value.order_by.return_value.first.return_value=assessment
        if cls is IssueCategory:q.filter.return_value.all.return_value=[IssueCategory(id=7,name='Politik Uang',active=True)]
        return q
    db.query.side_effect=query
    profile={'id':'officer-10','permissions':{'view_intelligence':True,'human_validation':permission},'status':'Active'}
    return db,profile,assessment,original

@pytest.mark.parametrize('decision',['FLAG_CONFIRMED','FLAG_DISMISSED','FURTHER_INVESTIGATION'])
def test_authorized_review_is_appended_and_audited(decision):
    db,profile,assessment,original=setup_review()
    def assign_id():
        db.add.call_args.args[0].id=77
    db.flush.side_effect=assign_id
    with patch.object(campaigns,'allowed',return_value=True),patch.object(campaigns,'has',side_effect=lambda p,k:p['permissions'].get(k,False)),patch('app.socialcrawl._result_in_scope',return_value=True),patch.object(campaigns,'audit') as audit:
        result=campaigns.campaign_action(db,profile,'campaignFlagReview',{
            'result_id':'2','assessment_version':1,'decision':decision,
            'rationale':'Officer requests evidence-based review.'},id='1')
    assert result['saved'] is True and result['paid_provider_called'] is False
    review=db.add.call_args.args[0]
    assert isinstance(review,EvidenceReview)
    assert review.assessment_id==3 and review.reviewer_id=='officer-10'
    assert review.decision==decision
    assert assessment.potential_issue_signals_json==original
    assert db.commit.call_count==1
    assert audit.call_args.args[4]=='POTENTIAL_FLAG_REVIEW'
    details=audit.call_args.args[5]
    assert details['assessment_version']==1 and details['legacy_signal_present'] is True
    assert audit.call_args.args[3]==77

def test_unauthorized_review_never_writes():
    db,profile,_,_=setup_review(permission=False)
    with patch.object(campaigns,'allowed',return_value=True),patch.object(campaigns,'has',side_effect=lambda p,k:p['permissions'].get(k,False)):
        with pytest.raises(PermissionError):
            campaigns.campaign_action(db,profile,'campaignFlagReview',{
                'result_id':'2','assessment_version':1,'decision':'FLAG_CONFIRMED',
                'rationale':'Officer requests evidence-based review.'},id='1')
    db.add.assert_not_called()
    db.commit.assert_not_called()

@pytest.mark.parametrize('campaign_allowed,permission',[(False,True),(True,False),(False,False)])
def test_review_denied_if_campaign_or_permission_missing(campaign_allowed,permission):
    db,profile,assessment,original=setup_review(permission=permission)
    with patch.object(campaigns,'allowed',return_value=campaign_allowed),patch.object(campaigns,'has',side_effect=lambda p,k:p['permissions'].get(k,False)),patch.object(campaigns,'audit') as audit_mock:
        with pytest.raises(PermissionError,match='Human review permission and campaign access required'):
            campaigns.campaign_action(db,profile,'campaignFlagReview',{
                'result_id':'2','assessment_version':1,'decision':'FLAG_CONFIRMED',
                'rationale':'Officer reviewed primary evidence.'},id='1')
    db.add.assert_not_called()
    db.commit.assert_not_called()
    audit_mock.assert_not_called()
    assert assessment.potential_issue_signals_json==original

@pytest.mark.parametrize('linked,in_scope',[(False,True),(True,False)])
def test_review_denied_for_unlinked_or_out_of_scope_evidence(linked,in_scope):
    db,profile,assessment,original=setup_review(linked=linked)
    with patch.object(campaigns,'allowed',return_value=True),patch.object(campaigns,'has',return_value=True),patch('app.socialcrawl._result_in_scope',return_value=in_scope),patch.object(campaigns,'audit') as audit_mock:
        with pytest.raises(ValueError,match='Evidence unavailable'):
            campaigns.campaign_action(db,profile,'campaignFlagReview',{
                'result_id':'2','assessment_version':1,'decision':'FLAG_DISMISSED',
                'rationale':'Officer reviewed primary evidence.'},id='1')
    db.add.assert_not_called()
    db.commit.assert_not_called()
    audit_mock.assert_not_called()
    assert assessment.potential_issue_signals_json==original
