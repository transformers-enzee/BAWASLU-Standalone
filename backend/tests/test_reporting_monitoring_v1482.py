"""v148.2 optional scoped monitoring in an unsigned management briefing.

No Supabase writes, paid AI calls, or claims of unobserved totals.
"""
from datetime import datetime, timedelta
from io import BytesIO
from copy import deepcopy

from docx import Document
from pypdf import PdfReader
from openpyxl import load_workbook

from app.access import profile
from app.models import User
from app.management_reporting import (
    _utc_publication_time, monitoring_snapshot_from_findings,
    build_briefing, briefing_pdf, briefing_docx, briefing_xlsx
)
from test_management_briefings_v1468 import dataset


NOW=datetime(2026,11,12,12,0,0)
START=NOW-timedelta(days=7)


def post(sid, published="2026-11-11T22:00:00+07:00",
         sentiment="NEGATIVE",platform="X",text="Riau electoral oversight"):
    return {
        "canonical_source_id":"social:"+str(sid),
        "published_at_raw":published,
        "sentiment":sentiment,"platform":platform,
        "message_original":text
    }


def finding(kind, *posts, title="Bawaslu Riau oversight",players=None):
    return {"kind":kind,"title":title,
            "players":players if players is not None else (
                ["violations"] if kind=="source_review" else
                ["concerns"] if kind=="discussion" else []),
            "posts":list(posts)}


def test_utc_window_deduplicates_and_never_guesses_missing_dates():
    findings=[
        finding("source_review",post(1),post(2,platform="Instagram",sentiment="POSITIVE")),
        finding("discussion",post(1,sentiment="NEUTRAL"),post(3,published="2026-11-11")),
        finding("narrative_candidate",post(4,published="2026-11-01T08:00:00Z"),
                title="Election rumor",players=["narratives"]),
        finding("discussion",post(5,published="2026-11-12T06:00:00Z",
                                sentiment="NEUTRAL",text="Riau oversight question")),
    ]
    report=monitoring_snapshot_from_findings(findings,START,NOW)
    assert report["unique_relevant_sources_in_recent_inbox"]==5
    assert report["published_in_period"]==3
    assert report["publication_date_unknown"]==1
    assert report["published_outside_period"]==1
    assert report["flagged_potential_violation_posts"]==2
    assert report["public_concern_posts"]==2
    assert report["signal_overlapping_sources_in_period"]==1
    assert report["source_sentiment_conflicts"]==1
    assert report["deduplicated_source_links_removed"]==1
    assert report["emerging_narrative_posts"]==0
    assert report["sentiment_counts"]=={"UNCLASSIFIED":1,"POSITIVE":1,"NEUTRAL":1}
    assert report["platform_counts"]=={"X":2,"Instagram":1}
    assert sum(report["sentiment_counts"].values())==report["published_in_period"]
    assert report["inbox_truncation_status"]=="UNKNOWN"
    assert report["all_platform_conversations_counted"] is False
    assert report["legal_violations_confirmed"] is False
    assert report["paid_provider_called"] is False
    assert _utc_publication_time("2026-11-11") is None
    assert _utc_publication_time("2026-11-11T23:01:00") is None
    assert _utc_publication_time("not a date") is None


def test_topic_filter_applies_to_saved_text_and_finding_title_only():
    report=monitoring_snapshot_from_findings([
        finding("discussion",post(11,text="Riau vote count"),title="Counting"),
        finding("discussion",post(12,text="Bali school opening"),title="Public services")
    ],START,NOW,"vote")
    assert report["published_in_period"]==1
    assert report["unique_relevant_sources_in_recent_inbox"]==1


