"""Human-reviewed spreadsheet routing and idempotency (no AI/provider calls)."""
import io
import openpyxl
from sqlalchemy import create_engine
from sqlalchemy.orm import Session
from app.db import Base
from app.models import MonitoringCampaign,CampaignEvidence,EvidenceAssessment,SocialListeningResult
from app.human_verified_import import read_rows,preview,import_rows,MODEL

def workbook(labels=('Relevant','Irrelevant','Relevant')):
    wb=openpyxl.Workbook();ws=wb.active;ws.title='Human Review 200'
    ws.append(['Sample ID','Platform','Account','Message','Direct URL','Relevancy','Sentiment','Category'])
    for i,label in enumerate(labels):
        ws.append([f'QA-{i+1:03}', 'x','reviewer','Informasi pemilu '+str(i),
                   'https://x.com/example/status/'+str(i//2),label,'Neutral',
                   'Allegations / Violations' if label=='Relevant' else '-'])
    data=io.BytesIO();wb.save(data);return data.getvalue()

def test_preview_preserves_duplicate_urls_but_separate_samples():
    result=preview(workbook())
    assert (result['total'],result['relevant'],result['irrelevant'],result['unique_direct_urls'])==(3,2,1,2)

def test_all_posts_saved_relevant_only_enter_inbox_and_rerun_is_idempotent():
    engine=create_engine('sqlite:///:memory:')
    Base.metadata.create_all(engine)
    db=Session(engine)
    db.add(MonitoringCampaign(id=1,name='BAWASLU',created_by='1'));db.commit()
    a=import_rows(db,db.get(MonitoringCampaign,1),workbook(),'1')
    assert a['inserted']==3 and a['saved_human_assessments']==3
    assert db.query(SocialListeningResult).count()==3
    assert db.query(CampaignEvidence).count()==3
    relevant=db.query(EvidenceAssessment).filter(EvidenceAssessment.relevance_label=='RELEVANT').count()
    assert relevant==2
    assert db.query(EvidenceAssessment).filter(EvidenceAssessment.relevance_label=='IRRELEVANT').count()==1
    assert not any(x.potential_issue_signals_json!='[]' for x in db.query(EvidenceAssessment).all())
    b=import_rows(db,db.get(MonitoringCampaign,1),workbook(),'1')
    assert b['inserted']==0 and b['saved_human_assessments']==0
    assert db.query(SocialListeningResult).count()==3
    db.close()

def test_invalid_human_label_is_rejected():
    from pytest import raises
    with raises(ValueError):
        read_rows(workbook(('Relevant','Unverified')))
