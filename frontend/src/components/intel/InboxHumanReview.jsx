import {useEffect,useRef,useState} from 'react';
import {base44} from '@/api/base44Client';
import Gate1FullWorkbench from './Gate1FullWorkbench';
import {useLanguage} from '@/lib/LanguageContext';

const copy=(data)=>String(data||'');
const originalLink=(value)=>{try{const u=new URL(value);return ['https:','http:'].includes(u.protocol)?u.href:null}catch{return null}};
const actionLabels={
  VERIFY_UNASSESSED:'Unassessed — verify election relevance',
  REVIEW_UNCERTAIN:'Uncertain — officer review',
  SPOT_CHECK_EXCLUDED:'Excluded — check possible false negative',
  CHECK_RELEVANT_EVIDENCE:'Relevant — spot-check evidence',
  REVIEW_UNKNOWN_LABEL:'Unknown label — investigate'
};

export default function InboxHumanReview(){
  const {language}=useLanguage();
  const T=(en,id)=>language==='id'?id:en;
  const params=new URLSearchParams(window.location.search);
  const initialCampaign=params.get('campaign_id')||'';
  const initialSource=params.get('result_id')||'';
  const [campaigns,setCampaigns]=useState([]);
  const [campaignId,setCampaignId]=useState(initialCampaign);
  const [selectedId,setSelectedId]=useState(initialSource);
  const [sample,setSample]=useState(null);
  const [category,setCategory]=useState('all');
  const [reviewStatus,setReviewStatus]=useState('all');
  const currentCampaign=useRef(initialCampaign);
  const currentSelectedId=useRef(initialSource);
  const currentCategory=useRef('all');
  const currentReviewStatus=useRef('all');
  currentCampaign.current=campaignId;
  currentSelectedId.current=selectedId;
  currentCategory.current=category;
  currentReviewStatus.current=reviewStatus;
  const [nextCursor,setNextCursor]=useState(null);
  const [hasMore,setHasMore]=useState(false);
  const [loadingMore,setLoadingMore]=useState(false);
  const [detail,setDetail]=useState(null);
  const [loading,setLoading]=useState(true);
  const [sampleLoading,setSampleLoading]=useState(false);
  const [detailLoading,setDetailLoading]=useState(false);
  const [error,setError]=useState('');
  const [actionBusy,setActionBusy]=useState(false);
  const [rationale,setRationale]=useState('');
  const [correctionField,setCorrectionField]=useState('relevance');
  const [correctionValue,setCorrectionValue]=useState('RELEVANT');
  const [reviewDecision,setReviewDecision]=useState('NEEDS_REVIEW');
  const [history,setHistory]=useState(null);
  const [historyBusy,setHistoryBusy]=useState(false);
  const [handoff,setHandoff]=useState(null);
  const [handoffBusy,setHandoffBusy]=useState(false);
  const [feedback,setFeedback]=useState(null);
  const [feedbackBusy,setFeedbackBusy]=useState(false);
  const [triageChoice,setTriageChoice]=useState('NEEDS_RECHECK');
  const [triageReason,setTriageReason]=useState('');
  const [feedbackQueue,setFeedbackQueue]=useState(null);
  const [feedbackQueueBusy,setFeedbackQueueBusy]=useState(false);
  const [pilotStatus,setPilotStatus]=useState(null);
  const [pilotBusy,setPilotBusy]=useState(false);
  const [pilotError,setPilotError]=useState('');
  const [success,setSuccess]=useState('');
  const [version,setVersion]=useState(0);
  useEffect(()=>{
    let active=true;
    setLoading(true);setError('');
    base44.inboxHumanReview.campaigns()
      .then(r=>{
        if(!active)return;
        const list=r.campaigns||[];
        setCampaigns(list);
        setCampaignId(id=>list.some(c=>String(c.id)===String(id))?id:String(list[0]?.id||''));
      })
      .catch(e=>{if(active){setError(e.message||T('Unable to load review campaigns','Gagal memuat kampanye'));setCampaigns([]);}})
      .finally(()=>{if(active)setLoading(false)});
    return ()=>{active=false};
  },[]);
  useEffect(()=>{
    if(!campaignId){setSample(null);setNextCursor(null);setHasMore(false);return}
    let active=true;
    setSample(null);setNextCursor(null);setHasMore(false);
    setSampleLoading(true);setError('');
    base44.inboxHumanReview.queue(campaignId,{category,reviewStatus}).then(r=>{
      if(!active)return;
      setSample(r);setNextCursor(r.next_cursor||null);setHasMore(Boolean(r.has_more));
    }).catch(e=>{if(active){setSample(null);setError(e.message||'Review queue unavailable')}})
      .finally(()=>{if(active)setSampleLoading(false)});
    return ()=>{active=false};
  },[campaignId,category,reviewStatus,version]);
  async function loadMore(){
    if(!campaignId||!hasMore||!nextCursor||loadingMore||sampleLoading)return;
    setLoadingMore(true);setError('');
    try{
      const cursor=nextCursor, activeCampaign=campaignId, activeCategory=category, activeStatus=reviewStatus;
      const r=await base44.inboxHumanReview.queue(activeCampaign,{category:activeCategory,reviewStatus:activeStatus,cursor});
      // Navigation during an in-flight request must not append another campaign's records.
      if(activeCampaign!==currentCampaign.current||activeCategory!==currentCategory.current||activeStatus!==currentReviewStatus.current)return;
      setSample(previous=>({...r,items:[...(previous?.items||[]),...(r.items||[])]}));
      setNextCursor(r.next_cursor||null);setHasMore(Boolean(r.has_more));
    }catch(e){setError(e.message||'Unable to load more sources')}
    finally{setLoadingMore(false)}
  }
  useEffect(()=>{
    if(!campaignId||!selectedId){setDetail(null);return}
    let active=true;
    setDetailLoading(true);setError('');setDetail(null);
    base44.inboxHumanReview.source(campaignId,selectedId)
      .then(r=>{if(active)setDetail(r)})
      .catch(e=>{if(active)setError(e.message||'Evidence unavailable or outside scope')})
      .finally(()=>{if(active)setDetailLoading(false)});
    return ()=>{active=false};
  },[campaignId,selectedId,version]);
  function selectSource(id){
    currentSelectedId.current=String(id);
    setSelectedId(String(id));
    setSuccess('');setRationale('');setHistory(null);setHandoff(null);setFeedback(null);
    const q=new URLSearchParams(window.location.search);
    q.set('gate1','1');q.set('campaign_id',String(campaignId));q.set('result_id',String(id));
    window.history.replaceState(null,'','/inbox?'+q.toString());
  }
  function chooseCampaign(id){
    currentCampaign.current=String(id);currentSelectedId.current='';
    setCampaignId(String(id));setSelectedId('');setDetail(null);setSuccess('');setRationale('');setHistory(null);
    setPilotStatus(null);setPilotError('');setFeedbackQueue(null);setHandoff(null);setFeedback(null);
    const q=new URLSearchParams(window.location.search);
    q.set('gate1','1');q.set('campaign_id',String(id));q.delete('result_id');
    window.history.replaceState(null,'','/inbox?'+q.toString());
  }
  // The Gate 1 endpoint retains the versioned EvidenceAssessment model of
  // campaignAssessmentCorrection, but has its own pilot and optimistic-lock gate.
  async function correct(){
    if(!detail?.can_correct_relevance||actionBusy||rationale.trim().length<10)return;
    if(!window.confirm(T('Save this field correction and append an audit event?','Simpan koreksi bidang ini beserta jejak audit?')))return;
    setActionBusy(true);setError('');setSuccess('');
    try{
      const expected_revision=correctionField==='relevance'?detail.relevance_revision:detail.sentiment_revision;
      await base44.inboxHumanReview.correct(campaignId,detail.result_id,{
        field:correctionField,value:correctionValue,expected_revision,
        expected_assessment_id:detail.assessment_id,
        expected_source_digest:detail.source_integrity_digest,reason:rationale.trim()
      });
      setSuccess(T('Correction saved. Earlier versions remain available.','Koreksi tersimpan. Versi sebelumnya tetap tersedia.'));
      setRationale('');setHistory(null);setHandoff(null);setFeedback(null);setFeedbackQueue(null);setVersion(v=>v+1);
    }catch(e){setError(e.message||'Unable to save correction')}
    finally{setActionBusy(false)}
  }
  async function decide(){
    if(!detail?.can_review_information||actionBusy||rationale.trim().length<10)return;
    if(!window.confirm(T('Record this information review decision? This does not publish an insight.','Catat keputusan tinjauan informasi? Ini tidak menerbitkan insight.')))return;
    setActionBusy(true);setError('');setSuccess('');
    try{
      await base44.inboxHumanReview.decide(campaignId,detail.result_id,{
        status:reviewDecision,expected_revision:detail.information_review_revision,
        expected_assessment_id:detail.assessment_id,
        expected_sentiment_revision:detail.sentiment_revision,
        expected_enrichment_revision:detail.full_field_revision||0,
        expected_source_digest:detail.source_integrity_digest,
        reason:rationale.trim()
      });
      setSuccess(T('Information review decision recorded.','Keputusan tinjauan informasi tercatat.'));
      setRationale('');setHistory(null);setVersion(v=>v+1);
    }catch(e){setError(e.message||'Unable to save review decision')}
    finally{setActionBusy(false)}
  }
  async function openHistory(){
    if(!campaignId||!selectedId||historyBusy)return;
    setHistoryBusy(true);setError('');
    try{setHistory(await base44.inboxHumanReview.history(campaignId,selectedId))}
    catch(e){setError(e.message||'Review history unavailable')}
    finally{setHistoryBusy(false)}
  }
  async function restore(field,targetRevision){
    if(!detail?.can_correct_relevance||actionBusy||rationale.trim().length<10)return;
    if(!window.confirm(T('Restore this historical value as a NEW audited correction?','Kembalikan nilai lama sebagai koreksi BARU yang diaudit?')))return;
    setActionBusy(true);setError('');setSuccess('');
    try{
      await base44.inboxHumanReview.restore(campaignId,detail.result_id,{
        field,target_revision:targetRevision,
        expected_revision:field==='relevance'?detail.relevance_revision:detail.sentiment_revision,
        expected_assessment_id:detail.assessment_id,
        expected_source_digest:detail.source_integrity_digest,
        reason:rationale.trim()
      });
      setSuccess(T('Historical value restored as a new revision.','Nilai lama dikembalikan sebagai revisi baru.'));
      setRationale('');setHistory(null);setVersion(v=>v+1);
    }catch(e){setError(e.message||'Could not restore historical value')}
    finally{setActionBusy(false)}
  }
  async function checkPilotReadiness(){
    if(!campaignId||pilotBusy)return;
    const requestCampaign=campaignId;
    setPilotBusy(true);setPilotStatus(null);setPilotError('');
    try {
      const result=await base44.inboxHumanReview.pilotReadiness(requestCampaign);
      if(requestCampaign===currentCampaign.current)setPilotStatus(result);
    } catch(e) {
      if(requestCampaign===currentCampaign.current)
        setPilotError(T('Administrator access is required to check pilot readiness.','Akses administrator diperlukan untuk memeriksa kesiapan pilot.'));
    } finally {setPilotBusy(false)}
  }
  const selectedCampaign=campaigns.find(c=>String(c.id)===String(campaignId));
  const qaCampaignSelected=['BAWASLU Gate 1 QA Pilot','Politik Uang'].includes(selectedCampaign?.name);
  const realQaSelected=String(campaignId)==='9'&&selectedCampaign?.name==='Politik Uang';
  async function openGate2Readiness(){
    if(!campaignId||!detail||handoffBusy)return;
    const key=String(detail.result_id), campaign=String(campaignId);
    setHandoffBusy(true);setHandoff(null);setError('');
    try{
      const packet=await base44.inboxHumanReview.gate2Readiness(campaign,key);
      if(campaign===currentCampaign.current&&currentSelectedId.current===key)setHandoff(packet);
    }catch(e){setError(e.message||T('Handoff readiness unavailable','Kesiapan alih tahap tidak tersedia'))}
    finally{setHandoffBusy(false)}
  }
  async function openFeedback(){
    if(!campaignId||!detail||feedbackBusy)return;
    const key=String(detail.result_id), campaign=String(campaignId);
    setFeedbackBusy(true);setFeedback(null);setError('');
    try{
      const response=await base44.inboxHumanReview.sourceFeedback(campaign,key);
      if(campaign===currentCampaign.current&&currentSelectedId.current===key)setFeedback(response);
    }catch(e){setError(e.message||T('Feedback history unavailable','Riwayat umpan balik tidak tersedia'))}
    finally{setFeedbackBusy(false)}
  }
  async function triageFeedback(event){
    if(!feedback?.can_triage||actionBusy||triageReason.trim().length<10||!detail)return;
    if(!window.confirm(T('Record this offline feedback triage? This will NOT train the AI.','Catat triase umpan balik offline ini? AI TIDAK akan dilatih.')))return;
    setActionBusy(true);setError('');setSuccess('');
    try{
      await base44.inboxHumanReview.triageFeedback(campaignId,detail.result_id,{
        correction_event_id:event.correction_event_id,
        expected_decision_revision:event.triage_revision,
        decision:triageChoice,rationale:triageReason.trim(),
        expected_source_digest:detail.source_integrity_digest
      });
      setSuccess(T('Offline feedback triage saved. Model training remains disabled.','Triase umpan balik offline tersimpan. Pelatihan model tetap nonaktif.'));
      setTriageReason('');setFeedback(null);setFeedbackQueue(null);setHandoff(null);
      setVersion(v=>v+1);
    }catch(e){setError(e.message||T('Feedback decision rejected; refresh and try again','Keputusan ditolak; segarkan dan coba lagi'))}
    finally{setActionBusy(false)}
  }
  async function openFeedbackQueue(more=false){
    if(!campaignId||feedbackQueueBusy)return;
    const campaign=String(campaignId);
    setFeedbackQueueBusy(true);setError('');
    try{
      const response=await base44.inboxHumanReview.campaignFeedback(campaign,{
        cursor:more?feedbackQueue?.next_cursor:null
      });
      if(campaign!==currentCampaign.current)return;
      setFeedbackQueue(previous=>more?{
        ...response,items:[...(previous?.items||[]),...(response.items||[])]
      }:response);
    }catch(e){setError(e.message||T('Cannot load correction feedback','Tidak dapat memuat umpan balik koreksi'))}
    finally{setFeedbackQueueBusy(false)}
  }
  // Indicators refer only to currently loaded, authorized review items.
  const loaded=sample?.items||[];
  const counts=loaded.reduce((acc,item)=>({...acc,[item.category]:(acc[item.category]||0)+1}),{});
  const statusCounts=loaded.reduce((acc,item)=>({...acc,[item.information_review_status||'NEEDS_REVIEW']:(acc[item.information_review_status||'NEEDS_REVIEW']||0)+1}),{});
  return <div className="space-y-4" data-testid="inbox-human-gate1">
    <div className="flex flex-wrap items-center justify-between gap-3">
      <div><h2 className="text-xl font-bold text-slate-900">{T('Human Review · Gate 1','Tinjauan Petugas · Gate 1')}</h2>
        <p className="text-sm text-slate-600">{T('Review saved election information, including posts excluded from the standard Inbox. Not a legal violation finding.','Periksa informasi pemilu tersimpan, termasuk unggahan yang dikecualikan dari Inbox biasa. Bukan temuan pelanggaran hukum.')}</p>
      </div>
      <a className="intel-ghost text-sm" href="/inbox">{T('Back to standard Inbox','Kembali ke Inbox biasa')}</a>
    </div>
    <section className="intel-card p-4 space-y-3">
      <label className="block text-sm font-semibold">{T('Campaign','Kampanye')}
        <select aria-label="Human Review campaign" className="intel-input mt-1 w-full" value={campaignId} disabled={loading} onChange={e=>chooseCampaign(e.target.value)}>
          <option value="">{T('Select campaign','Pilih kampanye')}</option>
          {campaigns.map(c=><option key={c.id} value={c.id}>{c.name}</option>)}
        </select>
      </label>
      {loading&&<p role="status">{T('Loading authorized campaigns…','Memuat kampanye yang diizinkan…')}</p>}
      {error&&<p role="alert" className="rounded-lg bg-red-50 p-3 text-sm text-red-800">{error}</p>}
      {!error&&!loading&&campaigns.length===0&&<p>{T('No authorized campaigns.','Tidak ada kampanye yang diizinkan.')}</p>}
      {qaCampaignSelected&&<div className="rounded-lg border border-slate-200 bg-slate-50 p-3 space-y-2 text-sm" data-testid="gate1-qa-pilot-preflight">
        <h3 className="font-semibold">{realQaSelected?T('Politik Uang · officer override QA','Politik Uang · QA koreksi petugas'):T('Synthetic QA write-pilot preflight','Pemeriksaan kesiapan pilot QA sintetis')}</h3>
        <p className="text-xs text-slate-600">{realQaSelected?T('Existing campaign evidence is for controlled QA only. Officer overrides are stored as separate audit events; original evidence and saved AI assessments are unchanged. No publication or AI training.','Bukti kampanye yang ada hanya untuk QA. Koreksi petugas dicatat terpisah; bukti asli dan penilaian AI tidak berubah. Tanpa publikasi atau pelatihan AI.'):T('This read-only check cannot enable correction writes or create test evidence. The QA campaign must remain a draft and all pilot posts must be synthetic.','Pemeriksaan hanya-baca ini tidak dapat mengaktifkan koreksi atau membuat bukti uji. Kampanye QA harus tetap draf dan semua unggahan harus sintetis.')}</p>
        <button type="button" data-testid="gate1-check-pilot-readiness" className="intel-ghost text-xs" onClick={checkPilotReadiness} disabled={pilotBusy}>
          {pilotBusy?T('Checking pilot readiness…','Memeriksa kesiapan pilot…'):T('Check staging pilot readiness','Periksa kesiapan pilot staging')}
        </button>
        {pilotError&&<p role="alert" className="text-red-700 text-xs">{pilotError}</p>}
        {pilotStatus&&<div className="space-y-1 text-xs" data-testid="gate1-pilot-readiness-report">
          <p>{T('Campaign status','Status kampanye')}: <strong>{pilotStatus.pilot_campaign_draft_and_named?'QA DRAFT':'NOT ELIGIBLE'}</strong></p>
          <p>{realQaSelected?T('Real evidence for QA','Bukti nyata untuk QA'):T('Synthetic linked sources','Sumber sintetis tertaut')}: <strong>{realQaSelected?pilotStatus.qa_real_evidence_count:pilotStatus.synthetic_source_count}</strong></p>
          {pilotStatus.linked_source_count===0&&<p className="rounded-md border border-amber-200 bg-amber-50 p-2 text-amber-900" data-testid="gate1-empty-campaign-diagnosis">{T('This QA campaign has no linked evidence. Changing filters cannot reveal posts. Test fixtures must be provisioned in an isolated QA database; do not import fictional posts into the shared operational database.','Kampanye QA ini belum memiliki bukti tertaut. Mengganti filter tidak akan menampilkan unggahan. Data uji harus disiapkan di basis data QA terisolasi; jangan masukkan unggahan fiktif ke basis data operasional bersama.')}</p>}
          {!realQaSelected&&<p>{T('Non-synthetic links','Tautan non-sintetis')}: <strong>{pilotStatus.non_synthetic_link_count}</strong></p>}
          <p>{T('Correction writes','Koreksi')}: <strong>{pilotStatus.correction_writes_enabled?'ENABLED':'DISABLED'}</strong></p>
          <p>{T('Pilot eligibility','Kelayakan pilot')}: <strong>{pilotStatus.ready_for_write_pilot?'ELIGIBLE FOR QA':'NOT READY · SAFE BLOCK'}</strong></p>
        </div>}
      </div>}
      <label className="block text-sm font-semibold">{T('Review category','Kategori tinjauan')}
        <select data-testid="gate1-category-filter" className="intel-input mt-1 w-full" value={category} onChange={e=>{currentCategory.current=e.target.value;setCategory(e.target.value)}}>
          <option value="all">{T('All ordinary evidence','Semua bukti biasa')}</option>
          <option value="unassessed">{T('Unassessed','Belum dinilai')}</option>
          <option value="uncertain">{T('Uncertain','Tidak pasti')}</option>
          <option value="excluded">{T('AI-excluded · false-negative checks','Dikecualikan AI · cek kelalaian')}</option>
          <option value="relevant">{T('Relevant · sampled checks','Relevan · pemeriksaan')}</option>
          <option value="other">{T('Unknown assessment labels','Label penilaian lain')}</option>
        </select>
      </label>
      {sample&&<div className="grid grid-cols-2 sm:grid-cols-4 gap-2 text-sm">
        <p>{T('Loaded sources','Sumber dimuat')}: <strong>{sample.items?.length||0}</strong></p>
        <p>{T('Unassessed (loaded)','Belum dinilai (dimuat)')}: <strong>{counts.unassessed||0}</strong></p>
        <p>{T('Excluded / uncertain (loaded)','Dikecualikan / ragu (dimuat)')}: <strong>{counts.excluded_or_uncertain||0}</strong></p>
        <p>{T('Relevant (loaded)','Relevan (dimuat)')}: <strong>{counts.relevant||0}</strong></p>
      </div>}
      <label className="block text-sm font-semibold">{T('Information QA status','Status QA informasi')}
        <select data-testid="gate1-review-status-filter" className="intel-input mt-1 w-full" value={reviewStatus} onChange={e=>{currentReviewStatus.current=e.target.value;setReviewStatus(e.target.value)}}>
          <option value="all">{T('All QA statuses','Semua status QA')}</option>
          <option value="needs_review">{T('Needs review','Perlu ditinjau')}</option>
          <option value="officer_verified">{T('Information reviewed','Informasi diperiksa petugas')}</option>
          <option value="held">{T('Held for verification','Ditahan untuk verifikasi')}</option>
          <option value="excluded">{T('Excluded by officer','Dikecualikan oleh petugas')}</option>
          <option value="revalidation_required">{T('Needs revalidation','Perlu validasi ulang')}</option>
        </select>
      </label>
      <div className="grid grid-cols-2 sm:grid-cols-4 gap-2 text-xs rounded-lg border border-slate-200 p-3" data-testid="gate1-qa-coverage">
        <p>{T('Needs review','Perlu ditinjau')}: <strong>{statusCounts.NEEDS_REVIEW||0}</strong></p>
        <p>{T('Reviewed information','Informasi diperiksa')}: <strong>{statusCounts.OFFICER_VERIFIED||0}</strong></p>
        <p>{T('Held / excluded','Ditahan / dikecualikan')}: <strong>{(statusCounts.HELD||0)+(statusCounts.EXCLUDED||0)}</strong></p>
        <p>{T('Revalidation required','Perlu validasi ulang')}: <strong>{statusCounts.REVALIDATION_REQUIRED||0}</strong></p>
      </div>
      <p className="text-xs text-slate-500">{T('Counts reflect the currently loaded authorized evidence only—not the full campaign, AI accuracy, or a violation rate. Watchlist-only links are excluded.','Jumlah hanya berdasarkan bukti yang sudah dimuat dan diizinkan—bukan seluruh kampanye, akurasi AI, atau tingkat pelanggaran. Tautan khusus watchlist dikecualikan.')}</p>
      <div className="border-t border-slate-200 pt-3 space-y-2" data-testid="gate1-feedback-queue">
        <button type="button" className="intel-ghost text-xs" disabled={feedbackQueueBusy} onClick={()=>openFeedbackQueue(false)}>
          {feedbackQueueBusy?T('Loading feedback…','Memuat umpan balik…'):T('View officer correction feedback queue','Lihat antrean umpan balik koreksi petugas')}
        </button>
        {feedbackQueue&&<div className="space-y-2">
          <p className="text-xs text-slate-600">{T('Correction feedback candidates (loaded only). These are NOT training examples or verified legal findings.','Kandidat umpan balik koreksi (yang dimuat saja). Ini BUKAN contoh pelatihan atau temuan hukum terverifikasi.')}</p>
          {(feedbackQueue.items||[]).map(item=><button type="button" key={item.correction_event_id}
            onClick={()=>selectSource(item.result_id)} className="w-full rounded-lg border border-slate-200 bg-white p-2 text-left text-xs">
            <strong>#{item.result_id} · {item.field}</strong> · {item.previous_effective_value} → {item.officer_value}
            <span className="block text-slate-600">{item.triage_decision} · {item.correction_current?T('Current','Berlaku'):T('Superseded','Diganti')}</span>
          </button>)}
          {feedbackQueue.items?.length===0&&<p className="text-xs text-slate-500">{T('No audited officer corrections found for authorized evidence.','Belum ada koreksi petugas yang diaudit untuk bukti berizin.')}</p>}
          {feedbackQueue.has_more&&<button className="intel-ghost text-xs" type="button" disabled={feedbackQueueBusy} onClick={()=>openFeedbackQueue(true)}>{T('Load more feedback','Muat umpan balik lagi')}</button>}
          <p className="text-xs text-slate-500">{T('This queue does not export data or trigger AI training.','Antrean ini tidak mengekspor data atau melatih AI.')}</p>
        </div>}
      </div>
    </section>
    {sampleLoading&&<p role="status">{T('Loading review queue…','Memuat antrean tinjauan…')}</p>}
    <div className="grid gap-4 lg:grid-cols-[minmax(0,1fr)_minmax(0,1.1fr)]">
      <section className="intel-card p-4 space-y-2" aria-label="Human Review source queue">
        <h3 className="font-bold">{T('Needs Human Review','Perlu Tinjauan Petugas')}</h3>
        {(sample?.items||[]).map(item=><button type="button" key={item.result_id}
          onClick={()=>selectSource(item.result_id)}
          className={'block w-full rounded-lg border p-3 text-left text-sm hover:bg-slate-50 '+(String(selectedId)===String(item.result_id)?'border-[#801b24] bg-red-50':'border-slate-200')}>
          <span className="font-semibold">{item.platform||'Social'} · #{item.result_id}</span>
          <span className="block text-slate-600">{actionLabels[item.action]||item.action}</span>
          <span className="block text-xs text-slate-500">{T('Current relevance','Relevansi saat ini')}: {item.relevance} ({item.relevance_basis||'SAVED_ASSESSMENT'})</span>
          {item.information_review_status&&<span className="block text-xs text-slate-500">{T('Information QA','QA informasi')}: {item.information_review_status}</span>}
        </button>)}
        {!sampleLoading&&sample&&sample.items?.length===0&&!hasMore&&<p className="text-sm text-slate-500">{T('No ordinary campaign evidence matches this filter. If all categories are empty, click Check staging pilot readiness to inspect linked-source counts.','Tidak ada bukti kampanye biasa yang cocok dengan filter ini. Jika semua kategori kosong, pilih Periksa kesiapan uji coba staging untuk melihat jumlah sumber tertaut.')}</p>}
        {hasMore&&<button data-testid="gate1-load-more" type="button" className="intel-ghost w-full text-sm" disabled={loadingMore||sampleLoading} onClick={loadMore}>{loadingMore?T('Loading more…','Memuat lagi…'):T('Load more evidence','Muat lebih banyak bukti')}</button>}
        {sample?.scan_limited&&<p className="text-xs text-amber-800">{T('Search continues on the next page; results are not complete yet.','Pencarian berlanjut pada halaman berikutnya; hasil belum lengkap.')}</p>}
      </section>
      <section className="intel-card p-4 space-y-3" aria-label="Human Review evidence detail">
        <h3 className="font-bold">{T('Original evidence & assessment','Bukti asli dan penilaian')}</h3>
        {detailLoading&&<p role="status">{T('Opening saved source…','Membuka sumber tersimpan…')}</p>}
        {!detail&&!detailLoading&&<p className="text-sm text-slate-500">{selectedId?T('Evidence could not be loaded.','Bukti tidak dapat dimuat.'):T('Select a post to review its original evidence.','Pilih unggahan untuk memeriksa bukti asli.')}</p>}
        {detail&&<>
          <p className="text-sm font-semibold">{detail.platform||'Social'} · #{detail.result_id} · {detail.campaign_name}</p>
          <p className="text-xs text-slate-500">{detail.author_name||T('Unknown author','Penulis tidak diketahui')} · {detail.published_at||T('Date unavailable','Tanggal tidak tersedia')}</p>
          <p className="whitespace-pre-wrap break-words rounded-lg bg-slate-50 p-3 text-sm">{detail.text_content||T('No text saved.','Tidak ada teks tersimpan.')}</p>
          {detail.content_truncated&&<p className="text-xs text-amber-800">{T('Text truncated. Check the original source.','Teks terpotong. Periksa sumber asli.')}</p>}
          {originalLink(detail.canonical_url)&&<a target="_blank" rel="noopener noreferrer" className="text-sm font-semibold text-[#801b24] underline" href={originalLink(detail.canonical_url)}>{T('Open original source','Buka sumber asli')}</a>}
          <div className="rounded-lg border border-slate-200 p-3 text-sm space-y-1">
            <p><strong>{T('Original AI relevance','Relevansi AI asli')}:</strong> {detail.original_ai_relevance||T('Not assessed','Belum dinilai')}</p>
            <p><strong>{T('Effective relevance','Relevansi efektif')}:</strong> {detail.effective_relevance} ({detail.relevance_basis})</p>
            <p><strong>{T('AI sentiment','Sentimen AI')}:</strong> {detail.ai_sentiment}</p>
            <p><strong>{T('Effective sentiment','Sentimen efektif')}:</strong> {detail.effective_sentiment} ({detail.sentiment_basis})</p>
            <p><strong>{T('Assessment version','Versi penilaian')}:</strong> {detail.assessment_version??T('Not assessed','Belum dinilai')}</p>
            <p><strong>{T('Last officer review','Tinjauan petugas terakhir')}:</strong> {detail.officer_review_decision||T('Not recorded','Belum tercatat')}</p>
            <p data-testid="gate1-information-status"><strong>{T('Information QA status','Status QA informasi')}:</strong> {detail.information_review_status} {detail.information_review_stale?'· '+T('Requires revalidation','Perlu validasi ulang'):''}</p>
            {detail.information_review_reviewer_id&&<p className="text-xs text-slate-600">{T('Reviewer','Pemeriksa')}: {detail.information_review_reviewer_id} · {detail.information_review_at}</p>}
            {detail.relevance_explanation&&<p className="text-xs text-slate-600">{detail.relevance_explanation}</p>}
          </div>
          {detail.can_review_information?<div className="border-t pt-3 space-y-3" data-testid="gate1-correction-workbench">
            {detail.qa_audit_only&&<p data-testid="gate1-real-qa-safety" className="rounded-md border border-amber-200 bg-amber-50 p-2 text-xs text-amber-900">{T('QA ONLY — your override changes Human Gate 1 review views, not the saved AI assessment, original Social Listening data, or Command Centre.','KHUSUS QA — koreksi hanya mengubah tampilan Human Gate 1, bukan penilaian AI tersimpan, data Social Listening asli, atau Command Centre.')}</p>}
            <h4 className="font-semibold text-sm">{T('Officer information review & corrections','Tinjauan informasi & koreksi petugas')}</h4>
            <p className="text-xs text-slate-500">{T('Officer Verified means this saved INFORMATION snapshot was reviewed; it does not verify allegations or legal violations. Field corrections are not whole-record verification. No automatic AI training or Command Centre publication.','Terverifikasi Petugas berarti cuplikan INFORMASI ini telah ditinjau; bukan verifikasi tuduhan atau pelanggaran hukum. Koreksi satu bidang bukan verifikasi seluruh catatan. Tidak ada pelatihan AI atau publikasi otomatis.')}</p>
            <textarea aria-label="Review reason" className="intel-input w-full" rows={3} value={rationale} onChange={e=>setRationale(e.target.value)} placeholder={T('Reason and supporting explanation (minimum 10 characters)','Alasan dan penjelasan pendukung (minimal 10 karakter)')}/>
            {detail.can_correct_relevance&&<div className="grid grid-cols-1 sm:grid-cols-2 gap-2">
              <label className="text-xs font-semibold">{T('Correct field','Bidang yang diperbaiki')}
                <select className="intel-input w-full mt-1" value={correctionField} onChange={e=>{setCorrectionField(e.target.value);setCorrectionValue(e.target.value==='relevance'?'RELEVANT':'NEUTRAL')}}>
                  <option value="relevance">{T('Election relevance','Relevansi pemilu')}</option>
                  <option value="sentiment">{T('Sentiment','Sentimen')}</option>
                </select>
              </label>
              <label className="text-xs font-semibold">{T('New value','Nilai baru')}
                <select className="intel-input w-full mt-1" value={correctionValue} onChange={e=>setCorrectionValue(e.target.value)}>
                  {(correctionField==='relevance'?['RELEVANT','HIGHLY_RELEVANT','IRRELEVANT','UNCERTAIN']:['POSITIVE','NEUTRAL','NEGATIVE']).map(v=><option value={v} key={v}>{v}</option>)}
                </select>
              </label>
              <button type="button" data-testid="gate1-save-field-correction" className="intel-ghost text-xs" onClick={correct} disabled={actionBusy||rationale.trim().length<10}>{T('Save audited field correction','Simpan koreksi yang diaudit')}</button>
            </div>}
            <label className="text-xs font-semibold">{T('Information review decision','Keputusan tinjauan informasi')}
              <select data-testid="gate1-review-decision" className="intel-input w-full mt-1" value={reviewDecision} onChange={e=>setReviewDecision(e.target.value)}>
                {['NEEDS_REVIEW','OFFICER_VERIFIED','HELD','EXCLUDED'].map(v=><option value={v} key={v}>{v}</option>)}
              </select>
            </label>
            <button type="button" className="intel-ghost text-xs" data-testid="gate1-save-review-decision" disabled={actionBusy||rationale.trim().length<10} onClick={decide}>{T('Record information QA decision','Catat keputusan QA informasi')}</button>
          </div>:<p className="rounded-lg bg-amber-50 p-3 text-xs text-amber-900">{detail.reason_if_not_actionable||T('Read-only. Officer corrections are not enabled.','Hanya-baca. Koreksi belum diaktifkan.')}</p>}
          <Gate1FullWorkbench campaignId={campaignId} detail={detail} onSaved={()=>{setHandoff(null);setFeedback(null);setFeedbackQueue(null);setHistory(null);setVersion(v=>v+1)}}/>
          <div className="border-t pt-3 space-y-2" data-testid="gate1-gate2-readiness">
            <h4 className="font-semibold text-sm">{T('Human Gate 2 handoff readiness','Kesiapan alih tahap Human Gate 2')}</h4>
            <p className="text-xs text-slate-600">{T('Information is not an insight. This preview never creates, approves, or publishes an insight.','Informasi bukan insight. Pratinjau ini tidak membuat, menyetujui, atau menerbitkan insight.')}</p>
            <button className="intel-ghost text-xs" type="button" disabled={handoffBusy} onClick={openGate2Readiness}>{handoffBusy?T('Checking…','Memeriksa…'):T('Check insight-draft readiness','Periksa kesiapan draf insight')}</button>
            {handoff&&<div className="rounded-lg bg-slate-50 border border-slate-200 p-3 space-y-2 text-xs" data-testid="gate1-gate2-packet">
              <p><strong>{T('Status','Status')}:</strong> {handoff.readiness}</p>
              <p><strong>{T('Source ID','ID sumber')}:</strong> #{handoff.result_id} · {T('Assessment','Penilaian')} v{handoff.assessment_version??'-'}</p>
              {handoff.review_blockers?.length>0&&<p><strong>{T('Blockers','Hambatan')}:</strong> {handoff.review_blockers.join(' · ')}</p>}
              <p className="text-slate-600">{T('Preliminary only. Independent Gate 2 approval is always required. No Command Centre publication.','Hanya pendahuluan. Persetujuan Human Gate 2 secara independen selalu diperlukan. Tidak ada publikasi ke Command Centre.')}</p>
            </div>}
          </div>
          <div className="border-t pt-3 space-y-2" data-testid="gate1-offline-feedback">
            <h4 className="font-semibold text-sm">{T('Officer feedback for future AI evaluation','Umpan balik petugas untuk evaluasi AI mendatang')}</h4>
            <p className="text-xs text-slate-600">{T('Officer corrections can be reviewed offline; they do not train or update the AI automatically.','Koreksi petugas dapat ditinjau secara offline; tidak melatih atau memperbarui AI secara otomatis.')}</p>
            <button className="intel-ghost text-xs" type="button" disabled={feedbackBusy} onClick={openFeedback}>{feedbackBusy?T('Loading…','Memuat…'):T('View correction feedback','Lihat umpan balik koreksi')}</button>
            {feedback&&<div className="space-y-3">
              {(feedback.items||[]).map(item=><div key={item.correction_event_id} className="rounded-lg border border-slate-200 p-3 space-y-2 text-xs" data-testid="gate1-feedback-item">
                <p><strong>{item.field}</strong>: {item.previous_effective_value} → {item.officer_value}</p>
                <p>{T('Reviewer','Pemeriksa')}: {item.officer_id} · {T('Correction','Koreksi')} #{item.correction_event_id}</p>
                <p>{T('Information QA','QA informasi')}: {item.information_review_status}</p>
                <p>{T('Offline disposition','Keputusan offline')}: <strong>{item.triage_decision}</strong> {item.correction_current?'':'· '+T('Superseded','Diganti')}</p>
                {feedback.can_triage&&<div className="space-y-2" data-testid="gate1-feedback-triage">
                  <label className="block">{T('Evaluation disposition','Keputusan evaluasi')}
                    <select className="intel-input w-full mt-1" value={triageChoice} onChange={e=>setTriageChoice(e.target.value)}>
                      <option value="NEEDS_RECHECK">{T('Needs recheck','Perlu pemeriksaan ulang')}</option>
                      <option value="ACCEPT_OFFLINE_EVALUATION">{T('Accept for offline evaluation only','Terima hanya untuk evaluasi offline')}</option>
                      <option value="REJECT_OFFLINE_EVALUATION">{T('Reject from offline evaluation','Tolak evaluasi offline')}</option>
                    </select>
                  </label>
                  <textarea aria-label="Offline feedback triage reason" className="intel-input w-full" rows={2} value={triageReason} onChange={e=>setTriageReason(e.target.value)} placeholder={T('Reason, minimum 10 characters','Alasan, minimal 10 karakter')}/>
                  <button type="button" className="intel-ghost text-xs" disabled={actionBusy||triageReason.trim().length<10} onClick={()=>triageFeedback(item)}>{T('Record audited offline decision','Catat keputusan offline yang diaudit')}</button>
                </div>}
              </div>)}
              {feedback.items?.length===0&&<p className="text-xs text-slate-500">{T('No officer corrections have been recorded for this evidence.','Belum ada koreksi petugas untuk bukti ini.')}</p>}
              <p className="text-xs text-slate-500">{T('Gate 3 must separately govern any later model-learning process. Training remains disabled.','Gate 3 harus mengatur proses pembelajaran model terpisah. Pelatihan tetap nonaktif.')}</p>
            </div>}
          </div>
          <div className="border-t pt-3 space-y-2" data-testid="gate1-audit-history">
            <button type="button" className="intel-ghost text-xs" onClick={openHistory} disabled={historyBusy}>{historyBusy?T('Loading history…','Memuat riwayat…'):T('View review & correction history','Lihat riwayat tinjauan & koreksi')}</button>
            {history&&<div className="rounded-lg border p-3 text-xs space-y-3">
              <p className="text-slate-600">{T('Original records are retained. Restoring creates a new revision; enter a reason above first.','Catatan asli disimpan. Pemulihan membuat revisi baru; masukkan alasan di atas dahulu.')}</p>
              <h5 className="font-semibold">{T('Relevance versions','Versi relevansi')}</h5>
              {(history.relevance_history||[]).map(x=><div className="flex items-center justify-between gap-2" key={'relevance'+x.revision}>
                <span>v{x.revision} · {x.value} · {x.model_version}</span>
                {detail.can_correct_relevance&&x.revision!==detail.relevance_revision&&<button className="intel-ghost text-xs" type="button" disabled={actionBusy||rationale.trim().length<10} onClick={()=>restore('relevance',x.revision)}>{T('Restore','Pulihkan')}</button>}
              </div>)}
              <h5 className="font-semibold">{T('Sentiment corrections','Koreksi sentimen')}</h5>
              {detail.can_correct_sentiment&&detail.sentiment_revision>0&&
                <button className="intel-ghost text-xs" type="button" disabled={actionBusy||rationale.trim().length<10} onClick={()=>restore('sentiment',0)}>{T('Restore saved AI sentiment as new revision','Pulihkan sentimen AI tersimpan sebagai revisi baru')}</button>}
              {(history.sentiment_history||[]).map(x=><div className="flex items-center justify-between gap-2" key={'sentiment'+x.revision}>
                <span>#{x.revision} · {x.value} · {T('Officer','Petugas')} {x.reviewer_id}</span>
                {detail.can_correct_sentiment&&x.revision!==detail.sentiment_revision&&<button className="intel-ghost text-xs" type="button" disabled={actionBusy||rationale.trim().length<10} onClick={()=>restore('sentiment',x.revision)}>{T('Restore','Pulihkan')}</button>}
              </div>)}
              <h5 className="font-semibold">{T('Audit trail','Jejak audit')}</h5>
              {(history.audit_history||[]).map(x=><p key={x.revision} className="break-words text-slate-600">#{x.revision} · {x.action} · {x.reviewer_id} · {x.created_at} · {x.reason||''}</p>)}
            </div>}
          </div>
          {success&&<p role="status" className="rounded-lg bg-green-50 p-3 text-sm text-green-800">{success}</p>}
        </>}
      </section>
    </div>
  </div>;
}
