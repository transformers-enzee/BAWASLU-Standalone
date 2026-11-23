import {useState} from 'react';

/** Proposed officer work only. The component cannot assign cases, send messages or refer matters. */
const readableUrl=(value,allow)=>{
 try{
  const u=new URL(value);
  return u.protocol==='https:'&&!u.username&&!u.password&&allow.includes(u.href)?u.href:null;
 }catch{return null;}
};
function exportReviewPacket(question,message){
 const decision=message?.officer_decision||{};
 const plan=Array.isArray(message?.decision_plan)?message.decision_plan:[];
 const packet={
  type:'BAWASLU_REVIEW_DRAFT',status:'PROPOSED_ONLY_NO_CASE_OR_APPROVAL',
  question:String(question||'').slice(0,1000),
  answer:String(message?.text||'').slice(0,5100),
  retrieved_at:message?.grounding?.retrieved_at||null,
  institutional_relevance:decision.relevance||'UNRESOLVED',
  institutional_implication:decision.institutional_implication||'',
  recommended_decision:decision.recommended_decision||'',
  legal_review:decision.legal_review||null,
  proposed_actions:plan.slice(0,3),
  source_claims:(decision.claims||[]).slice(0,5),
  source_consultation:(message?.source_consultation||[]).slice(0,4),
  warning:'This is an unapproved working packet. Verify sources, authority, jurisdiction and evidence before any official action.'
 };
 const blob=new Blob([JSON.stringify(packet,null,2)],{type:'application/json'});
 const url=URL.createObjectURL(blob);
 try{
  const link=document.createElement('a');link.href=url;link.download='bawaslu-officer-review-draft.json';
  document.body.append(link);link.click();link.remove();
 }finally{URL.revokeObjectURL(url);}
}
export default function AssistantOfficerDecisionPanel({message,question='',fresh=false,onDraftMemo}){
 const [notice,setNotice]=useState('');
 const decision=message?.officer_decision||null;
 const plan=Array.isArray(message?.decision_plan)?message.decision_plan.slice(0,3):[];
 if(!decision&&!plan.length)return null;
 const id=message?.answer_language==='id';
 const web=message?.response_profile==='WEB_RESEARCH';
 const legal=decision?.legal_review||null;
 const noNexus=decision?.relevance==='NO_ESTABLISHED_NEXUS';
 const allow=(decision?.consulted_urls||[]).filter(x=>typeof x==='string');
 const cardPlan=web?plan:plan.slice(0,1); // Existing saved-data answers already contain officer steps in prose.
 async function copyPlan(){
  const text=cardPlan.map((a,i)=>[
   (i+1)+'. '+a.milestone,
   (id?'Peran peninjau: ':'Reviewing role: ')+a.owner_role,
   (id?'Bukti: ':'Evidence: ')+(a.required_evidence||'To verify'),
   (id?'Hasil: ':'Deliverable: ')+a.expected_output,
   (id?'Pemicu tinjauan: ':'Review gate: ')+a.review_point
  ].join('\n')).join('\n\n');
  try{await navigator.clipboard.writeText(text);setNotice(id?'Rencana disalin.':'Plan copied.');}
  catch{setNotice(id?'Penyalinan tidak tersedia.':'Copy unavailable in this browser.');}
 }
 return <section data-testid="assistant-officer-decision" className="mt-3 space-y-3 rounded-xl border border-[#d4dfe7] bg-white p-4 text-sm" data-i18n-exempt>
  <div className="flex flex-wrap items-center justify-between gap-2">
   <h3 className="font-bold text-[#801b24]">{id?'Tindak lanjut untuk BAWASLU':'What BAWASLU should do next'}</h3>
   <span className="rounded-full bg-slate-100 px-2 py-1 text-[11px] font-semibold text-slate-600">{id?'Usulan · perlu persetujuan petugas':'Proposed · officer review required'}</span>
  </div>
  {decision?.recommended_decision&&<p data-testid="assistant-recommended-decision" className="font-semibold text-slate-800">{decision.recommended_decision}</p>}
  {decision?.institutional_implication&&<p className="leading-relaxed text-slate-700"><strong>{id?'Dampak pada BAWASLU: ':'Institutional significance: '}</strong>{decision.institutional_implication}</p>}
  {noNexus&&<p data-testid="assistant-no-nexus" className="rounded-md bg-slate-50 px-3 py-2 text-slate-700">{id?'Belum ada dasar tindakan formal BAWASLU. Periksa hanya jika bukti baru menunjukkan kaitan kewenangan.':'No formal BAWASLU action is established. Reassess only if new evidence demonstrates a lawful oversight nexus.'}</p>}
  {decision?.status==='ACTION_SYNTHESIS_UNAVAILABLE'&&<p role="status" className="text-amber-800">{id?'Sintesis tindak lanjut belum tervalidasi. Rencana di bawah adalah pemeriksaan awal, bukan temuan.':'Action synthesis was unavailable. The step below is preliminary verification, not a finding.'}</p>}
  {cardPlan.length>0?<div className="space-y-2" data-testid="assistant-officer-action-cards">
   {cardPlan.map((row,i)=><div key={i} className="rounded-lg border border-slate-200 bg-slate-50 p-3">
    <p className="font-semibold text-[#19364c]">{i+1}. {row.milestone}</p>
    <dl className="mt-2 grid grid-cols-1 gap-x-3 gap-y-1 text-xs sm:grid-cols-[120px_1fr]">
     <dt className="font-medium text-slate-500">{id?'Penanggung jawab':'Reviewing role'}</dt><dd>{row.owner_role||'Authorized reviewer'}</dd>
     <dt className="font-medium text-slate-500">{id?'Bukti diperlukan':'Evidence to obtain'}</dt><dd>{row.required_evidence||'Source and applicability verification needed'}</dd>
     <dt className="font-medium text-slate-500">{id?'Hasil kerja':'Deliverable'}</dt><dd>{row.expected_output||'Review note'}</dd>
     <dt className="font-medium text-slate-500">{id?'Pemicu keputusan':'Review / closure gate'}</dt><dd>{row.review_point||'Authorized human review before any formal step'}</dd>
    </dl>
    {web&&row.source_urls?.length>0&&<div className="mt-2 flex flex-wrap gap-2 text-xs">{row.source_urls.map(url=>{
     const href=readableUrl(url,allow);
     return href?<a key={url} href={href} target="_blank" rel="noopener noreferrer" className="text-teal-800 underline">{id?'Rujukan pendukung':'Supporting source'}</a>:null;
    })}</div>}
   </div>)}
  </div>:<p className="text-slate-600">{id?'Tidak ada penugasan formal yang dibenarkan oleh bukti saat ini.':'The available evidence does not justify a proposed formal task.'}</p>}
  {legal&&<details data-testid="assistant-legal-jurisdiction" className="rounded-lg border border-slate-200 p-3 text-xs">
   <summary className="cursor-pointer font-semibold text-[#19364c]">{id?'Batas kewenangan, hukum dan regulasi platform':'Legal, jurisdiction and platform-regulation review'}</summary>
   <div className="mt-2 space-y-2 leading-relaxed">
    {legal.domain&&<p><strong>{id?'Ranah hukum: ':'Legal domain: '}</strong>{legal.domain}</p>}
    {legal.competent_authority&&<p><strong>{id?'Lembaga berwenang: ':'Competent institution: '}</strong>{legal.competent_authority}</p>}
    {legal.rule_reference&&<p><strong>{id?'Rujukan yang perlu ditinjau: ':'Provision to review: '}</strong>{legal.rule_reference}</p>}
    {legal.applicability&&<p><strong>{id?'Penerapan: ':'Applicability: '}</strong>{legal.applicability}</p>}
    {legal.verification_needed&&<p><strong>{id?'Belum terverifikasi: ':'Needs verification: '}</strong>{legal.verification_needed}</p>}
    <p className="font-medium text-amber-800">{id?'Kecocokan aturan dan kewenangan belum disahkan petugas.':'Legal applicability and authority have not been officer-verified.'}</p>
   </div>
  </details>}
  {fresh&&cardPlan.length>0&&<div className="flex flex-wrap gap-2">
   <button type="button" onClick={copyPlan} data-testid="assistant-copy-officer-plan" className="rounded-lg border border-[#dce4eb] px-3 py-2 text-xs font-semibold text-[#19364c] hover:bg-slate-50">{id?'Salin rencana':'Copy action plan'}</button>
   <button type="button" onClick={()=>{try{exportReviewPacket(question,message);setNotice(id?'Draf laporan pemeriksaan diunduh.':'Review draft downloaded.');}catch{setNotice(id?'Gagal menyiapkan berkas.':'Could not prepare packet.');}}} data-testid="assistant-download-review-packet" className="rounded-lg border border-[#dce4eb] px-3 py-2 text-xs font-semibold text-[#19364c] hover:bg-slate-50">{id?'Unduh paket pemeriksaan (.json)':'Download review packet (.json)'}</button>
   {typeof onDraftMemo==='function'&&<button type="button" data-testid="assistant-prepare-leadership-memo" onClick={onDraftMemo} className="rounded-lg bg-[#801b24] px-3 py-2 text-xs font-semibold text-white hover:bg-[#a52a2f]">{id?'Susun memo pimpinan':'Draft leadership memo'}</button>}
  </div>}
  {notice&&<p role="status" className="text-xs text-slate-600">{notice}</p>}
  {!fresh&&<p className="text-xs text-amber-800">{id?'Snapshot historis: pemeriksaan baru diperlukan sebelum digunakan sebagai dasar tindakan.':'Historical snapshot: rerun source verification before using this for a new official action.'}</p>}
  <p className="text-[11px] text-slate-500">{id?'Semua rencana merupakan saran. Tidak ada penugasan, pengaduan, penindakan atau komunikasi yang dijalankan otomatis.':'All plans are suggestions. No assignment, filing, enforcement or communication is executed automatically.'}</p>
 </section>;
}
