/** Structured findings are backend-authorized and linked to cited record IDs.
 * Never display a source card as independent proof of a claim.
 */
const sourceStatus={CONSULTED:'Consulted',NOT_SELECTED:'Not selected',
 SELECTED_NOT_CONSULTED:'Selected · not consulted'};
const basisStatus={FIXED_SAVED_SNAPSHOT:'Saved snapshot · not a live source check',
 LIVE_PUBLIC_LOOKUP:'Live when retrieved · not a continuing or independently verified feed',
 SIMULATED_DEMO:'Simulated demo content · not real-world evidence',
 NOT_CONSULTED:'No source consulted',NOT_SELECTED:'Not selected'};
export default function AssistantWorkflowEvidence({message,fresh=false}){
 const sources=Array.isArray(message?.source_consultation)?message.source_consultation:[];
 const findings=Array.isArray(message?.structured_findings)?message.structured_findings:[];
 const plan=Array.isArray(message?.decision_plan)?message.decision_plan:[];
 const isDraft=message?.draft_policy==='DRAFT_ONLY_STAFF_REVIEW_AND_SEND';
 if(!sources.length&&!findings.length&&!plan.length&&!isDraft)return null;
 return <div className="mt-4 space-y-3 border-t border-slate-200 pt-4 text-xs" data-testid="assistant-structured-workflow">
  <section className="rounded-lg border border-slate-200 bg-white p-3 space-y-2" data-testid="assistant-consulted-sources">
   <h3 className="font-semibold text-[#19364c]">Source consultation record</h3>
   {!fresh&&<p className="font-semibold text-amber-900">Historical answer snapshot. Access, source contents and currentness may have changed; rerun the question for fresh evidence before casework.</p>}
   <p className="text-slate-600">Only the sources actually retrieved or looked up for this answer are labeled consulted. Citation links remain separate from source availability.</p>
   <div className="grid gap-2 md:grid-cols-3">
    {sources.map(row=><div key={row.key} className="rounded-md border border-slate-200 bg-slate-50 p-3">
     <strong className="block">{row.label}</strong>
     <span className="mt-1 block">{sourceStatus[row.status]||row.status}</span>
     <span className="mt-1 block text-[11px] text-slate-600">{basisStatus[row.basis]||row.basis} · {row.selected_count??0} items</span>
     {row.warning&&<span className="mt-2 block text-[11px] text-amber-800">{row.warning}</span>}
     {(row.urls||[]).filter(url=>/^https:\/\/[^ ]+$/.test(url)).map(url=><a key={url} href={url} target="_blank" rel="noopener noreferrer" className="mt-1 block truncate text-teal-800 underline" title={url}>{url}</a>)}
    </div>)}
   </div>
   {window.__BAWASLU_DEMO_REPLICA__&&<p className="font-semibold text-amber-900">Simulated demo environment. Do not treat sample records as live or independently verified.</p>}
  </section>
  {findings.length>0&&<section className="rounded-lg border border-slate-200 bg-white p-3" data-testid="assistant-source-linked-findings">
   <h3 className="mb-2 font-semibold text-[#19364c]">Structured, source-linked findings</h3>
   <div className="space-y-2">{findings.map((f,i)=><div key={i} className="rounded-md border border-slate-100 p-3">
    <p className="leading-relaxed">{f.text}</p>
    <p className="mt-2 text-[11px] text-slate-600">{f.evidence_class?.replaceAll('_',' ')||'Analytical interpretation'} · {f.support_status?.replaceAll('_',' ')||'Not verified'}</p>
    <p className="mt-1 font-medium">Supporting citations: {(f.source_ids||[]).length?f.source_ids.map(x=>'['+x+']').join(' · '):'None verified in this answer'}</p>
   </div>)}</div>
   <p className="mt-2 text-[11px] text-slate-600">Source-linked does not mean the underlying allegation is authenticated. Officers must verify primary documents, date, location and jurisdiction.</p>
  </section>}
  {plan.length>0&&<section className="rounded-lg border border-slate-200 bg-white p-3" data-testid="assistant-management-decision-plan">
   <h3 className="mb-2 font-semibold text-[#19364c]">Proposed decision and review plan</h3>
   <div className="space-y-2">{plan.map((row,i)=><div key={i} className="rounded-md border border-slate-100 p-3">
    <p className="font-semibold">{i+1}. {row.milestone}</p>
    <p className="mt-1">Suggested owner role: {row.owner_role||'Requires management assignment'}</p>
    <p>Review point / decision gate: {row.review_point||'To be agreed by an authorized officer'}</p>
    <p>Deliverable: {row.expected_output||'Review findings'}</p>
    <p className="mt-1 text-[11px] text-slate-500">Supporting IDs: {(row.source_ids||[]).join(', ')||'No linked source IDs'} · Proposal only</p>
   </div>)}</div>
  </section>}
  {isDraft&&<div className="rounded-lg border border-amber-200 bg-amber-50 p-3 font-semibold text-amber-900" data-testid="assistant-draft-review-required">
   DRAFT ONLY · Executive summaries, memos and email replies are for authorized staff to verify, revise and send. No assignment, approval, message or legal determination was created.
  </div>}
 </div>;
}
