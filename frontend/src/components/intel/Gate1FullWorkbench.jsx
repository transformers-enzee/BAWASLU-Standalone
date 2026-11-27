import {useEffect,useMemo,useRef,useState} from 'react';
import {base44} from '@/api/base44Client';
import {useLanguage} from '@/lib/LanguageContext';

const MAIN_FIELDS=['relevance','sentiment','candidate_names','political_parties','topic_labels','potential_issue_categories','evidence_quality'];
const CONTEXT_FIELDS=['platform','author_name','observed_handle','published_at','canonical_url','text_content','country','province','city','language','transcript','engagement_likes','engagement_comments','engagement_shares','engagement_views'];
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
const autoManualReason='Officer submitted a missing-source proposal for QA review. Provider retrieval is not asserted and this remains unverified.';
const INPUT='intel-input mt-1 w-full';
const EMPTY_MANUAL={platform:'youtube',text_content:'',source_url:'',author_name:'',reason:''};

function savedIssues(detail,view){
  const items=[];
  const add=(field,message)=>{if(!items.some(i=>i.field===field))items.push({field,message})};
  if(String(detail?.text_content||'').trim().length<40)
    add('text_content','Very short saved post text; context may be insufficient.');
  if(!detail?.published_at)
    add('published_at','Publication date was not available in the saved source.');
  if(!detail?.author_name)
    add('author_name','Post author was not available in the saved source.');
  if(!usable(view?.fields?.country?.effective))
    add('country','Country was not confirmed in the saved source.');
  if(!usable(view?.fields?.candidate_names?.effective))
    add('candidate_names','No candidate was identified in the saved assessment; this may be appropriate.');
  if(String(detail?.ai_sentiment||'').toUpperCase()==='UNCLASSIFIED')
    add('sentiment','Saved AI sentiment is unclassified.');
  return items.slice(0,3);
}

