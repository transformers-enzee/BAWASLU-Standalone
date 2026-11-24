"""Conservative source-matched numeric series and whole-report citation diagnostics.

Numeric match is not semantic verification, independence, or proof of a case.
Never infer a denominator, sum overlapping categories, or rank named persons.
"""
import re
import unicodedata

def normalized(text):
    return " ".join(unicodedata.normalize("NFKC",str(text or "")).casefold().split())

NUM=re.compile(r"(?<![\w-])\d+(?:[.,]\d+)*(?![\w-])")
CITE=re.compile(r"\[((?:P|R)-\d+)\]")

def integer_values(text):
    result=set()
    for match in NUM.finditer(str(text)):
        val=match.group()
        if re.fullmatch(r"\d{1,3}(?:[.,]\d{3})+",val):val=val.replace(",","").replace(".","")
        if val.isdigit():result.add(int(val))
    return result

def quote_in_source(quote,source):
    q=normalized(quote)
    return len(q)>=12 and q in normalized(source.get("excerpt"))

def build_series(proposals,sources):
    eligible={s["id"]:s for s in sources if s.get("kind")=="OFFICIAL" and s.get("read_status")=="READ"}
    out=[]
    for series in (proposals if isinstance(proposals,list) else [])[:5]:
        if not isinstance(series,dict) or series.get("group_by") not in ("CATEGORY","PROVINCE","STAGE"):continue
        fields=("title","election_type","period","case_status","unit")
        if not all(isinstance(series.get(k),str) and series[k].strip() for k in fields):continue
        rows=[];seen=set()
        for row in (series.get("rows") or [])[:38]:
            if not isinstance(row,dict):continue
            source=eligible.get(row.get("source_id"));value=row.get("value")
            label=str(row.get("label") or "")[:140];original=str(row.get("source_label") or "")
            quote=str(row.get("source_quote") or "")
            if not source or type(value) is not int or not 0<=value<=10**10 or not label.strip():continue
            if not original.strip() or normalized(original) not in normalized(quote):continue
            if not quote_in_source(quote,source) or value not in integer_values(quote):continue
            if normalized(label) in seen:continue
            seen.add(normalized(label))
            rows.append({"label":label,"value":value,"source_id":source["id"],"source_label":original[:140],"source_quote":quote[:600]})
        # Restrict each series to a single source and unit. Conflicting
        # publications are separate series, not merged into one ranking.
        if len(rows)<2 or len({r["source_id"] for r in rows})!=1:continue
        rows.sort(key=lambda r:-r["value"])
        out.append({**{k:series[k][:160] for k in fields},"group_by":series["group_by"],
            "rows":rows,"highest":rows[0]["label"],"range":rows[0]["value"]-rows[-1]["value"],
            "method":"Exact source excerpt and integer matching; proposed grouping requires reviewer validation",
            "complete_dataset":False})
    return out

def audit_report(answer,sources):
    eligible={s["id"]:s for s in sources if s.get("read_status") in ("READ","SAVED_SNAPSHOT")}
    flags=[];checked=0;matched=0
    for line in str(answer).splitlines():
        # Citation IDs, list numbering and heading numbering are not data.
        ids=list(dict.fromkeys(CITE.findall(line)))
        text=CITE.sub("",line).strip()
        text=re.sub(r"^\s*(?:#+\s*)?\d+[.)]\s+","",text)
        nums=integer_values(text)
        if not nums:continue
        # Without inline citation a number may be a proposed target or date;
        # do not claim it is unsupported, report it for review.
        checked+=1
        pool=set()
        for i in ids:
            if i in eligible:pool.update(integer_values(eligible[i].get("excerpt","")))
        missing=nums-pool
        if ids and not missing:matched+=1
        elif len(flags)<30:
            flags.append({"passage":line[:420],"source_ids":ids,
                "reason":"NUMERIC_TEXT_NOT_MATCHED" if ids else "NO_INLINE_SOURCE_FOR_NUMERIC_TEXT",
                "unmatched_values":sorted(missing)[:12]})
    return {"numeric_lines_checked":checked,"numeric_lines_matched":matched,
            "review_flags":flags,"method":"Lexical number/citation check only; not full factual or legal verification",
            "all_material_claims_verified":False}
