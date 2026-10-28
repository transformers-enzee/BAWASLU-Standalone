"""Integration release contracts: sessions, officer gating, canonical lineage.

Static checks ensure critical access-control wiring is present without login
credentials, external API requests or mutations of live evidence.
"""
from pathlib import Path
from app import source_ids
from app import integration_readiness
from app import source_lineage

FRONTEND=Path(__file__).resolve().parents[2]/"frontend"/"src"

def test_source_references_do_not_join_namespaces():
    assert source_ids.canonical_source_id("social",101)=="social:101"
    assert source_ids.canonical_source_id("radar","POST-101")=="radar:POST-101"
    assert source_ids.canonical_candidate_id("2")=="candidate:2"

def test_officer_scoping_remains_enforced():
    source=Path(source_lineage.__file__).read_text(encoding="utf-8")
    assert "_result_in_scope(db,p,row)" in source
    assert 'HTTPException(404,"Source unavailable")' in source
    assert "source_evidence_verified" in source

def test_integration_readiness_never_self_approves_manual_uat():
    source=Path(integration_readiness.__file__).read_text(encoding="utf-8")
    assert '"manual_validation_required":True' in source
    assert '"paid_requests"]=0' in source

def test_authentication_state_and_assistant_history_use_same_session():
    auth=(FRONTEND/"lib"/"AuthContext.jsx").read_text(encoding="utf-8")
    assistant=(FRONTEND/"pages"/"IntelligenceAssistant.jsx").read_text(encoding="utf-8")
    assert "setUser(null)" in auth
    assert "base44.auth.logout('/login')" in auth
    assert "bawaslu_access_token" in assistant
    assert "VITE_API_BASE_URL" in assistant
    assert "response.status===401" in assistant

def test_integration_console_invalidates_cached_protected_data():
    console=(FRONTEND/"pages"/"IntegrationReadiness.jsx").read_text(encoding="utf-8")
    assert "setMetrics(null); setPreview(null); setQueue(null); setConfirm(false)" in console
    assert "National Administrator access is required." in console
    assert "expected_missing:preview.eligible_missing_ids" in console

def test_lineage_checks_both_source_and_intelligence_scope():
    source=Path(source_lineage.__file__).read_text(encoding="utf-8")
    assert "_result_in_scope(db,p,row)" in source
    assert "allowed(p,candidate)" in source

def test_historical_backfill_refuses_duplicate_promotions():
    from scripts import backfill_source_ids
    source=Path(backfill_source_ids.__file__).read_text(encoding="utf-8")
    assert 'len({row["intelligence_id"] for row in rows})!=len(rows)' in source
    assert "expected_missing" in source


def test_social_review_changes_require_human_validation():
    from app import socialcrawl
    source=Path(socialcrawl.__file__).read_text(encoding="utf-8")
    block=source.split("    if action=='review':", 1)[1].split("    if action=='promote':", 1)[0]
    assert "has(p,'human_validation')" in block
    assert "_result_in_scope(db,p,row)" in source
    assert "row.review_state=decision" in block

def test_frontend_route_permissions_cover_inbox_watchlist_and_creation():
    source=(FRONTEND/"App.jsx").read_text(encoding="utf-8")
    readonly=source.split('<Route path="/legacy-home"',1)[0]
    assert readonly.rstrip().endswith('<Route element={<AccessGate permission="view_intelligence" />}>')
    for path in ("/legacy-home", "/watchlist", "/watchlist/:id", "/watchlist/:id/posts", "/inbox", "/intelligence/:id"):
        assert f'path="{path}"' in source
    assert '<Route element={<AccessGate permission="add_intelligence" />}><Route path="/add"' in source


def test_backend_module_boundaries_deny_missing_view_permission():
    from app import socialcrawl, registry
    social=Path(socialcrawl.__file__).read_text(encoding="utf-8")
    watch=Path(registry.__file__).read_text(encoding="utf-8")
    entry=social.split("def social_listening_action(",1)[1].split("    if action in ",1)[0]
    assert "if not has(p,'view_intelligence'): raise PermissionError" in entry
    guard=watch.split("def registry_action(",1)[1].split("    if action=='list':",1)[0]
    assert "if action=='myAccess': return {'access':p}" in guard
    assert "if not has(p,'view_intelligence'): raise PermissionError" in guard

def test_social_promotion_preserves_review_and_canonical_source_ids():
    from app import socialcrawl
    source=Path(socialcrawl.__file__).read_text(encoding="utf-8")
    promote=source.split("    if action=='promote':",1)[1]
    assert "has(p,'add_intelligence')" in promote
    assert "row.review_state not in ('RELEVANT','MONITOR')" in promote
    assert "canonical_source_id('social',row.id)" in promote


def test_supabase_pilot_schema_is_audited_without_paid_calls():
    source=Path(integration_readiness.__file__).read_text(encoding="utf-8")
    assert "to_regclass('pilot_smart_radar.source_posts')" in source
    assert "SELECT COUNT(*) FROM pilot_smart_radar.source_posts" in source
    assert '"smart_radar_pilot_posts"' in source
    assert "separate Supabase project" not in source


def test_smart_radar_source_counts_distinguish_references_from_loaded_posts():
    html=(FRONTEND.parent/"public"/"ui-freeze"/"smart-radar-v6_2.html").read_text(encoding="utf-8")
    assert "f.source_count??f.posts.length" in html
    assert "Original Posts (${f.posts.length} loaded of ${f.source_count??f.posts.length} referenced)" in html
    assert "Do not treat the aggregate count as opened or verified evidence." in html


def test_smart_radar_detail_fetches_original_posts_and_rejects_count_mismatch():
    adapter=(FRONTEND.parent/"public"/"ui-freeze"/"smart-radar-live.js").read_text(encoding="utf-8")
    assert "request('/api/smart-radar/finding/'+encodeURIComponent(id))" in adapter
    assert "Finding evidence count mismatch:" in adapter
    assert "model.posts = (finding.posts||[]).map" in adapter
    assert "View original source" in adapter
