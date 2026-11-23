"""No-cost web-first routing and evidence safeguards; no API/network required."""
from app.assistant_web_first import safe_public_question,safe_web_urls,web_brief_text


def test_web_queries_never_include_internal_source_identifiers():
    assert safe_public_question('What do official sources report about election supervision?')
    for sensitive in ['SOCIAL-1226','INT-2026-0111','DOC-3-P2','ATT-'+'a'*32+'-S1']:
        assert not safe_public_question('Investigate '+sensitive)


def test_only_https_attributable_urls_are_consulted():
    assert safe_web_urls(['https://bawaslu.go.id/id/profil','https://bawaslu.go.id/id/profil',
        'http://example.org/a','https://user:pass@example.org/private',
        'https://localhost/admin'])==['https://bawaslu.go.id/id/profil']


def test_unavailable_web_does_not_claim_live_knowledge():
    assert 'no attributable sources' in web_brief_text(None,'en')
    assert 'belum menghasilkan sumber' in web_brief_text(None,'id')
    assert 'no attributable sources' in web_brief_text({'summary':'unverified','urls':[]},'en')


def test_cited_public_result_remains_concise_and_unmodified():
    sample={'summary':'Decision: verify the official publication, then assign an officer to review.',
            'urls':['https://bawaslu.go.id/id/profil']}
    assert web_brief_text(sample,'en')==sample['summary']
