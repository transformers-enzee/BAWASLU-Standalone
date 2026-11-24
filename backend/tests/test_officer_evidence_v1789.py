"""Evidence recovery and transparent validation regression tests (offline)."""
import io
import json
import subprocess
from types import SimpleNamespace
from app.officer_action_v3 import analytics,language,research,document_extract,decisions,quality,legal

QUESTION="What are the top 10 election violations in Indonesia? Please breakdown by provinces, candidates, parties, and any subjects. How can BAWASLU tackle them more effectively? What are the laws that should be reviewed?"
SOURCE={"id":"P-1","kind":"OFFICIAL","read_status":"READ","url":"https://jdih.bawaslu.go.id/peraturan/synthetic.pdf",
        "excerpt":"Synthetic test dataset. Province A reported 12 cases. Province B reported 8 cases. Pasal 99 Synthetic provision for testing only."}

def test_english_query_language_and_explicit_override():
    assert language.requested_language(QUESTION)=="en"
    assert language.requested_language("Apa pelanggaran yang paling banyak dan bagaimana cara menanganinya?")=="id"
    assert language.requested_language("Explain the statistics. Answer in Indonesian.")=="id"
    assert language.requested_language("Jelaskan data yang tersedia. Jawab dalam bahasa Inggris.")=="en"
    assert language.wrong_language({"answer":"Berdasarkan data yang tersedia, pelanggaran yang dilaporkan dan ditangani oleh Bawaslu perlu diperiksa."},"en")
    assert not language.wrong_language({"answer":"The evidence is limited and the official counts need to be reviewed."},"en")

def test_all_provider_timeouts_receive_bounded_independent_retries(monkeypatch):
    monkeypatch.setenv("BAWASLU_ASSISTANT_WEB_SEARCH","true")
    calls=[]
    def discover(q,obj,hint,key,model,base,recent):
        calls.append(obj)
        return {"objective":obj,"status":"PROVIDER_TIMEOUT","queries":[],"results":[]}
    monkeypatch.setattr(research,"_discover",discover)
    r=research.public_research(QUESTION,"test","test","https://example.com/v1")
    assert len(calls)==11
    assert len(set(calls))==7
    assert r["status"]=="SEARCH_FAILED"
    assert all(row["status"]=="RESEARCH_INCOMPLETE" for row in r["coverage"])
    assert sum(row["attempts"]==2 for row in r["coverage"])==4

def test_real_document_worker_reads_generated_text_pdf():
    from reportlab.pdfgen import canvas
    buf=io.BytesIO()
    c=canvas.Canvas(buf)
    c.drawString(40,750,"Synthetic report only")
    c.showPage()
    c.drawString(40,750,"Province A reported 12 cases")
    c.save()
    result=research._document(buf.getvalue(),"application/pdf","https://example.com/test.pdf",QUESTION)
    assert result["extraction_code"]=="EXTRACTED",result
    assert "[PDF page 2]" in result["excerpt"]
    assert "Province A reported 12 cases" in result["excerpt"]
    assert result["units_inspected"]==2
    assert result["extraction_method"] in ("poppler","pypdf")

def test_document_worker_reports_timeout_and_parser_error(monkeypatch):
    def fail(*a,**k):raise subprocess.TimeoutExpired("test",24)
    monkeypatch.setattr(research.subprocess,"run",fail)
    assert research._document(b"%PDF-test","application/pdf","https://example.com/x.pdf","test")["extraction_code"]=="EXTRACTION_TIMEOUT"
    monkeypatch.setattr(research.subprocess,"run",lambda *a,**k:SimpleNamespace(returncode=2,stdout=b'{"error_code":"PdfReadError","excerpt":""}'))
    result=research._document(b"%PDF-test","application/pdf","https://example.com/x.pdf","test")
    assert result["extraction_code"]=="PdfReadError"
    assert result["excerpt"]==""

def test_numeric_series_refuses_unmatched_integers_and_cross_source_merge():
    s={"title":"Synthetic province reports","election_type":"Pemilu","period":"2024","case_status":"reports","unit":"reports","group_by":"PROVINCE",
       "rows":[{"label":"Province A","source_label":"Province A","value":12,"source_id":"P-1","source_quote":"Province A reported 12 cases"},
               {"label":"Province B","source_label":"Province B","value":8,"source_id":"P-1","source_quote":"Province B reported 8 cases"},
               {"label":"Fabricated","source_label":"Province A","value":99,"source_id":"P-1","source_quote":"Province A reported 12 cases"}]}
    result=analytics.build_series([s],[SOURCE])
    assert len(result)==1
    assert [r["value"] for r in result[0]["rows"]]==[12,8]
    assert result[0]["range"]==4
    assert result[0]["complete_dataset"] is False
    s["rows"][1]["source_id"]="P-2"
    assert not analytics.build_series([s],[SOURCE,{**SOURCE,"id":"P-2"}])

def test_report_numeric_diagnostics_are_not_certification():
    audit=analytics.audit_report("Province A reported 12 cases [P-1].\nProvince B reported 400 cases [P-1].\nProposed target: 30 days.",[SOURCE])
    assert audit["numeric_lines_checked"]==3
    assert audit["numeric_lines_matched"]==1
    assert len(audit["review_flags"])==2
    assert audit["all_material_claims_verified"] is False

def test_legal_reference_requires_source_quote_and_retains_review():
    row={"issue":"Synthetic issue","institution":"BAWASLU","legal_reference":"Pasal 99","instrument_version":"synthetic","source_ids":["P-1"],"source_quote":"Pasal 99 Synthetic provision for testing only."}
    out=legal.review_legal([row],[SOURCE])[0]
    assert out["primary_text_excerpt_matched"] is True
    assert out["primary_legal_text_confirmed"] is False
    assert out["officer_review_required"] is True
    out=legal.review_legal([{**row,"source_quote":"Pasal 123 invented quote"}],[SOURCE])[0]
    assert not out["primary_text_excerpt_matched"]
    assert out["legal_reference"]=="Controlling official provision not verified"

def test_language_mismatch_triggers_one_regeneration(monkeypatch):
    calls=[]
    def post(*args,**kwargs):
        calls.append(kwargs["json"])
        raw={"answer":"Pelanggaran yang tercatat dan data yang tersedia perlu diperiksa oleh petugas."} if len(calls)==1 else {"answer":"The evidence is incomplete and the officer should review the official report."}
        return SimpleNamespace(raise_for_status=lambda:None,json=lambda:{"status":"completed","output":[{"type":"message","content":[{"type":"output_text","text":json.dumps(raw)}]}]})
    monkeypatch.setattr(decisions.httpx,"post",post)
    out=decisions.synthesize(QUESTION,"RESEARCH","AUTO",[SOURCE],{},"READ","key","model","https://example.com/v1")
    assert len(calls)==2
    assert "Write every substantive answer field in English" in calls[0]["input"][0]["content"]
    assert out["answer"].startswith("The evidence")
