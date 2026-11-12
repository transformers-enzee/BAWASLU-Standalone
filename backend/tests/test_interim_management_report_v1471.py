"""Interim BAWASLU management report template and real document export QA.

All tests use SQLite fixtures. No live Supabase writes, paid AI or platform calls.
"""
from io import BytesIO
import pytest
from fastapi import HTTPException
from docx import Document
from openpyxl import load_workbook
from pypdf import PdfReader
from app.access import profile
from app.models import User
from app.management_reporting import (build_briefing, briefing_pdf, briefing_docx,
                                     briefing_xlsx, scoped_cases)
from app.management_report_templates import (
    TEMPLATE_VERSION, build_interim_template, render_pdf, render_docx,
    render_xlsx, _safe_link)
from test_management_briefings_v1468 import dataset


def _get(db,uid=2,period="weekly",topic="",language="id"):
    user=db.get(User,uid)
    return build_briefing(db,profile(db,user),user.id,period,topic,language=language)


def test_interim_report_is_scoped_deterministic_and_never_signed():
    db=dataset()
    try:
        report=_get(db,2)
        template=report["template"]
        assert template["template_version"]==TEMPLATE_VERSION=="INTERIM-1.0"
        assert template["approval_state"]=="DRAFT_NOT_APPROVED"
        assert template["scorecard"][0]["value"]==2
        assert template["scorecard"][1]["value"]==1
        assert len(template["findings"])==2
        assert all("Riau" in row["title"] for row in template["findings"])
        assert all("Bali" not in str(row) for row in template["findings"])
        assert all(value=="" for value in template["signoff"].values())
        assert template["paid_provider_called"] is False
        assert template["automated_legal_verdict"] is False
        assert "DRAF" in template["subtitle"]
        assert "bukan penetapan pelanggaran hukum" in template["executive_summary"]
        # Rendering twice from an identical snapshot must not alter user data.
        assert build_interim_template(report,"id")==template
        assert db.query(User).count()==4
    finally: db.close()


def test_english_issue_specific_report_has_no_cross_province_source():
    db=dataset()
    try:
        report=_get(db,2,topic="Riau",language="en")
        template=report["template"]
        assert template["title"]=="Issue Monitoring Brief"
        assert template["language"]=="en"
        assert "Riau" in template["scope_label"]
        assert len(template["source_appendix"])==2
        assert all("Bali" not in item["source_reference"]
                   for item in template["source_appendix"])
        assert "not a census" in " ".join(template["methodology"]).casefold()
        assert template["recommended_actions"]
        assert template["source_appendix"][0]["source_url"].startswith("https://")
    finally: db.close()


def test_zero_assignment_report_never_invents_findings_or_outcomes():
    db=dataset()
    try:
        report=_get(db,3,topic="Riau",language="en")
        template=report["template"]
        assert report["metrics"]["assignments"]==0
        assert template["findings"]==[]
        assert template["source_appendix"]==[]
        assert "No saved assignments" in template["recommended_actions"][0]
        assert "not" in template["executive_summary"].lower()
    finally: db.close()


def test_docx_pdf_xlsx_exports_have_matching_reference_scope_and_draft_mark():
    db=dataset()
    try:
        template=_get(db,2,language="en")["template"]
        docx_bytes=render_docx(template)
        assert docx_bytes[:2]==b"PK"
        word=Document(BytesIO(docx_bytes))
        word_text="\n".join(p.text for p in word.paragraphs)
        assert "Oversight Intelligence Management Brief" in word_text
        assert "Riau alleged election incident" in word_text
        assert "Bali issue" not in word_text
        assert "Approved by" in word_text
        assert "UNAPPROVED DRAFT" in word.sections[0].footer.paragraphs[0].text

        pdf_bytes=render_pdf(template)
        assert pdf_bytes.startswith(b"%PDF-")
        pdf=PdfReader(BytesIO(pdf_bytes))
        assert len(pdf.pages)>=1
        pdf_text="\n".join(page.extract_text() or "" for page in pdf.pages)
        assert "Oversight Intelligence Management Brief" in pdf_text
        assert "Riau alleged election incident" in pdf_text
        assert "Bali issue" not in pdf_text
        assert "UNAPPROVED DRAFT" in pdf_text

        xlsx_bytes=render_xlsx(template)
        assert xlsx_bytes[:2]==b"PK"
        workbook=load_workbook(BytesIO(xlsx_bytes),read_only=True)
        assert workbook.sheetnames==["Report Summary","Source Appendix"]
        appendix=list(workbook["Source Appendix"].values)
        assert len(appendix)==3
        assert all("Riau" in row[2] for row in appendix[1:])
        assert all("Bali" not in str(row) for row in appendix)
        report_values=" ".join(str(c) for row in workbook["Report Summary"].values for c in row)
        assert "DRAFT_NOT_APPROVED" in report_values
    finally: db.close()


def test_export_endpoints_use_officer_authorization_and_private_no_store():
    db=dataset()
    try:
        officer=db.get(User,2)
        for callback,marker,media in (
            (briefing_pdf,b"%PDF-","application/pdf"),
            (briefing_docx,b"PK","wordprocessingml"),
            (briefing_xlsx,b"PK","spreadsheetml"),
        ):
            response=callback("weekly","","en",officer,db)
            assert response.body.startswith(marker)
            assert media in response.media_type
            assert response.headers["Cache-Control"]=="private, no-store"
            assert response.headers["X-Report-Template"]=="INTERIM-1.0"
            assert response.headers["X-Report-Approval"]=="DRAFT_NOT_APPROVED"
            assert response.headers["content-disposition"].startswith("attachment;")
    finally: db.close()


def test_excel_formula_injection_and_unsafe_source_schemes_stay_inert():
    template=build_interim_template({
        "metrics":{"assignments":1,"active_assignments":1,"closed_assignments":0,
            "submitted_reports":0,"approved_reports":0,"unique_linked_sources":1},
        "period":"weekly", "topic_filter":"=EXP(100)", 
        "scope":{"geographic_scope":"Nationwide","province":""},
        "window_start_utc":"2026-11-01T00:00:00Z",
        "window_end_utc":"2026-11-08T00:00:00Z",
        "department_counts":{"Test department":1},
        "recent_cases":[{"id":1,"title":"=HYPERLINK(1)",
            "department":"=EXP(5)","source_type":"SOCIAL","source_id":"1",
            "campaign_id":1,"status":"OPEN","latest_report_status":None,
            "verified_province":"","source_excerpt":"=IMPORTXML(...)",
            "source_url":"javascript:alert(1)"}],
    },language="en")
    assert template["findings"][0]["source_url"]==""
    wb=load_workbook(BytesIO(render_xlsx(template)))
    sheet=wb["Source Appendix"]
    for coordinate in ("C2","E2","G2"):
        assert sheet[coordinate].data_type!="f"
        assert sheet[coordinate].value.startswith("'=")
    assert _safe_link("javascript:alert(1)")==""
    assert _safe_link("https://user:password@example.invalid/")==""
    assert _safe_link("https://example.invalid/post")=="https://example.invalid/post"


def test_invalid_report_language_and_period_are_rejected():
    db=dataset()
    try:
        with pytest.raises(ValueError):
            _get(db,2,language="es")
        with pytest.raises(HTTPException) as error:
            _get(db,2,period="yearly")
        assert error.value.status_code==422
    finally: db.close()
