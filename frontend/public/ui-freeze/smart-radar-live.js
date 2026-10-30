(() => {
  'use strict';
  const ui = window.__bawaslu;
  const $ = selector => document.querySelector(selector);
  const escapeHtml = value => String(value ?? '').replace(/[&<>"']/g, char => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[char]));
  const label = value => escapeHtml(value);
  let dashboard = null;
  let canManageWatchlist=false, monitoringProvince='', provinceGeo=null, provinceGeoFailed=false;
  let watchOffset=0;
  function renderInboxLineage(){
    const anchor=$('#kpis');if(!anchor)return;
    let panel=$('#sharedCampaignViolationAssessments');
    if(!panel){panel=document.createElement('section');
      panel.id='sharedCampaignViolationAssessments';
      panel.setAttribute('aria-label','Current Intelligence Inbox evidence source');
      panel.style.cssText='margin:12px 0;padding:12px 16px;border:1px solid #bdded6;border-radius:10px;background:#f3fbf8';
      anchor.insertAdjacentElement('afterend',panel);}
    const total=Number(dashboard?.source_total||0);
    panel.innerHTML='<b>Live Intelligence Inbox · '+total+' relevant saved source'+(total===1?'':'s')+'</b>'+
      '<p class="small muted">All operational findings below reuse the authorized Intelligence Inbox classifications and original source IDs. Legacy pilot posts are not included. Review decisions do not establish legal guilt.</p>'+
      (dashboard?.truncated_to_inbox_window?'<p class="small" role="status">The Inbox response currently caps findings at 300; this view may be incomplete.</p>':'');
  }
  let busy = false;
  const accessToken = () => localStorage.getItem('bawaslu_access_token') || '';
  // Short-lived in-memory cache: no browser persistence, no shared officer data.
  // Keep browser fetch no-store; this prevents *repeated network/Supabase reads*.
  const readCache = new Map();
  let cacheToken = null;
  function clearReadCache(){ readCache.clear(); }
  async function request(path, options = {}) {
    const token = accessToken();
    if (cacheToken !== token) { clearReadCache(); cacheToken = token; }
    const method = (options.method || 'GET').toUpperCase();
    const eligible = method === 'GET' && (path === '/api/smart-radar/dashboard' || path.startsWith('/api/smart-radar/finding/') || path.startsWith('/api/smart-radar/history/'));
    const ttl = path.includes('/history/') ? 10000 : path.includes('/finding/') ? 60000 : 45000;
    const now = Date.now();
    const key = path;
    if (eligible) {
      const cached = readCache.get(key);
      if (cached && cached.expires > now) return cached.promise;
      if (cached) readCache.delete(key);
    } else if (method !== 'GET') {
      clearReadCache();
    }
    const pending = (async () => {
      const response = await fetch(path, {
        ...options, cache: 'no-store', headers: {
          'Authorization': 'Bearer ' + token,
          ...(options.body ? {'Content-Type': 'application/json'} : {})
        }
      });
      const data = await response.json().catch(() => ({}));
      if (!response.ok) throw new Error(data.detail || data.error || 'Request failed (' + response.status + ')');
      return data;
    })();
    if (eligible) {
      // Evict rejected requests immediately; never cache authorization failures.
      const tracked = pending.catch(error => {
        if (readCache.get(key)?.promise === tracked) readCache.delete(key);
        throw error;
      });
      readCache.set(key, {expires:now+ttl,promise:tracked});
      if (readCache.size > 80) readCache.delete(readCache.keys().next().value);
      return tracked;
    }
    return pending;
  }
  const countPosts = rows => rows.reduce((sum, row) => sum + Number(row.supporting_posts || 0), 0);
  const addCounts = (rows, key) => {
    const counts = {};
    rows.forEach(f => Object.entries(f[key] || {}).forEach(([name, value]) => {
      counts[name] = (counts[name] || 0) + Number(value || 0);
    }));
    return counts;
  };
  const asRows = counts => Object.entries(counts).sort((a,b) => b[1]-a[1]);
  const safeUrl = value => {
    try {const url = new URL(value);return ['https:','http:'].includes(url.protocol) ? url.href : '';}
    catch {return '';}
  };
  function mapFinding(f) {
    return {
      id: String(f.id), title: f.title || String(f.id),
      p: (f.perspectives || [])[0] || 'operations',
      perspectives: f.perspectives || ['operations'], players: f.players || [],
      player: (f.players || [])[0] || 'narratives', topics: f.topics || [],
      geo: 'all', published_at: f.published_at || '',
      day: 0, status: f.status || 'awareness',
      summary: f.summary || '', insights: f.insights || {}, ai_summary: Boolean(f.ai_summary), ai_model: f.ai_model || '', summary_evidence_sample: f.summary_evidence_sample || null,
      violation: (f.players || []).includes('violations'),
      posts: [], source_count: Number(f.supporting_posts ?? 0),
      human_reviewed: Boolean(f.human_reviewed), history: [], history_loaded:false, history_loading:false,
      priority_score: f.priority_score, priority_label: f.priority_label || 'Not AI-scored',
      platform_counts: f.platform_counts || {}, day_counts: f.day_counts || {},
      actor_mentions: f.actor_mentions || {},
      sentiment_counts: f.sentiment_counts || {},
      geo_signal_counts: f.geo_signal_counts || {},
      verified_incident_counts: f.verified_incident_counts || {},
      next_followup: f.next_followup || '',
      source_ids: f.source_ids || [],followup: f.next_followup || ''
    };
  }
  function miniBars(rows, maxValue, color = '#279681') {
    if (!rows.length) return '<p class="small muted">No recorded values for this selection.</p>';
    return rows.map(([name, count]) =>
      '<div style="margin:12px 0"><div class="row small"><span>' + label(name) + '</span><b>' + count +
      '</b></div><div class="track"><div class="fill" style="width:' +
      (maxValue ? Math.max(0,Math.min(100,count/maxValue*100)) : 0) +
      '%;background:' + color + '"></div></div></div>').join('');
  }
  function donut(rows,prefix,colors) {
    const valid=rows.filter(([,v])=>Number(v)>0),total=valid.reduce((n,[,v])=>n+Number(v),0);
    if(!total)return '<p class="small muted">No classified evidence available.</p>';
    let offset=0;
    const stops=valid.map(([,v],i)=>{const start=offset;offset+=v/total*100;return colors[i%colors.length]+' '+start.toFixed(2)+'% '+offset.toFixed(2)+'%';});
    const legend=valid.map(([name,count],i)=>'<button type="button" class="insightclick" data-insight="'+prefix+encodeURIComponent(name)+'" style="display:flex;gap:9px;align-items:center;width:100%;padding:5px;text-align:left">'+
      '<span style="width:10px;height:10px;border-radius:50%;background:'+colors[i%colors.length]+'"></span>'+
      '<span style="flex:1">'+label(name==='UNCLASSIFIED'?'Unclassified':name)+'</span><b>'+count+' <span class="muted">('+Math.round(count/total*100)+'%)</span></b></button>').join('');
    return '<div style="display:flex;flex-wrap:wrap;align-items:center;gap:14px;justify-content:center;padding:14px 0">'+
      '<div role="img" aria-label="'+label(valid.map(x=>x[0]+': '+x[1]).join(', '))+'" style="width:150px;height:150px;flex:none;border-radius:50%;display:grid;place-items:center;background:conic-gradient('+stops.join(',')+')">'+
      '<div style="width:94px;height:94px;background:white;border-radius:50%;display:grid;place-items:center;text-align:center"><div><b style="font-size:24px">'+total+'</b><div class="small muted">posts</div></div></div></div>'+
      '<div style="min-width:165px;flex:1">'+legend+'</div></div>';
  }
  const regionAlias={'jakarta':'dki jakarta','daerah khusus ibukota jakarta':'dki jakarta','yogyakarta':'di yogyakarta','central java':'jawa tengah','west java':'jawa barat','east java':'jawa timur','east nusa tenggara':'nusa tenggara timur','sumatra selatan':'sumatera selatan'};
  const regionKey=v=>{const key=String(v||'').trim().toLocaleLowerCase('id-ID');return regionAlias[key]||key;};
  const candidateKey=name=>{
    const key=String(name||'').toLocaleLowerCase('id-ID').replace(/[^a-z0-9]+/g,'');
    const known={'prabowo':'prabowosubianto','gibran':'gibranrakabumingraka',
      'anies':'aniesbaswedan','anisbaswedan':'aniesbaswedan','ganjar':'ganjarpranowo',
      'jokowi':'jokowidodo','jokowidodo':'jokowidodo',
      'cakimin':'muhaiminiskandar'};
    return known[key]||key;
  };
  const mapRing=ring=>ring.map((pt,i)=>{const x=(pt[0]-94)*21.25,y=(7.7-pt[1])*21.25;return (i?'L':'M')+x.toFixed(1)+','+y.toFixed(1)}).join(' ')+'Z';
  const mapPath=g=>(g.type==='Polygon'?[g.coordinates]:(g.coordinates||[])).map(poly=>poly.map(mapRing).join(' ')).join(' ');
  function geoHeatmap(mentions,verified) {
    const confirmed=verified.reduce((n,[,v])=>n+v,0);
    const head='<p class="small muted"><b>'+confirmed+'</b> posts have human-verified incident geography. Map colours represent saved <b>unverified location references</b>, not incident locations.</p>';
    if(provinceGeoFailed)return head+'<p class="small muted">Map unavailable. Saved labels:</p>'+miniBars(mentions,Math.max(1,...mentions.map(x=>x[1])));
    if(!provinceGeo)return head+'<p class="small muted">Loading Indonesia province map…</p>';
    const scores=new Map(mentions.map(([k,v])=>[regionKey(k),Number(v)]));
    const max=Math.max(1,...mentions.map(x=>x[1])),shades=['#fff4c2','#fbd56b','#f59e35','#e85a2a','#bd2026'];
    const shapes=(provinceGeo.features||[]).map(f=>{
      const name=String(f.properties?.PROVINSI||''),count=scores.get(regionKey(name))||0;
      const intensity=count?Math.log1p(count)/Math.log1p(max):0;
      const fill=count?shades[Math.min(4,Math.floor(intensity*4.99))]:'#d9e3e8';
      return '<path d="'+mapPath(f.geometry)+'" fill="'+fill+'" stroke="#fff" stroke-width="1" fill-rule="evenodd" data-insight="geo:'+encodeURIComponent(name)+'" style="cursor:pointer">'+
        '<title>'+label(name)+': '+count+' saved mentions (unverified)</title></path>';
    }).join('');
    return head+'<svg viewBox="0 0 1050 460" role="img" aria-label="Indonesia province heatmap of saved unverified geographic mentions" style="width:100%;height:auto;background:#f6fafb;border-radius:9px">'+shapes+'</svg>'+
      '<p class="small muted">Grey: no mapped mentions. Low <span style="display:inline-block;width:90px;height:9px;background:linear-gradient(90deg,#fff4c2,#fbd56b,#f59e35,#e85a2a,#bd2026)"></span> High. Select a province for source posts.</p>'+
      '<p class="small muted">'+(mentions.length?mentions.map(([n,v])=>label(n)+': '+v).join(' · '):'No saved geographic references.')+'</p>';
  }
  function trendSvg(rows) {
    if(!rows.length)return '<p class="small muted">No publication dates in this selection.</p>';
    const dates=[...rows].sort((a,b)=>a[0].localeCompare(b[0])).slice(-12);
    const max=Math.max(1,...dates.map(x=>Number(x[1])));
    const pts=dates.map(([day,count],i)=>({day,count:Number(count),x:23+i*(dates.length>1?275/(dates.length-1):0),y:125-Number(count)/max*95}));
    return '<div style="position:relative"><svg viewBox="0 0 320 155" width="100%" aria-label="Daily post activity: hover or focus a point for the exact count" role="img">'+
      '<line x1="18" y1="125" x2="305" y2="125" stroke="#9ca8b2"/>'+
      '<polyline fill="none" stroke="#278d7a" stroke-width="3" points="'+pts.map(p=>p.x+','+p.y).join(' ')+'"/>'+
      pts.map(p=>'<circle tabindex="0" data-activity-day="'+label(p.day)+'" data-activity-count="'+p.count+'" role="button" aria-label="'+label(p.day)+': '+p.count+' posts" cx="'+p.x+'" cy="'+p.y+'" r="7" fill="#278d7a" stroke="white" stroke-width="2"><title>'+label(p.day)+': '+p.count+' posts</title></circle>').join('')+
      '<text x="18" y="149" font-size="10">'+label(dates[0][0])+'</text><text x="239" y="149" font-size="10">'+label(dates[dates.length-1][0])+'</text></svg>'+
      '<div id="activityTooltip" role="status" style="display:none;position:absolute;top:0;right:0;background:#14354c;color:white;padding:8px 12px;border-radius:8px;pointer-events:none"></div></div>'+
      '<p class="small muted">Hover or focus a point for the exact date and recorded post count.</p>';
  }
  function activityHover(event,visible){
    const point=event.target.closest?.('[data-activity-day]'),tip=$('#activityTooltip');
    if(!point||!tip)return;
    tip.style.display=visible?'block':'none';
    if(visible)tip.textContent=point.dataset.activityDay+' · '+point.dataset.activityCount+' posts';
  }
  document.addEventListener('pointerover',e=>activityHover(e,true));
  document.addEventListener('pointerout',e=>activityHover(e,false));
  document.addEventListener('focusin',e=>activityHover(e,true));
  document.addEventListener('focusout',e=>activityHover(e,false));
  function decorate() {
    const filtered = ui.view();
    const perspective = $('#operations').classList.contains('active') ? 'operations' : 'reputation';
    const pending = filtered.filter(f => f.status === 'pending').length;
    const reviewed = filtered.filter(f => f.human_reviewed).length;
    const nPosts = countPosts(filtered);
    $('#executive').textContent = dashboard ?
      'Intelligence Inbox provides '+nPosts+' relevant saved source posts across '+filtered.length+
      ' evidence-linked groups. '+pending+' group(s) await officer review and '+reviewed+
      ' have recorded triage decisions. Relevant is not equivalent to a verified legal violation.' :
      'Loading authorized Inbox evidence...';
    $('#kpis').innerHTML = [[filtered.length,'Issues Identified'],[pending,'Pending Reviews'],[reviewed,'Reviewed Issues'],[nPosts,'Supporting Posts']]
      .map(([value, name]) => '<div><strong>' + value + '</strong><span>' + name + '</span></div>').join('');
    const mentions = asRows(addCounts(filtered,'actor_mentions')).slice(0,10);
    const mentionMax = Math.max(1,...mentions.map(row => row[1]));
    $('#ranking').innerHTML = mentions.length ? mentions.map(([name,value],i) =>
      '<div class="rank"><span>'+(i+1)+'</span><div>'+label(name)+
      '<div class="track"><div class="fill" style="width:'+(value/mentionMax*100)+
      '%"></div></div></div><b>'+value+'</b></div>').join('') :
      '<p class="small muted">No candidate mentions in this selection.</p>';
    $('#ranking').removeAttribute('data-insight');
    $('#rankTitle').textContent = perspective === 'operations' ? 'Top 10 Candidate Mentions' : 'Most Discussed Institutional Themes';
    const known=new Map((dashboard?.watchlist_profiles||[]).map(p=>[candidateKey(p.name),p]));
    const watchSize=2;
    if(watchOffset>=mentions.length)watchOffset=Math.max(0,Math.ceil(mentions.length/watchSize)-1)*watchSize;
    const visibleCandidates=mentions.slice(watchOffset,watchOffset+watchSize);
    $('#watch').innerHTML='<p class="small muted">Top 10 candidate mentions in relevant Inbox evidence. Displaying up to two at a time; a mention is not evidence of wrongdoing.</p>'+
      (visibleCandidates.length?visibleCandidates.map(([name,count])=>{
        const profile=known.get(candidateKey(name));
        return '<div style="padding:9px 0;border-bottom:1px solid #e3e9ee;display:flex;align-items:center;justify-content:space-between;gap:8px">'+
          '<div><b>'+label(name)+'</b><div class="small muted">'+count+' mentions · '+(profile?label(profile.status)+' · Priority: '+label(profile.priority):'Not on Watchlist')+'</div></div>'+
          (profile?'<span class="small" style="color:#087a60">Registered ✓</span>':
          canManageWatchlist?'<button type="button" data-watch-add="'+encodeURIComponent(name)+'" style="border:1px solid #187c6c;border-radius:8px;padding:7px 10px;color:#116d5a;font-weight:bold">+ Add to Watchlist</button>':
          '<span class="small muted">Officer permission needed</span>')+'</div>';
      }).join(''):'<p class="small muted">No recorded candidate mentions in this selection.</p>')+
      (mentions.length>watchSize?'<div class="row small" style="margin-top:10px;gap:10px"><button type="button" class="button" data-watch-page="previous" '+(watchOffset===0?'disabled':'')+'>← Previous 2</button><span class="muted">'+(watchOffset+1)+'–'+Math.min(watchOffset+watchSize,mentions.length)+' of '+mentions.length+'</span><button type="button" class="button" data-watch-page="next" '+(watchOffset+watchSize>=mentions.length?'disabled':'')+'>Next 2 →</button></div>':'')+
      '<p class="small"><a class="watch-link" href="/social-listening?tab=watchlist" target="_top">Open Candidate Watchlist in Social Listening →</a></p>';
    $('#watch').removeAttribute('data-insight');
    const topicCounts = {};
    filtered.forEach(f => (f.topics||[]).forEach(t => {topicCounts[t] = (topicCounts[t]||0)+1;}));
    const topics = asRows(topicCounts);
    const topicMax = Math.max(1,...topics.map(row=>row[1]));
    $('#issues').innerHTML = miniBars(topics.slice(0,8),topicMax);
    $('#cloud').innerHTML = topics.slice(0,12).map(([name],i) =>
      '<span style="font-size:'+(18-i%3*2)+'px">'+label(name)+'</span>').join('');
    const dayRows=asRows(addCounts(filtered,'day_counts')).sort((a,b)=>a[0].localeCompare(b[0]));
    $('#trend').innerHTML=trendSvg(dayRows);
    $('#trend').removeAttribute('data-insight');
    const unverifiedLocations=asRows(addCounts(filtered,'geo_signal_counts'));
    const verifiedLocations=asRows(addCounts(filtered,'verified_incident_counts'));
    $('#regions').innerHTML=geoHeatmap(unverifiedLocations,verifiedLocations);
    $('#regions').removeAttribute('data-insight');
    const sentimentCounts=addCounts(filtered,'sentiment_counts');
    const sentimentRows=['POSITIVE','NEUTRAL','NEGATIVE','UNCLASSIFIED']
      .map(name=>[name,Number(sentimentCounts[name]||0)]);
    const classified=sentimentRows.slice(0,3).reduce((n,r)=>n+r[1],0);
    const total=classified+sentimentRows[3][1];
    $('#sentimentExplain').textContent=classified+' of '+total+' relevant posts have saved sentiment labels. Unclassified is NOT Neutral; no AI calls are made on this page.';
    $('#sentiments').innerHTML=donut(sentimentRows,'sentiment:',['#18a087','#91a5b4','#dc994d','#d5dde2']);
    const platforms=asRows(addCounts(filtered,'platform_counts'));
    $('#platforms').innerHTML=donut(platforms,'platform:',['#228a9d','#e0aa59','#7597b9','#9284bc','#bf8491','#809a91']);
    $('#trendsAiSummary').textContent = nPosts + ' relevant saved Inbox posts support ' + filtered.length +
      ' preliminary groups. Activity, platforms and sentiment reuse saved source annotations; no additional AI processing occurs.';
    $('#strategy').textContent = 'Review supporting posts and saved assessments before prioritising officer action. Unverified mentions and discussion levels are not proof of electoral violations.';
    $('#trend').closest('.chartcard').querySelector('.small').textContent = 'Recorded source-post publication dates';
    document.querySelectorAll('.demo').forEach(el => {
      if(el.textContent.includes('Illustrative')) el.textContent = 'Staging summaries must remain grounded in recorded sources.';
    });
    if (!dashboard) return;
    $('#awayCard').querySelector('.notice-description').textContent =
      'Last-visit changes cannot be calculated without a verified account-specific visit history. Review current items via Action Desk.';
    // The HTML display is identical to the approved prototype; its values come from the API.
  }
  ui.decorate = decorate;
  async function refresh() {
    dashboard = await request('/api/smart-radar/dashboard');
    if(dashboard.mode!=='SAVED_INBOX_SOURCE_OF_TRUTH')throw Error('Radar returned a non-Inbox evidence feed');
    ui.setData((dashboard.findings || []).map(mapFinding));
    renderInboxLineage();
    document.body.classList.add('bawaslu-ready');
  }
  async function boot() {
    let access = null;
    try {
      try {
        const a = await request('/api/functions/registry',{method:'POST',body:JSON.stringify({action:'myAccess',data:{}})});
        access = a.access || null;
        ui.canReview = access?.permissions?.human_validation === true;
        canManageWatchlist=access?.permissions?.manage_watchlist===true;
        monitoringProvince=access?.geographic_scope==='Nationwide'?'':String(access?.province||'');
        if (access?.geographic_scope !== 'Nationwide' && $('#geo')) {
          const region = access.province || 'Assigned region';
          $('#geo').options[0].textContent = region + ' — regional access only';
          $('#geo').disabled = true;
        }
      } catch {ui.canReview=false;}
      await refresh();
      fetch('/indonesia-provinces.geojson',{cache:'force-cache'})
        .then(r=>{if(!r.ok)throw Error('Map unavailable');return r.json()})
        .then(data=>{if(!Array.isArray(data?.features))throw Error('Invalid map');provinceGeo=data;decorate()})
        .catch(()=>{provinceGeoFailed=true;decorate()});

    } catch (error) {
      document.body.classList.add('bawaslu-ready');
      const region = access?.province || 'your assigned scope';
      const message = 'Unable to load authorized Intelligence Inbox evidence for Smart Radar: '+error.message;
      ui.setData([]);
      if (access?.geographic_scope !== 'Nationwide' && $('#scopeLabel')) {
        $('#scopeLabel').textContent=region+' · Source-scope restricted';
      }
      $('#executive').textContent = message;
      const status=$('#startup-status');
      if(status){status.textContent=message;status.classList.add('error');status.setAttribute('role','alert');}
      document.body.classList.add('bawaslu-ready');
    }
  }
  async function fetchFinding(id) {
    const finding = await request('/api/smart-radar/finding/'+encodeURIComponent(id));
    const model = ui.db().find(f => f.id===id);
    if(!model) return null;
    model.summary = finding.summary || model.summary;
    const referenced = Number(finding.supporting_posts || 0);
    const loaded = (finding.posts || []).length;
    if (referenced !== loaded) throw Error('Finding evidence count mismatch: ' + referenced + ' referenced, ' + loaded + ' loaded');
    model.source_count = referenced;
    model.posts = (finding.posts||[]).map(post=>[
      post.account_raw || 'Unknown public account',
      post.published_at_raw || 'Unknown time',
      post.message_original || '',
      post.source_url || '',
      post.canonical_source_id || '',
      post.platform || '',
      post.sentiment || 'UNCLASSIFIED',
      Array.isArray(post.geographic_mentions_unverified)?post.geographic_mentions_unverified:[],
      post.verified_incident_province || ''
    ]);
    return model;
  }
  // Fetch history on demand, avoiding a second sequential query on record open.
  ui.loadHistory = async id => {
    const model=ui.db().find(f=>f.id===id);
    if(!model||model.history_loaded||model.history_loading)return;
    model.history_loading=true;
    try {
      const result=await request('/api/smart-radar/history/'+encodeURIComponent(id));
      model.history=(result.events||[]).map(e=>({
        title:String(e.action||'Review action'),when:String(e.created_at||''),
        note:e.note||'Officer action recorded.'
      }));
      model.history_loaded=true;
    } catch(error) {model.history_error=error.message;}
    finally {
      model.history_loading=false;
      if($('#historyLoading') && $('#drawerTitle')?.textContent==='Finding Details')
        ui.refreshDrawer?.();
    }
  };
  let openingSequence=0;
  ui.openFinding = async (id, origin) => {
    // Open immediately; fetch the source evidence without blocking navigation.
    const sequence=String(++openingSequence);
    ui.openFindingOriginal(id,origin);
    const body=$('#drawerBody');
    body.dataset.findingRequest=sequence;
    body.innerHTML='<div class="soft" role="status" style="margin-top:16px"><strong>Opening saved evidence…</strong><p class="small">Loading original Inbox posts and supporting source links.</p></div>';
    try {
      const model=await fetchFinding(id);
      if(!model)throw Error('Finding not found');
      if($('#drawerBody').dataset.findingRequest!==sequence ||
         !$('#overlay').classList.contains('open') ||
         $('#drawerTitle').textContent!=='Finding Details')return;
      ui.openFindingOriginal(id,origin);
      $('#drawerBody').dataset.findingRequest=sequence;
      const originals=$('#drawerBody').querySelectorAll('.source');
      model.posts.forEach((post,i)=>{
        const href=safeUrl(post[3]);
        if(!href||!originals[i])return;
        const a=document.createElement('a');a.href=href;a.target='_blank';a.rel='noopener noreferrer';
        a.textContent='View original source →';a.className='source-link';
        originals[i].appendChild(a);
      });
    } catch(error) {
      if($('#drawerBody').dataset.findingRequest!==sequence ||
         !$('#overlay').classList.contains('open'))return;
      $('#drawerBody').innerHTML='<div role="alert" class="soft" style="margin-top:16px"><strong>Source evidence could not be loaded.</strong><p class="small">'+label(error.message)+'</p><p class="small">No review action has been submitted.</p></div>'+
        '<button class="button" data-finding="'+label(id)+'" type="button">Retry opening this record →</button>';
    }
  };
  ui.insightView = id => id.startsWith('platform:') ?
    ui.view().filter(f=>Number(f.platform_counts?.[decodeURIComponent(id.slice(9))]||0)>0) :
    id.startsWith('sentiment:') ?
    ui.view().filter(f=>Number(f.sentiment_counts?.[decodeURIComponent(id.slice(10)).toUpperCase()]||0)>0) :
    id.startsWith('geo:') ?
    ui.view().filter(f=>Object.entries(f.geo_signal_counts||{}).some(([k,n])=>regionKey(k)===regionKey(decodeURIComponent(id.slice(4)))&&n>0)) :
    id.startsWith('geo-verified:') ?
    ui.view().filter(f=>Number(f.verified_incident_counts?.[decodeURIComponent(id.slice(13))]||0)>0) :
    ui.view();
  ui.insightMatchesPost=(id,p)=>id.startsWith('platform:') ?
    String(p[5]||'').toLowerCase()===decodeURIComponent(id.slice(9)).toLowerCase() :
    id.startsWith('sentiment:') ?
    String(p[6]||'UNCLASSIFIED').toUpperCase()===decodeURIComponent(id.slice(10)).toUpperCase() :
    id.startsWith('geo:') ? (p[7]||[]).some(n=>regionKey(n)===regionKey(decodeURIComponent(id.slice(4)))) :
    id.startsWith('geo-verified:') ? p[8]===decodeURIComponent(id.slice(13)) : true;
  ui.openInsight = async id => {
    if (id === 'watchlist') {window.top.location.assign('/social-listening?tab=watchlist');return;}
    if (busy) return;
    busy=true;
    try {
      const rows=ui.insightView(id);
      await Promise.all(rows.map(f=>fetchFinding(f.id)));
      ui.openPanel('insight',id);
      const sources=$('#drawerBody').querySelectorAll('.source');
      const posts=rows.flatMap(f=>(f.posts||[]).filter(p=>ui.insightMatchesPost(id,p)));
      posts.forEach((post,i)=>{
        const href=safeUrl(post[3]);
        if(!href||!sources[i])return;
        const a=document.createElement('a');a.href=href;a.target='_blank';a.rel='noopener noreferrer';
        a.textContent='View original source →';a.className='source-link';
        sources[i].appendChild(a);
      });
    } catch(error) {ui.notify('Unable to open source evidence: '+error.message);}
    finally{busy=false;}
  };
  document.addEventListener('click',event=>{
    const control=event.target.closest('[data-watch-page]');
    if(!control)return;
    event.preventDefault();event.stopPropagation();
    watchOffset=Math.max(0,watchOffset+(control.dataset.watchPage==='next'?2:-2));
    decorate();
  });
  document.addEventListener('click',async event=>{
    const button=event.target.closest('[data-watch-add]');
    if(!button)return;
    event.preventDefault();event.stopPropagation();
    if(!canManageWatchlist){ui.notify('Watchlist management permission required.');return;}
    const name=decodeURIComponent(button.dataset.watchAdd||'');
    if(!dashboard||!name)return;
    if((dashboard.watchlist_profiles||[]).some(x=>candidateKey(x.name)===candidateKey(name))){
      ui.notify('This candidate is already registered.');return;
    }
    if(!window.confirm('Add '+name+' to the Social Listening Candidate Watchlist as Under Review? This does not imply wrongdoing.'))return;
    button.disabled=true;
    try{
      const saved=await request('/api/functions/registry',{method:'POST',body:JSON.stringify({
        action:'createWatchlist',data:{name,type:'Candidate',status:'Under Review',priority:'Medium',...(monitoringProvince?{province:monitoringProvince}:{})}
      })});
      dashboard.watchlist_profiles=[...(dashboard.watchlist_profiles||[]),{
        id:saved.item?.id||'',name,priority:'Medium',status:'Under Review'
      }];
      decorate();ui.notify('Candidate added to Watchlist for human review.');
    }catch(e){ui.notify('Could not add candidate: '+e.message);button.disabled=false;}
  });
  ui.onAction = async action => {
    if(!ui.canReview){ui.notify('Officer permission is required.');return;}
    const detail = $('#drawerSubtitle').textContent || '';
    const findingId = (ui.db().find(f=>detail.includes(f.id))||{}).id;
    if(!findingId) {ui.notify('Open a finding before submitting a decision.');return;}
    const map={queue:'queue',closed:'close',investigating:'investigate',monitoring:'monitor',escalated:'escalate',reopen:'reopen',update:'update'};
    const note=$('#note')?.value?.trim()||'';
    const next_followup=$('#follow')?.value||null;
    try {
      await request('/api/smart-radar/decision',{method:'POST',body:JSON.stringify({
        finding_id:findingId,action:map[action],note,next_followup
      })});
      await refresh();ui.closePanel();ui.notify('Officer decision saved.');
    } catch(error){ui.notify('Decision not saved: '+error.message);}
  };
  boot();
})();