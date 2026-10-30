(() => {
  'use strict';
  const ui=window.__watchlist;
  const $=selector=>document.querySelector(selector);
  const token=()=>localStorage.getItem('bawaslu_access_token')||'';
  const campaignId=new URLSearchParams(window.location.search).get('campaign_id');
  if(campaignId)document.documentElement.classList.add('campaign-embedded');
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

  // Recommendations stay inside the existing Add Candidate modal, scoped to
  // the current Social Listening campaign and backed by saved source IDs.
  let suggestions=[],suggestionsLoading=false,suggestionsError='',suggestionsFetchedAt=0,suggestionsRequest=null;
  const escapeHTML=value=>String(value??'').replace(/[&<>"']/g,char=>({
    '&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'
  }[char]));
  const normalizeName=value=>String(value||'').normalize('NFKC').toLocaleLowerCase()
    .replace(/[^\p{L}\p{N}]+/gu,' ').trim();
  const exactCandidate=item=>ui.getCandidates().find(candidate=>
    [candidate.name,...candidate.aliases].some(alias=>normalizeName(alias)===normalizeName(item.name)));
  // Shared distinctive first name plus an additional token means review, not
  // automatic merging, since matching text does not establish legal identity.
  function possibleNameVariant(item){
    const words=normalizeName(item.name).split(' ').filter(Boolean);
    if(words.length<2||words[0].length<5)return null;
    const peers=[
      ...ui.getCandidates().map(x=>({name:x.name})),
      ...suggestions.filter(x=>x!==item&&Number(x.matching_posts||0)>=Number(item.matching_posts||0))
    ];
    return peers.find(other=>{
      const candidate=normalizeName(other.name),tokens=candidate.split(' ');
      return candidate!==normalizeName(item.name)&&tokens[0]===words[0]&&
        words.filter(word=>tokens.includes(word)).length>=2;
    })||null;
  }
  function renderSuggestions(){
    const target=$('#aiCandidateSuggestions');
    if(!target||$('#modalTitle')?.textContent!=='Add Candidate')return;
    if(!campaignId){
      target.innerHTML='<h3>AI-suggested candidates</h3><p class="hint">Open Candidate Watchlist from a selected Social Listening campaign to view its AI recommendations.</p>';
      return;
    }
    const query=normalizeName($('#candidateSearch')?.value||'');
    let html='<h3>AI-suggested candidates</h3><p class="hint">Based on saved posts in this campaign. Candidate identity requires officer verification; source IDs support evidence review.</p>';
    if(suggestionsLoading)html+='<p class="hint" role="status">Loading campaign recommendations...</p>';
    if(suggestionsError)html+='<p class="hint" role="alert">'+escapeHTML(suggestionsError)+'</p>';
    if(!suggestionsLoading&&!suggestionsError&&!suggestions.length)html+='<p class="hint">No AI-detected candidates have been recorded for this campaign yet.</p>';
    let shown=0;
    suggestions.slice(0,10).forEach((item,i)=>{
      if(query&&!normalizeName(item.name).includes(query))return;
      shown++;
      const existing=exactCandidate(item),near=existing?null:possibleNameVariant(item);
      const active=(existing&&ui.isActive?.(existing.id))||(!existing&&item.tracked===true);
      const sources=(Array.isArray(item.source_ids)?item.source_ids:[]).slice(0,5)
        .map(id=>'#'+escapeHTML(id)).join(', ');
      const action=active?'<span class="pill tag-ok">Already tracking</span>':
        near?'<button class="btn ghost" data-review-suggestion="'+i+'">Review identity</button>':
        '<button class="btn primary" data-track-suggestion="'+i+'" '+(permitted?'':'disabled')+
          '>'+(existing?'＋ Track existing':'＋ Add & Track')+'</button>';
      html+='<div class="ai-suggestion"><div><strong>'+escapeHTML(item.name)+'</strong>'+
        '<div class="ai-suggestion-details">'+Number(item.matching_posts||0).toLocaleString()+
        ' saved mention(s)'+(sources?' · Evidence '+sources:'')+'</div>'+
        (near?'<div class="ai-suggestion-status">Possible variant of '+escapeHTML(near.name)+
          ' — review before creating another identity</div>':'')+
        '</div>'+action+'</div>';
    });
    if(query&&!shown)html+='<p class="hint">No AI suggestions match this search.</p>';
    html+='<p class="hint">AI-detected mentions do not confirm official accounts, endorsements or violations.</p>';
    target.innerHTML=html;
  }
  ui.onOpenAdd=async()=>{
    renderSuggestions();
    if(!campaignId||suggestionsRequest)return;
    if(suggestionsFetchedAt&&Date.now()-suggestionsFetchedAt<30000)return;
    suggestionsLoading=true;suggestionsError='';renderSuggestions();
    suggestionsRequest=(async()=>{
      const response=await fetch('/api/functions/socialListening',{
        method:'POST',cache:'no-store',
        headers:{'Content-Type':'application/json','Authorization':'Bearer '+token()},
        body:JSON.stringify({action:'campaignCandidateSuggestions',id:campaignId,data:{}})
      });
      const data=await response.json().catch(()=>({}));
      if(!response.ok)throw Error(data.detail||data.error||'Candidate suggestions unavailable ('+response.status+')');
      suggestions=Array.isArray(data.candidates)?data.candidates.slice(0,10):[];
      suggestionsFetchedAt=Date.now();
    })();
    try{await suggestionsRequest}
    catch(error){suggestionsError=error.message||'Unable to load campaign recommendations.'}
    finally{suggestionsLoading=false;suggestionsRequest=null;renderSuggestions()}
  };
  document.addEventListener('click',event=>{
    const button=event.target.closest('button[data-track-suggestion],button[data-review-suggestion]');
    if(!button)return;
    const index=Number(button.dataset.trackSuggestion??button.dataset.reviewSuggestion);
    const item=suggestions[index];
    if(!item)return;
    const existing=exactCandidate(item),near=existing?null:possibleNameVariant(item);
    if(button.dataset.reviewSuggestion!==undefined||near){
      ui.notify('Possible variant of '+(near?.name||item.name)+'. Verify the approved identity before tracking.');
      $('#candidateSearch')?.focus();
      return;
    }
    if(!permitted){ui.notify('Watchlist management permission required.');return}
    if(existing){
      if(ui.isActive?.(existing.id)){ui.notify('This candidate is already being tracked.');return}
      ui.onActivate?.(existing.id);
      return;
    }
    if(item.tracked){ui.notify('This candidate is already being tracked.');return}
    if(!window.confirm('Register and track '+item.name+'? Verify the full identity first. No official account is verified by this action.'))return;
    ui.onCreate?.(item.name,'');
  });

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
      const result=await registry('watchlistCapturedFeed',{page,page_size:50,...(campaignId?{campaign_id:campaignId}:{})},id);
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
      sentiment,flag:validatedFlag,
      assessment:(post.saved_assessments||[]).find(a=>a.is_flagged===true)||null, url:safeUrl(post.url),
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
  async function scopedMentions(candidate){
    const response=await fetch('/api/functions/socialListening',{method:'POST',cache:'no-store',headers:{'Content-Type':'application/json','Authorization':'Bearer '+token()},body:JSON.stringify({action:'campaignEvidence',id:campaignId,data:{}})});
    const payload=await response.json().catch(()=>({}));
    if(!response.ok)throw Error(payload.detail||payload.error||'Campaign evidence unavailable');
    const aliases=[candidate.name,...candidate.aliases].map(x=>String(x||'').trim()).filter(x=>x.length>=3);
    const normalize=value=>' '+String(value||'').toLocaleLowerCase().replace(/[^\p{L}\p{N}]+/gu,' ').trim()+' ';
    const candidateNames=aliases.map(normalize);
    return (payload.evidence||[]).filter(post=>candidateNames.some(name=>normalize(post.text_content).includes(name))).map(post=>({
      id:'CAM-'+post.id,kind:'earned',platform:post.platform||'Source',source:post.author_name||'Public source',
      date:String(post.published_at||''),text:post.text_content||'',sentiment:(()=>{const s=String(post.sentiment||'').toLowerCase();return ['positive','negative','neutral'].includes(s)?s[0].toUpperCase()+s.slice(1):'Unknown'})(),
      flag:(post.saved_assessments||[]).some(a=>a.is_flagged===true),
      assessment:(post.saved_assessments||[]).find(a=>a.is_flagged===true)||null,
      url:safeUrl(post.canonical_url),description:'Candidate name or alias mentioned in this campaign. Attribution and context require officer review.'
    }));
  }
  ui.onProfile=async id=>{
    if(loaded.has(id)||loading.has(id))return;
    const candidate=ui.getCandidate(id);
    if(!candidate)return;
    loading.add(id);
    try{
      const [captured,actor]=await Promise.allSettled([
        collectedPosts(id),campaignId?scopedMentions(candidate):intel('actorPicture',{actor_id:id})
      ]);
      const own=captured.status==='fulfilled'?captured.value.map(mapCaptured):[];
      const records=actor.status==='fulfilled'?(campaignId?(Array.isArray(actor.value)?actor.value:[]):(actor.value.records||[])):[];
      // Campaign views must never mix unscoped intelligence from other campaigns.
      const related=campaignId?records:records.map(mapEarned);
      const known=new Set(own.map(post=>post.url).filter(Boolean));
      candidate.posts=[...own,...related.filter(post=>!post.url||!known.has(post.url))]
        .sort((a,b)=>String(b.date||'').localeCompare(String(a.date||'')));
      // Reuse only flags returned by the saved assessment view; never infer a legal violation.
      candidate.findings=candidate.posts.filter(post=>post.flag===true).map(post=>({
        id:'FLAG-'+post.id,title:'Potential violation indicator · unverified',
        summary:'Saved assessment v'+(post.assessment?.assessment_version??'unknown')+
          ' · '+(post.assessment?.violation_uncertainty||'UNVERIFIED_AI_INDICATOR')+
          '. Inspect original evidence before any officer decision.',
        status:post.assessment?.violation_uncertainty||'Unverified',postIds:[post.id]
      }));
      loaded.add(id);
      ui.renderProfile(id);
      if(captured.status==='rejected'||actor.status==='rejected')
        ui.notify('Some campaign evidence could not load. Counts may be incomplete; review source availability.');
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