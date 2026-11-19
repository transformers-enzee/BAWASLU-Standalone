from app.assistant_pdf_quote_audit import audit_pdf_quoted_passages


def page(id, text):
    return {'record_id': id, 'record_type': 'PDF_KNOWLEDGE', 'source_excerpt': text}


def test_exact_quote_in_immediately_cited_page():
    result = audit_pdf_quoted_passages(
        'Dokumen menyebut “petugas memverifikasi lokasi kejadian” [DOC-1-P8].',
        [page('DOC-1-P8', 'Sebelum penugasan, petugas memverifikasi lokasi kejadian.')])
    assert result['status'] == 'PASS_QUOTE_TEXT_ONLY'
    assert not result['semantic_support_verified']


def test_wrong_page_quote_is_flagged():
    result = audit_pdf_quoted_passages(
        '“petugas memverifikasi lokasi kejadian” [DOC-1-P6]',
        [page('DOC-1-P6', 'Prosedur tindak lanjut hukum secara terpisah.')])
    assert result['issues'][0]['reason'] == 'QUOTED_TEXT_NOT_IN_SELECTED_PAGE'


def test_unknown_pdf_reference_is_flagged():
    result = audit_pdf_quoted_passages(
        '“petugas memverifikasi lokasi kejadian” [DOC-99-P8]',
        [page('DOC-1-P8', 'petugas memverifikasi lokasi kejadian')])
    assert result['issues'][0]['reason'] == 'PAGE_NOT_SELECTED'


def test_whitespace_normalization_in_quote():
    result = audit_pdf_quoted_passages(
        '"Verifikasi   lokasi kejadian" [DOC-1-P8]',
        [page('DOC-1-P8', 'Verifikasi\nlokasi kejadian')])
    assert result['status'] == 'PASS_QUOTE_TEXT_ONLY'


def test_no_quotes_is_not_a_verified_pass():
    result = audit_pdf_quoted_passages(
        'Penugasan mensyaratkan verifikasi lokasi [DOC-1-P8]',
        [page('DOC-1-P8', 'verifikasi lokasi')])
    assert result['status'] == 'NOT_APPLICABLE'
    assert result['all_claims_checked'] is False


def test_empty_excerpt_requires_review():
    result = audit_pdf_quoted_passages(
        '"Verifikasi lokasi" [DOC-1-P8]',
        [page('DOC-1-P8', '')])
    assert result['issues'][0]['reason'] == 'SOURCE_EXCERPT_EMPTY'


def test_quote_cited_to_social_record_not_treated_as_pdf():
    result = audit_pdf_quoted_passages(
        '"Verifikasi lokasi" [SOCIAL-24]',
        [page('DOC-1-P8', 'Verifikasi lokasi')])
    assert result['status'] == 'NOT_APPLICABLE'


def test_nonadjacent_quote_is_not_assumed_attributable():
    result = audit_pdf_quoted_passages(
        '"Verifikasi lokasi" adalah suatu frasa. [DOC-1-P8]',
        [page('DOC-1-P8', 'Verifikasi lokasi')])
    assert result['status'] == 'NOT_APPLICABLE'
