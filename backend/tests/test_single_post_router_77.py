"""Build 77.1: Single-record AI actions must reach the campaign router."""
from unittest.mock import patch
from app.socialcrawl import social_listening_action


def test_single_post_preview_dispatches_without_paid_provider():
    with patch('app.campaigns.campaign_action',return_value={'paid_ai_executed':False,'result_id':'649'}) as handler:
        result= social_listening_action(None,{},'campaignSingleAssessmentPreview',{'result_id':'649'},'1')
    assert result['paid_ai_executed'] is False
    handler.assert_called_once_with(None,{},'campaignSingleAssessmentPreview',{'result_id':'649'},'1')


def test_single_post_confirm_dispatches_without_using_batch():
    with patch('app.campaigns.campaign_action',return_value={'single_assessment_accepted':True}) as handler:
        result=social_listening_action(None,{},'campaignSingleAssessmentStart',{'result_id':'649','confirm_ai_cost':True},'1')
    assert result['single_assessment_accepted'] is True
    handler.assert_called_once()
