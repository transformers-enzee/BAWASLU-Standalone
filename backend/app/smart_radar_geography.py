"""Source-linked provisional geography for Smart Radar. All queries authorized by caller."""
import os
import threading
import time
from collections import defaultdict
from sqlalchemy import text

_GEO_LOCK=threading.RLock()
_GEO_CACHE={"rows":None,"expires":0.0}

def invalidate_geo_cache():
    with _GEO_LOCK:
        _GEO_CACHE.update(rows=None,expires=0.0)

def get_geo_by_post(db):
    ttl=max(10,min(300,int(os.getenv("SMART_RADAR_GEO_CACHE_SECONDS","60"))))
    with _GEO_LOCK:
        if _GEO_CACHE["rows"] is not None and time.monotonic()<_GEO_CACHE["expires"]:
            return _GEO_CACHE["rows"]
        rows=db.execute(text("""
            SELECT pilot_post_id,province_code,province_name,location_role,
                   verification_status,source_quote,evidence_note
            FROM pilot_smart_radar.post_geography
            WHERE verification_status IN ('unverified','verified')
              AND location_role IN ('activity','institution','incident')
        """)).mappings()
        by_post=defaultdict(list)
        for x in rows:
            by_post[x["pilot_post_id"]].append(dict(x))
        _GEO_CACHE.update(rows=dict(by_post),expires=time.monotonic()+ttl)
        return _GEO_CACHE["rows"]

def attach_geo_to_findings(findings,db):
    by_post=get_geo_by_post(db)
    for f in findings:
        layer_sets={name:defaultdict(set) for name in ("regional","activity","institution","potential_incident","verified_incident")}
        for pid in f.get("source_ids",[]):
            for loc in by_post.get(pid,[]):
                code=loc["province_code"]
                role=loc["location_role"]
                if role in ("activity","institution"):
                    layer_sets["regional"][code].add(pid)
                    layer_sets[role][code].add(pid)
                elif role=="incident":
                    layer_sets["verified_incident" if loc["verification_status"]=="verified" else "potential_incident"][code].add(pid)
        f["geo_layers"]={layer:{code:sorted(ids) for code,ids in by_province.items()} for layer,by_province in layer_sets.items()}
        f["province_codes"]=sorted(layer_sets["verified_incident"])
        f["verified_geo_posts"]=len({pid for ids in layer_sets["verified_incident"].values() for pid in ids})
    return findings
