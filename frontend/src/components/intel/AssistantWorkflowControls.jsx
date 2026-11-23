import {Link} from 'react-router-dom';

export default function AssistantWorkflowControls({
 workspace,workflowMode,setWorkflowMode,sourceSelection,setSourceSelection,busy
}){
 const count=Object.values(sourceSelection||{}).filter(Boolean).length;
 return <section className="intel-card space-y-4 p-4 md:p-5" data-testid="assistant-workflow-mode-selector">
  <div className="flex flex-wrap items-center justify-between gap-2">
   <div><h2 className="font-semibold text-[#19364c]">AI research and decision support</h2>
    <p className="mt-1 text-xs text-slate-600">Web-first public research for timely BAWASLU decisions; add authorized SmartRadar evidence only when needed.</p>
   </div>
   <div className="flex flex-wrap gap-2 text-xs">
    <Link to="/management" className="intel-ghost">Management home</Link>
    <Link to="/assistant" className="intel-ghost">Operational assistant</Link>
   </div>
  </div>
  <div className="grid gap-2 sm:grid-cols-2" role="group" aria-label="Assistant workflow modes">
   {[
    ['RESEARCH','Research & Analysis','Investigate issues, compare evidence, identify contradictions and unresolved questions'],
    ['STRATEGY_DRAFTING','Strategy & Drafting','Compare oversight responses, propose owner roles and review points, draft management communications']
   ].map(([mode,label,description])=><button key={mode} type="button" disabled={busy}
    aria-pressed={workflowMode===mode} onClick={()=>setWorkflowMode(mode)}
    className={'rounded-lg border p-3 text-left '+(workflowMode===mode?'border-[#801b24] bg-[#fff5f4] text-[#801b24]':'border-slate-200 bg-white text-slate-700')}>
    <strong className="block text-sm">{label}</strong><span className="mt-1 block text-xs">{description}</span>
   </button>)}
  </div>
  <fieldset className="space-y-2" data-testid="assistant-authorized-source-selection">
   <legend className="text-sm font-semibold text-[#19364c]">Select the sources the assistant may consult</legend>
   <div className="grid gap-2 md:grid-cols-3">
    {[
     ['smartRadar','SmartRadar / saved BAWASLU intelligence','Optional private local context for explicitly requested records or stored metrics'],
     ['publicWeb','Public web / public social · recommended','Default live public research; attributable official/news sources, not a population-wide social crawl'],
     ['legalReferences','Official legal/reference sources','Authorized PDF/reference library; authenticity and currentness need separate verification'],
     ['attachments','Conversation attachments','Private scanned documents and public HTTPS links, confined to this conversation']
    ].map(([key,label,note])=><label key={key} className="flex gap-2 rounded-lg border border-slate-200 bg-white p-3 text-xs">
     <input type="checkbox" className="mt-1" checked={Boolean(sourceSelection[key])} disabled={busy}
       onChange={e=>setSourceSelection(old=>({...old,[key]:e.target.checked}))}/>
     <span><strong className="block text-slate-800">{label}</strong><span className="mt-1 block text-slate-600">{note}</span></span>
    </label>)}
   </div>
   {!count&&<p role="alert" className="text-xs font-semibold text-red-700">Choose at least one authorized source category.</p>}
   {sourceSelection.publicWeb&&<p className="text-xs text-amber-900">Live public web lookup may incur OpenAI search costs. Only your question—not saved private source passages—is sent to web search. Do not include confidential information in a public-search question.</p>}
  </fieldset>
  <p className="text-xs text-slate-600" data-testid="assistant-source-truthfulness-note">Public web is the default research source. Saved SmartRadar records are optional and never supplied to public web search. Only attributable retrieved links count as consulted; public coverage is not a population-wide sentiment survey. Legal findings and officer actions require authorization.</p>
  {workflowMode==='STRATEGY_DRAFTING'&&<p className="text-xs font-semibold text-amber-900">Drafts and proposed decisions are for authorized staff to review, revise and send. The assistant cannot issue a legal determination, assign an officer or send an email.</p>}
 </section>;
}
