/* BAWASLU real-UI demo adapter, with snapshot-backed responses only.
   Every /api/ request resolves locally. External network I/O is denied by CSP. */
import {snapshot} from './currentSnapshot.js';
const DEMO_KEY='__BAWASLU_DEMO_REPLICA__';
window[DEMO_KEY]=true;
const clone=v=>JSON.parse(JSON.stringify(v));
const response=(value,status=200)=>new Response(JSON.stringify(value),{status,headers:{'Content-Type':'application/json'}});
const original=window.fetch.bind(window);
const user={id:'DEMO-OFFICER',full_name:'BAWASLU Demo Officer',email:'demo.invalid@localhost',status:'Active'};
const permissions={view_intelligence:true,add_intelligence:true,human_validation:true,administration:true,
  manage_watchlist:true,review_intelligence:true,manage_campaigns:true,view_raw_evidence:true};
const access={status:'Active',geographic_scope:'Nationwide',province:'',permissions,role:'Administrator'};
const campaigns=Array.from(new Map(snapshot.map(p=>[String(p.campaignId),{
 id:p.campaignId,name:p.campaign||'Pemantauan Pemilu',description:'Read-only demonstration snapshot',
 primary_keywords:['bawaslu','pemilu'],secondary_keywords:['gibran','ijazah'],excluded_keywords:[],
 platforms:['tiktok','instagram','youtube','facebook','twitter-ai-search','threads','online_news'],
 language:'',status:'Active',run_count:1,evidence_count:snapshot.filter(x=>x.campaignId===p.campaignId).length,
 created_at:'2026-10-15T00:00:00Z',date_from:null,date_to:null}])).values());
let additionalCampaigns=[],reviewState={},selectedWatch=['Gibran Rakabuming Raka','Prabowo Subianto','Anies Baswedan','Dedi Mulyadi','Purbaya Yudhi Sadewa'];
const names=['Gibran Rakabuming Raka','Prabowo Subianto','Anies Baswedan','Dedi Mulyadi','Purbaya Yudhi Sadewa','Ganjar Pranowo'];
const accountNames=names.map((name,i)=>({id:'WATCH-DEMO-'+i,name,type:'Candidate',priority:'Medium',status:'Active',
 province:'Indonesia',related_topics:[],candidate_aliases:[]}));
const rowsFor=(id)=>snapshot.filter(p=>!id||String(p.campaignId)===String(id));
const count=(arr,key)=>arr.reduce((out,x)=>{const k=String(typeof key==='function'?key(x):x[key]||'');if(k)out[k]=(out[k]||0)+1;return out},{});
const evidence=p=>({id:p.id,result_id:p.id,campaign_id:p.campaignId,platform:p.platform,content_type:'Post',
 published_at:p.date,author_name:p.author,author_display:p.author,observed_handle:p.author,
 text_content:p.text,canonical_url:'',thumbnail_url:null,relevance_label:'RELEVANT',
 sentiment:['POSITIVE','NEUTRAL','NEGATIVE'].includes(p.sentiment)?p.sentiment:'NEUTRAL',
 original_sentiment:p.sentiment,review_state:reviewState[p.id]||'UNREVIEWED',
 engagement_total:Number(p.engagement?.engagement_total||p.engagement?.likes||0),
 likes:Number(p.engagement?.likes||0),comments:Number(p.engagement?.comments||0),views:Number(p.engagement?.views||0),
 source_record_id:p.id});
