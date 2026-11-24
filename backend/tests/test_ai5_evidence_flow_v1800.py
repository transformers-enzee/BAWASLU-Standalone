"""v180.0 General Research: observed evidence, source selection and optional PDF trail.

Only synthetic passages and mocked discovery are used. These tests are NOT
claims about actual election violations or live cross-country outcomes.
"""
import io
from pypdf import PdfReader
from app.ai5 import engine,web,export

PILOT="Situasi pelanggaran pemilu Indonesia dibandingkan negara tetangga"
OTHER=("What happened to schools, clinics and roads after major coastal storms "
       "between 2021 and 2025, and how were services restored?")


def _source(id,title,excerpt,url="https://example.org/study",date="2024-04-10"):
    return {"id":id,"title":title,"excerpt":excerpt,"url":url,
            "published_at":date,"type":"PUBLIC_REPORT","read_status":"READ",
            "basis":"LIVE_PUBLIC_LOOKUP","duplicate_of":"",
            "search_dimensions":["Observed outcomes"]}


def _turn():
    sources=[_source("WEB-TST-1","Regional impact report",
             "A case documented in a hypothetical region.",
             "https://example.org/impacts")]
    answer={"title":"Observed outcomes across regions",
        "body":("## What was documented\n"
                "A synthetic study counted 1,134 reports in 2024. [[WEB-TST-1]]\n\n"
                "## What the comparison means\n"
                "A reported case is not a proven violation. [[WEB-TST-1]]"),
        "draft":"","table":{"title":"Illustrative comparison",
            "columns":["Region","Observed event","Interpretation"],
            "rows":[["Region A","1,134 reported incidents [[WEB-TST-1]]",
                     "Reports are not convictions"],["Region B",
                     "Observed services disruption", "Different denominator"]]},
        "open_questions":["Current verified convictions not established"]}
    trail={"evidence_intent":"OBSERVED_OUTCOMES",
           "budget":{"read_pages":7,"max_pages":18},
           "coverage":[{"name":"Observed outcomes","status":"PARTIAL",
                        "reason":"Some periods remain incomparable"}],
           "attempts":[{"phase":"initial","dimension":"Observed outcomes",
                        "query":"hypothetical storm impacts 2024",
                        "status":"FOUND","discovered":2,
                        "leads":[{"url":"https://example.org/impacts",
                                  "title":"Regional impact report",
                                  "selected":True,"read_status":"READ"},
                                 {"url":"https://example.org/unread",
                                  "title":"Unopened lead","selected":False,
                                  "reason":"bounded page selection"}]}],
           "model_source_ids":["WEB-TST-1"],
           "model_passages":[{"id":"WEB-TST-1",
                             "title":"Regional impact report",
                             "publication_date":"2024-04-10",
                             "sent_characters":220,
                             "excerpt_preview":"A hypothetical impact was observed."}]}
    return {"answer":answer,"sources":sources,"research_trace":trail,
            "turn_id":"5"*32,"question":OTHER}


def _pdf_text(data):
    reader=PdfReader(io.BytesIO(data))
    return reader, "\n".join(page.extract_text() or "" for page in reader.pages)


def test_question_intent_and_scaled_budget_across_topics():
    assert web.BROAD.search(PILOT)
    assert web.evidence_intent(PILOT)=="OBSERVED_OUTCOMES"
    assert web.evidence_intent(OTHER)=="OBSERVED_OUTCOMES"
    assert web.evidence_intent("How does a municipal health licensing system work?")=="INSTITUTIONAL_DESIGN"
    assert web.evidence_intent("Explain how licensing works and what happened in 2024")=="MIXED"
    narrow=web.search_budget([{"name":"one"}])
    broad=web.search_budget([{"name":str(i)} for i in range(8)])
    assert narrow[0]<broad[0]
    assert narrow[1]<broad[1]<=web.MAX_PAGES
    assert web.needs_recent(PILOT)


def test_actual_passage_packet_selects_documented_outcome_beyond_introduction():
    # A long report has a legal introduction; the actual measured finding is later.
    text=("A hypothetical constitution grants oversight powers. "*94+
          "ELECTION VIOLATIONS Indonesia Philippines: 1,134 recorded reports "
          "for 2024 national election, a report count and NOT proven offences. "+
          "Generic historical background. "*100)
    r=_source("WEB-LATE-1","Annual monitoring",text)
    r["search_dimensions"]=["Indonesia Philippines documented violations"]
    cfg={"question":PILOT,"evidence_intent":"OBSERVED_OUTCOMES"}
    packet=engine.model_sources(cfg,[r])
    assert len(packet)==1 and packet[0]["eligible"]
    assert "1,134 recorded reports" in packet[0]["excerpt"]
    assert packet[0]["excerpt"]!=text[:2800]
    trace=engine.model_trace(cfg,[r])
    assert trace["source_ids"]==["WEB-LATE-1"]
    assert trace["passages"][0]["sent_characters"]<=2800


