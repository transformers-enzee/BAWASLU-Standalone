import { useEffect, useRef, useState } from 'react';
import {useOutletContext} from 'react-router-dom';
import { Send, Plus, History, Trash2, MessageSquareText, ArrowDown, Download } from 'lucide-react';
import { base44 } from '@/api/base44Client';
import AssistantRecords from '@/components/intel/AssistantRecords';
import AssistantInsights from '@/components/intel/AssistantInsights';
import AssistantDetectedTags from '@/components/intel/AssistantDetectedTags';
import AssistantKnowledgeLibrary from '@/components/intel/AssistantKnowledgeLibrary';
import AssistantReviewConsolidation from '@/components/intel/AssistantReviewConsolidation';
import AssistantHumanScoring from '@/components/intel/AssistantHumanScoring';
import AssistantEvaluationSampler from '@/components/intel/AssistantEvaluationSampler';
import {textFor} from '@/lib/assistantResponseLocale';
import AssistantIntelligenceReport from '@/components/intel/AssistantIntelligenceReport';
import AssistantActionDesk, {UserWorkspacePulse} from '@/components/intel/AssistantActionDesk';
import TranslatedAssistantAnswer from '@/components/intel/TranslatedAssistantAnswer';
import { useLanguage } from '@/lib/LanguageContext';
import {buildAssistantReviewPacket,downloadAssistantReviewFile} from '@/lib/assistantReviewPacket';
import {canShowAssistantQa} from '@/lib/assistantQaVisibility';

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
 if(!response.ok){
  const detail=data?.detail??data?.error;
  const reason=typeof detail==='string'?detail:
   Array.isArray(detail)?detail.map(item=>item?.msg||item?.message||'Invalid field').join('; '):
   (detail&&typeof detail==='object'?(detail.message||JSON.stringify(detail)):'Conversation history unavailable');
  throw Error(response.status===401?'Your login session has expired. Sign in again.':reason);
 }
 return data;
}
export default function IntelligenceAssistant(){
 const {t}=useLanguage();
 const {access}=useOutletContext()||{};
 const canViewQa=canShowAssistantQa(access,{demo:!!window.__BAWASLU_DEMO_REPLICA__});
 const [qaOpen,setQaOpen]=useState(false);
 const showQa=canViewQa&&qaOpen;
 const starters=starterKeys.map(t);
 const initialQuery=new URLSearchParams(window.location.search).get('q')||'';
 const [question,setQuestion]=useState(initialQuery),[messages,setMessages]=useState([]);
 // Export only fresh answers generated in this authenticated page session.
 // Historical chat source access may have changed since the answer was saved.
 const [reviewableIndexes,setReviewableIndexes]=useState(()=>new Set());
 const [scoringPacket,setScoringPacket]=useState(null);
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
  setActive(null);setMessages([]);setReviewableIndexes(new Set());setScoringPacket(null);setQuestion('');setError('');setHistoryError('');
 }
 async function openThread(id){
  if(busy||historyBusy)return;
  setHistoryBusy(true);setHistoryError('');setError('');
  try{
   const thread=await historyRequest('/'+encodeURIComponent(id));
   setActive(thread.id);setMessages(thread.messages||[]);setReviewableIndexes(new Set());setScoringPacket(null);setQuestion('');
  }catch(e){setHistoryError(e.message)}
  finally{setHistoryBusy(false)}
 }
 async function removeThread(id){
  if(busy||historyBusy||!window.confirm('Delete this conversation history? Source intelligence records are not deleted.'))return;
  setHistoryBusy(true);setHistoryError('');
  try{
   await historyRequest('/'+encodeURIComponent(id),'DELETE');
   setThreads(old=>old.filter(x=>x.id!==id));
   if(activeIdRef.current===id){setActive(null);setMessages([]);setReviewableIndexes(new Set())}
  }catch(e){setHistoryError(e.message)}
  finally{setHistoryBusy(false)}
 }
 function scoreThisAnswer(index){
  try{
   if(!reviewableIndexes.has(index))
    throw Error('Only new answers from this authenticated session can be scored. Re-run older questions.');
   const answer=messages[index];
   const prompt=messages[index-1]?.role==='user'?messages[index-1].text:'';
   const version=document.querySelector('[data-build-version]')?.getAttribute('data-build-version')||'unknown';
   setScoringPacket(buildAssistantReviewPacket({question:prompt,answer,buildVersion:version}));
   setError('');
   document.querySelector('[data-testid="assistant-human-scoring"]')?.scrollIntoView({behavior:'smooth',block:'start'});
  }catch(e){setError(e?.message||'Could not open scoring for this answer.')}
 }
 function exportAnswerReview(index,format){
  try{
   if(!reviewableIndexes.has(index))
    throw new Error('For permission safety, only answers generated in this session can be exported. Re-run older questions to refresh evidence access.');
   const answer=messages[index];
   const originalQuestion=messages[index-1]?.role==='user'?messages[index-1].text:'';
   const buildVersion=document.querySelector('[data-build-version]')?.getAttribute('data-build-version')||'unknown';
   const packet=buildAssistantReviewPacket({
    question:originalQuestion,answer,buildVersion
   });
   downloadAssistantReviewFile(packet,format);
  }catch(e){setError(e?.message||'Review export could not be created.')}
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
   setReviewableIndexes(old=>new Set([...old,outgoing.length]));
   try{
    const title=String(messages[0]?.text||q).slice(0,120);
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
  {canViewQa&&<section data-testid="assistant-qa-tools" className="rounded-xl border border-[#e5e9ee] bg-white">
   <button type="button" data-testid="assistant-qa-tools-toggle" aria-expanded={qaOpen}
    className="flex w-full items-center justify-between gap-2 px-4 py-3 text-left text-xs font-semibold text-[#536578]"
    onClick={()=>setQaOpen(v=>!v)}>
    <span>Development QA tools (administrators)</span><span aria-hidden="true">{qaOpen?'Hide':'Show'}</span>
   </button>
   {showQa&&<div data-testid="assistant-qa-tools-content" className="space-y-3 border-t border-[#e5e9ee] p-3">
    <p className="text-xs leading-5 text-[#64748b]">Internal evaluation only. No official BAWASLU approval is implied, and preparing questions does not make a paid AI call.</p>
    <AssistantEvaluationSampler disabled={busy||historyBusy}
     onPrepare={prompt=>{setQuestion(prompt);setAnalysisMode('DATA');setError('')}}/>
    <AssistantHumanScoring incomingPacket={scoringPacket}/>
    <AssistantReviewConsolidation/>
   </div>}
  </section>}
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
        {m.grounding?.grounding_audit&&!showQa&&<div data-testid="assistant-source-caution"
          className="mt-3 rounded-lg border border-[#dce5ec] bg-white px-3 py-2 text-xs text-[#52657a]">
          <p>{(m.answer_language||'id')==='id'?'Sumber pendukung perlu diverifikasi petugas.':'Supporting sources require officer verification.'}</p>
          {m.grounding.grounding_audit.evidence_citation_coverage==='LEGAL_REFERENCE_NOT_CITED'&&
           <p data-testid="assistant-legal-source-missing" className="mt-1 font-medium text-[#91652e]">{(m.answer_language||'id')==='id'?'Belum ada halaman PDF hukum yang dikutip. Petugas harus memeriksa rujukan resmi sebelum menyimpulkan.':'No legal PDF page is cited. An officer must check the official reference before reaching a conclusion.'}</p>}
          {m.grounding.grounding_audit.legal_question&&m.grounding.grounding_audit.legal_source_review_state==='REVIEW_PENDING'&&
           <p data-testid="assistant-legal-reference-review-pending" className="mt-1 font-medium text-[#91652e]">{(m.answer_language||'id')==='id'?'Salah satu rujukan peraturan, SOP atau panduan yang dikutip belum ditelaah petugas. Pemeriksaan dokumen diperlukan sebelum rujukan ini digunakan untuk penilaian hukum.':'At least one cited regulation, SOP or guidance page is awaiting officer review. Document review is required before relying on it for legal assessment.'}</p>}
          {m.grounding.grounding_audit.legal_question&&(m.grounding.grounding_audit.cited_legal_reference_pages||0)>0&&
           <p data-testid="assistant-legal-version-unverified" className="mt-1 text-[#91652e]">{(m.answer_language||'id')==='id'?'Versi, perubahan, tanggal berlaku, dan kesesuaian jenis pemilihan dari rujukan hukum belum diverifikasi. Petugas perlu memeriksa naskah resmi.':'The legal reference version, amendments, effective date and election-type applicability have not been verified. An officer must check the official text.'}</p>}
          {(m.grounding.grounding_audit.legal_election_type_metadata_conflict_ids||[]).length>0&&
           <p data-testid="assistant-legal-metadata-scope-conflict" className="mt-1 font-medium text-[#91652e]">{(m.answer_language||'id')==='id'?'Jenis pemilihan yang dicatat pada metadata dokumen berbeda dengan pertanyaan. Periksa rujukan hukum resmi.':'Recorded document election type differs from the question. Check the official legal reference.'}</p>}
          {(m.grounding.grounding_audit.legal_election_type_title_conflict_ids||[]).length>0&&
           <p data-testid="assistant-legal-election-scope-mismatch" className="mt-1 font-medium text-[#91652e]">{(m.answer_language||'id')==='id'?'Jenis pemilihan pada judul salah satu rujukan mungkin tidak sesuai dengan pertanyaan. Periksa lingkup peraturannya.':'A cited legal document title may concern a different election type. Verify its scope before relying on it.'}</p>}
          {m.grounding.grounding_audit.evidence_citation_coverage==='LEGAL_REFERENCE_NONLEGAL_PDF_ONLY'&&
           <p data-testid="assistant-nonlegal-pdf-caution" className="mt-1 font-medium text-[#91652e]">{(m.answer_language||'id')==='id'?'Halaman PDF yang dikutip bukan berjenis peraturan, SOP atau panduan hukum. Petugas harus mencari rujukan resmi yang sesuai.':'The cited PDFs are not classified as regulations, SOPs or guidance. An officer must locate an appropriate official legal reference.'}</p>}
          {m.grounding.grounding_audit.evidence_citation_coverage==='SELECTED_EVIDENCE_NOT_CITED'&&
           <p data-testid="assistant-selected-sources-uncited" className="mt-1 text-[#91652e]">{(m.answer_language||'id')==='id'?'Bukti tersedia tetapi tidak dikutip dalam jawaban.':'Evidence was available but was not cited in the answer.'}</p>}
          {(m.grounding.grounding_audit.officer_review_steps||[]).length>0&&
           <details data-testid="assistant-officer-review-steps" className="mt-2">
             <summary className="cursor-pointer font-semibold text-[#52657a]">{(m.answer_language||'id')==='id'?'Langkah pemeriksaan petugas':'Officer review steps'} · {m.grounding.grounding_audit.officer_review_steps.length}</summary>
             <ol className="mt-2 list-decimal space-y-2 pl-5">
              {m.grounding.grounding_audit.officer_review_steps.map((step,j)=>{
               const id=(m.answer_language||'id')==='id';
               const labels={
                VERIFY_ORIGINAL_POST_CONTEXT:id?'Periksa postingan asli, konteks, dan waktu publikasi.':'Inspect the original post, context, and publication time.',
                TRACE_FORMAL_EVIDENCE_CHAIN:id?'Telusuri catatan intelijen formal, asal bukti dan jejak tinjauan petugas.':'Trace the formal intelligence record, source evidence and officer review history.',
                RECHECK_MISSING_OR_OMITTED_REFERENCES:id?'Periksa rujukan yang tidak tersedia atau terpotong.':'Recheck missing or omitted source references.',
                MATCH_CITED_LEGAL_PASSAGES:id?'Cocokkan setiap pasal dengan halaman PDF yang dirujuk.':'Match each legal article to its cited PDF page.',
                REQUEST_DOCUMENT_REVIEW:id?'Minta penelaahan dokumen yang belum ditinjau petugas.':'Request officer review of unreviewed documents.',
                VERIFY_ELECTION_TYPE_APPLICABILITY:id?'Periksa kecocokan jenis pemilihan antara pertanyaan dan naskah hukum resmi.':'Verify the election type and applicability against the official legal text.',
                LOCATE_AUTHORIZED_LEGAL_REFERENCE:id?'Cari dokumen hukum resmi yang dapat diakses sebelum menyimpulkan.':'Locate authorized official legal text before drawing conclusions.',
                VERIFY_OFFICIAL_LEGAL_OUTCOME:id?'Verifikasi putusan atau status hukum melalui catatan resmi.':'Verify any asserted legal outcome against official records.',
                CONFIRM_AUTHORITY_BEFORE_ANY_ACTION:id?'Pastikan fakta kasus, kewenangan, dan dasar hukum sebelum tindakan.':'Confirm case facts, authority, and law before any action.'
               };
               return <li key={step.code+'-'+j}><span>{labels[step.code]||step.code}</span>{step.source_ids?.length>0&&<span className="block text-[#718096]">{(id?'Rujukan ditampilkan: ':'Displayed references: ')+step.source_ids.join(', ')}</span>}</li>;
              })}
             </ol>
             <p className="mt-2 text-[#718096]">{(m.answer_language||'id')==='id'?'Daftar ini hanya panduan. Tidak ada tindakan atau persetujuan otomatis.':'Guidance only. No action or approval is performed automatically.'}</p>
           </details>}
          {(m.grounding.cited_count??0)===0&&(m.grounding.source_card_count??0)>0&&
           <p className="mt-1 text-[#91652e]">{(m.answer_language||'id')==='id'?'Kartu sumber hanya konteks, bukan bukti yang dikutip.':'Source cards are context, not cited evidence.'}</p>}
          {(m.grounding.grounding_audit.legal_review_reason_count||0)>1&&
           <p data-testid="assistant-combined-legal-review" className="mt-1 font-medium text-[#91652e]">{(m.answer_language||'id')==='id'?'Beberapa masalah independen memerlukan tinjauan petugas; sumber, kesimpulan hukum dan tindakan belum disahkan.':'Multiple independent issues require officer review; sources, legal conclusions and actions are not approved.'}</p>}
          {(m.grounding.grounding_audit.omitted_excess_citation_count||0)>0&&
           <p data-testid="assistant-citation-limit-caution" className="mt-1 text-[#91652e]">{(m.answer_language||'id')==='id'?'Beberapa kutipan melebihi batas 12 sumber unik dan telah dihilangkan. Periksa sumber yang tersisa.':'Some citations exceeded the 12-unique-source limit and were removed. Review the remaining references.'}</p>}
          {m.grounding.grounding_audit.legal_categorical_outcome_needs_officer_review&&
           <p data-testid="assistant-categorical-legal-caution" className="mt-1 text-[#91652e]">{(m.answer_language||'id')==='id'?'Jawaban menyatakan pelanggaran, kesalahan, atau sanksi sebagai sudah pasti. Periksa putusan dan sumber resmi sebelum bertindak.':'This answer presents a violation, guilt, or penalty as established. Verify official decisions and records before acting.'}</p>}
          {m.grounding.grounding_audit.legal_enforcement_recommendation_needs_officer_review&&
           <p data-testid="assistant-legal-enforcement-caution" className="mt-1 text-[#91652e]">{(m.answer_language||'id')==='id'?'Arahan penegakan atau sanksi dalam jawaban memerlukan penilaian petugas berwenang. Kutipan PDF tidak membuktikan kewenangan atau dasar hukum.':'An enforcement or penalty recommendation requires authorized officer review. PDF citations do not prove legal authority or applicability.'}</p>}
          {(m.grounding.grounding_audit.legal_article_claims_without_local_pdf_citation_count||0)>0&&
           <p data-testid="assistant-unattributed-article-caution" className="mt-1 text-[#91652e]">{(m.answer_language||'id')==='id'?'Ada pernyataan pasal tanpa kutipan halaman PDF pada kalimat yang sama. Periksa rujukannya.':'An article-level statement lacks a PDF page citation in the same sentence. Check its source.'}</p>}
          {m.grounding.grounding_audit.mixed_review_status_cited_pdf_pages&&
           <p data-testid="assistant-mixed-pdf-review-caution" className="mt-1 text-[#91652e]">{(m.answer_language||'id')==='id'?'Sebagian halaman PDF yang dikutip belum ditelaah petugas, meskipun halaman lain telah ditelaah.':'Some cited PDF pages have not been officer-reviewed, even though others have.'}</p>}
          {((m.grounding.grounding_audit.legal_article_numbers_not_found_in_cited_pdf||[]).length>0||
            (m.grounding.grounding_audit.legal_article_claim_citation_mismatch_count||0)>0)&&
           <p data-testid="assistant-legal-article-caution" className="mt-1 text-[#91652e]">{(m.answer_language||'id')==='id'?'Nomor pasal dalam jawaban tidak ditemukan pada kutipan halaman PDF yang dirujuk. Periksa naskah hukum resmi.':'An article number in this answer was not found in its cited PDF page excerpts. Verify the official legal text.'}</p>}
          {(m.grounding.grounding_audit.cited_unreviewed_pdf_pages||0)>0&&
           <p className="mt-1 text-[#91652e]">{(m.answer_language||'id')==='id'?'PDF yang dikutip belum ditinjau petugas dan keberlakuan hukumnya belum diverifikasi.':'Cited PDF is not officer-reviewed, and legal currentness is unverified.'}</p>}
         </div>}
         {showQa&&m.grounding?.grounding_audit&&<div data-testid="assistant-grounding-integrity" className="mt-3 rounded-lg border border-[#dce5ec] bg-white px-3 py-2 text-xs text-[#52657a]">
         <p className="font-semibold">{(m.answer_language||'id')==='id'?'Integritas rujukan jawaban':'Answer citation integrity'}</p>
         <p className="mt-1">{m.grounding.cited_count??0} {(m.answer_language||'id')==='id'?'ID sumber dikutip dalam jawaban':'source IDs cited in the answer'} · {m.grounding.source_card_count??0} {(m.answer_language||'id')==='id'?'kartu sumber tersedia':'source cards available'}.</p>
         {(m.grounding.cited_count??0)===0&&(m.grounding.source_card_count??0)>0&&
          <p className="mt-1 text-[#91652e]">{(m.answer_language||'id')==='id'?'Kartu sumber hanya konteks, bukan kutipan pendukung dari jawaban.':'Source cards are context only, not citations supporting the answer.'}</p>}
         {(m.grounding.grounding_audit.cited_unreviewed_pdf_pages||0)>0&&
          <p className="mt-1 text-[#91652e]">{(m.answer_language||'id')==='id'?'PDF yang dikutip belum ditelaah petugas; keberlakuan hukum belum diverifikasi.':'A cited PDF is not officer-reviewed; current legal force is unverified.'}</p>}
         <p className="mt-1">{(m.answer_language||'id')==='id'?'Pemeriksaan ini memvalidasi ID rujukan, bukan kebenaran klaim sumber.':'This check validates reference IDs, not the truth of source claims.'}</p>
        </div>}
        {showQa&&m.grounding?.answer_quality?.checks?.length>0&&
         <details data-testid="assistant-answer-quality" className="mt-2 rounded-lg border border-[#dce5ec] bg-white px-3 py-2 text-xs text-[#52657a]">
          <summary className="cursor-pointer font-semibold">{(m.answer_language||'id')==='id'?'Pemeriksaan kualitas otomatis':'Automated answer checks'} · {m.grounding.answer_quality.review_required_checks} {(m.answer_language||'id')==='id'?'perlu ditinjau':'require review'}</summary>
          <p className="mt-2 text-[#946b31]">{(m.answer_language||'id')==='id'?'Pemeriksaan berbasis aturan, bukan skor akurasi atau validasi manusia.':'Rule-based checks, not an accuracy score or human validation.'}</p>
          <div className="mt-2 space-y-1">{m.grounding.answer_quality.checks.map(check=>
           <p key={check.id} className="flex items-start justify-between gap-2"><span>{check.id.replace(/_/g,' ')}</span>
            <span className="font-semibold shrink-0">{check.status==='PASS'?'PASS':check.status==='REVIEW_REQUIRED'?'REVIEW REQUIRED':'N/A'}</span></p>)}</div>
          <p className="mt-2">{(m.answer_language||'id')==='id'?'Setiap kesimpulan hukum dan kebenaran bukti tetap memerlukan petugas yang berwenang.':'Source truth and legal conclusions still require an authorized officer.'}</p>
         </details>}
        {showQa&&m.grounding?.answer_quality?.checks?.length>0&&reviewableIndexes.has(i)&&<div data-testid="assistant-human-review-export" className="mt-3 rounded-lg border border-[#e6e0c9] bg-[#fffcf4] px-3 py-2 text-xs text-[#665b43]">
         <p className="font-semibold">{(m.answer_language||'id')==='id'?'Siapkan penilaian petugas':'Prepare human review'}</p>
         <p className="mt-1">{(m.answer_language||'id')==='id'
          ?'Unduhan manual ini memuat potongan bukti yang dapat Anda akses. Simpan dengan aman. Skor petugas belum diisi dan belum ada persetujuan.'
          :'Manual downloads contain evidence excerpts you can access. Store securely. Reviewer scores are blank and no approval has occurred.'}</p>
         <div className="mt-2 flex flex-wrap gap-2">
          <button type="button" onClick={()=>scoreThisAnswer(i)}
           data-testid="assistant-score-this-answer" className="intel-button text-xs">Score this answer</button>
          <button type="button" onClick={()=>exportAnswerReview(i,'json')} data-testid="assistant-review-json"
           className="intel-ghost text-xs"><Download size={13}/> {(m.answer_language||'id')==='id'?'Ekspor bukti penilaian (.json)':'Export review evidence (.json)'}</button>
          <button type="button" onClick={()=>exportAnswerReview(i,'csv')} data-testid="assistant-review-csv"
           className="intel-ghost text-xs"><Download size={13}/> {(m.answer_language||'id')==='id'?'Ekspor lembar skor kosong (.csv)':'Export blank scoring sheet (.csv)'}</button>
         </div>
        </div>}
        {m.response_profile!=='PDF_GUIDANCE'&&m.grounding?.supporting_count>0&&
         <p className="mt-4 text-xs text-[#64748b]">{m.grounding.supporting_count} {textFor(m.answer_language||'id',m.presentation_labels,'evidence_refs')} · {textFor(m.answer_language||'id',m.presentation_labels,'source_review_required')}</p>}
        {m.response_profile!=='PDF_GUIDANCE'&&<AssistantDetectedTags tags={m.detected_tags} language={m.answer_language||'id'} labels={m.presentation_labels}/>}
        {['CASE_REVIEW','CROSS_MODULE_REVIEW'].includes(m.response_profile)&&m.grounding?.formal_selected_count===0&&<p className="my-3 rounded-lg border border-amber-200 bg-amber-50 px-3 py-2 text-sm text-amber-900">Tidak ditemukan catatan Intelligence Inbox yang relevan dengan pertanyaan dalam cakupan akses ini. Bukti Social Listening tetap merupakan informasi awal yang perlu diverifikasi.</p>}
        {m.response_profile==='SOCIAL_ANALYSIS'&&<AssistantInsights snapshot={m.evidence_snapshot} grounding={m.grounding} language={m.answer_language||'id'} labels={m.presentation_labels}/>}
        {m.response_profile!=='PDF_GUIDANCE'&&<AssistantIntelligenceReport findings={m.analytical_findings} records={m.records} language={m.answer_language||'id'} labels={m.presentation_labels} compact={m.response_profile==='SOCIAL_ANALYSIS'}/>}
        <AssistantRecords records={m.records} featured={m.featured_sources} language={m.answer_language||'id'} labels={m.presentation_labels} compactPdf={m.response_profile==='PDF_GUIDANCE'} allowAssignments={m.response_profile==='ACTION_REQUEST'}/></>}
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
     <input aria-label={t('assistant_question_aria')} className="intel-input flex-1" maxLength={1000} placeholder={t('assistant_placeholder')} value={question} onChange={e=>setQuestion(e.target.value)}/>
     <button type="submit" className="intel-button" disabled={busy||historyBusy||!question.trim()}><Send size={16}/><span className="hidden sm:inline">{t('send')}</span></button>
    </form>
    <p className="text-xs text-[#8192a3]">AI menyiapkan analisis dan draf; petugas memilih, memeriksa, dan mengonfirmasi setiap tindakan resmi.</p>
   </div>
  </div>
 </div>;
}
