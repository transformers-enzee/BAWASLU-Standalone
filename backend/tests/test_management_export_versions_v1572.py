"""v157.2 management export version parity without accessing live data."""
import csv,io
from datetime import datetime,timedelta
from app.models import User
from app.access import profile
from app.casework import CaseReport
from app.management_reporting import briefing_csv,build_briefing
from app.management_report_templates import build_interim_template,render_docx,render_xlsx,render_pdf
from test_management_briefings_v1468 import dataset

def setup(db):
    base=datetime.utcnow()
    db.add(CaseReport(id=9,case_id=1,title="Returned UAT version",
        status="RETURNED",created_by=1,
        created_at=base+timedelta(seconds=1),updated_at=base))
    db.add(CaseReport(id=10,case_id=1,title="Approved revised UAT version",
        status="APPROVED",created_by=1,
        created_at=base+timedelta(seconds=2),updated_at=base))
    db.commit()

def test_template_exposes_latest_and_history_in_all_export_renderers():
    db=dataset()
    try:
        setup(db)
        report=build_briefing(db,profile(db,db.get(User,1)),1,language="en")
        template=report["template"]
        values={r["label"]:r["value"] for r in template["scorecard"]}
        assert values["Reports approved"]==1
        assert values["Stored report versions"]==3
        assert values["Historical report versions (not approvals)"]==2
        assert values["Historical returned versions"]==1
        assert values["Cases approved after a return"]==1
        assert values["Latest reports awaiting revision"]==0
        assert any("never counted again as current approvals" in x
                   for x in template["methodology"])
        xlsx=render_xlsx(template)
        from openpyxl import load_workbook
        wb=load_workbook(io.BytesIO(xlsx),read_only=True,data_only=True)
        rows=list(wb["Report Summary"].values)
        assert any(r[0]=="Reports approved" and r[1]==1 for r in rows)
        assert any(r[0]=="Historical returned versions" and r[1]==1 for r in rows)
        assert any(r[0]=="Cases approved after a return" and r[1]==1 for r in rows)
        wb.close()
        from docx import Document
        doc=Document(io.BytesIO(render_docx(template)))
        doc_text=" ".join(p.text for p in doc.paragraphs)
        table_text=" ".join(cell.text for table in doc.tables for row in table.rows for cell in row.cells)
        assert "Historical returned versions" in doc_text+table_text
        assert "Cases approved after a return" in doc_text+table_text
        pdf=render_pdf(template)
        assert pdf.startswith(b"%PDF")
    finally:db.close()

def test_csv_includes_one_latest_status_and_version_counts_per_case():
    db=dataset()
    try:
        setup(db)
        response=briefing_csv("weekly","",db.get(User,1),db)
        rows=list(csv.DictReader(io.StringIO(response.body.decode("utf-8-sig"))))
        assert len(rows)==3
        row=next(x for x in rows if x["Case ID"]=="1")
        assert row["Latest report status"]=="APPROVED"
        assert row["Latest report ID"]=="10"
        assert row["Stored report versions"]=="3"
        assert row["Superseded report versions"]=="2"
        assert sum(x["Latest report status"]=="APPROVED" for x in rows)==1
    finally:db.close()

def test_export_province_scope_excludes_other_province_data():
    db=dataset()
    try:
        setup(db)
        response=briefing_csv("weekly","",db.get(User,2),db)
        rows=list(csv.DictReader(io.StringIO(response.body.decode("utf-8-sig"))))
        assert {x["Case ID"] for x in rows}=={"1","2"}
        assert sum(x["Latest report status"]=="APPROVED" for x in rows)==1
    finally:db.close()

def test_latest_returned_supersedes_old_approval_in_csv():
    db=dataset()
    try:
        db.add(CaseReport(id=9,case_id=1,title="Returned revision",status="RETURNED",
          created_by=1,created_at=datetime.utcnow()+timedelta(seconds=1),
          updated_at=datetime.utcnow()))
        db.commit()
        response=briefing_csv("weekly","",db.get(User,1),db)
        rows=list(csv.DictReader(io.StringIO(response.body.decode("utf-8-sig"))))
        row=next(x for x in rows if x["Case ID"]=="1")
        assert row["Latest report status"]=="RETURNED"
        assert row["Stored report versions"]=="2"
        assert sum(x["Latest report status"]=="APPROVED" for x in rows)==0
    finally:db.close()
