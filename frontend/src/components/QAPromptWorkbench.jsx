import {useEffect,useState,useCallback} from 'react';
import {FlaskConical,Save,RefreshCw} from 'lucide-react';
import QAAlignmentReview from '@/components/QAAlignmentReview';
const fld='w-full border border-slate-200 rounded-lg px-3 py-2 text-sm bg-white';
const auth=()=>window.localStorage.getItem('bawaslu_access_token')||'';
async function call(path,body){
 const opts={method:body?'POST':'GET',cache:'no-store',headers:{Authorization:'Bearer '+auth()}};
 if(body){opts.headers['Content-Type']='application/json';opts.body=JSON.stringify(body)}
 const res=await fetch('/api/smart-radar/qa/tuning'+path,opts);
 const val=await res.json().catch(()=>({}));
 if(!res.ok)throw Error(typeof val.detail==='string'?val.detail:'QA request failed');
 return val;
}
export default function QAPromptWorkbench({canEdit=false,language='en',maxRun=3,ready=false}){
 const id=language==='id';
 const [preflight,setPreflight]=useState(null),[preflightError,setPreflightError]=useState('');
 const [audit,setAudit]=useState(null),[auditError,setAuditError]=useState('');
 const [auditVersion,setAuditVersion]=useState(17);
 const [auditBatch,setAuditBatch]=useState(5);
 const [useReferences,setUseReferences]=useState(false);
 const [qualityReferences,setQualityReferences]=useState(false);
 const [contrastReferences,setContrastReferences]=useState(false);
 const [data,setData]=useState(null),[prompt,setPrompt]=useState(''),[title,setTitle]=useState('Calibration revision 1'),
 [note,setNote]=useState(''),[selected,setSelected]=useState(null),[details,setDetails]=useState(null),
 [busy,setBusy]=useState(''),[error,setError]=useState(''),[notice,setNotice]=useState('');
 const reloadAudit=useCallback(()=>fetch('/api/smart-radar/qa/tuning/exemplar-audit?version_id='+auditVersion,{headers:{Authorization:'Bearer '+auth()},cache:'no-store'}).then(async r=>{if(!r.ok)throw Error('Audit status unavailable');return r.json()}).then(v=>{setAudit(v);setAuditError('')}).catch(e=>setAuditError(e.message)),[auditVersion]);
 const reloadPreflight=useCallback(()=>call('/preflight').then(v=>{setPreflight(v);setPreflightError('')}).catch(e=>setPreflightError(e.message)),[]);
 const refresh=useCallback(async()=>{
   const d=await call('');
   setData(d);setPrompt(s=>s||d.default_instructions||'');
   setSelected(s=>s||d.versions?.[0]?.id||null);
 },[]);
 useEffect(()=>{refresh().catch(e=>setError(e.message));reloadPreflight();reloadAudit()},[refresh,reloadPreflight,reloadAudit]);
 useEffect(()=>{
   if(selected)call('/versions/'+selected).then(setDetails).catch(e=>setError(e.message));
 },[selected,data?.versions?.length]);
 async function save(){
   setBusy('save');setError('');setNotice('');
   try{
     const r=await call('/versions',{title,instructions:prompt,change_note:note,use_shahrin_references:useReferences,use_quality_gated_references:qualityReferences,use_contrast_references:contrastReferences});
     setSelected(r.version_id);
     setNotice(id?'Versi baru disimpan; belum menggunakan API AI.':'New prompt version saved; no AI call was made.');
     setTitle(id?'Revisi berikutnya':'Next revision');setNote('');setUseReferences(false);setQualityReferences(false);setContrastReferences(false);
     await refresh();
   }catch(e){setError(e.message)}finally{setBusy('')}
 }
 async function test(retryFailed=false){
   setBusy(retryFailed?'retry':'test');setError('');setNotice('');
   try{
     const allowance=Math.min(3,maxRun||3,data?.slots_available??3);
     if(allowance<=0){
       setError(id?'Batas QA hari ini telah habis. Tidak ada permintaan AI yang dikirim.':
         'No QA requests remain under the configured budget. No AI call was made.');
       return;
     }
     const r=await call('/run',{
       version_id:selected,
       limit:retryFailed?1:Math.max(1,allowance),
       retry_failed:retryFailed
     });
     const messages=[];
     if(r.saved?.length)messages.push(r.saved.length+(id?' hasil tersimpan':' predictions saved'));
     if(r.errors?.length)messages.push(
       r.errors.length+(id?' rekaman gagal dan dilewati; dapat dicoba ulang secara terpisah':' failed and skipped; use Retry failed separately'));
     if(r.slots_remaining===0)messages.push(id?'Batas QA hari ini tercapai':'QA budget reached');
     if(!messages.length)messages.push(r.message|| (id?'Tidak ada sampel yang perlu diuji':'No new records available'));
     setNotice(messages.join(' · '));
     await refresh();setDetails(await call('/versions/'+selected));
   }catch(e){setError(e.message)}finally{setBusy('')}
 }
 async function load(v){
   setSelected(v);setBusy('load');setError('');
   try{
     const d=await call('/versions/'+v);
     setUseReferences(false);setPrompt(d.instructions);setTitle((id?'Revisi dari v':'Revision from v')+v);setNote('');setDetails(d);
   }catch(e){setError(e.message)}finally{setBusy('')}
 }
 const versions=data?.versions||[];
 const chosen=versions.find(v=>v.id===selected);
 const slots=Math.max(0,Math.min(3,maxRun||3,data?.slots_available??3));
 const hasFailures=(details?.results?.failed?.length||0)>0;
 return <section className="rounded-lg border border-slate-200 bg-white p-4 space-y-4">
   <div><h2 className="text-lg font-semibold flex items-center gap-2"><FlaskConical size={19}/>{id?'Perbaikan Prompt AI Berkelanjutan':'Continuous AI Prompt Improvement'}</h2>
     <p className="text-xs text-slate-600 mt-1">{id?'Ubah instruksi, simpan versi baru, uji pada sampel pengembangan yang sama, periksa kesalahan, lalu ulangi.':'Edit instructions, save a new version, test on the same development cases, inspect mistakes, and repeat. No deployment needed per revision.'}</p>
   </div>
   {error&&<p role="alert" className="text-sm text-red-800 bg-red-50 rounded-lg p-3">{error}</p>}
   {notice&&<p role="status" className="text-sm text-emerald-800 bg-emerald-50 rounded-lg p-3">{notice}</p>}
   <div className="rounded-lg border border-slate-200 bg-slate-50 p-3 space-y-2">
     <div className="flex justify-between items-center gap-2"><b className="text-sm">{id?'Pemeriksaan Kalibrasi Gratis':'No-credit Calibration Preflight'}</b>
       <button type="button" onClick={reloadPreflight} className="text-xs border rounded px-2 py-1 bg-white">{id?'Periksa ulang':'Recheck'}</button></div>
     {preflightError&&<p role="alert" className="text-xs text-red-700">{preflightError}</p>}
     {preflight&&<><p className="text-xs text-slate-700">{id?'Kesamaan acuan terdekat':'Nearest reference agreement'}: <b>{preflight.nearest_reference_agreement}/{preflight.development_evaluated}</b> · {id?'Contoh lemah/bertentangan':'Weak/conflicting cases'}: <b>{preflight.weak_or_conflicting}</b></p>
       <p className="text-xs text-slate-700">{id?'Kategori tanpa contoh yang memenuhi syarat':'Categories with no eligible examples'}: <b>{preflight.categories_without_eligible_references?.join(', ')||'None'}</b></p>
       <p className={'text-xs font-semibold '+(preflight.paid_v2_enabled?'text-amber-800':'text-red-700')}>{preflight.paid_v2_enabled?(id?'Uji berbayar v2 diizinkan; perlu tinjauan':'Paid v2 enabled; review first'):(id?'Pengujian berbayar v2 dijeda':'Paid v2 testing paused')}</p>
       <p className="text-xs text-slate-500">{id?'Kecocokan contoh bukan akurasi AI':'Reference agreement is not AI accuracy.'}</p></>}
   </div>
   <div className="rounded-lg border border-blue-200 bg-blue-50 p-3 space-y-2">
     <div className="flex justify-between gap-2 items-center"><b className="text-sm">{id?'Uji V17: 18 contoh yang sama':'V17 paired 18-post calibration pilot'}</b><button type="button" className="border bg-white rounded px-2 py-1 text-xs" onClick={reloadAudit}>{id?'Muat ulang':'Refresh audit'}</button></div>
     <p className="text-xs text-slate-700">{id?'V17: aturan kategori Shahrin yang lebih rinci, diuji pada 18 post yang sama seperti V16. Maksimum 18 panggilan berbayar; versi lama hanya untuk pembanding.':'V17 uses clearer Shahrin category boundaries and the same first 18 exemplar posts as V16. Default 5 paid calls per click, limited to 18 total. Historical versions are read-only; not independent accuracy.'}</p>
     <label className="text-xs flex items-center gap-2">{id?'Versi audit':'Audit version'}<select className="border bg-white rounded p-1" value={auditVersion} onChange={e=>{setAuditVersion(Number(e.target.value));setAudit(null)}}><option value={17}>V17 (new Shahrin category boundaries)</option><option value={16}>V16 (18-post baseline, read-only)</option><option value={15}>V15 (historical no-reference audit)</option><option value={14}>V14 (historical no-reference audit)</option></select></label>
     <label className="text-xs flex items-center gap-2">{id?'Ukuran batch berbayar':'Paid batch size'}<select className="border bg-white rounded p-1" value={auditBatch} onChange={e=>setAuditBatch(Number(e.target.value))}><option value={3}>3</option><option value={5}>5</option><option value={15}>15</option></select></label>
     {auditError&&<p role="alert" className="text-xs text-red-700">{auditError}</p>}
     {audit&&<p className="text-sm font-semibold">{audit.completed}/{audit.target} {id?'selesai':'assessed'} · {audit.agreement==null?'—':(audit.agreement*100).toFixed(1)+'%'} {id?'cocok':'agreement'} · {audit.quote_warnings} {id?'peringatan kutipan':'quote warnings'} · {audit.with_references??0} {id?'dengan referensi':'with Shahrin references'}</p>}
     {auditVersion===17&&audit?.baseline_paired_n>0&&<p className="text-xs text-slate-700">{id?"V16, post yang sama":"V16 on the exact same posts"}: <b>{audit.baseline_paired_matched}/{audit.baseline_paired_n} ({(audit.baseline_paired_agreement*100).toFixed(1)}%)</b> · {id?"V17":"V17"}: <b>{audit.matched}/{audit.completed}</b></p>}
     {canEdit&&<button type="button" disabled={!!busy||!ready||!audit||audit.remaining<=0||!preflight?.paid_v2_enabled||slots<=0||auditVersion!==17} className="bg-[#147968] text-white rounded px-3 py-2 text-sm disabled:opacity-50" onClick={async()=>{setBusy('audit');setAuditError('');try{const resp=await fetch('/api/smart-radar/qa/tuning/exemplar-audit/run',{method:'POST',headers:{Authorization:'Bearer '+auth(),'Content-Type':'application/json'},body:JSON.stringify({version_id:auditVersion,limit:auditBatch})});const out=await resp.json();if(!resp.ok)throw Error(typeof out.detail==='string'?out.detail:'Audit request failed');setNotice((out.saved?.length||0)+' exemplar predictions saved');await reloadAudit();await refresh()}catch(e){setAuditError(e.message)}finally{setBusy('')}}}>{busy==='audit'?'Assessing…':(id?'Uji '+auditBatch+' contoh berikutnya (berbayar)':'Assess next '+auditBatch+' exemplars (paid)')}</button>}
   </div>
   <QAAlignmentReview language={language} onSaved={()=>refresh().catch(e=>setError(e.message))}/>
   <div className="grid grid-cols-3 gap-2">
     {[[data?.development_posts??'—',id?'Sampel pengembangan':'Development posts'],
       [data?.exemplar_posts??'—',id?'Contoh dari manusia':'Human examples'],
       [data?.sealed_holdout_posts??'—',id?'Sampel tersegel':'Sealed holdouts']].map(([n,l])=>
         <div className="rounded-lg bg-slate-50 p-3" key={l}><b className="text-xl">{n}</b><p className="text-xs text-slate-500 mt-1">{l}</p></div>)}
   </div>
   <p className="text-xs p-3 border border-amber-200 rounded-lg bg-amber-50 text-amber-950">{id?
     'Kecocokan pada sampel pengembangan berguna untuk memperbaiki prompt, bukan bukti akurasi akhir. Label Shahrin masih perlu disetujui analis. Sampel uji final tidak dibuka saat tuning.':
     'Development agreement is useful for iterating, not final unbiased accuracy. Human reference conflicts must be reviewed; unresolved flagged cases are excluded from new tests. Final holdouts stay sealed.'}</p>
   <div className="grid lg:grid-cols-[1.2fr_1fr] gap-4 items-start">
     <div className="space-y-2">
       <h3 className="font-semibold text-sm">{id?'Ubah Instruksi AI':'Edit AI Instructions'}</h3>
       <label className="text-xs block">{id?'Nama versi baru':'New version name'}<input className={fld+' mt-1'} value={title} onChange={e=>setTitle(e.target.value)} disabled={!canEdit} maxLength={100}/></label>
       <label className="text-xs block">{id?'Perubahan dari versi sebelumnya':'What changed and why?'}<input className={fld+' mt-1'} value={note} onChange={e=>setNote(e.target.value)} disabled={!canEdit} maxLength={500} placeholder="E.g. Do not infer misconduct from political timing"/></label>
       <label className="text-xs block">{id?'Instruksi klasifikasi lengkap':'Classification instructions'}<textarea className={fld+' mt-1 font-mono leading-5'} rows={18} value={prompt} spellCheck={false} onChange={e=>setPrompt(e.target.value)} disabled={!canEdit}/></label>
       {canEdit&&<label className="flex gap-2 items-start text-xs text-slate-700"><input type="checkbox" checked={useReferences} onChange={e=>{setUseReferences(e.target.checked);if(e.target.checked){setQualityReferences(false);setContrastReferences(false)}}}/><span>{id?'Gunakan contoh acuan Shahrin yang relevan untuk versi BARU (tidak mengubah versi lama)':'Use relevant Shahrin reference examples for this NEW version (existing versions unchanged)'}</span></label>}
       {canEdit&&<label className="flex gap-2 items-start text-xs text-slate-700"><input type="checkbox" checked={qualityReferences} onChange={e=>{setQualityReferences(e.target.checked);if(e.target.checked){setUseReferences(false);setContrastReferences(false)}}}/><span>{id?'Gunakan referensi Shahrin dengan pemeriksaan kualitas untuk versi BARU':'Use quality-gated Shahrin references for this NEW version (experimental; weak/conflicting examples excluded)'}</span></label>}
       {canEdit&&<label className="flex gap-2 items-start text-xs text-slate-700"><input type="checkbox" checked={contrastReferences} onChange={e=>{setContrastReferences(e.target.checked);if(e.target.checked){setUseReferences(false);setQualityReferences(false)}}}/><span>{id?'Gunakan contoh acuan kontras Shahrin untuk versi BARU (eksperimental)':'Use contrastive Shahrin references for a NEW version (experimental; retains distinct opposite-category examples)'}</span></label>}
       <div className="flex flex-wrap gap-2">
         {canEdit&&<button onClick={save} disabled={!!busy||prompt.length<300||title.trim().length<3} type="button" className="bg-[#147968] text-white rounded-lg px-3 py-2 text-sm disabled:opacity-50 flex items-center gap-1"><Save size={14}/>{busy==='save'?'Saving…':id?'Simpan versi baru':'Save new version'}</button>}
         <button onClick={()=>refresh().catch(e=>setError(e.message))} disabled={!!busy} type="button" className="border rounded-lg px-3 py-2 text-sm flex items-center gap-1"><RefreshCw size={14}/>{id?'Muat ulang':'Refresh'}</button>
       </div>
     </div>
     <div className="space-y-3">
       <h3 className="font-semibold text-sm">{id?'Riwayat dan perbandingan':'Versions and comparison'}</h3>
       {!versions.length&&<p className="text-xs text-slate-500 border rounded-lg p-3">{id?'Belum ada versi tersimpan. Simpan versi pertama.':'No saved version yet. Save the first one.'}</p>}
       {versions.map(v=><button type="button" key={v.id} onClick={()=>load(v.id)} className={'w-full border rounded-lg p-3 text-left '+(selected===v.id?'border-emerald-700 bg-emerald-50':'border-slate-200')}>
         <b className="text-sm">v{v.id} · {v.title}</b><p className="text-xs text-slate-600 mt-1">{v.change_note||'—'}</p>
         <p className="text-sm mt-2 font-semibold">{v.agreement==null?'—':(v.agreement*100).toFixed(1)+'%'}
           <span className="text-xs font-normal text-slate-500"> · {v.correct}/{v.tested} {id?'cocok':'matched'} · {v.tested}/{v.development_total} {id?'diuji':'tested'}</span></p>
       </button>)}
       <div className="border border-slate-200 rounded-lg p-3">
         <b className="text-sm">{id?'Uji versi':'Test version'} {selected?('v'+selected):'—'}</b>
         <p className="text-xs text-slate-500 mt-2">{id?'Hasil salah kategori disimpan sebagai mismatch, bukan error. Permintaan gagal dilewati; percobaan ulang hanya saat Anda memilih Retry.':'Incorrect categories are saved as mismatches, NOT errors. Failed requests are skipped and retried only when you choose Retry.'}</p>
         <p className="text-xs text-slate-600 mt-2">{id?'Kuota permintaan QA tersisa':'QA request allowance remaining'}: <b>{data?.slots_available??'—'}</b> {id?'untuk batch berikutnya':'for the next batch'}</p>
         {canEdit&&<button type="button" disabled={!ready||!!busy||!selected||slots<=0||((chosen?.change_note?.startsWith('[shahrin-ref-v2]')||chosen?.change_note?.startsWith('[shahrin-ref-v3]'))&&!preflight?.paid_v2_enabled)||(chosen?.development_total>0&&chosen.tested>=chosen.development_total)} onClick={()=>test(false)} className="mt-3 w-full bg-[#147968] rounded-lg px-3 py-2 text-sm text-white disabled:opacity-50">
           {busy==='test'?'Assessing…':(id?'Uji ': 'Test next ')+slots+(id?' pos pengembangan berikutnya':' development posts')}
         </button>}
         {hasFailures&&
           <div className="mt-3 bg-amber-50 border border-amber-200 rounded-lg p-3">
             <b className="text-xs text-amber-900">{id?'Ada permintaan yang gagal':'Previous provider/validation failures'} ({details.results.failed.length})</b>
             <div className="space-y-1 my-2">
               {details.results.failed.map(f=><p className="text-xs text-slate-700" key={f.qa_id}><b>{f.qa_id}</b> · {f.reason}</p>)}
             </div>
             {canEdit&&<button type="button" disabled={!ready||!!busy||slots<=0} onClick={()=>test(true)} className="border border-amber-400 bg-white rounded-lg px-3 py-2 text-xs disabled:opacity-50">
               {busy==='retry'?'Retrying…':id?'Coba lagi satu rekaman gagal':'Retry one failed request (1)'}
             </button>}
           </div>}
       </div>
     </div>
   </div>
   {!!details?.results?.entries?.length&&<div className="border-t pt-4">
     <h3 className="font-semibold text-sm">{id?'Bandingkan hasil dengan Shahrin':'Inspect mistakes against Shahrin'} · v{selected}</h3>
     <p className="text-xs text-slate-500 mt-1">{id?'Gunakan kasus ini untuk mengedit prompt versi baru. Konfirmasikan label yang meragukan.':'Use development mistakes to edit the next prompt version. Confirm questionable labels with the analyst.'}</p>
     <div className="grid md:grid-cols-2 gap-3 mt-3">
       {details.results.entries.map(v=><div key={v.qa_id} className={'rounded-lg border p-3 text-xs '+(v.correct?'border-slate-200':'border-amber-300 bg-amber-50')}>
         <p className="font-semibold">{v.qa_id} · {v.correct?(id?'Cocok':'Match'):(id?'Tidak cocok':'Mismatch')}</p>
         <p className="mt-2"><b>{id?'Shahrin':'Shahrin'}:</b> {v.human_category}</p>
         <p><b>AI:</b> {v.ai_category}</p>
         <p className="text-slate-500">{v.review_status==='confirmed'?(id?'Label dikonfirmasi':'Human confirmed'):(id?'Menunggu konfirmasi':'Awaiting human sign-off')}</p>
         <p className="mt-2 text-slate-700">{v.rationale}</p><p className="text-slate-600 mt-1">{v.boundary}</p>
         <details className="mt-2"><summary className="cursor-pointer text-[#147968]">{id?'Baca posting asli':'Read original source'}</summary>
           <p className="mt-2 whitespace-pre-wrap max-h-56 overflow-y-auto">{v.original_text}</p>
           <a href={v.source_url} className="underline text-[#147968]" target="_blank" rel="noopener noreferrer">{id?'Buka tautan sumber':'Open source URL'}</a>
         </details>
         {v.evidence_validation==='needs_source_review'&&<p className="text-amber-700 mt-1">{id?'Kutipan AI belum terverifikasi':'AI quote not verified'}</p>}
       </div>)}
     </div>
   </div>}
 </section>
}
