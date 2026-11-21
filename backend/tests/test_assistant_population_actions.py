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
    assert snapshot["sentiment_percentages"]["NEGATIVE"]==round(100*63/125,1)
    assert snapshot["sentiment_percentages"]["NEUTRAL"]==round(100*62/125,1)
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


def test_officer_dismissal_is_not_pending_or_live_signal():
    dismissed=_post(100,flagged=False,reviewed=False)
    dismissed["potential_issues"]=[{"type":"OLD_AI_SUGGESTION"}]
    dismissed["flag_review_status"]="FLAG_DISMISSED"
    old_unaccepted=_post(101,flagged=False,reviewed=False)
    old_unaccepted["potential_issues"]=[{"type":"UNACCEPTED_AI_SUGGESTION"}]
    pending=_post(102,flagged=True,reviewed=False)
    reviewed=_post(103,flagged=True,reviewed=False)
    reviewed["flag_review_status"]="FURTHER_INVESTIGATION"
    snapshot=collect_social_population(
        None,{},"Analisis Gibran",
        _paged_action([dismissed,old_unaccepted,pending,reviewed]))["snapshot"]
    assert snapshot["social_posts"]==4
    assert snapshot["potential_issue_signal_post_count"]==2
    assert snapshot["unreviewed_issue_signal_post_count"]==1
    assert snapshot["reviewed_issue_signal_post_count"]==1
    ordered=[dismissed,old_unaccepted,pending,reviewed]
    selected=select_action_evidence(
        ordered,"Apa langkah tindak lanjut BAWASLU terkait Gibran?",limit=2,reserve=2)
    assert "102" in [row["id"] for row in selected]
    assert "100" not in [row["id"] for row in selected]


def test_empty_population_has_zero_shares_without_divide_by_zero():
    snapshot=collect_social_population(
        None,{},"Gibran",_paged_action([]))["snapshot"]
    assert snapshot["social_posts"]==0
    assert snapshot["population_complete"] is True
    assert all(value==0.0 for value in snapshot["sentiment_percentages"].values())


def test_missing_pagination_metadata_does_not_claim_complete_scan():
    post=_post(1)
    action=lambda db,profile,name,args:{"findings":[post],"pagination":{}}
    result=collect_social_population(None,{},"Gibran",action)
    assert result["complete"] is False
    assert "INCOMPLETE" in result["snapshot"]["statistics_scope"]


def test_social_evidence_exposes_officer_disposition_and_sentiment_origin():
    from app.assistant_orchestration import social_evidence
    dismissed=_post(15,flagged=False,correction=True)
    dismissed["potential_issues"]=[{"signal_type":"POTENTIAL_VIOLATION"}]
    dismissed["flag_review_status"]="FLAG_DISMISSED"
    source=social_evidence(dismissed)
    assert source["issue_review_status"]=="FLAG_DISMISSED"
    assert source["issue_signal_active"] is False
    assert source["sentiment_origin"]=="OFFICER_CORRECTION"
    assert source["sentiment_target_scope"]=="WHOLE_POST_NOT_ENTITY_SPECIFIC"
    assert source["verification_status"]=="UNVERIFIED_SOCIAL_SOURCE"

def test_reviewed_signal_does_not_become_legal_verdict():
    from app.assistant_orchestration import social_evidence
    reviewed=_post(22,flagged=True)
    reviewed["flag_review_status"]="FLAG_CONFIRMED"
    source=social_evidence(reviewed)
    assert source["issue_signal_active"] is True
    assert source["issue_review_status"]=="FLAG_CONFIRMED"
    assert "not a judicial" in source["issue_review_note"]


def test_population_numeric_audit_accepts_actual_distribution():
    from app.assistant_population_readiness import evaluate_population_statistics_answer
    snapshot={"sentiment_percentages":{"NEGATIVE":47.2,"NEUTRAL":45.6,
                 "POSITIVE":6.5,"UNKNOWN":0.7},
              "statistics_post_count":307,"population_complete":True}
    result=evaluate_population_statistics_answer(
        "Negatif: 145 (47,2%). Netral 45,6%. Positif 6,5%.",snapshot)
    assert result["status"]=="PASS_LEXICAL_ONLY"
    assert result["checked_shares"]==3
    assert result["mismatches"]==[]

def test_population_numeric_audit_flags_stale_twenty_post_share():
    from app.assistant_population_readiness import evaluate_population_statistics_answer
    snapshot={"sentiment_percentages":{"NEGATIVE":47.2,"NEUTRAL":45.6,
                 "POSITIVE":6.5,"UNKNOWN":0.7},
              "statistics_post_count":307,"population_complete":True}
    result=evaluate_population_statistics_answer(
        "Sentimen negatif 35% berdasarkan data Social Listening.",snapshot)
    assert result["status"]=="REVIEW_REQUIRED"
    assert result["mismatches"][0]["label"]=="NEGATIVE"

def test_population_numeric_audit_rejects_false_complete_claim():
    from app.assistant_population_readiness import evaluate_population_statistics_answer
    snapshot={"sentiment_percentages":{"NEGATIVE":60.0,"NEUTRAL":40.0},
              "statistics_post_count":100,"population_complete":False}
    result=evaluate_population_statistics_answer(
        "Seluruh data menunjukkan 60% sentimen negatif.",snapshot)
    assert result["status"]=="REVIEW_REQUIRED"
    assert {"scope":"partial_scan_claimed_complete"} in result["mismatches"]

def test_population_numeric_audit_does_not_condemn_hypothetical_scenario():
    from app.assistant_population_readiness import evaluate_population_statistics_answer
    snapshot={"sentiment_percentages":{"NEGATIVE":47.2},
              "statistics_post_count":307,"population_complete":True}
    result=evaluate_population_statistics_answer(
        "Contoh hipotetis: 80% sentimen negatif jika topik meningkat.",snapshot)
    assert result["status"]=="NOT_APPLICABLE"


def test_undismissed_sources_fill_action_evidence_before_dismissed_history():
    active=[_post(i) for i in range(101,125)]
    dismissed=[_post(i,flagged=False) for i in range(1,8)]
    for row in dismissed:
        row["flag_review_status"]="FLAG_DISMISSED"
    # Put dismissed rows first to test preference throughout the fill loop.
    ranked=dismissed+active
    chosen=select_action_evidence(
        ranked,"Apa langkah tindak lanjut BAWASLU?",limit=20)
    assert len(chosen)==20
    assert all(x["flag_review_status"]!="FLAG_DISMISSED" for x in chosen)
