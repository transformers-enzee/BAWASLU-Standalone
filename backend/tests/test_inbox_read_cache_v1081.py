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