export default function Gate1FullWorkbench({campaignId,detail,onSaved,onNext}){
  const {language}=useLanguage();
  const T=(en,id)=>language==='id'?id:en;
  const [mode,setMode]=useState('review');
  const [view,setView]=useState(null);
  const [manualList,setManualList]=useState(null);
  const [field,setField]=useState('');
  const [fieldFilter,setFieldFilter]=useState('priority');
  const [value,setValue]=useState('');
  const [noValue,setNoValue]=useState(false);
  const [note,setNote]=useState('');
  const [support,setSupport]=useState('');
  const [sourceConfirmed,setSourceConfirmed]=useState(false);
  const [pending,setPending]=useState([]);
  const [manual,setManual]=useState(EMPTY_MANUAL);
  const [sensitiveReason,setSensitiveReason]=useState('SOURCE_MISMATCH');
  const [reviewerReason,setReviewerReason]=useState('');
  const [busy,setBusy]=useState(false);
  const [error,setError]=useState('');
  const [notice,setNotice]=useState('');
  const [advanced,setAdvanced]=useState(false);
  const lastSourceRef=useRef('');

  const fields=view?.fields||{};
  const allFields=useMemo(()=>Array.from(new Set(['relevance','sentiment',...Object.values(view?.field_groups||{}).flat()])),[view?.field_groups]);
  const missingFields=useMemo(()=>allFields.filter(key=>{
    const val=key==='relevance'?detail?.effective_relevance:key==='sentiment'?detail?.effective_sentiment:fields[key]?.effective;
    return !usable(val);
  }),[allFields,detail?.effective_relevance,detail?.effective_sentiment,fields]);
  const orderedFields=useMemo(()=>{
    const group=fieldFilter==='missing'?missingFields:fieldFilter==='advanced'?allFields:
      [...MAIN_FIELDS,...CONTEXT_FIELDS].filter(key=>allFields.includes(key));
    return [...new Set(group)];
  },[fieldFilter,missingFields,allFields]);
  const options=useMemo(()=>[{title:T('Available correction fields','Bidang yang dapat dikoreksi'),items:orderedFields}],[orderedFields,language]);
  const important=HIGH_IMPACT.has(field);
  const choice=field==='relevance'?String(detail?.effective_relevance||''):
    field==='sentiment'?String(detail?.effective_sentiment||''):
    String(fields[field]?.effective??'');
  const original=field==='relevance'?String(detail?.original_ai_relevance||''):
    field==='sentiment'?String(detail?.ai_sentiment||''):
    String(fields[field]?.original??'');
  const issueHints=useMemo(()=>[...(view?.quality_hints||[]).map(h=>({...h,message:h.message+(h.suggested_value?' Suggested: '+h.suggested_value+' (verify before use).':'')})),...savedIssues(detail,view)].slice(0,5),[detail,view]);
  const reasonLabels={SOURCE_MISMATCH:'Source differs from saved value',WRONG_ATTRIBUTION:'Incorrect identity or location attribution',MISSING_CONTEXT:'Missing or incomplete source context',OTHER:'Other — officer explanation'};
  const correctionReason=important?(sensitiveReason==='OTHER'?note.trim():reasonLabels[sensitiveReason]+(note.trim()?' — '+note.trim():'')):note.trim();
  const isLegacy=field==='relevance'||field==='sentiment';
  const changed=field&&((noValue?choice!=='':String(value).trim()!==choice)&&
    (noValue||String(value).trim().length>0));
  const canSubmit=view?.can_edit&&detail?.can_review_information&&changed&&!busy&&
    (!isLegacy||Boolean(detail?.assessment_id))&&
    (!important||correctionReason.length>=10)&&
    (!sourceConfirmed||validUrl(support))&&
    (!support.trim()||validUrl(support));
  const needsReview=view?.secondary_review_required&&view?.secondary_review?.status!=='APPROVED';
  const blockedApproval=needsReview||view?.stale||detail?.full_field_stale;

  useEffect(()=>{
    if(String(campaignId)!=='9'||!detail?.result_id){setView(null);return}
    let active=true;
    const sourceChanged=lastSourceRef.current!==String(detail.result_id);
    lastSourceRef.current=String(detail.result_id);
    if(sourceChanged){setMode('review');setNotice('');setFieldFilter('priority')}
    setField('');setValue('');setNoValue(false);setPending([]);setAdvanced(false);
    setNote('');setSupport('');setSourceConfirmed(false);setError('');setView(null);
    base44.inboxHumanReview.fullReview(campaignId,detail.result_id)
      .then(x=>{if(active)setView(x)})
      .catch(e=>{if(active)setError(e.message||'Review details unavailable')});
    return ()=>{active=false};
  },[campaignId,detail?.result_id,detail?.assessment_id,detail?.source_integrity_digest,detail?.full_field_revision]);

  useEffect(()=>{
    if(String(campaignId)!=='9'||mode!=='missing')return;
    let active=true;
    const preferred=String(detail?.platform||'').toLowerCase();
    if(SUPPORTED_PLATFORMS.includes(preferred))setManual(x=>({...x,platform:preferred}));
    base44.inboxHumanReview.manualIntake(campaignId)
      .then(x=>{if(active)setManualList(x)})
      .catch(e=>{if(active)setError(e.message||'Manual evidence unavailable')});
    return ()=>{active=false};
  },[campaignId,mode,detail?.platform]);

  function selectField(key){
    setField(key);setValue('');setNote('');setSensitiveReason('SOURCE_MISMATCH');setSupport('');setNoValue(false);
    setSourceConfirmed(false);setError('');setAdvanced(false);
  }
  function createPatch(){
    if(!field||!changed)return null;
    const clean=noValue?'':String(value).trim();
    const explanation=correctionReason.length>=10?correctionReason:autoFieldReason(field);
    return {field,value:clean,mode:noValue?'UNAVAILABLE':usable(choice)?'CORRECTED':'SUPPLEMENTED',
      verification:sourceConfirmed?'SOURCE_CONFIRMED':'UNVERIFIED',
      evidence_url:support.trim(),field_reason:explanation};
  }
  function addAnother(){
    if(!canSubmit||isLegacy)return;
    const patch=createPatch();
    setPending(p=>[...p.filter(x=>x.field!==patch.field),patch]);
    selectField('');setNotice(T('Correction added. Select another field or save your changes.',
      'Koreksi ditambahkan. Pilih bidang lain atau simpan perubahan.'));
  }
  async function saveCorrections(next,onlyQueued=false){
    if(busy||!view?.can_edit||view.stale)return;
    const fresh=onlyQueued?null:field?createPatch():null;
    if(field&&!onlyQueued&&(!fresh||!canSubmit)){setError(T('Enter a different value. Sensitive changes need an explanation.',
      'Masukkan nilai berbeda. Perubahan sensitif perlu alasan.'));return}
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
      setPending([]);selectField('');
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
  async function saveMissing(){
    if(busy||manual.text_content.trim().length<10||!validUrl(manual.source_url))return;
    setBusy(true);setError('');setNotice('');
    try{
      await base44.inboxHumanReview.addManualIntake(campaignId,{
        platform:manual.platform,title:manual.text_content.trim().slice(0,100),
        text_content:manual.text_content.trim(),source_url:manual.source_url.trim(),
        author_name:manual.author_name.trim(),observed_at:'',
        reason:manual.reason.trim().length>=10?manual.reason.trim():autoManualReason,
        evidence_url:''
      });
      setManual({...EMPTY_MANUAL,platform:SUPPORTED_PLATFORMS.includes(String(detail?.platform||'').toLowerCase())?String(detail.platform).toLowerCase():'other'});
      setManualList(await base44.inboxHumanReview.manualIntake(campaignId));
      setNotice(T('Missing evidence recorded as an unverified QA proposal; no import or publication.',
        'Bukti dicatat sebagai usulan QA belum terverifikasi; tidak diimpor atau diterbitkan.'));
    }catch(e){setError(e.message||'Unable to record missing evidence')}
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
        type="button" onClick={()=>{setMode('missing');setError('')}} data-testid="gate1-action-missing">
        {T('Add Missing Post','Tambah Unggahan yang Hilang')}
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
            {view.can_edit&&<button type="button" className="underline text-[#801b24]" onClick={()=>{setFieldFilter('advanced');selectField(i.field)}}>
              {T('Fix','Perbaiki')}</button>}
          </div>):<p className="text-xs text-slate-500">{T('No obvious missing values detected. You can still correct any field.',
            'Tidak ada nilai hilang yang jelas. Anda tetap dapat mengoreksi bidang apa pun.')}</p>}
        </div>

        {view.can_edit&&<div className="rounded-lg border p-3 space-y-2" data-testid="gate1-full-field-editor">
          <div className="flex flex-wrap gap-2 text-xs" data-testid="gate1-field-filter">
            {[['priority',T('Recommended fields','Bidang utama')],['missing',T('Missing values','Nilai hilang')],['advanced',T('All fields','Semua bidang')]].map(([id,label])=><button type="button" key={id} aria-pressed={fieldFilter===id}
              className={'rounded-md border px-2 py-1 '+(fieldFilter===id?'border-[#801b24] font-semibold':'border-slate-200')} onClick={()=>{setFieldFilter(id);setField('')}}>{label}{id==='missing'?' ('+missingFields.length+')':''}</button>)}
          </div>
          <label className="text-xs font-semibold block">{T('What needs correcting?','Apa yang perlu diperbaiki?')}
            <select className={INPUT} value={field} onChange={e=>selectField(e.target.value)}
              data-testid="gate1-quick-field-select">
              <option value="">{T('Choose any field (only when needed)','Pilih bidang jika perlu')}</option>
              {orderedFields.length===0&&<option disabled>{T('No missing fields detected','Tidak ada bidang hilang terdeteksi')}</option>}
              {options.map(group=><optgroup key={group.title} label={group.title}>
                {group.items.map(key=><option value={key} key={key}>{pretty(key)}</option>)}
              </optgroup>)}
            </select>
          </label>
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
              </label>
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
              {!isLegacy&&<button type="button" className="text-xs underline text-slate-600" onClick={addAnother}
                disabled={!canSubmit||pending.length>=14}>{T('Correct another field','Perbaiki bidang lain')}</button>}
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
          <p className="text-xs text-slate-500">{T('Approve means you reviewed the saved information—not that any allegation is legally verified.',
            'Persetujuan berarti informasi telah ditinjau, bukan verifikasi tuduhan hukum.')}</p>
          {detail.information_review_status!=='OFFICER_VERIFIED'&&<div className="flex gap-2 flex-wrap">
            <button className="intel-ghost text-xs" type="button" disabled={busy||blockedApproval||pending.length>0||(field&&changed)}
              data-testid="gate1-one-click-approve" onClick={()=>decide('OFFICER_VERIFIED',true)}>
              {T('Looks correct · Approve & Next','Sudah benar · Setujui & Berikutnya')}</button>
            <button className="intel-ghost text-xs" type="button" disabled={busy||pending.length>0||(field&&changed)}
              onClick={()=>decide('HELD',true)}>{T('Hold for verification','Tunda untuk verifikasi')}</button>
          </div>}
          <details className="text-xs"><summary className="cursor-pointer text-slate-600">{T('Exclude or change review decision','Kecualikan atau ubah keputusan')}</summary>
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
          <div className="space-y-2 pt-2" data-testid="gate1-full-audit-history">
            <p>{T('Original source records are always retained. These are QA-only officer proposals.',
              'Catatan sumber asli tetap disimpan. Ini merupakan usulan petugas khusus QA.')}</p>
            {Object.entries(fields).filter(([,x])=>x.basis==='QA_OFFICER_ENRICHMENT').map(([key,x])=><div key={key} className="border-t pt-1 break-words">
              <strong>{pretty(key)}</strong>: {String(x.effective||'UNAVAILABLE').slice(0,300)} ({x.verification})</div>)}
            {view.history?.slice(0,15).map(h=><div className="border-t pt-1" key={h.revision}>
              #{h.revision} · {T('Officer','Petugas')} {h.actor_id} · {h.at} · {h.fields?.map(f=>pretty(f.field)).join(', ')} · {h.reason}
            </div>)}
          </div>
        </details>
      </>}
    </div>}

    {mode==='missing'&&<div className="space-y-3" data-testid="gate1-manual-intake">
      <div className="rounded-md bg-amber-50 border border-amber-200 p-3 text-xs text-amber-900">
        {T('For a post the provider did not return. Saved as an UNVERIFIED officer proposal, not a Social Listening record or published intelligence.',
          'Untuk unggahan yang tidak diambil penyedia. Disimpan sebagai usulan petugas BELUM TERVERIFIKASI, bukan data Social Listening atau intelijen terbit.')}
      </div>
      {view?.can_edit&&<div className="space-y-2">
        <label className="block text-xs font-semibold">{T('Link to the missing post','Tautan unggahan yang hilang')}
          <input type="url" className={INPUT} value={manual.source_url} onChange={e=>{const inferred=platformForUrl(e.target.value);setManual(x=>({...x,source_url:e.target.value,platform:inferred||x.platform}))}} placeholder="https://..."/>
        </label>
        <label className="block text-xs font-semibold">{T('Text or description','Teks atau deskripsi')}
          <textarea className={INPUT} rows={3} value={manual.text_content} onChange={e=>setManual(x=>({...x,text_content:e.target.value}))}
            placeholder={T('Paste the missing post text or describe what you found','Tempel teks unggahan atau jelaskan yang ditemukan')}/>
        </label>
        <label className="block text-xs font-semibold">{T('Platform','Platform')}
          <select data-testid="gate1-missing-post-platform" className={INPUT} value={manual.platform} onChange={e=>setManual(x=>({...x,platform:e.target.value}))}>
            {SUPPORTED_PLATFORMS.map(p=><option key={p} value={p}>{pretty(p)}</option>)}
          </select>
        </label>
        <details className="text-xs rounded-md bg-slate-50 p-2"><summary className="cursor-pointer">{T('More details (optional)','Rincian tambahan (opsional)')}</summary>
          <div className="space-y-2 pt-2">
            <label className="block">{T('Author or account','Penulis atau akun')}
              <input className={INPUT} value={manual.author_name} onChange={e=>setManual(x=>({...x,author_name:e.target.value}))}/>
            </label>
            <label className="block">{T('Why was it missed?','Mengapa tidak terambil?')}
              <textarea rows={2} className={INPUT} value={manual.reason} onChange={e=>setManual(x=>({...x,reason:e.target.value}))}/>
            </label>
          </div>
        </details>
        <button type="button" className="intel-ghost text-xs" onClick={saveMissing}
          data-testid="gate1-save-missing-evidence"
          disabled={busy||!validUrl(manual.source_url)||manual.text_content.trim().length<10}>
          {T('Save unverified proposal','Simpan usulan belum terverifikasi')}</button>
      </div>}
      <details className="rounded-md border p-3 text-xs">
        <summary className="cursor-pointer">{T('Previous missing-source proposals','Usulan sumber hilang sebelumnya')} ({manualList?.items?.length||0})</summary>
        {(manualList?.items||[]).map(x=><p className="border-t pt-2 mt-2" key={x.id}>
          #{x.id} · {x.title} · QA_UNVERIFIED · {x.officer_id}
        </p>)}
      </details>
    </div>}
    <p className="text-xs text-slate-500">{T('QA corrections do not train models, change canonical data or publish to Command Centre.',
      'Koreksi QA tidak melatih model, mengubah data asli, atau menerbitkan ke Command Centre.')}</p>
  </section>;
}
