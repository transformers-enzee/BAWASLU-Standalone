"""Bounded document extraction in a separate resource-limited process.

No macros, formulas, network requests or external links are evaluated.
The extractor returns sampled text with original page/row references.
"""
import csv
import io
import json
import re
import sys
import zipfile

MAX_TEXT=24000
MAX_PDF_PAGES=100
MAX_SHEET_ROWS=400
MAX_COLS=32

def extract_document(data,kind,question=""):
    words={w for w in re.findall(r"\w{4,}",question.casefold()) if w not in {"what","please","with","should","from","them"}}
    if re.search(r"violation|pelanggaran|provinc|provinsi|candidate|party|partai",question,re.I):
        words.update(("pelanggaran","pemilu","pilkada","provinsi","calon","partai","penanganan","jumlah","putusan","temuan","laporan"))
    sections=[];total=0;notes=[]
    if kind=="PDF":
        from pypdf import PdfReader
        reader=PdfReader(io.BytesIO(data),strict=False)
        if reader.is_encrypted:raise ValueError("Encrypted PDF")
        total=len(reader.pages)
        for i,page in enumerate(reader.pages[:MAX_PDF_PAGES],1):
            content=(page.extract_text(extraction_mode="layout") or "").strip()
            if content:sections.append((f"PDF page {i}",content[:9000]))
        if total>MAX_PDF_PAGES:notes.append("Only first 100 PDF pages inspected")
        if not sections:notes.append("No text layer; OCR not performed")
    elif kind=="CSV":
        text=data.decode("utf-8-sig",errors="strict")
        reader=csv.reader(io.StringIO(text))
        for i,row in enumerate(reader,1):
            total=i
            if i>MAX_SHEET_ROWS:notes.append("CSV row limit reached");break
            sections.append((f"CSV row {i}"," | ".join(str(v)[:300] for v in row[:MAX_COLS])))
    elif kind=="XLSX":
        from openpyxl import load_workbook
        with zipfile.ZipFile(io.BytesIO(data)) as archive:
            infos=archive.infolist()
            if len(infos)>1500 or sum(x.file_size for x in infos)>60_000_000:
                raise ValueError("Workbook decompression limit")
        book=load_workbook(io.BytesIO(data),read_only=True,data_only=True,keep_links=False)
        try:
            for sheet in book.worksheets[:6]:
                for i,row in enumerate(sheet.iter_rows(max_row=MAX_SHEET_ROWS,max_col=MAX_COLS,values_only=True),1):
                    if all(v is None for v in row):continue
                    total+=1
                    sections.append((f"Sheet {sheet.title[:80]} row {i}"," | ".join(str(v if v is not None else "")[:300] for v in row)))
                if (sheet.max_row or 0)>MAX_SHEET_ROWS:notes.append("Sheet row limit reached: "+sheet.title[:80])
            if len(book.worksheets)>6:notes.append("Only first six worksheets inspected")
        finally:book.close()
    else:raise ValueError("Unsupported document type")
    # Preserve tabular order and headers. Select PDF passages by relevance,
    # but keep the original page numbers. Never call an extracted subset a full dataset.
    if kind=="PDF":
        ranked=sorted(enumerate(sections),key=lambda item:(-sum(w in item[1][1].casefold() for w in words),item[0]))
        selected=sorted(ranked[:18],key=lambda item:item[0])
        sections=[x[1] for x in selected]
    pieces=[];used=0
    for label,body in sections:
        part=f"[{label}]\n{body}\n"
        if used+len(part)>MAX_TEXT:
            notes.append("Extracted text budget reached; not a complete dataset");break
        pieces.append(part);used+=len(part)
    return {"excerpt":"\n".join(pieces),"document_type":kind,"units_inspected":total,
            "extraction_notes":"; ".join(dict.fromkeys(notes)) or "Bounded extraction; verify original document and page/row references"}

if __name__=="__main__":
    try:
        import resource
        resource.setrlimit(resource.RLIMIT_AS,(384*1024*1024,384*1024*1024))
        resource.setrlimit(resource.RLIMIT_CPU,(7,8))
        result=extract_document(sys.stdin.buffer.read(8_000_001),sys.argv[1],sys.argv[2])
        print(json.dumps(result,ensure_ascii=False))
    except Exception:
        sys.exit(2)
