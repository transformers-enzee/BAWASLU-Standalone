"""No-cost QA for versioned Boolean search at monitoring project creation.

The database configuration stays backward compatible: existing keyword
projects are unchanged, Boolean projects use a versioned JSON envelope.
"""
import json
from types import SimpleNamespace
import pytest

from app.project_boolean import (
    parse_boolean, evaluate_boolean, decode_project_query,
    encode_boolean_project_query,
)
from app.campaign_scheduler import campaign_query, keyword_screen
from app.campaigns import _normalize


def test_boolean_parser_and_or_not_grouping_and_phrase():
    tree,anchors=parse_boolean('Gibran AND (ijazah OR pendidikan) NOT hoaks')
    assert anchors==['gibran']
    assert evaluate_boolean(tree,'Gibran membahas syarat ijazah')
    assert evaluate_boolean(tree,'Pendidikan Gibran')
    assert not evaluate_boolean(tree,'Gibran membahas ekonomi')
    assert not evaluate_boolean(tree,'Gibran ijazah hoaks')
    phrase,anchors=parse_boolean('"Gibran Rakabuming" AND pendidikan')
    assert len(anchors)==1
    assert evaluate_boolean(phrase,'Gibran Rakabuming terkait pendidikan')
    assert not evaluate_boolean(phrase,'Gibran dan Rakabuming terkait pendidikan')


def test_or_coverage_requires_two_retrieval_anchors():
    tree,anchors=parse_boolean('Gibran OR Prabowo')
    assert anchors==['gibran','prabowo']
    assert evaluate_boolean(tree,'Prabowo')
    assert not evaluate_boolean(tree,'BAWASLU')


@pytest.mark.parametrize('expression',[
    '', 'Gibran OR', 'OR Gibran', 'Gibran pemilu',
    '(Gibran OR ijazah', 'Gibran AND ()', '"Gibran',
    'NOT Gibran', 'Gibran OR NOT hoaks',
    'A'*513, ' OR '.join(['term']*35),
])
def test_invalid_or_unbounded_boolean_projects_are_rejected(expression):
    with pytest.raises(ValueError):
        parse_boolean(expression)


def test_legacy_keyword_mode_retains_existing_semantics():
    c=SimpleNamespace(primary_keywords_json='["Gibran","pemilu"]',
        secondary_keywords_json='["KPU"]',excluded_keywords_json='["spam"]',
        platforms_json='["instagram"]',language='',date_from='',date_to='',
        province='',regency_city='')
    config=decode_project_query(c.primary_keywords_json)
    assert config['search_mode']=='KEYWORDS'
    assert config['retrieval_terms']==['Gibran','pemilu']
    assert keyword_screen(c,{'text_content':'Gibran pemilu'})['matched']
    assert not keyword_screen(c,{'text_content':'Gibran spam'})['matched']
    assert campaign_query(c)['query']=='Gibran pemilu'


def test_boolean_config_is_saved_in_existing_json_column():
    expr='Gibran AND (ijazah OR pendidikan) NOT hoaks'
    encoded=encode_boolean_project_query(expr)
    assert json.loads(encoded)['schema']=='BAWASLU_PROJECT_BOOLEAN_V1'
    c=SimpleNamespace(primary_keywords_json=encoded,
        secondary_keywords_json='[]',excluded_keywords_json='[]',
        platforms_json='["instagram"]',language='',date_from='',date_to='',
        province='',regency_city='')
    saved=decode_project_query(c.primary_keywords_json)
    assert saved['search_mode']=='BOOLEAN'
    assert saved['boolean_query']==expr
    assert saved['retrieval_terms']==['gibran']
    assert campaign_query(c)['query']=='gibran'
    assert keyword_screen(c,{'text_content':'Gibran punya ijazah'})['matched']
    assert not keyword_screen(c,{'text_content':'Gibran hoaks pendidikan'})['matched']
    assert not keyword_screen(c,{'text_content':'Pendidikan dan KPU'})['matched']


def test_boolean_project_creation_does_not_require_keyword_tags_or_db_migration():
    scope={'id':'test-officer','role':'National Administrator',
           'geographic_scope':'Nationwide'}
    values=_normalize(None,scope,{'name':'Monitoring ijazah',
         'search_mode':'BOOLEAN',
         'boolean_query':'Gibran AND (ijazah OR pendidikan)',
         'platforms':['instagram','tiktok']})
    assert isinstance(json.loads(values['primary_keywords_json']),dict)
    assert values['secondary_keywords_json']=='[]'
    assert values['excluded_keywords_json']=='[]'
    assert decode_project_query(values['primary_keywords_json'])['retrieval_terms']==['gibran']


def test_literal_boundaries_and_whitespace():
    for expression, text, expected in [
        ('KPU','KPUX',False),('KPU','#KPU',True),
        ('"politik uang"','politik uangan',False),
        ('"politik uang"','Politik  uang',True),
        ('BAWASLU AND NOT hoaks','BAWASLU hoaksnya',True),
        ('BAWASLU AND NOT hoaks','BAWASLU hoaks',False),
    ]:
        tree,_=parse_boolean(expression)
        assert evaluate_boolean(tree,text)==expected
    with pytest.raises(ValueError,match='five'):
        encode_boolean_project_query('a OR b OR c OR d OR e OR f')


def test_boolean_trace_distinguishes_required_and_negated_terms():
    from app.project_boolean import boolean_term_trace,discover_boolean_plan
    tree,_=parse_boolean('BAWASLU AND (Bandung OR "Jawa Barat") AND NOT hoaks')
    trace=boolean_term_trace(tree,'Bandung diawasi BAWASLU')
    assert trace==[{'term':'bawaslu','negated':False,'present':True},
                   {'term':'bandung','negated':False,'present':True},
                   {'term':'jawa barat','negated':False,'present':False},
                   {'term':'hoaks','negated':True,'present':False}]
    plan=discover_boolean_plan('BAWASLU AND (Bandung OR "Jawa Barat")')
    assert plan['positive_retrieval_anchors']==['bawaslu']
    assert not plan['uses_anchor_fallback']


def test_saved_post_parser_allows_negative_only_without_relaxing_collection():
    tree,_=parse_boolean('NOT hoaks',require_positive=False)
    assert evaluate_boolean(tree,'pemilu') and not evaluate_boolean(tree,'hoaks')
    with pytest.raises(ValueError):parse_boolean('NOT hoaks')
