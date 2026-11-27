import {useEffect,useRef,useState} from 'react';
import {base44} from '@/api/base44Client';
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
  const currentCampaign=useRef(initialCampaign);
  const currentCategory=useRef('all');
  currentCampaign.current=campaignId;
  currentCategory.current=category;
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
    base44.inboxHumanReview.queue(campaignId,{category}).then(r=>{
      if(!active)return;
      setSample(r);setNextCursor(r.next_cursor||null);setHasMore(Boolean(r.has_more));
    }).catch(e=>{if(active){setSample(null);setError(e.message||'Review queue unavailable')}})
      .finally(()=>{if(active)setSampleLoading(false)});
    return ()=>{active=false};
  },[campaignId,category,version]);
  async function loadMore(){
    if(!campaignId||!hasMore||!nextCursor||loadingMore||sampleLoading)return;
    setLoadingMore(true);setError('');
    try{
      const cursor=nextCursor, activeCampaign=campaignId, activeCategory=category;
      const r=await base44.inboxHumanReview.queue(activeCampaign,{category:activeCategory,cursor});
      // Navigation during an in-flight request must not append another campaign's records.
      if(activeCampaign!==currentCampaign.current||activeCategory!==currentCategory.current)return;
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
    setSelectedId(String(id));
    setSuccess('');setRationale('');setHistory(null);
    const q=new URLSearchParams(window.location.search);
    q.set('gate1','1');q.set('campaign_id',String(campaignId));q.set('result_id',String(id));
    window.history.replaceState(null,'','/inbox?'+q.toString());
  }
  function chooseCampaign(id){
    currentCampaign.current=String(id);
    setCampaignId(String(id));setSelectedId('');setDetail(null);setSuccess('');setRationale('');setHistory(null);
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
        field:correctionField,value:correctionValue,expected_revision,reason:rationale.trim()
      });
      setSuccess(T('Correction saved. Earlier versions remain available.','Koreksi tersimpan. Versi sebelumnya tetap tersedia.'));
      setRationale('');setHistory(null);setVersion(v=>v+1);
    }catch(e){setError(e.message||'Unable to save correction')}
    finally{setActionBusy(false)}
  }
  async function decide(){
    if(!detail?.can_review_information||actionBusy||rationale.trim().length<10)return;
    if(!window.confirm(T('Record this information review decision? This does not publish an insight.','Catat keputusan tinjauan informasi? Ini tidak menerbitkan insight.')))return;
    setActionBusy(true);setError('');setSuccess('');
    try{
      await base44.inboxHumanReview.decide(campaignId,detail.result_id,{
        status:reviewDecision,expected_revision:detail.information_review_revision,reason:rationale.trim()
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
        reason:rationale.trim()
      });
      setSuccess(T('Historical value restored as a new revision.','Nilai lama dikembalikan sebagai revisi baru.'));
      setRationale('');setHistory(null);setVersion(v=>v+1);
    }catch(e){setError(e.message||'Could not restore historical value')}
    finally{setActionBusy(false)}
  }
  const counts=sample?.page_counts||{};
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
        <p>{T('Unassessed (page)','Belum dinilai (halaman)')}: <strong>{counts.unassessed||0}</strong></p>
        <p>{T('Excluded / uncertain (page)','Dikecualikan / ragu (halaman)')}: <strong>{counts.excluded_or_uncertain||0}</strong></p>
        <p>{T('Relevant (page)','Relevan (halaman)')}: <strong>{counts.relevant||0}</strong></p>
      </div>}
      <p className="text-xs text-slate-500">{T('Review queue is cursor-paginated across ordinary campaign evidence. Counts are for the current retrieved page, not population totals or a violation rate. Watchlist-only links are excluded.','Antrean tinjauan dibagi halaman untuk bukti kampanye biasa. Jumlah hanya untuk halaman yang dimuat, bukan seluruh data atau tingkat pelanggaran. Tautan khusus watchlist dikecualikan.')}</p>
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
          <span className="block text-xs text-slate-500">{T('AI relevance','Relevansi AI')}: {item.relevance}</span>
          {item.information_review_status&&<span className="block text-xs text-slate-500">{T('Information QA','QA informasi')}: {item.information_review_status}</span>}
        </button>)}
        {!sampleLoading&&sample&&sample.items?.length===0&&!hasMore&&<p className="text-sm text-slate-500">{T('No ordinary campaign evidence matches this filter.','Tidak ada bukti kampanye biasa yang cocok.')}</p>}
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
            <p><strong>{T('Saved relevance','Relevansi tersimpan')}:</strong> {detail.relevance}</p>
            <p><strong>{T('AI sentiment','Sentimen AI')}:</strong> {detail.ai_sentiment}</p>
            <p><strong>{T('Effective sentiment','Sentimen efektif')}:</strong> {detail.effective_sentiment} ({detail.sentiment_basis})</p>
            <p><strong>{T('Assessment version','Versi penilaian')}:</strong> {detail.assessment_version??T('Not assessed','Belum dinilai')}</p>
            <p><strong>{T('Last officer review','Tinjauan petugas terakhir')}:</strong> {detail.officer_review_decision||T('Not recorded','Belum tercatat')}</p>
            <p data-testid="gate1-information-status"><strong>{T('Information QA status','Status QA informasi')}:</strong> {detail.information_review_status} {detail.information_review_stale?'· '+T('Requires revalidation','Perlu validasi ulang'):''}</p>
            {detail.information_review_reviewer_id&&<p className="text-xs text-slate-600">{T('Reviewer','Pemeriksa')}: {detail.information_review_reviewer_id} · {detail.information_review_at}</p>}
            {detail.relevance_explanation&&<p className="text-xs text-slate-600">{detail.relevance_explanation}</p>}
          </div>
          {detail.can_review_information?<div className="border-t pt-3 space-y-3" data-testid="gate1-correction-workbench">
            <h4 className="font-semibold text-sm">{T('Officer information review & corrections','Tinjauan informasi & koreksi petugas')}</h4>
            <p className="text-xs text-slate-500">{T('Field correction is not whole-record verification. No legal finding, AI training or Command Centre publication occurs automatically.','Koreksi satu bidang bukan verifikasi seluruh catatan. Tidak ada temuan hukum, pelatihan AI, atau publikasi otomatis.')}</p>
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
