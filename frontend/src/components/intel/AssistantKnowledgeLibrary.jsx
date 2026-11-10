import {useEffect,useState} from 'react';
import {BookOpen,Upload,FileText,Download,Trash2,ShieldCheck} from 'lucide-react';
import {useLanguage} from '@/lib/LanguageContext';
const BASE='/api/assistant-knowledge';
function token(){return window.localStorage.getItem('bawaslu_access_token')||''}
async function request(path,method='GET',payload){
 const response=await fetch(BASE+path,{method,cache:'no-store',headers:{
  Authorization:'Bearer '+token(),...(payload instanceof FormData?{}:{'Content-Type':'application/json'})
 },...(payload?{body:payload instanceof FormData?payload:JSON.stringify(payload)}:{})});
 const json=await response.json().catch(()=>({}));
 if(!response.ok)throw Error(typeof json.detail==='string'?json.detail:'Knowledge request failed');
 return json;
}
export default function AssistantKnowledgeLibrary(){
 const {language}=useLanguage();
 const id=language==='id';
 const [docs,setDocs]=useState([]);
 const [expanded,setExpanded]=useState(false);
 const [status,setStatus]=useState(null);
 const [busy,setBusy]=useState(false);
 const [error,setError]=useState('');
 const [notice,setNotice]=useState('');
 const [file,setFile]=useState(null);
 const [title,setTitle]=useState('');
 const [scope,setScope]=useState('NATIONAL');
 const [province,setProvince]=useState('');
 async function refresh(){
  const data=await request('/documents');
  setDocs(data.documents||[]);
  setStatus(data);
  setScope(data.default_scope||'NATIONAL');
  setProvince(data.default_province||'');
 }
 useEffect(()=>{let active=true;request('/documents').then(data=>{
  if(!active)return;
  setDocs(data.documents||[]);setStatus(data);setScope(data.default_scope||'NATIONAL');setProvince(data.default_province||'');
 }).catch(()=>{});return()=>{active=false}},[]);
 async function upload(){
  if(!file||busy)return;
  if(file.size>5*1024*1024){setError(id?'PDF maksimal 5 MB.':'PDF maximum is 5 MB.');return}
  setBusy(true);setError('');setNotice('');
  try{
   const form=new FormData();
   form.append('file',file);form.append('title',title.trim()||file.name.replace(/\.pdf$/i,''));
   form.append('scope',scope);form.append('province',scope==='PROVINCE'?province:'');
   const result=await request('/upload','POST',form);
   await refresh();
   setFile(null);setTitle('');
   setNotice(result.duplicate?(id?'PDF yang sama sudah tersimpan.':'That PDF is already stored.'):
     id?'PDF berhasil diproses menjadi referensi AI dengan rujukan halaman.':'PDF indexed as page-cited AI reference.');
  }catch(e){setError(e.message)}finally{setBusy(false)}
 }
 async function download(doc){
  setBusy(true);setError('');
  try{
   const response=await fetch(BASE+'/'+doc.id+'/download',{headers:{Authorization:'Bearer '+token()},cache:'no-store'});
   if(!response.ok)throw Error(id?'Tidak dapat membuka PDF':'Could not open PDF');
   const blob=await response.blob();
   const url=URL.createObjectURL(blob);
   const link=document.createElement('a');
   link.href=url;link.download=doc.filename||'bawaslu-reference.pdf';
   link.click();setTimeout(()=>URL.revokeObjectURL(url),10000);
  }catch(e){setError(e.message)}finally{setBusy(false)}
 }
 async function remove(doc){
  if(!window.confirm(id?'Nonaktifkan PDF ini dari referensi AI?':'Remove this PDF from the AI reference library?'))return;
  setBusy(true);setError('');
  try{await request('/'+doc.id,'DELETE');await refresh();}
  catch(e){setError(e.message)}finally{setBusy(false)}
 }
 return <section className="rounded-xl border border-[#dce5ec] bg-white" aria-label="Assistant PDF knowledge library">
  <button type="button" className="flex w-full items-center justify-between gap-3 px-4 py-3 text-left hover:bg-[#f8fafc]" aria-expanded={expanded} onClick={()=>setExpanded(x=>!x)}>
   <span className="flex items-center gap-3"><BookOpen size={19} className="text-[#801b24]"/><span><strong className="text-sm text-[#243447]">{id?'Pustaka Referensi AI (PDF)':'AI Reference Library (PDF)'}</strong><span className="block text-xs text-[#64748b]">{id?'Unggah regulasi, SOP dan laporan untuk jawaban bersumber dengan rujukan halaman':'Upload regulations, SOPs and reports for answers grounded in cited pages'}</span></span></span>
   <span className="text-xs text-[#801b24] font-semibold">{docs.length} PDF · {expanded?'−':'+'}</span>
  </button>
  {expanded&&<div className="border-t p-4 space-y-4">
   <p className="text-xs text-[#64748b]"><ShieldCheck size={13} className="inline mr-1"/>{id?'Dokumen hanya dapat dibaca dalam cakupan hak akses Anda. PDF menjadi bahan rujukan terindeks, bukan pelatihan ulang model. Teks pindaian perlu OCR terlebih dahulu.':'Documents remain permission-scoped. PDFs become indexed references—not model fine-tuning. Scanned images need OCR first.'}</p>
   {status?.can_upload&&<div className="grid gap-3 md:grid-cols-2">
    <label className="text-xs">{id?'Pilih PDF (maks. 5 MB)':'Choose PDF (max 5 MB)'}<input type="file" accept="application/pdf,.pdf" className="mt-1 block w-full text-xs" onChange={e=>setFile(e.target.files?.[0]||null)}/></label>
    <label className="text-xs">{id?'Judul dokumen':'Document title'}<input className="intel-input mt-1 w-full" value={title} onChange={e=>setTitle(e.target.value)} placeholder={file?.name.replace(/\.pdf$/i,'')||''}/></label>
    <label className="text-xs">{id?'Cakupan dokumen':'Document scope'}<select className="intel-input mt-1 w-full" value={scope} onChange={e=>setScope(e.target.value)}>
     {status.default_scope==='NATIONAL'&&<option value="NATIONAL">{id?'Nasional':'National'}</option>}
     <option value="PROVINCE">{id?'Provinsi':'Province'}</option>
    </select></label>
    {scope==='PROVINCE'&&<label className="text-xs">{id?'Provinsi':'Province'}<input className="intel-input mt-1 w-full" value={province} onChange={e=>setProvince(e.target.value)} readOnly={status.default_scope==='PROVINCE'}/></label>}
    <div className="md:col-span-2"><button type="button" className="intel-button" disabled={busy||!file||scope==='PROVINCE'&&!province.trim()} onClick={upload}><Upload size={15} className="inline mr-2"/>{busy?'…':id?'Unggah & Indeks PDF':'Upload & Index PDF'}</button></div>
   </div>}
   {error&&<p role="alert" className="text-xs text-red-700">{error}</p>}
   {notice&&<p role="status" className="text-xs text-green-700">{notice}</p>}
   <div className="space-y-2">{docs.map(doc=><div key={doc.id} className="flex flex-wrap items-center justify-between gap-2 rounded-lg border border-[#e3e9ef] p-3"><div className="flex gap-2 items-start"><FileText size={16} className="text-[#801b24] mt-1"/><div><p className="text-sm font-semibold">{doc.title}</p><p className="text-xs text-[#64748b]">{doc.pages} {id?'halaman':'pages'} · {doc.scope==='NATIONAL'?(id?'Nasional':'National'):doc.province} · {doc.extracted_chars.toLocaleString()} {id?'karakter':'characters'}</p></div></div><div className="flex gap-2"><button type="button" className="intel-ghost text-xs" onClick={()=>download(doc)} disabled={busy}><Download size={13} className="inline mr-1"/>{id?'Unduh':'Download'}</button>{status?.can_upload&&<button type="button" className="intel-ghost text-xs text-red-700" disabled={busy} onClick={()=>remove(doc)}><Trash2 size={13}/></button>}</div></div>)}
   {!docs.length&&<p className="text-sm text-[#64748b]">{id?'Belum ada PDF. Unggah dokumen resmi yang relevan agar AI dapat mengutipnya.':'No PDFs uploaded yet. Add a relevant authorized document for the assistant to cite.'}</p>}</div>
  </div>}
 </section>;
}
