import { useEffect, useRef, useState } from 'react';
import { Send, Plus, History, Trash2, MessageSquareText, ArrowDown } from 'lucide-react';
import { base44 } from '@/api/base44Client';
import AssistantRecords from '@/components/intel/AssistantRecords';
import AssistantInsights from '@/components/intel/AssistantInsights';
import AssistantDetectedTags from '@/components/intel/AssistantDetectedTags';
import AssistantKnowledgeLibrary from '@/components/intel/AssistantKnowledgeLibrary';
import {textFor} from '@/lib/assistantResponseLocale';
import AssistantIntelligenceReport from '@/components/intel/AssistantIntelligenceReport';
import AssistantActionDesk, {UserWorkspacePulse} from '@/components/intel/AssistantActionDesk';
import TranslatedAssistantAnswer from '@/components/intel/TranslatedAssistantAnswer';
import { useLanguage } from '@/lib/LanguageContext';

const starterKeys=['starter_latest_validated','starter_main_issues','starter_last_7_days','starter_campaign_issues','starter_locations','starter_high_priority','starter_campaign_materials','starter_unverified','starter_today'];
async function historyRequest(path='',method='GET',body=null){
 const token=window.__BAWASLU_DEMO_REPLICA__?'DEMO-SNAPSHOT':(window.localStorage.getItem('bawaslu_access_token')||'');
 if(!token)throw Error('Your login session has expired. Sign in to access conversation history.');
 const response=await fetch('/api/assistant-history'+path,{
  method,cache:'no-store',
  headers:{Authorization:'Bearer '+token,...(body?{'Content-Type':'application/json'}:{})},
  ...(body?{body:JSON.stringify(body)}:{})
 });
 const data=await response.json().catch(()=>({}));
 if(!response.ok)throw Error(response.status===401?'Your login session has expired. Sign in again.':data.detail||data.error||'Conversation history unavailable');
 return data;
}
export default function IntelligenceAssistant(){
 const {t}=useLanguage();
 const starters=starterKeys.map(t);
 const initialQuery=new URLSearchParams(window.location.search).get('q')||'';
 const [question,setQuestion]=useState(initialQuery),[messages,setMessages]=useState([]);
 const [busy,setBusy]=useState(false),[error,setError]=useState('');
 const [threads,setThreads]=useState([]),[activeId,setActiveId]=useState(null);
 const [historyBusy,setHistoryBusy]=useState(false),[historyError,setHistoryError]=useState('');
 const [analysisMode,setAnalysisMode]=useState('AUTO');
 const [responseDepth,setResponseDepth]=useState('DEEP');
 const [showHistory,setShowHistory]=useState(false);
 const activeIdRef=useRef(null);
 const latestRef=useRef(null);
 const [showJump,setShowJump]=useState(false);
 useEffect(()=>{
  const onScroll=()=>{const documentHeight=document.documentElement.scrollHeight;setShowJump(documentHeight-window.innerHeight-window.scrollY>360&&messages.length>2)};
  window.addEventListener('scroll',onScroll,{passive:true});onScroll();return()=>window.removeEventListener('scroll',onScroll);
 },[messages.length]);
 function setActive(id){activeIdRef.current=id;setActiveId(id)}
 useEffect(()=>{
  let live=true;
  historyRequest().then(data=>{if(live)setThreads(data.threads||[])})
   .catch(e=>{if(live)setHistoryError(e.message)});
  return()=>{live=false};
 },[]);
 function newConversation(){
  if(busy||historyBusy)return;
  setActive(null);setMessages([]);setQuestion('');setError('');setHistoryError('');
 }
 async function openThread(id){
  if(busy||historyBusy)return;
  setHistoryBusy(true);setHistoryError('');setError('');
  try{
   const thread=await historyRequest('/'+encodeURIComponent(id));
   setActive(thread.id);setMessages(thread.messages||[]);setQuestion('');
  }catch(e){setHistoryError(e.message)}
  finally{setHistoryBusy(false)}
 }
 async function removeThread(id){
  if(busy||historyBusy||!window.confirm('Delete this conversation history? Source intelligence records are not deleted.'))return;
  setHistoryBusy(true);setHistoryError('');
  try{
   await historyRequest('/'+encodeURIComponent(id),'DELETE');
   setThreads(old=>old.filter(x=>x.id!==id));
   if(activeIdRef.current===id){setActive(null);setMessages([])}
  }catch(e){setHistoryError(e.message)}
  finally{setHistoryBusy(false)}
 }
 async function ask(text){
  const q=String(text||'').trim();
  if(!q||busy||historyBusy)return;
  setBusy(true);setError('');setQuestion('');
  const previous=messages.filter(m=>m.role==='user').at(-1)?.text||'';
  const outgoing=[...messages,{role:'user',text:q}];
  setMessages(outgoing);
  try{
   const response=await base44.functions.invoke('intelligenceAssistant',{question:q,previousQuestion:previous,analysisMode,responseDepth,conversationContext:messages.slice(-20).map(m=>({role:m.role,text:String(m.text||'').slice(0,1300)}))});
   const answer={
    role:'assistant',text:response.data.answer||'',
    records:response.data.records||[],provider:response.data.provider,
    grounding:response.data.grounding,evidence_snapshot:response.data.evidence_snapshot,
    analytical_findings:response.data.analytical_findings,featured_sources:response.data.featured_sources,
    response_profile:response.data.response_profile||'SOCIAL_ANALYSIS',
    answer_language:response.data.answer_language,detected_tags:response.data.detected_tags||[],presentation_labels:response.data.presentation_labels||{}
   };
   const full=[...outgoing,answer];
   setMessages(full);
   try{
    const title=messages[0]?.text||q.slice(0,120);
    const saved=await historyRequest('','PUT',{
     id:activeIdRef.current,title,messages:full
    });
    setActive(saved.id);
    setThreads(old=>[{
      id:saved.id,title:saved.title,updated_at:saved.updated_at,created_at:saved.created_at
    },...old.filter(x=>x.id!==saved.id)]);
   }catch(e){setHistoryError('The answer is shown but its history could not be saved: '+e.message)}
  }catch(e){
   setError(e.response?.data?.error||e.message||t('assistant_unavailable'));
   setMessages(messages);setQuestion(q);
  }finally{setBusy(false)}
 }
 return <div className="max-w-[1300px] mx-auto space-y-5">
  <header className="rounded-2xl bg-gradient-to-r from-[#801b24] to-[#a52a2f] px-6 py-7 text-white">
   <div className="text-[11px] uppercase tracking-[.18em] font-bold text-[#f1d9d6]">ASISTEN KERJA INTELIJEN BAWASLU</div>
   <h1 className="text-2xl md:text-3xl font-bold mt-2">{t('intelligence_assistant')}</h1>
   <p className="text-sm text-[#f5dfdb] mt-2">Dari temuan menuju pekerjaan nyata: analisis, prioritas pemeriksaan, penugasan, dan draf laporan dalam satu tempat.</p>
   <p className="text-xs text-[#f0d0cc] mt-2">Hanya sumber yang Anda berwenang akses. Tindak lanjut disimpan setelah konfirmasi dan tetap memerlukan pemeriksaan petugas.</p>
  </header>
  <UserWorkspacePulse/>
  <AssistantKnowledgeLibrary/>
  <div className="flex flex-wrap gap-2">
   <button type="button" className="intel-ghost" aria-expanded={showHistory} onClick={()=>setShowHistory(v=>!v)}><History size={15}/> Conversation history</button>
   <button type="button" className="intel-button" disabled={busy||historyBusy} onClick={newConversation}><Plus size={15}/>{t('new_conversation')}</button>
  </div>
  <div className={showHistory?'grid gap-4 lg:grid-cols-[270px_minmax(0,1fr)]':'block'}>
   {showHistory&&<aside className="intel-card p-3 space-y-2 max-h-[70vh] overflow-y-auto" aria-label="Saved conversations">
    <h2 className="text-xs uppercase tracking-wider font-bold text-[#546b76] px-2 py-2">Saved conversations</h2>
    {threads.map(thread=><div key={thread.id} className={'flex items-start gap-1 rounded-lg p-1 '+(activeId===thread.id?'bg-[#faebea]':'hover:bg-slate-50')}>
      <button type="button" disabled={busy||historyBusy} onClick={()=>openThread(thread.id)} className="flex-1 min-w-0 text-left rounded-md p-2" aria-current={activeId===thread.id?'page':undefined}>
       <span className="block text-sm font-semibold truncate">{thread.title||'Conversation'}</span>
       <span className="block text-[11px] text-slate-500 mt-1">{thread.updated_at?new Date(thread.updated_at).toLocaleString('en-GB'):''}</span>
      </button>
      <button type="button" className="rounded-md p-2 text-slate-500 hover:text-red-700" disabled={busy||historyBusy} title="Delete conversation" aria-label={'Delete '+(thread.title||'conversation')} onClick={()=>removeThread(thread.id)}><Trash2 size={15}/></button>
     </div>)}
    {!threads.length&&<p className="px-2 py-4 text-xs text-slate-500">No saved conversations yet. Your completed chats will appear here.</p>}
   </aside>}
   <div className="min-w-0 space-y-4">
    <section className="intel-card p-4 md:p-6 space-y-5 min-h-[300px]" aria-live="polite">
     {!messages.length&&<div className="space-y-4">
       <div><p className="text-sm font-bold text-[#801b24] mb-2">Mulai dari pekerjaan yang ingin diselesaikan</p>
        <div className="grid md:grid-cols-3 gap-3">
        {[
         ['Pilih prioritas','Temukan 3 isu paling penting yang perlu ditindaklanjuti BAWASLU dari bukti tersimpan. Jelaskan mengapa, sertakan sumber dan langkah verifikasi.'],
         ['Siapkan penugasan','Identifikasi isu elektoral atau dugaan pelanggaran yang memerlukan pemeriksaan petugas. Rekomendasikan departemen terkait dan sumber untuk tiap temuan.'],
         ['Siapkan laporan','Susun dasar laporan intelijen dari temuan tersimpan: ringkasan eksekutif, bukti kunci, ketidakpastian dan langkah yang perlu dilakukan.']
        ].map(([label,prompt])=><button key={label} type="button" disabled={busy||historyBusy}
           className="rounded-xl border border-[#e3cdd0] bg-[#fff9f9] p-3 text-left text-sm font-semibold text-[#801b24] hover:bg-[#f8ebed]"
           onClick={()=>ask(prompt)}>{label}<span className="block text-[11px] mt-1 font-normal text-[#697c8c]">Asisten mencari bukti dan menyiapkan tindak lanjut</span></button>)}
        </div>
       </div>
       <div className="flex gap-2 items-center"><MessageSquareText size={18} className="text-[#a52a2f]"/><p className="text-sm font-semibold">{t('try_asking')}</p></div>
       <div className="flex flex-wrap gap-2">{starters.map(starter=><button key={starter} type="button" disabled={busy||historyBusy} onClick={()=>ask(starter)} className="intel-ghost text-xs text-left">{starter}</button>)}</div>
     </div>}
     {messages.map((m,i)=><div key={i} className={m.role==='user'?'flex justify-end':'flex justify-start'}>
      <div className={m.role==='user'?'max-w-[90%] rounded-xl bg-[#801b24] text-white px-4 py-3 text-sm':'w-full rounded-xl bg-[#f5f7fa] border border-[#e4e9ef] p-4 text-sm'}>
       {m.role==='assistant'?<>
        {i===messages.length-1&&m.response_profile==='ACTION_REQUEST'&&
         <AssistantActionDesk message={m} question={messages[i-1]?.text||''} language={m.answer_language||'id'} labels={m.presentation_labels}/>}
        <TranslatedAssistantAnswer text={m.text} language={m.answer_language||''} labels={m.presentation_labels}/>
       </>:<p data-i18n-exempt className="whitespace-pre-line leading-6">{m.text}</p>}
       {m.role==='assistant'&&<>
        {m.response_profile!=='PDF_GUIDANCE'&&m.grounding?.supporting_count>0&&
         <p className="mt-4 text-xs text-[#64748b]">{m.grounding.supporting_count} {textFor(m.answer_language||'id',m.presentation_labels,'evidence_refs')} · {textFor(m.answer_language||'id',m.presentation_labels,'source_review_required')}</p>}
        {m.response_profile!=='PDF_GUIDANCE'&&<AssistantDetectedTags tags={m.detected_tags} language={m.answer_language||'id'} labels={m.presentation_labels}/>}
        {m.response_profile==='SOCIAL_ANALYSIS'&&<AssistantInsights snapshot={m.evidence_snapshot} grounding={m.grounding} language={m.answer_language||'id'} labels={m.presentation_labels}/>}
        {m.response_profile!=='PDF_GUIDANCE'&&<AssistantIntelligenceReport findings={m.analytical_findings} records={m.records} language={m.answer_language||'id'} labels={m.presentation_labels} compact={m.response_profile==='SOCIAL_ANALYSIS'}/>}
        <AssistantRecords records={m.records} featured={m.featured_sources} language={m.answer_language||'id'} labels={m.presentation_labels} compactPdf={m.response_profile==='PDF_GUIDANCE'}/></>}
      </div>
     </div>)}
     {busy&&<p role="status" className="text-sm text-[#617789]">{t('reviewing_records')}</p>}
     {error&&<p role="alert" className="text-sm text-red-700">{error}</p>}
     {historyError&&<p role="alert" className="text-sm text-amber-800">{historyError}</p>}
     <div ref={latestRef} aria-hidden="true"/>
    </section>
    {showJump&&<button type="button" onClick={()=>latestRef.current?.scrollIntoView({behavior:'smooth',block:'end'})} className="fixed bottom-24 right-7 z-40 flex items-center gap-2 rounded-full bg-[#801b24] px-4 py-2 text-sm font-semibold text-white shadow-lg" aria-label="Jump to latest chat message"><ArrowDown size={16}/> Jump to latest</button>}
    <div className="flex items-center justify-between flex-wrap gap-2 text-xs text-[#53657b]">
      <span>Ruang lingkup jawaban: {analysisMode==='AUTO'?'Analisis sumber yang tersedia':analysisMode==='DATA'?'Hanya sumber BAWASLU tersimpan':'Penjelasan umum'}</span>
      <label className="flex items-center gap-2">Intelligence depth
       <select aria-label="Intelligence response depth" className="rounded-lg border border-[#dce5e7] bg-white px-3 py-2 text-sm" value={responseDepth} onChange={e=>setResponseDepth(e.target.value)} disabled={busy}>
        <option value="EXECUTIVE">Executive brief</option>
        <option value="DEEP">Deep analysis</option>
        <option value="INVESTIGATION">Investigation support</option>
       </select>
      </label>
      <select aria-label="Assistant answer source" className="rounded-lg border border-[#dce5e7] bg-white px-3 py-2 text-sm" value={analysisMode} onChange={e=>setAnalysisMode(e.target.value)} disabled={busy}>
       <option value="AUTO">Otomatis</option>
       <option value="DATA">Bukti tersimpan</option>
       <option value="GENERAL">Pengetahuan umum</option>
      </select>
     </div>
    <form onSubmit={e=>{e.preventDefault();ask(question)}} className="intel-card p-3 flex gap-2">
     <input aria-label={t('assistant_question_aria')} className="intel-input flex-1" maxLength={400} placeholder={t('assistant_placeholder')} value={question} onChange={e=>setQuestion(e.target.value)}/>
     <button type="submit" className="intel-button" disabled={busy||historyBusy||!question.trim()}><Send size={16}/><span className="hidden sm:inline">{t('send')}</span></button>
    </form>
    <p className="text-xs text-[#8192a3]">AI menyiapkan analisis dan draf; petugas memilih, memeriksa, dan mengonfirmasi setiap tindakan resmi.</p>
   </div>
  </div>
 </div>;
}
