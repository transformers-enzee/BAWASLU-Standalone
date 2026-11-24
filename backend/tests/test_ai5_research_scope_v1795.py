"""AI-5 v179.6: deterministic whole-scope research integration tests.

No provider credits, external HTTP requests, or BAWASLU records are used.
The original user attachment was not available to this test runner. These
fixtures reproduce the cross-dimension failure and a different broad topic.
"""
import uuid

from app.ai5 import api, engine, state, web
from app.ai4 import attachments as storage

GRANT={"role":"National Leadership","status":"Active","geographic_scope":"Nationwide",
       "permissions":{"view_intelligence":True}}


def _run(monkeypatch,question,dimensions,initial_evidence,follow_evidence):
    storage.STORES.clear()
    observed={"queries":[],"model_sources":[],"model_coverage":[],"contexts":[]}
    monkeypatch.setattr(api,"profile",lambda *_:GRANT)
    monkeypatch.setattr(api,"has",lambda *_:True)
    monkeypatch.setattr(api.os,"getenv",lambda key,default="":
        "test-only-key" if key=="OPENAI_API_KEY" else default)
    monkeypatch.setattr(web,"plan_dimensions",lambda *_:dimensions)
    def discovery(q,*args):
        observed["queries"].append(q)
        if "independent primary evidence" in q:
            rows=[{"url":"https://example.org/follow-"+str(i),
                   "title":r["title"],"snippet":""}
                  for i,r in enumerate(follow_evidence)]
        else:
            label=next((d["name"] for d in dimensions if d["query"]==q),"full question")
            rows=[{"url":"https://example.org/"+label.replace(" ","-").lower()+"-"+str(i),
                   "title":r["title"],"snippet":""}
                  for i,r in enumerate(initial_evidence.get(label,[]))]
        return {"status":"FOUND","rows":rows,"queries":[q]}
    monkeypatch.setattr(web,"discover",discovery)
    def read(row):
        content=next((r["excerpt"] for rows in
            [*initial_evidence.values(),follow_evidence] for r in rows
            if r["title"]==row["title"]),"")
        return {"url":row["url"],"title":row["title"],"type":"PUBLIC_REPORT",
                "read_status":"READ" if content else "SNIPPET_ONLY",
                "excerpt":content,"published_at":"2026-01-10","updated_at":""}
    monkeypatch.setattr(web,"read_page",read)
    def audit(dims,pages,*args):
        covered_text=" ".join(r.get("excerpt","") for r in pages
                              if r["read_status"]=="READ").lower()
        result=[]
        for d in dims:
            token=d["name"].lower()
            result.append({"name":d["name"],
                 "status":"COVERED" if token in covered_text else "MISSING",
                 "reason":"Readable text" if token in covered_text else "No relevant readable text"})
        return result
    monkeypatch.setattr(web,"evaluate_coverage",audit)
    def model(cfg,hist,sources,*args):
        observed["model_sources"]=[r["title"] for r in sources]
        observed["model_coverage"]=cfg["research_coverage"]
        observed["contexts"].append(cfg["question"])
        source_ids=[r["id"] for r in sources if r.get("read_status")=="READ"]
        details=", ".join(d["name"] for d in cfg["research_dimensions"])
        missing=[r["name"] for r in cfg["research_coverage"] if r["status"]!="COVERED"]
        text=("Findings across "+details+". "+("Evidence missing for "+", ".join(missing)
             if missing else "All dimensions considered")+". "+
             "Qualitative differences matter when measures are incompatible. "+
             " ".join("[["+s+"]]" for s in source_ids))
        return {"title":"Research comparison","body":text,"draft":"",
                "table":{"title":"","columns":[],"rows":[]},"open_questions":missing,
                "source_ids":source_ids},"COMPLETE"
    monkeypatch.setattr(api.engine,"generate",model)
    uid=type("User",(),{"id":977})()
    output=api.chat({"question":question,"mode":"GENERAL_RESEARCH",
                "sourceMode":"WEB_ONLY","conversationId":str(uuid.uuid4())},
                uid,object())
    return output,observed


