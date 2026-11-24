"""v180.3: qualitative-comparison recovery across unrelated General Research topics.

Fixtures replay evidence patterns from the two user-supplied PDFs, but are
synthetic; they DO NOT reproduce inaccessible historical provider calls or
claim to measure factual completeness of a live model response.
"""
import json

import pytest

from app.ai5 import web, engine

PILOT="Situasi pelanggaran pemilu Indonesia dibandingkan negara tetangga"
OTHER=("Compare documented effects of coastal storms on schools, clinics "
       "and roads across neighboring regions and how officials responded.")


@pytest.mark.parametrize("question,number_title,peer_title,observation_title",[
    (PILOT,"Official election counts","Regional observer comparison",
     "Independent information operations study"),
    (OTHER,"Storm damage totals","Community monitoring reports",
     "Regional infrastructure response study"),
])
def test_comparison_followup_preserves_numbers_and_cross_subject_observations(
        monkeypatch,question,number_title,peer_title,observation_title):
    """Even when ordinary coverage looks complete, missing peer cases trigger search."""
    planned=[{"name":"Recorded results","query":question+" official counts"},
             {"name":"Comparative effects","query":question+" assessment"}]
    monkeypatch.setattr(web,"plan_dimensions",lambda *a:planned)
    requests=[]
    def discover(query,key,model,base,as_of,newest=False):
        requests.append(query)
        if "qualitative firsthand observations comparative case studies" in query:
            rows=[{"url":"https://example.org/observer","title":peer_title}]
        elif "other compared countries regions organizations observed incidents" in query:
            rows=[{"url":"https://example.org/response","title":observation_title}]
        else:
            rows=[{"url":"https://example.org/official","title":number_title}]
        return {"status":"FOUND","rows":rows,"queries":[query]}
    monkeypatch.setattr(web,"discover",discover)
    def read(row):
        if row["url"].endswith("official"):
            passage=("Recorded figures: 1,459 reports and 1,349 non-violations. "
                     "Numbers from the first subject cannot rank peers.")
        elif row["url"].endswith("observer"):
            passage=("Observers documented institutional use of public resources "
                     "in two neighboring settings and contrasted local case responses.")
        else:
            passage=("Independent comparative researchers described disinformation "
                     "campaigns, participant reactions, and administrative responses "
                     "across different settings.")
        return {"url":row["url"],"title":row["title"],"type":"PUBLIC_REPORT",
                "read_status":"READ","excerpt":passage,
                "published_at":"2024-06-01"}
    monkeypatch.setattr(web,"read_page",read)
    def audit(dimensions,pages,*args):
        if len(dimensions)==1 and dimensions[0]["name"].startswith("Qualitative"):
            names={p["title"] for p in pages}
            status=("COVERED" if {peer_title,observation_title}.issubset(names)
                    else "MISSING")
            return [{"name":dimensions[0]["name"],"status":status,
                     "reason":"Needs readable examples from more than one subject"}]
        return [{"name":d["name"],"status":"COVERED",
                 "reason":"Numerical evidence is available"} for d in dimensions]
    monkeypatch.setattr(web,"evaluate_coverage",audit)
    result=web.research(question,"key","model","https://example.org/v1",
                        "2026-11-24",recent=False)
    assert result["status"]=="READ_SOURCES_AVAILABLE"
    assert len(result["sources"])==3
    assert result["comparative_coverage"]["status"]=="COVERED"
    assert all(x["status"]=="COVERED" for x in result["coverage"])
    assert sum(x["phase"]=="gap follow-up" for x in result["attempts"])==2
    assert any("qualitative firsthand observations" in x for x in requests)
    assert any("other compared countries" in x for x in requests)
    assert all(x.get("selected") for a in result["attempts"] for x in a.get("leads",[]))
    cfg={"question":question,"evidence_intent":"OBSERVED_OUTCOMES",
         "comparative_coverage":result["comparative_coverage"]}
    packet=engine.model_sources(cfg,result["sources"])
    assert {x["title"] for x in packet if x["eligible"]}=={
        number_title,peer_title,observation_title}
    assert any("Recorded figures" in x["excerpt"] for x in packet)
    assert any("Observers documented" in x["excerpt"] for x in packet)
    assert any("disinformation campaigns" in x["excerpt"] for x in packet)
    # A polished statistics-only answer should not count as complete.
    numeric_id=next(x["id"] for x in result["sources"]
                    if x["title"]==number_title)
    only_numbers={"body":"The first subject has numerical results. [["+
                   numeric_id+"]]","draft":"",
                  "table":{"rows":[]}}
    assert engine.undiscussed_comparative_observations(
        cfg,only_numbers,result["sources"])
    complete={"body":only_numbers["body"]+" Qualitative observed practices "
              "across peers. [["+
              next(x["id"] for x in result["sources"] if x["title"]==peer_title)+"]]",
              "draft":"","table":{"rows":[]}}
    assert not engine.undiscussed_comparative_observations(
        cfg,complete,result["sources"])