function inboxFinding(p){
 const topics=Array.isArray(p.topics)?p.topics:[];
 const flags=Array.isArray(p.signals)?p.signals:[];
 return {...evidence(p),campaign_name:p.campaign,assessment_version:1,
  model_version:'Saved AI assessment snapshot',relevance_confidence:.85,explanation:p.explanation,
  sentiment_explanation:p.explanation,is_relevant:true,
  has_saved_assessment:true,ai_assessed:true,is_flagged:flags.length>0,
  can_review_flag:true,human_review_status:reviewState[p.id]||'AWAITING_REVIEW',possible_issues:flags,
  topic_labels:topics,topic_suggestions:topics,category:'Electoral Operations',
  candidate_signals:Array.isArray(p.candidates)?p.candidates:[],geographic_signals:[],
  potential_issue_signals:flags,incident_jurisdiction_review:{decision:'UNREVIEWED',incident_jurisdiction_verified:false},
  actionability:'REQUIRES_REVIEW',attention_assessment:{level:'REVIEW',reason:'Saved AI signal. Verify against original evidence.'}};
}
const allFindings=()=>snapshot.map(inboxFinding);
function chartData(rows){
 const dates=count(rows,p=>String(p.date||'').slice(0,10));
 const platforms=count(rows,p=>p.platform);
 const daily=Object.entries(dates).sort(([a],[b])=>a.localeCompare(b)).map(([date,n])=>({...Object.fromEntries(Object.keys(platforms).flatMap(key=>[[key+'__posts',rows.filter(p=>String(p.date||'').startsWith(date)&&p.platform===key).length],[key+'__engagement',0]])),date,posts:n}));
 const sentiments=count(rows,p=>['POSITIVE','NEGATIVE','NEUTRAL'].includes(p.sentiment)?p.sentiment:'NEUTRAL');
 const topics=[
  {topic:'Pengawasan Pemilu',count:rows.filter(x=>/bawaslu|pengawas/i.test(x.text)).length},
  {topic:'Ijazah Gibran',count:rows.filter(x=>/ijazah|gibran/i.test(x.text)).length},
  {topic:'Kampanye',count:rows.filter(x=>/kampanye/i.test(x.text)).length}
 ];
 const keywordCloud=['bawaslu','pemilu','gibran','ijazah','mahkamah','kpu','kampanye'].map(word=>({word,count:rows.filter(p=>p.text.toLowerCase().includes(word)).length}));
 return {statistics:{messages:rows.length,engagement:rows.reduce((n,p)=>n+Number(p.engagement?.engagement_total||p.engagement?.likes||0),0),
  accounts:new Set(rows.map(p=>p.author)).size,platforms:Object.keys(platforms).length},
 platforms, sentiment:sentiments,sentiments, daily_platform_trend:daily,activity:daily,
 topics_and_themes:{topics,subject_categories:topics,classified_count:rows.length,total:rows.length},
 top_accounts_engagement:[...new Map(rows.map(p=>[p.author,p])).values()].slice(0,12).map((p,i)=>({name:p.author,platform:p.platform,engagement:1000-i*45,followers:0})),
 top_accounts_followers:[],geographies:{},source_languages:{id:rows.length},demographics_coverage:{records:rows.length,country_available:0,language_available:rows.length},
 province_connected_distribution:[],word_cloud:keywordCloud.filter(w=>w.count>0),candidate_mentions:count(rows,p=>p.candidates?.[0]||'')};
}
function mockSocial(payload={}){
 const action=String(payload.action||''),id=payload.id||payload.data?.campaign_id||null,data=payload.data||{};
 const rows=rowsFor(id),group=rows.map(evidence);
 switch(action){
  case 'listCampaigns':return {campaigns:[...additionalCampaigns,...campaigns],total:campaigns.length+additionalCampaigns.length};
  case 'getCampaign':return {campaign:[...campaigns,...additionalCampaigns].find(c=>String(c.id)===String(id))||campaigns[0]};
  case 'campaignEvidence':return {evidence:group,total:group.length};
  case 'campaignCapturedPosts':{
   const page=Math.max(1,Number(data.page||1)),size=Math.min(200,Number(data.page_size||200));
   return {evidence:group.slice((page-1)*size,page*size),has_more:page*size<group.length,total:group.length};
  }
  case 'campaignEvidenceById':{const p=group.find(x=>String(x.id)===String(data.result_id));return {found:!!p,post:p||null}}
  case 'campaignDashboard':return chartData(rows);
  case 'campaignIntelligenceInbox':{
   const list=allFindings().filter(f=>(!data.campaign_id||String(f.campaign_id)===String(data.campaign_id))&&
     (!data.result_id||String(f.id)===String(data.result_id)));
   return {findings:list,campaigns,unassessed_count:0,issue_categories:[],
     assessment_counts:{assessed:list.length,unassessed:0,relevant:list.length},job_counts:{pending:0,active:0}};
  }
  case 'campaignFlagReview':
  case 'campaignManualFlag':
  case 'campaignOfficerClassificationCorrection':{
   const resultId=String(data.result_id||'');
   reviewState[resultId]=data.decision||'REVIEWED';
   return {ok:true,latest_review:{decision:reviewState[resultId],reviewed_at:new Date().toISOString()},demo:true};
  }
  case 'campaignFindingGroupsList':return {groups:[]};
  case 'campaignFindingGroupsPreview':return {groups:[],source_count:rows.length};
  case 'campaignDateTopPosts':return {posts:group.filter(x=>x.published_at?.startsWith(data.date||'')).slice(0,15)};
  case 'campaignDiscoverPreview':return {signature:'DEMO',estimated_credits:0,queries:[],results:[]};
  case 'campaignDiscoverStart':return {run_id:'DEMO',stage:'COMPLETED',status:'COMPLETED',result_count:0};
  case 'campaignDiscoverStatus':return {run_id:'DEMO',stage:'COMPLETED',status:'COMPLETED'};
  case 'campaignAssessmentAllStart':return {stage:'COMPLETED',no_unassessed:true,total:0};
  case 'campaignAssessmentAllStatus':return {stage:'COMPLETED',completed:rows.length,total:rows.length};
  case 'campaignCostPreview':return {estimated_credits:0,minimum_credits:0};
  case 'campaignSentimentBatchPreview':return {count:0,candidates:[],sample_size:0};
  case 'campaignManualPreflight':return {estimated_credits:0,query:'DEMO',confirmed_query:'DEMO',results:[]};
  case 'campaignTopicRefresh':return {topics:chartData(rows).topics_and_themes,preview:true};
  case 'createCampaign':
  case 'campaignCreate':{
   const c={id:'DEMO-CAMPAIGN-'+(additionalCampaigns.length+1),name:data.name||'New Demo Campaign',description:data.description||'',
    primary_keywords:data.primary_keywords||[],secondary_keywords:data.secondary_keywords||[],
    platforms:data.platforms||[],run_count:0,evidence_count:0,status:'DRAFT'};
   additionalCampaigns.unshift(c);return {campaign:c};
  }
  default:return {ok:true,demo:true,items:[],findings:[],evidence:[],groups:[],campaigns,statistics:chartData(rows).statistics};
 }
}
function mockRegistry(payload={}){
 const action=String(payload.action||'');
 if(action==='myAccess')return {access,permissions};
 if(action==='watchlistSummary')return {items:accountNames,source:'DEMO_SNAPSHOT'};
 if(action==='list')return {items:accountNames,accounts:[],relationships:[],sources:[],categories:[]};
 if(action==='getMyEffectiveAccess')return {access};
 return {items:accountNames,accounts:[],relationships:[],sources:[],categories:[],access,demo:true};
}
function localApi(url,init){
 const u=new URL(url,window.location.href),path=u.pathname;
 let payload={};try{payload=init.body?JSON.parse(init.body):{}}catch(_){}
 if(path==='/api/public-settings')return {id:'DEMO',public_settings:{signup_enabled:false}};
 if(path==='/api/auth/me')return user;
 if(path==='/api/auth/logout')return {ok:true,demo:true};
 if(path==='/api/health')return {status:'ok',build_version:'DEMO',commit:'SNAPSHOT'};
 if(path==='/api/functions/getMyEffectiveAccess')return {access};
 if(path==='/api/functions/registry')return mockRegistry(payload);
 if(path==='/api/functions/socialListening')return mockSocial(payload);
 if(path==='/api/functions/intelligence')return {items:[],accounts:[],relationships:[],sources:[],categories:[],demo:true};
 if(path==='/api/functions/intelligenceAssistant'){
  return {answer:'Demo / Simulasi: '+snapshot.length+' saved evidence records are available for exploration. This is a preset answer; no new model assessment was performed.',
    records:snapshot.slice(0,3).map(inboxFinding),provider:'READ_ONLY_DEMO',grounding:{accessible_count:snapshot.length,source_types:['SOCIAL_LISTENING']},demo:true};
 }
 if(path.startsWith('/api/assistant-history'))return {threads:[],messages:[],items:[],thread:null,demo:true};
 if(path==='/api/presentation/translate')return {text:payload.text||'',language:payload.language||'id',translation_only:true,demo:true};
 if(path==='/api/relevance-gates')return {items:[],gates:[]};
 if(path.includes('/campaign/')||path.includes('/external-import/'))return {ok:true,demo:true,status:'COMPLETED',evidence:[],records:[]};
 return {ok:true,demo:true,items:[],posts:[],findings:[],groups:[],campaigns:[]};
}
window.fetch=async (input,init={})=>{
 const url=typeof input==='string'?input:input?.url||'',u=new URL(url,window.location.href);
 if(u.pathname.startsWith('/api/'))return response(localApi(url,init));
 // Read-only static resources from this application host; never access other origins.
 if(u.origin===location.origin&&!/\/api\//.test(u.pathname))return original(input,init);
 return response({detail:'Blocked: read-only demo network isolation'},403);
};
window.__BAWASLU_DEMO_RESET__=()=>{additionalCampaigns.length=0;reviewState={};};
