"""Guard against unbounded Watchlist reads when filters match no account."""
from pathlib import Path
from app import registry

def test_watchlist_empty_account_filter_must_not_query_all_social_results():
    block=Path(registry.__file__).read_text(encoding='utf-8').split(
        "if action=='watchlistCapturedFeed':",1)[1].split("if action=='createWatchlist':",1)[0]
    guard=block.index('if not candidates:')
    query=block.index('query=db.query(SocialListeningResult).filter(or_(*candidates))')
    # Candidate mentions require a saved campaign link and must exclude
    # account-only collection, so an unmatched handle never expands to all posts.
    assert "CampaignEvidence.match_method!='WATCHLIST_ACCOUNT'" in block
    assert "CampaignEvidence.campaign_id==scoped_campaign.id" in block
    assert guard<query
    assert "'total':0" in block[guard:query]
    assert '_result_in_scope(db,p,item)' in block
