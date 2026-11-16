"""Warning-only distinction between platform-policy assertions and election-law PDFs.

Provider policy applicability, version and moderation outcomes are unverified.
This function sees ONLY preselected authorized evidence and displayed source IDs.
"""
import re

_SENTENCE=re.compile(r"(?<=[.!?;])\s+|\n+")
_CITE=re.compile(r"\[(?:DOC-[0-9]+-P[0-9]+|(?:INT|SOCIAL)-[A-Za-z0-9:_-]+)\]")
_PLATFORM=re.compile(r"\b(?:facebook|instagram|tiktok|tik\s*tok|youtube|threads|twitter|platform\s+[Xx]|kebijakan\s+platform)\b",re.I)
_VERDICT_EN=re.compile(r"\b(?:violates?|breaches?|has\s+violated|is\s+in\s+violation\s+of)\s+(?:(?:the|its|their)\s+)?(?:community\s+guidelines|platform\s+policy|platform\s+rules|[A-Za-z]+\s+(?:policy|rules|guidelines))\b",re.I)
_VERDICT_ID=re.compile(r"\b(?:melanggar|telah\s+melanggar|terbukti\s+melanggar)\s+(?:kebijakan|aturan|pedoman|standar\s+komunitas)\s+(?:platform|komunitas|facebook|instagram|tiktok|youtube|X)\b",re.I)
_UNCERTAIN=re.compile(r"\b(?:potential(?:ly)?|possible|might|may|could|alleged|suspected|unverified|diduga|dugaan|berpotensi|kemungkinan|mungkin|belum\s+terverifikasi|perlu\s+ditinjau)\b",re.I)
_REPORTED=re.compile(r"^(?:according\s+to|reportedly|reported\s+that|menurut\s+sumber|dilaporkan|mengutip)\b",re.I)

def evaluate_policy_boundary(question,evidence,answer,cited_ids,grounding=None):
    """Flag asserted platform rule breaches when legal PDFs are not policy proof."""
    base={"id":"platform_policy_legal_boundary",
          "method":"EXPLICIT_VERDICT_PHRASE_HEURISTIC",
          "status":"NOT_APPLICABLE",
          "possible_platform_policy_verdicts":0,
          "review_items":[],
          "platform_breach_confirmed":False,
          "electoral_law_breach_confirmed":False,
          "current_platform_policy_verified":False,
          "model_calls":0}
    if not (grounding or {}).get("legal_question"):
        return base
    selected={str(r.get("record_id")):r for r in evidence or []
              if isinstance(r,dict) and r.get("record_id")}
    cited=set(str(r) for r in cited_ids or [] if str(r) in selected)
    legal_refs={ref for ref in cited if selected[ref].get("record_type")=="PDF_KNOWLEDGE"
                and selected[ref].get("document_type") in {"REGULATION","SOP","GUIDANCE"}}
    if not legal_refs:
        return base
    flags=[]
    spans=_SENTENCE.split(str(answer or ""))
    for i,span in enumerate(spans):
        clean=_CITE.sub("",span).strip()
        if not clean or clean.endswith("?") or _REPORTED.search(clean) or _UNCERTAIN.search(clean):
            continue
        if not _PLATFORM.search(clean) or not (_VERDICT_EN.search(clean) or _VERDICT_ID.search(clean)):
            continue
        # A local displayed legal-PDF citation can give the misleading impression
        # that election-law documentation verifies a provider moderation ruling.
        local_legal=[ref for ref in legal_refs if "["+ref+"]" in span]
        if not local_legal and i+1<len(spans):
            following=spans[i+1].strip()
            # A standalone citation on the next line is claim-local, but a
            # narrative sentence with a citation is not. Do not borrow from
            # other paragraphs or from structured citations without display.
            if following and not _CITE.sub("",following).strip():
                local_legal=[ref for ref in legal_refs
                             if "["+ref+"]" in following]
        if local_legal:
            flags.append({"claim_index":i+1,
                          "cited_legal_page_ids":sorted(local_legal)[:12],
                          "reason":"PLATFORM_VERDICT_CITED_TO_ELECTORAL_LEGAL_REFERENCE"})
    return {**base,"status":"REVIEW_REQUIRED" if flags else "NOT_APPLICABLE",
            "possible_platform_policy_verdicts":len(flags),
            "review_items":flags[:12]}
