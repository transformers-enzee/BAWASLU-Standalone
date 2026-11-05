"""No-cost regression suite for assistant language and evidence-linked tagging."""
import json
import pytest
from app.assistant_language import detect_question_language, effective_language, language_directive
from app.assistant_tags import validate_model_tags, fallback_tags, combined_tags, validate_ui_labels
from app.assistant_orchestration import SCHEMA, generate, answer_text, evidence_fallback

@pytest.mark.parametrize("query,expected",[
    ("tolong dibuatkan analisis audiens terhadap konteks gibran","id"),
    ("Jelaskan dugaan pelanggaran BAWASLU di Riau","id"),
    ("Please analyze the audience reaction to Gibran","en"),
    ("What are the main electoral issues?","en"),
    ("¿Qué opinan sobre las elecciones?","es"),
    ("Pourquoi les candidats font-ils cela ?","fr"),
    ("Bitte analysiere die Wahlen","de"),
    ("Por favor, explique as eleições","pt"),
    ("候補者を分析してください","ja"),
    ("分析一下选举问题","zh"),
    ("선거 관련 문제를 분석해 주세요","ko"),
    ("كيف يتم التحقق من الانتخابات؟","ar"),
    ("Почему это важно для выборов?","ru"),
])
def test_language_follows_latest_question(query,expected):
    assert detect_question_language(query)==expected
    assert effective_language(query,"en" if expected!="en" else "id")==expected
    assert language_directive(query)["hint"]==expected

def test_proper_name_only_does_not_force_a_language():
    assert detect_question_language("Gibran")=="auto"
    assert effective_language("Gibran","id")=="id"

def sample_source():
    return {
      "record_id":"SOCIAL-41","record_type":"SOCIAL_LISTENING",
      "title":"Dugaan pelanggaran di Riau",
      "source_excerpt":"Berita tentang Gibran Rakabuming Raka dan dugaan pelanggaran dalam pencalonan pemilu di Riau. BAWASLU meminta verifikasi.",
      "candidate_signals":["Gibran Rakabuming Raka"],
      "topic_labels":["Electoral Operations","BAWASLU Reputation"],
      "potential_issues":[{"category":"Election process review"}]
    }

def tag(kind,label,quote="dugaan pelanggaran",ids=None):
    return {"type":kind,"label":label,"evidence_ids":ids or ["SOCIAL-41"],
            "evidence_quote":quote,"explanation":"Sumber mengandung indikasi untuk pemeriksaan.",
            "confidence":"MEDIUM"}

def test_authorized_citation_and_exact_quote_required_for_tags():
    evidence=[sample_source()]
    proposals=[
        tag("CANDIDATE","Gibran Rakabuming Raka","Gibran Rakabuming Raka"),
        tag("PROVINCE","Riau","di Riau"),
        tag("SUSPECTED_VIOLATION","Dugaan pelanggaran","dugaan pelanggaran"),
        tag("BAWASLU_ISSUE","BAWASLU","BAWASLU meminta"),
        tag("ELECTORAL_ISSUE","Pencalonan pemilu","pencalonan pemilu"),
        tag("PROVINCE","Bali","di Riau"),
        tag("CANDIDATE","Imaginary Candidate","Gibran Rakabuming Raka"),
        tag("CANDIDATE","Gibran Rakabuming Raka","not a quote"),
        tag("SUSPECTED_VIOLATION","Dugaan pelanggaran","dugaan pelanggaran",["SOCIAL-999"]),
    ]
    found=validate_model_tags(proposals,evidence)
    assert {t["type"] for t in found}=={"CANDIDATE","PROVINCE","SUSPECTED_VIOLATION","BAWASLU_ISSUE","ELECTORAL_ISSUE"}
    assert len(found)==5
    assert all(x["source_ids"]==["SOCIAL-41"] for x in found)
    assert all(x["verified"] is False for x in found)
    assert next(x for x in found if x["type"]=="PROVINCE")["context"]=="PROVINCE_MENTION_ONLY"