def test_comparative_question_has_gap_followup_model_sources_and_citations(monkeypatch):
    question="Compare solar and wind power on costs, reliability and environmental effects."
    dims=[{"name":"Costs","query":"solar wind costs comparison"},
          {"name":"Reliability","query":"solar wind reliability comparison"},
          {"name":"Environmental effects","query":"solar wind environmental effects"}]
    first={"Costs":[{"title":"Cost Study","excerpt":"Costs differ by region."}],
           "Reliability":[{"title":"Reliability Report",
                           "excerpt":"Reliability depends on storage and geography."}],
           "Environmental effects":[]}
    extra=[{"title":"Environmental Review",
            "excerpt":"Environmental effects include land use and habitat effects."}]
    result,obs=_run(monkeypatch,question,dims,first,extra)
    trail=result["research_trail"]
    assert result["synthesis_status"]=="COMPLETE"
    assert len(trail["coverage"])==3
    assert all(r["status"]=="COVERED" for r in trail["coverage"])
    assert any(a["phase"]=="gap follow-up" and
               a["dimension"]=="Environmental effects" for a in trail["attempts"])
    assert any("independent primary evidence" in x for x in obs["queries"])
    assert {"Cost Study","Reliability Report","Environmental Review"} <= set(obs["model_sources"])
    assert all(x in result["answer"]["body"] for x in
               ["Costs","Reliability","Environmental effects"])
    assert len(trail["cited_source_ids"])==3
    assert len(trail["model_source_ids"])==3
    assert trail["saved_count"]==0


def test_unrelated_broad_question_explicitly_reports_unresolved_gap(monkeypatch):
    question=("How do coastal cities compare in flood protection, public health "
              "and housing affordability?")
    dims=[{"name":"Flood protection","query":"coastal city flood protection"},
          {"name":"Public health","query":"coastal cities public health"},
          {"name":"Housing affordability","query":"coastal housing affordability"}]
    initial={"Flood protection":[{"title":"Coastal barriers",
                                   "excerpt":"Flood protection uses levees and wetlands."}],
             "Public health":[{"title":"Urban health research",
                               "excerpt":"Public health outcomes depend on services."}],
             "Housing affordability":[]}
    result,obs=_run(monkeypatch,question,dims,initial,[])
    trail=result["research_trail"]
    assert len(trail["coverage"])==3
    assert [x["name"] for x in trail["coverage"] if x["status"]!="COVERED"]==[
        "Housing affordability"]
    assert any(x["phase"]=="gap follow-up" for x in trail["attempts"])
    assert "Housing affordability" in result["answer"]["body"]
    assert "Evidence missing" in result["answer"]["body"]
    assert "Housing affordability" in result["answer"]["open_questions"]
    assert obs["contexts"]==[question]
    assert result["mode"]=="GENERAL_RESEARCH"


def test_candidate_selection_balanced_across_dimensions():
    buckets=[("A",[{"url":"https://example.com/a"+str(i)} for i in range(8)]),
             ("B",[{"url":"https://example.com/b"+str(i)} for i in range(8)]),
             ("C",[{"url":"https://example.com/c"+str(i)} for i in range(8)])]
    chosen=web._select_candidates(buckets,set(),9)
    assert len(chosen)==9
    assert [sum(x["search_dimensions"]==[label] for x in chosen)
            for label in ("A","B","C")]==[3,3,3]


def test_coverage_audit_does_not_upgrade_snippets(monkeypatch):
    monkeypatch.setattr(web,"_provider_json",lambda *args,**kwargs:None)
    dims=[{"name":"A","query":"A"},{"name":"B","query":"B"}]
    pages=[{"read_status":"SNIPPET_ONLY","search_dimensions":["A"],
            "title":"A result","excerpt":""}]
    reviews=web.evaluate_coverage(dims,pages,"key","model","base")
    assert [x["status"] for x in reviews]==["MISSING","MISSING"]


def test_synthesis_explicitly_requires_whole_scope_and_qualitative_comparison():
    assert "EVERY requested dimension" in engine.SYSTEM
    assert "qualitative differences" in engine.SYSTEM
    assert "dimension_coverage" in engine.generate.__code__.co_consts.__str__()
