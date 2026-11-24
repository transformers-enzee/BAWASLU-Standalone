"""v179.7 AI-5: real-question research coverage and PDF parity (offline fixtures).

These deliberately replay the wording of an actual pilot question. Provider
responses and source passages are synthetic, never evidence of real-world claims.
No OpenAI credits, Supabase writes, or live public websites are required.
"""
import io
import uuid
from pypdf import PdfReader
from app.ai5 import api,engine,export,state,web
from app.ai4 import attachments as attachments

GRANT={"role":"National Leadership","status":"Active","geographic_scope":"Nationwide",
       "permissions":{"view_intelligence":True}}
QUESTION=("what is the situation of election commission in Indonesia "
          "comparing with its neighboring countries")
OTHER=("Compare flood resilience, hospital access and housing affordability "
       "in three coastal metropolitan regions, and explain the trade-offs.")


def _user():
    return type("User",(),{"id":882})()


def _source(name,detail,uri,id="WEB-FIX-1"):
    return {"id":id,"title":name,"excerpt":detail,"read_status":"READ",
            "published_at":"2022-04-08","type":"PUBLIC_REPORT",
            "url":uri,"basis":"LIVE_PUBLIC_LOOKUP","duplicate_of":""}


def _access(monkeypatch):
    attachments.STORES.clear()
    monkeypatch.setattr(api,"profile",lambda *_:GRANT)
    monkeypatch.setattr(api,"has",lambda *_:True)
    monkeypatch.setenv("OPENAI_API_KEY","offline-fixture-key")


def _read_pdf(answer,sources,question,trace=None):
    t={"answer":answer,"sources":sources,"question":question,
       "research_trace":trace or {}, "turn_id":"2"*32}
    pdf=export.create_pdf(t)
    assert pdf[:5]==b"%PDF-"
    reader=PdfReader(io.BytesIO(pdf))
    text="\n".join(p.extract_text() or "" for p in reader.pages)
    urls=set()
    for page in reader.pages:
        for obj in page.get("/Annots",[]) or []:
            annot=obj.get_object()
            action=annot.get("/A")
            if action and action.get("/URI"):
                urls.add(str(action["/URI"]))
    return text,urls,pdf


def test_actual_indonesia_question_searches_missing_aspects_before_final_answer(monkeypatch):
    _access(monkeypatch)
    dims=[{"name":"Institutional design","query":"Indonesia neighbors election bodies design"},
          {"name":"Independence and appointments","query":"regional election commissions appointment"},
          {"name":"Present-day performance","query":"regional electoral performance"},
          {"name":"Practical comparative lessons","query":"regional election governance lessons"}]
    monkeypatch.setattr(web,"plan_dimensions",lambda *_:dims)
    calls=[]
    def search(query,*args):
        calls.append(query)
        if "independent primary evidence" in query:
            rows=[{"url":"https://example.org/study","title":"Historical design study",
                    "excerpt":""},
                  {"url":"https://example.org/assessment","title":"Performance monitoring",
                    "excerpt":""}]
        else:
            rows=[{"url":"https://example.org/constitution","title":"Constitutional outline",
                    "excerpt":""}]
        return {"status":"FOUND","rows":rows,"queries":[query]}
    monkeypatch.setattr(web,"discover",search)
    def reader(row):
        record={"Constitutional outline":("Institutional design: constitutional "
                        "commission structures can differ."),
                "Historical design study":("Independence and appointments: "
                        "historical appointments study, not current performance."),
                "Performance monitoring":("Present-day performance and Practical "
                        "comparative lessons require separate observed measures.")}[row["title"]]
        return {"url":row["url"],"title":row["title"],"excerpt":record,
                "read_status":"READ","published_at":"2022-04-08",
                "type":"PUBLIC_REPORT","duplicate_of":""}
    monkeypatch.setattr(web,"read_page",reader)
    def audit(dims,pages,*args):
        content=" ".join(r.get("excerpt") or "" for r in pages if
                         r.get("read_status")=="READ").lower()
        return [{"name":d["name"],
                 "status":"COVERED" if d["name"].lower() in content else "MISSING",
                 "reason":"fixture readable evidence" if d["name"].lower() in content
                          else "no readable evidence"} for d in dims]
    monkeypatch.setattr(web,"evaluate_coverage",audit)
    seen={}
    def model(cfg,hist,sources,*args):
        seen["source_titles"]=[x["title"] for x in sources if x.get("read_status")=="READ"]
        seen["coverage"]=cfg.get("research_coverage")
        ids=[x["id"] for x in sources if x.get("read_status")=="READ"]
        return {"title":"Regional electoral institutions",
          "body":("## Institutional design\nIndonesia has several electoral "
                  "institutions in this synthetic comparison. [["+ids[0]+"]]\n\n"
                  "## Independence and appointments\nThe historical study "
                  "documents historical design, not modern effectiveness. [["+
                  ids[-2]+"]]\n\n## Present-day performance\nPresent-day "
                  "performance requires observed comparable indicators. [["+
                  ids[-1]+"]]\n\n## Practical comparative lessons\n"
                  "Separating roles can improve checks but complicate coordination."),
          "table":{"title":"","columns":[],"rows":[]},"draft":"",
          "open_questions":["Which outcomes are currently measured comparably?"],
          "source_ids":ids},"COMPLETE"
    monkeypatch.setattr(api.engine,"generate",model)
    monkeypatch.setattr(api.engine,"review_scope",lambda *args:{
        "status":"COVERED","items":[],"missing_requests":[]})
    result=api.chat({"conversationId":str(uuid.uuid4()),"question":QUESTION,
                     "mode":"GENERAL_RESEARCH","sourceMode":"WEB_ONLY"},
                     _user(),object())
    assert result["synthesis_status"]=="COMPLETE"
    assert any(a["phase"]=="gap follow-up" for a in result["research_trail"]["attempts"])
    assert all(x["status"]=="COVERED" for x in seen["coverage"])
    assert "Performance monitoring" in seen["source_titles"]
    body=result["answer"]["body"]
    assert all(term in body for term in ("Institutional design","Independence",
                       "Present-day performance","Practical comparative lessons"))
    saved=state.get_turn(_user(),result["conversation_id"],GRANT,result["turn_id"])
    text,urls,_=_read_pdf(saved["answer"],saved["sources"],QUESTION,
                          saved["research_trace"])
    assert all(x in text for x in ("Institutional design","Independence",
                                    "Present-day performance","Practical comparative lessons"))
    assert "Constitutional outline (2022-04-08)" in text
    assert "https://example.org/constitution" in urls
    assert "[WEB-" not in text
    assert "Research Trail" in text


