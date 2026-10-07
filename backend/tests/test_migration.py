import json, os, pathlib, tempfile
os.environ['DATABASE_URL']='sqlite:///:memory:'
from app.db import Base, engine, SessionLocal
from app.models import IntelligenceItem, IssueCategory, DataSource, ExternalDataConnector, MigrationStagingRecord
from app.migration_importer import stage, commit_batch

def setup_function(): Base.metadata.drop_all(engine); Base.metadata.create_all(engine)

def test_importer_includes_previously_omitted_entities_and_is_traceable():
    with tempfile.TemporaryDirectory() as td:
        p=pathlib.Path(td)
        (p/'IntelligenceItem.json').write_text(json.dumps([{'id':'old-1','intelligence_id':'INT-2025-000001','title':'Legacy','original_content':'raw','source_identity':{'status':'UNRESOLVED'},'jurisdiction_type':'National','jurisdiction_confirmed':True}]))
        (p/'IssueCategory.json').write_text(json.dumps([{'id':'cat-1','name':'Campaign','active':True,'sort_order':1}]))
        (p/'DataSource.json').write_text(json.dumps([{'id':'src-1','name':'Manual','source_type':'Web','status':'Active'}]))
        (p/'ExternalDataConnector.json').write_text(json.dumps([{'id':'con-1','connector_id':'socialcrawl','provider_name':'SocialCrawl','status':'DISABLED','supported_sources':['TikTok','XHS']}]))
        db=SessionLocal(); batch=stage(db,p,dry_run=False); batch,errors=commit_batch(db,batch.id); assert not errors
        assert db.query(IntelligenceItem).filter_by(external_id='old-1').one().title=='Legacy'
        assert db.query(IssueCategory).filter_by(external_id='cat-1').one().name=='Campaign'
        assert db.query(DataSource).filter_by(external_id='src-1').one().name=='Manual'
        assert db.query(ExternalDataConnector).filter_by(external_id='con-1').one().connector_id=='socialcrawl'
        staged=db.query(MigrationStagingRecord).filter_by(source_record_id='old-1').one(); assert json.loads(staged.payload_json)['original_content']=='raw'; assert staged.validation_status=='committed'
        db.close()
