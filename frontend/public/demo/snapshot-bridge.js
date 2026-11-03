/* Read-only BAWASLU prototype bridge.
   Findings, counts, and evidence derive exclusively from the fixed saved-assessment snapshot.
   No keyword-based fabrication of findings, verified violations or incident geography. */
(function(){
 'use strict';
 const snapshotElement=document.getElementById('bawaslu-demo-snapshot');
 const rows=JSON.parse(snapshotElement.textContent);
 const metaElement=document.getElementById('bawaslu-demo-metadata');
 const meta=metaElement?JSON.parse(metaElement.textContent):{campaigns:[],watchlist:[]};
 const originalFetch=window.fetch.bind(window);
 const json=(data,status=200)=>new Response(JSON.stringify(data),{status,headers:{'Content-Type':'application/json'}});
 const countBy=(rows,fn)=>{const out={};for(const p of rows){const key=String(fn(p)||'');if(key)out[key]=(out[key]||0)+1;}return out;};
 const topicID={ 'Public Concern':'Kekhawatiran Publik','Public Information':'Informasi Publik',
  'Electoral Operations':'Operasional Pemilu','Campaign Rules':'Aturan Kampanye',
  'BAWASLU Reputation':'Reputasi BAWASLU','Election Administration':'Administrasi Pemilu'};
 const enID=new Map(Object.entries(topicID));
 const watchlist=(meta.watchlist||[]).map(x=>({...x,geographic_scope:'Nationwide',candidate_aliases:x.candidate_aliases||[]}));
 const campaignList=meta.campaigns||[];
 const normalizeCandidate=value=>{
  const s=String(value||'').trim();
  if(/gibran/i.test(s))return 'Gibran Rakabuming Raka';
  if(/prabowo/i.test(s))return 'Prabowo Subianto';
  if(/anies|anis baswedan/i.test(s))return 'Anies Baswedan';
  if(/ganjar/i.test(s))return 'Ganjar Pranowo';
  if(/cak imin|muhaimin/i.test(s))return 'Muhaimin Iskandar';
  if(/jokowi|joko widodo/i.test(s))return 'Joko Widodo';
  if(/ahok/i.test(s))return 'Ahok';
  return s;
 };
 const classify=p=>{
   if((p.signals||[]).length)return {kind:'source_review',player:'violations',name:'Reported election issue',id:'Isu pemilu yang dilaporkan',key:'violation:'+p.id};
   if((p.concerns||[]).length)return {kind:'discussion',player:'concerns',name:'Public concern',id:'Kekhawatiran publik',key:'concern:'+String(p.topics?.[0]||'Public Concern')};
   if((p.topics||[]).length){
    const topic=String(p.topics[0]);
    return {kind:'narrative_candidate',player:'narratives',name:'Emerging narrative',id:'Narasi berkembang',key:'narrative:'+topic};
   }
   return {kind:'source_awareness',player:null,name:'Source for officer review',id:'Sumber untuk peninjauan petugas',key:'awareness:'+p.id};
 };
 let reviews={};
 function assemble(){
  const groups=new Map();
  for(const p of rows){
   const cat=classify(p),group=groups.get(cat.key)||{code:cat,rows:[]};
   group.rows.push(p);groups.set(cat.key,group);
  }
  const findings=[...groups.values()].map((g,i)=>{
   const records=g.rows,cat=g.code,topic=records[0]?.topics?.[0]||'';
   const topicName=cat.player==='violations'?String(records[0]?.signals?.[0]?.category||'Election Administration'):topic;
   const title=cat.name+(topicName?': '+topicName:'');
   const titleId=cat.id+(topicName?': '+(topicID[topicName]||topicName):'');
   const n=records.length;
   const summary=cat.player==='violations'?'Saved assessment records describe a reported issue. The allegation requires independent officer verification.':
     cat.player==='concerns'?n+' saved relevant posts contain public-concern signals; these are unverified source claims.':
     cat.player==='narratives'?n+' saved relevant posts share the topic '+topicName+'. This is a discussion pattern, not a verified incident.':
     'This relevant source is available for officer review; its topic was not established by the saved assessment.';
   const summaryId=cat.player==='violations'?'Penilaian tersimpan mencatat isu yang dilaporkan. Dugaan memerlukan verifikasi independen oleh petugas.':
     cat.player==='concerns'?n+' unggahan relevan tersimpan memuat sinyal kekhawatiran publik; klaim sumber ini belum terverifikasi.':
     cat.player==='narratives'?n+' unggahan relevan tersimpan memiliki topik '+(topicID[topicName]||topicName)+'. Ini pola percakapan, bukan kejadian terverifikasi.':
     'Sumber relevan ini tersedia untuk ditinjau petugas; topiknya belum ditetapkan dalam penilaian tersimpan.';
   enID.set(title,titleId);enID.set(summary,summaryId);
   const actors={};for(const p of records)for(const raw of p.candidates||[]){const name=normalizeCandidate(raw);if(name)actors[name]=(actors[name]||0)+1;}
   const key='INBOX-DEMO-'+i;
   const result={id:key,kind:cat.kind,title,summary,ai_summary:false,ai_model:'',
    perspectives:cat.player==='concerns'?['reputation','operations']:['operations'],
    players:cat.player?[cat.player]:[],topics:[...new Set(records.flatMap(p=>p.topics||[]))],
    status:reviews[key]||((cat.player==='violations'||cat.player==='concerns')?'pending':'awareness'),
    published_at:records.map(p=>p.date||'').sort().slice(-1)[0]||'',
    source_ids:records.map(p=>p.sourceId),supporting_posts:n,
    human_reviewed:reviews[key]==='reviewed',source_evidence_verified:false,
    review_suggested:cat.player==='violations'||cat.player==='concerns',
    review_basis:'Saved Inbox assessment, officer triage required',
    sentiment_counts:countBy(records,p=>p.sentiment||'UNCLASSIFIED'),
    platform_counts:countBy(records,p=>p.platform),
    day_counts:countBy(records,p=>String(p.date||'').slice(0,10)),
    actor_mentions:actors,geo_signal_counts:{},verified_incident_counts:{},province_breakdown:{},
    priority_score:null,priority_label:'Not AI-scored',next_followup:'',
    insights:{operations:summary,reputation:summary},summary_id:summaryId,
    recurring_discussion:records.length>=2,source_assessment_versions:records.map(p=>({source_id:p.sourceId,assessment_version:p.assessmentVersion||1}))};
   return {...result,records};
  });
  return findings.sort((a,b)=>Number(b.status==='pending')-Number(a.status==='pending')||b.supporting_posts-a.supporting_posts);
 }
 const evidence=p=>({
   canonical_source_id:p.sourceId,account_raw:p.author||'Sumber publik contoh',
   published_at_raw:p.date||'',message_original:p.text||'',platform:p.platform||'',
   source_url:'',sentiment:p.sentiment||'UNCLASSIFIED',source_verification_status:'SAVED_INBOX_ASSESSMENT_UNVERIFIED',
   geographic_mentions_unverified:[],verified_incident_province:'',candidate_names:p.candidates||[],
   original_category_hint:(p.topics||[]).join(', '),review_status:p.reviewState||'UNREVIEWED'
 });
 const candidates=()=>{
  const c={};for(const p of rows)for(const raw of p.candidates||[]){
   const name=normalizeCandidate(raw);if(name)c[name]=(c[name]||0)+1;
  }return Object.entries(c).sort((a,b)=>b[1]-a[1]).slice(0,10);
 };
 const cloud=()=>{
  const words=[...new Set(campaignList.flatMap(c=>c.primary_keywords||[]))].filter(w=>w.length>=3);
  return words.map(keyword=>({keyword,count:rows.filter(p=>String(p.text||'').toLowerCase().includes(keyword.toLowerCase())).length}))
   .filter(x=>x.count).sort((a,b)=>b.count-a.count).slice(0,24);
 };
 const publicFindings=()=>assemble().map(({records,...f})=>f);
 function payload(){
   const findings=publicFindings();
   return {batch_id:null,source_total:rows.length,source_unique_urls:0,
    findings,platform_counts:countBy(rows,p=>p.platform),candidate_mentions:candidates(),
    main_keyword_cloud:cloud(),sentiment_counts:countBy(rows,p=>p.sentiment||'UNCLASSIFIED'),
    geo_signal_counts:{},verified_incident_counts:{},
    watchlist_profiles:watchlist,watchlist_source:'SAVED_PRODUCTION_DERIVED_SNAPSHOT',
    reviewed_total:findings.filter(x=>x.human_reviewed).length,
    mode:'SAVED_INBOX_SOURCE_OF_TRUTH',scoring_ready:false,
    feed_source:'FIXED_SAVED_ASSESSMENTS',inbox_source_scope:'APPROVED_RELEVANT_SNAPSHOT',
    inbox_window_limit:300,truncated_to_inbox_window:rows.length>=300,
    sentiment_coverage:{classified:rows.filter(x=>['POSITIVE','NEGATIVE','NEUTRAL'].includes(x.sentiment)).length,
      unclassified:rows.filter(x=>!['POSITIVE','NEGATIVE','NEUTRAL'].includes(x.sentiment)).length},
    geographic_scope_note:'No verified incident provinces inferred from source profiles.',
    disclaimer:'Read-only training snapshot of saved assessments. No legal verdict or source verification implied.',
    jurisdictions:[],timezone:'Asia/Jakarta',paid_provider_called:false};
 }
 function distribution(){
   const groups={};
   for(const p of rows){
     const label=p.topics?.[0]||((p.concerns||[]).length?'Public Concern':'Other');
     if(!groups[label])groups[label]=[];
     groups[label].push(p);
   }
   const sorted=Object.entries(groups).sort((a,b)=>b[1].length-a[1].length);
   const topics=sorted.slice(0,5).map(([label,rs],i)=>{
     const title=label==='Other'?'Other saved relevant sources':label;
     enID.set(title,label==='Other'?'Sumber relevan tersimpan lainnya':(topicID[label]||label));
     return {id:i+1,title,count:rs.length,sentiment:Object.entries(countBy(rs,p=>p.sentiment)).sort((a,b)=>b[1]-a[1])[0]?.[0]||'NEUTRAL',
       description:'Saved AI topic classifications; verify original evidence.'};
   });
   enID.set('Saved AI topic classifications; verify original evidence.','Klasifikasi topik AI tersimpan; periksa bukti asli.');
   return {operations:{topics,others:sorted.slice(5).reduce((n,x)=>n+x[1].length,0),total:rows.length,refresh_pending:false},
     reputation:{topics,others:sorted.slice(5).reduce((n,x)=>n+x[1].length,0),total:rows.length,refresh_pending:false}};
 }
 function request(path,method,opts){
   const u=new URL(path,location.origin),p=u.pathname;
   if(p==='/api/smart-radar/dashboard')return payload();
   if(p==='/api/smart-radar/issue-distribution')return distribution();
   if(p==='/api/smart-radar/issue-distribution/posts'){
     const ids=Object.entries(rows.reduce((a,x)=>{const key=x.topics?.[0]||((x.concerns||[]).length?'Public Concern':'Other');(a[key]??=[]).push(x);return a},{})).sort((a,b)=>b[1].length-a[1].length);
     const index=Math.max(0,Number(u.searchParams.get('topic_id')||1)-1);
     const found=ids[index]?.[1]||[];
     return {total:found.length,posts:found.slice(0,100).map(p=>({title:p.text.slice(0,110),text:p.text,platform:p.platform,published_at:p.date}))};
   }
   if(p.startsWith('/api/smart-radar/finding/')){
     const id=decodeURIComponent(p.split('/').pop()),f=assemble().find(x=>x.id===id);
     if(!f)return {detail:'Finding not in fixed snapshot'};
     const {records,...head}=f;return {...head,posts:records.map(evidence)};
   }
   if(p.startsWith('/api/smart-radar/history/'))return {events:[]};
   if(p==='/api/smart-radar/decision'){
     try{const body=JSON.parse(opts?.body||'{}');reviews[String(body.finding_id||'')]='reviewed'}catch(_){}
     return {ok:true,demo:true};
   }
   if(p==='/api/functions/registry'){
     let body={};try{body=JSON.parse(opts?.body||'{}')}catch(_){}
     if(body.action==='list')return {items:watchlist,accounts:[],sources:[],categories:[],relationships:[]};
     if(body.action==='myAccess')return {access:{status:'Active',permissions:{view_intelligence:true,manage_watchlist:true,human_validation:true},geographic_scope:'Nationwide'}};
     if(body.action==='watchlistCapturedFeed'){
       const selected=watchlist.find(x=>String(x.id)===String(body.id||'')),name=String(selected?.name||'').toLowerCase();
       const sources=name?rows.filter(p=>(p.candidates||[]).some(x=>normalizeCandidate(x).toLowerCase()===name)):[];
       const page=Math.max(1,Number(body.data?.page||1)),offset=(page-1)*50;
       return {posts:sources.slice(offset,offset+50).map(p=>({id:p.id,platform:p.platform,author_name:p.author,published_at:p.date,text:p.text,relation:'MENTION',saved_assessments:[{sentiment:p.sentiment,assessment_version:1}]})),total:sources.length};
     }
     if(body.action==='watchlistSyncStatus')return {enabled:false,manual_fetch_available:false,accounts:[]};
     if(body.action==='createWatchlist'){const item={id:'DEMO-WATCH-NEW-'+watchlist.length,name:body.data?.name||'Kandidat Demo',type:'Candidate',status:'Under Review',priority:'Medium'};watchlist.push(item);return {item,demo:true};}
     if(body.action==='updateWatchlist'){const row=watchlist.find(x=>String(x.id)===String(body.id));if(row)Object.assign(row,body.data||{});return {item:row||null,demo:true};}
     return {items:watchlist,accounts:[]};
   }
   if(p==='/api/functions/socialListening'){
     let body={};try{body=JSON.parse(opts?.body||'{}')}catch(_){}
     if(body.action==='campaignCandidateSuggestions'){
       const source=rows.filter(x=>!body.data?.campaign_id||x.campaignId===body.data.campaign_id);
       return {candidates:Object.entries(source.reduce((a,p)=>{for(const raw of p.candidates||[]){const name=normalizeCandidate(raw);(a[name]??={name,matching_posts:0,source_ids:[]}).matching_posts++;if(a[name].source_ids.length<5)a[name].source_ids.push(p.sourceId);}return a},{})).map(x=>x[1]).sort((a,b)=>b.matching_posts-a.matching_posts).slice(0,10)};
     }
     return {ok:true,demo:true,items:[],posts:[]};
   }
   if(p==='/api/presentation/translate'){
     let body={};try{body=JSON.parse(opts?.body||'{}')}catch(_){}
     const text=String(body.text||''),lang=body.language||body.target_language||'id';
     return {text:lang==='id'?(enID.get(text)||text):text,language:lang,translation_only:true,demo:true};
   }
   if(p==='/api/health')return {ok:true,build_version:'DEMO'};
   return {ok:true,demo:true,items:[],posts:[],findings:[]};
 }
 window.fetch=async(input,opts={})=>{
   const src=typeof input==='string'?input:input?.url||'';
   const u=new URL(src,location.href),method=String(opts.method||input?.method||'GET').toUpperCase();
   if(u.pathname.startsWith('/api/'))return json(request(src,method,opts));
   if(u.origin===location.origin&&['GET','HEAD'].includes(method)&&!u.pathname.startsWith('/api/'))return originalFetch(input,opts);
   return json({detail:'Demo: external access and mutations blocked'},403);
 };
 window.__BAWASLU_DEMO_REPLICA__=true;
})();