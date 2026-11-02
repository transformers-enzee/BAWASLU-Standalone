"""Command Centre v109.0: grounded player summaries and sentiment/geo lineage."""
from app.inbox_radar import compile_inbox_findings

def post(i,**kw):
    base={'id':str(i),'campaign_id':'1','relevance_label':'RELEVANT','text_content':'Ordinary election post',
    'author_name':'Author '+str(i),'canonical_url':'https://example.org/'+str(i),
    'topic_labels':[],'public_concern_signals':[],'potential_issues':[],'is_flagged':False,
    'sentiment':'UNCLASSIFIED','location_signals':[]}
    base.update(kw)
    return base

def test_violation_summary_describes_actual_source_issue():
    rows=[post(1,is_flagged=True,text_content='Laporan dugaan warga mencoblos lebih dari sekali'),
          post(2,is_flagged=True,text_content='Demo di Bawaslu mengenai kecurangan pemilu')]
    findings=compile_inbox_findings(rows)
    summaries=[f['summary'].lower() for f in findings if 'violations' in f['players']]
    assert len(summaries)==2
    assert any('repeat voting' in summary for summary in summaries)
    assert any('public demonstrations' in summary for summary in summaries)
    assert all('verification' in summary for summary in summaries)

def test_public_concern_uses_saved_officer_description_not_generic_boilerplate():
    row=post(10,public_concern_signals=[{
        'concern':'Voters reported unclear official registration instructions',
        'evidence_quote':'Warga mempertanyakan instruksi pemilih'}])
    f=compile_inbox_findings([row])[0]
    assert 'concerns' in f['players']
    assert 'unclear official registration instructions' in f['summary']
    assert 'need checking' not in f['summary'].lower()

def test_irrelevant_posts_never_contribute_to_dashboard_summaries():
    all_rows=[post(1,is_flagged=True,relevance_label='IRRELEVANT',text_content='Dugaan politik uang'),
              post(2,relevance_label='RELEVANT')]
    f=compile_inbox_findings(all_rows)
    assert len(f)==1
    assert all('violations' not in row['players'] for row in f)

def test_saved_sentiment_and_geography_still_attached_to_same_source():
    row=post(1,sentiment='NEGATIVE',
       location_signals=[{'province':'Nusa Tenggara Timur'}],
       incident_jurisdiction_review={'decision':'UNREVIEWED','incident_jurisdiction_verified':False})
    f=compile_inbox_findings([row])[0]
    assert f['sentiment_counts']=={'NEGATIVE':1}
    assert f['geo_signal_counts']=={'Nusa Tenggara Timur':1}
    assert f['verified_incident_counts']=={}
    assert f['posts'][0]['canonical_source_id']=='social:1'

def test_command_centre_language_toggle_does_not_replace_summary_with_pending():
    from pathlib import Path
    root=Path(__file__).resolve().parents[2]
    locale=(root/'frontend/public/ui-freeze/bawaslu-interface-locale.js').read_text(encoding='utf-8')
    html=(root/'frontend/public/ui-freeze/smart-radar-v6_2.html').read_text(encoding='utf-8')
    assert locale.index("if(cached==='pending')return;") < locale.index("if(typeof cached==='string')")
    assert "if(cached==='failed'){warn();return;}" in locale
    assert "summaryCache.delete(key)" in locale
    assert "data-translation-status" in locale
    assert "Know what is happening. Know what needs your attention." in locale
    assert "#strategy" in locale
    assert '[data-ai-summary]' in locale
    assert 'data-ai-summary' in html
    assert 'bawaslu-interface-locale.js?build=127.0' in html
    assert "summaryCache.set(original,'pending')" in locale
    assert "if(locale!=='id')" in locale

def test_display_translation_reuses_responses_api_without_reassessment(monkeypatch):
    from app.main import translate_saved_presentation
    calls=[]
    class FakeResponse:
        status_code=200
        def raise_for_status(self):pass
        def json(self):return {'status':'completed','output':[{
            'type':'message','content':[{'type':'output_text','text':'Dugaan ini masih memerlukan verifikasi.'}]}]}
    class FakeClient:
        def __enter__(self):return self
        def __exit__(self,*args):pass
        def post(self,url,headers,json):
            calls.append((url,json))
            return FakeResponse()
    monkeypatch.setenv('OPENAI_API_KEY','test-key')
    monkeypatch.setenv('OPENAI_MODEL','gpt-6-luna')
    monkeypatch.setattr('httpx.Client',lambda **kwargs:FakeClient())
    source='This allegation still requires verification.'
    result=translate_saved_presentation({'text':source,'language':'id'},user=object())
    assert result['text']=='Dugaan ini masih memerlukan verifikasi.'
    assert result['translation_only'] is True
    assert calls[0][0].endswith('/responses')
    assert calls[0][1]['model']=='gpt-6-luna'
    assert calls[0][1]['input'][1]['content']==source
    assert 'temperature' not in calls[0][1]

def test_command_centre_saved_issue_title_localization_not_source_rewrite():
    from pathlib import Path
    root=Path(__file__).resolve().parents[2]
    html=(root/'frontend/public/ui-freeze/smart-radar-v6_2.html').read_text(encoding='utf-8')
    locale=(root/'frontend/public/ui-freeze/bawaslu-interface-locale.js').read_text(encoding='utf-8')
    # Three item cards, one finding title, and the source drill-down heading.
    assert html.count('data-ai-title data-i18n-exempt')==5
    assert html.count('data-ai-summary data-i18n-exempt')>=3
    assert "'[data-ai-summary],[data-ai-title]" in locale
    assert 'Ringkasan intelijen · ' in locale
    assert 'Unggahan Pendukung · Buka →' in locale
    assert 'Terjemahan sementara tidak tersedia.' in locale
    # Original post descriptions remain untouched and linked to their source.
    assert '<p>${E(p[2])}</p>' in html
    assert '<p data-ai-title>${E(p[2])}</p>' not in html
