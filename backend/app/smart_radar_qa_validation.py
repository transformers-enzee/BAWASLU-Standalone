"""Validate Stage-1 v2 predictions without turning quote-format quirks into lost QA work.

Only the exact canonical primary category is essential to score classification.
Evidence quotes are usable ONLY when found verbatim in the original source.
Unverifiable quotes are preserved as *proposals*, never as verified evidence.
"""
import json
import re

class QAOutputError(ValueError):
    def __init__(self,code,message):
        self.code=code
        super().__init__(message)

def canonical_category(value,allowed):
    if not isinstance(value,str):
        raise QAOutputError("invalid_category","AI did not return a primary category")
    key=re.sub(r"\s*/\s*"," / ",re.sub(r"\s+"," ",value.strip())).casefold()
    lookup={x.casefold():x for x in allowed}
    if key not in lookup:
        raise QAOutputError("invalid_category","AI returned a category outside the approved seven")
    return lookup[key]

def verbatim_source_span(source,proposed):
    if not isinstance(proposed,str) or not proposed.strip():
        return None
    quote=proposed.strip()
    if quote in source:
        return quote
    # Whitespace variation alone is harmless, but the returned span MUST
    # be copied from the source to count as verified evidence.
    parts=[re.escape(p) for p in re.split(r"\s+",quote) if p]
    if not parts or len(parts)>100:
        return None
    match=re.search(r"\s+".join(parts),source)
    return source[match.start():match.end()] if match else None

def validate_qa_v2_output(payload,source,allowed,mode):
    choices=payload.get("choices") if isinstance(payload,dict) else None
    if not isinstance(choices,list) or not choices or not isinstance(choices[0],dict):
        raise QAOutputError("missing_completion","AI response did not include a completion")
    choice=choices[0]
    finish=choice.get("finish_reason")
    if finish=="length":
        raise QAOutputError("output_truncated","AI ran out of output tokens before finishing JSON")
    if finish=="content_filter":
        raise QAOutputError("output_filtered","AI provider filtered the completion")
    message=choice.get("message")
    content=message.get("content") if isinstance(message,dict) else None
    if not isinstance(content,str) or not content.strip():
        raise QAOutputError("empty_content","AI completed without readable JSON content")
    try:
        answer=json.loads(content)
    except (ValueError,TypeError) as exc:
        raise QAOutputError("invalid_json","AI returned invalid JSON") from exc
    if not isinstance(answer,dict):
        raise QAOutputError("invalid_json_object","AI output must be a JSON object")
    answer["primary_category"]=canonical_category(answer.get("primary_category"),allowed)
    warnings=[]
    if mode=="guided":
        raw_secondary=answer.get("secondary_categories")
        if not isinstance(raw_secondary,list):
            warnings.append("secondary_categories_missing_or_invalid")
            raw_secondary=[]
        accepted=[]
        for x in raw_secondary[:10]:
            try: cat=canonical_category(x,allowed)
            except QAOutputError:
                warnings.append("invalid_secondary_category_dropped")
                continue
            if cat==answer["primary_category"] or cat in accepted:
                warnings.append("duplicate_secondary_category_dropped")
                continue
            if len(accepted)<2:
                accepted.append(cat)
            else:
                warnings.append("excess_secondary_category_dropped")
        answer["secondary_categories"]=accepted
    else:
        answer.setdefault("secondary_categories",[])
    proposed=answer.get("evidence_quote")
    verified=verbatim_source_span(source,proposed)
    if verified is None:
        # Never present the model's unverified quote as actual source evidence.
        answer["evidence_quote_proposed"]=(proposed[:500] if isinstance(proposed,str) else "")
        answer["evidence_quote"]=""
        answer["evidence_validation"]="needs_source_review"
        warnings.append("evidence_quote_not_verified")
    else:
        answer["evidence_quote"]=verified
        answer["evidence_validation"]="verified_verbatim"
    answer["qa_validation_warnings"]=sorted(set(warnings))
    return answer
