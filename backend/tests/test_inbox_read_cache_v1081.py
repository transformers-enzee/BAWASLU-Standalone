import pytest
from app.inbox_read_cache import read,invalidate

def test_repeated_read_eliminates_second_db_query():
    invalidate()
    calls=[]
    def load():calls.append(1);return {'findings':[{'id':1}]}
    p={'id':'1','role':'Admin','province':''}
    assert read(p,{'campaign_id':1},load)['findings'][0]['id']==1
    assert read(p,{'campaign_id':1},load)['findings'][0]['id']==1
    assert len(calls)==1

def test_scope_and_user_isolation():
    invalidate()
    calls=[]
    def load():calls.append(1);return {'count':len(calls)}
    a={'id':'1','role':'Admin','province':'A'}
    b={'id':'1','role':'Admin','province':'B'}
    c={'id':'2','role':'Admin','province':'A'}
    assert read(a,{},load)['count']==1
    assert read(b,{},load)['count']==2
    assert read(c,{},load)['count']==3

def test_mutation_invalidation_reloads():
    invalidate()
    calls=[]
    def load():calls.append(1);return len(calls)
    assert read({'id':'1'}, {},load)==1
    invalidate()
    assert read({'id':'1'}, {},load)==2

def test_caller_mutation_never_mutates_cached_evidence():
    invalidate()
    def load():return {'findings':[{'id':1,'text':'original'}]}
    first=read({'id':'1'}, {},load)
    first['findings'][0]['text']='edited'
    assert read({'id':'1'}, {},load)['findings'][0]['text']=='original'

def test_failed_reads_are_not_cached():
    invalidate()
    counter=[]
    def bad():counter.append(1);raise PermissionError('Denied')
    for i in range(2):
        with pytest.raises(PermissionError):read({'id':'1'}, {},bad)
    assert len(counter)==2

def test_concurrent_authorized_reads_share_one_loader():
    from concurrent.futures import ThreadPoolExecutor
    from threading import Event, Lock
    import time
    invalidate()
    entered,finish,guard=Event(),Event(),Lock()
    calls=[0]
    def load():
        with guard:
            calls[0]+=1
        entered.set()
        assert finish.wait(timeout=5)
        return {'findings':[{'id':1001}]}
    p={'id':'same-user','permissions':{'view_intelligence':True},'province':'Bali'}
    with ThreadPoolExecutor(max_workers=6) as pool:
        jobs=[pool.submit(read,p,{'campaign_id':None},load) for _ in range(6)]
        assert entered.wait(timeout=5)
        time.sleep(.04)
        finish.set()
        values=[job.result(timeout=5) for job in jobs]
    assert calls[0]==1
    assert all(x['findings'][0]['id']==1001 for x in values)


def test_province_filter_participates_in_both_authorized_read_cache_keys():
    from pathlib import Path
    root=Path(__file__).resolve().parents[2]
    browser=(root/'frontend/src/api/base44Client.js').read_text(encoding='utf-8')
    server=(root/'backend/app/main.py').read_text(encoding='utf-8')
    inbox=(root/'frontend/src/pages/Inbox.jsx').read_text(encoding='utf-8')
    assert "data.include_totals===true,data.province_filter||''" in browser
    assert "'province_filter':(body.data or {}).get('province_filter')" in server
    assert 'province_filter:chosenLocation' in inbox
    assert '},[campaign,chosenLocation]);' in inbox


def test_province_scoped_keys_do_not_share_results_with_unfiltered_query():
    invalidate()
    calls=[]
    def load(label):
        calls.append(label)
        return {'findings':[{'id':label}]}
    p={'id':'1','role':'National Administrator','geographic_scope':'Nationwide'}
    base={'campaign_id':'','paged':True,'page_size':100}
    south={**base,'province_filter':'Sumatera Selatan'}
    assert read(p,base,lambda:load('all'))['findings'][0]['id']=='all'
    assert read(p,south,lambda:load('south'))['findings'][0]['id']=='south'
    assert read(p,base,lambda:load('wrong'))['findings'][0]['id']=='all'
    assert read(p,south,lambda:load('wrong'))['findings'][0]['id']=='south'
    assert calls==['all','south']
