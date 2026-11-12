import {useEffect, useState} from 'react';
import {Download, Printer, RefreshCw, FileBarChart2} from 'lucide-react';
import {useLanguage} from '@/lib/LanguageContext';

const API='/api/management-reporting';
const auth=()=>({Authorization:'Bearer '+(window.localStorage.getItem('bawaslu_access_token')||'')});
const entries=o=>Object.entries(o||{}).sort((a,b)=>b[1]-a[1]);
function sourceUrl(raw){try{const u=new URL(raw);return ['http:','https:'].includes(u.protocol)?u.href:null}catch{return null}}

export default function ManagementBriefings(){
 const {language}=useLanguage(),id=language==='id';
 const t=(english,indonesian)=>id?indonesian:english;
 const [period,setPeriod]=useState('weekly'),[draftTopic,setDraftTopic]=useState(''),[topic,setTopic]=useState('');
 const [report,setReport]=useState(null),[busy,setBusy]=useState(true),[exporting,setExporting]=useState(false);
 const [error,setError]=useState(''),[refresh,setRefresh]=useState(0);
 const params=new URLSearchParams({period,topic}).toString();
 useEffect(()=>{
   const controller=new AbortController();setBusy(true);setError('');
   fetch(API+'/briefing?'+params,{cache:'no-store',headers:auth(),signal:controller.signal})
    .then(async r=>{const data=await r.json().catch(()=>({}));if(!r.ok)throw Error(data.detail||'Report unavailable');return data})
    .then(setReport).catch(e=>{if(e.name!=='AbortError'){setReport(null);setError(e.message)}})
    .finally(()=>{if(!controller.signal.aborted)setBusy(false)});
   return ()=>controller.abort();
 },[params,refresh]);
 async function exportCsv(){
   setExporting(true);setError('');
   try{
     const response=await fetch(API+'/briefing.csv?'+params,{headers:auth(),cache:'no-store'});
     if(!response.ok)throw Error('CSV export unavailable ('+response.status+')');
     const url=URL.createObjectURL(await response.blob());
     const link=document.createElement('a');link.href=url;link.download='bawaslu-casework-'+period+'.csv';
     document.body.appendChild(link);link.click();link.remove();URL.revokeObjectURL(url);
   }catch(e){setError(e.message)}finally{setExporting(false)}
 }
 const m=report?.metrics||{},recent=report?.recent_cases||[];
 return <section id="management-briefing" data-i18n-exempt="true" className="mx-auto max-w-6xl space-y-5 bg-[#faf9f8] p-5 text-[#243b52] md:p-8">
  <style>{'@media print {body * {visibility:hidden!important} #management-briefing, #management-briefing * {visibility:visible!important} #management-briefing {position:absolute!important;left:0;top:0;width:100%;background:white!important} .briefing-no-print {display:none!important}}'}</style>
  <header className="flex flex-wrap justify-between gap-4">
   <div><span className="text-xs font-bold uppercase tracking-widest text-[#947c5d]">BAWASLU · Command Centre</span>
    <h2 className="mt-2 flex items-center gap-2 text-2xl font-semibold"><FileBarChart2 size={23}/>{t('Reports & Briefings','Laporan & Ringkasan')}</h2>
    <p className="mt-1 text-sm text-[#64748b]">{t('Officer casework snapshot — not a formal violation determination.','Ringkasan penugasan petugas — bukan penetapan pelanggaran hukum.')}</p></div>
   <div className="briefing-no-print flex flex-wrap gap-2 self-start">
    <button className="intel-ghost text-sm" type="button" onClick={()=>setRefresh(n=>n+1)} disabled={busy}><RefreshCw size={15} className="mr-1 inline"/>{t('Refresh','Muat ulang')}</button>
    <button className="intel-ghost text-sm" type="button" disabled={!report||busy||exporting} onClick={exportCsv}><Download size={15} className="mr-1 inline"/>{t('Excel CSV','CSV Excel')}</button>
    <button className="intel-button text-sm" type="button" disabled={!report||busy} onClick={()=>window.print()}><Printer size={15} className="mr-1 inline"/>{t('Print / Save PDF','Cetak / Simpan PDF')}</button>
   </div>
  </header>
  <div className="briefing-no-print flex flex-wrap items-end gap-3 rounded-xl border bg-white p-4">
   <label className="text-xs font-semibold">{t('Period','Periode')}
    <select className="intel-input mt-1 block" value={period} onChange={e=>setPeriod(e.target.value)}>
     <option value="daily">{t('Daily','Harian')}</option><option value="weekly">{t('Weekly','Mingguan')}</option><option value="monthly">{t('Monthly','Bulanan')}</option>
    </select></label>
   <label className="min-w-[180px] flex-1 text-xs font-semibold">{t('Topic (optional)','Topik (opsional)')}
    <input className="intel-input mt-1 w-full" maxLength={120} value={draftTopic} onChange={e=>setDraftTopic(e.target.value)} onKeyDown={e=>{if(e.key==='Enter')setTopic(draftTopic.trim())}} placeholder={t('Filter case title or excerpt','Filter judul atau kutipan')}/></label>
   <button type="button" className="intel-ghost text-sm" onClick={()=>setTopic(draftTopic.trim())}>{t('Apply','Terapkan')}</button>
  </div>
  {error&&<p role="alert" className="rounded-lg bg-red-50 p-3 text-sm text-red-700">{error}</p>}
  {busy&&<p role="status" className="text-sm text-[#64748b]">{t('Loading authorized data…','Memuat data yang diizinkan…')}</p>}
  {!busy&&report&&<>
   <p className="rounded-lg border bg-white p-3 text-xs text-[#64748b]">{report.window_start_utc} — {report.window_end_utc} · {report.scope?.geographic_scope==='Nationwide'?t('National','Nasional'):report.scope?.province} {report.topic_filter?' · '+report.topic_filter:''}</p>
   <div className="grid grid-cols-2 gap-3 lg:grid-cols-4">{[
     [t('Assignments created','Penugasan dibuat'),m.assignments],
     [t('Unique linked sources','Sumber terkait unik'),m.unique_linked_sources],
     [t('Active assignments','Penugasan aktif'),m.active_assignments],
     [t('Approved case reports','Laporan disetujui'),m.approved_reports]
   ].map(([label,value])=><div key={label} className="rounded-xl border bg-white p-4"><strong className="block text-3xl tabular-nums">{value||0}</strong><p className="mt-2 text-xs text-[#64748b]">{label}</p></div>)}</div>
   <section className="rounded-xl border bg-white p-5"><h3 className="font-semibold">{t('Executive snapshot','Ringkasan eksekutif')}</h3>
    <p className="mt-2 text-sm leading-6">{t(
      'In this reporting period, '+m.assignments+' assignments were created, '+m.active_assignments+' remain active and '+m.closed_assignments+' were closed. '+m.submitted_reports+' related reports are submitted for review and '+m.approved_reports+' have approved workflow status.',
      'Pada periode ini, '+m.assignments+' penugasan dibuat, '+m.active_assignments+' masih aktif dan '+m.closed_assignments+' ditutup. '+m.submitted_reports+' laporan terkait diajukan untuk ditinjau dan '+m.approved_reports+' berstatus disetujui.'
    )}</p><p className="mt-3 text-xs text-[#866b43]">{report.disclaimer}</p></section>
   <div className="grid gap-4 md:grid-cols-2">{[
     [t('Casework status','Status penugasan'),report.case_status_counts],
     [t('Department workload','Beban kerja unit'),report.department_counts],
     [t('Verified incident provinces','Provinsi kejadian terverifikasi'),report.verified_incident_province_counts],
     [t('Related report status','Status laporan terkait'),report.report_status_counts]
   ].map(([heading,data])=><div key={heading} className="rounded-xl border bg-white p-4"><h3 className="mb-3 font-semibold">{heading}</h3>
    {entries(data).length?entries(data).map(([name,value])=><div key={name} className="flex justify-between border-b py-2 text-sm"><span>{name}</span><strong>{value}</strong></div>):<p className="text-sm text-[#64748b]">{t('No records','Tidak ada data')}</p>}</div>)}</div>
   <section className="rounded-xl border bg-white p-4"><h3 className="font-semibold">{t('Source-linked assignments','Penugasan beserta sumber')}</h3>
    <div className="mt-3 overflow-x-auto"><table className="w-full text-left text-xs"><thead><tr><th className="p-2">{t('Case','Kasus')}</th><th className="p-2">{t('Date','Tanggal')}</th><th className="p-2">{t('Status','Status')}</th><th className="p-2">{t('Unit','Unit')}</th><th className="p-2">{t('Evidence','Bukti')}</th></tr></thead>
    <tbody>{recent.map(item=><tr className="border-t" key={item.id}><td className="p-2">{item.title}</td><td className="p-2">{item.created_at?.slice(0,10)}</td><td className="p-2">{item.status}</td><td className="p-2">{item.department}</td><td className="p-2">{sourceUrl(item.source_url)?<a className="text-[#116d85] underline" href={sourceUrl(item.source_url)} target="_blank" rel="noopener noreferrer">{t('Original','Asli')}</a>:item.source_type+' #'+item.source_id}</td></tr>)}</tbody></table></div>
    {!recent.length&&<p className="mt-2 text-sm text-[#64748b]">{t('No authorized casework in this period.','Tidak ada penugasan pada periode ini.')}</p>}
   </section>
   <p className="text-xs text-[#64748b]">{t('Factual report only. An official BAWASLU management template and reviewed narrative require separate approval.','Laporan faktual. Template resmi BAWASLU dan narasi harus ditinjau dan disetujui secara terpisah.')}</p>
  </>}
 </section>;
}
