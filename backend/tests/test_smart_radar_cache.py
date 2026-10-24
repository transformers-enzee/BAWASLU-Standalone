"""Verify repeated dashboard reads do not repeatedly query Supabase for static pilot data."""
from app import smart_radar as radar
class Rows:
    def mappings(self):return self
    def __iter__(self):return iter([{"pilot_post_id":"PILOT-001","source_url":"https://example.org"}])
class DB:
    def __init__(self):self.n=0
    def execute(self,*a,**k):self.n+=1;return Rows()
    def rollback(self):pass
def test_source_cache_reuses_rows():
    radar.invalidate_source_cache()
    db=DB()
    radar.fetch_sources(db);radar.fetch_sources(db)
    assert db.n==1
    radar.invalidate_source_cache()
    radar.fetch_sources(db)
    assert db.n==2
    radar.invalidate_source_cache()
def test_assessment_cache_reuses_rows():
    radar.invalidate_assessment_cache()
    db=DB()
    radar.fetch_assessments(db);radar.fetch_assessments(db)
    assert db.n==1
    radar.invalidate_assessment_cache()
