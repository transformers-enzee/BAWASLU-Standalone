/** Approved Smart Radar V6.2 pilot, plus a live Inbox evidence feed.
 * Only explicit campaign IDs are queried. Never assume old Radar pilot IDs
 * correspond to Social Listening source IDs.
 */
import {useEffect,useState} from 'react';
import {useSearchParams} from 'react-router-dom';

export default function SmartRadar(){
 const [params]=useSearchParams();
 const campaignId=params.get('campaign_id');
 const validCampaign=Boolean(campaignId && /^[1-9][0-9]*$/.test(campaignId));
 const [state,setState]=useState({loading:false,data:null,error:''});
 const [perspective,setPerspective]=useState('inbox');
 const [selectedTopic,setSelectedTopic]=useState('');
 const [showSummaries,setShowSummaries]=useState(false);
 useEffect(()=>{
  if(!validCampaign){setState({loading:false,data:null,error:''});return;}
  let cancelled=false;
  setState({loading:true,data:null,error:''});
  const token=localStorage.getItem('bawaslu_access_token')||'';
  fetch('/api/source-lineage/inbox-radar-feed/'+encodeURIComponent(campaignId),
   {cache:'no-store',headers:{Authorization:'Bearer '+token}})
   .then(async res=>{const x=await res.json();if(!res.ok)throw new Error(x.detail||'Inbox feed unavailable');return x;})
   .then(data=>{if(!cancelled)setState({loading:false,data,error:''});})
   .catch(e=>{if(!cancelled)setState({loading:false,data:null,error:e.message});});
  return ()=>{cancelled=true;};
 },[campaignId,validCampaign]);
 const entries=state.data?.entries||[];
 const summaryRows=entries.filter(x=>(x.summary_verification?.pipeline||[]).length);
 const topicNames=row=>(row.topic_labels||[]).map(topic=>typeof topic==='string'?topic:topic?.topic||topic?.label).filter(Boolean);
 const topicCounts=Object.entries(entries.reduce((acc,row)=>{for(const topic of row.topic_labels||[]){const key=typeof topic==='string'?topic:topic?.topic||topic?.label;if(key)acc[key]=(acc[key]||0)+1;}return acc;},{})).sort((a,b)=>b[1]-a[1]);
 return <section aria-label="Smart Radar V6.2" className="-mx-5 -my-5 md:-mx-9 md:-my-9 bg-[#f1f5f7]">
  {validCampaign&&<div className="border-b border-[#dce5ea] bg-white px-5 py-3 text-sm">
   <div className="font-semibold text-[#122f46]">Intelligence Inbox evidence feed · Campaign {campaignId}</div>
   <div className="text-xs text-[#526575]">Verified social-source assessments; legacy Radar pilot records remain separate.</div>
   {state.loading&&<div role="status">Loading saved assessment evidence…</div>}
   {state.error&&<div role="alert">Unable to load campaign evidence: {state.error}</div>}
   {state.data&&<div role="status">{entries.length} saved relevant assessments available to Smart Radar.</div>}
   {state.data&&<div className="mt-2 flex gap-2"><button type="button" onClick={()=>setPerspective('inbox')} aria-pressed={perspective==='inbox'} className="rounded border px-3 py-1">Inbox evidence</button><button type="button" onClick={()=>setPerspective('pilot')} aria-pressed={perspective==='pilot'} className="rounded border px-3 py-1">Historic Radar pilot</button></div>}
   {entries.length>0&&perspective==='inbox'&&<div className="mt-2 flex flex-wrap gap-2">{entries.slice(0,12).map(x=>
    <a key={x.canonical_source_id} href={'/inbox?campaign_id='+encodeURIComponent(campaignId)+'&result_id='+encodeURIComponent(x.canonical_source_id.slice(7))}
     className="rounded border border-[#dce5ea] px-2 py-1 text-xs text-[#174663]">
     {x.canonical_source_id} · v{x.assessment_version||'?'} · {(x.topic_labels||[]).join(', ')||'No topic'}
    </a>)}</div>}
  </div>}
  {validCampaign&&state.data&&perspective==='inbox'&&<div className="bg-white px-5 py-3 text-sm" aria-label="Saved Inbox intelligence perspectives">
   <div className="font-semibold mb-2">Saved assessment perspectives (provisional)</div>
   <div className="flex flex-wrap gap-3">{topicCounts.map(([topic,count])=><button type="button" aria-pressed={selectedTopic===topic} onClick={()=>setSelectedTopic(selectedTopic===topic?'':topic)} key={topic} className="rounded border p-3 text-left"><strong>{topic}</strong><div>{count} saved source posts</div></button>)}
   <div className="rounded border p-3"><strong>Public Concerns</strong><div>{entries.filter(x=>(x.public_concern_signals||[]).length).length} posts with saved signals</div></div>
   <div className="rounded border p-3"><strong>Potential Issues</strong><div>{entries.filter(x=>(x.potential_issues||[]).length).length} posts with preliminary signals</div></div></div>
   {selectedTopic&&<div className="mt-3"><button type="button" className="text-xs underline" onClick={()=>setSelectedTopic('')}>Clear topic filter</button><div className="mt-2 flex flex-wrap gap-2">{entries.filter(row=>topicNames(row).includes(selectedTopic)).map(row=><a key={row.canonical_source_id} href={'/inbox?campaign_id='+encodeURIComponent(campaignId)+'&result_id='+encodeURIComponent(row.canonical_source_id.slice(7))} className="rounded border px-2 py-1 text-xs">{row.canonical_source_id} · {row.relevance_label||'Assessed'} · v{row.assessment_version||'?'}</a>)}</div></div>}
   <button type="button" onClick={()=>setShowSummaries(!showSummaries)} className="mt-2 rounded border p-2 text-xs">Production AI drafts: {summaryRows.length} posts · {showSummaries?'Hide':'View'} source-verified drafts</button>
   {showSummaries&&<div>{summaryRows.length===0?<p className="text-xs">No source-verified production AI drafts saved.</p>:summaryRows.map(x=><div className="border p-2 mt-1 text-xs" key={x.canonical_source_id}><strong>{x.canonical_source_id}</strong>{x.summary_verification.pipeline.map((draft,i)=><p key={i}>{draft.player}: {draft.summary} · AI draft, awaiting human review</p>)}</div>)}</div>}
   {topicCounts.length===0&&<p className="mt-2 text-xs text-[#526575]">No saved topic classifications in these assessed posts.</p>}
   <p className="mt-2 text-xs text-[#526575]">Counts describe saved relevant Inbox assessments, not corroborated incidents or representative public opinion.</p>
  </div>}
  {(!validCampaign||perspective==='pilot'||!state.data)&&<iframe title="BAWASLU Smart Radar V6.2" src="/ui-freeze/smart-radar-v6_2.html"
   className="block w-full border-0 bg-[#f1f5f7]" style={{height:'calc(100vh - 76px)',minHeight:640}}/>}
 </section>;
}
