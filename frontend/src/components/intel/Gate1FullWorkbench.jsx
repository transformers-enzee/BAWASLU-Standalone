import {useEffect,useMemo,useRef,useState} from 'react';
import {base44} from '@/api/base44Client';
import {useLanguage} from '@/lib/LanguageContext';

// Keep all source/technical data available for inspection, not routine modification.
const ASSESSMENT_GROUPS=[
  {id:'violation',en:'Potential violations',idLabel:'Potensi pelanggaran',priority:'P1',fields:['potential_issue_categories']},
  {id:'actors',en:'Candidates & involved parties',idLabel:'Kandidat & pihak terkait',priority:'P1',fields:['candidate_names','political_parties','organizations']},
  {id:'jurisdiction',en:'Incident jurisdiction',idLabel:'Wilayah kejadian',priority:'P1',fields:['incident_jurisdiction','geographic_context']},
  {id:'relevance',en:'Election relevance',idLabel:'Relevansi pemilu',priority:'P2',fields:['relevance']},
  {id:'verification',en:'Evidence verification',idLabel:'Verifikasi bukti',priority:'P2',fields:['evidence_quality','verification_gaps']},
  {id:'timeline',en:'Incident & timeline',idLabel:'Kejadian & kronologi',priority:'P2',fields:['incident_chronology']},
  {id:'narrative',en:'Public narrative & issues',idLabel:'Narasi & isu publik',priority:'P2',fields:['topic_labels','narrative','public_concerns','sentiment']},
  {id:'attention',en:'Attention & follow-up',idLabel:'Perhatian & tindak lanjut',priority:'P2',fields:['review_priority']},
];
const ASSESSMENT_FIELDS=ASSESSMENT_GROUPS.flatMap(g=>g.fields);
const SOURCE_EXCEPTION_FIELDS=['platform','content_type','author_name','observed_handle','published_at',
  'canonical_url','text_content','language','country','province','city','location_basis','incident_date'];
const TECHNICAL_READ_ONLY_FIELDS=['transcript','translation','engagement_likes','engagement_comments',
  'engagement_shares','engagement_views','provider_fetch_status','duplicate_reference','verification_gaps',
  'relevance_explanation','sentiment_explanation','public_concerns','organizations','geographic_context',
  'missing_data','officer_notes'];

const SUPPORTED_PLATFORMS=['youtube','facebook','instagram','tiktok','x','other'];
const platformForUrl=(value)=>{try{const h=new URL(value).hostname.toLowerCase();const domains={youtube:['youtube.com','youtu.be'],facebook:['facebook.com','fb.watch'],instagram:['instagram.com'],tiktok:['tiktok.com'],x:['x.com','twitter.com']};return Object.entries(domains).find(([,hosts])=>hosts.some(d=>h===d||h.endsWith('.'+d)))?.[0]||''}catch{return ''}};
const CLASSIFICATIONS={
  relevance:['RELEVANT','HIGHLY_RELEVANT','UNCERTAIN','IRRELEVANT'],
  sentiment:['POSITIVE','NEUTRAL','NEGATIVE'],
  evidence_quality:['COMPLETE','PARTIAL','MISSING','CONFLICTING','UNVERIFIABLE','DUPLICATE'],
  provider_fetch_status:['AVAILABLE','PARTIAL','API_FAILED','DELETED','ACCESS_RESTRICTED','NOT_RETURNED']
};
const HIGH_IMPACT=new Set(['author_name','observed_handle','canonical_url','text_content','transcript',
  'translation','candidate_names','political_parties','organizations','potential_issue_categories',
  'country','province','city','incident_date','geographic_context']);
const LONG=new Set(['text_content','transcript','translation','narrative','missing_data',
  'officer_notes','verification_gaps','relevance_explanation','sentiment_explanation']);
const READABLE={
  relevance:'Election relevance',sentiment:'Sentiment',author_name:'Post author',canonical_url:'Original post URL',
  text_content:'Post text',published_at:'Publication date',candidate_names:'Candidates mentioned',
  topic_labels:'Topics',potential_issue_categories:'Possible election issue',
  evidence_quality:'Evidence completeness',provider_fetch_status:'Provider retrieval',
  transcript:'Video transcription',translation:'Translation',geographic_context:'Geographic context',
  missing_data:'Missing information',verification_gaps:'Verification gaps',
  engagement_likes:'Likes',engagement_comments:'Comments',engagement_shares:'Shares',
  engagement_views:'Views',observed_handle:'Account handle',officer_notes:'Officer notes'
};
const pretty=(key)=>READABLE[key]||String(key||'').replaceAll('_',' ').replace(/\b\w/g, c=>c.toUpperCase());
const validUrl=(v)=>{try{const u=new URL(v);return ['https:','http:'].includes(u.protocol)&&Boolean(u.hostname)}catch{return false}};
const usable=(v)=>{const s=String(v??'').trim();return Boolean(s)&&!['[]','{}','null','UNKNOWN','UNCLASSIFIED'].includes(s.toUpperCase())};
const autoFieldReason=(field)=>'Automatically generated audit note: officer proposed changing '+pretty(field)+
  '; the supplied value remains unverified unless separately reviewed.';
const autoBatchReason=(n)=>'System-generated QA audit note: officer submitted '+n+
  ' field correction(s). This action does not assert independent source verification.';
const autoDecisionReason=(status)=>status==='OFFICER_VERIFIED'?
  'Officer explicitly confirmed review of the saved information snapshot for Gate 1 QA only; not legal verification.':
  status==='HELD'?'Officer chose to hold this information pending further source and context verification.':
  'Officer chose to exclude this information from the Gate 1 QA review; not a legal finding.';
const INPUT='intel-input mt-1 w-full';

function savedIssues(detail,view){
  // Only surface meaningful review gaps: absent candidate or location is not
  // automatically an error; many sources legitimately do not mention either.
  const issues=[];
  const add=(field,message)=>{if(!issues.some(i=>i.field===field))issues.push({field,message})};
  if(!usable(detail?.canonical_url))add('canonical_url','Original source link is unavailable. Confirm evidence provenance.');
  // Publication dates are only elevated if the contextual missing-data planner finds relevance.
  if(!usable(detail?.text_content)&&!usable(view?.fields?.transcript?.effective))
    add('text_content','Neither post text nor a transcript is available for contextual review.');
  if(['UNCLASSIFIED','UNKNOWN','UNASSESSED'].includes(String(detail?.ai_sentiment||'').toUpperCase())
     && !['IRRELEVANT'].includes(String(detail?.effective_relevance||'').toUpperCase()))
    add('sentiment','AI sentiment is unclassified and may need assessment.');
  return issues.slice(0,3);
}

