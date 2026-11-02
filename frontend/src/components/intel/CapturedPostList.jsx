import {useEffect,useMemo,useState} from 'react';
import {ExternalLink,Smile,Meh,Frown,CircleHelp} from 'lucide-react';
import {base44} from '@/api/base44Client';
const platformName=v=>({tiktok:'TikTok',instagram:'Instagram',youtube:'YouTube',facebook:'Facebook',threads:'Threads',twitter:'X',x:'X',reddit:'Reddit',linkedin:'LinkedIn',online_news:'Online News'}[String(v||'').toLowerCase()]||String(v||'Unknown source'));
function Post({post}){
 const [imageError,setImageError]=useState(false);
 const sentiment=String(post.sentiment||'').toLowerCase();
 const [Icon,color,name]=sentiment==='positive'?[Smile,'text-green-700','Positive']:sentiment==='neutral'?[Meh,'text-amber-600','Neutral']:sentiment==='negative'?[Frown,'text-red-700','Negative']:[CircleHelp,'text-slate-400','Unclassified'];
 const url=/^https:\/\//i.test(post.canonical_url||'')?post.canonical_url:'';
 return <article aria-label={'Source post '+post.id} className="flex items-start gap-3 border-b border-[#e5ebef] py-4 last:border-0">
  {post.thumbnail_url&&!imageError&&<div className="h-16 w-16 shrink-0 overflow-hidden rounded-lg bg-slate-100"><img src={post.thumbnail_url} alt="" loading="lazy" referrerPolicy="no-referrer" className="h-full w-full object-cover" onError={()=>setImageError(true)}/></div>}
  <div className="min-w-0 flex-1">
   <div className="flex flex-wrap items-center gap-x-3 gap-y-1"><strong className="text-sm text-[#19324a]">{post.author_display||'Source author unavailable'}</strong><span className="text-xs text-[#60768c]">{platformName(post.platform)} · {post.published_at?String(post.published_at).slice(0,10):'Undated'}</span></div>
   <p data-i18n-exempt className="mt-1 whitespace-pre-wrap break-words text-sm leading-6 text-[#33475b]">{post.text_content||'No source text available'}</p>
   <div className="mt-1 flex flex-wrap items-center gap-x-3 text-xs text-[#60768c]"><span>{post.content_type||'Post'} · #{post.id}</span>{url&&<a href={url} target="_blank" rel="noopener noreferrer" className="inline-flex items-center gap-1 font-semibold text-[#9f3033] hover:underline">Original source <ExternalLink size={12}/></a>}</div>
  </div>
  <span title={'Saved sentiment: '+name} className={'flex shrink-0 flex-col items-center gap-1 '+color}><Icon size={22}/><span className="text-[10px]">{name}</span></span>
 </article>;
}
export default function CapturedPostList({campaignId,refreshKey=0}){
 const [posts,setPosts]=useState([]),[loading,setLoading]=useState(true),[error,setError]=useState('');
 const [from,setFrom]=useState(''),[to,setTo]=useState(''),[keyword,setKeyword]=useState('');
 const [platform,setPlatform]=useState(''),[sentiment,setSentiment]=useState(''),[sort,setSort]=useState('newest');
 useEffect(()=>{
  let active=true;setPosts([]);setLoading(true);setError('');
  async function load(){
   try{
    const all=[],seen=new Set();let page=1;
    while(active){
     const response=await base44.functions.invoke('socialListening',{action:'campaignCapturedPosts',id:campaignId,data:{page,page_size:200}});
     const result=response.data||{};
     if(!Array.isArray(result.evidence)||typeof result.has_more!=='boolean')throw Error('Invalid campaign feed');
     for(const post of result.evidence){if(!seen.has(String(post.id))){seen.add(String(post.id));all.push(post)}}
     if(!result.has_more)break;
     if(!result.evidence.length||page>=100000)throw Error('Incomplete campaign feed');
     page++;
    }
    if(active)setPosts(all);
   }catch(e){if(active)setError(e.response?.data?.detail||e.response?.data?.error||e.message||'Unable to load posts')}
   finally{if(active)setLoading(false)}
  }
  if(campaignId)load();
  return()=>{active=false};
 },[campaignId,refreshKey]);
 const platforms=useMemo(()=>[...new Set(posts.map(p=>p.platform).filter(Boolean))].sort(),[posts]);
 const visible=useMemo(()=>{
  const q=keyword.toLocaleLowerCase('id-ID').trim();
  const items=posts.filter(p=>{
   const day=String(p.published_at||'').slice(0,10);
   return (!from||(day&&day>=from))&&(!to||(day&&day<=to))&&
    (!platform||p.platform===platform)&&(!sentiment||String(p.sentiment||'').toLowerCase()===sentiment)&&
    (!q||String(p.text_content||'').toLocaleLowerCase('id-ID').includes(q));
  });
  const score=p=>{try{const e=typeof p.engagement==='object'?p.engagement:JSON.parse(p.engagement_json||'{}');return Number(e.engagement_total||e.likes||0)}catch{return 0}};
  return items.sort((a,b)=>sort==='oldest'?String(a.published_at||'').localeCompare(String(b.published_at||'')):
   sort==='engagement'?score(b)-score(a):String(b.published_at||'').localeCompare(String(a.published_at||'')));
 },[posts,from,to,keyword,platform,sentiment,sort]);
 return <section aria-label="Captured posts list" className="rounded-[13px] border border-[#dce5ed] bg-white px-5 py-4">
  <div className="mb-4 grid gap-3 sm:grid-cols-2 xl:grid-cols-3" aria-label="Captured posts filters and sorting">
   <label className="text-xs">From date<input className="intel-input mt-1" type="date" value={from} onChange={e=>setFrom(e.target.value)}/></label>
   <label className="text-xs">To date<input className="intel-input mt-1" type="date" value={to} onChange={e=>setTo(e.target.value)}/></label>
   <label className="text-xs">Keyword<input className="intel-input mt-1" placeholder="Search post text" value={keyword} onChange={e=>setKeyword(e.target.value)}/></label>
   <label className="text-xs">Platform<select className="intel-input mt-1" value={platform} onChange={e=>setPlatform(e.target.value)}><option value="">All platforms</option>{platforms.map(x=><option value={x} key={x}>{platformName(x)}</option>)}</select></label>
   <label className="text-xs">Sentiment<select className="intel-input mt-1" value={sentiment} onChange={e=>setSentiment(e.target.value)}><option value="">All sentiments</option>{['positive','neutral','negative','unclassified'].map(x=><option key={x} value={x}>{x[0].toUpperCase()+x.slice(1)}</option>)}</select></label>
   <label className="text-xs">Sort by<select className="intel-input mt-1" value={sort} onChange={e=>setSort(e.target.value)}><option value="newest">Newest first</option><option value="oldest">Oldest first</option><option value="engagement">Engagement</option></select></label>
  </div>
  <div className="mb-2 flex items-center justify-between gap-3 text-xs text-slate-600"><span>{visible.length.toLocaleString()} of {posts.length.toLocaleString()} captured posts</span><button type="button" className="intel-ghost text-xs" onClick={()=>{setFrom('');setTo('');setKeyword('');setPlatform('');setSentiment('');setSort('newest')}}>Clear filters</button></div>
  {loading?<p role="status" className="py-6 text-sm text-[#60768c]">Loading captured posts…</p>:error?<p role="alert" className="py-6 text-sm text-red-700">Unable to load the complete post list: {error}</p>:visible.length?visible.map(post=><Post key={post.id} post={post}/>):<p className="py-6 text-sm text-[#60768c]">No captured posts match these filters.</p>}
 </section>;
}