def test_unrelated_question_has_answer_audit_gap_rescue_full_pdf_parity(monkeypatch):
    _access(monkeypatch)
    first=_source("Flood infrastructure historical review",
                  "Historic flood infrastructure design.",
                  "https://example.org/flood")
    later=_source("Urban hospital accessibility study",
                  "Hospital access varies by population.",
                  "https://example.org/hospitals",id="WEB-FIX-2")
    research={"status":"READ_SOURCES_AVAILABLE","sources":[first],
              "as_of":"2026-11-24","attempts":[],"dimensions":[
                  {"name":"Flood resilience","query":"coastal flood resilience"},
                  {"name":"Hospital access","query":"coastal hospital access"},
                  {"name":"Housing affordability","query":"coastal housing affordability"}],
              "coverage":[{"name":"Flood resilience","status":"COVERED"},
                          {"name":"Hospital access","status":"MISSING"},
                          {"name":"Housing affordability","status":"MISSING"}]}
    monkeypatch.setattr(api.web,"research",lambda *args:research.copy())
    gaps=[]
    def recovery(q,missing,*args):
        gaps.extend(missing)
        return {"sources":[later],"attempts":[{"phase":"answer gap follow-up",
          "status":"FOUND","query":"coastal hospital access","discovered":1}]}
    monkeypatch.setattr(api.web,"fill_answer_gaps",recovery)
    model_runs=[]
    def model(cfg,history,sources,*args):
        model_runs.append([x["id"] for x in sources])
        if len(model_runs)==1:
            body="## Flood resilience\nThe historical flood review covers only infrastructure. [[WEB-FIX-1]]"
        else:
            body=("## Flood resilience\nHistoric infrastructure does not show current outcomes. [[WEB-FIX-1]]\n\n"
                  "## Hospital access\nThe study discusses hospital accessibility. [[WEB-FIX-2]]\n\n"
                  "## Housing affordability\nNo comparable housing data were retrieved; a ranking "
                  "would be unsupported.\n\n## Trade-offs\nA response should contrast access and cost.")
        return {"title":"Coastal city comparisons","body":body,"draft":"",
                "table":{"title":"","columns":[],"rows":[]},
                "open_questions":["Housing affordability remains unquantified"],
                "source_ids":["WEB-FIX-1","WEB-FIX-2"]},"COMPLETE"
    monkeypatch.setattr(api.engine,"generate",model)
    audit_calls=[]
    def check(*args):
        audit_calls.append(1)
        if len(audit_calls)==1:
            return {"status":"GAPS_FOUND","items":[],"missing_requests":[
                "Hospital access","Housing affordability","Trade-offs"]}
        return {"status":"COVERED","items":[],"missing_requests":[]}
    monkeypatch.setattr(api.engine,"review_scope",check)
    result=api.chat({"conversationId":str(uuid.uuid4()),"question":OTHER,
                     "sourceMode":"WEB_ONLY"},_user(),object())
    assert len(model_runs)==2 and len(audit_calls)==2
    assert "Hospital access" in gaps and "Housing affordability" in gaps
    assert result["research_trail"]["answer_audit"]["status"]=="COVERED"
    assert "WEB-FIX-2" in result["research_trail"]["model_source_ids"]
    saved=state.get_turn(_user(),result["conversation_id"],GRANT,result["turn_id"])
    text,urls,_=_read_pdf(saved["answer"],saved["sources"],OTHER,
                          saved["research_trace"])
    for label in ("Flood resilience","Hospital access","Housing affordability","Trade-offs"):
        assert label in result["answer"]["body"] and label in text
    assert "Urban hospital accessibility study (2022-04-08)" in text
    assert "https://example.org/hospitals" in urls


