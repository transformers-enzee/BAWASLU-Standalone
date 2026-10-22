"""Build 64.4 local keyword semantics, no external provider credits."""
import json
from types import SimpleNamespace
from app.campaign_scheduler import keyword_screen

def c(primary,secondary=None,excluded=None):
    return SimpleNamespace(primary_keywords_json=json.dumps(primary),
        secondary_keywords_json=json.dumps(secondary or []),
        excluded_keywords_json=json.dumps(excluded or []))

def test_main_keyword_or_matches_either():
    campaign=c(['bawaslu','pemilu'])
    assert keyword_screen(campaign,{'text_content':'BAWASLU oversight'})['matched']
    assert keyword_screen(campaign,{'text_content':'Pemilu preparations'})['matched']
    assert keyword_screen(campaign,{'text_content':'BAWASLU Pemilu'})['matched']
    assert not keyword_screen(campaign,{'text_content':'unrelated football'})['matched']

def test_secondary_is_context_not_mandatory():
    campaign=c(['bawaslu','pemilu'],['Gibran','election oversight'])
    a=keyword_screen(campaign,{'text_content':'Bawaslu monitors the election'})
    b=keyword_screen(campaign,{'text_content':'Bawaslu monitors Gibran'})
    assert a['matched'] and a['context_signal']=='MAIN_KEYWORD_ONLY'
    assert b['matched'] and b['secondary_keywords']==['Gibran']
    assert b['context_signal']=='STRONGER_CONTEXT'

def test_exclusions_take_precedence():
    campaign=c(['pemilu'],['Gibran'],['concert'])
    data=keyword_screen(campaign,{'text_content':'Pemilu concert Gibran'})
    assert not data['matched']
    assert data['excluded_keywords']==['concert']

def test_case_insensitive_multiword_and_comments():
    campaign=c(['money politics'],['pemilu'])
    result=keyword_screen(campaign,{'text_content':'Election briefing',
            'raw':{'comments':[{'text':'Report MONEY POLITICS during Pemilu'}]}})
    assert result['matched']
    assert result['main_keywords']==['money politics']
    assert result['secondary_keywords']==['pemilu']