def test_retrieved_page_selection_and_targeted_outcome_followup(monkeypatch):
    dimensions=[{"name":"Recorded incidents",
                 "query":"Indonesia Philippines election recorded incidents"},
                {"name":"Investigation outcomes",
                 "query":"Indonesia Philippines election investigation outcomes"}]
    monkeypatch.setattr(web,"plan_dimensions",lambda *args:dimensions)
    calls=[]
    def discover(query,*args):
        calls.append(query)
        if "independent primary evidence" in query:
            rows=[{"url":"https://example.org/cases",
                   "title":"Investigation results and sanctions"}]
        else:
            rows=[{"url":"https://example.org/law",
                   "title":"Constitution and election administration"}]
        return {"rows":rows,"status":"FOUND","queries":[query]}
    monkeypatch.setattr(web,"discover",discover)
    def reader(item):
        if item["url"].endswith("/cases"):
            excerpt="Investigation outcomes: 127 cases closed and 28 sanctions in 2024."
        else:excerpt="Institutional design establishes a national election commission."
        return {"url":item["url"],"title":item["title"],
                "read_status":"READ","excerpt":excerpt,
                "published_at":"2024-01-01","type":"PUBLIC_REPORT"}
    monkeypatch.setattr(web,"read_page",reader)
    def audit(dims,pages,*args):
        full=" ".join(p.get("excerpt","") for p in pages)
        return [{"name":d["name"],
                 "status":"COVERED" if d["name"] in full else "MISSING",
                 "reason":"Synthetic fixture"} for d in dims]
    monkeypatch.setattr(web,"evaluate_coverage",audit)
    output=web.research(PILOT,"key","model","https://example.org/api",
                        "2026-11-24",recent=True)
    assert output["evidence_intent"]=="OBSERVED_OUTCOMES"
    assert len(output["coverage"])==2
    assert output["coverage"][1]["status"]=="COVERED"
    assert any("independent primary evidence documented incident" in x for x in calls)
    assert any(x["phase"]=="gap follow-up" for x in output["attempts"])
    assert all(x["leads"] and "selected" in x["leads"][0]
               for x in output["attempts"])
    assert len(output["sources"])==2
    assert output["budget"]["read_pages"]==2


def test_concrete_figures_buried_in_caveats_trigger_answer_revision():
    reply={"body":"A generalized comparison has insufficient numbers.",
           "draft":"","table":{"rows":[]},
           "open_questions":[
              "In 2024, a monitoring report recorded 1.134 findings and "
              "3.411 complaints [[WEB-TEST-1]], but this was not in the main body."]}
    reasons=engine.main_answer_evidence_gaps(reply)
    assert reasons and "main answer" in reasons[0]
    reply["body"]+=" 1.134 findings and 3.411 complaints were reported in 2024."
    assert not engine.main_answer_evidence_gaps(reply)


def test_pdf_main_only_has_no_audit_spillover_and_citations_are_clickable():
    turn=_turn()
    main=export.create_pdf(turn)
    reader,text=_pdf_text(main)
    assert len(reader.pages)>=1
    assert "What was documented" in text and "What the comparison means" in text
    assert "Illustrative comparison" in text
    assert "1,134 reported incidents" in text
    assert "Regional impact report (2024-04-10)" in text
    assert "Research Trail" not in text
    assert "hypothetical storm impacts 2024" not in text
    assert len((reader.pages[-1].extract_text() or "").split())>20
    links=set()
    for page in reader.pages:
        for entry in page.get("/Annots",[]) or []:
            obj=entry.get_object()
            if obj.get("/A") and obj["/A"].get("/URI"):
                links.add(str(obj["/A"]["/URI"]))
    assert "https://example.org/impacts" in links


def test_pdf_detailed_audit_is_optional_and_page_break_is_explicit():
    turn=_turn()
    main=export.create_pdf(turn)
    included=export.create_pdf(turn,include_research_trail=True)
    rmain,tmain=_pdf_text(main)
    rappend,tappend=_pdf_text(included)
    assert len(rappend.pages)>len(rmain.pages)
    assert "Appendix" in tappend and "Research Trail" in tappend
    assert "Search queries and page selection" in tappend
    assert "hypothetical storm impacts 2024" in tappend
    assert "A hypothetical impact was observed" in tappend
    assert "What the comparison means" in tmain and "What the comparison means" in tappend
    assert "Regional impact report (2024-04-10)" in tmain
    assert len((rappend.pages[-1].extract_text() or "").split())>=30
    # A false value in the API must not be silently accepted as a string toggle.
    try:
        export.create(turn,"pdf",include_research_trail="yes")
    except ValueError:
        pass
    else:
        assert False,"invalid Research Trail flag was accepted"


def test_coverage_auditor_sees_documented_events_after_legal_preamble(monkeypatch):
    actual=("The constitution establishes election administration. "*75+
            "Indonesia Philippines comparison of election cases: "
            "3.411 complaints in 2024, with a documented handling procedure. "+
            "Institutional material. "*80)
    dims=[{"name":"Recorded election complaints",
           "query":"Indonesia Philippines election complaints 2024"}]
    chosen=web.coverage_excerpt({"excerpt":actual},dims)
    assert "3.411 complaints in 2024" in chosen
    assert chosen!=actual[:1500]
    captured={}
    def mock_json(*args,**kwargs):
        captured["payload"]=args[4]
        captured["prompt"]=args[3]
        return {"reviews":[{"index":0,"status":"PARTIAL",
                             "reason":"Some documented complaints, no judgments"}]}
    monkeypatch.setattr(web,"_provider_json",mock_json)
    rows=[{"title":"Legal and case overview","read_status":"READ",
           "excerpt":actual,"search_dimensions":["Recorded election complaints"]}]
    checked=web.evaluate_coverage(dims,rows,"key","model","base")
    assert checked[0]["status"]=="PARTIAL"
    assert "3.411 complaints" in captured["payload"]["read_pages"][0]["excerpt"]
    assert "outcomes" in captured["prompt"].lower()