def test_observation_passage_later_than_numeric_introduction_is_kept():
    prefix=("Official statistics document 9,345 recorded reports. "*92)
    observation=("Independent observers described disinformation and propaganda "
                 "operations involving neighboring institutions. They documented "
                 "how administrators responded and why patterns differed. ")*6
    text=prefix+observation+" Background narrative. "*85
    source={"id":"PUBLIC-QUAL-1","type":"PUBLIC_REPORT","title":"Field review",
            "read_status":"READ","excerpt":text,"search_dimensions":[
                "comparative observation follow-up 1"]}
    cfg={"question":PILOT,"evidence_intent":"OBSERVED_OUTCOMES"}
    passage=engine.relevant_passage(source,PILOT)
    assert "observers described disinformation" in passage
    assert passage!=text[:2800]
    assert "Recorded" in passage
    assert len(passage)<=2800


def test_institutional_only_questions_do_not_expand_into_outcome_lanes():
    q="How does a public hospital licensing framework work?"
    assert web.qualitative_comparison_requirement(q) is None
    q2="Compare how two licensing institutions are structured and governed"
    assert web.qualitative_comparison_requirement(q2) is None
    assert web.qualitative_comparison_requirement(PILOT) is not None
    assert web.qualitative_comparison_requirement(OTHER) is not None


def test_review_scope_receives_qualitative_evidence_and_flags_omission(monkeypatch):
    recorded={}
    class FakeResponse:
        status_code=200
        def json(self):
            return {"output":[{"type":"message","content":[{
                "type":"output_text","text":json.dumps({
                   "items":[{"request":"Compare observation patterns",
                             "status":"OMITTED",
                             "reason":"Peer observations were present but unused"}],
                   "missing_requests":["Compare observation patterns"]})}]}]}
    class FakeClient:
        def __init__(self,*args,**kwargs):pass
        def __enter__(self):return self
        def __exit__(self,*args):return False
        def post(self,*args,**kwargs):
            recorded["payload"]=kwargs["json"]
            return FakeResponse()
    monkeypatch.setattr(engine.httpx,"Client",FakeClient)
    cfg={"question":PILOT,"research_dimensions":[],
         "research_coverage":[],
         "comparative_coverage":{"status":"COVERED"},
         "comparative_evidence_summaries":[{
             "title":"Regional observer comparison","date":"2024-06-01",
             "dimensions":["comparative observations"],
             "excerpt":"Observers documented differences in state resource use"}]}
    audit=engine.review_scope(cfg,{"body":"No comparable figures.",
                                  "draft":"","table":{"rows":[]}},
                              "key","model","https://example.org")
    assert audit["status"]=="GAPS_FOUND"
    assert "Compare observation patterns" in audit["missing_requests"]
    payload=json.loads(recorded["payload"]["input"][1]["content"])
    assert payload["comparative_coverage"]["status"]=="COVERED"
    assert "Observers documented differences" in str(
        payload["public_comparative_evidence"])


def test_general_research_prompt_requires_qualitative_comparison():
    assert "Missing common metrics" in engine.SYSTEM
    assert "documented qualitative patterns" in engine.SYSTEM
    assert "statistical limitation once" in engine.SYSTEM
    assert "GENERAL_RESEARCH" in engine.SYSTEM


