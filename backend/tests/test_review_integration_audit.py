"""Build 73.6: integration-style review persistence and audit regression, no paid providers."""
from unittest.mock import MagicMock, patch
import pytest
from app import campaigns
from app.models import MonitoringCampaign, CampaignEvidence, SocialListeningResult, EvidenceAssessment, IssueCategory, EvidenceReview

def setup_review(permission=True):
    db=MagicMock()
    campaign=MonitoringCampaign(id=1,name='Test campaign')
    item=SocialListeningResult(id=2,text_content='Warga melaporkan dugaan pembagian uang kepada pemilih.')
    assessment=EvidenceAssessment(id=3,campaign_id=1,result_id=2,assessment_version=1,
        relevance_label='RELEVANT',potential_issue_signals_json='[{"category_id":7,"evidence_quote":"pembagian uang kepada pemilih"}]')
    original=assessment.potential_issue_signals_json
    db.get.side_effect=lambda cls,id:campaign if cls is MonitoringCampaign else item
    def query(cls):
        q=MagicMock()
        if cls is CampaignEvidence:q.filter_by.return_value.first.return_value=object()
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
    assert audit.call_args.args[3]=='POTENTIAL_FLAG_REVIEW'
    details=audit.call_args.args[4]
    assert details['assessment_version']==1 and details['legacy_signal_present'] is True

def test_unauthorized_review_never_writes():
    db,profile,_,_=setup_review(permission=False)
    with patch.object(campaigns,'allowed',return_value=True),patch.object(campaigns,'has',side_effect=lambda p,k:p['permissions'].get(k,False)):
        with pytest.raises(PermissionError):
            campaigns.campaign_action(db,profile,'campaignFlagReview',{
                'result_id':'2','assessment_version':1,'decision':'FLAG_CONFIRMED',
                'rationale':'Officer requests evidence-based review.'},id='1')
    db.add.assert_not_called()
    db.commit.assert_not_called()
