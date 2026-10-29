import {useEffect,useState} from 'react';
import {ExternalLink,ImageOff,Smile,Meh,Frown,CircleHelp} from 'lucide-react';
import {base44} from '@/api/base44Client';
const platformName=v=>({tiktok:'TikTok',instagram:'Instagram',youtube:'YouTube',facebook:'Facebook',threads:'Threads',twitter:'X',x:'X',reddit:'Reddit',linkedin:'LinkedIn',online_news:'Online News'}[String(v||'').toLowerCase()]||String(v||'Unknown source'));
function Post({post}){
 const [imageError,setImageError]=useState(false);
 const sentiment=String(post.sentiment||'').toLowerCase();
 const [Icon,color,name]=sentiment==='positive'?[Smile,'text-green-700','Positive']:sentiment==='neutral'?[Meh,'text-amber-600','Neutral']:sentiment==='negative'?[Frown,'text-red-700','Negative']:[CircleHelp,'text-slate-400','Unclassified'];
 const url=/^https:\/\//i.test(post.canonical_url||'')?post.canonical_url:'';
 return <article aria-label={'Source post '+post.id} className="flex items-start gap-3 border-b border-[#e5ebef] py-4 last:border-0">
  <div className="flex h-16 w-16 shrink-0 items-center justify-center overflow-hidden rounded-lg bg-slate-100">{post.thumbnail_url&&!imageError?<img src={post.thumbnail_url} alt="" loading="lazy" referrerPolicy="no-referrer" className="h-full w-full object-cover" onError={()=>setImageError(true)}/>:<ImageOff size={20} className="text-slate-400"/>}</div>
  <div className="min-w-0 flex-1">
   <div className="flex flex-wrap items-center gap-x-3 gap-y-1"><strong className="text-sm text-[#19324a]">{post.author_name||'Source account unavailable'}</strong><span className="text-xs text-[#60768c]">{platformName(post.platform)} · {post.published_at?String(post.published_at).slice(0,10):'Undated'}</span></div>
   <p className="mt-1 whitespace-pre-wrap break-words text-sm leading-6 text-[#33475b]">{post.text_content||'No source text available'}</p>
   <div className="mt-1 flex flex-wrap items-center gap-x-3 text-xs text-[#60768c]"><span>{post.content_type||'Post'} · #{post.id}</span>{url&&<a href={url} target="_blank" rel="noopener noreferrer" className="inline-flex items-center gap-1 font-semibold text-[#117c6c] hover:underline">Original source <ExternalLink size={12}/></a>}</div>
  </div>
  <span title={'Saved sentiment: '+name} className={'flex shrink-0 flex-col items-center gap-1 '+color}><Icon size={22}/><span className="text-[10px]">{name}</span></span>
 </article>;
}
/** Full post list for the selected campaign, never the dashboard's 200-post sample. */
export default function CapturedPostList({campaignId}){
 const [posts,setPosts]=useState([]),[loading,setLoading]=useState(true),[error,setError]=useState('');
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
 },[campaignId]);
 return <section aria-label="Captured posts list" className="rounded-[13px] border border-[#dce5ed] bg-white px-5 py-2">
  {loading?<p role="status" className="py-6 text-sm text-[#60768c]">Loading captured posts…</p>:error?<p role="alert" className="py-6 text-sm text-red-700">Unable to load the complete post list: {error}</p>:posts.length?posts.map(post=><Post key={post.id} post={post}/>):<p className="py-6 text-sm text-[#60768c]">No captured posts for this campaign.</p>}
 </section>;
}
