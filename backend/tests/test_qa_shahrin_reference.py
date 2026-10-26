"""Offline tests: no external API, no paid inference."""
import hashlib
import json
import pytest

from app.qa_shahrin_reference import MODEL_VARIANT, build_qa_messages, prepare_qa_request

PROMPT = "Classify the input into seven approved categories. Output JSON only."
HASH = hashlib.sha256(PROMPT.encode()).hexdigest()
SOURCE_HASH = "b" * 64


def payload(examples=None):
    refs = examples if examples is not None else []
    return {
        "rubric_version_id": 9, "rubric_hash": HASH,
        "reference_revision": "shahrin-ref-v1", "target_qa_id": "QA-10649",
        "example_count": len(refs), "examples": refs,
    }


def ref(qa_id="QA-1", category="Election Operations", text="Contoh proses pemilu oleh badan penyelenggara.", score=0.3):
    return {"qa_id": qa_id, "shahrin_category": category,
            "source_excerpt": text, "similarity": score}


def build(examples=None):
    return build_qa_messages(
        post_text="Teks postingan asli tanpa label", source_hash=SOURCE_HASH,
        rubric_text=PROMPT, payload=payload(examples),
        model="test-model", target_qa_id="QA-10649",
    )


def test_zero_example_fallback_keeps_json_contract_without_inference():
    result = build()
    assert result.reference_count == 0
    assert result.variant == MODEL_VARIANT
    assert "Output JSON only" in result.messages[0]["content"]
    data = json.loads(result.messages[1]["content"])
    assert data["reference_examples"] == []
    assert data["target_original_post"] == "Teks postingan asli tanpa label"
    assert "QA-10649" not in json.dumps(result.messages)


def test_examples_are_data_and_ids_stay_out_of_model_request():
    references = [ref(), ref("QA-2", "Disputes / Legal", "MK memproses permohonan penggugat.", .2)]
    result = build(references)
    data = json.loads(result.messages[1]["content"])
    assert [x["human_reference_category"] for x in data["reference_examples"]] == [
        "Election Operations", "Disputes / Legal"]
    assert "QA-1" not in json.dumps(result.messages)
    assert "QA-2" not in json.dumps(result.messages)
    assert result.reference_ids == ("QA-1", "QA-2")
    assert result.cache_key == build(references).cache_key
    assert result.cache_key != build([ref(text="Proses berbeda dengan sumber pertama")]).cache_key


@pytest.mark.parametrize("bad", [
    [ref("QA-10649")],
    [ref("QA-1"), ref("QA-1", "Disputes / Legal")],
    [ref("QA-1"), ref("QA-2", "Election Operations")],
    [ref("QA-1", score=.9)],
    [ref("QA-1", score=.11)],
    [ref("QA-1", category="Unauthorized Label")],
    [ref("QA-1", text="")],
    [ref("QA-1", text="x" * 901)],
])
def test_rejects_bad_or_leaky_examples(bad):
    with pytest.raises(ValueError):
        build(bad)


def test_rejects_mutated_rubric_and_payload_for_wrong_target():
    with pytest.raises(ValueError, match="hash mismatch"):
        build_qa_messages(
            post_text="Teks", source_hash=SOURCE_HASH,
            rubric_text=PROMPT + " modified", payload=payload(),
            model="test", target_qa_id="QA-10649")
    with pytest.raises(ValueError, match="different target"):
        build_qa_messages(
            post_text="Teks", source_hash=SOURCE_HASH, rubric_text=PROMPT,
            payload=payload(), model="test", target_qa_id="QA-99999")


def test_db_assembly_only_reads_prompt_source_and_payload():
    class FakeDB:
        def execute(self, query, params):
            self.query, self.params = str(query), params
            return self
        def mappings(self):
            return self
        def one_or_none(self):
            return {
                "message_original": "Contoh unggahan", "source_hash": SOURCE_HASH,
                "base_prompt": PROMPT, "references": payload(),
            }
    db = FakeDB()
    assembled = prepare_qa_request(db, "QA-10649", "test-model")
    assert assembled.reference_count == 0
    assert "qa_imported_human_categories" not in db.query
    assert "curated_category" not in db.query
    assert db.params["max_examples"] == 3
    assert db.params["version_id"] == 9


def test_preview_router_is_disabled_by_default(monkeypatch):
    from fastapi import HTTPException
    from app.qa_shahrin_reference import preview_shahrin_references
    monkeypatch.delenv("BAWASLU_QA_REFERENCE_PREVIEW_ENABLED", raising=False)
    with pytest.raises(HTTPException) as exc:
        preview_shahrin_references("QA-10649", user=None, db=None)
    assert exc.value.status_code == 404
