"""Ensure Radar route is matched before the catchall canonical ID resolver."""
from fastapi.routing import APIRoute
from app.source_lineage import router

def test_actual_fastapi_route_order():
 paths=[r.path for r in router.routes if isinstance(r,APIRoute)]
 assert paths.index('/api/source-lineage/inbox-radar-feed/{campaign_id}') < paths.index('/api/source-lineage/{reference:path}')
 from starlette.routing import Match
 scope={'type':'http','method':'GET','path':'/api/source-lineage/inbox-radar-feed/1','root_path':'','headers':[],'query_string':b''}
 matched=[r.endpoint.__name__ for r in router.routes if isinstance(r,APIRoute) and r.matches(scope)[0]==Match.FULL]
 assert matched
 assert matched[0]=='inbox_radar_feed'
