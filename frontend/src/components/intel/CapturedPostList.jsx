import {useEffect,useMemo,useRef,useState} from 'react';
import {ExternalLink,Smile,Meh,Frown,CircleHelp} from 'lucide-react';
import {base44} from '@/api/base44Client';
import SentimentCorrection from './SentimentCorrection';
import {compileBooleanPostSearch} from '@/lib/booleanPostSearch.mjs';
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
export default function CapturedPostList({campaignId,refreshKey=0,onSentimentCorrected,initialSearchMode='standard',showModeTabs=true}){
 const {language}=useLanguage();
 const isEnglish=language==='en';
 const t=(en,id)=>isEnglish?en:id;
 const [posts,setPosts]=useState([]),[loading,setLoading]=useState(true),[error,setError]=useState('');
 const [total,setTotal]=useState(0),[platforms,setPlatforms]=useState([]),[nextCursor,setNextCursor]=useState(null);
 const [paging,setPaging]=useState({key:'',history:[]}),[correctionRevision,setCorrectionRevision]=useState(0);
 // Feed pagination can finish after an officer saves a correction. Preserve
 // that correction in every subsequent page merge without another refresh.
 const savedCorrections=useRef(new Map());
 const onCorrectionSaved=(post,correction)=>{
  savedCorrections.current.set(sentimentCorrectionKey(campaignId,post.id),correction);
  setPosts(rows=>rows.map(row=>String(row.id)===String(post.id)?
    correctedSentimentPost(row,correction):row));
  onSentimentCorrected?.(correction);
  setCorrectionRevision(v=>v+1);
 };
 const [from,setFrom]=useState(''),[to,setTo]=useState(''),[keyword,setKeyword]=useState('');
 const [searchMode,setSearchMode]=useState(initialSearchMode==='boolean'?'boolean':'standard'),[booleanQuery,setBooleanQuery]=useState('');
 const booleanSearch=useMemo(()=>{
  if(searchMode!=='boolean'||!booleanQuery.trim())return {test:null,error:''};
  try{return {test:compileBooleanPostSearch(booleanQuery),error:''}}
  catch(error){return {test:null,error:error.message||'Invalid Boolean expression'}}
 },[searchMode,booleanQuery]);
 const [platform,setPlatform]=useState([]),[sentiment,setSentiment]=useState([]),[sort,setSort]=useState('newest');
 const [extra,setExtra]=useState({}),[advanced,setAdvanced]=useState(false),[facets,setFacets]=useState({}),[facetBusy,setFacetBusy]=useState(false),[facetError,setFacetError]=useState(false);
 const [suggest,setSuggest]=useState(false),[datePreset,setDatePreset]=useState('all');
 const [recent,setRecent]=useState([]);
 const setField=(key,value)=>setExtra(old=>({...old,[key]:value,...(key==='province'?{regency:[]}: {})}));
 const queryKey=JSON.stringify({mode:searchMode,query:searchMode==='standard'?keyword:booleanQuery,from,to,platform,sentiment,sort,...extra});
 const clear=()=>{setFrom('');setTo('');setKeyword('');setBooleanQuery('');setPlatform([]);setSentiment([]);setSort('newest');setExtra({});setDatePreset('all');setSuggest(false)};
 const toggle=(values,value,change)=>change(values.includes(value)?values.filter(x=>x!==value):[...values,value]);
 const selectDate=value=>{
  setDatePreset(value);
  if(value==='custom')return;
  if(value==='all'){setFrom('');setTo('');return}
  const parts=new Intl.DateTimeFormat('en-GB',{year:'numeric',month:'2-digit',day:'2-digit',timeZone:'Asia/Jakarta'}).formatToParts(new Date());
  const day=key=>parts.find(p=>p.type===key).value;
  const today=new Date(Date.UTC(Number(day('year')),Number(day('month'))-1,Number(day('day'))));
  const start=new Date(today);start.setUTCDate(start.getUTCDate()-(Number(value)-1));
  setFrom(start.toISOString().slice(0,10));setTo(today.toISOString().slice(0,10));
 };
 useEffect(()=>{
  let active=true;setFacets({});setFacetBusy(true);setFacetError(false);
  base44.functions.invoke('socialListening',{action:'campaignCapturedPosts',id:campaignId,data:{page_size:1,search:{},include_facets:true}})
   .then(r=>{if(active)setFacets(r.data?.facets||{})})
   .catch(()=>{if(active)setFacetError(true)})
   .finally(()=>{if(active)setFacetBusy(false)});
  return()=>{active=false};
 },[campaignId,refreshKey,correctionRevision]);
 const optionRows=(key)=>facets[key]||[];
 const suggestRows=[...recent.map(value=>({key:'recent',value})),...['hashtags','candidate','topic','author','province'].flatMap(key=>optionRows(key).map(row=>({...row,key})))]
   .filter(row=>!keyword.trim()||row.value.toLocaleLowerCase().includes(keyword.trim().toLocaleLowerCase())).slice(0,10);
 const addSuggestion=row=>{
  if(row.key==='hashtags'||row.key==='recent')setKeyword(row.value);
  else{setField(row.key,[...new Set([...(extra[row.key]||[]),row.value])]);setKeyword('')}
  setSuggest(false)
 };
 const remember=()=>{const q=keyword.trim();if(q)setRecent(old=>[q,...old.filter(x=>x!==q)].slice(0,5));setSuggest(false)};
 const selectedCount=platform.length+sentiment.length+Object.values(extra).reduce((n,v)=>n+(Array.isArray(v)?v.length:v==null||v===''?0:1),0)+(from||to?1:0);
 const filterLabels={platform:t('Platform','Platform'),sentiment:t('Sentiment','Sentimen'),province:t('Province','Provinsi'),regency:'Kabupaten / Kota',topic:t('Topic','Topik'),candidate:t('Candidate / actor','Kandidat / tokoh'),issue:t('Potential violation signals','Indikasi potensi pelanggaran'),concern:t('Public concerns','Kekhawatiran publik'),author:t('Author / account','Penulis / akun'),content_type:t('Content type','Jenis konten'),language:t('Language','Bahasa'),relevance:t('Electoral relevance','Relevansi pemilu'),assessment:t('Assessment status','Status penilaian'),location_confidence:t('Location evidence','Bukti lokasi'),engagement_total:t('Interactions','Interaksi'),likes:t('Likes','Suka'),comments:t('Comments','Komentar'),shares:t('Shares','Bagikan'),views:t('Views','Tayangan')};
 const filterValue=(key,value)=>{if(key==='platform')return platformName(value);if(key==='regency')return value.split(' | ').slice(1).join(' | ');const names={positive:t('Positive','Positif'),neutral:t('Neutral','Netral'),negative:t('Negative','Negatif'),unclassified:t('Unclassified','Belum diklasifikasikan'),pending:t('Pending','Menunggu'),processing:t('Processing','Sedang diproses'),assessed:t('Assessed','Dinilai'),failed:t('Failed','Gagal'),officer_corrected:t('Officer corrected','Dikoreksi petugas'),relevant:t('Relevant','Relevan'),highly_relevant:t('Highly relevant','Sangat relevan'),irrelevant:t('Irrelevant','Tidak relevan'),uncertain:t('Uncertain','Tidak pasti'),verified:t('Verified','Terverifikasi'),mentioned:t('Mentioned','Disebut'),unknown:t('Unknown','Tidak diketahui')};return ['sentiment','assessment','relevance','location_confidence'].includes(key)||value==='Unknown'?names[value.toLowerCase()]||value:value;};
 const chipLabel=key=>filterLabels[key]||(key.endsWith('_min')?t('Minimum','Minimum')+' '+(filterLabels[key.slice(0,-4)]||key):key.endsWith('_max')?t('Maximum','Maksimum')+' '+(filterLabels[key.slice(0,-4)]||key):key);
 const multi=(label,options,selected,change,format=x=>x)=> <details className="min-w-0 rounded-lg border border-[#dce5ed] bg-white px-3 py-2"><summary className="cursor-pointer text-sm font-medium">{label}{selected.length?' ('+selected.length+')':''}</summary><div className="mt-2 max-h-48 space-y-1 overflow-auto">{options.length?options.map(row=><label key={row.value} className="flex cursor-pointer items-center gap-2 text-xs"><input type="checkbox" checked={selected.includes(row.value)} onChange={()=>toggle(selected,row.value,change)}/><span className="flex-1 break-words">{format(row.value)}</span>{typeof row.count==='number'&&<span className="text-slate-500">{row.count}</span>}</label>):<p className="text-xs text-slate-500">{t('No saved values yet','Belum ada nilai tersimpan')}</p>}</div></details>;
 const pagingKey=String(campaignId)+'|'+queryKey+'|'+String(refreshKey)+'|'+String(correctionRevision);
 const history=paging.key===pagingKey?paging.history:[];
 const cursor=history.length?history[history.length-1]:null;
 useEffect(()=>{
  let active=true;setPosts([]);setTotal(0);setNextCursor(null);setLoading(true);setError('');
  if(booleanSearch.error){setLoading(false);return}
  const timer=setTimeout(async()=>{
   try{
    const response=await base44.functions.invoke('socialListening',{action:'campaignCapturedPosts',id:campaignId,data:{page_size:100,search:JSON.parse(queryKey),cursor}});
    const result=response.data||{};
    if(!Array.isArray(result.evidence)||result.server_filtered!==true||typeof result.has_more!=='boolean')throw Error('Invalid paginated search response');
    if(active){
     const all=result.evidence;
     setPosts(overlaySentimentCorrections(all,campaignId,savedCorrections.current));
     setTotal(Number(result.total||0));setPlatforms(result.platforms||[]);setNextCursor(result.next_cursor||null);
    }
   }catch(e){if(active)setError(e.response?.data?.detail||e.response?.data?.error||e.message||'Unable to load posts')}
   finally{if(active)setLoading(false)}
  },300);
  return()=>{active=false;clearTimeout(timer)};
 },[campaignId,refreshKey,queryKey,cursor,correctionRevision,booleanSearch.error]);
 const visible=posts;
 return <section data-i18n-exempt aria-label={t('Captured posts list','Daftar unggahan tersimpan')} lang={isEnglish?'en':'id'} className="rounded-[13px] border border-[#dce5ed] bg-white px-5 py-4">
  <div className="mb-4 space-y-2" data-testid="social-listening-search-modes">
   {showModeTabs&&<div className="flex flex-wrap gap-2" role="group" aria-label={t('Saved-post search mode','Mode pencarian unggahan tersimpan')}>
        <button type="button" aria-pressed={searchMode==='standard'} onClick={()=>setSearchMode('standard')} className={searchMode==='standard'?'intel-button text-xs':'intel-ghost text-xs'}>{t('Standard search','Pencarian standar')}</button>
        <button type="button" aria-pressed={searchMode==='boolean'} onClick={()=>setSearchMode('boolean')} className={searchMode==='boolean'?'intel-button text-xs':'intel-ghost text-xs'}>{t('Boolean search','Pencarian Boolean')}</button>
       </div>}
   <p className="text-xs text-slate-600">{searchMode==='boolean'
    ?t('Search saved post text using AND, OR, NOT, quoted phrases and parentheses. Case-insensitive. No new crawling or AI charges.','Cari teks unggahan tersimpan memakai AND, OR, NOT, frasa dalam tanda kutip, dan tanda kurung. Tidak membedakan huruf besar/kecil. Tanpa crawl atau biaya AI baru.')
    :t('Search saved text, author, account or URL. Switch modes for Boolean logic.','Cari teks, penulis, akun atau URL yang tersimpan. Ganti mode untuk memakai logika Boolean.')}</p>
  </div>
  <div className="mb-4 space-y-3" aria-label={t('Captured posts filters and sorting','Filter dan urutan unggahan')}>
   <div className="relative">
    {searchMode==='standard'?<label className="block text-xs font-semibold">{t('Search captured posts','Cari unggahan tersimpan')}<input className="intel-input mt-1 w-full" placeholder={t('Keywords, #hashtags, @accounts or source URL','Kata kunci, #tagar, @akun atau URL sumber')} value={keyword} maxLength={512} onFocus={()=>setSuggest(true)} onChange={e=>{setKeyword(e.target.value);setSuggest(true)}} onKeyDown={e=>{if(e.key==='Escape')setSuggest(false);if(e.key==='Enter')remember()}}/></label>
    :<label className="block text-xs font-semibold">{t('Boolean expression','Ekspresi Boolean')}<input data-testid="social-listening-boolean-query" className="intel-input mt-1 w-full" value={booleanQuery} onChange={e=>setBooleanQuery(e.target.value)} maxLength={512} spellCheck={false} placeholder={'Gibran AND (ijazah OR pendidikan) AND NOT hoaks'}/></label>}
    {searchMode==='standard'&&suggest&&suggestRows.length>0&&<div className="absolute z-20 mt-1 max-h-64 w-full overflow-auto rounded-lg border bg-white p-2 shadow-lg"><div className="flex items-center justify-between px-2 text-xs text-slate-500">{t('Suggestions from saved posts','Saran dari unggahan tersimpan')}<button type="button" onClick={()=>setSuggest(false)} aria-label={t('Close suggestions','Tutup saran')}>×</button></div>{suggestRows.map(row=><button key={row.key+row.value} type="button" onClick={()=>addSuggestion(row)} className="flex w-full items-center justify-between gap-2 rounded px-2 py-2 text-left text-sm hover:bg-slate-100"><span>{row.value}</span><span className="text-xs text-slate-500">{({recent:t('Recent search','Pencarian terakhir'),hashtags:t('Hashtag','Tagar'),candidate:t('Actor','Tokoh'),topic:t('Topic','Topik'),author:t('Author','Akun'),province:t('Location mention','Lokasi disebut')})[row.key]}{row.count!=null?' · '+row.count:''}</span></button>)}</div>}
   </div>
   <div className="flex flex-wrap gap-2 text-xs"><span className="self-center text-slate-500">{t('Quick views:','Tampilan cepat:')}</span>
    <button type="button" className="intel-ghost text-xs" onClick={()=>{clear();setSort('newest')}}>{t('Latest','Terbaru')}</button>
    <button type="button" className="intel-ghost text-xs" onClick={()=>{clear();setSentiment(['negative'])}}>{t('Negative','Negatif')}</button>
    <button type="button" className="intel-ghost text-xs" onClick={()=>{clear();setSort('engagement')}}>{t('High engagement','Interaksi tinggi')}</button>
    <button type="button" className="intel-ghost text-xs" onClick={()=>{clear();setField('assessment',['pending'])}}>{t('Pending assessment','Menunggu penilaian')}</button>
   </div>
   <div className="grid gap-2 sm:grid-cols-2 xl:grid-cols-3">
    <label className="text-xs">{t('Date range','Rentang tanggal')}<select className="intel-input mt-1" value={datePreset} onChange={e=>selectDate(e.target.value)}>{[['all',t('All dates','Semua tanggal')],['1',t('Today','Hari ini')],['7',t('Last 7 days','7 hari terakhir')],['30',t('Last 30 days','30 hari terakhir')],['90',t('Last 90 days','90 hari terakhir')],['custom',t('Custom range','Rentang khusus')]].map(([v,n])=><option key={v} value={v}>{n}</option>)}</select></label>
    {multi('Platform',platforms.map(value=>({value,count:optionRows('platform').find(x=>x.value===value)?.count})),platform,setPlatform,platformName)}
    {multi(sentiment.length?t('Sentiment','Sentimen'):t('All sentiments','Semua sentimen'),['positive','neutral','negative','unclassified'].map(value=>({value,count:optionRows('sentiment').find(x=>x.value===value)?.count})),sentiment,setSentiment,x=>({positive:t('Positive','Positif'),neutral:t('Neutral','Netral'),negative:t('Negative','Negatif'),unclassified:t('Unclassified','Belum diklasifikasikan')})[x])}
    {multi(t('Province (mentioned / verified)','Provinsi (disebut / terverifikasi)'),optionRows('province'),extra.province||[],v=>setField('province',v))}
    {multi('Kabupaten / Kota',optionRows('regency').filter(row=>!extra.province?.length||extra.province.includes(row.value.split(' | ')[0])),extra.regency||[],v=>setField('regency',v),x=>x.split(' | ').slice(1).join(' | '))}
    <label className="text-xs">{t('Sort by','Urutkan berdasarkan')}<select className="intel-input mt-1" value={sort} onChange={e=>setSort(e.target.value)}><option value="newest">{t('Newest first','Terbaru dahulu')}</option><option value="oldest">{t('Oldest first','Terlama dahulu')}</option><option value="engagement">{t('Engagement','Interaksi')}</option></select></label>
   </div>
   {datePreset==='custom'&&<div className="grid grid-cols-2 gap-2"><label className="text-xs">{t('From date','Dari tanggal')}<input className="intel-input mt-1" type="date" value={from} onChange={e=>setFrom(e.target.value)}/></label><label className="text-xs">{t('To date','Sampai tanggal')}<input className="intel-input mt-1" type="date" value={to} onChange={e=>setTo(e.target.value)}/></label></div>}
   <button type="button" className="intel-ghost text-xs" aria-expanded={advanced} onClick={()=>setAdvanced(v=>!v)}>{advanced?'−':'+'} {t('Advanced filters','Filter lanjutan')}</button>
   {advanced&&<div className="grid gap-2 rounded-lg bg-slate-50 p-3 sm:grid-cols-2 xl:grid-cols-3">
    {[['topic',t('Topic & themes','Topik & tema')],['candidate',t('Candidate / actor','Kandidat / tokoh')],['issue',t('Potential violation signals','Indikasi potensi pelanggaran')],['concern',t('Public concerns','Kekhawatiran publik')],['author',t('Author / account','Penulis / akun')],['content_type',t('Content type','Jenis konten')],['language',t('Language','Bahasa')],['relevance',t('Electoral relevance','Relevansi pemilu')],['assessment',t('Assessment status','Status penilaian')],['location_confidence',t('Location evidence','Bukti lokasi')]].map(([key,label])=><div key={key}>{multi(label,optionRows(key),extra[key]||[],v=>setField(key,v),x=>filterValue(key,x))}</div>)}
    {['engagement_total','likes','comments','shares','views'].map(key=><div key={key} className="rounded border bg-white p-2"><span className="text-xs font-medium">{({engagement_total:t('Interactions','Interaksi'),likes:t('Likes','Suka'),comments:t('Comments','Komentar'),shares:t('Shares','Bagikan'),views:t('Views','Tayangan')})[key]}</span><div className="mt-1 grid grid-cols-2 gap-1">{['min','max'].map(suffix=><label key={suffix} className="text-[10px]">{suffix==='min'?'Min':'Max'}<input type="number" min="0" max="999999999999999" step="1" className="intel-input mt-1 w-full" value={extra[key+'_'+suffix]??''} onChange={e=>setField(key+'_'+suffix,e.target.value===''?null:Math.max(0,Math.min(999999999999999,Math.floor(Number(e.target.value)))))}/></label>)}</div></div>)}
   </div>}
   <p className="text-xs text-slate-500">{t('Location mentions are not confirmed incident jurisdiction. Suggestions reflect saved, accessible posts; unknown metrics are not treated as zero.','Lokasi yang disebut bukan yurisdiksi kejadian terverifikasi. Saran berasal dari unggahan tersimpan yang dapat diakses; metrik tidak diketahui bukan nol.')}</p>
   {facetBusy&&<p className="text-xs text-slate-500">{t('Loading available filter suggestions…','Memuat saran filter…')}</p>}
   {facetError&&<p className="text-xs text-amber-700">{t('Suggestions unavailable. Text, date, platform and sentiment search remain available.','Saran tidak tersedia. Pencarian teks, tanggal, platform dan sentimen tetap tersedia.')}</p>}
   {selectedCount>0&&<div className="flex flex-wrap items-center gap-1 text-xs">{[...platform.map(v=>['platform',v]),...sentiment.map(v=>['sentiment',v]),...Object.entries(extra).flatMap(([k,v])=>Array.isArray(v)?v.map(x=>[k,x]):v==null||v===''?[]:[[k,String(v)]])].map(([k,v])=><button type="button" key={k+v} className="rounded-full bg-slate-100 px-2 py-1" onClick={()=>k==='platform'?toggle(platform,v,setPlatform):k==='sentiment'?toggle(sentiment,v,setSentiment):setField(k,Array.isArray(extra[k])?extra[k].filter(x=>x!==v):null)}>{chipLabel(k)}: {filterValue(k,v)} ×</button>)}</div>}
  </div>
  {searchMode==='boolean'&&<div className="mb-3 text-xs text-slate-600">
   <p>{t('Example','Contoh')}: <code className="rounded bg-slate-100 px-1 py-0.5">("Gibran Rakabuming" OR Gibran) AND ijazah AND NOT hoaks</code></p>
   {booleanSearch.error&&<p role="alert" data-testid="social-listening-boolean-error" className="mt-2 rounded border border-red-200 bg-red-50 px-3 py-2 text-red-700">{t('Check the Boolean expression: ','Periksa ekspresi Boolean: ')}{booleanSearch.error}</p>}
  </div>}
  <div className="mb-2 flex items-center justify-between gap-3 text-xs text-slate-600"><span role="status">{isEnglish?
    `${visible.length.toLocaleString()} on this page · ${total.toLocaleString()} matching captured posts`:
    `${visible.length.toLocaleString()} di halaman ini · ${total.toLocaleString()} unggahan tersimpan cocok`}
    {loading ? t(' · Loading…',' · Memuat…'):
      error ? t(' · Search failed',' · Pencarian gagal') : ''}</span><button type="button" className="intel-ghost text-xs" onClick={clear}>{t('Clear filters','Hapus filter')}</button></div>
  {error&&<p role="alert" className="py-3 text-sm text-red-700">{t('Unable to load saved post search:','Gagal memuat pencarian unggahan:')} {error}.</p>}
  {searchMode==='boolean'&&booleanSearch.error?null:visible.length?visible.map(post=><Post key={post.id} post={post} isEnglish={isEnglish} campaignId={campaignId} onCorrected={correction=>onCorrectionSaved(post,correction)}/>):loading?<p role="status" className="py-6 text-sm text-[#60768c]">{t('Loading captured posts…','Memuat unggahan…')}</p>:<p className="py-6 text-sm text-[#60768c]">{t('No captured posts match these filters.','Tidak ada unggahan yang cocok dengan filter ini.')}</p>}
  {!loading&&!error&&!booleanSearch.error&&(history.length>0||nextCursor)&&<div className="mt-4 flex items-center justify-between gap-2 text-xs">
   <button type="button" className="intel-ghost" disabled={!history.length} onClick={()=>setPaging({key:pagingKey,history:history.slice(0,-1)})}>{t('Previous page','Halaman sebelumnya')}</button>
   <span>{t('Page','Halaman')} {history.length+1}</span>
   <button type="button" className="intel-ghost" disabled={!nextCursor} onClick={()=>setPaging({key:pagingKey,history:[...history,nextCursor]})}>{t('Next page','Halaman berikutnya')}</button>
  </div>}
 </section>;
}
