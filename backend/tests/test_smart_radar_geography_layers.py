"""Evidence-linked geography views preserve uncertainty and prevent duplicate post counts."""
from app.smart_radar_geography import get_geo_by_post, attach_geo_to_findings, invalidate_geo_cache
class QueryResult:
    def mappings(self): return self
    def __iter__(self):
        return iter([
          {"pilot_post_id":"PILOT-003","province_code":"12","province_name":"Sumatera Utara","location_role":"activity","verification_status":"unverified","source_quote":"Kota Medan","evidence_note":"Hearing venue"},
          {"pilot_post_id":"PILOT-003","province_code":"12","province_name":"Sumatera Utara","location_role":"institution","verification_status":"unverified","source_quote":"KPU Kabupaten Langkat","evidence_note":"Named institution"},
          {"pilot_post_id":"PILOT-080","province_code":"18","province_name":"Lampung","location_role":"activity","verification_status":"unverified","source_quote":"Kabupaten Lampung Tengah","evidence_note":"Regional activity"}
        ])
class FakeDB:
    def __init__(self):self.calls=0
    def execute(self,q):
        self.calls+=1
        sql=str(q)
        assert "location_role IN ('activity','institution','incident')" in sql
        assert "verification_status IN ('unverified','verified')" in sql
        return QueryResult()

def test_provisional_geo_layers_do_not_create_verified_incidents():
    invalidate_geo_cache()
    db=FakeDB()
    findings=[{"id":"RADAR-A","source_ids":["PILOT-003","PILOT-080"]}]
    attach_geo_to_findings(findings,db)
    f=findings[0]
    assert set(f["geo_layers"]["regional"])=={"12","18"}
    assert f["geo_layers"]["regional"]["12"]==["PILOT-003"]
    assert f["geo_layers"]["institution"]["12"]==["PILOT-003"]
    assert f["geo_layers"]["potential_incident"]=={}
    assert f["geo_layers"]["verified_incident"]=={}
    assert f["province_codes"]==[]
    assert f["verified_geo_posts"]==0
    attach_geo_to_findings(findings,db)
    assert db.calls==1
    invalidate_geo_cache()