def test_monitoring_opt_in_preserves_fast_casework_default_and_scoped_sources(monkeypatch):
    db=dataset()
    calls=[]
    try:
        from app import inbox_radar
        def authorized_feed(connection, principal, states=None):
            calls.append(principal.get("province") or "Nationwide")
            if principal.get("province")=="Bali":
                return [finding("discussion",post(50,platform="Facebook",
                   text="Bali local election issue"))],{}
            return [finding("source_review",post(15),
                    title="Riau election incident"),
                    finding("discussion",post(16,platform="Reddit",
                         sentiment="NEUTRAL"),title="Riau public concern")],{}
        monkeypatch.setattr(inbox_radar,"live_inbox_findings",authorized_feed)
        access=profile(db,db.get(User,2))
        baseline=build_briefing(db,access,2,now=NOW,language="en")
        assert calls==[]
        assert baseline["monitoring"]["enabled"] is False
        assert baseline["metrics"]["assignments"]==2
        scoped=build_briefing(db,access,2,now=NOW,language="en",
                             include_monitoring=True)
        assert calls==["Riau"]
        assert scoped["monitoring"]["published_in_period"]==2
        assert scoped["monitoring"]["platform_counts"]=={"X":1,"Reddit":1}
        assert scoped["monitoring"]["flagged_potential_violation_posts"]==1
        assert scoped["monitoring"]["sentiment_counts"]=={"NEGATIVE":1,"NEUTRAL":1}
        assert scoped["data_basis"]=="AUTHORIZED_OFFICER_CASEWORK_AND_SAVED_INBOX_MONITORING_SAMPLE"
        assert scoped["metrics"]==baseline["metrics"]
        assert scoped["template"]["approval_state"]=="DRAFT_NOT_APPROVED"
        assert len(scoped["template"]["scorecard"])==6
        assert scoped["template"]["monitoring_summary"]["published_in_period"]==2
        assert "not the total number of captured posts" in scoped["template"]["executive_summary"]
        assert "Inbox window of up to 300 links per campaign" in " ".join(scoped["template"]["methodology"])
        assert scoped["paid_provider_called"] is False

        bali=build_briefing(db,profile(db,db.get(User,3)),3,now=NOW,
                           language="en",include_monitoring=True)
        assert bali["monitoring"]["platform_counts"]=={"Facebook":1}
        assert "Riau" not in str(bali["template"]["monitoring_summary"])
        assert calls==["Riau","Bali"]
    finally:
        db.close()


def test_exports_include_monitoring_only_when_requested(monkeypatch):
    db=dataset()
    try:
        from app import inbox_radar
        monkeypatch.setattr(inbox_radar,"live_inbox_findings",
            lambda connection,principal,states=None:(
                [finding("source_review",post(17,
                    published=datetime.utcnow().replace(microsecond=0).isoformat()+"Z"))],{}))
        officer=db.get(User,2)
        for callback,prefix in [
            (briefing_pdf,b"%PDF-"),(briefing_docx,b"PK"),(briefing_xlsx,b"PK")
        ]:
            result=callback("weekly","","en",officer,db,include_monitoring=True)
            assert result.body.startswith(prefix)
            assert result.headers["X-Report-Monitoring"]=="SAMPLED_INBOX"
            assert result.headers["X-Report-Approval"]=="DRAFT_NOT_APPROVED"
            assert result.headers["Cache-Control"]=="private, no-store"
            if callback==briefing_pdf:
                content="\n".join(p.extract_text() or "" for p in
                         PdfReader(BytesIO(result.body)).pages)
                assert "Observed Inbox posts (sample)" in content
                assert "monitoring" in content.lower()
            elif callback==briefing_docx:
                word=Document(BytesIO(result.body))
                assert "Observed Inbox posts (sample)" in " ".join(
                    cell.text for t in word.tables for row in t.rows for cell in row.cells)
            else:
                book=load_workbook(BytesIO(result.body),read_only=True)
                content=" ".join(str(x) for row in book["Report Summary"].values
                                 for x in row if x is not None)
                assert "Observed Inbox posts (sample)" in content
        csv_only=briefing_pdf("weekly","","en",officer,db)
        assert csv_only.headers["X-Report-Monitoring"]=="CASEWORK_ONLY"
    finally:db.close()
