/* Demo-only read-only Home source. Derived from the same frozen assessments as /demo/smart-radar.html.
   No network, Supabase, generator, or mock trending values. */
import {snapshot} from './currentSnapshot.js';

const anchors={
 'Voter register accuracy':['daftar pemilih','pdpb','daftar pemilih tetap'],
 'Election money politics':['politik uang','serangan fajar'],
 'BAWASLU institutional trust':['reputasi bawaslu','kepercayaan publik terhadap bawaslu','kritik terhadap bawaslu','citra bawaslu','bawaslu tidak netral','bawaslu berpihak'],
 'Election dispute proceedings':['sengketa pemilu','sengketa pilkada','putusan dkpp'],
 'Candidate nomination process':['proses pencalonan','pendaftaran calon','verifikasi calon'],
 'Participatory election oversight':['pengawasan partisipatif','pengawas partisipatif']
};
const narrative=text=>{
 const body=String(text||'').toLowerCase();
 if(['selamat hari','sumpah pemuda','dirgahayu','selamat ulang tahun','ucapan selamat','memperingati hari'].some(x=>body.includes(x))&&
   !['pelanggaran','dugaan','laporan','pengawasan pemilu','sengketa','kecurangan'].some(x=>body.includes(x)))return '';
 return Object.entries(anchors).find(([,terms])=>terms.some(term=>body.includes(term)))?.[0]||'';
};
const countBy=(rows,key)=>rows.reduce((all,row)=>(all[key(row)]=(all[key(row)]||0)+1,all),{});
const unique=()=>{const seen=new Set();return snapshot.filter(row=>{if(seen.has(row.sourceId))return false;seen.add(row.sourceId);return true})};
const classify=p=>{
 if((p.signals||[]).length)return {key:'violation:'+p.sourceId,player:'violations',status:'pending'};
 if((p.concerns||[]).length)return {key:'concern:'+(p.topics?.[0]||p.sourceId),player:'concerns',status:'pending'};
 const anchor=narrative(p.text);
 if(anchor)return {key:'narrative:'+anchor,player:'narratives',status:'awareness'};
 return {key:'awareness:'+p.sourceId,player:null,status:'awareness'};
};
const inOperations=p=>(p.signals||[]).length>0||(p.topics||[]).includes('Electoral Operations')||
  (!(p.topics||[]).includes('BAWASLU Reputation')&&!(p.concerns||[]).length);
const inReputation=p=>(p.topics||[]).includes('BAWASLU Reputation')||
  ((p.concerns||[]).length>0&&!(p.signals||[]).length);
export function demoHomeRadar(){
 const records=unique();
 const groups=new Map();
 for(const row of records){
   const info=classify(row),group=groups.get(info.key)||{kind:info,rows:[]};
   group.rows.push(row);groups.set(info.key,group);
 }
 const findings=[...groups.values()].map(({kind,rows},index)=>({
   id:'DEMO-HOME-'+index,
   players:kind.player?[kind.player]:[],
   status:kind.status,
   perspectives:[...(rows.some(inOperations)?['operations']:[]),...(rows.some(inReputation)?['reputation']:[])],
   supporting_posts:rows.length,
   human_reviewed:false,next_followup:null,
   day_counts:countBy(rows,p=>String(p.date||'').slice(0,10)),
   geo_signal_counts:{}
 }));
 const topics=Object.entries(countBy(records,p=>p.topics?.[0]||((p.concerns||[]).length?'Public Concern':'Other')))
   .sort((a,b)=>b[1]-a[1]).map(([title,count],index)=>({id:index+1,title,count}));
 return {dashboard:{
   source_total:records.length,findings,geo_signal_counts:{},verified_incident_counts:{},
   mode:'SAVED_INBOX_SOURCE_OF_TRUTH',snapshot_as_of:'2026-11-03',truncated_to_inbox_window:snapshot.length>=300,
   geographic_scope_note:'No incident location is inferred from country, campaign, or author addresses.'
  },distribution:{operations:{topics:topics.slice(0,5),total:records.length,others:topics.slice(5).reduce((n,x)=>n+x.count,0)},
   reputation:{topics:topics.slice(0,5),total:records.length,others:topics.slice(5).reduce((n,x)=>n+x.count,0)}}};
}
