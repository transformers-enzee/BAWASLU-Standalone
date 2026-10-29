"""Guard against unbounded Watchlist reads when filters match no account."""
from pathlib import Path
from app import registry

def test_watchlist_empty_account_filter_must_not_query_all_social_results():
    block=Path(registry.__file__).read_text(encoding='utf-8').split(
        "if action=='watchlistCapturedFeed':",1)[1].split("if action=='createWatchlist':",1)[0]
    guard=block.index('if not match_conditions:')
    query=block.index('query=db.query(SocialListeningResult).filter(or_(*match_conditions))')
    assert guard<query
    assert "'total':0" in block[guard:query]
    assert '_result_in_scope(db,p,item)' in block
