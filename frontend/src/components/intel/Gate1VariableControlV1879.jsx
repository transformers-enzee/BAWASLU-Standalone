import {useEffect,useMemo,useState} from 'react';
import {base44} from '@/api/base44Client';
import {useLanguage} from '@/lib/LanguageContext';

const GROUPS=[
  {id:'violation',en:'Potential violations',indo:'Potensi pelanggaran',keys:['potential_issue_categories']},
  {id:'actors',en:'Candidates & involved parties',indo:'Kandidat & pihak terkait',keys:['candidate_names','political_parties','organizations']},
  {id:'jurisdiction',en:'Incident jurisdiction',indo:'Wilayah kejadian',keys:['incident_jurisdiction','geographic_context']},
  {id:'context',en:'Election context',indo:'Konteks pemilu',keys:['relevance']},
  {id:'narrative',en:'Public narrative',indo:'Narasi publik',keys:['topic_labels','narrative','public_concerns','sentiment']},
  {id:'evidence',en:'Evidence assessment',indo:'Penilaian bukti',keys:['evidence_quality','verification_gaps']},
  {id:'timeline',en:'Incident & timeline',indo:'Kejadian & kronologi',keys:['incident_chronology']},
  {id:'followup',en:'Attention & follow-up',indo:'Perhatian & tindak lanjut',keys:['review_priority']},
];
const LABELS={
  potential_issue_categories:'Potential election issue',candidate_names:'People mentioned',
  political_parties:'Political parties',organizations:'Other organizations',
  incident_jurisdiction:'Incident jurisdiction',geographic_context:'Geographic context',
  relevance:'Election relevance',topic_labels:'Topics',narrative:'Narrative',
  public_concerns:'Public concerns',sentiment:'Sentiment',evidence_quality:'Evidence quality',
  verification_gaps:'Verification gaps',incident_chronology:'Incident chronology',
  review_priority:'Review priority',canonical_url:'Original post URL',text_content:'Post content',
  published_at:'Publication date',author_name:'Post author',observed_handle:'Account handle',
  engagement_likes:'Likes',engagement_comments:'Comments',engagement_shares:'Shares',
  engagement_views:'Views',transcript:'Video transcription',translation:'Translation'
};
const OPTIONS={relevance:['RELEVANT','HIGHLY_RELEVANT','UNCERTAIN','IRRELEVANT'],
  sentiment:['POSITIVE','NEUTRAL','NEGATIVE'],
  evidence_quality:['COMPLETE','PARTIAL','MISSING','CONFLICTING','UNVERIFIABLE','DUPLICATE'],
  platform:['youtube','facebook','instagram','tiktok','x','other'],
  provider_fetch_status:['AVAILABLE','PARTIAL','API_FAILED','DELETED','ACCESS_RESTRICTED','NOT_RETURNED']};
const SENSITIVE=new Set(['potential_issue_categories','candidate_names','political_parties','organizations',
  'incident_jurisdiction','geographic_context','incident_chronology','author_name',
  'observed_handle','canonical_url','text_content','country','province','city','incident_date',
  'transcript','translation']);
const REASONS=[
  ['SOURCE_MISMATCH','Source differs from saved value'],
  ['WRONG_ATTRIBUTION','Incorrect identity or jurisdiction'],
  ['MISSING_CONTEXT','Missing or incomplete information'],
  ['OTHER','Other (explain)'],
];
const TITLE=(key)=>LABELS[key]||String(key).replaceAll('_',' ').replace(/\b\w/g,c=>c.toUpperCase());
const decoded=(raw)=>{
  const text=String(raw??'').trim();
  if(!(text.startsWith('[')||text.startsWith('{')))return text;
  try{return JSON.parse(text)}catch{return text}
};
const pretty=(raw)=>{
  const v=decoded(raw);
  const name=(x)=>{
    if(x===null||x===undefined)return '';
    if(typeof x==='string'||typeof x==='number')return String(x).replaceAll('_',' ');
    if(Array.isArray(x))return x.map(name).filter(Boolean).join(', ');
    if(typeof x==='object')return name(x.category_name||x.candidate_name||x.party_name||
      x.name||x.topic||x.label||x.title||x.value||x.summary||'');
    return '';
  };
  return name(v)||'';
};
const present=(raw)=>{
  const s=String(raw??'').trim();
  return !!s&&!['[]','{}','null','unknown','unclassified'].includes(s.toLowerCase());
};
const urlOkay=(raw)=>{
  if(!raw)return true;
  try{const url=new URL(raw);return ['http:','https:'].includes(url.protocol)&&!!url.hostname}catch{return false}
};
const INPUT='intel-input w-full mt-1';

