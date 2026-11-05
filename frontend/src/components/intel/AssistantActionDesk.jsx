import {useEffect,useMemo,useState} from 'react';
import {useNavigate} from 'react-router-dom';
import {ArrowUpRight,ClipboardList,FileCheck2,Layers3,CheckCircle2,ShieldCheck,ChevronDown,Loader2} from 'lucide-react';

const ENDPOINT='/api/casework';
const CONTROL='rounded-lg border border-[#dce4eb] bg-white px-3 py-2 text-sm w-full focus:outline-none focus:ring-2 focus:ring-[#a52a2f]';
const PRIMARY='rounded-lg bg-[#801b24] px-4 py-2.5 text-sm font-semibold text-white hover:bg-[#a52a2f] disabled:opacity-50';
const safeUrl=value=>{try{const u=new URL(value);return ['https:','http:'].includes(u.protocol)?u.href:null}catch{return null}};
const isDemo=()=>window.__BAWASLU_DEMO_REPLICA__||/^\/demo(?:\/|$)/.test(window.location.pathname);
const short=(text,max=220)=>String(text||'').trim().slice(0,max);
async function api(path,method='GET',body){
 const token=window.localStorage.getItem('bawaslu_access_token')||'';
 if(!token)throw Error('Sesi masuk diperlukan untuk membuat penugasan.');
 const response=await fetch(ENDPOINT+path,{
  method,cache:'no-store',
  headers:{Authorization:'Bearer '+token,...(body?{'Content-Type':'application/json'}:{})},
  ...(body?{body:JSON.stringify(body)}:{})
 });
 const data=await response.json().catch(()=>({}));
 if(!response.ok)throw Error(typeof data.detail==='string'?data.detail:'Proses penugasan tidak berhasil');
 return data;
}
const toSource=record=>{
 if(!record||typeof record!=='object')return null;
 if(record.record_type==='SOCIAL_LISTENING'&&/^\d+$/.test(String(record.source_post_id||''))&&/^\d+$/.test(String(record.campaign_id||''))){
  return {key:'SOCIAL-'+record.source_post_id,source_type:'SOCIAL',source_id:String(record.source_post_id),
    campaign_id:Number(record.campaign_id),title:short(record.source_excerpt||record.title,135),
    url:record.source_url||'',platform:record.platform||'',published:record.publication_date||''};
 }
 if(record.record_type==='FORMAL_INTELLIGENCE'&&record.intelligence_id){
  return {key:String(record.intelligence_id),source_type:'INTELLIGENCE',
    source_id:String(record.intelligence_id),campaign_id:null,
    title:short(record.title,135),url:record.source_url||'',platform:'Catatan intelijen'};
 }
 return null;
};
function compactQuestion(question){
 let result=String(question||'').replace(/^\s*(tolong\s+)?(dibuatkan|buatkan|berikan|analisis|jelaskan)\s*/i,'').trim();
 if(!result)result='isu yang teridentifikasi';
 return short(result,130);
}
function UserWorkspacePulse(){
 const [pulse,setPulse]=useState(null);
 const navigate=useNavigate();
 useEffect(()=>{
  if(isDemo())return;
  let active=true;
  api('/assistant-workspace').then(res=>{if(active)setPulse(res)}).catch(()=>{});
  return()=>{active=false};
 },[]);
 if(!pulse)return null;
 return <div className="grid gap-2 sm:grid-cols-3" aria-label="Penugasan dalam kewenangan Anda" data-i18n-exempt>
  {[
   {label:'Ditugaskan kepada saya',value:pulse.my_assignments,icon:ClipboardList},
   {label:'Kasus yang bisa ditindaklanjuti',value:pulse.visible_open_cases,icon:Layers3},
   {label:'Laporan perlu keputusan',value:pulse.reports_for_my_review,icon:FileCheck2}
  ].map(({label,value,icon:Icon})=><button key={label} type="button" onClick={()=>navigate('/casework')} className="flex items-center gap-2 rounded-xl border border-[#ead4d4] bg-white px-3 py-3 text-left hover:bg-[#fbf2f3]">
    <Icon size={18} className="shrink-0 text-[#982d37]"/>
    <span className="flex-1 min-w-0 text-xs text-[#586a7b]">{label}</span>
    <span className="font-bold text-[#801b24] tabular-nums">{value}</span>
  </button>)}
 </div>;
}
export {UserWorkspacePulse};

