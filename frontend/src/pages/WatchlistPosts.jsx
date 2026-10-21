import { useEffect, useMemo, useState } from 'react';
import { Link, useParams } from 'react-router-dom';
import { registry, useRegistry } from '@/components/intel/useIntel';

const PAGE_SIZE=20;
const number=value=>Number(value||0).toLocaleString();
const sourceUrl=value=>{try{const url=new URL(value);return ['http:','https:'].includes(url.protocol)?url.href:null}catch{return null}};

export default function WatchlistPosts(){
 const {id}=useParams();
 const {items,accounts,loading,error}=useRegistry();
 const item=items.find(x=>String(x.id)===String(id));
 const linked=useMemo(()=>accounts.filter(x=>String(x.watchlist_id)===String(id)),[accounts,id]);
 const platforms=useMemo(()=>[...new Set(linked.map(x=>String(x.platform||'').trim()).filter(Boolean))].sort(),[linked]);
 const [platform,setPlatform]=useState('');
 const [accountId,setAccountId]=useState('');
 const [dateFrom,setDateFrom]=useState('');
 const [dateTo,setDateTo]=useState('');
 const [searchText,setSearchText]=useState('');
 const [search,setSearch]=useState('');
 const [page,setPage]=useState(1);
 const [result,setResult]=useState({posts:[],total:0,page_size:PAGE_SIZE,linked_accounts:0,matchable_accounts:0});
 const [busy,setBusy]=useState(false),[feedError,setFeedError]=useState('');
 const [syncInfo,setSyncInfo]=useState(null);
 const [refreshTick,setRefreshTick]=useState(0);
 useEffect(()=>{const timer=window.setInterval(()=>setRefreshTick(x=>x+1),30000);return ()=>window.clearInterval(timer)},[]);
 useEffect(()=>{
  if(!item)return;
  let active=true;
  registry('watchlistSyncStatus',{},id).then(data=>{if(active)setSyncInfo(data)}).catch(()=>{});
  return ()=>{active=false};
 },[id,item?.id,refreshTick]);
 useEffect(()=>{
  if(!item)return;
  let active=true;
  setBusy(true);setFeedError('');
  registry('watchlistCapturedFeed',{page,page_size:PAGE_SIZE,platform,account_id:accountId,date_from:dateFrom,date_to:dateTo,search},id)
   .then(data=>{if(active)setResult(data)})
   .catch(e=>{if(active)setFeedError(e?.response?.data?.error||e.message||'Unable to load captured posts')})
   .finally(()=>{if(active)setBusy(false)});
  return ()=>{active=false};
 },[id,item?.id,page,platform,accountId,dateFrom,dateTo,search,refreshTick]);
 const posts=result.posts||[];
 const total=Number(result.total||0);
 const pages=Math.max(1,Math.ceil(total/PAGE_SIZE));
 const totals=posts.reduce((sum,post)=>({
  views:sum.views+(Number(post.views)||0),
  engagement:sum.engagement+(Number(post.engagement_total)||0)
 }),{views:0,engagement:0});
 function resetFilters(){
  setPlatform('');setAccountId('');setDateFrom('');setDateTo('');setSearchText('');setSearch('');setPage(1);
 }
 if(loading)return <p className="text-sm text-slate-500">Loading Watchlist profile…</p>;
 if(!item)return <div className="space-y-3"><Link to="/watchlist" className="text-sm text-[#126d91]">← Watchlist</Link><p role="alert" className="text-sm text-red-700">{error||'Watchlist profile unavailable'}</p></div>;
 return <main className="space-y-4" aria-label="Watchlist captured posts">
  <div className="space-y-2">
   <Link to="/watchlist" className="text-sm text-[#126d91]">← Back to Watchlist</Link>
   <div className="flex flex-wrap items-start justify-between gap-3">
    <div>
     <p className="text-xs uppercase tracking-wider text-slate-500">Watchlist / Captured account posts</p>
     <h1 className="intel-heading mt-1">{item.name}</h1>
     <p className="text-sm text-slate-500 mt-1">{linked.length} registered account{linked.length===1?'':'s'} · Posts already stored in BAWASLU</p>
    </div>
    <Link to="/watchlist" className="intel-ghost text-xs">Manage account URLs</Link>
   </div>
  </div>
  <section className="intel-card p-3 space-y-2" aria-label="Automatic account monitoring">
   <div className="flex flex-wrap items-center justify-between gap-2"><h2 className="font-semibold text-sm">Automatic account monitoring</h2><span className="text-xs text-slate-500">Refreshes this feed every 30 seconds while open</span></div>
   {syncInfo?.enabled?
    <p className="text-xs text-teal-700">Enabled · Checking public account feeds every {syncInfo.interval_minutes} minutes while the monitoring worker is running. Each check may use up to {syncInfo.estimated_max_credits_per_check} SocialCrawl credits per account.</p>:
    <p className="text-xs text-amber-800">Automatic collection is not active. An administrator must enable the background worker and set a positive daily SocialCrawl credit budget before new accounts can be fetched automatically.</p>}
   {syncInfo&&<div className="grid sm:grid-cols-2 gap-2">{syncInfo.accounts?.map(x=><div key={x.account_id} className="rounded-md bg-slate-50 px-3 py-2 text-xs space-y-1"><div className="flex justify-between gap-2"><strong>{x.platform} · {x.handle||'Profile URL'}</strong><span className="text-slate-600">{x.state==='WAITING'?'Monitoring':x.state==='PENDING'?'Queued':x.state==='RUNNING'?'Fetching':x.state==='BUDGET_PAUSED'?'Budget paused':x.state==='ERROR'?'Error':x.state==='NEEDS_HANDLE'?'Handle required':x.state==='UNSUPPORTED'?'Unsupported':x.state}</span></div><p className="text-slate-500">Last checked: {x.last_checked_at?new Date(x.last_checked_at+'Z').toLocaleString():'Not yet'} · Captured: {x.total_posts}</p>{x.last_error&&<p className="text-amber-800">{x.last_error}</p>}</div>)}</div>}
   <p className="text-[11px] text-slate-500">New uploads appear after the next successful provider check, not instantly. Historical author-name matches are unverified; reading the feed does not consume additional credits.</p>
  </section>
  <form onSubmit={e=>{e.preventDefault();setPage(1);setSearch(searchText.trim())}} className="intel-card p-3 space-y-3" aria-label="Filter captured account posts">
   <div className="grid grid-cols-2 lg:grid-cols-5 gap-2">
    <label className="text-xs">Platform
     <select value={platform} onChange={e=>{setPlatform(e.target.value);setAccountId('');setPage(1)}} className="intel-input mt-1 w-full">
      <option value="">All platforms</option>
      {platforms.map(x=><option key={x} value={x}>{x}</option>)}
     </select>
    </label>
    <label className="text-xs">Account
     <select value={accountId} onChange={e=>{setAccountId(e.target.value);setPage(1)}} className="intel-input mt-1 w-full">
      <option value="">All accounts</option>
      {linked.filter(x=>!platform||x.platform.toLowerCase()===platform.toLowerCase()).map(x=><option key={x.id} value={x.id}>{x.platform} · {x.handle||x.url}</option>)}
     </select>
    </label>
    <label className="text-xs">From date<input type="date" value={dateFrom} max={dateTo||undefined} onChange={e=>{setDateFrom(e.target.value);setPage(1)}} className="intel-input mt-1 w-full"/></label>
    <label className="text-xs">To date<input type="date" value={dateTo} min={dateFrom||undefined} onChange={e=>{setDateTo(e.target.value);setPage(1)}} className="intel-input mt-1 w-full"/></label>
    <label className="text-xs">Search captured text<input value={searchText} onChange={e=>setSearchText(e.target.value)} placeholder="Search post content" className="intel-input mt-1 w-full" maxLength={120}/></label>
   </div>
   <div className="flex flex-wrap gap-2">
    <button type="submit" className="intel-button text-xs">Apply search</button>
    <button type="button" className="intel-ghost text-xs" onClick={resetFilters}>Clear filters</button>
   </div>
  </form>
  <div className="grid grid-cols-3 gap-2">
   {[['Matching posts',number(total)],['Views · this page',number(totals.views)],['Engagement · this page',number(totals.engagement)]].map(([label,value])=><div key={label} className="intel-card px-3 py-3 min-w-0"><p className="text-xs text-slate-500">{label}</p><strong className="text-lg tabular-nums break-words">{value}</strong></div>)}
  </div>
  {result.matchable_accounts===0&&linked.length>0&&<p role="note" className="text-sm text-amber-800">None of these account URLs has an identifiable profile handle. Add a valid public profile URL and account handle to enable exact matching.</p>}
  {feedError&&<p role="alert" className="intel-card p-3 text-sm text-red-700">{feedError}</p>}
  {busy?<p role="status" className="text-sm text-slate-500">Loading captured account posts…</p>:!feedError&&<>
   <section className="space-y-2" aria-label="Matched captured posts">
    {posts.map(post=><article key={post.id} className="intel-card p-4 space-y-2">
     <div className="flex flex-wrap items-center gap-x-3 gap-y-1 text-xs text-slate-500">
      <span className="font-semibold text-slate-700">{post.platform||'Unknown platform'} · {post.account||post.author_name||'Unknown account'}</span>
      <span>{post.published_at?String(post.published_at).slice(0,16).replace('T',' '):'Date unavailable'}</span>
      {post.match_method==='author_name_unverified'&&<span className="text-amber-700">Author-name match · unverified</span>}
     </div>
     <p className="text-sm text-slate-700 whitespace-pre-wrap break-words">{post.text||'No text available'}</p>
     <div className="flex flex-wrap gap-3 text-xs text-slate-500">
      <span>Views: {post.views==null?'—':number(post.views)}</span>
      <span>Likes: {post.likes==null?'—':number(post.likes)}</span>
      <span>Comments: {post.comments==null?'—':number(post.comments)}</span>
      <span>Shares: {post.shares==null?'—':number(post.shares)}</span>
      <span>Engagement: {post.engagement_total==null?'—':number(post.engagement_total)}</span>
     </div>
     {sourceUrl(post.url)&&<a className="text-xs font-semibold text-[#126d91] hover:underline" href={sourceUrl(post.url)} target="_blank" rel="noopener noreferrer">View original post ↗</a>}
    </article>)}
    {!posts.length&&<div className="intel-card p-6 text-sm text-slate-500">{linked.length?'No previously captured posts matched these accounts and filters. This does not mean the accounts have no published posts.':'Add public account URLs and handles in Watchlist to begin matching stored evidence.'}</div>}
   </section>
   <div className="flex items-center justify-between gap-3 text-xs text-slate-500">
    <span>{total?('Showing '+number((page-1)*PAGE_SIZE+1)+'–'+number(Math.min(page*PAGE_SIZE,total))+' of '+number(total)):'No matching records'}</span>
    <div className="flex items-center gap-2">
     <button type="button" className="intel-ghost text-xs" disabled={page<=1} onClick={()=>setPage(x=>Math.max(1,x-1))}>Previous</button>
     <span>Page {page} / {pages}</span>
     <button type="button" className="intel-ghost text-xs" disabled={page>=pages} onClick={()=>setPage(x=>x+1)}>Next</button>
    </div>
   </div>
  </>}
 </main>;
}
