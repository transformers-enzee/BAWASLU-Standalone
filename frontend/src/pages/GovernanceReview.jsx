import {useCallback,useEffect,useState} from 'react';
import {Link,useOutletContext} from 'react-router-dom';
import {base44} from '@/api/base44Client';
import {useLanguage} from '@/lib/LanguageContext';

const infoActions={VERIFY_UNASSESSED:'Unassessed: verify election relevance',REVIEW_UNCERTAIN:'Uncertain: officer relevance check',SPOT_CHECK_EXCLUDED:'Excluded: sample possible false negative',REVIEW_UNKNOWN_LABEL:'Unknown label: investigate',CHECK_RELEVANT_EVIDENCE:'Relevant: spot-check assessment'};
const btn='rounded-lg border border-slate-300 bg-white px-3 py-2 text-sm font-semibold text-slate-700 hover:bg-slate-50 disabled:opacity-50';
const label={REVIEW_FOR_APPROVAL:'Needs independent officer review',REASSESS_SOURCE:'Source changed: reassessment needed',RESOLVE_REVIEW_CONFLICT:'Conflicting officer corrections',NO_ACTION:'No action'};
export default function GovernanceReview(){
  const {access}=useOutletContext();
  const {language}=useLanguage();
  const T=(en,id)=>language==='id'?id:en;
  const [readiness,setReadiness]=useState(null);
  const [campaigns,setCampaigns]=useState([]);
  const [selected,setSelected]=useState('');
  const [report,setReport]=useState(null);
  const [loading,setLoading]=useState(false);
  const [error,setError]=useState('');
  const [truncated,setTruncated]=useState(false);
  const mayView=access?.status==='Active'&&access?.permissions?.administration===true&&access?.permissions?.view_intelligence===true;
  const refresh=useCallback(async()=>{
    if(!mayView)return;
    setError('');setLoading(true);setReport(null);
    // Fail closed to an explicit load error: do not show stale campaign options.
    setCampaigns([]);setTruncated(false);setSelected('');
    try{
      const ready=await base44.governance.readiness();
      setReadiness(ready);
      if(ready.governance_qa_reads_enabled){
        const response=await base44.governance.qaCampaigns();
        setCampaigns(response.campaigns||[]);
        setTruncated(Boolean(response.truncated));
        setSelected(value=>(response.campaigns||[]).some(x=>String(x.id)===value)?value:String(response.campaigns?.[0]?.id||''));
      } else {setCampaigns([]);setTruncated(false);setSelected('');}
    }catch(e){setError(e.message||'Unable to load governance review status');}
    finally{setLoading(false);}
  },[mayView]);
  useEffect(()=>{refresh();},[refresh]);
  useEffect(()=>{
    if(!mayView||!selected||!readiness?.governance_qa_reads_enabled){setReport(null);return;}
    let cancelled=false;
    setError('');setReport(null);
    base44.governance.qaSummary(selected).then(r=>{if(!cancelled)setReport(r);})
      .catch(e=>{if(!cancelled)setError(e.message||'Unable to load campaign review');});
    return ()=>{cancelled=true;};
  },[mayView,selected,readiness?.governance_qa_reads_enabled]);
  if(!mayView)return <p role="alert" className="p-5">Administrator permission is required.</p>;
  const schemaReady=readiness?.ready_for_controlled_staging_qa===true;
  return <div className="max-w-5xl space-y-5" data-testid="governance-review-page">
    <header className="space-y-1"><Link to="/administration" className="text-sm text-[#801b24] hover:underline">{T('Administration','Administrasi')}</Link>
      <h1 className="text-2xl font-bold text-slate-900">{T('Human Review Status','Status Tinjauan Petugas')}</h1>
      <p className="text-sm text-slate-600">{T('Read-only checks for evidence review and Command Centre insight approval. This page does not update posts or trigger AI.','Pemeriksaan hanya-baca untuk bukti dan persetujuan insight Command Centre. Halaman ini tidak mengubah unggahan atau menjalankan AI.')}</p>
    </header>
    <div className="flex gap-2 flex-wrap"><button type="button" className={btn} disabled={loading} onClick={refresh}>{loading?T('Loading…','Memuat…'):T('Refresh status','Muat ulang status')}</button></div>
    {error&&<div role="alert" className="border rounded-lg p-3 text-sm text-red-800 bg-red-50">{error}</div>}
    {!readiness&&!error&&<p className="text-sm text-slate-500">{T('Loading review readiness…','Memuat kesiapan tinjauan…')}</p>}
    {readiness&&<section className="rounded-xl border border-slate-200 bg-white p-5 space-y-3">
      <h2 className="font-semibold">{T('Current controls','Kontrol saat ini')}</h2>
      <div className="grid grid-cols-1 sm:grid-cols-3 gap-3 text-sm">
        <div><p className="text-slate-500">{T('Database security','Keamanan database')}</p><strong>{schemaReady?T('Verified','Terverifikasi'):T('Requires review','Perlu diperiksa')}</strong></div>
        <div><p className="text-slate-500">{T('Read-only review','Tinjauan hanya-baca')}</p><strong>{readiness.governance_qa_reads_enabled?T('Enabled','Aktif'):T('Not enabled','Belum aktif')}</strong></div>
        <div><p className="text-slate-500">{T('Pilot corrections and approvals','Koreksi & persetujuan pilot')}</p><strong>{readiness.pilot_writes_ready?T('Pilot configuration active','Konfigurasi pilot aktif'):T('Disabled / protected','Nonaktif / terlindungi')}</strong></div>
      </div>
      {!readiness.governance_qa_reads_enabled&&<div role="status" className="rounded-lg border border-amber-200 bg-amber-50 p-3 text-sm text-amber-950">{T('Read-only checks are not activated on this deployment. No officer action is required.','Pemeriksaan hanya-baca belum diaktifkan pada versi ini. Tidak diperlukan tindakan petugas.')}</div>}
      {!schemaReady&&<div role="alert" className="text-sm text-red-700">{T('Database security prerequisites must be verified before officer testing.','Persyaratan keamanan database harus diverifikasi sebelum pengujian petugas.')}</div>}
    </section>}
    {readiness?.governance_qa_reads_enabled&&<section className="rounded-xl border border-slate-200 bg-white p-5 space-y-4">
      <div><h2 className="font-semibold">{T('Review cases by campaign','Kasus tinjauan per kampanye')}</h2><p className="text-xs text-slate-500">{T('Only campaigns within your authorized geographic scope are listed.','Hanya kampanye dalam wilayah kewenangan Anda yang ditampilkan.')}</p></div>
      {!error&&campaigns.length>0?<label className="block text-sm font-medium">{T('Select campaign','Pilih kampanye')}<select className="mt-1 w-full border rounded-lg p-2 bg-white" value={selected} onChange={e=>setSelected(e.target.value)}>{campaigns.map(c=><option key={c.id} value={c.id}>{c.name} · {c.province||T('Nationwide','Nasional')}</option>)}</select></label>:!error?<p className="text-sm text-slate-600">{T('No authorized campaigns were found.','Tidak ada kampanye yang dapat diakses.')}</p>:<p role="status" className="text-sm text-amber-800">{T('Campaigns could not be loaded. Check the error above and use Refresh status.','Kampanye tidak dapat dimuat. Periksa kesalahan di atas dan pilih Muat ulang status.')}</p>}
      {truncated&&<p className="text-sm text-amber-800">{T('Showing a bounded sample of campaigns.','Menampilkan sebagian kampanye.')}</p>}
      {report&&<><section className="rounded-lg border border-slate-200 bg-slate-50 p-4 space-y-3" data-testid="governance-information-qa">
        <div><h3 className="font-semibold text-slate-900">{T('Gate 1 · Information quality','Gate 1 · Kualitas informasi')}</h3>
          <p className="text-xs text-slate-600">{T('Recent authorized campaign evidence sample, including excluded and unassessed posts. These are sample counts—not campaign totals.','Sampel bukti kampanye terbaru yang diizinkan, termasuk unggahan yang dikecualikan dan belum dinilai. Angka ini adalah jumlah sampel, bukan total kampanye.')}</p></div>
        <div className="grid grid-cols-2 sm:grid-cols-4 gap-3 text-sm">
          <div><span className="text-slate-500">{T('Sources checked','Sumber diperiksa')}</span><strong className="block text-xl">{report.information_qa?.scanned_count||0}</strong></div>
          <div><span className="text-slate-500">{T('Unassessed','Belum dinilai')}</span><strong className="block text-xl">{report.information_qa?.counts?.unassessed||0}</strong></div>
          <div><span className="text-slate-500">{T('Excluded / uncertain','Dikecualikan / ragu')}</span><strong className="block text-xl">{report.information_qa?.counts?.excluded_or_uncertain||0}</strong></div>
          <div><span className="text-slate-500">{T('Relevant','Relevan')}</span><strong className="block text-xl">{report.information_qa?.counts?.relevant||0}</strong></div>
        </div>
        {(report.information_qa?.items||[]).length>0?<div className="space-y-2">
          {(report.information_qa?.items||[]).map(item=><div key={item.result_id} className="rounded-lg border bg-white px-3 py-2 text-xs space-y-1">
            <div className="flex flex-wrap items-center justify-between gap-2"><strong>{item.platform||T('Social post','Unggahan sosial')} · #{item.result_id}</strong>
              <Link className="font-semibold text-[#801b24] underline" to={'/inbox?campaign_id='+encodeURIComponent(item.campaign_id)+'&result_id='+encodeURIComponent(item.result_id)}>{T('Review in Inbox','Periksa di Inbox')}</Link></div>
            <div>{infoActions[item.action]||item.action}</div>
            <p className="text-slate-600">{T('AI relevance','Relevansi AI')}: {item.relevance} · {T('Sentiment basis','Dasar sentimen')}: {item.sentiment_basis} · {T('Officer review','Tinjauan petugas')}: {item.officer_review_decision||T('Not recorded','Belum tercatat')}</p>
          </div>)}
        </div>:<p className="text-xs text-slate-600">{T('No scoped campaign evidence found in the sample.','Tidak ditemukan bukti kampanye dalam sampel sesuai kewenangan.')}</p>}
        <p className="text-xs text-slate-500">{T('Read-only · recent links only · watchlist-only records excluded · no paid AI calls.','Hanya-baca · hanya tautan terbaru · akun watchlist saja dikecualikan · tanpa panggilan AI berbayar.')}</p>
      </section><div className="grid sm:grid-cols-3 gap-3 text-sm">
        <div><p className="text-slate-500">{T('Awaiting review','Menunggu tinjauan')}</p><p className="text-2xl font-semibold">{report.awaiting_review}</p></div>
        <div><p className="text-slate-500">{T('Evidence changed','Bukti berubah')}</p><p className="text-2xl font-semibold">{report.needs_reassessment}</p></div>
        <div><p className="text-slate-500">{T('Correction conflicts','Konflik koreksi')}</p><p className="text-2xl font-semibold">{report.requires_conflict_resolution}</p></div>
      </div>
      {(report.cases||[]).length>0?<div className="space-y-2">{report.cases.map(c=><div key={c.id} className="rounded-lg border p-3 space-y-1">
        <div className="font-medium">{c.title}</div><p className="text-xs text-slate-600">{T('Next step','Tindakan lanjut')}: {label[c.next_action]||c.next_action}</p>
        <p className="text-xs text-slate-500">{T('Review state','Status tinjauan')}: {c.state} · {T('Evidence current','Bukti mutakhir')}: {c.source_current?T('Yes','Ya'):T('No','Tidak')}</p>
        {c.review_blockers?.length>0&&<p className="text-xs text-amber-800">{T('Checks','Pemeriksaan')}: {c.review_blockers.join(', ')}</p>}
      </div>)}</div>:<p className="text-sm text-slate-600">{T('No governance review cases in this campaign yet. Existing Inbox posts remain unchanged.','Belum ada kasus tinjauan tata kelola dalam kampanye ini. Unggahan Inbox yang ada tidak berubah.')}</p>}
      <p className="text-xs text-slate-500">{T('Read-only preview · up to 30 cases · no paid AI calls.','Pratinjau hanya-baca · hingga 30 kasus · tanpa panggilan AI berbayar.')}</p>
      </>}
    </section>}
  </div>;
}
