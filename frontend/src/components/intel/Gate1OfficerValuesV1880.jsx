import {useEffect,useMemo,useState} from 'react';
import {base44} from '@/api/base44Client';
import {useLanguage} from '@/lib/LanguageContext';

// Officer workbench has seven primary information areas. Technical fields stay stored
// but do not appear as routine tasks. Merged areas still edit their original keys.
const PRIMARY=[
  {id:'actors',label:'Involved parties',indo:'Pihak terkait',keys:['candidate_names','political_parties','organizations']},
  {id:'jurisdiction',label:'Incident jurisdiction',indo:'Wilayah kejadian',keys:['incident_jurisdiction','geographic_context']},
  {id:'narrative',label:'Main issue & narrative',indo:'Isu utama & narasi',keys:['topic_labels','narrative','public_concerns']},
  {id:'evidence',label:'Evidence status',indo:'Status bukti',keys:['evidence_quality','verification_gaps']},
];
const INFO_TYPES=[
  ['POTENTIAL_ELECTORAL_VIOLATION','Potential electoral issue'],
  ['CANDIDATE_ACTIVITY','Candidate activity'],
  ['ELECTION_ADMINISTRATION','Election administration'],
  ['PUBLIC_CONCERN','Public concern'],
  ['ELECTORAL_DISPUTE','Election dispute'],
  ['GENERAL_ELECTION_INTELLIGENCE','General election intelligence'],
  ['OTHER','Other election intelligence'],
];
const SOURCE_SUMMARY=['platform','author_name','published_at','canonical_url','text_content'];
const ROUTINE_HIDE=new Set([
  'relevance_explanation','sentiment_explanation','missing_data','duplicate_reference',
  'officer_notes','provider_fetch_status','review_priority','engagement_likes',
  'engagement_comments','engagement_shares','engagement_views','transcript','translation',
  'language'
]);
const LABELS={
  information_type:'Information type',potential_issue_categories:'Potential election issue',candidate_names:'People mentioned',
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
const OPTIONS={information_type:INFO_TYPES.map(x=>x[0]),relevance:['RELEVANT','HIGHLY_RELEVANT','UNCERTAIN','IRRELEVANT'],
  sentiment:['POSITIVE','NEUTRAL','NEGATIVE'],
  evidence_quality:['COMPLETE','PARTIAL','MISSING','CONFLICTING','UNVERIFIABLE','DUPLICATE'],
  platform:['youtube','facebook','instagram','tiktok','x','other'],
  provider_fetch_status:['AVAILABLE','PARTIAL','API_FAILED','DELETED','ACCESS_RESTRICTED','NOT_RETURNED']};
const SENSITIVE=new Set(['information_type','potential_issue_categories','candidate_names','political_parties','organizations',
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
const infoLabel=(key)=>INFO_TYPES.find(x=>x[0]===key)?.[1]||String(key||'').replaceAll('_',' ');
const formatDate=(raw)=>{
  const d=new Date(raw);
  return Number.isNaN(d.valueOf())?String(raw):d.toLocaleString('en-GB',{
    timeZone:'UTC',day:'2-digit',month:'short',year:'numeric',hour:'2-digit',minute:'2-digit'
  })+' UTC';
};
const formatGeo=(raw)=>{
  const text=String(raw??'');
  const json=decoded(text);
  const source=typeof json==='object'&&json&&!Array.isArray(json)?json:null;
  const match=(key)=>text.match(new RegExp("[\\\"']"+key+"[\\\"']\\s*:\\s*[\\\"']?([^\\\"',}]+)","i"))?.[1]?.trim()||'';
  const code=(source?.value||match('value'));
  const confidence=source?.confidence??Number(match('confidence'));
  const from=source?.source||match('source');
  if(!code)return '';
  const name=code==='ID'?'Indonesia':code;
  const pct=Number.isFinite(Number(confidence))&&String(confidence)!==''?
    ' · '+Math.round(Number(confidence)*100)+'% confidence':'';
  return name+(from?' · '+from:'')+pct;
};


export default function Gate1OfficerValuesV1880({campaignId,detail,onSaved,onNext}){
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
  const [openArea,setOpenArea]=useState('');
  const [adminOverride,setAdminOverride]=useState(false);
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
  const mainKeys=useMemo(()=>new Set([
    'relevance','information_type','potential_issue_categories','sentiment','incident_chronology',
    ...PRIMARY.flatMap(g=>g.keys)
  ]),[]);
  const sourceKeys=(view?.source_exception_fields||[]);
  const diagnosticsKeys=availableKeys.filter(k=>!mainKeys.has(k)&&!SOURCE_SUMMARY.includes(k));
  const filteredSourceKeys=[...new Set([...SOURCE_SUMMARY,...sourceKeys,...diagnosticsKeys])].filter(k=>
    !search||TITLE(k).toLowerCase().includes(search.toLowerCase())||
    String(data[k]?.effective||'').toLowerCase().includes(search.toLowerCase()));
  const infoType=current('information_type');
  const hasIssue=present(current('potential_issue_categories'));
  const hasNarrative=['topic_labels','narrative','public_concerns'].some(k=>present(current(k)));
  const showSentiment=present(current('sentiment'))&&(infoType==='PUBLIC_CONCERN'||hasNarrative||!hasIssue);
  const showChronology=present(current('incident_chronology'))||
    (view?.missing_review_tasks||[]).some(x=>x.area==='timeline');
  const infoSuggestion=hasIssue?'POTENTIAL_ELECTORAL_VIOLATION':
    hasNarrative?'PUBLIC_CONCERN':'';

  const taskKeys=new Set((view?.missing_review_tasks||[]).map(x=>x.field));
  const hintedKeys=new Set((view?.quality_hints||[]).map(x=>x.field));
  const canEditBase=!!(view?.can_edit&&detail?.can_review_information&&!view?.stale);
  const canEdit=(key)=>{
    if(!canEditBase)return false;
    if((key==='relevance'||key==='sentiment')&&!detail?.can_correct_relevance)return false;
    if((view?.assessment_fields||[]).includes(key))return true;
    // Source/provider and technical fields are inspection-only unless the officer
    // deliberately opens the advanced exception path.
    if(!adminOverride&&sourceKeys.includes(key))return false;
    if(!adminOverride&&ROUTINE_HIDE.has(key))return false;
    if(view?.can_correct_source&&adminOverride)return true;
    return !!(adminOverride&&view?.can_complete_missing&&
      (view?.completable_fields||[]).includes(key)&&
      !present(original(key))&&!present(current(key)));
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
  const display=(key,raw)=>{
    if(!present(raw))return '';
    if(key==='information_type')return infoLabel(String(raw).trim());
    if(key==='published_at'||key==='incident_date')return formatDate(raw);
    if(['country','province','city'].includes(key)){
      const geo=formatGeo(raw);
      if(geo)return geo;
    }
    return pretty(raw)||String(raw);
  };
  const compact=(v,n=135)=>v.length>n?v.slice(0,n-1)+'…':v;
  function row(key,{readOnly=false}={}){
    const value=current(key);
    const effective=display(key,value);
    const flagged=taskKeys.has(key)||hintedKeys.has(key);
    const editor=field===key;
    const editable=!readOnly&&canEdit(key);
    const emptyLabel=key==='information_type'?
      T('Not classified','Belum diklasifikasi'):
      key==='potential_issue_categories'?T('No issue assessed','Belum ada isu dinilai'):
      T('Not recorded','Belum dicatat');
    return <div key={key} className={'border-b border-slate-100 py-2.5 space-y-2 '+
      (editor?'rounded-md bg-[#fffafb] px-2 -mx-2':'')}
      data-testid={'gate1-variable-'+key}>
      <div className="flex gap-2 items-center justify-between min-w-0">
        <div className="min-w-0 flex-1">
          <div className="flex gap-2 items-center flex-wrap">
            <p className="text-xs text-slate-500">{TITLE(key)}</p>
            {flagged&&<span className="text-[10px] rounded bg-amber-50 text-amber-900 px-1.5 py-0.5">
              {T('Check','Periksa')}</span>}
          </div>
          <p className={'text-sm leading-5 break-words '+(effective?'text-slate-900':'text-slate-400')}
            data-testid={'gate1-effective-'+key}
            title={effective||emptyLabel}>{effective?compact(effective,150):emptyLabel}</p>
          {data[key]?.basis==='QA_OFFICER_ENRICHMENT'&&<span className="text-[10px] text-slate-500">
            {T('Officer-adjusted','Disesuaikan petugas')}</span>}
          {key==='information_type'&&!effective&&infoSuggestion&&<span className="block text-[11px] text-slate-500">
            {T('Suggested from saved context','Saran dari konteks tersimpan')}: {infoLabel(infoSuggestion)}
          </span>}
        </div>
        {editable&&<button type="button" className="intel-ghost text-xs shrink-0"
          disabled={busy} data-testid={'gate1-edit-'+key}
          onClick={()=>editor?cancel():begin(key)}>
          {editor?T('Close','Tutup'):T('Edit','Ubah')}
        </button>}
      </div>
      {editor&&<div className="border-t border-rose-100 pt-2 space-y-2" data-testid="gate1-inline-editor">
        <div className="text-xs text-slate-600">
          {T('Original value','Nilai asli')}: <strong className="break-words">
            {present(original(key))?compact(display(key,original(key)),180):T('Not provided','Tidak tersedia')}</strong>
        </div>
        {OPTIONS[key]?<label className="block text-xs font-semibold">
          {T('Effective value','Nilai efektif')}
          <select value={draft} onChange={e=>{setDraft(e.target.value);setUnavailable(false)}}
            className={INPUT} data-testid="gate1-inline-value">
            <option value="">{T('Choose value','Pilih nilai')}</option>
            {OPTIONS[key].map(v=><option key={v} value={v}>
              {key==='information_type'?infoLabel(v):v.replaceAll('_',' ')}
            </option>)}
          </select>
        </label>:key==='incident_date'?
          <label className="block text-xs font-semibold">{T('Incident date','Tanggal kejadian')}
            <input type="date" className={INPUT} value={draft.slice(0,10)}
              onChange={e=>{setDraft(e.target.value);setUnavailable(false)}}
              data-testid="gate1-inline-value"/>
          </label>:
          <label className="block text-xs font-semibold">{T('Effective value','Nilai efektif')}
            <textarea rows={['potential_issue_categories','text_content','narrative'].includes(key)?3:2}
              className={INPUT} value={draft} disabled={unavailable}
              data-testid="gate1-inline-value"
              placeholder={T('Enter an evidence-supported value','Masukkan nilai berdasarkan bukti')}
              onChange={e=>{setDraft(e.target.value);setUnavailable(false)}}/>
          </label>}
        {key==='potential_issue_categories'&&<p className="text-xs text-slate-500">
          {T('A reported issue is not a proven electoral violation.','Isu yang dilaporkan bukan pelanggaran terbukti.')}</p>}
        {key==='candidate_names'&&<p className="text-xs text-slate-500">
          {T('Mentioned people are not necessarily candidates or accused parties.',
            'Nama yang disebut belum tentu kandidat atau pihak terduga.')}</p>}
        {key==='incident_jurisdiction'&&<p className="text-xs text-slate-500">
          {T('Use evidence about the event, not the social account location.',
            'Gunakan bukti lokasi kejadian, bukan lokasi akun.')}</p>}
        {!['relevance','sentiment'].includes(key)&&<details className="text-xs">
          <summary className="cursor-pointer">{T('Value unavailable?','Nilai tidak tersedia?')}</summary>
          <label className="flex items-center gap-2 mt-2">
            <input type="checkbox" checked={unavailable}
              onChange={e=>{setUnavailable(e.target.checked);if(e.target.checked)setDraft('')}}/>
            {T('Mark effective value unavailable','Tandai nilai tidak tersedia')}
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
          <button type="button" className="intel-ghost text-xs"
            disabled={!canSave} data-testid="gate1-inline-save" onClick={()=>save(false)}>
            {busy?T('Saving…','Menyimpan…'):T('Save value','Simpan nilai')}</button>
          {onNext&&<button type="button" className="intel-ghost text-xs"
            disabled={!canSave} onClick={()=>save(true)}>{T('Save & Next','Simpan & Berikutnya')}</button>}
          <button type="button" className="intel-ghost text-xs" disabled={busy} onClick={cancel}>
            {T('Cancel','Batal')}</button>
        </div>
        {highImpact&&<p className="text-xs text-slate-600">
          {T('Significant changes may require independent review. Original values stay protected.',
            'Perubahan penting dapat memerlukan pemeriksaan independen. Nilai asli terlindungi.')}</p>}
        {(String(original(key)).startsWith('[')||String(original(key)).startsWith('{'))&&
          <details className="text-xs" data-testid="gate1-raw-original">
            <summary className="cursor-pointer">{T('Full original value','Nilai asli lengkap')}</summary>
            <pre className="mt-2 max-h-40 overflow-auto whitespace-pre-wrap break-all">{original(key)}</pre>
          </details>}
      </div>}
    </div>;
  }
  function area(group){
    const expanded=openArea===group.id;
    const values=group.keys.map(k=>display(k,current(k))).filter(Boolean);
    const summary=values.length?compact(values.join(' · '),130):
      T('No applicable value recorded','Belum ada nilai yang relevan');
    return <div key={group.id} className="border-b border-slate-100 py-2.5" data-testid={'gate1-area-'+group.id}>
      <button type="button" className="w-full text-left flex justify-between items-center gap-2"
        aria-expanded={expanded} onClick={()=>setOpenArea(expanded?'':group.id)}>
        <span className="min-w-0 flex-1">
          <span className="block text-xs text-slate-500">{T(group.label,group.indo)}</span>
          <span className={'block text-sm break-words '+(values.length?'text-slate-900':'text-slate-400')}>
            {summary}</span>
        </span>
        <span className="shrink-0 text-xs text-[#801b24]">{expanded?T('Close','Tutup'):T('View / Edit','Lihat / Ubah')}</span>
      </button>
      {expanded&&<div className="pl-3 mt-2 border-l-2 border-slate-100" data-testid={'gate1-area-details-'+group.id}>
        {group.keys.map(k=>row(k))}
      </div>}
    </div>;
  }

  if(String(campaignId)!=='9'||!detail?.qa_audit_only)return null;
  return <section className="space-y-2" data-testid="gate1-officer-values-v1880">
    <div className="flex items-center justify-between gap-2">
      <div>
        <h3 className="font-semibold text-base">{T('Intelligence Values','Nilai Intelijen')}</h3>
        <p className="text-xs text-slate-500">{T('Current values. Edit only when needed.','Nilai yang tersimpan. Ubah hanya jika diperlukan.')}</p>
      </div>
      <span className="text-[10px] rounded border border-amber-200 bg-amber-50 px-2 py-1 text-amber-900">QA only</span>
    </div>
    {error&&<p className="text-xs rounded bg-red-50 border border-red-200 p-2" role="alert">{error}</p>}
    {notice&&<p className="text-xs rounded bg-slate-50 border p-2" role="status">{notice}</p>}
    {!view?<p className="text-xs border rounded p-3" role="status">{T('Loading current values…','Memuat nilai…')}</p>:<>
      {view.stale&&<p className="text-xs rounded border border-amber-200 bg-amber-50 p-2">{T('The source changed; refresh before editing.','Sumber berubah; muat ulang sebelum mengubah.')}</p>}
      {(view?.missing_review_tasks||[]).length>0&&<p className="text-xs text-amber-800" data-testid="gate1-contextual-hints">
        {T('Some source values may need checking. Empty fields do not automatically require completion.','Beberapa nilai mungkin perlu diperiksa. Bidang kosong tidak selalu wajib dilengkapi.')}</p>}
      <div className="rounded-lg border border-slate-200 px-3 py-1" data-testid="gate1-essential-values">
        {row('relevance')}
        {row('information_type')}
        {row('potential_issue_categories')}
        {PRIMARY.map(area)}
      </div>
      {(showSentiment||showChronology)&&<details className="rounded-lg border border-slate-200 p-3" data-testid="gate1-contextual-values">
        <summary className="text-sm font-medium cursor-pointer">{T('Additional relevant context','Konteks terkait lainnya')}</summary>
        <div className="pt-2">{showSentiment&&row('sentiment')}{showChronology&&row('incident_chronology')}</div>
      </details>}
      <details className="rounded-lg border border-slate-200 p-3" data-testid="gate1-source-evidence">
        <summary className="text-sm font-medium cursor-pointer">{T('Source evidence & original data','Bukti sumber & data asli')}</summary>
        <div className="pt-2 space-y-2">
          <p className="text-xs text-slate-500">{T('Provider values are read-only by default. Original evidence is preserved.',
            'Nilai penyedia hanya-baca secara bawaan. Bukti asli tetap tersimpan.')}</p>
          {SOURCE_SUMMARY.map(k=>row(k,{readOnly:!adminOverride}))}
          <details className="border-t border-slate-100 pt-2 text-xs" data-testid="gate1-provider-metadata">
            <summary className="cursor-pointer">{T('Other source & technical metadata','Metadata sumber dan teknis lainnya')}</summary>
            <div className="pt-2 space-y-2">
              <input className={INPUT} value={search} onChange={e=>setSearch(e.target.value)}
                data-testid="gate1-all-values-search" placeholder={T('Search source fields','Cari bidang sumber')}/>
              {filteredSourceKeys.filter(k=>!SOURCE_SUMMARY.includes(k)).map(k=>row(k,{readOnly:!adminOverride}))}
              {filteredSourceKeys.filter(k=>!SOURCE_SUMMARY.includes(k)).length===0&&
                <p className="text-slate-500">{T('No matching fields','Tidak ada bidang yang cocok')}</p>}
            </div>
          </details>
          {view.can_correct_source&&<details className="text-xs border-t border-slate-100 pt-2" data-testid="gate1-authorized-overrides">
            <summary className="cursor-pointer">{T('Authorized source / technical correction','Koreksi sumber / teknis berwenang')}</summary>
            <p className="text-slate-500 pt-2">{T('Only correct a verified mismatch. Every exception is audited.','Hanya perbaiki kesalahan yang terverifikasi. Semua pengecualian diaudit.')}</p>
            <label className="flex gap-2 items-center mt-2">
              <input type="checkbox" checked={adminOverride} onChange={e=>{setAdminOverride(e.target.checked);cancel()}}/>
              {T('Enable authorized exception editing','Aktifkan koreksi pengecualian berwenang')}
            </label>
            {adminOverride&&<p className="text-amber-800 pt-2">{T('Source and technical fields now offer Edit. Independent review still applies.','Bidang sumber dan teknis dapat diubah. Pemeriksaan independen tetap berlaku.')}</p>}
          </details>}
          {view.can_report_data_error&&<details className="text-xs border-t border-slate-100 pt-2" data-testid="gate1-data-error-report">
            <summary className="cursor-pointer">{T('Report incorrect provider or technical data','Laporkan data sumber atau teknis yang salah')}</summary>
            <label className="block mt-2">{T('Field','Bidang')}
              <select className={INPUT} value={reportField} onChange={e=>setReportField(e.target.value)}>
                <option value="">{T('Choose field','Pilih bidang')}</option>
                {[...(view.source_exception_fields||[]),...(view.technical_read_only_fields||[])].map(k=>
                  <option key={k} value={k}>{TITLE(k)}</option>)}
              </select>
            </label>
            <textarea className={INPUT} rows={2} value={reportNote} onChange={e=>setReportNote(e.target.value)}
              placeholder={T('Optional context','Keterangan opsional')}/>
            <button type="button" className="intel-ghost text-xs mt-2" onClick={report}
              disabled={busy||!reportField}>{T('Record data issue','Catat masalah')}</button>
          </details>}
        </div>
      </details>
      {view.secondary_review_required&&view.secondary_review?.status==='PENDING'&&
        <details className="rounded-lg border border-amber-200 p-3" data-testid="gate1-secondary-review">
          <summary className="cursor-pointer text-sm font-medium">
            {T('One change awaits independent review','Satu perubahan menunggu pemeriksaan independen')}
          </summary>
          <p className="text-xs text-slate-600 mt-2">
            {T('An authorized second officer must review the significant change. Original data remains protected.',
              'Petugas kedua yang berwenang perlu meninjau perubahan penting. Data asli terlindungi.')}
          </p>
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
        <summary className="cursor-pointer text-sm font-medium">{T('Value changes & audit history',
          'Perubahan nilai & riwayat audit')}</summary>
        <div className="pt-2 space-y-2 text-xs">
          <p>{T('Original provider and AI data are retained. These corrections are QA-only effective values.',
            'Data asli penyedia dan AI tetap tersimpan. Koreksi ini hanya untuk nilai efektif QA.')}</p>
          {view.secondary_review_required&&<p>
            {T('Independent check','Pemeriksaan independen')}: <strong>{view.secondary_review?.status||'PENDING'}</strong>
            {view.secondary_review?.reviewer_id?' · '+T('Reviewer','Pemeriksa')+' '+view.secondary_review.reviewer_id:''}
          </p>}
          {(view.history||[]).slice(0,20).map(h=><div key={h.revision} className="border-t pt-2 space-y-1 break-words">
            <p><strong>#{h.revision}</strong> · {T('Officer','Petugas')} {h.actor_id} · {h.at}
              {h.stale?' · '+T('Older source version','Versi sumber lama'):''}</p>
            {(h.fields||[]).map((x,i)=><div key={i}>
              <strong>{TITLE(x.field)}</strong>
              <p className="text-slate-600">{T('Previous','Sebelumnya')}: {compact(display(x.field,x.previous||''),180)||'—'}</p>
              <p>{T('New value','Nilai baru')}: {compact(display(x.field,x.value||''),180)||T('Unavailable','Tidak tersedia')}</p>
              {x.verification&&<span className="text-slate-500">{x.verification}</span>}
            </div>)}
            {h.reason&&<p className="text-slate-500">{T('Basis','Dasar')}: {h.reason}</p>}
          </div>)}
          {!(view.history||[]).length&&<p>{T('No field changes yet','Belum ada perubahan bidang')}</p>}
        </div>
      </details>
      {!canEditBase&&<p className="text-xs text-slate-600">{detail?.reason_if_not_actionable||
        T('Read-only review; field editing is not enabled for this record.','Tampilan hanya-baca; edit bidang tidak diaktifkan.')}</p>}
    </>}
  </section>;
}
