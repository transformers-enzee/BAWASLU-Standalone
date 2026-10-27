import { useEffect, useRef, useState } from 'react';
import { Send, Plus, History, Trash2, MessageSquareText } from 'lucide-react';
import { base44 } from '@/api/base44Client';
import AssistantRecords from '@/components/intel/AssistantRecords';
import AssistantAnswer from '@/components/intel/AssistantAnswer';
import { useLanguage } from '@/lib/LanguageContext';

const starterKeys=['starter_latest_validated','starter_main_issues','starter_last_7_days','starter_campaign_issues','starter_locations','starter_high_priority','starter_campaign_materials','starter_unverified','starter_today'];
async function historyRequest(path='',method='GET',body=null){
 const token=window.localStorage.getItem('bawaslu_access_token')||'';
 if(!token)throw Error('Your login session has expired. Sign in to access conversation history.');
 const response=await fetch((import.meta.env.VITE_API_BASE_URL||'')+'/api/assistant-history'+path,{
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
 const [showHistory,setShowHistory]=useState(true);
 const activeIdRef=useRef(null);
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
   const response=await base44.functions.invoke('intelligenceAssistant',{question:q,previousQuestion:previous});
   const answer={
    role:'assistant',text:response.data.answer||'',
    records:response.data.records||[],provider:response.data.provider,
    grounding:response.data.grounding
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
  <header className="rounded-2xl bg-gradient-to-r from-[#132d45] to-[#116b58] px-6 py-7 text-white">
   <div className="text-[11px] uppercase tracking-[.18em] font-bold text-[#b3e1d8]">{t('assistant_read_only')}</div>
   <h1 className="text-2xl md:text-3xl font-bold mt-2">{t('intelligence_assistant')}</h1>
   <p className="text-sm text-[#d3e9e4] mt-2">{t('assistant_tagline')}</p>
   <p className="text-xs text-[#c6ded9] mt-2">Answers are limited to authorised intelligence. Review supporting records before any officer decision.</p>
  </header>
  <div className="flex flex-wrap gap-2">
   <button type="button" className="intel-ghost" aria-expanded={showHistory} onClick={()=>setShowHistory(v=>!v)}><History size={15}/> Conversation history</button>
   <button type="button" className="intel-button" disabled={busy||historyBusy} onClick={newConversation}><Plus size={15}/>{t('new_conversation')}</button>
  </div>
  <div className={showHistory?'grid gap-4 lg:grid-cols-[270px_minmax(0,1fr)]':'block'}>
   {showHistory&&<aside className="intel-card p-3 space-y-2 max-h-[70vh] overflow-y-auto" aria-label="Saved conversations">
    <h2 className="text-xs uppercase tracking-wider font-bold text-[#546b76] px-2 py-2">Saved conversations</h2>
    {threads.map(thread=><div key={thread.id} className={'flex items-start gap-1 rounded-lg p-1 '+(activeId===thread.id?'bg-[#e7f4f0]':'hover:bg-slate-50')}>
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
     {!messages.length&&<div className="space-y-3">
       <div className="flex gap-2 items-center"><MessageSquareText size={18} className="text-[#147b67]"/><p className="text-sm font-semibold">{t('try_asking')}</p></div>
       <div className="flex flex-wrap gap-2">{starters.map(starter=><button key={starter} type="button" disabled={busy||historyBusy} onClick={()=>ask(starter)} className="intel-ghost text-xs text-left">{starter}</button>)}</div>
     </div>}
     {messages.map((m,i)=><div key={i} className={m.role==='user'?'flex justify-end':'flex justify-start'}>
      <div className={m.role==='user'?'max-w-[90%] rounded-xl bg-[#153b57] text-white px-4 py-3 text-sm':'w-full rounded-xl bg-[#f5f7fa] border border-[#e4e9ef] p-4 text-sm'}>
       {m.role==='assistant'?<AssistantAnswer text={m.text}/>:<p className="whitespace-pre-line leading-6">{m.text}</p>}
       {m.role==='assistant'&&<>{m.provider&&<p className={'mt-4 rounded-lg border px-3 py-2 text-xs '+(m.provider.mode==='OPENAI_GROUNDED'?'border-sky-200 bg-sky-50 text-[#315f76]':'border-amber-200 bg-amber-50 text-[#7b622c]')}><strong>{m.provider.mode==='OPENAI_GROUNDED'?t('grounded_ai_answer'):t('safe_fallback')}</strong>{m.provider.model?' · '+m.provider.model:''}{m.grounding?' · '+(m.grounding.supporting_count||0)+' '+t('supporting_records_count'):''}</p>}<AssistantRecords records={m.records}/></>}
      </div>
     </div>)}
     {busy&&<p role="status" className="text-sm text-[#617789]">{t('reviewing_records')}</p>}
     {error&&<p role="alert" className="text-sm text-red-700">{error}</p>}
     {historyError&&<p role="alert" className="text-sm text-amber-800">{historyError}</p>}
    </section>
    <form onSubmit={e=>{e.preventDefault();ask(question)}} className="intel-card p-3 flex gap-2">
     <input aria-label={t('assistant_question_aria')} className="intel-input flex-1" maxLength={400} placeholder={t('assistant_placeholder')} value={question} onChange={e=>setQuestion(e.target.value)}/>
     <button type="submit" className="intel-button" disabled={busy||historyBusy||!question.trim()}><Send size={16}/><span className="hidden sm:inline">{t('send')}</span></button>
    </form>
    <p className="text-xs text-[#8192a3]">{t('assistant_footer')}</p>
   </div>
  </div>
 </div>;
}
