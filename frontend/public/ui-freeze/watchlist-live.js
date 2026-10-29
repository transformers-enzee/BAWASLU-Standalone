(() => {
  'use strict';
  const ui=window.__watchlist;
  const $=selector=>document.querySelector(selector);
  const token=()=>localStorage.getItem('bawaslu_access_token')||'';
  let permitted=false,loading=new Set(),loaded=new Set();
  const safeUrl=value=>{try{const url=new URL(value);return ['http:','https:'].includes(url.protocol)?url.href:''}catch{return ''}};
  async function registry(action,data={},id=null){
    const response=await fetch('/api/functions/registry',{method:'POST',cache:'no-store',headers:{
      'Content-Type':'application/json','Authorization':'Bearer '+token()
    },body:JSON.stringify({action,data,id})});
    const result=await response.json().catch(()=>({}));
    if(!response.ok)throw Error(result.detail||result.error||'Registry unavailable ('+response.status+')');
    return result;
  }
  async function intel(action,data={}){
    const response=await fetch('/api/functions/intelligence',{method:'POST',cache:'no-store',headers:{
      'Content-Type':'application/json','Authorization':'Bearer '+token()
    },body:JSON.stringify({action,data})});
    const result=await response.json().catch(()=>({}));
    if(!response.ok)throw Error(result.detail||result.error||'Intelligence unavailable');
    return result;
  }
  function candidate(item,accounts){
    return {
      id:String(item.id),name:item.name,aliases:Array.isArray(item.candidate_aliases)?item.candidate_aliases:[],jurisdiction:[item.regency_city,item.province].filter(Boolean).join(', ')||'National',
      context:item.related_election||item.type||'Approved registry candidate',
      summary:item.description||'No officer-approved activity summary has been recorded. Review the original evidence before making an assessment.',
      posts:[],findings:[],accounts:accounts.filter(a=>String(a.watchlist_id)===String(item.id)).map(a=>({
        platform:a.platform,handle:a.handle||a.url,status:'Registered account · affiliation verification required',url:a.url
      }))
    };
  }
  async function reload(){
    const data=await registry('list');
    const candidates=(data.items||[]).filter(x=>String(x.type||'').toLowerCase()==='candidate')
      .map(x=>candidate(x,data.accounts||[]));
    const active=(data.items||[]).filter(x=>String(x.type||'').toLowerCase()==='candidate'&&x.status==='Active').map(x=>String(x.id));
    loaded.clear();
    ui.setData(candidates,active);
    if(!permitted)document.querySelectorAll('#addCandidate,#emptyAdd,[data-activate],[data-create-candidate],#stopTrack,#editCandidateAliases').forEach(b=>b.disabled=true);
    $('.content').style.visibility='visible';
    return data;
  }
  ui.onActivate=async id=>{
    if(!permitted){ui.notify('Watchlist management permission required.');return;}
    try{
      await registry('updateWatchlist',{status:'Active'},id);
      await reload();ui.closeModal();ui.renderProfile(id);ui.notify('Candidate tracking activated.');
    }catch(error){ui.notify('Tracking unchanged: '+error.message);}
  };
  ui.onStop=async id=>{
    if(!permitted){ui.notify('Watchlist management permission required.');return;}
    try{
      await registry('updateWatchlist',{status:'Inactive'},id);
      await reload();ui.closeModal();ui.showHome();ui.notify('Tracking stopped. Original source records are preserved.');
    }catch(error){ui.notify('Tracking unchanged: '+error.message);}
  };
  ui.onUpdateAliases=async (id,rawAliases)=>{
    if(!permitted){ui.notify('Watchlist management permission required.');return;}
    const aliases=String(rawAliases||'').split(',').map(x=>x.trim()).filter(Boolean);
    try{
      await registry('updateWatchlist',{candidate_aliases:aliases},id);
      await reload();ui.closeModal();ui.renderProfile(id);
      ui.notify('Officer-approved aliases saved to the canonical candidate identity.');
    }catch(error){ui.notify('Aliases not updated: '+error.message);}
  };
  ui.onCreate=async (rawName,rawAliases='')=>{
    if(!permitted){ui.notify('Watchlist management permission required.');return;}
    const name=String(rawName||'').trim();
    if(name.length<3||name.length>255){ui.notify('Enter the approved candidate full name (3–255 characters).');return;}
    const duplicate=ui.getCandidates().find(c=>c.name.toLowerCase()===name.toLowerCase());
    if(duplicate){ui.notify('Candidate already exists; select that identity from the directory.');return;}
    try{
      const aliases=String(rawAliases||'').split(',').map(x=>x.trim()).filter(Boolean);
      const response=await registry('createWatchlist',{name,type:'Candidate',status:'Active',priority:'Medium',
        candidate_aliases:aliases});
      const id=String(response.item?.id||'');
      await reload();ui.closeModal();
      if(id)ui.renderProfile(id);ui.notify('Candidate registered and tracking activated.');
    }catch(error){ui.notify('Candidate not created: '+error.message);}
  };
  async function collectedPosts(id){
    const posts=[];
    for(let page=1;page<=10;page++){
      const result=await registry('watchlistCapturedFeed',{page,page_size:50},id);
      posts.push(...(result.posts||[]));
      if(posts.length>=Number(result.total||0)||!result.posts?.length)break;
    }
    return posts;
  }
  function mapCaptured(post){
    const sentiments=[...new Set((post.saved_assessments||[])
      .map(a=>String(a.sentiment||'').toUpperCase())
      .filter(v=>['POSITIVE','NEGATIVE','NEUTRAL'].includes(v)))];
    const sentiment=sentiments.length===1?
      sentiments[0][0]+sentiments[0].slice(1).toLowerCase():'Unknown';
    const validatedFlag=(post.saved_assessments||[]).some(a=>a.is_flagged===true);
    return {
      id:'SRC-'+post.id,kind:'own',platform:post.platform||'Unknown platform',
      source:post.account||post.author_name||'Registered account · attribution not independently verified',
      date:String(post.published_at||''),text:post.text||'',
      sentiment,flag:validatedFlag, url:safeUrl(post.url),
      description:'Stored captured account post; candidate affiliation requires human verification.'
    };
  }
  function mapEarned(record){
    const id=String(record.source_id||record.intelligence_id||record.id);
    const sentimentRaw=String(record.sentiment_label||record.sentiment||'').toLowerCase();
    const sentiment=['positive','negative','neutral'].includes(sentimentRaw)?
      sentimentRaw[0].toUpperCase()+sentimentRaw.slice(1):'Unknown';
    return {
      id:'INT-'+id,kind:'earned',platform:record.platform||record.source_type||'Source',
      source:record.author||record.observed_publisher_handle||record.source_name||'Public source',
      date:String(record.publication_datetime||record.publication_date||record.collection_datetime||''),
      text:record.original_content||record.title||'',sentiment,flag:false,
      url:safeUrl(record.source_url),description:'Evidence-linked intelligence record'
    };
  }
  ui.onProfile=async id=>{
    if(loaded.has(id)||loading.has(id))return;
    const candidate=ui.getCandidate(id);
    if(!candidate)return;
    loading.add(id);
    try{
      const [captured,actor]=await Promise.allSettled([
        collectedPosts(id),intel('actorPicture',{actor_id:id})
      ]);
      const own=captured.status==='fulfilled'?captured.value.map(mapCaptured):[];
      const records=actor.status==='fulfilled'?(actor.value.records||[]):[];
      const related=records.map(mapEarned);
      const known=new Set(own.map(post=>post.url).filter(Boolean));
      candidate.posts=[...own,...related.filter(post=>!post.url||!known.has(post.url))]
        .sort((a,b)=>String(b.date||'').localeCompare(String(a.date||'')));
      candidate.findings=[];
      loaded.add(id);
      ui.renderProfile(id);
      if(captured.status==='rejected'&&actor.status==='rejected')
        ui.notify('Source feeds unavailable. The registered candidate profile is still available.');
      // Preserve original links in the post detail dialogs.
    }catch(error){ui.notify('Unable to load candidate evidence: '+error.message);}
    finally{loading.delete(id);}
  };
  document.addEventListener('click',event=>{
    const target=event.target.closest('[data-post]');
    if(!target)return;
    const candidate=ui.getCandidate(ui.selected());
    const post=candidate?.posts.find(p=>p.id===target.dataset.post);
    const url=safeUrl(post?.url);
    if(url){
      const a=document.createElement('a');
      a.href=url;a.target='_blank';a.rel='noopener noreferrer';
      a.textContent='View original source →';a.className='relatedlink';
      a.style.display='inline-block';a.style.marginTop='12px';
      $('#modalBody')?.appendChild(a);
    }
  });
  async function boot(){
    try{
      const access=await registry('myAccess');
      permitted=access.access?.permissions?.manage_watchlist===true;
      await reload();
    }catch(error){
      $('.content').style.visibility='visible';
      const notice=$('.notice');
      if(notice)notice.textContent='Unable to load authorised candidate registry: '+error.message;
      ui.setData([],[]);
    }
  }
  boot();
})();