def test_pdf_retains_structured_comparison_and_clickable_sources():
    first=_source("Official Election Commission", "Historical record.",
                  "https://example.org/commission")
    answer={"title":"Comparative report",
            "body":"# Overview\n**Institutional design** and current performance differ. [[WEB-FIX-1]]\n"
                   "## Implications\nHistorical design does not prove recent success.",
            "draft":"","table":{"title":"Country comparison",
                  "columns":["Country","Structure","Limits"],
                  "rows":[["A","Commission [[WEB-FIX-1]]","Historical data"],
                          ["B","Separate bodies","Current performance unknown"]]},
            "open_questions":[]}
    text,urls,data=_read_pdf(answer,[first],"Compare institutions")
    for fragment in ("Overview","Implications","Country comparison",
                     "Historical data","Current performance unknown",
                     "Official Election Commission (2022-04-08)"):
        assert fragment in text
    assert "https://example.org/commission" in urls
    assert "[WEB-FIX-1]" not in text
    assert len(data)>1000


def test_generation_contract_distinguishes_history_and_current_outcomes():
    assert "historical studies are historical evidence" in engine.SYSTEM
    assert "institutional design" in engine.SYSTEM.lower()
    assert "readable evidence" in engine.SYSTEM
    assert callable(engine.review_scope)
    assert callable(web.fill_answer_gaps)


def test_word_and_excel_keep_readable_linked_source_names():
    from zipfile import ZipFile
    from openpyxl import load_workbook
    source=_source("Official election reference","Historical source.",
                   "https://example.org/electoral-law")
    answer={"title":"Citation QA","body":"## Review\nA supported observation [[WEB-FIX-1]].",
            "draft":"","table":{"title":"Options","columns":["Country","Finding"],
                                "rows":[["A","Observation [[WEB-FIX-1]]"]]},
            "open_questions":[]}
    turn={"answer":answer,"sources":[source],"turn_id":"3"*32,
          "question":"Compare a historical and a current system"}
    word=export.create_docx(turn)
    with ZipFile(io.BytesIO(word)) as archive:
        xml=archive.read("word/document.xml").decode("utf-8")
        rels=archive.read("word/_rels/document.xml.rels").decode("utf-8")
    assert "Official election reference (2022-04-08)" in xml
    assert "w:hyperlink" in xml
    assert "https://example.org/electoral-law" in rels
    assert "WEB-FIX-1" not in xml
    workbook=load_workbook(io.BytesIO(export.create_xlsx(turn)))
    assert "Official election reference (2022-04-08)" in str(
        workbook["Analysis"].cell(2,2).value)
    assert workbook["Sources"].cell(2,2).hyperlink.target==(
        "https://example.org/electoral-law")


def test_long_comparison_begins_on_first_pdf_page():
    source=_source("Institutional review","Historical reading.",
                   "https://example.org/overview")
    paragraph=("Institutional arrangements establish the election body's "
               "powers and appointment process. Historical comparisons should "
               "not be mistaken for evidence of current performance.")
    answer={"title":"Comparative election study",
            "body":"Institutional analysis, evidence periods and current gaps.",
            "draft":"","table":{"title":"Country comparison",
                    "columns":["Country","Institution","Strength","Evidence limit"],
                    "rows":[[name,paragraph,paragraph,paragraph] for name in
                            ("Indonesia","Philippines","Malaysia","Thailand",
                             "Timor-Leste","Singapore","Papua New Guinea")]},
            "open_questions":[]}
    turn={"answer":answer,"sources":[source],"turn_id":"4"*32}
    reader=PdfReader(io.BytesIO(export.create_pdf(turn)))
    first=reader.pages[0].extract_text() or ""
    assert "Country comparison" in first
    assert "Indonesia" in first, "Table must begin below its heading, not on a mostly blank second page"
