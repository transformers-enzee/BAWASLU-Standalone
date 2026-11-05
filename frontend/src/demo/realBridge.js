/* BAWASLU real-UI demo adapter, with snapshot-backed responses only.
   Every /api/ request resolves locally. External network I/O is denied by CSP. */
import {snapshot,demoAllEvidence,demoCampaigns,demoWatchlist} from './currentSnapshot.js';
import {demoProvinceMentions} from './inboxProvinceReferences.js';
const DEMO_KEY='__BAWASLU_DEMO_REPLICA__';
window[DEMO_KEY]=true;
const clone=v=>JSON.parse(JSON.stringify(v));
const response=(value,status=200)=>new Response(JSON.stringify(value),{status,headers:{'Content-Type':'application/json'}});
const original=window.fetch.bind(window);
const user={id:'DEMO-OFFICER',full_name:'BAWASLU Demo Officer',email:'demo.invalid@localhost',status:'Active'};
const permissions={view_intelligence:true,add_intelligence:true,human_validation:true,administration:true,
  manage_watchlist:true,review_intelligence:true,manage_campaigns:true,view_raw_evidence:true};
const access={status:'Active',geographic_scope:'Nationwide',province:'',permissions,role:'Administrator'};
const DEMO_VISIBLE_CAMPAIGN_IDS=new Set(['DEMO-CAMPAIGN-01','DEMO-CAMPAIGN-04']);
const campaigns=demoCampaigns.filter(c=>DEMO_VISIBLE_CAMPAIGN_IDS.has(c.id)).map(c=>({
 id:c.id,name:c.name,description:'Approved, sanitized BAWASLU campaign snapshot',
 primary_keywords:c.primary_keywords||[],secondary_keywords:c.secondary_keywords||[],
 excluded_keywords:c.excluded_keywords||[],platforms:c.platforms||[],
 status:c.status||'DRAFT',run_count:c.captured_count?1:0,
 evidence_count:c.captured_count||0,assessed_relevant_count:c.assessed_relevant_count||0,
 created_at:'2026-11-03T00:00:00Z',date_from:null,date_to:null}));
let additionalCampaigns=[],reviewState={};
const selectedWatch=demoWatchlist.map(x=>x.name);
const accountNames=demoWatchlist.map(x=>({...x,related_topics:[],candidate_aliases:x.candidate_aliases||[]}));
const assessmentBySource=new Map(snapshot.map(x=>[x.campaignId+'|'+x.sourceId,x]));
const rowsFor=id=>demoAllEvidence.filter(x=>!id||String(x.campaignId)===String(id)).map(x=>{
 const assessment=assessmentBySource.get(x.campaignId+'|'+x.sourceId);
 return assessment?{...x,topics:assessment.topics,candidates:assessment.candidates,signals:assessment.signals,
 concerns:assessment.concerns,sentiment:assessment.sentiment,explanation:assessment.explanation,
 assessmentVersion:assessment.assessmentVersion,relevance_label:'RELEVANT'}:{...x,relevance_label:'NOT_ASSESSED',sentiment:'UNCLASSIFIED'};
});
const count=(arr,key)=>arr.reduce((out,x)=>{const k=String(typeof key==='function'?key(x):x[key]||'');if(k)out[k]=(out[k]||0)+1;return out},{});
const evidence=p=>({id:p.id,result_id:p.id,campaign_id:p.campaignId,platform:p.platform,content_type:'Post',
 published_at:p.date,author_name:p.author,author_display:p.author,observed_handle:p.author,
 text_content:p.text,canonical_url:'',thumbnail_url:null,relevance_label:p.relevance_label||'RELEVANT',
 sentiment:['POSITIVE','NEUTRAL','NEGATIVE'].includes(p.sentiment)?p.sentiment:'UNCLASSIFIED',
 original_sentiment:p.sentiment,review_state:reviewState[p.id]||'UNREVIEWED',
 engagement_total:Number(p.engagement?.engagement_total||p.engagement?.likes||0),
 likes:Number(p.engagement?.likes||0),comments:Number(p.engagement?.comments||0),views:Number(p.engagement?.views||0),
 source_record_id:p.id});