export default function Gate1VariableControlV1879({campaignId,detail,onSaved,onNext}){
  const {language}=useLanguage();
  const T=(en,id)=>language==='id'?id:en;
  const [view,setView]=useState(null);
  const [field,setField]=useState('');
  const [draft,setDraft]=useState('');
  const [unavailable,setUnavailable]=useState(false);
  const [basis,setBasis]=useState('SOURCE_MISMATCH');
  const [explanation,setExplanation]=useState('');
  const [evidence,setEvidence]=useState('');
  const [sourceVerified,setSourceVerified]=useState(false);
  const [search,setSearch]=useState('');
  const [reportField,setReportField]=useState('');
  const [reportNote,setReportNote]=useState('');
  const [reviewerNote,setReviewerNote]=useState('');
  const [busy,setBusy]=useState(false);
  const [error,setError]=useState('');
  const [notice,setNotice]=useState('');

  useEffect(()=>{
    if(String(campaignId)!=='9'||!detail?.result_id||!detail?.qa_audit_only){setView(null);return}
    let active=true;
    setView(null);setField('');setDraft('');setUnavailable(false);setError('');setNotice('');
    base44.inboxHumanReview.fullReview(campaignId,detail.result_id)
      .then(x=>{if(active)setView(x)})
      .catch(e=>{if(active)setError(e.message||'Unable to load effective values')});
    return ()=>{active=false};
  },[campaignId,detail?.result_id,detail?.assessment_id,detail?.source_integrity_digest,detail?.full_field_revision]);

  const data=view?.fields||{};
  const current=(key)=>key==='relevance'?String(detail?.effective_relevance||''):
    key==='sentiment'?String(detail?.effective_sentiment||''):
    String(data[key]?.effective??'');
  const original=(key)=>key==='relevance'?String(detail?.original_ai_relevance||''):
    key==='sentiment'?String(detail?.ai_sentiment||''):
    String(data[key]?.original??'');
  const availableKeys=useMemo(()=>[...new Set([
    ...Object.values(view?.field_groups||{}).flat(),'relevance','sentiment'
  ])],[view?.field_groups]);
  const mainKeys=useMemo(()=>new Set(GROUPS.flatMap(g=>g.keys)),[]);
  const otherKeys=availableKeys.filter(k=>!mainKeys.has(k)).filter(k=>!search||
    TITLE(k).toLowerCase().includes(search.toLowerCase())||
    String(data[k]?.effective||'').toLowerCase().includes(search.toLowerCase()));
  const taskKeys=new Set((view?.missing_review_tasks||[]).map(x=>x.field));
  const hintedKeys=new Set((view?.quality_hints||[]).map(x=>x.field));
  const canEditBase=!!(view?.can_edit&&detail?.can_review_information&&!view?.stale);
  const canEdit=(key)=>{
    if(!canEditBase)return false;
    if((key==='relevance'||key==='sentiment')&&!detail?.can_correct_relevance)return false;
    if((view?.assessment_fields||[]).includes(key))return true;
    if(view?.can_correct_source)return true;
    return !!(view?.can_complete_missing&&(view?.completable_fields||[]).includes(key)
      &&!present(original(key))&&!present(current(key)));
  };
  const selectedCurrent=field?current(field):'';
  const highImpact=SENSITIVE.has(field);
  const baseText=basis==='OTHER'?explanation.trim():
    (REASONS.find(x=>x[0]===basis)?.[1]||'Corrected saved value')+
    (explanation.trim()?' — '+explanation.trim():'');
  const proposed=draft.trim();
  const unchanged=proposed===(present(selectedCurrent)?
    (OPTIONS[field]?String(selectedCurrent).trim():pretty(selectedCurrent)):'');
  const canSave=!!(field&&canEdit(field)&&!busy&&view&&!view.stale&&(
    unavailable?(field!=='relevance'&&field!=='sentiment'&&data[field]?.mode!=='UNAVAILABLE'):
      (proposed.length>0&&!unchanged))&&
    (!highImpact||baseText.length>=10)&&urlOkay(evidence)&&
    (!sourceVerified||evidence.trim().length>0));

  function begin(key){
    if(!canEdit(key))return;
    setField(key);setDraft(present(current(key))?
      (OPTIONS[key]?String(current(key)).trim():pretty(current(key))):'');
    setUnavailable(false);setBasis('SOURCE_MISMATCH');setExplanation('');
    setEvidence('');setSourceVerified(false);setError('');setNotice('');
  }
  function cancel(){setField('');setDraft('');setUnavailable(false);setError('')}
  function auditReason(key){
    return 'Automatic Gate 1 audit note: officer adjusted effective '+TITLE(key)+
      '; original provider and AI values remain unchanged.';
  }
  async function reload(){
    const updated=await base44.inboxHumanReview.fullReview(campaignId,detail.result_id);
    setView(updated);return updated;
  }
  async function save(next=false){
    if(!canSave)return;
    const key=field;
    const text=unavailable?'':proposed;
    const reason=highImpact?baseText:auditReason(key);
    setBusy(true);setError('');setNotice('');
    try{
      if(key==='relevance'||key==='sentiment'){
        await base44.inboxHumanReview.correct(campaignId,detail.result_id,{
          field:key,value:text,
          expected_revision:key==='relevance'?detail.relevance_revision:detail.sentiment_revision,
          expected_assessment_id:detail.assessment_id,
          expected_source_digest:detail.source_integrity_digest,
          reason
        });
      }else{
        await base44.inboxHumanReview.saveFullReview(campaignId,detail.result_id,{
          fields:[{
            field:key,value:text,
            mode:unavailable?'UNAVAILABLE':present(selectedCurrent)?'CORRECTED':'SUPPLEMENTED',
            verification:unavailable?'UNVERIFIED':sourceVerified?'SOURCE_CONFIRMED':
              !present(selectedCurrent)?'OFFICER_SUPPLIED':'UNVERIFIED',
            evidence_url:evidence.trim(),field_reason:reason
          }],
          expected_revision:view.revision,
          expected_assessment_id:detail.assessment_id,
          expected_source_digest:detail.source_integrity_digest,
          reason
        });
      }
      cancel();
      await reload();
      setNotice(T('Value saved to audit history. Original source is protected.',
        'Nilai disimpan dalam riwayat audit. Sumber asli tetap terlindungi.'));
      onSaved?.();
      if(next)onNext?.();
    }catch(e){
      setError(e.message||T('Could not save; refresh the record and try again.',
        'Gagal menyimpan; muat ulang catatan dan coba lagi.'));
    }finally{setBusy(false)}
  }
  async function report(){
    if(!reportField||!view?.can_report_data_error||busy)return;
    setBusy(true);setError('');setNotice('');
    try{
      await base44.inboxHumanReview.reportDataError(campaignId,detail.result_id,{
        field:reportField,note:reportNote.trim(),
        expected_assessment_id:detail.assessment_id,
        expected_source_digest:detail.source_integrity_digest
      });
      await reload();setReportNote('');
      setNotice(T('Data issue reported. No value was changed.','Masalah data dilaporkan. Nilai tidak diubah.'));
    }catch(e){setError(e.message||'Unable to report data issue')}
    finally{setBusy(false)}
  }
  async function secondary(status){
    if(!view?.can_secondary_review||reviewerNote.trim().length<10||busy)return;
    setBusy(true);setError('');setNotice('');
    try{
      await base44.inboxHumanReview.secondFullReview(campaignId,detail.result_id,{
        status,expected_revision:view.revision,
        expected_assessment_id:detail.assessment_id,
        expected_source_digest:detail.source_integrity_digest,
        reason:reviewerNote.trim()
      });
      await reload();setReviewerNote('');
      setNotice(T('Independent review recorded.','Pemeriksaan independen tersimpan.'));
      onSaved?.();
    }catch(e){setError(e.message||'Independent review failed')}
    finally{setBusy(false)}
  }
  function row(key){
    const currentValue=current(key);
    const effective=present(currentValue)?pretty(currentValue):'';
    const flagged=taskKeys.has(key)||hintedKeys.has(key);
    const editor=field===key;
    const editable=canEdit(key);
    return <div key={key} className={'rounded-lg border px-3 py-2.5 space-y-2 '+
      (editor?'border-[#801b24] bg-[#fffafb]':'border-slate-200 bg-white')}
      data-testid={'gate1-variable-'+key}>
      <div className="flex items-start gap-2 justify-between">
        <div className="min-w-0 flex-1 space-y-1">
          <div className="flex flex-wrap items-center gap-2">
            <span className="font-medium text-xs">{TITLE(key)}</span>
            {flagged&&<span className="text-[10px] px-1.5 py-0.5 bg-amber-50 border border-amber-200 text-amber-800 rounded">
              {T('Check value','Periksa nilai')}</span>}
          </div>
          <p className={'text-sm break-words whitespace-pre-wrap '+(effective?'text-slate-800':'text-slate-400')}
            data-testid={'gate1-effective-'+key}>{effective||T('Not identified','Belum teridentifikasi')}</p>
          {data[key]?.basis==='QA_OFFICER_ENRICHMENT'&&<p className="text-xs text-slate-500">
            {T('Officer-adjusted value','Nilai disesuaikan petugas')}</p>}
        </div>
        {editable&&<button type="button" className="intel-ghost text-xs shrink-0" disabled={busy}
          data-testid={'gate1-edit-'+key} onClick={()=>editor?cancel():begin(key)}>
          {editor?T('Close','Tutup'):effective?T('Edit','Ubah'):T('Add','Isi')}
        </button>}
      </div>
      {editor&&<div className="border-t border-slate-200 pt-3 space-y-2" data-testid="gate1-inline-editor">
        <div className="text-xs text-slate-600">
          {T('Original value','Nilai asli')}: <strong className="break-words">
            {present(original(key))?pretty(original(key)):T('Not provided','Tidak tersedia')}</strong>
        </div>
        {OPTIONS[key]?<label className="block text-xs font-semibold">{T('Effective value','Nilai efektif')}
          <select value={draft} onChange={e=>{setDraft(e.target.value);setUnavailable(false)}}
            className={INPUT} data-testid="gate1-inline-value">
            <option value="">{T('Choose value','Pilih nilai')}</option>
            {OPTIONS[key].map(v=><option key={v} value={v}>{v.replaceAll('_',' ')}</option>)}
          </select>
        </label>:['published_at','incident_date'].includes(key)?
          <label className="block text-xs font-semibold">{T('Effective date','Tanggal efektif')}
            <input type="date" className={INPUT} value={draft}
              onChange={e=>{setDraft(e.target.value);setUnavailable(false)}}
              data-testid="gate1-inline-value"/>
          </label>:
          <label className="block text-xs font-semibold">{T('Effective value','Nilai efektif')}
            <textarea rows={['potential_issue_categories','text_content','narrative','transcript'].includes(key)?3:2}
              className={INPUT} value={draft} disabled={unavailable} data-testid="gate1-inline-value"
              placeholder={T('Enter supported value','Masukkan nilai berdasarkan bukti')}
              onChange={e=>{setDraft(e.target.value);setUnavailable(false)}}/>
          </label>}
        {key==='potential_issue_categories'&&<p className="text-xs text-slate-600">
          {T('A reported issue is not a legally proven violation. Raw signal remains in history.',
            'Isu yang dilaporkan bukan pelanggaran terbukti. Sinyal asli tersimpan dalam riwayat.')}</p>}
        {key==='candidate_names'&&<p className="text-xs text-slate-600">
          {T('Being mentioned does not establish candidacy or involvement.',
            'Penyebutan nama tidak membuktikan pencalonan atau keterlibatan.')}</p>}
        {key==='incident_jurisdiction'&&<p className="text-xs text-slate-600">
          {T('Use event location evidence, not the author account location.',
            'Gunakan bukti lokasi kejadian, bukan lokasi akun.')}</p>}
        {!['relevance','sentiment'].includes(key)&&<details className="text-xs">
          <summary className="cursor-pointer">{T('Missing or unavailable?','Nilai tidak tersedia?')}</summary>
          <label className="flex items-center gap-2 mt-2">
            <input type="checkbox" checked={unavailable}
              onChange={e=>{setUnavailable(e.target.checked);if(e.target.checked)setDraft('')}}/>
            {T('Mark effective value unavailable','Tandai nilai efektif tidak tersedia')}
          </label>
        </details>}
        {highImpact&&<label className="block text-xs font-semibold">{T('Correction basis','Dasar koreksi')}
          <select value={basis} onChange={e=>setBasis(e.target.value)} className={INPUT}>
            {REASONS.map(([id,label])=><option key={id} value={id}>{label}</option>)}
          </select>
        </label>}
        {highImpact&&basis==='OTHER'&&<textarea rows={2} className={INPUT}
          value={explanation} onChange={e=>setExplanation(e.target.value)}
          placeholder={T('Short reason (10+ characters)','Alasan singkat (10+ karakter)')}/>}
        <details className="text-xs">
          <summary className="cursor-pointer">{T('Supporting reference (optional)','Referensi pendukung (opsional)')}</summary>
          <input type="url" className={INPUT} value={evidence} onChange={e=>setEvidence(e.target.value)}
            placeholder="https://..."/>
          {evidence&&<label className="flex items-center gap-2 mt-2">
            <input type="checkbox" checked={sourceVerified}
              onChange={e=>setSourceVerified(e.target.checked)}/>
            {T('I checked this reference','Saya memeriksa referensi ini')}
          </label>}
        </details>
        <div className="flex gap-2 flex-wrap">
          <button type="button" className="intel-ghost text-xs" onClick={()=>save(false)}
            disabled={!canSave} data-testid="gate1-inline-save">{busy?T('Saving…','Menyimpan…'):T('Save value','Simpan nilai')}</button>
          {onNext&&<button type="button" className="intel-ghost text-xs" onClick={()=>save(true)}
            disabled={!canSave}>{T('Save & Next','Simpan & Berikutnya')}</button>}
          <button type="button" className="intel-ghost text-xs" onClick={cancel} disabled={busy}>
            {T('Cancel','Batal')}</button>
        </div>
        {highImpact&&<p className="text-xs text-slate-600">
          {T('Significant changes are audited and require independent review where applicable.',
            'Perubahan penting diaudit dan memerlukan pemeriksaan independen bila berlaku.')}</p>}
        {(String(original(key)).startsWith('[')||String(original(key)).startsWith('{'))&&
          <details className="text-xs" data-testid="gate1-raw-original">
            <summary className="cursor-pointer">{T('See original structured value','Lihat nilai terstruktur asli')}</summary>
            <pre className="mt-2 max-h-40 overflow-auto whitespace-pre-wrap break-all">{original(key)}</pre>
          </details>}
      </div>}
    </div>;
  }

  if(String(campaignId)!=='9'||!detail?.qa_audit_only)return null;
  return <section className="space-y-3" data-testid="gate1-variable-control-v1879">
    <div className="flex flex-wrap justify-between gap-2 items-center">
      <div>
        <h3 className="font-semibold text-base">{T('Information Values','Nilai Informasi')}</h3>
        <p className="text-xs text-slate-600">{T('See saved values. Edit only what you want to change.',
          'Lihat nilai yang tersimpan. Ubah hanya yang perlu diperbaiki.')}</p>
      </div>
      <span className="rounded border border-amber-200 bg-amber-50 text-amber-900 px-2 py-1 text-xs">QA only</span>
    </div>
    {error&&<p className="rounded-lg bg-red-50 border border-red-200 text-red-800 text-xs p-3" role="alert">{error}</p>}
    {notice&&<p className="rounded-lg bg-slate-50 border text-xs p-3" role="status">{notice}</p>}
    {!view?<p className="rounded-lg border p-3 text-xs" role="status">
      {T('Loading current effective values…','Memuat nilai efektif…')}</p>:<>
      {!!view.stale&&<p className="rounded-lg bg-amber-50 border border-amber-200 p-3 text-xs">
        {T('Source or assessment changed. Refresh before editing.','Sumber atau penilaian berubah. Muat ulang sebelum mengubah.')}</p>}
      {view.missing_review_tasks?.length>0&&<p className="text-xs text-amber-800" data-testid="gate1-contextual-hints">
        {view.missing_review_tasks.length} {T('important value(s) worth checking; no correction is mandatory without evidence.',
          'nilai penting perlu diperiksa; koreksi tidak wajib tanpa bukti.')}
      </p>}
      <div className="space-y-2" data-testid="gate1-priority-values">
        <p className="font-semibold text-xs text-slate-600">{T('Main BAWASLU information','Informasi utama BAWASLU')}</p>
        {GROUPS.slice(0,3).map(g=><div key={g.id} className="space-y-2">
          <h4 className="font-semibold text-sm">{T(g.en,g.indo)}</h4>
          {g.keys.map(row)}
        </div>)}
      </div>
      <details className="rounded-lg border border-slate-200 p-3" data-testid="gate1-other-intelligence-values">
        <summary className="cursor-pointer font-semibold text-sm">{T('Other intelligence values (5 areas)',
          'Nilai intelijen lainnya (5 bidang)')}</summary>
        <div className="space-y-3 pt-3">
          {GROUPS.slice(3).map(g=><div key={g.id} className="space-y-2">
            <h4 className="text-xs font-semibold text-slate-600">{T(g.en,g.indo)}</h4>
            {g.keys.map(row)}
          </div>)}
        </div>
      </details>
      <details className="rounded-lg border border-slate-200 p-3" data-testid="gate1-all-permitted-values">
        <summary className="cursor-pointer text-sm font-medium">{T('All other values & source data',
          'Nilai lainnya & data sumber')}</summary>
        <div className="pt-3 space-y-2">
          <p className="text-xs text-slate-600">{T('Available for inspection. Authorized source corrections use the same audit trail.',
            'Tersedia untuk diperiksa. Koreksi sumber dengan izin menggunakan audit yang sama.')}</p>
          <input className={INPUT} value={search} onChange={e=>setSearch(e.target.value)}
            placeholder={T('Search by field or value','Cari bidang atau nilai')}
            data-testid="gate1-all-values-search"/>
          {otherKeys.map(row)}
          {otherKeys.length===0&&<p className="text-xs text-slate-500">{T('No matching fields','Tidak ada bidang yang sesuai')}</p>}
          {view.can_report_data_error&&<details className="text-xs border-t pt-2" data-testid="gate1-data-error-report">
            <summary className="cursor-pointer">{T('Report incorrect provider or technical data',
              'Laporkan data penyedia atau teknis yang salah')}</summary>
            <label className="block mt-2">{T('Field','Bidang')}
              <select className={INPUT} value={reportField} onChange={e=>setReportField(e.target.value)}>
                <option value="">{T('Select field','Pilih bidang')}</option>
                {[...(view.source_exception_fields||[]),...(view.technical_read_only_fields||[])].map(k=>
                  <option key={k} value={k}>{TITLE(k)}</option>)}
              </select>
            </label>
            <textarea rows={2} className={INPUT} value={reportNote}
              onChange={e=>setReportNote(e.target.value)}
              placeholder={T('Optional description','Penjelasan opsional')}/>
            <button type="button" className="intel-ghost text-xs mt-2" onClick={report}
              disabled={busy||!reportField}>{T('Record data issue','Catat masalah data')}</button>
          </details>}
        </div>
      </details>
      {view.secondary_review_required&&<details className="rounded-lg border border-amber-200 p-3"
        data-testid="gate1-secondary-review">
        <summary className="cursor-pointer font-medium text-sm">
          {T('Independent check for significant changes','Pemeriksaan independen untuk perubahan penting')}
          {' · '+(view.secondary_review?.status||'PENDING')}
        </summary>
        <p className="text-xs pt-2 text-slate-600">{T('Another authorized officer must review significant changes.',
          'Petugas berwenang lain harus memeriksa perubahan penting.')}</p>
        {view.can_secondary_review&&<div className="space-y-2 pt-2">
          <textarea rows={2} className={INPUT} value={reviewerNote}
            onChange={e=>setReviewerNote(e.target.value)}
            placeholder={T('Independent review basis (10+ characters)','Dasar pemeriksaan independen (10+ karakter)')}/>
          <div className="flex gap-2 flex-wrap">
            <button type="button" className="intel-ghost text-xs" disabled={busy||reviewerNote.trim().length<10}
              onClick={()=>secondary('APPROVED')}>{T('Approve change','Setujui perubahan')}</button>
            <button type="button" className="intel-ghost text-xs" disabled={busy||reviewerNote.trim().length<10}
              onClick={()=>secondary('REJECTED')}>{T('Reject change','Tolak perubahan')}</button>
          </div>
        </div>}
      </details>}
      <details className="rounded-lg border border-slate-200 p-3" data-testid="gate1-variable-audit-history">
        <summary className="cursor-pointer text-sm font-medium">{T('Original values & audit history',
          'Nilai asli & riwayat audit')}</summary>
        <div className="pt-2 space-y-2 text-xs">
          <p>{T('Provider evidence and original AI assessments are preserved. These are QA-only effective values.',
            'Bukti penyedia dan penilaian AI asli dipertahankan. Ini nilai efektif khusus QA.')}</p>
          {(view.history||[]).slice(0,20).map(h=><div key={h.revision} className="border-t pt-2 break-words">
            <strong>#{h.revision}</strong> · {h.actor_id} · {h.at} · {h.reason}
            <p>{h.fields?.map(x=>TITLE(x.field)).join(', ')}</p>
          </div>)}
          {!(view.history||[]).length&&<p>{T('No field changes yet','Belum ada perubahan bidang')}</p>}
        </div>
      </details>
      {!canEditBase&&<p className="text-xs text-slate-600">{detail?.reason_if_not_actionable||
        T('Read-only review; field editing is not enabled for this record.','Tampilan hanya-baca; edit bidang tidak diaktifkan.')}</p>}
    </>}
  </section>;
}
