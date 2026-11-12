import {useEffect,useMemo,useRef,useState} from 'react';
import {ClipboardList,FileText,Tag,ArrowRightLeft,CheckCircle2,FilePlus2,Printer,RefreshCw,ExternalLink,Inbox,UserRoundCheck,Send,ShieldCheck} from 'lucide-react';
import {useLanguage} from '@/lib/LanguageContext';

const API='/api/casework';
const STATUS={OPEN:'Baru',ASSIGNED:'Ditugaskan',IN_REVIEW:'Dalam peninjauan',NEEDS_INFORMATION:'Perlu informasi',CLOSED:'Selesai'};
const REPORT={DRAFT:'Draf',SUBMITTED:'Menunggu persetujuan',RETURNED:'Perlu revisi',APPROVED:'Disetujui'};
const TAGS={CANDIDATE:'Kandidat',PROVINCE:'Provinsi',SUSPECTED_VIOLATION:'Indikasi pelanggaran',BAWASLU_ISSUE:'Isu BAWASLU',ELECTORAL_ISSUE:'Isu kepemiluan'};
const initialReport={title:'',executive_summary:'',findings:'',verification_notes:'',recommendations:''};
const TRACE_LABELS={
 source_linked:['Original source linked','Sumber asli tertaut'],
 receiving_officer_accepted:['Receiving officer accepted','Petugas penerima menerima'],
 original_source_checked:['Original source access reviewed','Akses sumber asli diperiksa'],
 latest_report_submitted:['Current report submitted','Laporan terkini diajukan'],
 independent_report_approval:['Independent officer approval','Persetujuan pemeriksa lain']
};
function Label({children}){return <span className="text-xs font-semibold text-[#53657b]">{children}</span>}
const field='w-full rounded-lg border border-[#dbe3ec] bg-white px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-[#ab454d]';
const small='rounded-lg border border-[#dbe3ec] bg-white px-3 py-2 text-sm hover:bg-[#f7f9fb]';
const primary='rounded-lg bg-[#801b24] text-white px-4 py-2 text-sm font-semibold disabled:opacity-50 hover:bg-[#a52a2f]';
const EN_STATUS={OPEN:'Open',ASSIGNED:'Assigned',IN_REVIEW:'In review',NEEDS_INFORMATION:'More information',CLOSED:'Closed',DRAFT:'Draft',SUBMITTED:'Submitted',RETURNED:'Returned',APPROVED:'Approved'};
function CaseBadge({status,english=false}){return <span className="rounded-full bg-[#f3e9ea] px-2.5 py-1 text-[11px] font-semibold text-[#801b24]">{english?EN_STATUS[status]||status:STATUS[status]||REPORT[status]||status}</span>}
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
 const [sourceReviewStatus,setSourceReviewStatus]=useState('SOURCE_CHECKED');
 const [sourceReviewNote,setSourceReviewNote]=useState('');
 const [sourceOpened,setSourceOpened]=useState(false);
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
 async function selectCase(id){setSelected(id);setError('');setSourceReviewNote('');setSourceOpened(false);try{const d=await request('/cases/'+id);setDetail(d);setScope(d.case.target_scope);setProvince(d.case.target_province);setDepartment(d.case.target_department);setAssignee(d.case.assignee_id?String(d.case.assignee_id):'');setNewStatus(d.case.status==='CLOSED'?'CLOSED':'IN_REVIEW');
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
 async function recordSourceReview(){
  if(!selected||busy)return;
  await act(async()=>{
   await request('/cases/'+selected+'/source-review','POST',{
    status:sourceReviewStatus,note:sourceReviewNote.trim(),
    original_source_opened:sourceOpened
   });
   setSourceReviewNote('');setSourceOpened(false);
  },tr('Source-access review recorded in the audit trail. This is not a legal verdict.',
      'Pemeriksaan akses sumber dicatat dalam audit. Ini bukan putusan hukum.'));
 }
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
 const activeReport=detail?.reports?.find(r=>r.id===editReport)||null;
 const focused=embedded&&Boolean(sourceId||initialCaseId);
 const emptyQueue=embedded&&!focused&&cases.length===0&&!showNew;
 
 return <div className={(embedded?'w-full space-y-4':'mx-auto max-w-[1440px] space-y-5')+' print:max-w-none print:p-0'} data-i18n-exempt lang={isEnglish?'en':'id'}>
  {!embedded&&<div className="rounded-2xl bg-gradient-to-r from-[#801b24] to-[#a52a2f] px-6 py-6 text-white print:hidden"><div className="text-xs tracking-widest text-[#f4d3d0] uppercase">BAWASLU · Penanganan Intelijen</div><h1 className="mt-2 text-2xl font-bold">Penugasan & Laporan</h1><p className="text-sm text-[#f6e4e2] mt-1">Tag AI → peninjauan petugas → penugasan tim → laporan → persetujuan</p></div>}
  {!embedded&&<section className="intel-card p-3 print:hidden" aria-label={tr('Workload queues','Antrean pekerjaan')}>
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
  {embedded&&!focused&&<div className="flex items-end gap-2 print:hidden" data-inbox-queue-picker>
   <label className="min-w-0 flex-1 space-y-1"><span className="block text-xs font-semibold text-[#526477]">{tr('Show work','Lihat pekerjaan')}</span>
    <select className={field} value={queueFilter} aria-label={tr('Filter assignments','Filter penugasan')} onChange={e=>{setQueueFilter(e.target.value);setSelected(null);setDetail(null);setTab(e.target.value==='needs_my_review'?'reports':'assignments')}}>
     {queues.map(([key,label])=><option key={key} value={key}>{label} ({Number(queueCounts[key]||0)})</option>)}
    </select>
   </label><button type="button" className={small+' h-10 shrink-0'} disabled={busy} aria-label={tr('Refresh','Segarkan')} onClick={()=>act(reload,tr('Updated','Diperbarui'))}><RefreshCw size={16}/></button>
  </div>}
  {(!embedded||!!selectedCase)&&<div className="flex flex-wrap gap-2 print:hidden">
    <button type="button" className={tab==='assignments'?primary:small} onClick={()=>setTab('assignments')}><ClipboardList size={15} className="inline mr-1"/>{tr('Assignment','Penugasan')}</button>
    <button type="button" className={tab==='reports'?primary:small} onClick={()=>setTab('reports')}><FileText size={15} className="inline mr-1"/>{tr('Report','Laporan')}</button>
    {!embedded&&<button type="button" className={small} disabled={busy} onClick={()=>act(reload,tr('Updated','Diperbarui'))}><RefreshCw size={14} className="inline mr-1"/>{tr('Refresh','Segarkan')}</button>}
    {!embedded&&options?.can_create&&<button type="button" className={primary} onClick={()=>{setShowNew(v=>!v);setTab('assignments')}}><FilePlus2 size={15} className="inline mr-1"/>{tr('New assignment','Buat penugasan')}</button>}
   </div>}
  {error&&<p role="alert" className="rounded-lg border border-red-200 bg-red-50 px-4 py-3 text-sm text-red-700 print:hidden">{error}</p>}
  {notice&&<p role="status" className="rounded-lg border border-[#d3e8df] bg-[#f3faf7] px-4 py-3 text-sm text-[#116846] print:hidden">{notice}</p>}
  {cases.length>=300&&<p className="rounded-lg border border-[#e6e0c9] bg-[#fbfaf2] p-3 text-xs text-[#7b6038] print:hidden">{tr(
    'Showing the latest 300 cases in your authorized region; queue totals describe this recent window, not all historical casework.',
    'Menampilkan 300 kasus terbaru sesuai wilayah akses; jumlah antrean berlaku untuk periode data terbaru, bukan seluruh riwayat penugasan.')}</p>}
  {showNew&&options?.can_create&&<section className="intel-card p-5 space-y-4 print:hidden"><h2 className="font-bold text-[#801b24]">{tr('Assign this intelligence record','Tugaskan temuan intelijen ini')}</h2>{embedded&&sourceId?
   <p className="rounded-lg border border-[#e3e9ef] bg-[#f8fafc] px-3 py-2 text-xs text-[#536579]">
    {tr('Selected source','Sumber terpilih')}: {sourceType} #{sourceId}{campaignId?' · '+tr('Campaign','Kampanye')+' '+campaignId:''}
   </p>:
   <div className="grid md:grid-cols-3 gap-3"><label className="space-y-1"><Label>Tipe sumber</Label><select className={field} value={sourceType} onChange={e=>{setSourceType(e.target.value);setPreview(null)}}><option value="SOCIAL">Unggahan Social Listening</option><option value="INTELLIGENCE">Rekaman Intelijen</option></select></label><label className="space-y-1"><Label>Nomor rekaman</Label><input className={field} value={sourceId} onChange={e=>{setSourceId(e.target.value);setPreview(null)}} placeholder={sourceType==='SOCIAL'?'Contoh: 209':'Contoh: INT-2026-001'}/></label>{sourceType==='SOCIAL'&&<label className="space-y-1"><Label>Nomor kampanye</Label><input className={field} value={campaignId} onChange={e=>{setCampaignId(e.target.value);setPreview(null)}} placeholder="ID kampanye sumber" /></label>}</div>}{(!embedded||!preview)&&<button className={small} disabled={busy||!sourceId||sourceType==='SOCIAL'&&!campaignId} onClick={previewSource}><Tag size={14} className="inline mr-1"/>{tr('Load evidence and suggested tags','Muat bukti dan saran tag')}</button>}
  {preview&&<div className="space-y-3 rounded-xl bg-[#f7f9fb] border border-[#e3e9ef] p-4"><p className="text-sm font-semibold">{preview.title}</p><p className="text-sm text-[#64748b] line-clamp-3">{preview.excerpt}</p><TagList tags={preview.tags}/><p className="text-xs text-[#64748b]">{tr('Officer-verified province','Provinsi terverifikasi petugas')}: {preview.verified_province||tr('Not yet confirmed','Belum ada')}. {tr('AI location and violation hints are not legal decisions.','Petunjuk provinsi dan indikasi pelanggaran bukan keputusan hukum.')}</p><LinkSource href={preview.source_url}/><div className="grid md:grid-cols-2 gap-3"><label className="space-y-1"><Label>{tr('Assignment title','Judul penugasan')}</Label><input className={field} value={newTitle} onChange={e=>setNewTitle(e.target.value)}/></label><label className="space-y-1"><Label>{tr('Receiving department','Departemen tujuan')}</Label><select className={field} value={department} onChange={e=>setDepartment(e.target.value)}>{options.departments.map(d=><option key={d}>{d}</option>)}</select></label><label className="space-y-1"><Label>{tr('Receiving team','Tim penerima')}</Label><select className={field} value={scope} onChange={e=>{setScope(e.target.value);setProvince(e.target.value==='PROVINCE'?(preview.verified_province||''):'');setAssignee('')}}><option value="NATIONAL">Nasional</option><option value="PROVINCE" disabled={!preview.verified_province}>{tr('Province (verified location required)','Provinsi (wajib lokasi tervalidasi)')}</option></select></label>{scope==='PROVINCE'&&<label className="space-y-1"><Label>{tr('Verified province','Provinsi terverifikasi')}</Label><input className={field} readOnly value={preview.verified_province||''}/></label>}<label className="space-y-1"><Label>{tr('Receiving officer (optional)','Petugas tujuan (opsional)')}</Label><select className={field} value={assignee} onChange={e=>setAssignee(e.target.value)}><option value="">{tr('Department queue','Antrean departemen')}</option>{eligible.map(o=><option key={o.id} value={o.id}>{o.name}{o.province?' — '+o.province:''}</option>)}</select></label></div><label className="block space-y-1"><Label>{tr('Assignment note','Catatan penugasan')}</Label><textarea className={field} rows={2} value={note} onChange={e=>setNote(e.target.value)} placeholder="Alasan dan prioritas kerja untuk petugas"/></label><button className={primary} disabled={busy||!newTitle.trim()||scope==='PROVINCE'&&!preview.verified_province} onClick={createCase}>{tr('Save assignment','Simpan penugasan')}</button></div>}</section>}
  {emptyQueue&&<section role="status" data-inbox-empty-state className="rounded-xl border border-[#e1e7ed] bg-white px-5 py-8 text-center print:hidden">
    <ClipboardList size={23} className="mx-auto mb-3 text-[#8ca0b3]"/>
    <p className="text-sm font-semibold text-[#2c4155]">{queueFilter==='needs_my_review'?
      tr('No reports awaiting your approval','Tidak ada laporan menunggu persetujuan'):
      queueFilter==='assigned_to_me'?tr('No assignments for you yet','Belum ada penugasan untuk Anda'):
      tr('No work in this queue yet','Belum ada pekerjaan pada antrean ini')}</p>
    <p className="mx-auto mt-2 max-w-sm text-xs leading-relaxed text-[#65788b]">{tr(
      'Select a post in Intelligence Inbox, then choose Assign / Transfer or Draft Report.',
      'Pilih unggahan di Kotak Masuk Intelijen, lalu gunakan Tugaskan / Alihkan atau Buat Draf Laporan.')}</p>
   </section>}
  {!emptyQueue&&<div className={embedded?'grid gap-4 print:block':'grid gap-4 lg:grid-cols-[320px_minmax(0,1fr)] print:block'}>
   {(!embedded||(!focused&&!selectedCase))&&<aside className="intel-card p-3 max-h-[45vh] overflow-y-auto space-y-2 print:hidden"><div className="flex justify-between px-2 py-2 items-center"><h2 className="font-bold text-[#263749]">{tr('Assignments','Daftar penugasan')}</h2><span className="text-xs text-[#64748b]">{filteredCases.length} / {cases.length}</span></div>{filteredCases.map(c=><button key={c.id} onClick={()=>{selectCase(c.id);if(queueFilter==='needs_my_review')setTab('reports')}} className={'w-full rounded-lg p-3 text-left border '+(selected===c.id?'bg-[#fbf0f0] border-[#d7a4a6]':'border-transparent hover:bg-[#f7f9fb]')}><div className="flex justify-between gap-1 items-start"><span className="text-xs font-bold text-[#801b24]">#{c.id} · {c.target_department}</span><CaseBadge status={c.status} english={isEnglish}/></div><p className="font-semibold text-sm line-clamp-2 mt-2">{c.title}</p><p className="text-xs text-[#64748b] mt-1">{c.target_scope==='NATIONAL'?tr('National','Nasional'):c.target_province} · <DateText value={c.updated_at}/></p>
    {(c.queue_flags?.assigned_to_me||c.queue_flags?.needs_my_review)&&<p className="text-[11px] font-semibold text-[#801b24] mt-1">{c.queue_flags?.needs_my_review?
     tr('Approval requested','Menunggu persetujuan'):tr('Assigned to you','Ditugaskan kepada Anda')}</p>}</button>)}{!filteredCases.length&&<p className="text-sm text-[#64748b] p-3">{cases.length?
   tr('No cases in this queue. Choose another category.','Belum ada kasus pada antrean ini. Pilih kategori lain.'):
   tr('No assignments are visible within your authorized scope.','Belum ada penugasan yang terlihat dalam kewenangan Anda.')}</p>}</aside>}
   <div className="min-w-0 space-y-4 print:hidden">
    {embedded&&selectedCase&&!focused&&<button type="button" className={small+' text-xs'} onClick={()=>{setSelected(null);setDetail(null)}}>{tr('Back to assignments','Kembali ke penugasan')}</button>}
    {!selectedCase&&!embedded&&<section className="intel-card p-8 text-center text-[#64748b]"><ClipboardList size={28} className="mx-auto mb-3"/><p>{tr('Select an assignment to review its evidence and report.','Pilih penugasan untuk meninjau bukti dan laporannya.')}</p></section>}
    {selectedCase&&<><section className="intel-card p-5 space-y-4"><div className="flex flex-wrap justify-between gap-2"><div><p className="text-xs font-semibold text-[#801b24]">KASUS #{selectedCase.id} · {selectedCase.source_type}</p><h2 className="text-lg font-bold mt-1 text-[#273444] break-words">{selectedCase.title}</h2></div><CaseBadge status={selectedCase.status} english={isEnglish}/></div><div className="grid sm:grid-cols-2 gap-2 text-sm"><p><strong>{tr('Destination','Tujuan')}:</strong> {selectedCase.target_department} — {selectedCase.target_scope==='NATIONAL'?'Nasional':selectedCase.target_province}</p><p><strong>{tr('Officer','Petugas')}:</strong> {options?.officers?.find(o=>o.id===selectedCase.assignee_id)?.name||'Antrean departemen'}</p><p><strong>{tr('Verified incident province','Provinsi kejadian terverifikasi')}:</strong> {selectedCase.verified_province||'Belum terverifikasi'}</p><p><strong>Status:</strong> {isEnglish?EN_STATUS[selectedCase.status]||selectedCase.status:STATUS[selectedCase.status]||selectedCase.status}</p></div><TagList tags={selectedCase.tags}/><p className="text-sm whitespace-pre-wrap bg-[#f7f9fb] rounded-lg p-3">{selectedCase.source_excerpt}</p><LinkSource href={selectedCase.source_url}/></section>
      {detail?.workflow_trace&&<section className="intel-card p-4 space-y-2" data-casework-acceptance-trace>
       <div className="flex items-center justify-between gap-3">
        <h3 className="text-sm font-bold text-[#263749]">{tr('Officer workflow trace','Jejak alur kerja petugas')}</h3>
        <span className="text-sm font-bold tabular-nums text-[#801b24]">{detail.workflow_trace.completed}/{detail.workflow_trace.total}</span>
       </div>
       <div className="grid gap-1 sm:grid-cols-2">
        {detail.workflow_trace.steps?.map(step=><div key={step.key} className="flex items-start gap-2 text-xs">
         <span aria-hidden="true" className={step.done?'text-[#116846]':'text-[#8b9aaa]'}>{step.done?'✓':'○'}</span>
         <span>{(TRACE_LABELS[step.key]||[step.key,step.key])[isEnglish?0:1]}</span>
        </div>)}
       </div>
       <p className="text-xs text-[#65788b]">{tr(
        'Audit evidence of workflow progress only. Source truth, legal findings and client acceptance remain unverified.',
        'Hanya bukti audit kemajuan alur kerja. Kebenaran sumber, temuan hukum, dan penerimaan klien belum diverifikasi.')}</p>
      </section>}
      {tab==='assignments'&&<>{detail?.can_acknowledge&&<section className="intel-card p-5 space-y-2 border-l-4 border-[#a52a2f]">
         <h3 className="font-bold text-[#801b24]">{tr('Incoming assignment','Penugasan masuk')}</h3>
         <p className="text-sm text-[#53657b]">{tr(
           'This case is ready for the receiving team. Accept it to claim an unassigned item and begin review. No legal determination is made.',
           'Kasus siap ditangani tim penerima. Terima untuk mengambil tugas yang belum ditugaskan dan mulai menelaah. Tidak ada keputusan hukum otomatis.')}</p>
         <button className={primary} disabled={busy} onClick={acknowledge}>
           <CheckCircle2 size={15} className="inline mr-1"/>{tr('Accept & start review','Terima & mulai penelaahan')}
         </button>
       </section>}
       <section className="intel-card p-5 space-y-3" data-casework-source-review>
        <h3 className="font-bold text-[#801b24]">{tr('Original source access review','Pemeriksaan akses sumber asli')}</h3>
        <p className="text-xs text-[#65788b]">{tr(
         'Record whether you opened the original source and checked its context. This does not verify the allegation or establish a legal violation.',
         'Catat apakah sumber asli telah dibuka dan konteksnya diperiksa. Ini tidak memverifikasi tuduhan atau menetapkan pelanggaran hukum.')}</p>
        {detail?.workflow_trace?.latest_source_review_status&&<p className="text-xs text-[#53657b]">
         {tr('Latest recorded outcome: ','Hasil terakhir: ')}<strong>{detail.workflow_trace.latest_source_review_status}</strong>
        </p>}
        {detail?.can_record_source_review?<div className="space-y-3">
         <label className="block space-y-1"><Label>{tr('Review outcome','Hasil pemeriksaan')}</Label>
          <select className={field} value={sourceReviewStatus} onChange={e=>{setSourceReviewStatus(e.target.value);setSourceOpened(false)}}>
           <option value="SOURCE_CHECKED">{tr('Original opened and context reviewed','Sumber asli dibuka dan konteks ditinjau')}</option>
           <option value="NEEDS_INFORMATION">{tr('More information required','Memerlukan informasi tambahan')}</option>
           <option value="SOURCE_UNAVAILABLE">{tr('Original unavailable','Sumber asli tidak dapat diakses')}</option>
          </select>
         </label>
         {sourceReviewStatus==='SOURCE_CHECKED'&&<label className="flex items-start gap-2 text-xs text-[#53657b]">
          <input type="checkbox" checked={sourceOpened} onChange={e=>setSourceOpened(e.target.checked)} disabled={!selectedCase.source_url||busy}/>
          {tr('I opened the original linked source (not just the AI summary).',
              'Saya membuka sumber asli tertaut (bukan hanya ringkasan AI).')}
         </label>}
         <label className="block space-y-1"><Label>{tr('Review note (minimum 20 characters)','Catatan peninjauan (minimum 20 karakter)')}</Label>
          <textarea className={field} rows={3} value={sourceReviewNote} disabled={busy}
           onChange={e=>setSourceReviewNote(e.target.value)}
           placeholder={tr('What did you check and what still needs verification?','Apa yang diperiksa dan apa yang masih perlu diverifikasi?')}/>
         </label>
         <button type="button" className={primary} onClick={recordSourceReview}
          disabled={busy||sourceReviewNote.trim().length<20||
           (sourceReviewStatus==='SOURCE_CHECKED'&&(!sourceOpened||!selectedCase.source_url))}>
          {tr('Record source review','Catat pemeriksaan sumber')}
         </button>
        </div>:<p className="text-xs text-[#64748b]">{tr(
         'Only the receiving officer who has accepted this assignment can record source review.',
         'Hanya petugas penerima yang telah menerima penugasan yang dapat mencatat pemeriksaan sumber.')}</p>}
       </section>
       <section className="intel-card p-5 space-y-4"><h3 className="font-bold text-[#801b24]"><ArrowRightLeft size={16} className="inline mr-2"/>{tr('Transfer to team / department','Alihkan ke tim / departemen')}</h3><div className="grid md:grid-cols-2 gap-3"><label className="space-y-1"><Label>{tr('Department','Departemen')}</Label><select disabled={!detail?.can_edit||busy} className={field} value={department} onChange={e=>setDepartment(e.target.value)}>{options?.departments?.map(d=><option key={d}>{d}</option>)}</select></label><label className="space-y-1"><Label>{tr('Team','Tim')}</Label><select disabled={!detail?.can_edit||busy} className={field} value={scope} onChange={e=>{setScope(e.target.value);setAssignee('');setProvince(e.target.value==='PROVINCE'?(selectedCase.verified_province||''):'' )}}><option value="NATIONAL">Nasional</option><option value="PROVINCE" disabled={!selectedCase.verified_province}>Provinsi (lokasi terkonfirmasi)</option></select></label>{scope==='PROVINCE'&&<label className="space-y-1"><Label>{tr('Province','Provinsi')}</Label><input className={field} value={province} readOnly/></label>}<label className="space-y-1"><Label>{tr('Receiving officer','Petugas penerima')}</Label><select disabled={!detail?.can_edit||busy} className={field} value={assignee} onChange={e=>setAssignee(e.target.value)}><option value="">{tr('Department queue','Antrean departemen')}</option>{eligible.map(o=><option value={o.id} key={o.id}>{o.name}</option>)}</select></label></div><textarea className={field} rows={2} value={routeNote} disabled={!detail?.can_edit} onChange={e=>setRouteNote(e.target.value)} placeholder="Alasan pengalihan (minimal 8 karakter)"/><button className={primary} disabled={!detail?.can_edit||busy||routeNote.trim().length<8} onClick={route}>{tr('Send assignment','Kirim penugasan')}</button></section><section className="intel-card p-5 space-y-3"><h3 className="font-bold text-[#801b24]">{tr('Update status','Perbarui status')}</h3><div className="flex flex-wrap gap-2"><select className={field+' max-w-xs'} value={newStatus} onChange={e=>setNewStatus(e.target.value)} disabled={!detail?.can_edit}>{Object.entries(STATUS).filter(([code])=>code!=='CLOSED'||detail?.can_approve).map(([code,label])=><option key={code} value={code}>{label}</option>)}</select><button className={primary} disabled={!detail?.can_edit||busy||stateNote.trim().length<8} onClick={status}>{tr('Save status','Simpan status')}</button></div><textarea className={field} value={stateNote} onChange={e=>setStateNote(e.target.value)} rows={2} placeholder="Catatan perubahan (minimal 8 karakter)" disabled={!detail?.can_edit}/></section><section className="intel-card p-5"><h3 className="font-bold text-[#801b24]">{tr('Activity history','Riwayat dan audit')}</h3><div className="mt-3 space-y-2">{detail?.events?.map(event=><div className="border-l-2 border-[#d1b1b5] pl-3 py-1" key={event.id}><p className="text-sm font-semibold">{event.action.replaceAll('_',' ')}</p><p className="text-xs text-[#64748b]"><DateText value={event.at}/> · Petugas #{event.actor_id}</p><p className="text-xs mt-1 text-[#64748b]">{event.details?.note||''}</p></div>)}</div></section></>}
      {tab==='reports'&&<><section className="intel-card p-5"><div className="flex justify-between gap-2 mb-4 flex-wrap"><h3 className="font-bold text-[#801b24]">{tr('Reports and approval','Laporan dan persetujuan')}</h3><div className="flex flex-wrap gap-2">{detail?.can_edit&&<><button className={small} onClick={()=>beginReport(null)}>{tr('New draft','Draf baru')}</button><button className={small} onClick={aiDraft} disabled={busy}>{tr('Draft with AI','Buat draf analisis dengan AI')}</button></>}</div></div>{detail?.reports?.map(r=><div key={r.id} className="border border-[#e5eaf0] rounded-lg p-4 mb-3"><div className="flex justify-between gap-2"><div><p className="font-semibold">{r.title}</p><p className="text-xs text-[#64748b] mt-1">Laporan #{r.id} · <DateText value={r.updated_at}/></p></div><CaseBadge status={r.status} english={isEnglish}/></div><p className="text-xs whitespace-pre-wrap mt-2 line-clamp-4">{r.executive_summary||r.findings||'Belum ada isi.'}</p><div className="flex flex-wrap gap-2 mt-3"><button className={small} onClick={()=>{setEditReport(r.id);setForm({title:r.title,executive_summary:r.executive_summary,findings:r.findings,verification_notes:r.verification_notes,recommendations:r.recommendations})}}>{tr('View report','Baca laporan')}</button>{detail?.can_edit&&r.is_latest_version&&['DRAFT','RETURNED'].includes(r.status)&&<button className={small} onClick={()=>reportTransition(r,'SUBMITTED')} disabled={busy}>{tr('Submit for approval','Ajukan persetujuan')}</button>}{detail?.can_approve&&r.is_latest_version&&r.status==='SUBMITTED'&&r.created_by!==options?.current_user_id&&<><button className={small} disabled={busy} onClick={()=>reportTransition(r,'APPROVED')}>{tr('Approve','Setujui')}</button><button className={small} disabled={busy} onClick={()=>reportTransition(r,'RETURNED')}>{tr('Return','Kembalikan')}</button></>}</div>{!r.is_latest_version&&<p className="mt-2 text-xs font-semibold text-[#8c4350]">{tr('Superseded report version · audit history only','Versi laporan lama · hanya riwayat audit')}</p>}{r.review_comment&&<p className="mt-2 text-xs text-[#8c4350]">Umpan balik: {r.review_comment}</p>}</div>)}{!detail?.reports?.length&&<p className="text-sm text-[#64748b]">Belum ada laporan. Gunakan draf manual atau draf AI yang harus diperiksa petugas.</p>}</section>
       {(form.title||editReport)&&<section className="intel-card p-5 space-y-3"><h3 className="font-bold text-[#801b24]">{tr('Report editor','Editor laporan')}</h3>{[['title','Judul',1],['executive_summary','Ringkasan eksekutif',4],['findings','Temuan dan bukti',5],['verification_notes','Pemeriksaan dan keterbatasan bukti',4],['recommendations','Rekomendasi tindak lanjut',4]].map(([key,label,rows])=><label className="block space-y-1" key={key}><Label>{label}</Label>{rows===1?<input className={field} value={form[key]} onChange={e=>setForm(old=>({...old,[key]:e.target.value}))}/>:<textarea className={field} rows={rows} value={form[key]} onChange={e=>setForm(old=>({...old,[key]:e.target.value}))}/>}</label>)}<div className="flex gap-2 flex-wrap"><button className={primary} disabled={!detail?.can_edit||busy||!form.title||(!!editReport&&(!['DRAFT','RETURNED'].includes(activeReport?.status)||!activeReport?.is_latest_version))} onClick={saveReport}>{tr('Save draft','Simpan draf')}</button>{editReport&&<button className={small} onClick={()=>{const r=detail?.reports?.find(x=>x.id===editReport);if(r){document.title=r.title;window.print()}}}><Printer size={14} className="inline mr-1"/> Cetak laporan</button>}</div></section>}</>}
     </>}
   </div>
  </div>}
  <PrintedReport report={detail?.reports?.find(x=>x.id===editReport)} caseItem={selectedCase}/>
 </div>;
}
