"""Read-only Shahrin error summaries must never surface sealed source data."""
import pytest
from app.qa_saved_accuracy import CONFUSION_QUERY,QUERY,qa_history_summary
from app.access import default_permissions

def officer(role='National Administrator'):
    return {'id':'11','role':role,'status':'Active',
        'permissions':default_permissions(role)}

def test_confusion_query_excludes_sealed_holdout_and_source_text():
    sql=str(CONFUSION_QUERY)
    assert "NOT ILIKE '%holdout%'" in sql
    assert "GROUP BY prompt_version,model,cohort" in sql
    assert "LIMIT 30" in sql
    assert "h.source_url=sp.source_url" in sql
    assert "h.original_excel_row=sp.original_excel_row" in sql
    assert "message_original" not in sql
    assert "message_original" not in str(QUERY)

def test_unauthorized_officer_cannot_read_aggregated_shahrin_errors():
    class UnusedDatabase:
        def execute(self,*_):raise AssertionError('Should not query')
    with pytest.raises(PermissionError):
        qa_history_summary(UnusedDatabase(),officer('Viewer'))