def test_ai5_general_research_revises_stats_only_answer_and_exports_pdf(monkeypatch):
    """End-to-end AI-5 route using the original pilot wording and WEB_ONLY."""
    import io
    import uuid
    from pypdf import PdfReader
    from app.ai5 import api,state,export
    from app.ai4 import attachments
    attachments.STORES.clear()
    grant={"role":"National Leadership","status":"Active",
           "geographic_scope":"Nationwide",
           "permissions":{"view_intelligence":True}}
    user=type("User",(),{"id":1803})()
    monkeypatch.setattr(api,"profile",lambda *_:grant)
    monkeypatch.setattr(api,"has",lambda *_:True)
    monkeypatch.setenv("OPENAI_API_KEY","offline-key")
    sources=[
        {"id":"WEB-NUM-1","title":"Illustrative official reporting counts",
         "url":"https://example.org/numeric","read_status":"READ",
         "type":"PUBLIC_REPORT","published_at":"2024-01-05",
         "basis":"LIVE_PUBLIC_LOOKUP","duplicate_of":"",
         "excerpt":"Official 2019 and 2024 reporting totals; counts are not comparable.",
         "search_dimensions":["recorded results"]},
        {"id":"WEB-OBS-2","title":"Illustrative regional observer analysis",
         "url":"https://example.org/observer","read_status":"READ",
         "type":"PUBLIC_REPORT","published_at":"2019-05-20",
         "basis":"LIVE_PUBLIC_LOOKUP","duplicate_of":"",
         "excerpt":"Historical observer report: Indonesia and the Philippines have documented concerns about abuse of state resources.",
         "search_dimensions":["comparative observations"]},
        {"id":"WEB-OBS-3","title":"Illustrative regional information analysis",
         "url":"https://example.org/disinformation","read_status":"READ",
         "type":"PUBLIC_REPORT","published_at":"2020-07-09",
         "basis":"LIVE_PUBLIC_LOOKUP","duplicate_of":"",
         "excerpt":"Regional historical study: Indonesia, Philippines and Thailand observed disinformation campaigns and institutional responses.",
         "search_dimensions":["comparative observation follow-up 1"]}
    ]
    research={"status":"READ_SOURCES_AVAILABLE","sources":sources,
              "attempts":[],"as_of":"2026-11-24",
              "dimensions":[{"name":"Reported counts","query":PILOT+" figures"},
                            {"name":"Neighbor experiences","query":PILOT+" observer"}],
              "coverage":[{"name":"Reported counts","status":"COVERED"},
                          {"name":"Neighbor experiences","status":"COVERED"}],
              "comparative_coverage":{"name":"Qualitative cross-subject observations and responses",
                     "status":"COVERED","reason":"Two readable comparative studies"},
              "evidence_intent":"OBSERVED_OUTCOMES",
              "budget":{"initial":8,"max_pages":15,"read_pages":3}}
    monkeypatch.setattr(api.web,"research",lambda *args:research.copy())
    model_calls=[]
    def synthesis(cfg,history,received,*args):
        model_calls.append(list(received))
        if len(model_calls)==1:
            body=("## Reported counts\nCounts from one country are documented "
                  "[[WEB-NUM-1]]. No comparable numbers exist elsewhere.")
        else:
            body=("## Main findings\nRecorded counts are documented "
                  "[[WEB-NUM-1]], but cannot rank neighbors. "
                  "Observer studies involving Indonesia and the Philippines describe patterns of institutional "
                  "resource use [[WEB-OBS-2]], while Indonesia, Philippines and Thailand show information campaigns with "
                  "administrative responses [[WEB-OBS-3]].\n\n"
                  "## What the comparison reveals\nBoth quantitative reporting "
                  "and qualitative observations are needed, and reporting "
                  "definitions differ.")
        return {"title":"Regional evidence comparison","body":body,
                "draft":"","table":{"title":"","columns":[],"rows":[]},
                "open_questions":[],"source_ids":[r["id"] for r in received]},"COMPLETE"
    monkeypatch.setattr(api.engine,"generate",synthesis)
    monkeypatch.setattr(api.engine,"review_scope",lambda *args:{
        "status":"COVERED","items":[],"missing_requests":[]})
    conv=str(uuid.uuid4())
    reply=api.chat({"question":PILOT,"mode":"GENERAL_RESEARCH",
                    "sourceMode":"WEB_ONLY","conversationId":conv},
                   user,object())
    assert len(model_calls)==2, "A numerical-only first answer needs a rewrite"
    assert reply["mode"]=="GENERAL_RESEARCH"
    assert reply["source_mode"]=="WEB_ONLY"
    assert reply["research_trail"]["comparative_coverage"]["status"]=="COVERED"
    body=reply["answer"]["body"]
    assert all(x in body for x in ("resource use","information campaigns","Philippines","Thailand"))
    assert "[[WEB-OBS-2]]" in body and "[[WEB-OBS-3]]" in body
    record=state.get_turn(user,reply["conversation_id"],grant,reply["turn_id"])
    assert record["research_trace"]["comparative_coverage"]["status"]=="COVERED"
    pdf=export.create_pdf(record)
    text="\n".join(page.extract_text() or "" for page in
                   PdfReader(io.BytesIO(pdf)).pages)
    assert "Reported counts" in text
    assert "information campaigns" in text
    assert "resource use" in text and "Philippines" in text and "Thailand" in text
    assert "Illustrative regional observer analysis" in text
