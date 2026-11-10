import {useEffect,useMemo,useRef,useState} from 'react';
import {ClipboardList,FileText,Tag,ArrowRightLeft,CheckCircle2,FilePlus2,Printer,RefreshCw,ExternalLink,Inbox,UserRoundCheck,Send,ShieldCheck} from 'lucide-react';
import {useLanguage} from '@/lib/LanguageContext';

const API='/api/casework';
const STATUS={OPEN:'Baru',ASSIGNED:'Ditugaskan',IN_REVIEW:'Dalam peninjauan',NEEDS_INFORMATION:'Perlu informasi',CLOSED:'Selesai'};
const REPORT={DRAFT:'Draf',SUBMITTED:'Menunggu persetujuan',RETURNED:'Perlu revisi',APPROVED:'Disetujui'};
const TAGS={CANDIDATE:'Kandidat',PROVINCE:'Provinsi',SUSPECTED_VIOLATION:'Indikasi pelanggaran',BAWASLU_ISSUE:'Isu BAWASLU',ELECTORAL_ISSUE:'Isu kepemiluan'};
const initialReport={title:'',executive_summary:'',findings:'',verification_notes:'',recommendations:''};
function Label({children}){return <span className="text-xs font-semibold text-[#53657b]">{children}</span>}
const field='w-full rounded-lg border border-[#dbe3ec] bg-white px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-[#ab454d]';
const small='rounded-lg border border-[#dbe3ec] bg-white px-3 py-2 text-sm hover:bg-[#f7f9fb]';
const primary='rounded-lg bg-[#801b24] text-white px-4 py-2 text-sm font-semibold disabled:opacity-50 hover:bg-[#a52a2f]';
function CaseBadge({status}){return <span className="rounded-full bg-[#f3e9ea] px-2.5 py-1 text-[11px] font-semibold text-[#801b24]">{STATUS[status]||REPORT[status]||status}</span>}
function DateText({value}){if(!value)return null;const d=new Date(value);return <span>{Number.isNaN(d.getTime())?'':d.toLocaleString('id-ID')}</span>}
async function request(path,method='GET',data){
 const token=window.localStorage.getItem('bawaslu_access_token')||'';
 if(!token)throw Error('Sesi masuk tidak tersedia. Silakan masuk kembali.');
 const res=await fetch(API+path,{method,cache:'no-store',headers:{Authorization:'Bearer '+token,...(data?{'Content-Type':'application/json'}:{})},...(data?{body:JSON.stringify(data)}:{})});
 const json=await res.json().catch(()=>({}));
 if(!res.ok){const detail=json.detail||json.error||'Permintaan tidak dapat diselesaikan';throw Error(typeof detail==='string'?detail:JSON.stringify(detail));}
 return json;
}
const safeUrl=value=>{try{const u=new URL(value);return ['https:','http:'].includes(u.protocol)?u.href:null}catch{return null}};
const LinkSource=({href})=>safeUrl(href)?<a href={safeUrl(href)} target="_blank" rel="noopener noreferrer" className="inline-flex items-center gap-1 text-xs font-semibold text-[#116d85] hover:underline"><ExternalLink size={12}/> Lihat sumber asli</a>:null;
function TagList({tags}){if(!tags?.length)return <p className="text-xs text-[#64748b]">Belum ada tag yang didukung data.</p>;return <div className="flex flex-wrap gap-2">{tags.map((t,i)=><span key={i} className="rounded-full border border-[#dfe6ed] bg-[#f8fafc] px-3 py-1 text-xs">{TAGS[t.type]||t.type}: <strong>{t.label}</strong>{t.verified?' · Terverifikasi':''}</span>)}</div>}
function PrintedReport({report,caseItem}){
 if(!report||!caseItem)return null;
 return <div className="hidden print:block bg-white text-black p-6"><h1 className="text-2xl font-bold">{report.title}</h1><p>BAWASLU — laporan pendukung pengawasan · {REPORT[report.status]||report.status}</p><p className="mt-2">Penugasan #{caseItem.id} · {caseItem.target_department}</p>{[['Ringkasan Eksekutif',report.executive_summary],['Temuan',report.findings],['Verifikasi',report.verification_notes],['Rekomendasi',report.recommendations]].map(([title,body])=><section key={title} className="mt-5"><h2 className="font-bold text-lg">{title}</h2><p className="whitespace-pre-wrap">{body||'Belum diisi.'}</p></section>)}<p className="mt-5">Referensi: {caseItem.source_url||caseItem.source_type+' '+caseItem.source_id}</p><p className="mt-4 text-xs">Draf dan rekomendasi memerlukan pemeriksaan petugas berwenang. Tag AI bukan kesimpulan hukum.</p></div>;
}
export default function Casework({embedded=false,initialSource=null,initialCaseId=null,initialTab=null,initialQueue='all'}){
 // Operational workflow hosted inside Intelligence Inbox, not a new module.

 const {language}=useLanguage();
 const isEnglish=language==='en';
 const tr=(en,id)=>isEnglish?en:id;
 const params=new URLSearchParams(embedded?'':window.location.search);
 if(embedded&&initialSource){
  params.set('source_type',initialSource.sourceType||'SOCIAL');
  params.set('source_id',String(initialSource.sourceId||''));
  if(initialSource.campaignId)params.set('campaign_id',String(initialSource.campaignId));
 }
 if(embedded&&initialCaseId)params.set('case_id',String(initialCaseId));
 if(embedded&&initialTab)params.set('tab',initialTab);
 const [sourceType,setSourceType]=useState(params.get('source_type')||'SOCIAL');
 const [sourceId,setSourceId]=useState(params.get('source_id')||'');
 const [campaignId,setCampaignId]=useState(params.get('campaign_id')||'');
 const [tab,setTab]=useState(params.get('tab')==='reports'?'reports':'assignments');
 const [options,setOptions]=useState(null),[cases,setCases]=useState([]),[detail,setDetail]=useState(null),[selected,setSelected]=useState(null);
 const [queueFilter,setQueueFilter]=useState(initialQueue||'all');
 const [queueCounts,setQueueCounts]=useState({});
 const [preview,setPreview]=useState(null),[newTitle,setNewTitle]=useState('');
 const [department,setDepartment]=useState('Data & Analisis'),[scope,setScope]=useState('NATIONAL'),[province,setProvince]=useState(''),[assignee,setAssignee]=useState('');
 const [note,setNote]=useState(''),[routeNote,setRouteNote]=useState(''),[stateNote,setStateNote]=useState('');
 const [newStatus,setNewStatus]=useState('IN_REVIEW');
 const [form,setForm]=useState(initialReport),[editReport,setEditReport]=useState(null);
 const [busy,setBusy]=useState(false),[error,setError]=useState(''),[notice,setNotice]=useState('');
 const [showNew,setShowNew]=useState(Boolean(params.get('source_id')));
 const previewAttempted=useRef(false);
 async function reload(){const [a,b]=await Promise.all([request('/options'),request('/cases')]);setOptions(a);setCases(b.cases||[]);setQueueCounts(b.queue_counts||{});}
 useEffect(()=>{let active=true;Promise.all([request('/options'),request('/cases')]).then(([a,b])=>{if(active){setOptions(a);setCases(b.cases||[]);setQueueCounts(b.queue_counts||{});
    if(embedded&&params.get('source_id')&&!params.get('case_id')){
     const match=(b.cases||[]).find(c=>c.source_type===(params.get('source_type')||'SOCIAL')&&
       String(c.source_id)===String(params.get('source_id'))&&
       String(c.campaign_id||'')===String(params.get('campaign_id')||'')&&c.status!=='CLOSED');
     if(match){setShowNew(false);selectCase(match.id)}
    }
    if(!params.get('case_id')){setScope(a.user_scope||'NATIONAL');setProvince(a.user_province||'')}}}).catch(e=>{if(active)setError(e.message)});return()=>{active=false}},[]);
 useEffect(()=>{
  const id=Number(params.get('case_id')||0);
  if(Number.isInteger(id)&&id>0)selectCase(id);
 },[]);
 async function selectCase(id){setSelected(id);setError('');try{const d=await request('/cases/'+id);setDetail(d);setScope(d.case.target_scope);setProvince(d.case.target_province);setDepartment(d.case.target_department);setAssignee(d.case.assignee_id?String(d.case.assignee_id):'');setNewStatus(d.case.status==='CLOSED'?'CLOSED':'IN_REVIEW');
   const opening=(params.get('tab')==='reports'&&d.reports?.length)?d.reports[0]:null;
   setEditReport(opening?.id||null);
   setForm(opening?{title:opening.title,executive_summary:opening.executive_summary,
      findings:opening.findings,verification_notes:opening.verification_notes,
      recommendations:opening.recommendations}:initialReport)}catch(e){setError(e.message)}}
 const eligible=useMemo(()=>options?.officers?.filter(x=>x.scope===scope&&(scope==='NATIONAL'||x.province===province))||[],[options,scope,province]);
 const filteredCases=useMemo(()=>queueFilter==='all'?cases:cases.filter(x=>Boolean(x.queue_flags?.[queueFilter])),[cases,queueFilter]);
 const queues=[
  ['all',tr('All cases','Semua kasus'),ClipboardList],
  ['assigned_to_me',tr('Assigned to me','Tugas saya'),UserRoundCheck],
  ['team_unassigned',tr('Team inbox','Antrean tim'),Inbox],
  ['needs_my_review',tr('Reports to approve','Laporan perlu persetujuan'),ShieldCheck],
  ['received_from_other_team',tr('Incoming handoffs','Penugasan masuk'),ArrowRightLeft],
  ['sent_by_me',tr('Sent by me','Dikirim oleh saya'),Send]
 ];
 async function act(fn,message){setBusy(true);setError('');setNotice('');try{await fn();setNotice(message);await reload();if(selected){const d=await request('/cases/'+selected);setDetail(d)}}catch(e){setError(e.message)}finally{setBusy(false)}}
 async function previewSource(){setBusy(true);setError('');try{const q=new URLSearchParams({source_type:sourceType,source_id:sourceId,...(sourceType==='SOCIAL'?{campaign_id:campaignId}:{})});const p=await request('/preview?'+q.toString());setPreview(p);setNewTitle(p.title);if(p.recommended_department&&options?.departments?.includes(p.recommended_department))setDepartment(p.recommended_department);if(p.verified_province&&options?.user_scope==='PROVINCE'){setScope('PROVINCE');setProvince(p.verified_province)}else{setScope('NATIONAL');setProvince('')}}catch(e){setError(e.message)}finally{setBusy(false)}}
 useEffect(()=>{if(embedded&&sourceId&&showNew&&options?.can_create&&!preview&&!previewAttempted.current){
  previewAttempted.current=true;
  previewSource();
 }},[embedded,sourceId,showNew,options?.can_create]);
 async function createCase(){await act(async()=>{const created=await request('/cases','POST',{source_type:sourceType,source_id:sourceId,campaign_id:sourceType==='SOCIAL'?Number(campaignId):null,title:newTitle,department,target_scope:scope,target_province:scope==='PROVINCE'?province:'',assignee_id:assignee?Number(assignee):null,notes:note});setShowNew(false);setPreview(null);setSelected(created.id);setDetail(await request('/cases/'+created.id));setTab(initialTab==='reports'?'reports':'assignments')},tr('Assignment created. Review the evidence and prepare the report.','Penugasan dibuat. Periksa bukti dan siapkan laporan.'))}
 async function acknowledge(){
  if(!selected||busy)return;
  await act(async()=>{await request('/cases/'+selected+'/acknowledge','POST',{})},
   tr('Assignment accepted. Review started and the action was recorded.',
      'Penugasan diterima. Penelaahan dimulai dan tindakan tercatat.'));
 }
 async function route(){if(!detail)return;await act(async()=>{await request('/cases/'+selected+'/route','POST',{department,target_scope:scope,target_province:scope==='PROVINCE'?province:'',assignee_id:assignee?Number(assignee):null,note:routeNote});setRouteNote('')},'Penugasan dialihkan dan riwayat dicatat.')}
 async function status(){await act(async()=>{await request('/cases/'+selected+'/status','POST',{status:newStatus,note:stateNote});setStateNote('')},'Status penugasan diperbarui.')}
 function beginReport(report){setEditReport(report?.id||null);setForm(report?{title:report.title,executive_summary:report.executive_summary,findings:report.findings,verification_notes:report.verification_notes,recommendations:report.recommendations}:{...initialReport,title:'Laporan analisis — '+(detail?.case?.title||'')});setTab('reports')}
 async function saveReport(){await act(async()=>{if(editReport){await request('/reports/'+editReport,'PUT',form)}else{await request('/cases/'+selected+'/reports','POST',form)}setEditReport(null)},'Draf laporan tersimpan.')}
 async function aiDraft(){await act(async()=>{await request('/cases/'+selected+'/reports/ai-draft','POST',{});setTab('reports')},'Draf AI dibuat sebagai bahan telaah, bukan laporan final.')}
 async function reportTransition(report,status){await act(async()=>{const comment=status==='RETURNED'?window.prompt('Alasan pengembalian (minimal 8 karakter):',''):'';
 if(status==='RETURNED'&&(!comment||comment.trim().length<8))throw Error('Diperlukan alasan pengembalian minimal 8 karakter.');
 await request('/reports/'+report.id+'/transition','POST',{status,review_comment:comment||''})},status==='APPROVED'?'Laporan disetujui oleh pemeriksa.':'Status laporan diperbarui.')}
 const selectedCase=detail?.case||null;
 
 return <div className={(embedded?'w-full space-y-4':'mx-auto max-w-[1440px] space-y-5')+' print:max-w-none print:p-0'} data-i18n-exempt lang={isEnglish?'en':'id'}>
  {!embedded&&<div className="rounded-2xl bg-gradient-to-r from-[#801b24] to-[#a52a2f] px-6 py-6 text-white print:hidden"><div className="text-xs tracking-widest text-[#f4d3d0] uppercase">BAWASLU · Penanganan Intelijen</div><h1 className="mt-2 text-2xl font-bold">Penugasan & Laporan</h1><p className="text-sm text-[#f6e4e2] mt-1">Tag AI → peninjauan petugas → penugasan tim → laporan → persetujuan</p></div>}
  {(!embedded||!sourceId)&&<section className="intel-card p-3 print:hidden" aria-label={tr('Workload queues','Antrean pekerjaan')}>
    <p className="mb-3 text-xs font-semibold text-[#526477]">{tr('Your operational queues — select a category to filter cases','Antrean kerja Anda — pilih kategori untuk menyaring kasus')}</p>
    <div className="grid grid-cols-2 gap-2 md:grid-cols-3 xl:grid-cols-6">{queues.map(([key,label,Icon])=>
      <button key={key} type="button" aria-pressed={queueFilter===key}
        onClick={()=>{setQueueFilter(key);if(key==='needs_my_review')setTab('reports')}}
        className={'flex flex-col gap-1 rounded-lg border p-3 text-left transition-colors '+(queueFilter===key?
          'border-[#b65c64] bg-[#fdf1f2] text-[#801b24]':
          'border-[#dbe4eb] bg-white text-[#405267] hover:bg-[#f8fafc]')}>
        <Icon size={17}/><strong className="text-xl tabular-nums">{Number(queueCounts[key]||0)}</strong>
        <span className="text-xs leading-tight">{label}</span>
      </button>)}</div>
    <p className="mt-2 text-xs text-[#64748b]">{tr(
      'Incoming assignments require receiving-officer acceptance. Approval requires a different authorized reviewer.',
      'Penugasan masuk harus diterima petugas tujuan. Persetujuan laporan dilakukan pemeriksa lain yang berwenang.')}</p>
   </section>}
  <div className="flex flex-wrap gap-2 print:hidden"><button className={tab==='assignments'?primary:small} onClick={()=>setTab('assignments')}><ClipboardList size={15} className="inline mr-1"/> Penugasan</button><button className={tab==='reports'?primary:small} onClick={()=>setTab('reports')}><FileText size={15} className="inline mr-1"/> Laporan</button><button className={small} onClick={()=>act(async()=>{await reload()},'Daftar diperbarui')} disabled={busy}><RefreshCw size={14} className="inline mr-1"/> Segarkan</button>{options?.can_create&&<button className={primary} onClick={()=>{setShowNew(v=>!v);setTab('assignments')}}><FilePlus2 size={15} className="inline mr-1"/> Buat penugasan</button>}</div>
  {error&&<p role="alert" className="rounded-lg border border-red-200 bg-red-50 px-4 py-3 text-sm text-red-700 print:hidden">{error}</p>}
  {notice&&<p role="status" className="rounded-lg border border-[#d3e8df] bg-[#f3faf7] px-4 py-3 text-sm text-[#116846] print:hidden">{notice}</p>}
  {showNew&&options?.can_create&&<section className="intel-card p-5 space-y-4 print:hidden"><h2 className="font-bold text-[#801b24]">Penugasan baru dari sumber yang sudah tersimpan</h2>{embedded&&sourceId?
   <p className="rounded-lg border border-[#e3e9ef] bg-[#f8fafc] px-3 py-2 text-xs text-[#536579]">
    {tr('Selected source','Sumber terpilih')}: {sourceType} #{sourceId}{campaignId?' · '+tr('Campaign','Kampanye')+' '+campaignId:''}
   </p>:
   <div className="grid md:grid-cols-3 gap-3"><label className="space-y-1"><Label>Tipe sumber</Label><select className={field} value={sourceType} onChange={e=>{setSourceType(e.target.value);setPreview(null)}}><option value="SOCIAL">Unggahan Social Listening</option><option value="INTELLIGENCE">Rekaman Intelijen</option></select></label><label className="space-y-1"><Label>Nomor rekaman</Label><input className={field} value={sourceId} onChange={e=>{setSourceId(e.target.value);setPreview(null)}} placeholder={sourceType==='SOCIAL'?'Contoh: 209':'Contoh: INT-2026-001'}/></label>{sourceType==='SOCIAL'&&<label className="space-y-1"><Label>Nomor kampanye</Label><input className={field} value={campaignId} onChange={e=>{setCampaignId(e.target.value);setPreview(null)}} placeholder="ID kampanye sumber" /></label>}</div>}<button className={small} disabled={busy||!sourceId||sourceType==='SOCIAL'&&!campaignId} onClick={previewSource}><Tag size={14} className="inline mr-1"/> Identifikasi tag dari data</button>
  {preview&&<div className="space-y-3 rounded-xl bg-[#f7f9fb] border border-[#e3e9ef] p-4"><p className="text-sm font-semibold">{preview.title}</p><p className="text-sm text-[#64748b] line-clamp-3">{preview.excerpt}</p><TagList tags={preview.tags}/><p className="text-xs text-[#64748b]">Provinsi terverifikasi petugas: {preview.verified_province||'Belum ada'}. Petunjuk provinsi dan indikasi pelanggaran tidak menjadi keputusan otomatis.</p><LinkSource href={preview.source_url}/><div className="grid md:grid-cols-2 gap-3"><label className="space-y-1"><Label>Judul penugasan</Label><input className={field} value={newTitle} onChange={e=>setNewTitle(e.target.value)}/></label><label className="space-y-1"><Label>Departemen tujuan</Label><select className={field} value={department} onChange={e=>setDepartment(e.target.value)}>{options.departments.map(d=><option key={d}>{d}</option>)}</select></label><label className="space-y-1"><Label>Tim penerima</Label><select className={field} value={scope} onChange={e=>{setScope(e.target.value);setProvince(e.target.value==='PROVINCE'?(preview.verified_province||''):'');setAssignee('')}}><option value="NATIONAL">Nasional</option><option value="PROVINCE" disabled={!preview.verified_province}>Provinsi (wajib lokasi tervalidasi)</option></select></label>{scope==='PROVINCE'&&<label className="space-y-1"><Label>Provinsi terverifikasi</Label><input className={field} readOnly value={preview.verified_province||''}/></label>}<label className="space-y-1"><Label>Petugas tujuan (opsional)</Label><select className={field} value={assignee} onChange={e=>setAssignee(e.target.value)}><option value="">Antrean departemen</option>{eligible.map(o=><option key={o.id} value={o.id}>{o.name}{o.province?' — '+o.province:''}</option>)}</select></label></div><label className="block space-y-1"><Label>Catatan penugasan</Label><textarea className={field} rows={2} value={note} onChange={e=>setNote(e.target.value)} placeholder="Alasan dan prioritas kerja untuk petugas"/></label><button className={primary} disabled={busy||!newTitle.trim()||scope==='PROVINCE'&&!preview.verified_province} onClick={createCase}>Simpan penugasan</button></div>}</section>}
  <div className={embedded&&sourceId?'grid gap-4 print:block':'grid gap-4 lg:grid-cols-[320px_minmax(0,1fr)] print:block'}>
   {(!embedded||!sourceId)&&<aside className="intel-card p-3 max-h-[75vh] overflow-y-auto space-y-2 print:hidden"><div className="flex justify-between px-2 py-2 items-center"><h2 className="font-bold text-[#263749]">Daftar penugasan</h2><span className="text-xs text-[#64748b]">{filteredCases.length} / {cases.length}</span></div>{filteredCases.map(c=><button key={c.id} onClick={()=>{selectCase(c.id);if(queueFilter==='needs_my_review')setTab('reports')}} className={'w-full rounded-lg p-3 text-left border '+(selected===c.id?'bg-[#fbf0f0] border-[#d7a4a6]':'border-transparent hover:bg-[#f7f9fb]')}><div className="flex justify-between gap-1 items-start"><span className="text-xs font-bold text-[#801b24]">#{c.id} · {c.target_department}</span><CaseBadge status={c.status}/></div><p className="font-semibold text-sm line-clamp-2 mt-2">{c.title}</p><p className="text-xs text-[#64748b] mt-1">{c.target_scope==='NATIONAL'?tr('National','Nasional'):c.target_province} · <DateText value={c.updated_at}/></p>
    {(c.queue_flags?.assigned_to_me||c.queue_flags?.needs_my_review)&&<p className="text-[11px] font-semibold text-[#801b24] mt-1">{c.queue_flags?.needs_my_review?
     tr('Approval requested','Menunggu persetujuan'):tr('Assigned to you','Ditugaskan kepada Anda')}</p>}</button>)}{!filteredCases.length&&<p className="text-sm text-[#64748b] p-3">{cases.length?
   tr('No cases in this queue. Choose another category.','Belum ada kasus pada antrean ini. Pilih kategori lain.'):
   tr('No assignments are visible within your authorized scope.','Belum ada penugasan yang terlihat dalam kewenangan Anda.')}</p>}</aside>}
   <div className="min-w-0 space-y-4 print:hidden">
    {!selectedCase&&<section className="intel-card p-8 text-center text-[#64748b]"><ClipboardList size={28} className="mx-auto mb-3"/><p>Pilih penugasan untuk melihat pemeriksaan, pengalihan antar tim dan draf laporannya.</p></section>}
    {selectedCase&&<><section className="intel-card p-5 space-y-4"><div className="flex flex-wrap justify-between gap-2"><div><p className="text-xs font-semibold text-[#801b24]">KASUS #{selectedCase.id} · {selectedCase.source_type}</p><h2 className="text-xl font-bold mt-1 text-[#273444]">{selectedCase.title}</h2></div><CaseBadge status={selectedCase.status}/></div><div className="grid sm:grid-cols-2 gap-2 text-sm"><p><strong>Tujuan:</strong> {selectedCase.target_department} — {selectedCase.target_scope==='NATIONAL'?'Nasional':selectedCase.target_province}</p><p><strong>Petugas:</strong> {options?.officers?.find(o=>o.id===selectedCase.assignee_id)?.name||'Antrean departemen'}</p><p><strong>Provinsi kejadian terverifikasi:</strong> {selectedCase.verified_province||'Belum terverifikasi'}</p><p><strong>Status:</strong> {STATUS[selectedCase.status]||selectedCase.status}</p></div><TagList tags={selectedCase.tags}/><p className="text-sm whitespace-pre-wrap bg-[#f7f9fb] rounded-lg p-3">{selectedCase.source_excerpt}</p><LinkSource href={selectedCase.source_url}/></section>
      {tab==='assignments'&&<>{detail?.can_acknowledge&&<section className="intel-card p-5 space-y-2 border-l-4 border-[#a52a2f]">
         <h3 className="font-bold text-[#801b24]">{tr('Incoming assignment','Penugasan masuk')}</h3>
         <p className="text-sm text-[#53657b]">{tr(
           'This case is ready for the receiving team. Accept it to claim an unassigned item and begin review. No legal determination is made.',
           'Kasus siap ditangani tim penerima. Terima untuk mengambil tugas yang belum ditugaskan dan mulai menelaah. Tidak ada keputusan hukum otomatis.')}</p>
         <button className={primary} disabled={busy} onClick={acknowledge}>
           <CheckCircle2 size={15} className="inline mr-1"/>{tr('Accept & start review','Terima & mulai penelaahan')}
         </button>
       </section>}
       <section className="intel-card p-5 space-y-4"><h3 className="font-bold text-[#801b24]"><ArrowRightLeft size={16} className="inline mr-2"/>Alihkan ke tim / departemen</h3><div className="grid md:grid-cols-2 gap-3"><label className="space-y-1"><Label>Departemen</Label><select disabled={!detail?.can_edit||busy} className={field} value={department} onChange={e=>setDepartment(e.target.value)}>{options?.departments?.map(d=><option key={d}>{d}</option>)}</select></label><label className="space-y-1"><Label>Tim</Label><select disabled={!detail?.can_edit||busy} className={field} value={scope} onChange={e=>{setScope(e.target.value);setAssignee('');setProvince(e.target.value==='PROVINCE'?(selectedCase.verified_province||''):'' )}}><option value="NATIONAL">Nasional</option><option value="PROVINCE" disabled={!selectedCase.verified_province}>Provinsi (lokasi terkonfirmasi)</option></select></label>{scope==='PROVINCE'&&<label className="space-y-1"><Label>Provinsi</Label><input className={field} value={province} readOnly/></label>}<label className="space-y-1"><Label>Petugas penerima</Label><select disabled={!detail?.can_edit||busy} className={field} value={assignee} onChange={e=>setAssignee(e.target.value)}><option value="">Antrean departemen</option>{eligible.map(o=><option value={o.id} key={o.id}>{o.name}</option>)}</select></label></div><textarea className={field} rows={2} value={routeNote} disabled={!detail?.can_edit} onChange={e=>setRouteNote(e.target.value)} placeholder="Alasan pengalihan (minimal 8 karakter)"/><button className={primary} disabled={!detail?.can_edit||busy||routeNote.trim().length<8} onClick={route}>Kirim penugasan</button></section><section className="intel-card p-5 space-y-3"><h3 className="font-bold text-[#801b24]">Perbarui status</h3><div className="flex flex-wrap gap-2"><select className={field+' max-w-xs'} value={newStatus} onChange={e=>setNewStatus(e.target.value)} disabled={!detail?.can_edit}>{Object.entries(STATUS).filter(([code])=>code!=='CLOSED'||detail?.can_approve).map(([code,label])=><option key={code} value={code}>{label}</option>)}</select><button className={primary} disabled={!detail?.can_edit||busy||stateNote.trim().length<8} onClick={status}>Simpan status</button></div><textarea className={field} value={stateNote} onChange={e=>setStateNote(e.target.value)} rows={2} placeholder="Catatan perubahan (minimal 8 karakter)" disabled={!detail?.can_edit}/></section><section className="intel-card p-5"><h3 className="font-bold text-[#801b24]">Riwayat dan audit</h3><div className="mt-3 space-y-2">{detail?.events?.map(event=><div className="border-l-2 border-[#d1b1b5] pl-3 py-1" key={event.id}><p className="text-sm font-semibold">{event.action.replaceAll('_',' ')}</p><p className="text-xs text-[#64748b]"><DateText value={event.at}/> · Petugas #{event.actor_id}</p><p className="text-xs mt-1 text-[#64748b]">{event.details?.note||''}</p></div>)}</div></section></>}
      {tab==='reports'&&<><section className="intel-card p-5"><div className="flex justify-between gap-2 mb-4 flex-wrap"><h3 className="font-bold text-[#801b24]">Laporan dan persetujuan</h3><div className="flex flex-wrap gap-2">{detail?.can_edit&&<><button className={small} onClick={()=>beginReport(null)}>Draf baru</button><button className={small} onClick={aiDraft} disabled={busy}>Buat draf analisis dengan AI</button></>}</div></div>{detail?.reports?.map(r=><div key={r.id} className="border border-[#e5eaf0] rounded-lg p-4 mb-3"><div className="flex justify-between gap-2"><div><p className="font-semibold">{r.title}</p><p className="text-xs text-[#64748b] mt-1">Laporan #{r.id} · <DateText value={r.updated_at}/></p></div><CaseBadge status={r.status}/></div><p className="text-xs whitespace-pre-wrap mt-2 line-clamp-4">{r.executive_summary||r.findings||'Belum ada isi.'}</p><div className="flex flex-wrap gap-2 mt-3"><button className={small} onClick={()=>{setEditReport(r.id);setForm({title:r.title,executive_summary:r.executive_summary,findings:r.findings,verification_notes:r.verification_notes,recommendations:r.recommendations})}}>Baca laporan</button>{detail?.can_edit&&['DRAFT','RETURNED'].includes(r.status)&&<button className={small} onClick={()=>reportTransition(r,'SUBMITTED')} disabled={busy}>Ajukan persetujuan</button>}{detail?.can_approve&&r.status==='SUBMITTED'&&r.created_by!==options?.current_user_id&&<><button className={small} disabled={busy} onClick={()=>reportTransition(r,'APPROVED')}>Setujui</button><button className={small} disabled={busy} onClick={()=>reportTransition(r,'RETURNED')}>Kembalikan</button></>}</div>{r.review_comment&&<p className="mt-2 text-xs text-[#8c4350]">Umpan balik: {r.review_comment}</p>}</div>)}{!detail?.reports?.length&&<p className="text-sm text-[#64748b]">Belum ada laporan. Gunakan draf manual atau draf AI yang harus diperiksa petugas.</p>}</section>
       {(form.title||editReport)&&<section className="intel-card p-5 space-y-3"><h3 className="font-bold text-[#801b24]">Editor laporan</h3>{[['title','Judul',1],['executive_summary','Ringkasan eksekutif',4],['findings','Temuan dan bukti',5],['verification_notes','Pemeriksaan dan keterbatasan bukti',4],['recommendations','Rekomendasi tindak lanjut',4]].map(([key,label,rows])=><label className="block space-y-1" key={key}><Label>{label}</Label>{rows===1?<input className={field} value={form[key]} onChange={e=>setForm(old=>({...old,[key]:e.target.value}))}/>:<textarea className={field} rows={rows} value={form[key]} onChange={e=>setForm(old=>({...old,[key]:e.target.value}))}/>}</label>)}<div className="flex gap-2 flex-wrap"><button className={primary} disabled={!detail?.can_edit||busy||!form.title||(!!editReport&&!['DRAFT','RETURNED'].includes(detail?.reports?.find(r=>r.id===editReport)?.status))} onClick={saveReport}>Simpan draf</button>{editReport&&<button className={small} onClick={()=>{const r=detail?.reports?.find(x=>x.id===editReport);if(r){document.title=r.title;window.print()}}}><Printer size={14} className="inline mr-1"/> Cetak laporan</button>}</div></section>}</>}
     </>}
   </div>
  </div>
  <PrintedReport report={detail?.reports?.find(x=>x.id===editReport)} caseItem={selectedCase}/>
 </div>;
}
