"""Regression guards for SmartRadar assistant attachment and access lifecycle.

Static contract tests intentionally avoid connecting to Supabase or calling paid AI.
These complement (not replace) authenticated HTTP integration tests.
"""
import ast
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1] / "app"
FRONTEND = Path(__file__).resolve().parents[2] / "frontend" / "src"

def read(path):
    return path.read_text(encoding="utf-8")

def test_legacy_and_v2_assistant_share_permission_gate():
    tree = ast.parse(read(ROOT / "main.py"))
    fn = next(node for node in ast.walk(tree) if isinstance(node, ast.FunctionDef)
              and node.name == "intelligence_assistant")
    initial = ast.get_source_segment(read(ROOT / "main.py"), fn) or ""
    assert initial.index("if not has(p,'view_intelligence')") < initial.index("if 'analysisMode' not in body")
    assert "accessible=list_intelligence(db,p)" in initial

def test_thread_deletion_removes_private_artifacts_first():
    source = read(ROOT / "assistant_history.py")
    section = source[source.index("def delete_thread("):]
    assert section.index("AssistantResponseFeedback") < section.index("db.delete(row)")
    assert section.index("delete_thread_attachments(db, user.id, row.id)") < section.index("db.delete(row)")

def test_attachment_removal_revokes_active_view_and_exports():
    page = read(FRONTEND / "pages" / "IntelligenceAssistant.jsx")
    composer = read(FRONTEND / "components" / "intel" / "AssistantComposerAttachments.jsx")
    assert "onRemoved={refreshAfterAttachmentRemoval}" in page
    assert "setReviewableIndexes(new Set())" in page[page.index("async function refreshAfterAttachmentRemoval"):page.index("async function removeThread")]
    assert "await onRemoved(item)" in composer
    assert "setMessages(saved.messages||[])" in page

def test_attachment_storage_is_private_and_scan_is_fail_closed():
    source = read(ROOT / "assistant_attachments.py")
    assert "if not host:" in source and "Upload scanner is unavailable" in source
    assert "user_id=user.id" in source
    assert "_check_scope(row,p)" in source
    assert "shared_case_record" in source
