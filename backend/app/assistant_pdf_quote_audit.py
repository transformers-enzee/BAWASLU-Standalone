"""Conservative, read-only checks of *explicit quotations* next to PDF citations.

A citation identifier alone is not proof of support. Matching a verbatim quote
to the selected page excerpt proves only lexical presence, never semantics,
document authenticity, legal authority, or currentness.
"""
import re

_QUOTE_WITH_PDF = re.compile(
    r'["“]([^"”\n]{12,260})["”]\s*(?:\[(DOC-\d+-P\d+)\])',
    re.I,
)
_SPACES = re.compile(r'\s+')


def _normalized(value):
    return _SPACES.sub(' ', str(value or '')).strip().casefold()


def audit_pdf_quoted_passages(answer, evidence):
    pages = {
        str(row.get('record_id')): row
        for row in evidence or []
        if isinstance(row, dict)
        and row.get('record_type') == 'PDF_KNOWLEDGE'
        and re.fullmatch(r'DOC-\d+-P\d+', str(row.get('record_id') or ''))
    }
    matched = []
    issues = []
    for occurrence in _QUOTE_WITH_PDF.finditer(str(answer or '')):
        quote, ref = occurrence.groups()
        page = pages.get(ref)
        if page is None:
            issues.append({'page_id': ref, 'reason': 'PAGE_NOT_SELECTED'})
            continue
        source = _normalized(page.get('source_excerpt'))
        if not source:
            issues.append({'page_id': ref, 'reason': 'SOURCE_EXCERPT_EMPTY'})
        elif _normalized(quote) not in source:
            issues.append({'page_id': ref, 'reason': 'QUOTED_TEXT_NOT_IN_SELECTED_PAGE'})
        else:
            matched.append(ref)
    return {
        'status': ('REVIEW_REQUIRED' if issues else
                   'PASS_QUOTE_TEXT_ONLY' if matched else 'NOT_APPLICABLE'),
        'checked_quotes': len(matched) + len(issues),
        'matching_quote_page_ids': matched,
        'issues': issues,
        'scope': 'IMMEDIATELY_CITED_EXPLICIT_PDF_QUOTES_ONLY',
        'all_claims_checked': False,
        'semantic_support_verified': False,
        'legal_currentness_verified': False,
        'source_text_is_complete_verified': False,
    }