export default function Gate1FullWorkbench({campaignId,detail,onSaved,onNext}){
  const {language}=useLanguage();
  const T=(en,id)=>language==='id'?id:en;
  const [mode,setMode]=useState('review');
  const [view,setView]=useState(null);
  const [field,setField]=useState('');
  const [selectedGroup,setSelectedGroup]=useState('');
  const [selectedMissing,setSelectedMissing]=useState('');
  const [reviewLane,setReviewLane]=useState('assessment');
  const [sourceErrorOpen,setSourceErrorOpen]=useState(false);
  const [errorField,setErrorField]=useState('');
  const [errorNote,setErrorNote]=useState('');
  const [value,setValue]=useState('');
  const [noValue,setNoValue]=useState(false);
  const [note,setNote]=useState('');
  const [support,setSupport]=useState('');
  const [sourceConfirmed,setSourceConfirmed]=useState(false);
  const [pending,setPending]=useState([]);
  const [sensitiveReason,setSensitiveReason]=useState('SOURCE_MISMATCH');
  const [reviewerReason,setReviewerReason]=useState('');
  const [reportBusy,setReportBusy]=useState(false);
  const [busy,setBusy]=useState(false);
  const [error,setError]=useState('');
  const [notice,setNotice]=useState('');
  const [advanced,setAdvanced]=useState(false);
  const lastSourceRef=useRef('');

  const fields=view?.fields||{};
  const availableGroup=(id)=>ASSESSMENT_GROUPS.find(g=>g.id===id);
  const effectiveValue=(key)=>key==='relevance'?String(detail?.effective_relevance||''):
    key==='sentiment'?String(detail?.effective_sentiment||''):
    String(fields[key]?.effective??'');
  const originalValue=(key)=>key==='relevance'?String(detail?.original_ai_relevance||''):
    key==='sentiment'?String(detail?.ai_sentiment||''):
    String(fields[key]?.original??'');
  const groupSummary=(group)=>group.fields.map(k=>usable(effectiveValue(k))?
    pretty(k)+': '+effectiveValue(k).slice(0,70):pretty(k)+': not identified').join(' · ');
  const reportValue=errorField?String(fields[errorField]?.effective??''):'';
  const important=HIGH_IMPACT.has(field)||reviewLane==='source'||field==='incident_jurisdiction'||field==='incident_chronology';
  const choice=effectiveValue(field);
  const original=originalValue(field);
  const issueHints=useMemo(()=>[...(view?.quality_hints||[]).map(h=>({...h,message:h.message+(h.suggested_value?' Suggested: '+h.suggested_value+' (verify before use).':'')})),...savedIssues(detail,view)].slice(0,5),[detail,view]);
  const reasonLabels={SOURCE_MISMATCH:'Source differs from saved value',WRONG_ATTRIBUTION:'Incorrect identity or location attribution',MISSING_CONTEXT:'Missing or incomplete source context',OTHER:'Other — officer explanation'};
  const correctionReason=important?(sensitiveReason==='OTHER'?note.trim():reasonLabels[sensitiveReason]+(note.trim()?' — '+note.trim():'')):note.trim();
  const isLegacy=field==='relevance'||field==='sentiment';
  const changed=field&&(noValue?
    (!isLegacy&&view?.fields?.[field]?.mode!=='UNAVAILABLE'):
    (String(value).trim()!==choice&&String(value).trim().length>0));
  const allowedField=reviewLane==='source'?
    (view?.can_correct_source&&SOURCE_EXCEPTION_FIELDS.includes(field)):
    reviewLane==='missing'?
      (view?.can_complete_missing&&view?.missing_review_tasks?.some(t=>t.field===field)):
      ASSESSMENT_FIELDS.includes(field);
  const canSubmit=view?.can_edit&&allowedField&&detail?.can_review_information&&changed&&!busy&&
    (!isLegacy||Boolean(detail?.assessment_id))&&
    (!important||correctionReason.length>=10)&&
    (!sourceConfirmed||validUrl(support))&&
    (!support.trim()||validUrl(support));
  const needsReview=view?.secondary_review_required&&view?.secondary_review?.status!=='APPROVED';
  const materialGaps=(view?.missing_review_tasks||[]).some(x=>x.priority==='P1');
  const blockedApproval=needsReview||view?.stale||detail?.full_field_stale||materialGaps;

  useEffect(()=>{
    if(String(campaignId)!=='9'||!detail?.result_id){setView(null);return}
    let active=true;
    const sourceChanged=lastSourceRef.current!==String(detail.result_id);
    lastSourceRef.current=String(detail.result_id);
    if(sourceChanged){setMode('review');setNotice('');setSelectedGroup('');setSelectedMissing('');setReviewLane('assessment');setSourceErrorOpen(false);setErrorField('');setErrorNote('')}
    setField('');setValue('');setNoValue(false);setPending([]);setAdvanced(false);
    setNote('');setSupport('');setSourceConfirmed(false);setError('');setView(null);
    base44.inboxHumanReview.fullReview(campaignId,detail.result_id)
      .then(x=>{if(active)setView(x)})
      .catch(e=>{if(active)setError(e.message||'Review details unavailable')});
    return ()=>{active=false};
  },[campaignId,detail?.result_id,detail?.assessment_id,detail?.source_integrity_digest,detail?.full_field_revision]);

  function selectField(key){
    setField(key);setValue('');setNote('');setSensitiveReason('SOURCE_MISMATCH');setSupport('');setNoValue(false);
    setSourceConfirmed(false);setError('');setAdvanced(false);
  }
  function chooseGroup(group){
    setSelectedGroup(group.id);setReviewLane('assessment');setSourceErrorOpen(false);
    selectField(group.fields[0]);
  }
  function beginSourceError(key=''){
    setSourceErrorOpen(true);setErrorField(key);setErrorNote('');
    setReviewLane('assessment');setSelectedGroup('');selectField('');
  }
  async function reportDataError(){
    if(!view?.can_report_data_error||!errorField||reportBusy)return;
    setReportBusy(true);setError('');setNotice('');
    try{
      await base44.inboxHumanReview.reportDataError(campaignId,detail.result_id,{
        field:errorField,note:errorNote.trim(),
        expected_assessment_id:detail.assessment_id,
        expected_source_digest:detail.source_integrity_digest,
      });
      setView(await base44.inboxHumanReview.fullReview(campaignId,detail.result_id));
      setErrorNote('');
      setNotice(T('Data issue recorded for verification. Original data was not changed.',
        'Masalah data dicatat untuk verifikasi. Data asli tidak berubah.'));
    }catch(e){setError(e.message||T('Could not report this data issue.','Gagal melaporkan masalah data.'))}
    finally{setReportBusy(false)}
  }
  function startSourceOverride(){
    if(!view?.can_correct_source||!SOURCE_EXCEPTION_FIELDS.includes(errorField))return;
    setReviewLane('source');setSelectedGroup('');setSourceErrorOpen(false);
    selectField(errorField);
  }
  function chooseMissing(task){
    setSelectedMissing(task.field);setReviewLane('missing');setMode('missing');
    selectField(task.field);
    setSensitiveReason('MISSING_CONTEXT');
  }
  function createPatch(){
    if(!field||!changed)return null;
    const clean=noValue?'':String(value).trim();
    const explanation=correctionReason.length>=10?correctionReason:autoFieldReason(field);
    return {field,value:clean,mode:noValue?'UNAVAILABLE':usable(choice)?'CORRECTED':'SUPPLEMENTED',
      verification:noValue?'UNVERIFIED':reviewLane==='missing'?'OFFICER_SUPPLIED':sourceConfirmed?'SOURCE_CONFIRMED':'UNVERIFIED',
      evidence_url:support.trim(),field_reason:explanation};
  }
  function addAnother(){
    if(!canSubmit||isLegacy||reviewLane==='source')return;
    const patch=createPatch();
    setPending(p=>[...p.filter(x=>x.field!==patch.field),patch]);
    selectField('');setNotice(T('Correction added. Select another field or save your changes.',
      'Koreksi ditambahkan. Pilih bidang lain atau simpan perubahan.'));
  }
  async function saveCorrections(next,onlyQueued=false){
    if(busy||!view?.can_edit||view.stale)return;
    const fresh=onlyQueued?null:field?createPatch():null;
    if(field&&!onlyQueued&&(!fresh||!canSubmit)){setError(T('Enter a different value. A source exception may need a correction basis.',
      'Masukkan nilai berbeda. Koreksi sumber mungkin memerlukan dasar.'));return}
    if(fresh&&isLegacy&&pending.length){setError(T('Save AI labels separately from other fields.',
      'Simpan label AI secara terpisah dari bidang lain.'));return}
    if(fresh?.mode==='UNAVAILABLE'&&isLegacy){setError(T('Use a label rather than marking this field unavailable.',
      'Gunakan label dan jangan tandai bidang ini tidak tersedia.'));return}
    const patches=[...pending.filter(p=>p.field!==fresh?.field),...(fresh?[fresh]:[])];
    if(!patches.length){setError(T('Select an incorrect or missing field first.','Pilih bidang yang salah atau hilang.'));return}
    if(patches.some(p=>!p.field_reason||p.field_reason.length<10)){setError('Missing correction explanation');return}
    setBusy(true);setError('');setNotice('');
    try{
      if(fresh&&isLegacy){
        await base44.inboxHumanReview.correct(campaignId,detail.result_id,{
          field:fresh.field,value:fresh.value,
          expected_revision:fresh.field==='relevance'?detail.relevance_revision:detail.sentiment_revision,
          expected_assessment_id:detail.assessment_id,
          expected_source_digest:detail.source_integrity_digest,
          reason:correctionReason.length>=10?correctionReason:autoFieldReason(fresh.field)
        });
      }else{
        await base44.inboxHumanReview.saveFullReview(campaignId,detail.result_id,{
          fields:patches,expected_revision:view.revision,
          expected_assessment_id:detail.assessment_id,
          expected_source_digest:detail.source_integrity_digest,
          reason:correctionReason.length>=10?correctionReason:autoBatchReason(patches.length)
        });
      }
      setPending([]);selectField('');setSelectedGroup('');setSelectedMissing('');setReviewLane('assessment');
      setNotice(T('Saved in QA history. Original provider and AI values remain unchanged.',
        'Disimpan dalam riwayat QA. Data sumber dan AI asli tidak berubah.'));
      onSaved?.();
      if(next)onNext?.();
    }catch(e){setError(e.message||T('Unable to save correction. Refresh and retry.','Gagal menyimpan koreksi. Muat ulang dan coba lagi.'))}
    finally{setBusy(false)}
  }
  async function decide(status,next){
    if(busy||!view?.can_edit)return;
    if(blockedApproval&&status==='OFFICER_VERIFIED'){
      setError(T('Independent approval or revalidation is required before approving this information.',
        'Persetujuan independen atau validasi ulang diperlukan sebelum menyetujui informasi.'));return;
    }
    if((field&&changed)||pending.length){setError(T('Save or discard field changes before recording a review decision.',
      'Simpan atau batalkan koreksi sebelum mencatat keputusan.'));return}
    if(status==='EXCLUDED'&&note.trim().length<10){setError(T('Please explain why the evidence should be excluded.',
      'Jelaskan alasan bukti perlu dikecualikan.'));return}
    setBusy(true);setError('');setNotice('');
    try{
      await base44.inboxHumanReview.decide(campaignId,detail.result_id,{
        status,expected_revision:detail.information_review_revision,
        expected_assessment_id:detail.assessment_id,
        expected_sentiment_revision:detail.sentiment_revision,
        expected_enrichment_revision:view.revision,
        expected_source_digest:detail.source_integrity_digest,
        reason:note.trim().length>=10?note.trim():autoDecisionReason(status)
      });
      setNotice(T('Review recorded. This does not verify legal allegations or publish intelligence.',
        'Tinjauan dicatat. Tidak memverifikasi tuduhan hukum atau menerbitkan intelijen.'));
      onSaved?.();if(next)onNext?.();
    }catch(e){setError(e.message||T('Unable to record review decision.','Gagal menyimpan keputusan tinjauan.'))}
    finally{setBusy(false)}
  }
  async function reviewSecondary(status){
    if(busy||!view?.can_secondary_review||reviewerReason.trim().length<10)return;
    setBusy(true);setError('');
    try{
      await base44.inboxHumanReview.secondFullReview(campaignId,detail.result_id,{
        status,expected_revision:view.revision,expected_assessment_id:detail.assessment_id,
        expected_source_digest:detail.source_integrity_digest,reason:reviewerReason.trim()
      });
      setView(await base44.inboxHumanReview.fullReview(campaignId,detail.result_id));
      setReviewerReason('');setNotice(T('Independent decision saved.','Keputusan pemeriksa kedua tersimpan.'));
      onSaved?.();
    }catch(e){setError(e.message||'Independent review unavailable')}
    finally{setBusy(false)}
  }
  if(String(campaignId)!=='9'||!detail?.qa_audit_only)return null;
  return <section className="border-t pt-3 space-y-3" data-testid="gate1-full-field-workbench">
    <div className="flex flex-wrap items-center justify-between gap-2">
      <div>
        <h4 className="text-base font-semibold">{T('Review & Correct','Tinjau & Koreksi')}</h4>
        <p className="text-xs text-slate-500">{T('Only fix what is wrong or missing. The system records the audit automatically.',
          'Perbaiki hanya yang salah atau hilang. Jejak audit dicatat otomatis.')}</p>
      </div>
      <span className="rounded-md bg-amber-50 border border-amber-200 px-2 py-1 text-xs text-amber-900">QA only</span>
    </div>

    <div className="flex flex-wrap gap-2" role="tablist" aria-label="Officer review actions">
      <button role="tab" aria-selected={mode==='review'} className={'intel-ghost text-xs '+(mode==='review'?'font-bold border-[#801b24]':'')}
        type="button" onClick={()=>{setMode('review');setError('')}} data-testid="gate1-action-review">
        {T('Review & Correct','Tinjau & Koreksi')}
      </button>
      <button role="tab" aria-selected={mode==='missing'} className={'intel-ghost text-xs '+(mode==='missing'?'font-bold border-[#801b24]':'')}
        type="button" onClick={()=>{setMode('missing');setReviewLane('missing');setSelectedMissing('');selectField('');setError('')}} data-testid="gate1-action-missing">
        {T('Complete Missing Data','Lengkapi Data yang Hilang')}
      </button>
    </div>

    {error&&<p role="alert" className="rounded-md bg-red-50 text-red-800 p-2 text-xs">{error}</p>}
    {notice&&<p role="status" className="rounded-md bg-green-50 text-green-800 p-2 text-xs">{notice}</p>}
    {mode==='review'&&<div className="space-y-3">
      {!view?<p role="status" className="text-sm">{T('Loading review details…','Memuat rincian tinjauan…')}</p>:<>
        <div className="rounded-lg border border-slate-200 p-3 space-y-2" data-testid="gate1-automatic-quality-hints">
          <div className="flex flex-wrap items-center justify-between gap-2">
            <h5 className="text-sm font-semibold">{T('Things worth checking','Hal yang perlu diperiksa')}</h5>
            <span className="text-xs text-slate-500">{T('Automatic saved-data checks, not confirmed errors','Pemeriksaan otomatis, bukan kesalahan terkonfirmasi')}</span>
          </div>
          {issueHints.length?issueHints.map(i=><div key={i.field} className="flex items-start gap-2 text-xs">
            <span className="text-amber-700" aria-hidden="true">!</span>
            <div className="flex-1"><span>{i.message}</span></div>
            {view.can_edit&&<button type="button" className="underline text-[#801b24]" onClick={()=>{
              const group=ASSESSMENT_GROUPS.find(g=>g.fields.includes(i.field));
              if(group){chooseGroup(group);selectField(i.field)}else beginSourceError(i.field);
            }}>{T('Review','Periksa')}</button>}
          </div>):<p className="text-xs text-slate-500">{T('No obvious inconsistencies detected. You can still review assessments or report data errors.',
            'Tidak ditemukan ketidaksesuaian yang jelas. Anda tetap dapat meninjau penilaian atau melaporkan kesalahan data.')}</p>}
        </div>

        {view.can_edit&&<div className="rounded-lg border p-3 space-y-3" data-testid="gate1-full-field-editor">
          {reviewLane==='assessment'&&<>
            <h5 className="font-semibold text-sm">{T('What needs correcting?','Apa yang perlu diperbaiki?')}</h5>
            <p className="text-xs text-slate-500">{T('Select one assessment area only when the AI interpretation is incorrect. The saved values remain visible.',
              'Pilih bidang penilaian hanya jika hasil AI salah. Nilai tersimpan tetap terlihat.')}</p>
            <p className="text-xs font-medium">{T('Main priorities: violations, involved parties, incident jurisdiction','Prioritas utama: pelanggaran, pihak terkait, wilayah kejadian')}</p>
            <div className="grid gap-2 sm:grid-cols-2" data-testid="gate1-field-filter">
              {ASSESSMENT_GROUPS.filter(group=>group.priority==='P1').map(group=><button key={group.id} type="button"
                aria-pressed={selectedGroup===group.id} data-testid={'gate1-review-group-'+group.id}
                onClick={()=>chooseGroup(group)} className={'rounded-lg border p-3 text-left text-xs space-y-1 '+(selectedGroup===group.id?'border-[#801b24] bg-red-50':'border-slate-200')}>
                <span className="block font-semibold">{T(group.en,group.idLabel)}</span>
                <span className="block text-slate-600 break-words">{groupSummary(group)}</span>
              </button>)}
            </div>
            <details className="text-xs rounded-md border p-2" data-testid="gate1-other-review-areas">
              <summary className="font-medium cursor-pointer">{T('Other relevant information (5 areas)','Informasi terkait lainnya (5 bidang)')}</summary>
              <div className="grid gap-2 sm:grid-cols-2 pt-2">
                {ASSESSMENT_GROUPS.filter(group=>group.priority==='P2').map(group=><button key={group.id} type="button"
                  aria-pressed={selectedGroup===group.id} data-testid={'gate1-review-group-'+group.id}
                  onClick={()=>chooseGroup(group)} className={'rounded-lg border p-3 text-left space-y-1 '+(selectedGroup===group.id?'border-[#801b24] bg-red-50':'border-slate-200')}>
                  <span className="block font-semibold">{T(group.en,group.idLabel)}</span>
                  <span className="block text-slate-600 break-words">{groupSummary(group)}</span>
                </button>)}
              </div>
            </details>
            <p className="text-xs text-slate-500">{T('Missing values are reviewed only when relevant. No candidate or location is not automatically an error.',
              'Nilai yang tidak ada diperiksa hanya jika relevan. Tidak adanya kandidat atau lokasi bukan otomatis kesalahan.')}</p>
            {selectedGroup&&<label className="text-xs font-semibold block">{T('Selected assessment field','Bidang penilaian yang dipilih')}
              <select className={INPUT} data-testid="gate1-quick-field-select"
                value={field} onChange={e=>selectField(e.target.value)}>
                {availableGroup(selectedGroup)?.fields.map(key=><option key={key} value={key}>{pretty(key)}</option>)}
              </select>
            </label>}
          </>}
          {reviewLane==='source'&&<div className="rounded-lg border border-amber-200 bg-amber-50 p-3 space-y-2 text-xs">
            <strong>{T('Authorized source correction','Koreksi sumber dengan izin')}</strong>
            <p>{T('This is an exception, not a routine AI edit. The provider value remains unchanged and high-impact changes require independent review.',
              'Ini pengecualian, bukan koreksi AI rutin. Nilai sumber tetap utuh dan perubahan penting memerlukan tinjauan petugas lain.')}</p>
            <button className="underline" type="button" onClick={()=>{setReviewLane('assessment');setSelectedGroup('');selectField('')}}>
              {T('Back to assessments','Kembali ke penilaian')}
            </button>
          </div>}
          {field&&<div className="space-y-2" data-testid="gate1-quick-editor">
            <div className="rounded-md bg-slate-50 p-2 text-xs space-y-1">
              <p className="text-slate-500">{T('Original provider / AI value','Nilai sumber / AI asli')}: <strong className="break-words whitespace-pre-wrap">{usable(original)?original:T('Not available','Tidak tersedia')}</strong></p>
              <p data-testid="gate1-current-effective-value">{T('Current effective value','Nilai efektif saat ini')}: <strong className="break-words whitespace-pre-wrap">{usable(choice)?choice:T('Not identified','Tidak teridentifikasi')}</strong></p>
              <p className="text-slate-500">{T('Value basis','Dasar nilai')}: {isLegacy?'Saved AI / officer correction':fields[field]?.basis||'Original saved'} · {fields[field]?.verification||'Unverified'}</p>
            </div>
            <label className="text-xs font-semibold block">{T('Correct value','Nilai yang benar')}
              {CLASSIFICATIONS[field]?<select className={INPUT} value={value} onChange={e=>setValue(e.target.value)}
                data-testid="gate1-quick-value">
                <option value="">{T('Select corrected value','Pilih nilai koreksi')}</option>
                {CLASSIFICATIONS[field].map(x=><option key={x} value={x}>{pretty(x)}</option>)}
              </select>:
              <textarea className={INPUT} rows={LONG.has(field)?3:2} value={value}
                onChange={e=>{setValue(e.target.value);setNoValue(false)}} disabled={noValue}
                placeholder={T('Enter the corrected or missing information','Isi informasi yang benar atau hilang')}
                data-testid="gate1-quick-value"/>}
            </label>
            {!CLASSIFICATIONS[field]&&<label className="flex items-center gap-2 text-xs">
              <input type="checkbox" checked={noValue} onChange={e=>{setNoValue(e.target.checked);setValue('')}}/>
              {T('Information unavailable / could not be retrieved','Informasi tidak tersedia / tidak berhasil diambil')}
            </label>}
            {important&&<div className="rounded-md border border-amber-200 bg-amber-50 p-2 space-y-2">
              <p className="text-xs text-amber-900">{T('Identity, location or other high-impact changes need a short explanation and a different officer’s approval.',
                'Perubahan identitas, lokasi atau informasi penting perlu penjelasan singkat dan persetujuan petugas lain.')}</p>
              <label className="text-xs block font-semibold">{T('Correction basis','Dasar koreksi')}
                <select data-testid="gate1-sensitive-reason" className={INPUT} value={sensitiveReason} onChange={e=>setSensitiveReason(e.target.value)}>
                  {Object.entries(reasonLabels).map(([key,label])=><option value={key} key={key}>{label}</option>)}
                </select>
              </label>
              {sensitiveReason==='OTHER'&&<label className="text-xs block font-semibold">{T('Short explanation','Penjelasan singkat')}
                <textarea className={INPUT} rows={2} value={note} onChange={e=>setNote(e.target.value)}
                  placeholder={T('Explain the different value','Jelaskan perbedaan nilai')}/>
              </label>}
              <label className="text-xs block font-semibold">{T('Evidence link (when available)','Tautan bukti (jika tersedia)')}
                <input className={INPUT} type="url" value={support} onChange={e=>setSupport(e.target.value)} placeholder="https://..."/>
              </label>
            </div>}
            {!important&&<details className="rounded-md bg-slate-50 p-2 text-xs" open={advanced}>
              <summary className="cursor-pointer" onClick={e=>{e.preventDefault();setAdvanced(s=>!s)}}>
                {T('Add explanation or supporting link (optional)','Tambahkan penjelasan atau tautan (opsional)')}
              </summary>
              {advanced&&<div className="space-y-2 pt-2">
                <label className="block">{T('Explanation','Penjelasan')}
                  <textarea className={INPUT} rows={2} value={note} onChange={e=>setNote(e.target.value)}/>
                </label>
                <label className="block">{T('Supporting link','Tautan pendukung')}
                  <input className={INPUT} value={support} onChange={e=>setSupport(e.target.value)} placeholder="https://..."/>
                </label>
                {support&&<label className="flex gap-2 items-center">
                  <input type="checkbox" checked={sourceConfirmed} onChange={e=>setSourceConfirmed(e.target.checked)}/>
                  {T('I checked this value against the linked source','Saya memeriksa nilai ini dengan sumber tertaut')}
                </label>}
              </div>}
            </details>}
            <div className="flex flex-wrap gap-2">
              <button type="button" className="intel-ghost text-xs" onClick={()=>saveCorrections(false)}
                disabled={!canSubmit||view.stale||Boolean(pending.length&&isLegacy)}
                data-testid="gate1-save-quick-correction">{T('Save correction','Simpan koreksi')}</button>
              <button type="button" className="intel-ghost text-xs" onClick={()=>saveCorrections(true)}
                disabled={!canSubmit||view.stale||Boolean(pending.length&&isLegacy)}
                data-testid="gate1-save-and-next">{T('Save & Next','Simpan & Berikutnya')}</button>
              {!isLegacy&&reviewLane==='assessment'&&<details className="text-xs">
                <summary className="cursor-pointer text-slate-500">{T('More correction options','Pilihan koreksi tambahan')}</summary>
                <button type="button" className="underline text-slate-700 mt-2" onClick={addAnother}
                  disabled={!canSubmit||pending.length>=14}>{T('Queue this and correct another assessment','Tambahkan lalu koreksi penilaian lain')}</button>
              </details>}
            </div>
          </div>}
          {pending.length>0&&<div className="rounded-md bg-slate-50 p-2 space-y-2" data-testid="gate1-pending-fields">
            <p className="text-xs font-semibold">{pending.length} {T('corrections ready to save','koreksi siap disimpan')}</p>
            {pending.map(p=><div key={p.field} className="flex items-center justify-between gap-2 text-xs">
              <span>{pretty(p.field)}: {p.mode==='UNAVAILABLE'?T('Unavailable','Tidak tersedia'):String(p.value).slice(0,60)}</span>
              <button type="button" className="underline text-red-800" onClick={()=>setPending(x=>x.filter(y=>y.field!==p.field))}>
                {T('Remove','Hapus')}</button>
            </div>)}
            <button type="button" className="intel-ghost text-xs" onClick={()=>saveCorrections(false,true)}
              disabled={busy||view.stale} data-testid="gate1-save-queued-corrections">
              {T('Save queued corrections','Simpan koreksi yang siap')}</button>
          </div>}
        </div>}

        <details className="rounded-lg border p-3 space-y-2" data-testid="gate1-report-data-error">
          <summary className="text-xs font-semibold cursor-pointer">{T('Source or technical data incorrect? · Report Data Error',
            'Data sumber atau teknis salah? · Laporkan kesalahan data')}</summary>
          <div className="pt-2">
          <div className="flex flex-wrap justify-between items-center gap-2">
            <div>
              <h5 className="font-semibold text-sm">{T('Source data incorrect?','Data sumber salah?')}</h5>
              <p className="text-xs text-slate-500">{T('Engagement figures and transcripts are read-only; report an issue instead of editing them.',
                'Metrik interaksi dan transkrip hanya untuk dilihat; laporkan masalah, bukan mengedit.')}</p>
            </div>
            {view.can_report_data_error&&<button type="button" className="intel-ghost text-xs"
              onClick={()=>sourceErrorOpen?setSourceErrorOpen(false):beginSourceError()}
              data-testid="gate1-open-data-error">
              {T('Report Data Error','Laporkan Kesalahan Data')}
            </button>}
          </div>
          {sourceErrorOpen&&view.can_report_data_error&&<div className="space-y-2 rounded-md bg-slate-50 p-3" data-testid="gate1-data-error-form">
            <label className="block text-xs font-semibold">{T('Which saved field may be wrong?','Bidang tersimpan mana yang mungkin salah?')}
              <select className={INPUT} data-testid="gate1-data-error-field" value={errorField}
                onChange={e=>setErrorField(e.target.value)}>
                <option value="">{T('Choose field to report','Pilih bidang yang dilaporkan')}</option>
                <optgroup label={T('Source information','Informasi sumber')}>
                  {SOURCE_EXCEPTION_FIELDS.map(key=><option key={key} value={key}>{pretty(key)}</option>)}
                </optgroup>
                <optgroup label={T('Technical metadata (report only)','Metadata teknis (laporan saja)')}>
                  {TECHNICAL_READ_ONLY_FIELDS.map(key=><option key={key} value={key}>{pretty(key)}</option>)}
                </optgroup>
              </select>
            </label>
            {errorField&&<div className="space-y-2">
              <p className="text-xs break-words" data-testid="gate1-data-error-current-value">
                {T('Current saved value','Nilai yang tersimpan')}: <strong className="whitespace-pre-wrap">{usable(reportValue)?reportValue:T('Not available','Tidak tersedia')}</strong>
              </p>
              <label className="block text-xs">{T('What looks wrong? (optional)','Apa yang keliru? (opsional)')}
                <textarea rows={2} className={INPUT} value={errorNote}
                  onChange={e=>setErrorNote(e.target.value)}
                  placeholder={T('Short description, if helpful','Penjelasan singkat jika diperlukan')}/>
              </label>
              <div className="flex flex-wrap gap-2">
                <button type="button" className="intel-ghost text-xs" data-testid="gate1-submit-data-error"
                  disabled={reportBusy} onClick={reportDataError}>
                  {T('Record data issue','Catat masalah data')}
                </button>
                {view.can_correct_source&&SOURCE_EXCEPTION_FIELDS.includes(errorField)&&<button type="button"
                  className="intel-ghost text-xs" data-testid="gate1-open-source-override"
                  onClick={startSourceOverride}>
                  {T('Correct source value (authorized)','Koreksi nilai sumber (berizin)')}
                </button>}
              </div>
              <p className="text-xs text-slate-600">{T('Reporting never changes provider values. Source exceptions are audited; high-impact changes require another officer.',
                'Pelaporan tidak mengubah nilai penyedia. Koreksi sumber diaudit; perubahan penting memerlukan petugas lain.')}</p>
            </div>}
          </div>}
          {!!view.source_error_reports?.length&&<details className="text-xs">
            <summary className="cursor-pointer text-slate-600">{T('Reported source issues','Masalah sumber yang dilaporkan')} ({view.source_error_reports.length})</summary>
            {(view.source_error_reports||[]).map(report=><p key={report.id} className="mt-2 border-t pt-2 break-words">
              #{report.id} · {pretty(report.field)} · {report.status} · {report.note}
            </p>)}
          </details>}
          </div>
        </details>

        {view.secondary_review_required&&<div className="rounded-lg bg-amber-50 border border-amber-200 p-3 space-y-2"
          data-testid="gate1-secondary-review">
          <p className="text-sm font-semibold">{T('Second officer approval','Persetujuan petugas kedua')}: {view.secondary_review?.status||'PENDING'}</p>
          <p className="text-xs">{T('Sensitive QA corrections must be reviewed by a different authorized administrator before approval.',
            'Koreksi QA sensitif harus diperiksa administrator berbeda sebelum dapat disetujui.')}</p>
          {view.can_secondary_review&&<div className="space-y-2">
            <textarea className={INPUT} rows={2} value={reviewerReason} onChange={e=>setReviewerReason(e.target.value)}
              placeholder={T('Why do you approve or reject? (10+ characters)','Alasan persetujuan atau penolakan (10+ karakter)')}/>
            <div className="flex gap-2 flex-wrap">
              <button type="button" className="intel-ghost text-xs" disabled={busy||reviewerReason.trim().length<10} onClick={()=>reviewSecondary('APPROVED')}>{T('Approve','Setujui')}</button>
              <button type="button" className="intel-ghost text-xs" disabled={busy||reviewerReason.trim().length<10} onClick={()=>reviewSecondary('REJECTED')}>{T('Reject','Tolak')}</button>
            </div>
          </div>}
          {!view.can_secondary_review&&<p className="text-xs text-slate-600">{T('Another administrator must complete this step.','Administrator lain harus menyelesaikan langkah ini.')}</p>}
        </div>}

        {view.can_edit&&<div className="rounded-lg border p-3 space-y-2" data-testid="gate1-quick-decision">
          <h5 className="text-sm font-semibold">{T('Finished checking this post?','Selesai memeriksa unggahan ini?')}</h5>
          <p className="text-xs text-slate-500">{T('This records an information review, not a legal finding. Unresolved priority gaps require completion or a hold.',
            'Ini mencatat tinjauan informasi, bukan putusan hukum. Kekurangan penting perlu dilengkapi atau ditunda.')}</p>
          {detail.information_review_status!=='OFFICER_VERIFIED'&&<div className="flex gap-2 flex-wrap">
            <button className="intel-ghost text-xs" type="button" disabled={busy||blockedApproval||pending.length>0||(field&&changed)}
              data-testid="gate1-one-click-approve" onClick={()=>decide('OFFICER_VERIFIED',true)}>
              {T('Looks Correct · Next','Sudah Benar · Berikutnya')}</button>
            <button className="intel-ghost text-xs" type="button" disabled={busy||pending.length>0||(field&&changed)}
              onClick={()=>decide('HELD',true)}>{T('Hold for verification','Tunda untuk verifikasi')}</button>
          </div>}
          <details className="text-xs"><summary className="cursor-pointer text-slate-600">{T('Authorized: Exclude or change review decision','Berwenang: kecualikan atau ubah keputusan')}</summary>
            <div className="pt-2 space-y-2">
              <textarea className={INPUT} rows={2} value={note} onChange={e=>setNote(e.target.value)}
                placeholder={T('Reason for exclusion (required)','Alasan pengecualian (wajib)')}/>
              <button type="button" className="intel-ghost text-xs" onClick={()=>decide('EXCLUDED',true)}
                disabled={busy||note.trim().length<10}>{T('Exclude from QA & Next','Kecualikan dari QA & Berikutnya')}</button>
            </div>
          </details>
        </div>}

        <details className="text-xs rounded-lg border p-3" data-testid="gate1-effective-field-list">
          <summary className="cursor-pointer font-medium">{T('View all values and audit history','Lihat semua nilai dan riwayat audit')}</summary>
          <div className="space-y-3 pt-2" data-testid="gate1-full-audit-history">
            <p>{T('All fields are available for inspection. Only the eight review areas are routinely editable. Original evidence is retained.',
              'Semua bidang dapat diperiksa. Hanya delapan bidang penilaian rutin yang dapat dikoreksi. Bukti asli tetap disimpan.')}</p>
            <details data-testid="gate1-readonly-source">
              <summary className="cursor-pointer font-medium">{T('Source evidence — read-only','Bukti sumber — hanya baca')}</summary>
              {SOURCE_EXCEPTION_FIELDS.map(key=><div key={key} className="border-t py-2 break-words">
                <span className="font-semibold">{pretty(key)}</span> · {String(fields[key]?.effective??'').trim()||T('Not available','Tidak tersedia')}
              </div>)}
            </details>
            <details data-testid="gate1-readonly-technical">
              <summary className="cursor-pointer font-medium">{T('Technical metadata — read-only','Metadata teknis — hanya baca')}</summary>
              {TECHNICAL_READ_ONLY_FIELDS.map(key=><div key={key} className="border-t py-2 break-words">
                <span className="font-semibold">{pretty(key)}</span> · {String(fields[key]?.effective??'').trim()||T('Not available','Tidak tersedia')}
              </div>)}
            </details>
            <details>
              <summary>{T('Assessment correction history','Riwayat koreksi penilaian')}</summary>
              {Object.entries(fields).filter(([,x])=>x.basis==='QA_OFFICER_ENRICHMENT').map(([key,x])=><div key={key} className="border-t pt-1 break-words">
                <strong>{pretty(key)}</strong>: {String(x.effective||'UNAVAILABLE').slice(0,300)} ({x.verification})
              </div>)}
              {view.history?.slice(0,15).map(h=><div className="border-t pt-1" key={h.revision}>
                #{h.revision} · {T('Officer','Petugas')} {h.actor_id} · {h.at} · {h.fields?.map(f=>pretty(f.field)).join(', ')} · {h.reason}
              </div>)}
            </details>
            <p className="text-slate-500">{T('Missing values are not automatically errors. All fields remain accessible for audit.',
              'Nilai kosong tidak otomatis salah. Semua bidang tetap tersedia untuk audit.')}</p>
          </div>
        </details>
      </>}
    </div>}

    {mode==='missing'&&<div className="space-y-3" data-testid="gate1-manual-intake">
      {!view?<p role="status" className="text-xs">{T('Loading existing record…','Memuat catatan yang ada…')}</p>:<>
        <div className="rounded-lg border p-3 space-y-2" data-testid="gate1-missing-existing-record">
          <h5 className="font-semibold text-sm">{T('Complete missing values in this record','Lengkapi nilai yang hilang dalam catatan ini')} #{detail.result_id}</h5>
          <p className="text-xs text-slate-600">{T('Automated checks only surface missing values important to this source. No new post will be created.',
            'Pemeriksaan otomatis hanya menampilkan nilai hilang yang penting. Tidak ada unggahan baru yang dibuat.')}</p>
          <p className="text-xs">{T('Unresolved items','Item belum terselesaikan')}: <strong>{view.missing_review_tasks?.length||0}</strong></p>
          {view.missing_review_tasks?.length>0?<>
            <div className="space-y-2" data-testid="gate1-contextual-missing-tasks">
              {view.missing_review_tasks.map(task=><button type="button" key={task.field}
                onClick={()=>chooseMissing(task)} aria-pressed={selectedMissing===task.field}
                className={'w-full text-left border rounded-lg p-3 space-y-1 text-xs '+(selectedMissing===task.field?'border-[#801b24] bg-red-50':'border-slate-200')}>
                <span className="block font-semibold">{pretty(task.field)} · {task.priority==='P1'?T('High attention','Perhatian tinggi'):T('Contextual check','Pemeriksaan sesuai konteks')}</span>
                <span className="block text-slate-600">{task.reason}</span>
              </button>)}
            </div>
            {selectedMissing&&field&&<div className="rounded-lg border bg-slate-50 p-3 space-y-2" data-testid="gate1-complete-missing-field">
              <h5 className="font-semibold text-sm">{T('Complete','Lengkapi')}: {pretty(field)}</h5>
              <p className="text-xs">{T('Original saved','Nilai asli tersimpan')}: <strong>{usable(original)?original:T('Not provided','Tidak tersedia')}</strong></p>
              <p className="text-xs">{T('Current effective','Nilai efektif saat ini')}: <strong>{usable(choice)?choice:T('Missing','Hilang')}</strong></p>
              <label className="block text-xs font-semibold">{T('Provide verified information if available','Isi informasi berdasarkan bukti jika tersedia')}
                {CLASSIFICATIONS[field]?<select className={INPUT} data-testid="gate1-missing-value"
                  value={value} onChange={e=>{setValue(e.target.value);setNoValue(false)}}>
                  <option value="">{T('Choose value','Pilih nilai')}</option>
                  {CLASSIFICATIONS[field].map(x=><option key={x} value={x}>{pretty(x)}</option>)}
                </select>:<textarea data-testid="gate1-missing-value" className={INPUT} rows={2}
                  value={value} disabled={noValue} onChange={e=>{setValue(e.target.value);setNoValue(false)}}
                  placeholder={T('Missing information','Informasi yang hilang')}/>}
              </label>
              {!isLegacy&&<label className="flex gap-2 text-xs items-center">
                <input type="checkbox" checked={noValue} onChange={e=>{setNoValue(e.target.checked);setValue('')}}/>
                {T('Cannot verify / information unavailable','Tidak dapat diverifikasi / informasi tidak tersedia')}
              </label>}
              {important&&<label className="block text-xs font-semibold">{T('Reason for completing this field','Alasan melengkapi bidang')}
                <select className={INPUT} value={sensitiveReason} onChange={e=>setSensitiveReason(e.target.value)}>
                  {Object.entries(reasonLabels).map(([key,label])=><option key={key} value={key}>{label}</option>)}
                </select>
              </label>}
              {important&&sensitiveReason==='OTHER'&&<textarea className={INPUT} value={note} onChange={e=>setNote(e.target.value)} rows={2}
                placeholder={T('Short supporting explanation','Penjelasan pendukung singkat')}/>}
              <details className="text-xs">
                <summary className="cursor-pointer">{T('Source link (optional)','Tautan sumber (opsional)')}</summary>
                <input type="url" className={INPUT} value={support} onChange={e=>setSupport(e.target.value)} placeholder="https://..."/>
                {support&&<label className="flex gap-2 items-center mt-2"><input type="checkbox" checked={sourceConfirmed} onChange={e=>setSourceConfirmed(e.target.checked)}/>
                  {T('I verified against this source','Saya sudah memeriksa sumber ini')}</label>}
              </details>
              <div className="flex flex-wrap gap-2">
                <button type="button" className="intel-ghost text-xs" data-testid="gate1-save-missing-evidence"
                  onClick={()=>saveCorrections(false)} disabled={!canSubmit||view.stale}>
                  {T('Save missing value','Simpan nilai yang hilang')}
                </button>
                <button type="button" className="intel-ghost text-xs" onClick={()=>saveCorrections(true)}
                  disabled={!canSubmit||view.stale}>{T('Save & Next','Simpan & Berikutnya')}</button>
              </div>
              <p className="text-xs text-slate-500">{T('Officer-supplied values are audited; original source data is retained. Significant changes may need independent review.',
                'Nilai yang diisi petugas dicatat dalam audit; sumber asli tetap disimpan. Perubahan penting mungkin memerlukan pemeriksaan independen.')}</p>
            </div>}
          </>:<p className="text-xs text-slate-600" data-testid="gate1-no-material-missing">
            {T('No unresolved essential fields identified. Missing optional information is not an error.',
              'Tidak ditemukan bidang penting yang belum lengkap. Informasi opsional yang kosong bukan kesalahan.')}
          </p>}
        </div>
      </>}
    </div>}
    <p className="text-xs text-slate-500">{T('Review changes are recorded separately. Original source evidence is retained.',
      'Perubahan tinjauan dicatat terpisah. Bukti sumber asli tetap disimpan.')}</p>
  </section>;
}
