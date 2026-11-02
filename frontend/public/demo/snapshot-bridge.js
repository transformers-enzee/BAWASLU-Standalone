/* Production-look BAWASLU demo bridge. Read-only snapshot; every API call is resolved in-browser. */
(function(){
 'use strict';
 const element=document.getElementById('bawaslu-demo-snapshot');
 const records=JSON.parse(element.textContent);
 const toJSON=(v,status=200)=>new Response(JSON.stringify(v),{status,headers:{'Content-Type':'application/json'}});
 const originalFetch=window.fetch.bind(window);
 const categories=[
 {id:1,title:'Gibran Qualification Dispute Exposes Restricted Election Oversight Access',sentiment:'NEGATIVE',matcher:/gibran|ijazah|diploma|mahkamah|putusan/i,player:'concerns',summary:'Public discussions about legal decisions and public access to election oversight require independent verification.'},
 {id:2,title:'Election Results Face Persistent Distrust, Protest, and Institutional Legitimacy Concerns',sentiment:'NEGATIVE',matcher:/hasil pemilu|protes|legitimasi|kecurangan|demonstrasi|election result/i,player:'concerns',summary:'Public expressions of dissatisfaction with election outcomes and institutions require a careful factual review.'},
 {id:3,title:'Bawaslu Capacity Building and Public Participation Strengthen Preventive Oversight',sentiment:'POSITIVE',matcher:/bawaslu|pengawas|partisipasi|edukasi|sosialisasi|pelatihan/i,player:'narratives',summary:'Discussions about BAWASLU outreach and public participation can indicate opportunities for preventative engagement.'},
 {id:4,title:'Polling Irregularities Trigger Recounts, Technology Failures, and Operational Corrections',sentiment:'MIXED',matcher:/penghitungan|rekapitulasi|teknologi|tps|pemungutan/i,player:'violations',summary:'Operational claims about ballot processes and counting require verification of primary evidence.'},
 {id:5,title:'Reported Campaign and Voting Violations Drive Formal Enforcement Attention',sentiment:'NEGATIVE',matcher:/kampanye|amplop|uang|bagi|pelanggaran|suap/i,player:'violations',summary:'Claims about campaign conduct may merit officer review but do not establish any legal violation.'},
 {id:6,title:'Other Election Conversations',sentiment:'NEUTRAL',matcher:/.*/,player:'narratives',summary:'Other public election-related conversations that have not been assigned to one of the main themes.'}
 ];
 const cleaned=records.map((p,i)=>({...p,group:Math.max(0,categories.findIndex(t=>t.matcher.test(p.text||''))),_i:i}));
 const rowGroups=categories.map((c,i)=>cleaned.filter(p=>p.group===i));
 function countsBy(rows,fn){const out={};for(const x of rows){const k=String(fn(x)||'');if(k)out[k]=(out[k]||0)+1}return out}
 function candidates(rows){const c={};for(const x of rows)for(const name of (Array.isArray(x.candidates)?x.candidates:[])){const n=String(name||'').trim();if(n)c[n]=(c[n]||0)+1}return c}
 const watchlist=['Gibran Rakabuming Raka','Prabowo Subianto','Anies Baswedan','Ganjar Pranowo','Purbaya Yudhi Sadewa','Dedi Mulyadi'].map(name=>({id:'DEMO-'+name.toLowerCase().replace(/\s+/g,'-'),name,status:'Active',priority:'Medium',geographic_scope:'Nationwide',type:'Candidate',province:'Indonesia',candidate_aliases:[]}));
 let demoReviews={};
 const makeFinding=(group,i)=>{
  const topic=categories[i],day=countsBy(group,p=>String(p.date||'').slice(0,10)),scope={};
  const summary=topic.summary;
  return {id:'INBOX-DEMO-'+i,kind:'saved_inbox',title:topic.title,summary,ai_summary:true,ai_model:'Saved assessment snapshot',
   perspectives:['operations'],players:[topic.player],topics:[topic.id],status:demoReviews[i]||((i===3||i===4)?'pending':'awareness'),
   source_ids:group.map(p=>p.sourceId),supporting_posts:group.length,human_reviewed:demoReviews[i]==='reviewed',
   sentiment_counts:countsBy(group,p=>p.sentiment),platform_counts:countsBy(group,p=>p.platform),
   day_counts:day,actor_mentions:candidates(group),geo_signal_counts:{},verified_incident_counts:{},priority_score:topic.player==='violations'?70:45,
   priority_label:'Needs review',next_followup:null,insights:{}};
 };
 function payload(){
  const findings=rowGroups.map(makeFinding).filter(f=>f.supporting_posts>0);
  const candidateCounts=Object.entries(candidates(cleaned)).sort((a,b)=>b[1]-a[1]).slice(0,10);
  return {batch_id:null,source_total:cleaned.length,source_unique_urls:cleaned.length,
   findings,platform_counts:countsBy(cleaned,p=>p.platform),candidate_mentions:candidateCounts,
   main_keyword_cloud:[{keyword:'bawaslu',count:82},{keyword:'pemilu',count:75},{keyword:'gibran',count:62},{keyword:'ijazah',count:58},{keyword:'kpu',count:34},{keyword:'pilpres',count:21}],
   sentiment_counts:countsBy(cleaned,p=>p.sentiment),geo_signal_counts:{'DKI Jakarta':5,'Jawa Timur':2,'Nusa Tenggara Timur':4,'Jawa Barat':2},
   verified_incident_counts:{},watchlist_profiles:watchlist,watchlist_source:'DEMO_SNAPSHOT',
   sentiment_coverage:{classified:cleaned.filter(x=>['POSITIVE','NEGATIVE','NEUTRAL'].includes(x.sentiment)).length,
     unclassified:cleaned.filter(x=>x.sentiment==='UNCLASSIFIED').length},
   geographic_scope_note:'Source references are not verified incident geography.',reviewed_total:findings.filter(x=>x.human_reviewed).length,
   mode:'SAVED_INBOX_SOURCE_OF_TRUTH',scoring_ready:false,feed_source:'READ_ONLY_DEMO_SNAPSHOT',inbox_source_scope:'DEMO_PUBLIC_SNAPSHOT',
   inbox_window_limit:300,truncated_to_inbox_window:false,disclaimer:'Read-only demo snapshot. Saved AI results are not legal findings.',
   jurisdictions:[],timezone:'Asia/Jakarta',paid_provider_called:false};
 }
 function evidence(p){return {account_raw:p.author||'Public source',published_at_raw:p.date||'',message_original:p.text||'',
  source_url:'',canonical_source_id:p.id,platform:p.platform||'',sentiment:p.sentiment||'NEUTRAL',
  geographic_mentions_unverified:[],verified_incident_province:''};}
 function issueRows(perspective){const topics=categories.map((t,i)=>({id:t.id,title:t.title,description:t.summary,count:rowGroups[i].length,sentiment:t.sentiment})).filter(x=>x.count>0);
  return {topics:topics.slice(0,5),others:topics[5]?.count||0,total:cleaned.length,refresh_pending:false};}
 function api(path,method,options){
  const u=new URL(path,location.origin),p=u.pathname;
  if(p==='/api/smart-radar/dashboard')return payload();
  if(p==='/api/smart-radar/issue-distribution')return {operations:issueRows('operations'),reputation:issueRows('reputation')};
  if(p==='/api/smart-radar/issue-distribution/posts'){
   const index=Math.max(0,categories.findIndex(t=>t.id===Number(u.searchParams.get('topic_id'))));
   const rows=rowGroups[index];return {total:rows.length,posts:rows.slice(0,100).map(p=>({text:p.text,platform:p.platform,published_at:p.date}))};
  }
  if(p.startsWith('/api/smart-radar/finding/')){
   const index=Number(decodeURIComponent(p.split('/').pop()).split('INBOX-DEMO-')[1]||0);
   return {...makeFinding(rowGroups[index]||[],index),posts:(rowGroups[index]||[]).map(evidence)};
  }
  if(p.startsWith('/api/smart-radar/history/'))return {events:[]};
  if(p==='/api/smart-radar/decision'){
   try{const b=JSON.parse(options?.body||'{}');const id=String(b.finding_id||'').replace('INBOX-DEMO-','');demoReviews[Number(id)]='reviewed'}catch(_){}
   return {ok:true,demo:true};
  }
  if(p==='/api/functions/registry'){
   let body={};try{body=JSON.parse(options?.body||'{}')}catch(_){}
   const action=body.action||'',id=String(body.id||'');
   if(action==='list')return {items:watchlist,accounts:[],sources:[],categories:[],relationships:[]};
   if(action==='myAccess')return {access:{status:'Active',permissions:{view_intelligence:true,manage_watchlist:true,human_validation:true},geographic_scope:'Nationwide'}};
   if(action==='watchlistCapturedFeed'){
     const active=watchlist.find(x=>String(x.id)===id);
     const rows=active?cleaned.filter(p=>p.candidates?.some(name=>String(active.name).toLowerCase().includes(String(name).toLowerCase())||String(name).toLowerCase().includes(active.name.split(' ')[0].toLowerCase()))):[];
     const page=Math.max(1,Number(body.data?.page||1)),size=50;
     return {posts:rows.slice((page-1)*size,page*size).map(p=>({id:p.id,relation:'MENTION',platform:p.platform,author_name:p.author,published_at:p.date,text:p.text,url:'',saved_assessments:[{sentiment:p.sentiment,is_flagged:false,assessment_version:1}]})),total:rows.length};
   }
   if(action==='watchlistSyncStatus')return {enabled:false,manual_fetch_available:false,accounts:[]};
   if(action==='createWatchlist'){const item={id:'DEMO-WATCH-'+watchlist.length,name:body.data?.name||'Demo Candidate',type:'Candidate',status:'Active',priority:'Medium',candidate_aliases:body.data?.candidate_aliases||[]};watchlist.push(item);return {item,demo:true};}
   if(action==='updateWatchlist'){const row=watchlist.find(x=>String(x.id)===id);if(row)Object.assign(row,body.data||{});return {item:row||null,demo:true};}
   if(action==='addAccount')return {account:{id:'DEMO-ACCOUNT',...body.data},demo:true};
   return {access:{permissions:{view_intelligence:true,manage_watchlist:true,human_validation:true},geographic_scope:'Nationwide'},items:watchlist,accounts:[]};
  }
  if(p==='/api/functions/socialListening'){
    let body={};try{body=JSON.parse(options?.body||'{}')}catch(_){}
    if(body.action==='campaignCandidateSuggestions'){
      const tally={};for(const p of cleaned)for(const name of (Array.isArray(p.candidates)?p.candidates:[])){const key=String(name||'').trim();if(key){tally[key]??={name:key,matching_posts:0,source_ids:[],tracked:false};tally[key].matching_posts++;if(tally[key].source_ids.length<5)tally[key].source_ids.push(p.id)}}
      return {candidates:Object.values(tally).sort((a,b)=>b.matching_posts-a.matching_posts).slice(0,10)};
    }
    return {ok:true,demo:true,posts:[],items:[]};
  }
  if(p==='/api/smart-radar/summarize-live')return {generated:[],remaining:0,demo:true};
  const translatedId={"Gibran Qualification Dispute Exposes Restricted Election Oversight Access":"Sengketa Kualifikasi Gibran Mengungkap Keterbatasan Akses Pengawasan Pemilu","Election Results Face Persistent Distrust, Protest, and Institutional Legitimacy Concerns":"Hasil Pemilu Menghadapi Ketidakpercayaan, Protes, dan Kekhawatiran Legitimasi Lembaga","Bawaslu Capacity Building and Public Participation Strengthen Preventive Oversight":"Peningkatan Kapasitas Bawaslu dan Partisipasi Publik Memperkuat Pengawasan Pencegahan","Polling Irregularities Trigger Recounts, Technology Failures, and Operational Corrections":"Ketidakteraturan Pemungutan Suara Memicu Penghitungan Ulang, Kendala Teknologi, dan Perbaikan Operasional","Reported Campaign and Voting Violations Drive Formal Enforcement Attention":"Laporan Dugaan Pelanggaran Kampanye dan Pemungutan Suara Memerlukan Perhatian Penegakan Hukum","Other Election Conversations":"Percakapan Pemilu Lainnya","Public discussions about legal decisions and public access to election oversight require independent verification.":"Diskusi publik mengenai putusan hukum dan akses pengawasan pemilu memerlukan verifikasi independen.","Public expressions of dissatisfaction with election outcomes and institutions require a careful factual review.":"Ungkapan ketidakpuasan publik terhadap hasil pemilu dan lembaga memerlukan pemeriksaan fakta secara saksama.","Discussions about BAWASLU outreach and public participation can indicate opportunities for preventative engagement.":"Diskusi mengenai sosialisasi BAWASLU dan partisipasi publik dapat menunjukkan peluang penguatan pencegahan.","Operational claims about ballot processes and counting require verification of primary evidence.":"Klaim operasional mengenai proses pemungutan dan penghitungan suara memerlukan verifikasi bukti primer.","Claims about campaign conduct may merit officer review but do not establish any legal violation.":"Klaim mengenai kegiatan kampanye dapat memerlukan peninjauan petugas, tetapi tidak membuktikan pelanggaran hukum."};
  if(p==='/api/presentation/translate'){
    const body=JSON.parse(options?.body||'{}'),text=body.text||'';
    return {text:body.language==='id'?(translatedId[text]||text):text,language:body.language||'id',translation_only:true,demo:true};
  }
  if(p==='/api/health')return {ok:true,build_version:'DEMO'};
  return {ok:true,demo:true,items:[],posts:[],findings:[],source:'DEMO_SNAPSHOT'};
 }
 window.fetch=async function(input,options={}){
  const url=typeof input==='string'?input:input?.url||'';
  const pathname=new URL(url,location.href).pathname,method=String(options.method||input?.method||'GET').toUpperCase();
  if(pathname.startsWith('/api/'))return toJSON(api(url,method,options));
  if(pathname==='/indonesia-provinces.geojson')return originalFetch(input,options);
  // No external requests from the public demo.
  return toJSON({error:'Demo network access disabled'},403);
 };
 window.__BAWASLU_DEMO_REPLICA__=true;
})();
