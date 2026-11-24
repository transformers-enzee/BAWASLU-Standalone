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
import time
import subprocess
import shutil

MAX_TEXT=24000
MAX_PDF_PAGES=100
MAX_SHEET_ROWS=400
MAX_COLS=32

def extract_document(data,kind,question=""):
    words={w for w in re.findall(r"\w{4,}",question.casefold()) if w not in {"what","please","with","should","from","them"}}
    if re.search(r"violation|pelanggaran|provinc|provinsi|candidate|party|partai",question,re.I):
        words.update(("pelanggaran","pemilu","pilkada","provinsi","calon","partai","penanganan","jumlah","putusan","temuan","laporan"))
    sections=[];total=0;notes=[];inspected=0;started=time.monotonic()
    if kind=="PDF":
        method="pypdf"
        # Poppler is installed in the staging runtime; the Python parser
        # remains available in development and as a fallback.
        if shutil.which("pdftotext"):
            try:
                result=subprocess.run(["pdftotext","-layout","-f","1","-l",str(MAX_PDF_PAGES),"-","-"],
                    input=data,capture_output=True,timeout=9,check=True)
                chunks=result.stdout.decode("utf-8",errors="replace").split("\f")
                if chunks and not chunks[-1].strip():chunks.pop()
                inspected=len(chunks)
                sections=[(f"PDF page {i}",text.strip()[:9000]) for i,text in enumerate(chunks,1) if text.strip()]
                if sections:
                    method="poppler";notes.append("Poppler scan bounded to first 100 pages; total pages not established")
            except (subprocess.SubprocessError,OSError):
                notes.append("Poppler extraction unavailable; tried Python parser")
        if not sections:
            from pypdf import PdfReader
            reader=PdfReader(io.BytesIO(data),strict=False)
            if reader.is_encrypted:raise ValueError("Encrypted PDF")
            total=len(reader.pages);inspected=0
            for i,page in enumerate(reader.pages[:MAX_PDF_PAGES],1):
                if time.monotonic()-started>15:
                    notes.append("Time-bounded page scan");break
                inspected+=1
                try:
                    content=(page.extract_text(extraction_mode="layout") or "").strip()
                except Exception:
                    try:content=(page.extract_text() or "").strip()
                    except Exception:
                        notes.append("Page extraction failed: "+str(i));continue
                if content:sections.append((f"PDF page {i}",content[:9000]))
            if total>inspected:notes.append(f"Inspected {inspected} of {total} PDF pages")
        if not sections:notes.append("No extractable text layer; OCR not performed")
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
            notes.append("Extracted text budget reached; not a complete dataset")
            continue
        pieces.append(part);used+=len(part)
    return {"excerpt":"\n".join(pieces),"document_type":kind,"units_inspected":inspected if kind=="PDF" else min(total,MAX_SHEET_ROWS*6),
            "units_total":(total or None) if kind=="PDF" else total,"extraction_method":method if kind=="PDF" else "row extraction",
            "extraction_notes":"; ".join(dict.fromkeys(notes)) or "Bounded extraction; verify original document and page/row references"}

if __name__=="__main__":
    try:
        import resource
        resource.setrlimit(resource.RLIMIT_AS,(512*1024*1024,512*1024*1024))
        resource.setrlimit(resource.RLIMIT_CPU,(18,20))
        result=extract_document(sys.stdin.buffer.read(8_000_001),sys.argv[1],sys.argv[2])
        print(json.dumps(result,ensure_ascii=False))
    except Exception as exc:
        print(json.dumps({"error_code":type(exc).__name__,"excerpt":""}))
        sys.exit(2)
