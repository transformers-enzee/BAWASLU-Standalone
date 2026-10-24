"""Only human-verified incident provinces contribute to the provincial heatmap."""
from app import smart_radar

class GeoRows:
    def mappings(self): return self
    def __iter__(self):
        return iter([
            {"pilot_post_id":"PILOT-001","province_code":"32"},
            {"pilot_post_id":"PILOT-001","province_code":"32"},
            {"pilot_post_id":"PILOT-002","province_code":"94"},
        ])
class GeoDB:
    def __init__(self): self.calls=0
    def execute(self, query):
        self.calls+=1
        sql=str(query)
        assert "verification_status='verified'" in sql
        assert "location_role='incident'" in sql
        return GeoRows()
    def rollback(self): pass

def test_incident_province_query_excludes_unverified_roles_and_caches():
    smart_radar._GEO_CACHE.update(rows=None,expires=0)
    db=GeoDB()
    result=smart_radar.fetch_verified_incident_geography(db)
    assert result=={"PILOT-001":{"32"},"PILOT-002":{"94"}}
    assert smart_radar.fetch_verified_incident_geography(db)==result
    assert db.calls==1
    smart_radar._GEO_CACHE.update(rows=None,expires=0)