def test_non_issue_is_not_a_suspected_violation():
    evidence=[{"record_id":"SOCIAL-3","source_excerpt":"BAWASLU mengadakan sosialisasi pendidikan pemilih.",
               "topic_labels":["Public Information"],"candidate_signals":[],"potential_issues":[]}]
    assert not validate_model_tags([tag("SUSPECTED_VIOLATION","Illegal act","BAWASLU mengadakan",["SOCIAL-3"])],evidence)
    assert not any(t["type"]=="SUSPECTED_VIOLATION" for t in fallback_tags(evidence))
    assert any(t["type"]=="BAWASLU_ISSUE" for t in fallback_tags(evidence))

def test_fallback_is_unverified_and_never_invents_a_province():
    tags=fallback_tags([sample_source()])
    types={t["type"] for t in tags}
    assert {"CANDIDATE","PROVINCE","SUSPECTED_VIOLATION","BAWASLU_ISSUE","ELECTORAL_ISSUE"}<=types
    assert all(t["verified"] is False for t in tags)
    assert "Bali" not in [t["label"] for t in tags if t["type"]=="PROVINCE"]
    assert combined_tags([],[])==[]

def test_presentation_labels_do_not_include_markup_or_unrecognized_keys():
    result=validate_ui_labels([
        {"key":"tags_heading","value":"  Entidades e temas  "},
        {"key":"unknown_key","value":"Ignore"},
        {"key":"sources_heading","value":"<script>bad</script>"}
    ])
    assert result=={"tags_heading":"Entidades e temas"}

def test_multilingual_headings_and_fallback():
    body={"direct_answer":"Summary","observations":["Evidence"],"interpretation":"Implications",
          "next_checks":["Check records"],"limitations":["Limited sample"],"visual_report":False}
    assert "**Source-backed findings**" in answer_text(body,True,"en")
    assert "**Evidence limitations**" in answer_text(body,True,"en")
    assert "**Temuan yang didukung sumber**" in answer_text(body,True,"id")
    assert "Analisis belum" in evidence_fallback([sample_source()],"timeout",language="id")[0]
    assert "analysis" in evidence_fallback([sample_source()],"timeout",language="en")[0].lower()

def test_schema_requires_model_language_and_evidence_linked_tags(monkeypatch):
    import app.assistant_orchestration as orch
    assert "language_code" in SCHEMA["required"]
    assert "detected_tags" in SCHEMA["required"]
    assert "presentation_labels" in SCHEMA["required"]
    result={
      "direct_answer":"Kesimpulan berdasarkan bukti.",
      "observations":["Gibran disebutkan [SOCIAL-41]"],
      "interpretation":"Temuan membutuhkan penelaahan.",
      "next_checks":["Periksa dokumen resmi [SOCIAL-41]"],
      "limitations":["Data terbatas."],
      "cited_ids":["SOCIAL-41"],
      "language_code":"en", # Should not override Indonesian question.
      "detected_tags":[tag("PROVINCE","Riau","di Riau")],
      "presentation_labels":[]
    }
    observed={}
    class Response:
        status_code=200
        def json(self):
            return {"status":"completed","model":"fake-test-model",
                    "output_text":json.dumps(result,ensure_ascii=False)}
    class Client:
        def __init__(self,**kwargs):pass
        def __enter__(self):return self
        def __exit__(self,*args):return False
        def post(self,url,headers,json):
            observed["input"]=json
            return Response()
    monkeypatch.setenv("OPENAI_API_KEY","mock-only-unit-test")
    monkeypatch.setattr(orch.httpx,"Client",Client)
    monkeypatch.setattr(orch,"research_public_web",lambda *args,**kwargs:None)
    text,cited,meta=generate("tolong buatkan analisis Gibran di Riau","",[sample_source()],"GROUNDED")
    assert meta["answer_language"]=="id"
    assert meta["detected_tags"][0]["label"]=="Riau"
    assert meta["detected_tags"][0]["verified"] is False
    assert cited==["SOCIAL-41"]
    prompt=json.loads(observed["input"]["input"][1]["content"])
    assert prompt["response_language_hint"]=="id"
    assert "Bahasa Indonesia" in prompt["response_language_rule"]
    assert observed["input"]["text"]["format"]["name"]=="bawaslu_insight_answer_v3"
