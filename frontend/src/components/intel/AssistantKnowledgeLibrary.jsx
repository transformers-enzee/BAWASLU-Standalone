import {useEffect,useState} from 'react';
import {BookOpen,Upload,FileText,Download,Trash2,ShieldCheck,CheckCircle,Brain} from 'lucide-react';
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
 const [documentType,setDocumentType]=useState('REGULATION');
 const [issuer,setIssuer]=useState('');
 const [semanticIndex,setSemanticIndex]=useState(false);
 const [reviewing,setReviewing]=useState(null);
 const [reviewNotes,setReviewNotes]=useState('');
 const [searchQuestion,setSearchQuestion]=useState('');
 const [searchSemantic,setSearchSemantic]=useState(false);
 const [searchResults,setSearchResults]=useState(null);
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
   form.append('document_type',documentType);form.append('issuer',issuer);
   form.append('semantic_index',String(semanticIndex));
   const result=await request('/upload','POST',form);
   await refresh();
   setFile(null);setTitle('');setIssuer('');setSemanticIndex(false);
   const statusText=result.document?.embedding_status||'NOT_INDEXED';
   setNotice(result.duplicate?(id?'PDF yang sama sudah tersimpan.':'That PDF is already stored.'):
     (id?'PDF diunggah dan halaman tersimpan.':'PDF uploaded with page references.')+
     (semanticIndex?' '+(result.semantic_indexed?(id?'Pencarian semantik aktif.':'Semantic search is ready.'):
       (id?'Indeks semantik belum tersedia ('+statusText+'); pencarian kata tetap tersedia.':
          'Semantic indexing unavailable ('+statusText+'); keyword search remains available.')):''));
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
 async function previewSearch(){
  if(!searchQuestion.trim()||busy)return;
  setBusy(true);setError('');
  try{
   const q=new URLSearchParams({question:searchQuestion.trim(),semantic:String(searchSemantic)});
   const result=await request('/search-preview?'+q.toString());
   setSearchResults(result.matches||[]);
  }catch(e){setError(e.message)}finally{setBusy(false)}
 }
 async function indexDocument(doc){
  if(!window.confirm(id?
   'Indeks semantik akan mengirim teks PDF ke layanan embedding AI dan dapat menggunakan kredit. Lanjutkan?':
   'Semantic indexing sends PDF text to the AI embeddings provider and may incur usage charges. Continue?'))return;
  setBusy(true);setError('');setNotice('');
  try{
   const result=await request('/'+doc.id+'/semantic-index','POST',{});
   await refresh();
   setNotice(result.indexed?(id?'Pencarian semantik aktif.':'Semantic search enabled.'):
    (id?'Indeks tidak tersedia; pencarian kata kunci tetap aktif.':'Index unavailable; keyword search remains active.'));
  }catch(e){setError(e.message)}finally{setBusy(false)}
 }
 async function reviewDocument(doc,approved){
  setBusy(true);setError('');setNotice('');
  try{
   const result=await request('/'+doc.id+'/review','POST',{
    document_type:doc.document_type||'OTHER',
    issuer:doc.issuer||'',
    notes:reviewNotes,reviewed:approved});
   await refresh();
   setReviewing(null);setReviewNotes('');
   setNotice(id?'Status telaah dokumen tersimpan.':'Document review status saved.');
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
    <label className="text-xs">{id?'Jenis dokumen':'Document type'}
      <select className="intel-input mt-1 w-full" value={documentType} onChange={e=>setDocumentType(e.target.value)}>
       <option value="REGULATION">{id?'Peraturan / regulasi':'Regulation'}</option>
       <option value="SOP">SOP</option><option value="REPORT">{id?'Laporan':'Report'}</option>
       <option value="GUIDANCE">{id?'Panduan':'Guidance'}</option>
       <option value="OTHER">{id?'Lainnya':'Other'}</option>
      </select>
    </label>
    <label className="text-xs">{id?'Penerbit / instansi (opsional)':'Issuing authority (optional)'}
      <input className="intel-input mt-1 w-full" maxLength={220} value={issuer} onChange={e=>setIssuer(e.target.value)}/>
    </label>
    <label className="md:col-span-2 flex gap-2 items-start text-xs text-[#425466]">
      <input type="checkbox" checked={semanticIndex} onChange={e=>setSemanticIndex(e.target.checked)} className="mt-0.5"/>
      <span>{id?
       'Aktifkan pencarian semantik (opsional): kutipan teks PDF dikirim ke penyedia embedding OpenAI dan dapat menggunakan kredit AI. Dokumen yang sensitif sebaiknya tidak diindeks tanpa persetujuan.':
       'Enable semantic search (optional): PDF excerpts are sent to OpenAI for embeddings and may incur usage charges. Obtain approval before indexing sensitive documents.'}</span>
    </label>
    <div className="md:col-span-2"><button type="button" className="intel-button" disabled={busy||!file||scope==='PROVINCE'&&!province.trim()} onClick={upload}><Upload size={15} className="inline mr-2"/>{busy?'…':id?'Unggah & Indeks PDF':'Upload & Index PDF'}</button></div>
   </div>}
   {error&&<p role="alert" className="text-xs text-red-700">{error}</p>}
   {notice&&<p role="status" className="text-xs text-green-700">{notice}</p>}
   {docs.length>0&&<div className="space-y-2 rounded-lg border border-[#e3e9ef] bg-[#f8fafc] p-3">
      <p className="font-semibold text-sm text-[#801b24]">{id?'Uji pencarian dokumen':'Test knowledge retrieval'}</p>
      <p className="text-xs text-[#64748b]">{id?
       'Periksa halaman yang ditemukan sebelum bertanya kepada AI. Uji ini tidak membuat jawaban AI.':
       'Inspect which document pages are found before asking the assistant. This test does not generate an AI answer.'}</p>
      <div className="flex flex-wrap gap-2">
       <input className="intel-input flex-1 min-w-[220px]" maxLength={500} value={searchQuestion}
          onChange={e=>setSearchQuestion(e.target.value)}
          placeholder={id?'Contoh: prosedur penanganan pelanggaran pemilu':'Example: how is an election violation investigated?'}/>
       <button type="button" className="intel-button text-xs" disabled={busy||!searchQuestion.trim()} onClick={previewSearch}>{id?'Cari referensi':'Search references'}</button>
      </div>
      <label className="flex gap-2 text-xs items-start text-[#526577]">
       <input type="checkbox" className="mt-0.5" checked={searchSemantic} onChange={e=>setSearchSemantic(e.target.checked)}/>
       <span>{id?
         'Gunakan pencarian semantik (memerlukan embedding query, dapat memakai kredit AI jika ada dokumen berindeks).':
         'Include semantic search (query embeddings may incur AI usage when indexed documents exist).'}</span>
      </label>
      {searchResults&&<div className="space-y-2">
       {!searchResults.length&&<p className="text-xs text-[#64748b]">{id?'Tidak ditemukan halaman yang cocok.':'No matching pages found.'}</p>}
       {searchResults.map(result=><div key={result.record_id} className="rounded-md border border-[#e1e7ec] bg-white p-2">
        <p className="text-xs font-semibold">{result.title} · {id?'halaman':'page'} {result.page} · {result.match_method}</p>
        <p className="text-xs text-[#5d6c7c] mt-1">{result.source_excerpt}</p>
       </div>)}
      </div>}
   </div>}
   <div className="space-y-2">{docs.map(doc=><div key={doc.id} className="flex flex-wrap items-center justify-between gap-2 rounded-lg border border-[#e3e9ef] p-3"><div className="flex gap-2 items-start"><FileText size={16} className="text-[#801b24] mt-1"/><div><p className="text-sm font-semibold">{doc.title}</p><p className="text-xs text-[#64748b]">{doc.pages} {id?'halaman':'pages'} · {doc.scope==='NATIONAL'?(id?'Nasional':'National'):doc.province} · {doc.extracted_chars.toLocaleString()} {id?'karakter':'characters'}</p>
       <p className="text-xs mt-1 text-[#53657b]">{doc.document_type||'OTHER'} · {doc.issuer|| (id?'Penerbit belum diisi':'Issuer unspecified')} · {doc.review_status==='OFFICER_REVIEWED'?(id?'Ditelaah petugas':'Officer reviewed'):(id?'Belum ditelaah':'Not reviewed')} · {doc.embedding_status==='READY'?(id?'Semantik siap':'Semantic ready'):(id?'Kata kunci saja':'Keyword search only')}</p>
      </div></div><div className="flex gap-2 flex-wrap items-center"><button type="button" className="intel-ghost text-xs" onClick={()=>download(doc)} disabled={busy}><Download size={13} className="inline mr-1"/>{id?'Unduh':'Download'}</button>{status?.can_upload&&doc.embedding_status!=='READY'&&<button type="button" disabled={busy} className="intel-ghost text-xs" onClick={()=>indexDocument(doc)}><Brain size={13} className="inline mr-1"/>{id?'Indeks semantik':'Semantic index'}</button>}
     {status?.can_review&&<button type="button" disabled={busy} className="intel-ghost text-xs" onClick={()=>{setReviewing(doc.id);setReviewNotes(doc.review_notes||'')}}><CheckCircle size={13} className="inline mr-1"/>{id?'Tinjau dokumen':'Review document'}</button>}
     {status?.can_upload&&<button type="button" className="intel-ghost text-xs text-red-700" disabled={busy} onClick={()=>remove(doc)}><Trash2 size={13}/></button>}</div>
    {reviewing===doc.id&&<div className="w-full border-t border-[#e3e9ef] pt-2 mt-2 space-y-2">
      <p className="text-xs text-[#53657b]">{id?
        'Pemeriksaan dokumen bukan verifikasi bahwa regulasi masih berlaku. Periksa penerbit, keaslian, perubahan dan pencabutan terlebih dahulu.':
        'Document review does not certify that a regulation is still in force. Check authenticity, amendments and repeal.'}</p>
      <textarea rows={2} className="intel-input w-full" maxLength={1500} value={reviewNotes}
        onChange={e=>setReviewNotes(e.target.value)}
        placeholder={id?'Catatan pemeriksaan (min 12 karakter)':'Review notes (min 12 characters)'}/>
      <div className="flex gap-2">
       <button className="intel-button text-xs" type="button" disabled={busy||reviewNotes.trim().length<12}
         onClick={()=>reviewDocument(doc,true)}>{id?'Tandai telah ditelaah':'Mark officer-reviewed'}</button>
       <button className="intel-ghost text-xs" type="button" disabled={busy}
         onClick={()=>setReviewing(null)}>{id?'Batal':'Cancel'}</button>
      </div>
    </div>}
   </div>)}
   {!docs.length&&<p className="text-sm text-[#64748b]">{id?'Belum ada PDF. Unggah dokumen resmi yang relevan agar AI dapat mengutipnya.':'No PDFs uploaded yet. Add a relevant authorized document for the assistant to cite.'}</p>}</div>
  </div>}
 </section>;
}
