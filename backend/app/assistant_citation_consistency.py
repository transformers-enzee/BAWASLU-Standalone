"""Read-only citation inventory comparison for the final displayed Assistant answer.

This validates identifiers and citation-list consistency, NOT source truth,
semantic support, PDF page authenticity, or legal currentness.
"""
import re

_REFERENCE = re.compile(r"\[((?:INT|SOCIAL)-[A-Za-z0-9:_-]+|DOC-\d+-P\d+)\]")


def reconcile_citation_inventory(answer, cited_ids, evidence):
    allowed = {str(row.get('record_id')) for row in evidence or []
               if isinstance(row, dict) and row.get('record_id')}
    displayed = list(dict.fromkeys(_REFERENCE.findall(str(answer or ''))))
    metadata = list(dict.fromkeys(str(value) for value in cited_ids or []
                                  if value is not None))
    shown = set(displayed)
    saved = set(metadata)
    result = {
        'displayed_ids': displayed,
        'metadata_ids': metadata,
        'unauthorized_displayed_ids': sorted(shown - allowed),
        'unauthorized_metadata_ids': sorted(saved - allowed),
        'displayed_not_in_metadata': sorted(shown - saved),
        'metadata_not_displayed': sorted(saved - shown),
        'reference_integrity_only': True,
        'claim_truth_verified': False,
        'pdf_page_content_verified': False,
    }
    result['status'] = ('REVIEW_REQUIRED' if any(result[k] for k in (
        'unauthorized_displayed_ids', 'unauthorized_metadata_ids',
        'displayed_not_in_metadata', 'metadata_not_displayed'))
        else 'PASS_IDENTIFIERS_ONLY')
    return result