export default function AssistantActionDesk({message,question}){
 const navigate=useNavigate();
 const [chosen,setChosen]=useState(null);
 const [preview,setPreview]=useState(null);
 const [options,setOptions]=useState(null);
 const [busy,setBusy]=useState(false);
 const [error,setError]=useState('');
 const [confirmed,setConfirmed]=useState(false);
 const [department,setDepartment]=useState('Data & Analisis');
 const [scope,setScope]=useState('NATIONAL');
 const [assignee,setAssignee]=useState('');
 const [title,setTitle]=useState('');
 const [editedSummary,setEditedSummary]=useState('');
 const [showDetails,setShowDetails]=useState(false);
 const checks=(message?.analytical_findings?.review_steps||[]).filter(x=>typeof x==='string'&&x.trim()).slice(0,3);
 const observations=(message?.analytical_findings?.observations||[]).filter(x=>typeof x==='string'&&x.trim()).slice(0,5);
 const sources=useMemo(()=>{
  const seen=new Set();
  return (message?.records||[]).map(toSource).filter(source=>{
   if(!source||seen.has(source.key))return false;
   seen.add(source.key);return true;
  }).slice(0,5);
 },[message?.records]);
 if(isDemo()||!(message?.records?.length||checks.length))return null;
 async function openSource(source){
  setBusy(true);setError('');setChosen(source);setPreview(null);setConfirmed(false);setAssignee('');
  try{
   const query=new URLSearchParams({source_type:source.source_type,source_id:source.source_id});
   if(source.campaign_id)query.set('campaign_id',String(source.campaign_id));
   const [p,o]=await Promise.all([api('/preview?'+query.toString()),api('/options')]);
   setPreview(p);setOptions(o);setDepartment(o.departments.includes(p.recommended_department)?p.recommended_department:'Data & Analisis');
   setScope('NATIONAL');
   setTitle('Telaah: '+compactQuestion(question));
   setEditedSummary(short((message.text||'').split('\n\n')[0],2800));
  }catch(e){setError(e.message)}
  finally{setBusy(false)}
 }
 const officers=(options?.officers||[]).filter(o=>o.scope===scope&&(scope==='NATIONAL'||o.province===preview?.verified_province));
 async function confirmHandoff(){
  if(!confirmed||!preview||!chosen||busy)return;
  setBusy(true);setError('');
  try{
   const req={
    source_type:chosen.source_type,source_id:chosen.source_id,
    campaign_id:chosen.campaign_id,department,target_scope:scope,
    target_province:scope==='PROVINCE'?(preview.verified_province||''):'',
    assignee_id:assignee?Number(assignee):null,
    title:short(title,240),executive_summary:short(editedSummary,3500),
    findings:short(observations.length?observations.map((x,i)=>String(i+1)+'. '+x).join('\n\n'):message.text,8700),
    review_steps:checks,question:short(question,500),confirm:true
   };
   const result=await api('/assistant-handoff','POST',req);
   navigate('/casework?case_id='+result.case.id+'&tab=reports');
  }catch(e){setError(e.message)}
  finally{setBusy(false)}
 }
 return <section className="mb-5 overflow-hidden rounded-xl border border-[#d9b9bd] bg-white" aria-label="Asisten tindakan lanjutan" data-i18n-exempt>
  <div className="bg-[#fcf1f2] p-4">
   <div className="flex items-start gap-3"><span className="rounded-lg bg-[#f1dfe1] p-2"><ShieldCheck className="text-[#801b24]" size={20}/></span><div className="min-w-0 flex-1">
    <h3 className="font-bold text-[#801b24] text-base">Saya bisa menyiapkan tindak lanjutnya</h3>
    <p className="text-sm text-[#4d6071] mt-1">Pilih sumber penting di bawah. Saya isi penugasan, sarankan unit penerima, dan susun draf laporan dari analisis ini. Anda cukup periksa dan konfirmasi.</p>
   </div></div>
  </div>
  {!!checks.length&&<div className="px-4 pt-4"><div className="text-xs font-bold uppercase tracking-wide text-[#64748b] mb-2">Langkah kerja yang sudah disiapkan</div><div className="grid gap-2 md:grid-cols-3">{checks.map((item,i)=><div key={i} className="border border-[#e4e9ef] rounded-lg p-3 text-xs leading-relaxed"><span className="font-bold text-[#801b24]">Langkah {i+1} · </span>{short(item.replace(/\[(?:SOCIAL|INT)-[A-Za-z0-9:_-]+\]/g,''),210)}{item.length>210?'…':''}</div>)}</div></div>}
  <div className="px-4 py-4 space-y-2">
   <div className="text-xs font-bold uppercase tracking-wide text-[#64748b]">Bukti yang bisa langsung dijadikan penugasan</div>
   {sources.length?<div className="grid gap-2 md:grid-cols-2">{sources.slice(0,4).map(s=><div key={s.key} className={'flex flex-col justify-between gap-2 rounded-lg border p-3 '+(chosen?.key===s.key?'border-[#a52a2f] bg-[#fff9f9]':'border-[#e4e9ef]')}>
    <div><p className="text-[11px] font-semibold text-[#801b24]">{s.key} · {s.platform}</p><p className="text-sm mt-1 line-clamp-2">{s.title}</p>{s.published&&<p className="text-[11px] text-[#6b7e90] mt-1">{s.published.slice(0,10)}</p>}</div>
    <div className="flex flex-wrap items-center gap-3"><button className="text-xs font-bold text-[#801b24] hover:underline" onClick={()=>openSource(s)} type="button" disabled={busy}>Siapkan tugas & laporan</button>{safeUrl(s.url)&&<a className="inline-flex items-center gap-1 text-xs text-[#167087] hover:underline" href={safeUrl(s.url)} target="_blank" rel="noopener noreferrer">Periksa sumber <ArrowUpRight size={12}/></a>}</div>
   </div>)}</div>:<p className="text-sm text-[#64748b]">Sumber yang bisa langsung ditugaskan belum tersedia. Buka sumber asli atau penelusuran Inbox untuk mengidentifikasi rekaman yang relevan.</p>}
  </div>
  {error&&<p role="alert" className="mx-4 mb-4 rounded-lg border border-red-200 bg-red-50 p-3 text-sm text-red-800">{error}</p>}
  {chosen&&<div className="border-t border-[#e5eaef] bg-[#f9fafc] p-4 space-y-4">
   <div className="flex justify-between gap-3 items-start"><div><h4 className="font-bold text-[#243447]">Penugasan siap ditinjau</h4><p className="text-xs text-[#64748b]">Tidak ada tindakan yang disimpan sebelum Anda mengonfirmasi.</p></div><button type="button" onClick={()=>{setChosen(null);setPreview(null);setError('')}} className="text-xs text-[#64748b] hover:underline">Tutup</button></div>
   {busy&&!preview&&<p className="text-sm text-[#64748b] flex items-center gap-2"><Loader2 size={15} className="animate-spin"/> Memeriksa akses dan sumber…</p>}
   {preview&&<><div className="flex flex-wrap gap-2 text-xs">{(preview.tags||[]).slice(0,6).map((tag,i)=><span key={i} className="rounded-full border border-[#e7d7d9] bg-white px-2.5 py-1">{tag.label}{tag.verified?' ✓':''}</span>)}</div>
    <p className="text-xs text-[#64748b]">Saran departemen berdasarkan tag: <strong>{preview.recommended_department}</strong>. Lokasi yang hanya disebut dalam unggahan bukan yurisdiksi terverifikasi.</p>
    <div className="grid md:grid-cols-2 gap-3">
     <label className="space-y-1 block md:col-span-2"><span className="text-xs font-semibold">Judul kasus</span><input className={CONTROL} maxLength={240} value={title} onChange={e=>setTitle(e.target.value)}/></label>
     <label className="space-y-1 block"><span className="text-xs font-semibold">Departemen</span><select className={CONTROL} value={department} onChange={e=>setDepartment(e.target.value)}>{options?.departments?.map(x=><option key={x} value={x}>{x}</option>)}</select></label>
     <label className="space-y-1 block"><span className="text-xs font-semibold">Tim tujuan</span><select className={CONTROL} value={scope} onChange={e=>{setScope(e.target.value);setAssignee('')}}><option value="NATIONAL">Nasional</option>{preview.verified_province&&<option value="PROVINCE">Provinsi · {preview.verified_province}</option>}</select></label>
     <label className="space-y-1 block"><span className="text-xs font-semibold">Petugas penerima (opsional)</span><select className={CONTROL} value={assignee} onChange={e=>setAssignee(e.target.value)}><option value="">Antrean departemen</option>{officers.map(o=><option key={o.id} value={o.id}>{o.name}</option>)}</select></label>
     <label className="space-y-1 block"><span className="text-xs font-semibold">Sumber utama</span><div className={CONTROL+' bg-[#f2f4f7]'}>{chosen.key}{chosen.campaign_id?' · Kampanye '+chosen.campaign_id:''}</div></label>
    </div>
    <button className="inline-flex gap-2 items-center text-xs font-semibold text-[#801b24]" type="button" onClick={()=>setShowDetails(x=>!x)}><ChevronDown size={13}/> {showDetails?'Tutup pratinjau draf':'Tinjau ringkasan laporan yang akan dibuat'}</button>
    {showDetails&&<label className="block space-y-1"><span className="text-xs font-semibold">Ringkasan eksekutif (dapat disunting)</span><textarea className={CONTROL} rows={4} value={editedSummary} onChange={e=>setEditedSummary(e.target.value)} maxLength={3500}/><p className="text-xs text-[#64748b]">Temuan dan daftar verifikasi dari jawaban juga akan disalin sebagai draf, bukan hasil validasi hukum.</p></label>}
    <label className="flex gap-2 items-start text-xs text-[#46586a]"><input type="checkbox" className="mt-1" checked={confirmed} onChange={e=>setConfirmed(e.target.checked)}/><span>Saya memahami sumber dan analisis masih perlu diperiksa. Simpan sebagai <strong>penugasan dan draf laporan</strong>, bukan kesimpulan pelanggaran.</span></label>
    <button type="button" className={PRIMARY} disabled={busy||!confirmed||!options?.can_create||!title.trim()} onClick={confirmHandoff}><CheckCircle2 size={16} className="inline mr-2"/>{busy?'Memproses…':'Buat penugasan + draf laporan'}</button>
    {!options?.can_create&&<p className="text-xs text-amber-800">Peran Anda hanya dapat meninjau hasil. Penugasan baru memerlukan izin petugas.</p>}
    <p className="text-[11px] text-[#64748b]">Pengisian ulang menggunakan jawaban yang sudah tersedia, tanpa panggilan AI tambahan. Persetujuan dan perubahan status dilakukan oleh petugas berwenang.</p>
   </>}
  </div>}
 </section>;
}
