"""Build 73.5: Server-side review validation, without AI or crawl providers."""
import pytest
from unittest.mock import MagicMock, patch
from app import campaigns
from app.models import MonitoringCampaign, CampaignEvidence, SocialListeningResult, EvidenceAssessment

def run_review(payload, permission=True, relevance='RELEVANT', version=1):
    db=MagicMock()
    campaign=MonitoringCampaign(id=1,name='QA')
    evidence=SocialListeningResult(id=2,text_content='Warga melaporkan dugaan pembagian uang kepada pemilih.')
    assessment=EvidenceAssessment(id=3,campaign_id=1,result_id=2,
        assessment_version=version,relevance_label=relevance,
        potential_issue_signals_json='[{"category_id":7,"evidence_quote":"pembagian uang kepada pemilih"}]')
    db.get.side_effect=lambda cls,id:campaign if cls is MonitoringCampaign else evidence
    def query_side(cls):
        q=MagicMock()
        if cls is CampaignEvidence:q.filter_by.return_value.first.return_value=object()
        elif cls is EvidenceAssessment:q.filter_by.return_value.order_by.return_value.first.return_value=assessment
        return q
    db.query.side_effect=query_side
    profile={'id':'10','permissions':{'view_intelligence':True,'human_validation':permission},'status':'Active'}
    with patch.object(campaigns,'allowed',return_value=True),patch.object(campaigns,'has',side_effect=lambda p,k:p['permissions'].get(k,False)),patch('app.socialcrawl._result_in_scope',return_value=True):
        return campaigns.campaign_action(db,profile,'campaignFlagReview',payload,id='1'),db,assessment

@pytest.mark.parametrize('decision',['INVALID','CONFIRM','',None])
def test_invalid_review_decision_rejected_without_writes(decision):
    with pytest.raises(ValueError,match='Invalid flag review decision'):
        run_review({'result_id':'2','assessment_version':1,'decision':decision,'rationale':'Sufficient review rationale'})

@pytest.mark.parametrize('rationale',['short',' '*12,'a'*1501])
def test_insufficient_review_rationale_rejected(rationale):
    with pytest.raises(ValueError,match='Rationale must contain'):
        run_review({'result_id':'2','assessment_version':1,'decision':'FLAG_CONFIRMED','rationale':rationale})

def test_stale_assessment_version_rejected():
    with pytest.raises(ValueError,match='Assessment changed'):
        run_review({'result_id':'2','assessment_version':1,'decision':'FLAG_DISMISSED','rationale':'Detailed officer assessment'},version=2)

def test_non_relevant_evidence_rejected():
    with pytest.raises(ValueError,match='Relevant AI-assessed evidence required'):
        run_review({'result_id':'2','assessment_version':1,'decision':'FLAG_CONFIRMED','rationale':'Detailed officer assessment'},relevance='IRRELEVANT')

def test_permission_enforced_for_review():
    with pytest.raises(PermissionError,match='Human review permission'):
        run_review({'result_id':'2','assessment_version':1,'decision':'FLAG_CONFIRMED','rationale':'Detailed officer assessment'},permission=False)
