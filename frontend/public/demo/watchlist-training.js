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
  // Recommendations stay inside the existing Add Candidate modal  // Recommendations stay inside the existing Add Candidate modal, scoped to
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
    if(!target||!$('#panel')?.classList.contains('open'))return;
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
        id:String(a.id),platform:a.platform,handle:a.handle||a.url,
        status:'Registered public account · affiliation requires officer verification',url:a.url
      }))
    };
  }
  async function reload(){
    const data=await registry('list',{view:'candidate_watchlist'});
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
  ui.onAddAccount=async (candidateId,platform,url,handle)=>{
    if(!permitted){ui.notify('Watchlist management permission required.');return;}
    if(!/^https:\/\//i.test(url||'')){ui.notify('Enter a valid HTTPS public profile URL.');return;}
    try{
      await registry('addAccount',{platform,url,handle},candidateId);
      await reload();
      ui.closeModal();
      ui.renderProfile(candidateId);
      ui.showAccountTab();
      ui.notify('Account registered. Own posts appear only when its published posts have been collected and the author matches its handle.');
    }catch(error){ui.notify('Account not registered: '+error.message);}
  };
  ui.onAddAccounts=async (candidateId,lines)=>{
    if(!permitted){ui.notify('Watchlist management permission required.');return;}
    const entries=String(lines||'').split(/\r?\n/).map(x=>x.trim()).filter(Boolean).map(line=>{
      const fields=line.split('|').map(x=>x.trim());
      return {platform:fields[0]?.toLowerCase(),url:fields[1],handle:fields[2]};
    });
    const allowed=new Set(['instagram','tiktok','x','youtube','threads','facebook','reddit']);
    if(!entries.length||entries.length>15||entries.some(x=>!allowed.has(x.platform)||!/^https:\/\//i.test(x.url||'')||!x.handle)){
      ui.notify('Enter 1–15 lines in platform | HTTPS profile URL | handle format.');return;
    }
    const keys=new Set(entries.map(x=>x.platform+'|'+x.url.toLowerCase()));
    if(keys.size!==entries.length){ui.notify('Remove duplicate platform URLs in this batch.');return;}
    let saved=0;
    try{
      for(const entry of entries){await registry('addAccount',entry,candidateId);saved++;}
      await reload();ui.closeModal();ui.renderProfile(candidateId);ui.showAccountTab();
      ui.notify(saved+' verified account(s) linked to this candidate.');
    }catch(error){await reload();ui.renderProfile(candidateId);ui.showAccountTab();ui.notify(saved+' saved; next account failed: '+error.message);}
  };
  ui.onRefreshProfile=id=>{
    if(loading.has(id))return;
    loaded.delete(id);
    ui.renderProfile(id);
  };
  ui.onFetchAccount=async (candidateId,accountId)=>{
    if(!permitted){ui.notify('Watchlist management permission required.');return;}
    const candidate=ui.getCandidate(candidateId);
    const account=candidate?.accounts.find(a=>a.id===String(accountId));
    if(!account){ui.notify('Registered account unavailable.');return;}
    if(!candidate.manualFetchAvailable){
      ui.notify('Manual collection requires a configured SocialCrawl API key and daily credit budget of at least 2.');
      return;
    }
    if(!window.confirm('Fetch the first page of public posts from '+account.platform+' '+account.handle+
      '? SocialCrawl can charge up to about 2 credits for this request. Continue?'))return;
    try{
      const response=await registry('requestAccountFetch',{
        account_id:String(accountId),...(campaignId?{campaign_id:campaignId}:{})
      },candidateId);
      if(response.status!=='QUEUED'){
        ui.notify(response.reason||('Account fetch status: '+response.status));return;
      }
      ui.notify('Account fetch queued. Checking collection status...');
      const wait=ms=>new Promise(resolve=>setTimeout(resolve,ms));
      for(let i=0;i<15;i++){
        await wait(3500);
        const check=await registry('watchlistSyncStatus',{},candidateId);
        const state=(check.accounts||[]).find(x=>x.account_id===String(accountId));
        if(state&&['WAITING','ERROR','UNSUPPORTED','NEEDS_HANDLE','BUDGET_PAUSED'].includes(state.state)){
          ui.notify(state.state==='WAITING'?'Account posts saved. Refreshing Watchlist evidence.':
            'Account collection: '+state.state+(state.last_error?' · '+state.last_error:''));
          ui.onRefreshProfile(candidateId);
          return;
        }
      }
      ui.notify('Account collection is still processing. Use Refresh Results to check the latest saved posts.');
    }catch(error){ui.notify('Unable to start account fetch: '+error.message);}
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
    const posts=[],seen=new Set();
    // Page through the SAME saved campaign Captured Posts evidence used by
    // Social Listening. This never calls SocialCrawl or OpenAI. Do not cap at
    // the dashboard's 200-post preview or an arbitrary 500-record limit.
    for(let page=1;page<=10000;page++){
      const result=await registry('watchlistCapturedFeed',
        {page,page_size:50,...(campaignId?{campaign_id:campaignId}:{})},id);
      const records=Array.isArray(result.posts)?result.posts:[];
      for(const item of records){
        const key=String(item.id);
        if(!seen.has(key)){posts.push(item);seen.add(key)}
      }
      const total=Number(result.total||0);
      if(page*50>=total||!records.length)break;
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
      id:'SRC-'+post.id,sourceId:String(post.id),
      kind:post.relation==='OWN_POST'?'own':'earned',
      platform:post.platform||'Unknown platform',
      source:post.author_name||post.account||'Unknown source author',
      date:String(post.published_at||''),text:post.text||'',
      sentiment,flag:validatedFlag,
      assessment:(post.saved_assessments||[]).find(a=>a.is_flagged===true)||null, url:safeUrl(post.url),
      description:post.relation==='OWN_POST'
        ?'Published by an account registered for this candidate; verify identity and original authorship.'
        :'Existing Social Listening Captured Post mentioning this candidate; published by another account.'
    };
  }
  function candidateActivitySummary(candidate){
    const language=(()=>{try{return localStorage.getItem('bawaslu-language')||'id'}catch(_){return 'id'}})();
    const id=language==='id';
    const posts=(candidate.posts||[]).filter(p=>p.kind==='own'&&String(p.text||'').trim());
    const others=(candidate.posts||[]).filter(p=>p.kind==='earned');
    if(!posts.length)return id
      ?'Belum ada unggahan tersimpan dari akun kandidat terdaftar yang dapat diringkas. '+others.length+' penyebutan oleh akun lain ditampilkan terpisah dan tidak membuktikan aktivitas pribadi kandidat.'
      :'No saved posts from registered candidate accounts are available to summarize. '+others.length+' mentions by other accounts are tracked separately and do not establish what the candidate personally did.';
    const dates=posts.map(p=>String(p.date||'').slice(0,10)).filter(Boolean).sort();
    const topics=[
      [id?'kampanye atau kegiatan publik':'campaigning or public outreach',/kampanye|campaign|relawan|bertemu|mengunjungi|kunjungan|sapa warga|dialog|silaturahmi/i],
      [id?'pernyataan atau pidato publik':'public statements or speeches',/pidato|menyatakan|mengatakan|menegaskan|berbicara|speech|statement|pernyataan|menyampaikan/i],
      [id?'program atau kebijakan':'policy proposals or programs',/program|visi|misi|kebijakan|ekonomi|pendidikan|kesehatan|pembangunan|policy/i],
      [id?'pemilu dan pemungutan suara':'election and voting matters',/pemilu|pilpres|pilkada|suara|voting|debat|bawaslu|kpu|election/i],
      [id?'kegiatan organisasi atau masyarakat':'community or organizational engagement',/masyarakat|komunitas|organisasi|acara|kegiatan|hadir|pertemuan/i]
    ].map(([label,re])=>({label,count:posts.filter(p=>re.test(p.text)).length})).filter(x=>x.count>0);
    const summary=topics.slice(0,3).map(x=>x.label+' ('+x.count+' '+(id?'unggahan':'posts')+')').join('; ')||
      (id?'topik belum dapat dikategorikan secara andal':'topics cannot be reliably categorized');
    const excerpts=posts.slice(0,3).map(p=>String(p.text).replace(/https?:\/\/\S+/g,'').replace(/\s+/g,' ').trim().slice(0,120)).filter(Boolean);
    if(id)return 'Dari '+posts.length+' unggahan tersimpan pada akun kandidat terdaftar'+(dates.length?' antara '+dates[0]+' dan '+dates[dates.length-1]:'')+
       ', aktivitas yang teramati mencakup '+summary+'.\n\nCuplikan unggahan: '+(excerpts.length?excerpts.map((x,i)=>(i+1)+') “'+x+'”').join('  '):'Teks tidak tersedia.')+
       '\n\nSebanyak '+others.length+' unggahan dari akun lain menyebut kandidat ini dan tidak dianggap sebagai aktivitas pribadi. Kepemilikan akun dan klaim sumber memerlukan verifikasi.';
    return 'From '+posts.length+' saved posts by registered candidate accounts'+(dates.length?' between '+dates[0]+' and '+dates[dates.length-1]:'')+
      ', recorded activities include '+summary+'.\n\nPost excerpts: '+(excerpts.length?excerpts.map((x,i)=>(i+1)+') “'+x+'”').join('  '):'No text available.')+
      '\n\n'+others.length+' posts from other accounts mention the candidate; these are not personal activities. Account ownership and source claims require verification.';
  }
  ui.onProfile=async id=>{
    if(loaded.has(id)||loading.has(id))return;
    const candidate=ui.getCandidate(id);
    if(!candidate)return;
    loading.add(id);
    candidate.feedLoadState='loading';
    candidate.feedWarning='';
    ui.renderProfile(id);
    try{
      // The ONLY candidate-post feed is the saved, campaign-scoped Social
      // Listening source. No unscoped actor picture or secondary earned-media
      // request may add records under Mentions by Others.
      candidate.posts=(await collectedPosts(id)).map(mapCaptured)
        .sort((a,b)=>String(b.date||'').localeCompare(String(a.date||'')));
      candidate.findings=candidate.posts.filter(post=>post.flag===true).map(post=>({
        id:'FLAG-'+post.id,title:'Potential violation indicator · unverified',
        summary:'Saved assessment v'+(post.assessment?.assessment_version??'unknown')+
          ' · '+(post.assessment?.violation_uncertainty||'UNVERIFIED_AI_INDICATOR')+
          '. Inspect original evidence before any officer decision.',
        status:post.assessment?.violation_uncertainty||'Unverified',postIds:[post.id]
      }));
      candidate.summary=candidateActivitySummary(candidate);
      candidate.feedLoadState='ready';
      loaded.add(id);
      ui.renderProfile(id);
      registry('watchlistSyncStatus',{},id).then(status=>{
        candidate.manualFetchAvailable=status.manual_fetch_available===true;
        candidate.collectionStatus=status.enabled
          ?'Automatic account collection is enabled.'
          :status.manual_fetch_available
            ?'Automatic collection is disabled, but a manual account-post fetch is available.'
            :'No account posts will be collected until the server has a SocialCrawl API key and daily credit budget of at least 2. Registering an account alone never fetches its posts.';
        candidate.accountSyncStates=Array.isArray(status.accounts)?status.accounts:[];
        if(ui.selected()===id)ui.renderProfile(id);
      }).catch(error=>{
        candidate.collectionStatus='Account collection status unavailable: '+(error.message||'request failed');
        candidate.manualFetchAvailable=false;
        if(ui.selected()===id)ui.renderProfile(id);
      });
    }catch(error){
      // Do not replace previously displayed source evidence with misleading
      // empty KPIs when a read fails. Expose the error and a retry control.
      candidate.feedLoadState='error';
      candidate.feedWarning='Saved campaign Captured Posts unavailable: '+
        (error.message||'request failed')+'. No additional posts were fetched.';
      ui.renderProfile(id);
    }finally{loading.delete(id);}
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
      ui.canManage=permitted;
      await reload();
    }catch(error){
      $('.content').style.visibility='visible';
      const notice=$('.notice');
      if(notice)notice.textContent='Unable to load authorised candidate registry: '+error.message;
      ui.setData([],[]);
    }
  }
  // Recompute the fixed bilingual summary whenever the parent toggles EN/ID.
  // No paid translator or live API is required.
  window.addEventListener('message',event=>{
    if(event.origin!==window.location.origin||event.data?.type!=='BAWASLU_UI_LANGUAGE')return;
    try{window.localStorage.setItem('bawaslu-language',event.data.language==='id'?'id':'en')}catch(_){}
    const selected=ui.selected();
    const candidate=selected&&ui.getCandidate(selected);
    if(candidate){
      candidate.summary=candidateActivitySummary(candidate);
      ui.renderProfile(selected);
    }
  });
  boot();
})();