function inboxFinding(p){
 const topics=Array.isArray(p.topics)?p.topics:[];
 const flags=Array.isArray(p.signals)?p.signals:[];
 return {...evidence(p),campaign_name:p.campaign,assessment_version:p.assessmentVersion||1,
  model_version:'Saved AI assessment snapshot',relevance_confidence:.85,explanation:p.explanation,
  sentiment_explanation:p.explanation,is_relevant:true,
  has_saved_assessment:true,ai_assessed:true,is_flagged:!!p.flagged||flags.length>0,
  can_review_flag:true,human_review_status:reviewState[p.id]||'AWAITING_REVIEW',possible_issues:flags,
  topic_labels:topics,topic_suggestions:topics,category:topics[0]||'Not classified',public_concern_signals:p.concerns||[],
  candidate_signals:Array.isArray(p.candidates)?p.candidates:[],geographic_signals:[],
  // Demo-only mentions from source text; not verified incident geography.
  location_signals:demoProvinceMentions(p.text),
  potential_issue_signals:flags,incident_jurisdiction_review:{decision:'UNREVIEWED',incident_jurisdiction_verified:false},
  actionability:'REQUIRES_REVIEW',attention_assessment:{level:'REVIEW',reason:'Saved AI signal. Verify against original evidence.'}};
}
const allFindings=()=>snapshot.map(inboxFinding);
function chartData(rows){
 const dates=count(rows,p=>String(p.date||'').slice(0,10));
 const platforms=count(rows,p=>p.platform);
 const daily=Object.entries(dates).sort(([a],[b])=>a.localeCompare(b)).map(([date,n])=>({...Object.fromEntries(Object.keys(platforms).flatMap(key=>[[key+'__posts',rows.filter(p=>String(p.date||'').startsWith(date)&&p.platform===key).length],[key+'__engagement',0]])),date,posts:n}));
 const sentiments=count(rows,p=>['POSITIVE','NEGATIVE','NEUTRAL'].includes(p.sentiment)?p.sentiment:'UNCLASSIFIED');
 const categories=count(rows.filter(p=>Array.isArray(p.topics)&&p.topics.length),p=>p.topics[0]);
 const topics=Object.entries(categories).map(([topic,n])=>({topic,count:n})).sort((a,b)=>b.count-a.count);
 const keywordCloud=[...new Set(campaigns.flatMap(c=>c.primary_keywords||[]))].slice(0,80)
  .map(word=>({word,count:rows.filter(p=>String(p.text||'').toLowerCase().includes(String(word).toLowerCase())).length}));
 const categoryRows=topics.map(t=>{
  const matching=rows.filter(p=>(p.topics||[]).includes(t.topic));
  const sc=count(matching,p=>p.sentiment);
  return {name:t.topic,count:t.count,sentiment:{Positive:sc.POSITIVE||0,Neutral:sc.NEUTRAL||0,Negative:sc.NEGATIVE||0},
   sample_posts:matching.slice(0,8).map(p=>({id:p.id,author:p.author,date:p.date,text:p.text,platform:p.platform}))};
 });
 const authorTotals={};for(const p of rows){const a=p.author||'Sumber contoh';authorTotals[a]??={name:a,platform:p.platform,engagement:0,followers:0};
  authorTotals[a].engagement+=Number(p.engagement?.engagement_total||p.engagement?.likes||0)+Number(p.engagement?.comments||0)+Number(p.engagement?.shares||0);}
 return {statistics:{messages:rows.length,engagement:rows.reduce((n,p)=>n+Number(p.engagement?.engagement_total||p.engagement?.likes||0),0),
  accounts:new Set(rows.map(p=>p.author)).size,platforms:Object.keys(platforms).length},
 platforms, sentiment:sentiments,sentiments, daily_platform_trend:daily,activity:daily,
 topics_and_themes:{
  categories:categoryRows,subject_categories:topics,classified_count:rows.filter(p=>(p.topics||[]).length>0).length,total:rows.length,
  total_mentions:rows.length,categorized_mentions:rows.filter(p=>(p.topics||[]).length>0).length,
  pending_assessment_mentions:rows.filter(p=>p.relevance_label==='NOT_ASSESSED').length,
  uncategorized_mentions:rows.filter(p=>!(p.topics||[]).length).length},
 top_accounts_engagement:Object.values(authorTotals).sort((a,b)=>b.engagement-a.engagement).slice(0,12),
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
 if(path==='/api/functions/integrationStatus')return {status:'OFFLINE_DEMO',providers:[]};
 if(path==='/api/functions/intelligenceAssistant'){
  const id=window.localStorage.getItem('bawaslu-language')==='id';
  return {answer:id?('Demo: '+snapshot.length+' catatan bukti tersimpan tersedia untuk ditinjau. Ini jawaban simulasi, bukan penilaian AI baru.'):
    ('Demo: '+snapshot.length+' saved evidence records are available for exploration. This is a preset answer, not a new AI assessment.'),
    records:snapshot.slice(0,3).map(inboxFinding),provider:'READ_ONLY_DEMO',grounding:{accessible_count:snapshot.length,source_types:['SOCIAL_LISTENING']},demo:true};
 }
 if(path.startsWith('/api/assistant-history'))return {threads:[],messages:[],items:[],thread:null,demo:true};
 const expandedOfflineTranslations={"The mention of Gibran's ijazah (diploma) in the context of a political challenge indicates a relevant electoral discussion.":"Penyebutan ijazah Gibran dalam konteks gugatan politik menunjukkan adanya diskusi yang relevan dengan pemilu.","The text discusses Gibran's political situation in relation to a court decision, which is relevant to electoral matters.":"Teks membahas situasi politik Gibran terkait putusan pengadilan yang relevan dengan urusan pemilu.","The post discusses Gibran's political conduct during the election process, which is relevant to electoral discussions.":"Unggahan membahas tindakan politik Gibran selama proses pemilu yang relevan dengan diskusi kepemiluan.","The post discusses the educational qualifications of presidential candidates, which is relevant to the electoral context.":"Unggahan membahas kualifikasi pendidikan calon presiden yang relevan dengan konteks pemilu.","The text discusses political controversies surrounding Gibran, which is relevant to electoral oversight and public concern.":"Teks membahas kontroversi politik seputar Gibran yang relevan dengan pengawasan pemilu dan kekhawatiran publik.","The text discusses a legal ruling regarding Gibran's educational certificate, which is relevant to the electoral context.":"Teks membahas putusan hukum mengenai surat keterangan pendidikan Gibran yang relevan dengan konteks pemilu.","The text discusses a legal ruling regarding Gibran's diploma, which is relevant to the electoral context.":"Teks membahas putusan hukum mengenai ijazah Gibran yang relevan dengan konteks pemilu.","The text discusses the political implications of a court ruling regarding Gibran's educational credentials, which is relevant to the electoral context.":"Teks membahas implikasi politik putusan pengadilan mengenai dokumen pendidikan Gibran dalam konteks pemilu.","The content discusses a legal matter involving Gibran Rakabuming Raka, which is relevant to the electoral context due to the mention of a lawsuit related to his educational credentials.":"Konten membahas perkara hukum yang melibatkan Gibran Rakabuming Raka, relevan dengan konteks pemilu karena menyebut gugatan terkait dokumen pendidikannya.","The text discusses a legal action related to Gibran's ijazah, which is relevant to the electoral context.":"Teks membahas tindakan hukum terkait ijazah Gibran yang relevan dengan konteks pemilu.","The text discusses political lobbying related to Gibran's educational credentials, which is relevant to the electoral context.":"Teks membahas lobi politik terkait dokumen pendidikan Gibran yang relevan dengan konteks pemilu.","The text discusses a political demand related to Gibran's educational qualifications, which is relevant to the electoral context.":"Teks membahas tuntutan politik terkait kualifikasi pendidikan Gibran yang relevan dengan konteks pemilu.","The text discusses an event related to Gibran's supporters showcasing a certificate, which is relevant to the electoral context.":"Teks membahas peristiwa terkait pendukung Gibran yang menunjukkan surat keterangan dalam konteks pemilu.","Not AI-scored":"Belum dinilai oleh AI","Not classified":"Belum diklasifikasikan"};
 const offlineTranslations={"AI suggestion only; original source remains unverified.":"Hanya saran AI; sumber asli tetap belum terverifikasi.","Human verified relevancy from uploaded BAWASLU 200 Dataset Human Verified.xlsx; no AI classification.":"Relevansi diverifikasi manusia berdasarkan dataset BAWASLU yang diunggah; belum dilakukan klasifikasi AI.","Provider Discover collected; awaiting OpenAI topic analysis":"Data dikumpulkan melalui Discover; sedang menunggu analisis topik oleh OpenAI.","Human verified relevancy from uploaded BAWASLU 200 Dataset Human Verified.xlsx; no AI classification. | Source-grounded public concern review; no legal finding.":"Relevansi diverifikasi manusia berdasarkan dataset BAWASLU yang diunggah; belum dilakukan klasifikasi AI. | Tinjauan kekhawatiran publik berdasarkan sumber, bukan temuan hukum.","The text discusses a political issue related to Gibran's educational credentials, which is relevant to the electoral context.":"Teks membahas persoalan politik terkait dokumen pendidikan Gibran, yang relevan dengan konteks pemilu.","The text discusses a legal decision related to Gibran's diploma, which is relevant to the electoral context.":"Teks membahas putusan hukum terkait ijazah Gibran, yang relevan dengan konteks pemilu.","The text discusses a legal proceeding related to Gibran's diploma, which is relevant to the electoral context.":"Teks membahas proses hukum terkait ijazah Gibran, yang relevan dengan konteks pemilu.","The text discusses Gibran's educational qualifications in the context of a legal proceeding, which is relevant to his candidacy.":"Teks membahas kualifikasi pendidikan Gibran dalam konteks proses hukum, yang relevan dengan pencalonannya.","The text discusses election supervision and mentions Bawaslu, aligning with the campaign's objective.":"Teks membahas pengawasan pemilu dan menyebut Bawaslu, sesuai dengan tujuan kampanye pemantauan.","The text discusses reporting potential electoral violations to Bawaslu, which is directly related to election oversight.":"Teks membahas pelaporan potensi pelanggaran pemilu kepada Bawaslu, yang berkaitan langsung dengan pengawasan pemilu.","The hashtags include terms related to the election and electoral oversight, indicating topical relevance.":"Tagar memuat istilah terkait pemilu dan pengawasannya, sehingga relevan secara topik.","The text explicitly mentions BAWASLU and discusses a public discussion, which is relevant to electoral oversight.":"Teks secara eksplisit menyebut BAWASLU dan membahas diskusi publik yang relevan dengan pengawasan pemilu.","The text discusses Bawaslu's public information services, which is directly related to electoral operations.":"Teks membahas layanan informasi publik Bawaslu yang berkaitan langsung dengan penyelenggaraan pemilu.","The text discusses Bawaslu's oversight role in the election process, specifically regarding access to candidate data, which is directly related to electoral administration.":"Teks membahas peran pengawasan Bawaslu dalam proses pemilu, khususnya akses data kandidat yang berkaitan langsung dengan administrasi pemilu.","The text discusses Bawaslu's role in educating election monitors, which is directly related to election administration.":"Teks membahas peran Bawaslu dalam memberikan edukasi kepada pengawas pemilu, yang berkaitan langsung dengan administrasi pemilu.","The text discusses the ethical responsibilities and professionalism required of election organizers, which is directly related to the election process.":"Teks membahas tanggung jawab etis dan profesionalisme penyelenggara pemilu, yang berkaitan langsung dengan proses pemilu.","The text discusses a finding related to electoral violations, specifically multiple voting, which is relevant to the election process.":"Teks membahas temuan terkait dugaan pelanggaran pemilu, khususnya pemungutan suara berulang, yang relevan dengan proses pemilu.","The text discusses electoral outcomes and mentions BAWASLU in the context of alleged electoral fraud and dissatisfaction with the election process.":"Teks membahas hasil pemilu dan menyebut BAWASLU dalam konteks dugaan kecurangan serta ketidakpuasan terhadap proses pemilu.","The post discusses electoral issues and mentions BAWASLU and the upcoming election, making it relevant to the election process.":"Unggahan membahas isu pemilu serta menyebut BAWASLU dan pemilu mendatang, sehingga relevan dengan proses pemilu.","The text discusses Bawaslu's reminder to political parties about campaign regulations, which is directly related to electoral oversight.":"Teks membahas imbauan Bawaslu kepada partai politik mengenai peraturan kampanye, yang berkaitan langsung dengan pengawasan pemilu."};
 if(path==='/api/presentation/translate'){
   const original=String(payload.text||'');
   const translated=payload.language==='id'?(offlineTranslations[original]||expandedOfflineTranslations[original]||original):original;
   return {text:translated,language:payload.language||'id',translation_only:true,demo:true};
 }
 if(path==='/api/relevance-gates')return {items:[],gates:[]};
 if(path.includes('/campaign/')||path.includes('/external-import/'))return {ok:true,demo:true,status:'COMPLETED',evidence:[],records:[]};
 return {ok:true,demo:true,items:[],posts:[],findings:[],groups:[],campaigns:[]};
}
window.fetch=async (input,init={})=>{
 const url=typeof input==='string'?input:input?.url||'',u=new URL(url,window.location.href);
 const method=String(init.method||input?.method||'GET').toUpperCase();
 // Sole permitted demo mutation: anonymous feedback sent to the isolated
 // server endpoint. Intelligence records remain frozen in browser memory.
 if(u.origin===location.origin&&u.pathname==='/api/demo-feedback'&&method==='POST')
   return original(input,init);
 if(u.pathname.startsWith('/api/'))return response(localApi(url,init));
 // Only static asset reads are permitted. No network mutations of any kind.
 if(u.origin===location.origin&&['GET','HEAD'].includes(method)&&!/\/api\//.test(u.pathname))return original(input,init);
 return response({detail:'Blocked: read-only demo network isolation'},403);
};
// Defense in depth: catch any future library that tries to bypass the demo fetch adapter.
const demoXhrOpen=XMLHttpRequest.prototype.open;
XMLHttpRequest.prototype.open=function(method,url,...rest){
 const target=new URL(String(url||''),location.href);
 if(target.pathname.startsWith('/api/')||target.origin!==location.origin||!['GET','HEAD'].includes(String(method).toUpperCase()))
  throw new Error('Demo mode blocks API writes and external network requests');
 return demoXhrOpen.call(this,method,url,...rest);
};
try{
 if(navigator.sendBeacon)navigator.sendBeacon=()=>false;
}catch(_){}

window.__BAWASLU_DEMO_META__=Object.freeze({
 branch:'demo-isolated-20261103',dataset:'sanitized-production-snapshot',records:snapshot.length,
 snapshotDate:'2026-11-03',connectedToProduction:false,participantStorage:'memory-only'
});
window.__BAWASLU_DEMO_RESET__=()=>{additionalCampaigns.length=0;reviewState={};};
