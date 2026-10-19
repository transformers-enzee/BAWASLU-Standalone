"""Credit-free unified hotness ranking regression tests (Build 79.6)."""
from app.campaigns import _rank_captured_posts, _captured_post_metrics

def test_hottest_ranks_engagement_and_views_together():
    rows=[
        {'id':'1','engagement_total':20,'views':200},
        {'id':'2','engagement_total':300,'views':10000},
        {'id':'3','engagement_total':80,'views':250000},
        {'id':'4','engagement_total':0,'views':0},
    ]
    ranked=_rank_captured_posts(rows)
    assert ranked[0]['id']=='2'
    assert ranked[-1]['id']=='4'
    assert [x['id'] for x in ranked]==[x['id'] for x in _rank_captured_posts(rows)]
    assert len(ranked)==4

def test_hottest_ranks_popularity_when_engagement_is_missing():
    rows=[
        {'id':'5','engagement_total':None,'views':100000},
        {'id':'6','engagement_total':None,'views':100},
        {'id':'7','engagement_total':None,'views':None},
    ]
    assert [x['id'] for x in _rank_captured_posts(rows)]==['5','6','7']

def test_hottest_ranks_engagement_when_views_unavailable():
    rows=[
        {'id':'5','engagement_total':100,'views':None},
        {'id':'6','engagement_total':10,'views':None},
    ]
    assert [x['id'] for x in _rank_captured_posts(rows)]==['5','6']

def test_provider_metric_parser_keeps_zero_and_missing_distinct():
    metrics=_captured_post_metrics('{"likes":15,"comments":2,"shares":3,"views":800}')
    assert metrics['engagement_total']==20 and metrics['views']==800
    absent=_captured_post_metrics('{}')
    assert absent['engagement_total'] is None and absent['views'] is None
