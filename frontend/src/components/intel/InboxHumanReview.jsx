import {useEffect,useState} from 'react';
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
  const [detail,setDetail]=useState(null);
  const [loading,setLoading]=useState(true);
  const [sampleLoading,setSampleLoading]=useState(false);
  const [detailLoading,setDetailLoading]=useState(false);
  const [error,setError]=useState('');
  const [actionBusy,setActionBusy]=useState(false);
  const [rationale,setRationale]=useState('');
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
    if(!campaignId){setSample(null);return}
    let active=true;
    setSampleLoading(true);setError('');
    base44.inboxHumanReview.sample(campaignId).then(r=>{if(active)setSample(r)})
      .catch(e=>{if(active){setSample(null);setError(e.message||'Review sample unavailable')}})
      .finally(()=>{if(active)setSampleLoading(false)});
    return ()=>{active=false};
  },[campaignId,version]);
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
    setSuccess('');setRationale('');
    const q=new URLSearchParams(window.location.search);
    q.set('gate1','1');q.set('campaign_id',String(campaignId));q.set('result_id',String(id));
    window.history.replaceState(null,'','/inbox?'+q.toString());
  }
  function chooseCampaign(id){
    setCampaignId(String(id));setSelectedId('');setDetail(null);setSuccess('');setRationale('');
    const q=new URLSearchParams(window.location.search);
    q.set('gate1','1');q.set('campaign_id',String(id));q.delete('result_id');
    window.history.replaceState(null,'','/inbox?'+q.toString());
  }
  async function correct(decision){
    if(!detail?.can_correct_relevance||actionBusy||rationale.trim().length<10)return;
    if(!window.confirm(T('Save this human relevance correction with its audit trail?','Simpan koreksi relevansi petugas dengan jejak audit?')))return;
    setActionBusy(true);setError('');setSuccess('');
    try{
      await base44.functions.invoke('socialListening',{
        action:'campaignAssessmentCorrection',id:String(campaignId),
        data:{result_id:String(detail.result_id),decision,rationale:rationale.trim()}
      });
      setSuccess(T('Officer correction saved. Original source and earlier assessment preserved.','Koreksi petugas tersimpan. Sumber asli dan penilaian sebelumnya dipertahankan.'));
      setRationale('');setVersion(v=>v+1);
    }catch(e){setError(e.message||'Unable to save correction')}
    finally{setActionBusy(false)}
  }
  const counts=sample?.counts||{};
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
      {sample&&<div className="grid grid-cols-2 sm:grid-cols-4 gap-2 text-sm">
        <p>{T('Sources checked','Sumber diperiksa')}: <strong>{sample.scanned_count}</strong></p>
        <p>{T('Unassessed','Belum dinilai')}: <strong>{counts.unassessed||0}</strong></p>
        <p>{T('Excluded / uncertain','Dikecualikan / ragu')}: <strong>{counts.excluded_or_uncertain||0}</strong></p>
        <p>{T('Relevant','Relevan')}: <strong>{counts.relevant||0}</strong></p>
      </div>}
      <p className="text-xs text-slate-500">{T('Counts reflect a bounded recent authorized evidence sample, not all collected posts or a violation rate. Watchlist-only evidence excluded.','Hitungan mencerminkan sampel terbatas bukti terbaru sesuai kewenangan, bukan seluruh unggahan atau tingkat pelanggaran. Bukti khusus watchlist dikecualikan.')}</p>
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
        </button>)}
        {!sampleLoading&&sample&&sample.items?.length===0&&<p className="text-sm text-slate-500">{T('No ordinary campaign evidence in this scoped sample.','Tidak ada bukti kampanye biasa dalam sampel ini.')}</p>}
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
            {detail.relevance_explanation&&<p className="text-xs text-slate-600">{detail.relevance_explanation}</p>}
          </div>
          {detail.can_correct_relevance?<div className="border-t pt-3 space-y-2">
            <h4 className="font-semibold text-sm">{T('Officer relevance correction','Koreksi relevansi oleh petugas')}</h4>
            <textarea className="intel-input w-full" rows={3} value={rationale} onChange={e=>setRationale(e.target.value)} placeholder={T('Reason for correction (at least 10 characters)','Alasan koreksi (minimal 10 karakter)')}/>
            <div className="flex flex-wrap gap-2">{['RELEVANT','IRRELEVANT','UNCERTAIN'].map(decision=><button type="button" className="intel-ghost text-xs" disabled={actionBusy||rationale.trim().length<10} key={decision} onClick={()=>correct(decision)}>{T('Mark','Tandai')} {decision}</button>)}</div>
            <p className="text-xs text-slate-500">{T('Uses the existing audited officer correction action. No automatic Command Centre publication or model training.','Menggunakan tindakan koreksi petugas yang sudah memiliki audit. Tidak otomatis diterbitkan atau digunakan untuk pelatihan model.')}</p>
          </div>:<p className="rounded-lg bg-amber-50 p-3 text-xs text-amber-900">{detail.reason_if_not_actionable||T('Read-only. Officer corrections are not enabled.','Hanya-baca. Koreksi belum diaktifkan.')}</p>}
          {success&&<p role="status" className="rounded-lg bg-green-50 p-3 text-sm text-green-800">{success}</p>}
        </>}
      </section>
    </div>
  </div>;
}
