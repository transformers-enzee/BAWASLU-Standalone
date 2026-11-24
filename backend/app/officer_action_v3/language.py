"""Explicit English/Indonesian language contract; other languages follow the request."""
import re

EN={"what","which","how","why","when","please","should","could","would","the","and","of","with","for","are","is","from","your","this","these","election","violations"}
ID={"apa","apakah","bagaimana","mengapa","kapan","tolong","jelaskan","sebutkan","yang","dan","dengan","untuk","dari","pada","dalam","adalah","oleh","tersebut","perlu","pelanggaran","pemilihan"}

def detect(text):
    words=re.findall(r"[a-z]+",str(text).casefold())
    e=sum(w in EN for w in words);i=sum(w in ID for w in words)
    if e>=2 and e>=i*1.6:return "en"
    if i>=2 and i>=e*1.6:return "id"
    return "auto"

def requested_language(question):
    q=question.casefold()
    if re.search(r"\b(?:answer|reply|respond|write|translate|jawab|tulis|terjemahkan)(?:\s+\w+){0,3}\s+(?:in |dalam |bahasa )?(?:bahasa indonesia|indonesian)\b",q):return "id"
    if re.search(r"\b(?:answer|reply|respond|write|translate|jawab|tulis|terjemahkan)(?:\s+\w+){0,3}\s+(?:in |dalam |bahasa )?(?:english|inggris)\b",q):return "en"
    return detect(q)

def wrong_language(report,language):
    if language not in ("en","id") or not isinstance(report,dict):return False
    # Source titles and original quotes do not determine the answer language.
    parts=[str(report.get(k) or "") for k in ("headline","answer","key_takeaway","recommended_decision","draft")]
    return detect(" ".join(parts)) not in (language,"auto")
