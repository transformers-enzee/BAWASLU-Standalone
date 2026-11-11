import {useEffect,useMemo,useRef,useState} from 'react';
import {ExternalLink,Smile,Meh,Frown,CircleHelp} from 'lucide-react';
import {base44} from '@/api/base44Client';
import SentimentCorrection from './SentimentCorrection';
import {useLanguage} from '@/lib/LanguageContext';
import {correctedSentimentPost,overlaySentimentCorrections,sentimentCorrectionKey} from '@/lib/sentimentFeedState';
const platformName=v=>({tiktok:'TikTok',instagram:'Instagram',youtube:'YouTube',facebook:'Facebook',threads:'Threads',twitter:'X',x:'X',reddit:'Reddit',linkedin:'LinkedIn',online_news:'Online News'}[String(v||'').toLowerCase()]||String(v||'Unknown source'));
function Post({post,campaignId,onCorrected,isEnglish}){
 const [imageError,setImageError]=useState(false);
 const sentiment=String(post.sentiment||'').toLowerCase();
 const [Icon,color,name]=sentiment==='positive'?[Smile,'text-green-700',isEnglish?'Positive':'Positif']:
   sentiment==='neutral'?[Meh,'text-amber-600',isEnglish?'Neutral':'Netral']:
   sentiment==='negative'?[Frown,'text-red-700',isEnglish?'Negative':'Negatif']:
   [CircleHelp,'text-slate-400',isEnglish?'Unclassified':'Belum diklasifikasikan'];
 const url=/^https:\/\//i.test(post.canonical_url||'')?post.canonical_url:'';
 return <article aria-label={(isEnglish?'Source post ':'Unggahan sumber ')+post.id} className="flex items-start gap-3 border-b border-[#e5ebef] py-4 last:border-0">
  {post.thumbnail_url&&!imageError&&<div className="h-16 w-16 shrink-0 overflow-hidden rounded-lg bg-slate-100"><img src={post.thumbnail_url} alt="" loading="lazy" referrerPolicy="no-referrer" className="h-full w-full object-cover" onError={()=>setImageError(true)}/></div>}
  <div className="min-w-0 flex-1">
   <div className="flex flex-wrap items-center gap-x-3 gap-y-1"><strong className="text-sm text-[#19324a]">{post.author_display||(isEnglish?'Source author unavailable':'Nama akun tidak tersedia')}</strong><span className="text-xs text-[#60768c]">{platformName(post.platform)} · {post.published_at?String(post.published_at).slice(0,10):(isEnglish?'Undated':'Tanpa tanggal')}</span></div>
   <p data-i18n-exempt className="mt-1 whitespace-pre-wrap break-words text-sm leading-6 text-[#33475b]">{post.text_content||(isEnglish?'No source text available':'Teks sumber tidak tersedia')}</p>
   <div className="mt-1 flex flex-wrap items-center gap-x-3 text-xs text-[#60768c]"><span>{post.content_type||(isEnglish?'Post':'Unggahan')} · #{post.id}</span>{url&&<a href={url} target="_blank" rel="noopener noreferrer" className="inline-flex items-center gap-1 font-semibold text-[#9f3033] hover:underline" >{isEnglish?'Original source':'Sumber asli'} <ExternalLink size={12}/></a>}</div>
  </div>
  <div className="flex shrink-0 max-w-[180px] flex-col gap-1 items-end">
   <span title={(isEnglish?'Saved sentiment: ':'Sentimen tersimpan: ')+name} className={'flex shrink-0 flex-col items-center gap-1 '+color}><Icon size={22}/><span className="text-[10px]">{name}</span></span>
   {post.sentiment_correction&&<span className="text-[10px] text-green-700" >{isEnglish?'Officer corrected':'Dikoreksi petugas'}</span>}
   <SentimentCorrection campaignId={campaignId} resultId={post.id} value={post.sentiment}
     canEdit={post.can_correct_sentiment} onSaved={onCorrected}/>
  </div>
 </article>;
}
export default function CapturedPostList({campaignId,refreshKey=0,onSentimentCorrected}){
 const {language}=useLanguage();
 const isEnglish=language==='en';
 const t=(en,id)=>isEnglish?en:id;
 const [posts,setPosts]=useState([]),[loading,setLoading]=useState(true),[error,setError]=useState('');
 // Feed pagination can finish after an officer saves a correction. Preserve
 // that correction in every subsequent page merge without another refresh.
 const savedCorrections=useRef(new Map());
 const onCorrectionSaved=(post,correction)=>{
  savedCorrections.current.set(sentimentCorrectionKey(campaignId,post.id),correction);
  setPosts(rows=>rows.map(row=>String(row.id)===String(post.id)?
    correctedSentimentPost(row,correction):row));
  onSentimentCorrected?.(correction);
 };
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
     if(active)setPosts(overlaySentimentCorrections(all,campaignId,savedCorrections.current)); // Pages never overwrite officer edits.
     if(!result.has_more)break;
     if(!result.evidence.length||page>=100000)throw Error('Incomplete campaign feed');
     page++;
    }
    if(active)setPosts(overlaySentimentCorrections(all,campaignId,savedCorrections.current));
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
 return <section data-i18n-exempt aria-label={t('Captured posts list','Daftar unggahan tersimpan')} lang={isEnglish?'en':'id'} className="rounded-[13px] border border-[#dce5ed] bg-white px-5 py-4">
  <div className="mb-4 grid gap-3 sm:grid-cols-2 xl:grid-cols-3" aria-label={t('Captured posts filters and sorting','Filter dan urutan unggahan')}>
   <label className="text-xs">{t('From date','Dari tanggal')}<input className="intel-input mt-1" type="date" value={from} onChange={e=>setFrom(e.target.value)}/></label>
   <label className="text-xs">{t('To date','Sampai tanggal')}<input className="intel-input mt-1" type="date" value={to} onChange={e=>setTo(e.target.value)}/></label>
   <label className="text-xs">{t('Keyword','Kata kunci')}<input className="intel-input mt-1" placeholder={t('Search post text','Cari teks unggahan')} value={keyword} onChange={e=>setKeyword(e.target.value)}/></label>
   <label className="text-xs">Platform<select className="intel-input mt-1" value={platform} onChange={e=>setPlatform(e.target.value)}><option value="">{t('All platforms','Semua platform')}</option>{platforms.map(x=><option value={x} key={x}>{platformName(x)}</option>)}</select></label>
   <label className="text-xs">{t('Sentiment','Sentimen')}<select className="intel-input mt-1" value={sentiment} onChange={e=>setSentiment(e.target.value)}><option value="">{t('All sentiments','Semua sentimen')}</option>{['positive','neutral','negative','unclassified'].map(x=><option key={x} value={x}>{({positive:t('Positive','Positif'),neutral:t('Neutral','Netral'),negative:t('Negative','Negatif'),unclassified:t('Unclassified','Belum diklasifikasikan')})[x]}</option>)}</select></label>
   <label className="text-xs">{t('Sort by','Urutkan berdasarkan')}<select className="intel-input mt-1" value={sort} onChange={e=>setSort(e.target.value)}><option value="newest">{t('Newest first','Terbaru dahulu')}</option><option value="oldest">{t('Oldest first','Terlama dahulu')}</option><option value="engagement">{t('Engagement','Interaksi')}</option></select></label>
  </div>
  <div className="mb-2 flex items-center justify-between gap-3 text-xs text-slate-600"><span role="status">{isEnglish?
    `${visible.length.toLocaleString()} of ${posts.length.toLocaleString()} captured posts`:
    `${visible.length.toLocaleString()} dari ${posts.length.toLocaleString()} unggahan tersimpan`}
    {loading ? t(' · Loading more…',' · Memuat lainnya…'):
      error ? t(' · Partial results (loading failed)',' · Hasil tidak lengkap (gagal memuat)') : ''}</span><button type="button" className="intel-ghost text-xs" onClick={()=>{setFrom('');setTo('');setKeyword('');setPlatform('');setSentiment('');setSort('newest')}}>{t('Clear filters','Hapus filter')}</button></div>
  {error&&<p role="alert" className="py-3 text-sm text-red-700">{t('Unable to load the complete post list:','Gagal memuat seluruh unggahan:')} {error}. {t('Showing any records retrieved before the failure.','Menampilkan unggahan yang berhasil diambil sebelumnya.')}</p>}
  {visible.length?visible.map(post=><Post key={post.id} post={post} isEnglish={isEnglish} campaignId={campaignId} onCorrected={correction=>onCorrectionSaved(post,correction)}/>):loading?<p role="status" className="py-6 text-sm text-[#60768c]">{t('Loading captured posts…','Memuat unggahan…')}</p>:<p className="py-6 text-sm text-[#60768c]">{t('No captured posts match these filters.','Tidak ada unggahan yang cocok dengan filter ini.')}</p>}
 </section>;
}
