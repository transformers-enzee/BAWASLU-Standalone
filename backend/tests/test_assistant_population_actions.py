"""Offline regression coverage for scope-correct Assistant social intelligence.

No Supabase network access, paid AI calls, or officer-record writes.
"""
from app.assistant_social_population import collect_social_population, select_action_evidence


def _post(number, *, flagged=False, reviewed=False, correction=False):
    return {
        "id":str(number),
        "relevance_label":"RELEVANT",
        "text_content":f"Gibran: rekaman uji pemantauan nomor {number}",
        "published_at":"2026-11-19",
        "canonical_url":f"https://example.org/posts/{number}",
        "platform":"Facebook",
        "sentiment":"NEGATIVE" if number % 2 else "NEUTRAL",
        "sentiment_origin":"OFFICER_CORRECTION" if correction else "SAVED_ASSESSMENT",
        "is_flagged":flagged,
        "potential_issues":[{"type":"POTENTIAL_REVIEW"}] if flagged else [],
        "flag_review_status":"REVIEWED" if reviewed else None,
    }


def _paged_action(posts):
    ordered=sorted(posts,key=lambda p:int(p["id"]),reverse=True)
    def action(db,profile,name,args):
        assert name=="campaignIntelligenceInbox"
        assert args["paged"] is True
        limit=int(args["page_size"])
        cursor=int(args["cursor"]) if "cursor" in args else None
        available=[p for p in ordered if cursor is None or int(p["id"])<cursor]
        page=available[:limit]
        return {"findings":page,"pagination":{
            "has_more":len(available)>limit,
            "next_cursor":page[-1]["id"] if len(available)>limit and page else None,
        }}
    return action


def test_query_wide_counts_are_not_limited_to_twenty_evidence_posts():
    posts=[_post(i,flagged=(i<=9),reviewed=(i<=3),
                 correction=(i<=2)) for i in range(1,126)]
    outcome=collect_social_population(None,{},"Analisis sentimen Gibran",
                                      _paged_action(posts))
    snapshot=outcome["snapshot"]
    assert outcome["complete"] is True
    assert outcome["matched_count"]==125
    assert snapshot["social_posts"]==125
    assert snapshot["statistics_post_count"]==125
    assert snapshot["analysis_post_count"]==20
    assert sum(snapshot["sentiment_counts"].values())==125
    assert snapshot["potential_issue_signal_post_count"]==9
    assert snapshot["unreviewed_issue_signal_post_count"]==6
    assert snapshot["reviewed_issue_signal_post_count"]==3
    assert snapshot["officer_sentiment_override_post_count"]==2
    assert snapshot["unique_source_url_count"]==125
    assert snapshot["statistics_scope"]=="ALL_MATCHED_AUTHORIZED_RECORDS_IN_PAGED_SCAN"


def test_partial_census_is_explicitly_labeled_not_exhaustive():
    posts=[_post(i) for i in range(1,126)]
    outcome=collect_social_population(None,{},"Analisis sentimen Gibran",
                                      _paged_action(posts),max_pages=1)
    snapshot=outcome["snapshot"]
    assert outcome["complete"] is False
    assert snapshot["statistics_post_count"]==100
    assert snapshot["population_complete"] is False
    assert "INCOMPLETE" in snapshot["statistics_scope"]
    assert "partial" in snapshot["notice"].lower()


def test_action_request_reserves_pending_candidates_not_confirmed_violations():
    ranked=[_post(i,flagged=i in (27,28,29),reviewed=i==27)
            for i in range(1,31)]
    selected=select_action_evidence(ranked,
                "Apa langkah tindak lanjut BAWASLU terkait Gibran?",limit=20)
    chosen={row["id"] for row in selected}
    assert len(selected)==20
    assert "28" in chosen and "29" in chosen
    assert "27" not in chosen
    assert all(row in ranked for row in selected)
    regular=select_action_evidence(ranked,"Analisis sentimen Gibran",limit=20)
    assert [x["id"] for x in regular]==[str(i) for i in range(1,21)]


def test_saved_issue_flag_is_not_a_case_assignment():
    posts=[_post(1,flagged=True)]
    result=collect_social_population(None,{},"Analisis Gibran",
                                     _paged_action(posts))["snapshot"]
    assert result["potential_issue_signal_post_count"]==1
    assert result["unreviewed_issue_signal_post_count"]==1
    assert "not verified electoral" in result["issue_signal_disclaimer"]
