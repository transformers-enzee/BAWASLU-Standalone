from app.assistant_citation_consistency import reconcile_citation_inventory


def rec(identifier):
    return {'record_id': identifier}


def test_exact_pdf_citation_match():
    value = reconcile_citation_inventory('Rute penugasan [DOC-1-P8].',
                                         ['DOC-1-P8'], [rec('DOC-1-P8')])
    assert value['status'] == 'PASS_IDENTIFIERS_ONLY'
    assert value['pdf_page_content_verified'] is False


def test_extra_displayed_pdf_page_is_flagged():
    value = reconcile_citation_inventory('Halaman [DOC-1-P6] dan [DOC-1-P9].',
                                         ['DOC-1-P6'], [rec('DOC-1-P6'), rec('DOC-1-P9')])
    assert value['displayed_not_in_metadata'] == ['DOC-1-P9']
    assert value['status'] == 'REVIEW_REQUIRED'


def test_unselected_pdf_citation_is_flagged():
    value = reconcile_citation_inventory('Aturan [DOC-99-P7].',
                                         ['DOC-99-P7'], [rec('DOC-1-P7')])
    assert value['unauthorized_displayed_ids'] == ['DOC-99-P7']
    assert value['unauthorized_metadata_ids'] == ['DOC-99-P7']


def test_cited_metadata_without_display_is_flagged():
    value = reconcile_citation_inventory('Rangkuman tanpa sumber.',
                                         ['DOC-1-P6'], [rec('DOC-1-P6')])
    assert value['metadata_not_displayed'] == ['DOC-1-P6']


def test_cross_module_both_types_present():
    value = reconcile_citation_inventory('Kasus [INT-9] dan unggahan [SOCIAL-23].',
                                         ['INT-9','SOCIAL-23'], [rec('INT-9'),rec('SOCIAL-23')])
    assert value['status'] == 'PASS_IDENTIFIERS_ONLY'


def test_cross_module_extra_displayed_source_rejected():
    value = reconcile_citation_inventory('Kasus [INT-9] dan unggahan [SOCIAL-23].',
                                         ['INT-9'], [rec('INT-9'),rec('SOCIAL-23')])
    assert value['displayed_not_in_metadata'] == ['SOCIAL-23']


def test_duplicate_citation_counts_once():
    value = reconcile_citation_inventory('Halaman [DOC-1-P6] dan [DOC-1-P6].',
                                         ['DOC-1-P6','DOC-1-P6'], [rec('DOC-1-P6')])
    assert value['displayed_ids'] == ['DOC-1-P6']
    assert value['status'] == 'PASS_IDENTIFIERS_ONLY'


def test_absent_sources_not_mistaken_for_truth():
    value = reconcile_citation_inventory('Tanpa sumber.', [], [])
    assert value['status'] == 'PASS_IDENTIFIERS_ONLY'
    assert not value['claim_truth_verified']
