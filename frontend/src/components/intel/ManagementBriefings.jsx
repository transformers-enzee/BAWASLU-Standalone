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
 const [includeMonitoring,setIncludeMonitoring]=useState(false);
 const [report,setReport]=useState(null),[busy,setBusy]=useState(true),[exporting,setExporting]=useState(false);
 const [error,setError]=useState(''),[refresh,setRefresh]=useState(0);
 const params=new URLSearchParams({period,topic,language:id?'id':'en',include_monitoring:String(includeMonitoring)}).toString();
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

 async function exportTemplate(kind){
   if(!['pdf','docx','xlsx'].includes(kind))return;
   setExporting(true);setError('');
   try{
     const response=await fetch(API+'/briefing.'+kind+'?'+params,{headers:auth(),cache:'no-store'});
     if(!response.ok){
       const payload=await response.json().catch(()=>({}));
       throw Error(payload.detail||('Report export unavailable ('+response.status+')'));
     }
     const url=URL.createObjectURL(await response.blob());
     const anchor=document.createElement('a');
     anchor.href=url;
     anchor.download='bawaslu-interim-briefing-'+period+'.'+kind;
     document.body.appendChild(anchor);anchor.click();anchor.remove();
     setTimeout(()=>URL.revokeObjectURL(url),1000);
   }catch(e){setError(String(e.message||e))}
   finally{setExporting(false)}
 }
 const m=report?.metrics||{},recent=report?.recent_cases||[],template=report?.template||{},coverage=report?.report_coverage||{},monitoring=report?.monitoring||{};
 return <section id="management-briefing" data-i18n-exempt="true" className="mx-auto max-w-6xl space-y-5 bg-[#faf9f8] p-5 text-[#243b52] md:p-8">
  <style>{'@media print {body * {visibility:hidden!important} #management-briefing, #management-briefing * {visibility:visible!important} #management-briefing {position:absolute!important;left:0;top:0;width:100%;background:white!important} .briefing-no-print {display:none!important}}'}</style>
  <header className="flex flex-wrap justify-between gap-4">
   <div><span className="text-xs font-bold uppercase tracking-widest text-[#947c5d]">BAWASLU · Command Centre</span>
    <h2 className="mt-2 flex items-center gap-2 text-2xl font-semibold"><FileBarChart2 size={23}/>{t('Reports & Briefings','Laporan & Ringkasan')}</h2>
    <p className="mt-1 text-sm text-[#64748b]">{t('Officer casework snapshot — not a formal violation determination.','Ringkasan penugasan petugas — bukan penetapan pelanggaran hukum.')}</p></div>
   <div className="briefing-no-print flex flex-wrap gap-2 self-start">
    <button className="intel-ghost text-sm" type="button" onClick={()=>setRefresh(n=>n+1)} disabled={busy}><RefreshCw size={15} className="mr-1 inline"/>{t('Refresh','Muat ulang')}</button>
    <button className="intel-ghost text-sm" type="button" disabled={!report||busy||exporting} onClick={()=>exportTemplate('docx')}><Download size={15} className="mr-1 inline"/>Word (.docx)</button>
    <button className="intel-ghost text-sm" type="button" disabled={!report||busy||exporting} onClick={()=>exportTemplate('xlsx')}><Download size={15} className="mr-1 inline"/>Excel (.xlsx)</button>
    <button className="intel-ghost text-sm" type="button" disabled={!report||busy||exporting} onClick={exportCsv}><Download size={15} className="mr-1 inline"/>CSV</button>
    <button className="intel-button text-sm" type="button" disabled={!report||busy||exporting} onClick={()=>exportTemplate('pdf')}><Download size={15} className="mr-1 inline"/>PDF</button>
    <button className="intel-ghost text-sm" type="button" disabled={!report||busy} onClick={()=>window.print()}><Printer size={15} className="mr-1 inline"/>{t('Print','Cetak')}</button>
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
   <label className="flex items-center gap-2 self-center text-xs text-[#52657a]" data-testid="briefing-monitoring-option">
    <input type="checkbox" checked={includeMonitoring} onChange={e=>setIncludeMonitoring(e.target.checked)}/>
    {t('Include saved Inbox monitoring (may take longer)','Sertakan pemantauan Inbox tersimpan (dapat lebih lama)')}
   </label>
  </div>
  {error&&<p role="alert" className="rounded-lg bg-red-50 p-3 text-sm text-red-700">{error}</p>}
  {busy&&<p role="status" className="text-sm text-[#64748b]">{t('Loading authorized data…','Memuat data yang diizinkan…')}</p>}
  {!busy&&report&&<>
   <div data-testid="interim-report-template" className="overflow-hidden rounded-xl border border-[#dbc4c7] bg-white shadow-sm">
    <div className="border-b-4 border-[#801b24] px-5 pb-5 pt-6 md:px-7">
     <p className="text-[11px] font-bold uppercase tracking-[0.2em] text-[#801b24]">BAWASLU · {template.template_version} · {t('Internal report','Laporan internal')}</p>
     <h3 className="mt-3 text-2xl font-bold leading-snug text-[#25384c]">{template.title||t('Management Intelligence Brief','Laporan Intelijen Manajemen')}</h3>
     <p className="mt-2 text-xs font-semibold uppercase tracking-wide text-[#8d3340]">{template.subtitle||'DRAFT_NOT_APPROVED'}</p>
     <p className="mt-2 text-sm text-[#63748a]">{t('Reporting period','Periode')}: {template.period_label} · {t('Geographic scope','Cakupan wilayah')}: {template.scope_label}</p>
     {template.topic&&<p className="mt-1 text-sm text-[#63748a]">{t('Topic','Topik')}: {template.topic}</p>}
    </div>
    <div className="p-5 text-xs text-[#795e44] md:px-7">
     {t('Interim operational template, NOT an official BAWASLU form. This report is an unapproved draft until reviewed and signed by authorized officers.',
        'Template operasional sementara, BUKAN formulir resmi BAWASLU. Laporan ini merupakan draf yang belum disetujui sampai ditelaah dan ditandatangani petugas berwenang.')}
    </div>
   </div>
   <p className="rounded-lg border bg-white p-3 text-xs text-[#64748b]">{report.window_start_utc} — {report.window_end_utc} · {report.scope?.geographic_scope==='Nationwide'?t('National','Nasional'):report.scope?.province} {report.topic_filter?' · '+report.topic_filter:''}</p>
   <div className="grid grid-cols-2 gap-3 lg:grid-cols-4">{[
     [t('Assignments created','Penugasan dibuat'),m.assignments],
     [t('Unique linked sources','Sumber terkait unik'),m.unique_linked_sources],
     [t('Active assignments','Penugasan aktif'),m.active_assignments],
     [t('Approved case reports','Laporan disetujui'),m.approved_reports]
   ].map(([label,value])=><div key={label} className="rounded-xl border bg-white p-4"><strong className="block text-3xl tabular-nums">{value||0}</strong><p className="mt-2 text-xs text-[#64748b]">{label}</p></div>)}</div>
   {monitoring.enabled===true&&<section data-testid="briefing-intelligence-monitoring" className="rounded-xl border border-[#dce5ec] bg-white p-5">
    <h3 className="font-semibold text-[#24384c]">{t('Saved Inbox monitoring — separate evidence population','Pemantauan Inbox tersimpan — populasi bukti terpisah')}</h3>
    <p className="mt-2 text-xs leading-5 text-[#866b43]">{t(
      'Sampled authorized relevant posts by original publication time (not capture time). This is not an all-platform census, a unique-person count, or a confirmed legal violation.',
      'Sampel unggahan relevan sesuai hak akses berdasarkan waktu publikasi asli (bukan waktu pengambilan). Ini bukan sensus seluruh platform, jumlah orang unik, atau konfirmasi pelanggaran hukum.')}</p>
    <div className="mt-3 grid grid-cols-2 gap-3 md:grid-cols-4">{[
      [t('Published in selected window','Dipublikasikan dalam periode'),monitoring.published_in_period],
      [t('Flagged source posts','Unggahan bertanda dugaan'),monitoring.flagged_potential_violation_posts],
      [t('Public concern posts','Unggahan keluhan publik'),monitoring.public_concern_posts],
      [t('Time not verifiable','Waktu tidak terverifikasi'),monitoring.publication_date_unknown]
    ].map(([label,value])=><div key={label} className="rounded-lg bg-[#f7f9fb] p-3"><strong className="block text-xl tabular-nums">{value??0}</strong><p className="mt-1 text-xs text-[#64748b]">{label}</p></div>)}</div>
    <div className="mt-3 grid gap-3 md:grid-cols-2">{[
      [t('Platform breakdown','Rincian platform'),monitoring.platform_counts],
      [t('Sentiment distribution','Distribusi sentimen'),monitoring.sentiment_counts]
    ].map(([label,data])=><div key={label}><h4 className="text-sm font-semibold">{label}</h4>
      {entries(data).length?entries(data).map(([name,count])=><p key={name} className="flex justify-between border-b py-1 text-xs"><span>{name}</span><strong>{count}</strong></p>):
      <p className="text-xs text-[#64748b]">{t('No dated posts in this sampled window','Tidak ada unggahan dengan waktu valid dalam sampel periode ini')}</p>}</div>)}</div>
    <div data-testid="briefing-sampled-evidence-quality" className="mt-3 rounded-lg border border-[#dce5ec] bg-[#fbfcfd] p-3 text-xs text-[#56697c]">
      <strong>{t("Original evidence readiness (sampled posts)","Kesiapan bukti asli (sampel unggahan)")}</strong>
      <p className="mt-1">{t("Missing original post text","Teks postingan asli tidak tersedia")}: {monitoring.source_quality?.missing_original_text??0} · {t("Missing safe original URL","URL asli aman tidak tersedia")}: {monitoring.source_quality?.missing_safe_original_url??0}</p>
      <p className="mt-1">{t("Conflicting saved excerpts","Kutipan tersimpan berbeda")}: {monitoring.source_quality?.conflicting_saved_original_text??0} · {t("Unconfigured platform policies","Aturan platform belum tersedia")}: {monitoring.source_quality?.platform_policy_reference_unconfigured??0}</p>
      <p className="mt-1 text-[#876532]">{t("These counts cover unique dated posts in the selected authorized sample, not all captured posts or proven violations.","Angka ini mencakup unggahan unik dengan waktu valid dalam sampel berizin, bukan seluruh unggahan atau pelanggaran yang terbukti.")}</p>
    </div>
    {(monitoring.source_quality?.review_priorities||[]).length>0&&
     <div data-testid="briefing-evidence-follow-up" className="mt-3 rounded-lg border border-[#dce5ec] bg-white p-3 text-xs">
      <strong>{t('Recommended source verification (sampled monitoring)','Verifikasi sumber yang disarankan (sampel pemantauan)')}</strong>
      <ul className="mt-2 space-y-1">
       {(monitoring.source_quality.review_priorities||[]).map(item=>{
        const names={
         VERIFY_ORIGINAL_POST_TEXT:t('Recover original post text','Cari teks postingan asli'),
         VERIFY_ORIGINAL_SOURCE_URL:t('Validate original source URL','Validasi URL sumber asli'),
         RECONCILE_CONFLICTING_SAVED_EXCERPTS:t('Reconcile conflicting excerpts','Cocokkan kutipan yang berbeda'),
         CHECK_CURRENT_PLATFORM_RULES:t('Locate current platform rules','Cari aturan platform terkini'),
         RECOVER_EXPLICIT_PUBLICATION_TIME:t('Confirm original publication time','Konfirmasi waktu publikasi asli')
        };
        return <li key={item.code} className="flex flex-wrap gap-2"><strong>{item.priority}</strong><span>{names[item.code]||item.code}:</span><span>{item.affected_sources}</span></li>;
       })}
      </ul>
      <p className="mt-2 text-[#876532]">{t('These are source-quality tasks, not violation findings or automatic case assignments. Undated sources are outside the dated-post denominator.','Ini adalah pemeriksaan kualitas sumber, bukan temuan pelanggaran atau penugasan otomatis. Sumber tanpa waktu tidak termasuk dalam jumlah unggahan bertanggal.')}</p>
     </div>}
    <p data-testid="briefing-signal-overlap" className="mt-3 text-xs text-[#866b43]">
      {t('Preliminary issue categories can overlap for the same post and must not be summed.',
         'Kategori indikasi awal dapat tumpang tindih untuk unggahan yang sama dan tidak boleh dijumlahkan.')}
      {' '}{t('Overlapping posts:','Unggahan tumpang tindih:')} {monitoring.signal_overlapping_sources_in_period??0}.
      {' '}{t('Conflicting publication times:','Konflik waktu publikasi:')} {monitoring.source_publication_time_conflicts??0}.
      {' '}{t('Conflicting sentiments:','Konflik sentimen:')} {monitoring.source_sentiment_conflicts??0}.
      {' '}{t('Conflicting platforms:','Konflik platform:')} {monitoring.source_platform_conflicts??0}.
    </p>
    <p className="mt-3 text-xs text-[#866b43]">{t('Window: up to 300 links per authorized campaign. Publication time unknown or outside the period:',
      'Jendela: maksimal 300 tautan per kampanye yang diizinkan. Waktu publikasi tidak diketahui atau di luar periode:')} {monitoring.publication_date_unknown??0} / {monitoring.published_outside_period??0}.
      {' '}{t('Completeness cannot be inferred from a zero count.','Jumlah nol tidak berarti seluruh unggahan sudah tercakup.')}</p>
   </section>}
   <section data-testid="briefing-data-coverage" className="rounded-xl border border-[#dce5ec] bg-white p-4 text-sm">
    <h3 className="font-semibold text-[#24384c]">{t('Coverage and report status integrity','Cakupan dan integritas status laporan')}</h3>
    <p className="mt-2 text-[#52657a]">{t('Full authorized casework in this period:','Seluruh penugasan sesuai hak akses dalam periode ini:')} <strong>{coverage.assignments_in_period??m.assignments??0}</strong>. {t('Recent list shows','Daftar terbaru menampilkan')} <strong>{coverage.preview_rows??recent.length}</strong> / {coverage.preview_limit??12}; {t('report appendix shows','lampiran laporan menampilkan')} <strong>{coverage.template_rows??template.findings?.length??0}</strong> / {coverage.template_limit??8}.</p>
    <p className="mt-2 text-[#52657a]">{t('Assignments with a report:','Penugasan dengan laporan:')} <strong>{m.assignments_with_reports??0}</strong> · {t('Without a report:','Tanpa laporan:')} <strong>{m.assignments_without_reports??0}</strong> · {t('Stored report versions:','Versi laporan tersimpan:')} <strong>{m.report_versions_recorded??0}</strong>.</p>
    <p className="mt-2 text-xs text-[#866b43]">{t('Approval and submission KPIs use only the latest saved report version per assignment. Previous versions remain audit history. Preview rows are samples, not the denominator of the KPIs.',
      'KPI persetujuan dan pengajuan hanya menghitung versi laporan terbaru per penugasan. Versi sebelumnya tetap berada dalam riwayat audit. Daftar temuan hanya sampel, bukan dasar jumlah KPI.')}</p>
   </section>
   <section className="rounded-xl border bg-white p-5"><h3 className="font-semibold">{t('Executive snapshot','Ringkasan eksekutif')}</h3>
    <p className="mt-2 text-sm leading-6">{template.executive_summary}</p><p className="mt-3 text-xs text-[#866b43]">{report.disclaimer}</p></section>
   <div className="grid gap-4 md:grid-cols-2">{[
     [t('Casework status','Status penugasan'),report.case_status_counts],
     [t('Department workload','Beban kerja unit'),report.department_counts],
     [t('Verified incident provinces','Provinsi kejadian terverifikasi'),report.verified_incident_province_counts],
     [t('Latest report status by assignment','Status laporan terbaru per penugasan'),report.report_status_counts]
   ].map(([heading,data])=><div key={heading} className="rounded-xl border bg-white p-4"><h3 className="mb-3 font-semibold">{heading}</h3>
    {entries(data).length?entries(data).map(([name,value])=><div key={name} className="flex justify-between border-b py-2 text-sm"><span>{name}</span><strong>{value}</strong></div>):<p className="text-sm text-[#64748b]">{t('No records','Tidak ada data')}</p>}</div>)}</div>

   <section className="rounded-xl border bg-white p-5">
    <h3 className="text-base font-semibold">{t('Priority findings for officer review','Temuan prioritas untuk telaah petugas')}</h3>
    <p className="mb-4 mt-1 text-xs text-[#65758a]">{t('Up to eight most recent authorized casework assignments. Their status is not a legal verdict.','Maksimal delapan penugasan terbaru yang diizinkan. Statusnya bukan keputusan hukum.')}</p>
    {(template.findings||[]).length?(template.findings||[]).map((item,i)=><article key={item.case_id} className="border-t border-[#e5e9ee] py-3">
      <p className="font-semibold text-[#24384c]">{i+1}. {item.title}</p>
      <p className="mt-1 text-xs text-[#63748a]">{t('Case','Kasus')} #{item.case_id} · {item.department} · {item.status} · {item.source_reference}</p>
      {item.source_excerpt&&<p className="mt-2 text-sm text-[#405366]">{item.source_excerpt}</p>}
      <p className="mt-1 text-xs text-[#8a6944]">{item.verification_note}</p>
      {sourceUrl(item.source_url)&&<a className="mt-1 inline-block text-xs font-semibold text-[#116d85] underline" href={sourceUrl(item.source_url)} target="_blank" rel="noopener noreferrer">{t('Inspect original evidence','Periksa bukti asli')} ↗</a>}
     </article>):
     <p className="text-sm text-[#65758a]">{t('No authorized casework assignments in this window.','Tidak ada penugasan yang sesuai dalam periode ini.')}</p>}
   </section>
   <section className="rounded-xl border bg-white p-5">
    <h3 className="font-semibold">{t('Recommended next checks','Pemeriksaan lanjutan yang disarankan')}</h3>
    <ol className="ml-5 mt-3 list-decimal space-y-2 text-sm text-[#405366]">{(template.recommended_actions||[]).map((action,index)=><li key={index}>{action}</li>)}</ol>
    <p className="mt-3 text-xs text-[#8a6944]">{t('Recommendations are procedural prompts; no assignments, takedowns, or approvals were created.','Rekomendasi ini hanya panduan prosedur; tidak ada penugasan, takedown, atau persetujuan yang dibuat.')}</p>
   </section>
   <section className="rounded-xl border bg-white p-4"><h3 className="font-semibold">{t('Source-linked assignments','Penugasan beserta sumber')}</h3>
    <div className="mt-3 overflow-x-auto"><table className="w-full text-left text-xs"><thead><tr><th className="p-2">{t('Case','Kasus')}</th><th className="p-2">{t('Date','Tanggal')}</th><th className="p-2">{t('Status','Status')}</th><th className="p-2">{t('Unit','Unit')}</th><th className="p-2">{t('Evidence','Bukti')}</th></tr></thead>
    <tbody>{recent.map(item=><tr className="border-t" key={item.id}><td className="p-2">{item.title}</td><td className="p-2">{item.created_at?.slice(0,10)}</td><td className="p-2">{item.status}</td><td className="p-2">{item.department}</td><td className="p-2">{sourceUrl(item.source_url)?<a className="text-[#116d85] underline" href={sourceUrl(item.source_url)} target="_blank" rel="noopener noreferrer">{t('Original','Asli')}</a>:item.source_type+' #'+item.source_id}</td></tr>)}</tbody></table></div>
    {!recent.length&&<p className="mt-2 text-sm text-[#64748b]">{t('No authorized casework in this period.','Tidak ada penugasan pada periode ini.')}</p>}
   </section>
   <section className="rounded-xl border bg-white p-5">
    <h3 className="font-semibold">{t('Methodology and limitations','Metodologi dan keterbatasan')}</h3>
    <ul className="ml-5 mt-3 list-disc space-y-2 text-sm text-[#52657a]">{(template.methodology||[]).map((note,i)=><li key={i}>{note}</li>)}</ul>
   </section>
   <section className="rounded-xl border bg-white p-5">
    <h3 className="font-semibold">{t('Officer review and sign-off (unsigned)','Pemeriksaan dan pengesahan petugas (belum ditandatangani)')}</h3>
    <p className="mb-4 mt-1 text-xs text-[#8a6944]">{t('Blank signature fields are intentional. Downloading a draft does not indicate approval.','Kolom tanda tangan sengaja dikosongkan. Mengunduh draf bukan berarti persetujuan.')}</p>
    <div className="grid gap-4 text-sm md:grid-cols-2">{[
      t('Prepared by','Disusun oleh'),t('Reviewed by','Ditelaah oleh'),
      t('Approved by','Disetujui oleh'),t('Date','Tanggal')
    ].map(label=><div key={label}><p className="text-xs font-semibold text-[#64748b]">{label}</p><div className="mt-4 border-b border-[#cbd5e1] pb-2">&nbsp;</div></div>)}</div>
   </section>
   <p className="text-xs text-[#64748b]">{t('Interim report v1.0 · Scoped officer casework · Not an official legal determination or approval.',
     'Laporan sementara v1.0 · Penugasan sesuai cakupan petugas · Bukan penetapan atau persetujuan hukum resmi.')}</p>
  </>}
 </section>;
}
