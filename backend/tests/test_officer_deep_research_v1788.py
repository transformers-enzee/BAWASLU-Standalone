"""Independent assistant research/report regression tests. No provider credits."""
import io
import pytest
from app.officer_action_v3 import depth,research,document_extract,quality,decisions

QUESTION=("what are the top 10 election violations in Indonesia? Please breakdown by provinces, "
          "candidates, parties, and any subjects. How can BAWASLU tackle them more effectively? "
          "What are the laws that should be reviewed?")

def test_benchmark_question_requires_deep_research():
    assert depth.depth_for(QUESTION)=="DEEP"
    names={name for name,_ in depth.objectives(QUESTION)}
    assert {"national statistics","provincial breakdown","candidate cases","party accountability",
            "subjects and institutions","legal instruments","prevention and implementation"} <= names
    assert len(depth.research_tasks(QUESTION))==4
    assert depth.output_budget(QUESTION)>=12000
    assert depth.depth_for("What is Gakkumdu?")=="QUICK"

def test_multi_objective_discovery_and_gap_resolution(monkeypatch):
    monkeypatch.setenv("BAWASLU_ASSISTANT_WEB_SEARCH","true")
    calls=[]
    def discover(q,obj,hint,key,model,base,recent):
        calls.append(obj)
        # A separate result for each research objective.
        slug=str(len(calls))
        return {"objective":obj,"status":"DISCOVERED","queries":[obj],
                "results":[{"url":"https://bawaslu.go.id/official-"+slug,"title":obj+(" (retry)" if calls.count(obj)>1 else "")}]}
    def read(url,snippet="",title="",question=""):
        fail="provincial breakdown" in title and "(retry)" not in title
        return {"url":url,"title":title,"read_status":"INACCESSIBLE" if fail else "READ",
                "excerpt":"" if fail else "Synthetic source excerpt", "published_at":"2024-11-24"}
    monkeypatch.setattr(research,"_discover",discover)
    monkeypatch.setattr(research,"read_page",read)
    result=research.public_research(QUESTION,"test","test-model","https://api.openai.com/v1")
    assert result["research_depth"]=="DEEP"
    assert len(calls)==8 and calls.count("provincial breakdown")==2
    assert result["status"]=="READ"
    assert len(result["sources"])<=research.DEEP_MAX_PAGES
    assert len({r["id"] for r in result["sources"]})==len(result["sources"])
    assert any(r["read_status"]=="INACCESSIBLE" for r in result["sources"])
    assert len(result["search_passes"])==8
    assert len(result["coverage"])==7
    assert all(row["status"]=="READABLE_LEADS" for row in result["coverage"])

def test_pdf_extraction_retains_page_labels():
    from reportlab.pdfgen import canvas
    stream=io.BytesIO()
    pdf=canvas.Canvas(stream)
    pdf.drawString(50,750,"Synthetic election violation statistics - not official data")
    pdf.showPage()
    pdf.drawString(50,750,"Province A 12 recorded reports")
    pdf.save()
    result=document_extract.extract_document(stream.getvalue(),"PDF",QUESTION)
    assert result["document_type"]=="PDF"
    assert "[PDF page 2]" in result["excerpt"]
    assert "Province A 12" in result["excerpt"]

def test_csv_and_xlsx_preserve_original_row_numbers():
    from openpyxl import Workbook
    csv=document_extract.extract_document(b"Province,Reports\nProvince A,12\nProvince B,8\n","CSV",QUESTION)
    assert "[CSV row 2]" in csv["excerpt"] and "Province A | 12" in csv["excerpt"]
    book=Workbook()
    book.active.title="Synthetic"
    book.active.append(["Province","Reports"])
    book.active.append(["Province A",12])
    buf=io.BytesIO()
    book.save(buf)
    xlsx=document_extract.extract_document(buf.getvalue(),"XLSX",QUESTION)
    assert "[Sheet Synthetic row 2]" in xlsx["excerpt"]
    assert "Province A | 12" in xlsx["excerpt"]

def test_deep_report_survives_without_old_truncation():
    src={"id":"P-1","kind":"OFFICIAL","url":"https://bawaslu.go.id/report.pdf",
         "read_status":"READ","excerpt":"Synthetic source for a test; no real claims."}
    body="## National statistics\n\n"+("Evidence and conditional strategy [P-1].\n\n"*350)+"## Legislative review\n\nFinal section survives."
    raw={"answer":body,"claims":[{"claim":"Synthetic row "+str(i),"source_ids":["P-1"],
        "status":"PRIMARY_SOURCE_REPORTED","caveat":"Test only"} for i in range(12)],
        "limitations":[],"relevance":"POSSIBLE"}
    report=quality.finalize(raw,[src],QUESTION,"RESEARCH","READ","WEB_ONLY",{})
    assert report["answer"]==body
    assert len(report["claims"])==12
    assert report["research_depth"]=="DEEP"
    assert "[P-1]" in report["answer"]
    assert report["quality"]["human_approval_required"]

def test_source_free_current_answer_not_invented():
    report=quality.finalize({"answer":"Unverified synthetic claim","limitations":[]},[],
                            QUESTION,"RESEARCH","SEARCH_FAILED","WEB_ONLY",{})
    assert "Unverified synthetic claim" not in report["answer"]
    assert report["claims"]==[]

def test_document_citation_and_answer_prompt_require_coverage():
    for fragment in ("Answer EVERY material part","answer-first","Sponsorship is not party liability","page/row","Markdown report"):
        assert fragment.casefold() in decisions.SYSTEM.casefold()
