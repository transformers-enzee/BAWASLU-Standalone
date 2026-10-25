import {useEffect,useState,useCallback} from 'react';
import {Link} from 'react-router-dom';
import {useOutletContext} from 'react-router-dom';
import {useLanguage} from '@/lib/LanguageContext';
import {ArrowLeft,RefreshCw,Upload,CheckCircle2,AlertCircle,FlaskConical} from 'lucide-react';

const CATS=['Allegations / Violations','Voter Register / PDPB','Citizen Reports / Public Concerns','Disputes / Legal','Participatory Oversight','Election Operations','Digital Risks / Information','Uncertain'];
const token=()=>window.localStorage.getItem('bawaslu_access_token')||'';
async function api(path,body,upload=false){
  const opt={method:body?'POST':'GET',cache:'no-store',headers:{Authorization:'Bearer '+token()}};
  if(body){if(upload){opt.body=body}else{opt.headers['Content-Type']='application/json';opt.body=JSON.stringify(body)}}
  const res=await fetch('/api/smart-radar/qa'+path,opt);
  const json=await res.json().catch(()=>({}));
  if(!res.ok)throw new Error(json.detail||'Request failed');
  return json;
}
const wording={
 en:{
   title:'AI Quality Assurance Lab',note:'Compare blind AI classifications with actual analyst-reviewed labels. Separate from officer Action Desk.',
   imports:'Import curated source workbook',upload:'Upload 407-record workbook',importNote:'Uploads source posts only. Curated categories are candidate tags—not human reference decisions.',
   human:'Human reference labels',model:'AI predictions',covered:'Compared',accuracy:'Primary-category match',f1:'Macro F1',pending:'Not measurable yet',
   sample:'Balanced 100',all:'All 407',reviewed:'Human-labelled',run:'Assess next 3 (AI)',disabled:'AI assessment disabled until the staging administrator enables it.',
   missing:'No QA records yet. Import the curated 407-record workbook to create the balanced 100-record test.',
   source:'Original source',curated:'Provisional category (NOT GOLD)',humanTitle:'Shahrin / analyst reference review',
   relevance:'Electoral relevance',category:'Human primary category',perspective:'Perspective',actionable:'Review-worthy signal',
   incident:'Incident grouping key (optional)',notes:'Evidence / reviewer notes',save:'Save human reference',aiTitle:'Independent AI assessment',
   noAI:'Not assessed by AI',noHuman:'No human reference yet',reasons:'Explanation / uncertainty',
   agreement:'Category agreement',match:'Match',mismatch:'Mismatch',notready:'Pending both assessments',browse:'Records',
   onlyHuman:'No accuracy result until genuine human decisions and AI predictions both exist.',
   access:'Only authorized national QA reviewers may use this page.',admin:'AI costs are bounded, opt-in and cached; no AI runs when opening this page.',
   review:'Review a record',open:'Open original link',page:'Page',back:'Back to Smart Radar',aiMode:'AI status',
   saveOk:'Human review saved (QA-only)',importOk:'Curated workbook imported into QA area',
   unknown:'Uncertain',original:'Original post',next:'Next',prev:'Previous'
 },
 id:{
   title:'Laboratorium Kendali Mutu AI',note:'Bandingkan klasifikasi AI secara mandiri dengan label yang benar-benar telah ditinjau analis. Terpisah dari Meja Tindak Lanjut.',
   imports:'Impor berkas sumber kurasi',upload:'Unggah berkas 407 unggahan',importNote:'Hanya mengimpor sumber. Kategori kurasi adalah label sementara—bukan keputusan analis.',
   human:'Label acuan analis',model:'Prediksi AI',covered:'Sudah dibandingkan',accuracy:'Kecocokan kategori utama',f1:'F1 Makro',pending:'Belum dapat diukur',
   sample:'100 Sampel Seimbang',all:'Semua 407',reviewed:'Diberi Label Analis',run:'Nilai 3 unggahan berikutnya (AI)',disabled:'Penilaian AI belum diaktifkan oleh administrator staging.',
   missing:'Belum ada data QA. Impor berkas kurasi 407 unggahan untuk membuat 100 sampel seimbang.',
   source:'Sumber asli',curated:'Kategori sementara (BUKAN ACUAN)',humanTitle:'Penilaian acuan Shahrin / analis',
   relevance:'Relevansi pemilu',category:'Kategori utama hasil review',perspective:'Perspektif',actionable:'Memerlukan peninjauan',
   incident:'Kode kelompok kejadian (opsional)',notes:'Catatan bukti / peninjau',save:'Simpan acuan analis',aiTitle:'Penilaian AI independen',
   noAI:'Belum dinilai AI',noHuman:'Belum ada acuan analis',reasons:'Alasan / ketidakpastian',
   agreement:'Kecocokan kategori',match:'Cocok',mismatch:'Tidak cocok',notready:'Menunggu kedua penilaian',browse:'Daftar unggahan',
   onlyHuman:'Akurasi belum dapat dihitung tanpa keputusan manusia dan prediksi AI untuk unggahan yang sama.',
   access:'Hanya peninjau QA nasional yang berwenang dapat mengakses halaman ini.',admin:'Biaya AI dibatasi, memerlukan tindakan eksplisit dan hasilnya disimpan; membuka halaman tidak menjalankan AI.',
   review:'Tinjau unggahan',open:'Buka sumber asli',page:'Halaman',back:'Kembali ke Smart Radar',aiMode:'Status AI',
   saveOk:'Penilaian analis tersimpan (khusus QA)',importOk:'Berkas kurasi telah diimpor ke area QA',
   unknown:'Tidak pasti',original:'Unggahan asli',next:'Berikutnya',prev:'Sebelumnya'
 }
};
const bx='rounded-lg border border-slate-200 p-4 bg-white';
const input='w-full rounded-lg border border-slate-200 px-3 py-2 text-sm bg-white';
export default function SmartRadarQA(){
 const {access}=useOutletContext();
 const {language}=useLanguage();const t=key=>(wording[language]||wording.en)[key]||key;
 const [stats,setStats]=useState(null),[metrics,setMetrics]=useState(null),[records,setRecords]=useState([]);
 const [page,setPage]=useState(1),[cohort,setCohort]=useState('balanced'),[total,setTotal]=useState(0);
 const [current,setCurrent]=useState(null),[form,setForm]=useState({relevance:'Uncertain',primary_category:'Uncertain',perspective:'uncertain',actionable:'Uncertain',incident_key:'',note:''});
 const [file,setFile]=useState(null),[busy,setBusy]=useState(''),[message,setMessage]=useState(''),[error,setError]=useState('');
 const refresh=useCallback(async()=>{
   const [s,m,x]=await Promise.all([api('/status'),api('/metrics'),api('/records?cohort='+cohort+'&page='+page+'&size=15')]);
   setStats(s);setMetrics(m);setRecords(x.rows);setTotal(x.total);
 },[cohort,page]);
 useEffect(()=>{refresh().catch(e=>setError(e.message))},[refresh]);
 const select=row=>{
   setCurrent(row);
   setForm({qa_id:row.qa_id,relevance:row.h_relevance||'Uncertain',primary_category:row.h_category||'Uncertain',
     perspective:row.h_perspective||'uncertain',actionable:row.h_actionable||'Uncertain',
     incident_key:row.h_incident_key||'',note:row.h_note||''});
 };
 async function onUpload(e){
   e.preventDefault();if(!file)return;
   setBusy('import');setError('');setMessage('');
   try{
     const data=new FormData();data.append('file',file);
     const result=await api('/import-curated',data,true);
     setMessage(t('importOk')+': '+result.imported_or_existing+'; '+result.balanced_cohort+' QA');
     setPage(1);await refresh();
   }catch(e){setError(e.message)}finally{setBusy('')}
 }
 async function assess(){
   setBusy('assess');setError('');setMessage('');
   try{const result=await api('/assess-next',{limit:3});
     setMessage(result.errors?.length?'AI stopped: '+result.errors[0].reason:(result.processed?.length||0)+' assessments saved');
     await refresh();
   }catch(e){setError(e.message)}finally{setBusy('')}
 }
 async function onSave(e){
   e.preventDefault();if(!current)return;setBusy('save');setError('');setMessage('');
   try{await api('/human-review',{...form,qa_id:current.qa_id});
     setMessage(t('saveOk'));await refresh();
     setCurrent(null);
   }catch(e){setError(e.message)}finally{setBusy('')}
 }
 const canImport=access?.role==='National Administrator'&&access?.permissions?.administration;
 const canReview=Boolean(access?.permissions?.review_ai_suggestions||access?.permissions?.administration);
 if(!canReview)return <p className="p-6 text-red-700">{t('access')}</p>;
 return <div className="max-w-[1400px] mx-auto space-y-5">
   <div className="rounded-xl bg-gradient-to-r from-[#16364a] to-[#147968] text-white px-6 py-5 flex flex-wrap gap-4 justify-between items-center">
    <div><Link to="/" className="text-xs text-white/80 inline-flex gap-1 items-center"><ArrowLeft size={14}/>{t('back')}</Link>
     <h1 className="font-semibold text-2xl mt-2 flex items-center gap-2"><FlaskConical/> {t('title')}</h1>
     <p className="text-sm mt-1 text-white/85 max-w-[700px]">{t('note')}</p></div>
    <button onClick={()=>refresh().catch(e=>setError(e.message))} className="rounded-lg border border-white/40 px-3 py-2 text-sm"><RefreshCw size={15} className="inline mr-1"/>Refresh</button>
   </div>
   {error&&<div role="alert" className="border border-red-300 bg-red-50 text-red-800 rounded-lg p-3">{error}</div>}
   {message&&<div role="status" className="border border-emerald-300 bg-emerald-50 text-emerald-900 rounded-lg p-3">{message}</div>}
   <div className="grid grid-cols-2 lg:grid-cols-5 gap-3">
     {[[stats?.cohort_total??0,t('sample')],[metrics?.human_labeled??0,t('human')],[metrics?.ai_assessed??0,t('model')],[metrics?.compared??0,t('covered')],[metrics?.primary_category_accuracy==null?'—':(metrics.primary_category_accuracy*100).toFixed(1)+'%',t('accuracy')]].map(([n,l])=>
       <div className={bx} key={l}><b className="text-2xl text-slate-800 tabular-nums">{n}</b><p className="text-xs text-slate-500 mt-1">{l}</p></div>)}
   </div>
   <div className="grid grid-cols-2 md:grid-cols-4 gap-2">
    {[
      [metrics?.relevance_accuracy,language==='id'?'Kecocokan relevansi':'Relevance agreement'],
      [metrics?.perspective_accuracy,language==='id'?'Kecocokan perspektif':'Perspective agreement'],
      [metrics?.actionability_accuracy,language==='id'?'Kecocokan keputusan tindak lanjut':'Actionability agreement'],
      [metrics?.action_false_positives,language==='id'?'Alarm tindak lanjut keliru':'False-positive review signals']
     ].map(([v,label],i)=><div key={label} className="border border-slate-200 bg-white rounded-lg p-3"><b className="text-lg">{v==null?'—':i===3?v:(v*100).toFixed(1)+'%'}</b><p className="text-[11px] text-slate-500 mt-1">{label}</p></div>)}
   </div>
   <p className="text-xs text-amber-800 rounded-lg p-3 bg-amber-50 border border-amber-200">{t('onlyHuman')} {t('admin')}</p>
   <div className="grid lg:grid-cols-2 gap-4">
    <div className={bx}>
     <h2 className="font-semibold">{t('imports')}</h2><p className="text-xs text-slate-500 my-2">{t('importNote')}</p>
     {canImport?<form onSubmit={onUpload} className="flex flex-wrap gap-2 items-center">
       <label className="text-xs border rounded-lg px-3 py-2 cursor-pointer flex-1 min-w-0 text-slate-700"><Upload size={14} className="inline mr-1"/>{file?.name||'BAWASLU_Curated_Social_Listening_QA.xlsx'}
        <input type="file" className="sr-only" accept=".xlsx" onChange={e=>setFile(e.target.files?.[0]||null)}/></label>
       <button className="rounded-lg px-3 py-2 bg-[#147968] text-white text-sm disabled:opacity-50" disabled={!file||!!busy}>{busy==='import'?'Importing…':t('upload')}</button>
     </form>:<p className="text-sm text-slate-500">Import is restricted to national administrators.</p>}
     <p className="text-xs mt-2 text-slate-500">{stats?.total||0} / 407 imported. Balanced QA excludes source URLs already used in the 109-post pilot.</p>
    </div>
    <div className={bx}>
     <h2 className="font-semibold">{t('aiMode')}</h2>
     <p className="text-sm text-slate-600 my-2">{stats?.ai_ready?'Ready for a controlled 3-post batch':t('disabled')}</p>
     <div className="flex justify-between gap-3 items-center"><p className="text-xs text-slate-500">Model: {stats?.model||'Not configured'} · Rubric {stats?.prompt_version||'v1'}</p>
       {canImport&&<button disabled={!stats?.ai_ready||!!busy||!stats?.cohort_total} onClick={assess} className="rounded-lg px-3 py-2 bg-[#147968] text-white text-sm disabled:opacity-50">{busy==='assess'?'Assessing…':t('run')}</button>}</div>
    </div>
   </div>
   <div className="grid lg:grid-cols-[1.05fr_1fr] gap-4 items-start">
     <div className={bx}>
       <div className="flex flex-wrap items-center justify-between gap-2 mb-4">
         <h2 className="font-semibold">{t('browse')} ({total})</h2>
         <div className="flex gap-2 text-xs">{[['balanced',t('sample')],['human',t('reviewed')],['all',t('all')]].map(([v,l])=><button key={v} onClick={()=>{setCohort(v);setPage(1);setCurrent(null)}} className={'px-3 py-2 rounded-lg border '+(cohort===v?'bg-[#147968] text-white':'bg-white text-slate-600')}>{l}</button>)}</div>
       </div>
       {!records.length?<p className="py-10 text-sm text-slate-500">{t('missing')}</p>:records.map(row=>
         <button onClick={()=>select(row)} key={row.qa_id} className={'block w-full text-left border rounded-lg p-3 mb-2 hover:border-emerald-500 '+(current?.qa_id===row.qa_id?'border-emerald-600 bg-emerald-50':'border-slate-200')}>
           <div className="flex justify-between gap-2"><span className="font-semibold text-sm text-slate-800">{row.qa_id} <span className="font-normal text-slate-500">· {row.platform}</span></span><span className="text-[11px] text-slate-500">{row.h_category&&row.ai_result?(row.agreement?t('match'):t('mismatch')):t('notready')}</span></div>
           <p className="text-xs text-slate-700 mt-1 line-clamp-2">{row.message_original}</p>
           <p className="text-[11px] text-slate-500 mt-2">{t('curated')}: {row.curated_category}</p>
         </button>)}
       <div className="flex justify-between items-center text-xs text-slate-600 pt-2">
         <button disabled={page<=1} onClick={()=>setPage(p=>p-1)}>{t('prev')}</button>
         <span>{t('page')} {page} / {Math.max(1,Math.ceil(total/15))}</span>
         <button disabled={page>=Math.ceil(total/15)} onClick={()=>setPage(p=>p+1)}>{t('next')}</button>
       </div>
     </div>
     <div className={bx}>
       {!current?<p className="text-sm text-slate-500 p-8 text-center">{t('review')}</p>:<>
         <h2 className="font-semibold mb-3">{current.qa_id}</h2>
         <p className="text-xs text-slate-500 mb-2">{t('curated')}: {current.curated_category} — {t('notready')}</p>
         <div className="bg-slate-50 rounded-lg border p-3 max-h-[240px] overflow-y-auto text-sm whitespace-pre-wrap">{current.message_original}</div>
         <a href={current.source_url} className="text-xs text-[#147968] underline inline-block mt-2" target="_blank" rel="noopener noreferrer">{t('open')}</a>
         <div className="mt-4 border-t pt-4"><h3 className="font-semibold">{t('aiTitle')}</h3>
           {!current.ai_result?<p className="text-sm text-slate-500 mt-2">{t('noAI')}</p>:<div className="text-sm space-y-2 mt-2">
             <p><b>{current.ai_result.primary_category}</b> · {current.ai_result.relevance_score}/100 relevance · {current.ai_result.priority_score}/100 priority</p>
             <p className="text-slate-600">{current.ai_result.rationale}</p>
             <p className="text-slate-500 text-xs">{current.ai_result.uncertainty_note}</p>
             <p className="text-xs text-slate-500">Quote: {current.ai_result.evidence_quote}</p>
           </div>}
         </div>
         <form onSubmit={onSave} className="mt-4 border-t pt-4 space-y-3">
           <h3 className="font-semibold">{t('humanTitle')}</h3>
           <div className="grid grid-cols-2 gap-3">
             <label className="text-xs">{t('relevance')}<select className={input+' mt-1'} value={form.relevance} onChange={e=>setForm(s=>({...s,relevance:e.target.value}))}>{['Relevant','Irrelevant','Uncertain'].map(x=><option key={x}>{x}</option>)}</select></label>
             <label className="text-xs">{t('perspective')}<select className={input+' mt-1'} value={form.perspective} onChange={e=>setForm(s=>({...s,perspective:e.target.value}))}>{['operations','reputation','both','uncertain'].map(x=><option key={x}>{x}</option>)}</select></label>
             <label className="text-xs col-span-2">{t('category')}<select className={input+' mt-1'} value={form.primary_category} onChange={e=>setForm(s=>({...s,primary_category:e.target.value}))}>{CATS.map(x=><option key={x}>{x}</option>)}</select></label>
             <label className="text-xs col-span-2">{t('actionable')}<select className={input+' mt-1'} value={form.actionable} onChange={e=>setForm(s=>({...s,actionable:e.target.value}))}>{['Yes','No','Uncertain'].map(x=><option key={x}>{x}</option>)}</select></label>
           </div>
           <label className="text-xs block">{t('incident')}<input className={input+' mt-1'} value={form.incident_key} onChange={e=>setForm(s=>({...s,incident_key:e.target.value}))}/></label>
           <label className="text-xs block">{t('notes')}<textarea rows={3} className={input+' mt-1'} value={form.note} onChange={e=>setForm(s=>({...s,note:e.target.value}))}/></label>
           <button disabled={!!busy} className="bg-[#147968] text-white rounded-lg px-4 py-2 text-sm disabled:opacity-50">{busy==='save'?'Saving…':t('save')}</button>
         </form>
       </>}
     </div>
   </div>
 </div>;
}
