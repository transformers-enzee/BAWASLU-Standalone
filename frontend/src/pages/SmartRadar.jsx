import { useEffect, useMemo, useState } from 'react';
import { useOutletContext } from 'react-router-dom';
import { Radar, X, Bell, ArrowLeft, CheckCircle, AlertTriangle, ExternalLink } from 'lucide-react';
const token=()=>window.localStorage.getItem('bawaslu_access_token')||'';
async function call(path,body){
 const r=await fetch('/api/smart-radar'+path,{cache:'no-store',method:body?'POST':'GET',headers:{Authorization:'Bearer '+token(),...(body?{'Content-Type':'application/json'}:{})},...(body?{body:JSON.stringify(body)}:{})});
 const v=await r.json().catch(()=>({}));if(!r.ok)throw Error(v.detail||'Server error');return v;
}
const players=[['attention','Needs Attention'],['concerns','Public Concerns'],['narratives','Emerging Narratives'],['validated','Validated Intelligence']];
const topics=['All Topics','Allegations / Violations','Citizen Reports / Public Concerns','Digital Risks / Information','Disputes / Legal','Election Operations','Participatory Oversight','Voter Register / PDPB'];
function dateValue(s){const t=Date.parse(s||'');return Number.isFinite(t)?t:0}
const inputClass='border border-slate-200 rounded-lg px-3 py-2 text-sm bg-white w-full';
const btn='rounded-lg px-3 py-2 text-sm border border-slate-200 bg-white hover:bg-slate-50';
const primary='rounded-lg px-3 py-2 text-sm bg-[#147968] text-white hover:bg-[#106754]';
export default function SmartRadar(){
 const {access}=useOutletContext();
 const [data,setData]=useState(null),[loading,setLoading]=useState(true),[error,setError]=useState('');
 const [processing,setProcessing]=useState(null),[running,setRunning]=useState(false);
 const [perspective,setPerspective]=useState('operations'),[topic,setTopic]=useState('All Topics'),[period,setPeriod]=useState('historical');
 const [panel,setPanel]=useState(null),[deskTab,setDeskTab]=useState('review'),[notice,setNotice]=useState(true),[expanded,setExpanded]=useState(false);
 const [selected,setSelected]=useState(null),[detailLoading,setDetailLoading]=useState(false),[history,setHistory]=useState(null),[note,setNote]=useState(''),[followup,setFollowup]=useState('');
 const [confirm,setConfirm]=useState(null),[saving,setSaving]=useState(false),[toast,setToast]=useState('');
 const reload=()=>call('/dashboard').then(setData);
 const refreshProcessing=()=>call('/processing-status').then(setProcessing).catch(()=>setProcessing(null));
 const runPilot=async()=>{setRunning(true);try{const result=await call('/process-batch',{limit:5});await Promise.all([reload(),refreshProcessing()]);setToast(result.failed?.length?'AI processing stopped: '+result.failed[0].reason:result.processed.length+' posts assessed and saved');}catch(e){setError(e.message)}finally{setRunning(false)}};
 useEffect(()=>{reload().catch(e=>setError(e.message)).finally(()=>setLoading(false));if(access?.role==='National Administrator')refreshProcessing()},[access?.role]);
 const findings=data?.findings||[];
 const filtered=useMemo(()=>findings.filter(f=>{
  if(f.perspective!==perspective)return false;
  if(topic!=='All Topics'&&!f.topics.includes(topic))return false;
  if(period!=='historical'&&dateValue(f.published_at)<Date.now()-Number(period)*86400000)return false;
  return true;
 }),[findings,perspective,topic,period]);
 const needs=filtered.filter(f=>f.status==='pending').sort((a,b)=>(b.priority_score??-1)-(a.priority_score??-1));
 const inPlayer=k=>k==='validated'?filtered.filter(f=>f.human_reviewed):k==='attention'?needs:filtered.filter(f=>f.player===k);
 const due=f=>f.next_followup&&dateValue(f.next_followup)<=Date.now();
 const actionCount=findings.filter(f=>f.status==='pending'||(f.status==='investigating'&&due(f))).length;
 const openFinding=async f=>{
  setSelected(null);setDetailLoading(true);setHistory(null);setNote('');
  setFollowup(f.next_followup||'');setPanel('finding');
  try{setSelected(await call('/finding/'+encodeURIComponent(f.id)))}
  catch(e){setError(e.message);setPanel(null)}
  finally{setDetailLoading(false)}
 };
 const doAction=async()=>{if(!confirm||!selected)return;setSaving(true);try{
   await call('/decision',{finding_id:selected.id,action:confirm,note,next_followup:followup||null});
   await reload();setPanel(null);setSelected(null);setConfirm(null);setToast('Officer decision saved');setTimeout(()=>setToast(''),4500);
  }catch(e){setError(e.message);setConfirm(null)}finally{setSaving(false)}};
 const options=selected?(selected.status==='pending'?[['close','Close'],['investigate','Investigate'],['monitor','Monitor']]:
 selected.status==='investigating'?[['update','Save — Continue Investigating'],['monitor','Return to Monitoring'],['close','Finish — Close'],['escalate','Finish — Escalated to BAWASLU']]:
 selected.status==='monitoring'?[['investigate','Investigate'],['close','Stop Monitoring']]:
 selected.status==='closed'||selected.status==='escalated'?[['reopen','Reopen Finding']]:
 [['queue','Send to Review']]):[];
 const dated=filtered.filter(f=>f.published_at).sort((a,b)=>dateValue(a.published_at)-dateValue(b.published_at));
 const byDay={};dated.forEach(f=>{const d=f.published_at.slice(0,10);byDay[d]=(byDay[d]||0)+f.supporting_posts});
 const max=Math.max(1,...Object.values(byDay));
 const mentions=(data?.candidate_mentions||[]).slice(0,10);
 const maxMention=Math.max(1,...mentions.map(x=>x[1]));
 const categories=topics.slice(1).map(t=>[t,filtered.filter(f=>f.topics.includes(t)).length]).filter(x=>x[1]);
 const canReview=access?.permissions?.human_validation===true;
 if(loading)return <p className="p-6 text-sm text-slate-500">Loading Smart Radar source data...</p>;
 if(error&&!data)return <p role="alert" className="p-5 text-red-700">{error}</p>;
 return <div className="space-y-5 max-w-[1370px] mx-auto">
  <div className="rounded-2xl p-6 bg-gradient-to-r from-[#18344c] to-[#167561] text-white flex items-center justify-between gap-5">
   <div><p className="text-[11px] uppercase tracking-[.2em] opacity-75">BAWASLU · Intelligence Command Center</p><h1 className="text-3xl font-bold mt-1 flex items-center gap-2"><Radar/> Smart Radar</h1><p className="text-sm opacity-85 mt-1">Evidence-linked, preliminary intelligence from the staging pilot</p></div>
   <button className="bg-white/15 border border-white/30 rounded-xl px-4 py-3 whitespace-nowrap" onClick={()=>setPanel('desk')}>Action Desk {actionCount>0&&<b className="rounded-full bg-red-600 px-2 py-1 ml-1 text-xs">{actionCount}</b>}</button>
  </div>
  <div className="grid md:grid-cols-4 gap-3">
   <div className="md:col-span-2"><label className="text-xs font-bold">Intelligence Perspective</label><div className="flex gap-1 p-1 bg-slate-100 rounded-lg mt-1">{[['operations','Electoral Operations'],['reputation','BAWASLU Reputation']].map(([k,l])=><button key={k} className={'flex-1 rounded-md px-2 py-2 text-xs font-semibold '+(perspective===k?'bg-[#167968] text-white':'text-slate-600')} onClick={()=>setPerspective(k)}>{l}</button>)}</div></div>
   <div><label className="text-xs font-bold">Jurisdiction</label><select disabled className={inputClass+' mt-1'}><option>Indonesia — National (pilot)</option></select></div>
   <div><label className="text-xs font-bold">Period</label><select value={period} onChange={e=>setPeriod(e.target.value)} className={inputClass+' mt-1'}><option value="historical">Pilot historical period (all 109)</option><option value="7">Last 7 Days</option><option value="30">Last 30 Days</option></select></div>
   <div className="md:col-span-4"><label className="text-xs font-bold">Intelligence Topic</label><select className={inputClass+' mt-1'} value={topic} onChange={e=>setTopic(e.target.value)}>{topics.map(t=><option key={t}>{t}</option>)}</select></div>
  </div>
  {notice&&<div className="rounded-lg border-l-4 border-[#16886e] border bg-[#f1faf6] p-3 flex items-start gap-3"><Bell className="shrink-0 text-[#147968]" size={18}/><div className="flex-1"><b className="text-sm">Welcome Back</b><p className="text-xs text-slate-500">Historical pilot data · No verified personal last-visit baseline</p><div className="flex flex-wrap gap-4 my-2 text-xs"><span><b>—</b> New Issues</span><span><b>—</b> Important Updates</span><span><b>{actionCount}</b> Follow-ups / Reviews Due</span><span><b>—</b> New Narratives</span></div><p className="text-xs">Since your last visit, new allegations and concerns were identified. Some require a decision; others are for awareness only.</p>{expanded&&<p className="text-xs mt-2 text-slate-600">Exact since-last-visit counts will become available after account-specific visit tracking and incremental ingestion are enabled.</p>}</div><button aria-label="Details" className="text-xs underline" onClick={()=>setExpanded(!expanded)}>{expanded?'Less':'Details'}</button><button aria-label="Dismiss notification" onClick={()=>setNotice(false)}><X size={17}/></button></div>}
  {processing&&<div className="rounded-xl border border-amber-200 bg-amber-50 p-4"><div className="flex flex-wrap justify-between gap-3 items-center"><div><b className="text-sm">Phase 3 AI processing · Administrator</b><p className="text-xs text-amber-800 mt-1">{processing.assessed} / {processing.sources} posts assessed and saved · {processing.input_tokens} input tokens · {processing.output_tokens} output tokens</p><p className="text-xs text-slate-500">Only runs when clicked. Requires SMART_RADAR_PILOT_AI_ENABLED=true, OPENAI_API_KEY and SMART_RADAR_PILOT_MODEL on the staging backend.</p></div><button className={primary} disabled={running||processing.assessed>=processing.sources} onClick={runPilot}>{running?"Processing...":"Assess next 5 posts"}</button></div></div>}
  <div className="border border-slate-200 rounded-xl p-5"><h2 className="font-semibold">✦ Executive Briefing</h2><p className="text-sm text-slate-600 mt-2">{filtered.length} preliminary discussion groups are visible in this filtered view, supported by {filtered.reduce((n,f)=>n+f.supporting_posts,0)} original source posts. These are exploratory groupings, not verified incidents or AI-reviewed allegations. Review linked evidence before taking action.</p><p className="text-xs text-amber-700 mt-2">{data?.disclaimer}</p></div>
  <div className="grid grid-cols-2 lg:grid-cols-4 gap-3">{[[filtered.length,'Preliminary Groups'],[filtered.reduce((n,f)=>n+f.supporting_posts,0),'Supporting Posts'],[needs.length,'Needs Attention (Scored)'],[filtered.filter(f=>f.human_reviewed).length,'Reviewed Issues']].map(([n,l])=><div key={l} className="border rounded-xl p-4 bg-white"><b className="text-2xl">{n}</b><p className="text-xs text-slate-500 mt-1">{l}</p></div>)}</div>
  <div className="flex justify-between items-end"><h2 className="font-semibold text-lg">Four Intelligence Players</h2><span className="text-xs text-slate-500">Click any player for details</span></div>
  <div className="grid lg:grid-cols-2 gap-4">{players.map(([key,name])=>{const group=inPlayer(key);return <button key={key} onClick={()=>setPanel(key)} className="text-left border border-slate-200 hover:border-[#14816e] hover:shadow-md rounded-xl p-5 bg-white min-h-[230px] flex flex-col">
    <span className="text-[#16816e] text-xl">{key==='attention'?'⚑':key==='validated'?'✓':key==='concerns'?'◉':'↗'}</span><b className="text-lg mt-2">{name}</b><span className="text-xs text-[#147968] mt-2">{group.length} {key==='validated'?'Reviewed Issues':key==='narratives'?'Narratives Identified':'Issues Identified'} · {group.reduce((n,f)=>n+f.supporting_posts,0)} Supporting Posts</span><p className="text-sm text-slate-600 mt-3 flex-1">{group.length?group.slice(0,2).map(f=>f.title).join(' · ')+'. These groupings and underlying claims require independent assessment.':key==='attention'?'No AI-prioritized findings yet. Scoring and officer triage are not complete.':key==='validated'?'No human-reviewed findings yet.':'No matching groups for this selection.'}</p><span className="text-xs font-semibold text-[#147968] mt-3 pt-3 border-t">View intelligence and original sources →</span>
   </button>})}</div>
  <div className="grid lg:grid-cols-2 gap-4">
   <div className="border rounded-xl bg-white p-5"><h3 className="font-semibold">Candidate Mention Ranking</h3><p className="text-xs text-slate-500">Raw source-post mentions only — not wrongdoing or a validated watchlist</p>{mentions.map(([name,n])=><div key={name} className="text-xs mt-3"><div className="flex justify-between"><span>{name}</span><b>{n}</b></div><div className="bg-slate-100 rounded-full h-2 mt-1"><div className="bg-[#1d8d79] h-2 rounded-full" style={{width:100*n/maxMention+'%'}}/></div></div>)}</div>
   <div className="border rounded-xl bg-white p-5"><h3 className="font-semibold">Priority Candidate Watchlist</h3><p className="text-xs text-slate-500 mt-2">Not populated: priority associations require evidence-linked AI assessment and QC. Popularity does not imply misconduct.</p><div className="mt-7 border-t pt-4"><h3 className="font-semibold">Topic Distribution</h3>{categories.map(([cat,n])=><div key={cat} className="flex justify-between text-xs py-2 border-b border-slate-100"><span>{cat}</span><b>{n}</b></div>)}</div></div>
   <div className="border rounded-xl bg-white p-5"><h3 className="font-semibold">Source Activity</h3><p className="text-xs text-slate-500">Published dates from pilot posts (not new-ingestion timestamps)</p><div className="flex items-end gap-1 h-28 mt-4 overflow-x-auto">{Object.entries(byDay).slice(-35).map(([day,n])=><div key={day} title={day+': '+n+' posts'} style={{height:Math.max(3,n/max*95)+'%'}} className="bg-[#238977] rounded-t min-w-[7px] flex-1"/>)}</div></div>
   <div className="border rounded-xl bg-white p-5"><h3 className="font-semibold">Geographic Intelligence</h3><p className="text-sm text-slate-600 mt-4">Incident geography is unresolved in this source-only pilot. We must not infer an incident's location from a politician's constituency or account location.</p><h3 className="font-semibold mt-7">Source Platforms</h3>{Object.entries(data?.platform_counts||{}).map(([p,n])=><div key={p} className="flex justify-between text-xs py-1"><span>{p}</span><b>{n}</b></div>)}</div>
  </div>
  <div className="border rounded-xl bg-white p-5"><h3 className="font-semibold">Strategic Insights</h3><p className="text-sm text-slate-600 mt-2">Recommended next step: validate source and grouping quality, then run the agreed AI relevance and priority pipeline before producing officer-ready recommendations or SWOT.</p></div>
  {toast&&<div className="fixed bottom-5 left-1/2 -translate-x-1/2 bg-[#145343] text-white text-sm rounded-lg px-5 py-3 z-[90]">{toast}</div>}
  {error&&data&&<div role="alert" className="fixed bottom-5 right-5 bg-red-100 text-red-900 border border-red-300 rounded-lg p-3 z-[90] max-w-sm"><button className="float-right ml-3" onClick={()=>setError('')}>×</button>{error}</div>}
  {panel&&<div className="fixed inset-0 z-[70] bg-slate-900/60 flex justify-end" onMouseDown={e=>{if(e.target===e.currentTarget)setPanel(null)}}>
    <div role="dialog" aria-modal="true" className="w-full max-w-xl h-full overflow-y-auto bg-white p-5 shadow-xl">
    <div className="flex justify-between items-center gap-3 mb-5"><h2 className="font-bold text-xl">{panel==='desk'?'Action Desk':panel==='finding'?'Finding Details':players.find(p=>p[0]===panel)?.[1]}</h2><button onClick={()=>setPanel(null)} className={btn}><X size={17}/></button></div>
    {panel==='desk'&&<><p className="text-sm text-slate-500 mb-4">BAWASLU officer homework, separate from technical QC.</p><div className="flex gap-2 mb-4">{[['review','To Review'],['investigating','Investigating'],['monitoring','Monitoring']].map(([k,l])=><button key={k} className={deskTab===k?primary:btn} onClick={()=>setDeskTab(k)}>{l}</button>)}</div>{findings.filter(f=>deskTab==='review'?f.status==='pending':f.status===deskTab).map(f=><button key={f.id} onClick={()=>openFinding(f)} className="border w-full rounded-lg p-3 text-left mb-2 hover:border-[#167968]"><b>{f.title}</b><p className="text-xs text-slate-500 mt-1">{f.perspective} · {f.status} · {f.supporting_posts} posts</p></button>)}{!findings.some(f=>deskTab==='review'?f.status==='pending':f.status===deskTab)&&<p className="text-sm text-slate-500">No assigned findings in this section.</p>}</>}
    {players.some(p=>p[0]===panel)&&<><p className="text-xs text-amber-700 mb-3">Preliminary grouping. Priority labels await AI scoring. Opening evidence does not constitute officer review.</p>{inPlayer(panel).map(f=><button key={f.id} onClick={()=>openFinding(f)} className="border block w-full text-left rounded-lg p-4 mb-3 hover:border-[#167968]"><div className="flex justify-between gap-3"><b>{f.title}</b><span className="text-xs whitespace-nowrap text-[#147968]">{f.priority_label}</span></div><p className="text-sm text-slate-600 mt-2">{f.summary}</p><p className="text-xs text-slate-500 mt-2">{f.supporting_posts} Supporting Posts · {f.status}</p></button>)}{!inPlayer(panel).length&&<p className="text-sm text-slate-500">No findings in the current selection.</p>}</>}
    {panel==='finding'&&detailLoading&&<p className="text-sm text-slate-500">Loading source evidence...</p>}
    {panel==='finding'&&selected&&<><button className={btn} onClick={()=>setPanel('desk')}><ArrowLeft size={14} className="inline"/> Back to Action Desk</button><h3 className="text-lg font-bold mt-4">{selected.title}</h3><div className="flex flex-wrap gap-2 my-3"><span className="bg-slate-100 px-2 py-1 text-xs rounded-full">{selected.status}</span><span className="bg-amber-50 text-amber-800 px-2 py-1 text-xs rounded-full">{selected.priority_label}</span>{selected.topics.map(t=><span key={t} className="bg-slate-100 px-2 py-1 text-xs rounded-full">{t}</span>)}</div><p className="text-sm text-slate-600">{selected.summary}</p><h4 className="font-semibold mt-5">Original Supporting Posts ({selected.posts.length})</h4>{selected.posts.map(p=><div key={p.pilot_post_id} className="border rounded-lg p-3 my-3"><p className="text-xs text-slate-500">{p.pilot_post_id} · {p.platform} · {p.published_at_raw} · {p.account_raw}</p><p className="text-sm whitespace-pre-wrap my-2">{p.message_original}</p><a href={p.source_url} target="_blank" rel="noopener noreferrer" className="text-[#147968] text-xs underline">View original source <ExternalLink className="inline" size={12}/></a></div>)}
    <button className={btn+' mt-3 w-full'} onClick={async()=>{if(history){setHistory(null);return}try{setHistory((await call('/history/'+encodeURIComponent(selected.id))).events)}catch(e){setError(e.message)}}}>Previous Reviews & Updates {history?'▲':'▼'}</button>{history&&<div className="mt-3">{history.length?history.map((h,i)=><div key={i} className="border-b py-2 text-xs"><b>{h.action}</b><span className="text-slate-400 ml-2">{h.created_at}</span><p>{h.note}</p></div>):<p className="text-xs text-slate-500">No recorded officer reviews yet.</p>}</div>}
    {canReview&&<div className="mt-6 border-t pt-4"><label className="text-sm font-semibold">Officer note {['escalated','closed'].includes(selected.status)?'(required when reopening)':''}</label><textarea className={inputClass+' mt-1 min-h-24'} value={note} onChange={e=>setNote(e.target.value)} placeholder="Short evidence-grounded note or reference"/>{selected.status==='investigating'&&<div className="mt-3"><label className="text-sm font-semibold">Optional next follow-up date</label><input className={inputClass} type="date" value={followup} onChange={e=>setFollowup(e.target.value)}/></div>}<div className="flex flex-wrap gap-2 mt-4">{options.map(([k,label])=><button key={k} className={primary} onClick={()=>{if(['reopen','escalate'].includes(k)&&!note.trim()){setError('A short note is required for this action');return}setConfirm(k)}}>{label}</button>)}</div><p className="text-xs text-slate-500 mt-2">Officer action only. Technical QC is not performed here.</p></div>}
    </>}
   </div>
  </div>}
  {confirm&&<div className="fixed inset-0 z-[80] flex items-center justify-center p-5 bg-slate-950/70"><div role="alertdialog" aria-modal="true" className="bg-white rounded-xl p-6 w-full max-w-md"><h3 className="text-lg font-bold">Confirm officer decision</h3><p className="text-sm mt-2">Are you sure you want to {confirm==='update'?'save and continue investigating':confirm==='escalate'?'finish and record escalation to BAWASLU':confirm==='queue'?'send this preliminary group for officer review':confirm} this finding?</p><div className="flex justify-end gap-2 mt-5"><button className={btn} disabled={saving} onClick={()=>setConfirm(null)}>Cancel</button><button className={primary} disabled={saving} onClick={doAction}>{saving?'Saving...':'Yes, Confirm'}</button></div></div></div>}
 </div>
}
