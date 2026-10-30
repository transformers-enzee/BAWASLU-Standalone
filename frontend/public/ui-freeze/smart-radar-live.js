(() => {
  'use strict';
  const ui = window.__bawaslu;
  const $ = selector => document.querySelector(selector);
  const escapeHtml = value => String(value ?? '').replace(/[&<>"']/g, char => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[char]));
  const label = value => escapeHtml(value);
  let dashboard = null;
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
      human_reviewed: Boolean(f.human_reviewed), history: [],
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
  function trendSvg(rows) {
    if (!rows.length) return '<p class="small muted">No publication timestamps in this selection.</p>';
    const dates = rows.sort((a,b) => a[0].localeCompare(b[0])).slice(-12);
    const max = Math.max(1,...dates.map(row => row[1]));
    const points = dates.map(([day,value],i) =>
      (23+i*(dates.length>1 ? 275/(dates.length-1) : 0)) + ',' + (125-value/max*95)).join(' ');
    return '<svg viewBox="0 0 320 145" width="100%" role="img" aria-label="Recorded conversation activity trend">' +
      '<line x1="18" y1="124" x2="305" y2="124" stroke="#9ca8b2"/>' +
      '<polyline points="' + points + '" fill="none" stroke="#278d7a" stroke-width="3"/>' +
      '<text x="18" y="141" font-size="10">' + label(dates[0][0]) + '</text>' +
      '<text x="245" y="141" font-size="10">' + label(dates[dates.length-1][0]) + '</text></svg>';
  }
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
    const profiles=(dashboard?.watchlist_profiles||[])
      .filter(p=>['Active','Under Review'].includes(p.status))
      .sort((a,b)=>(['Critical','High','Medium','Low'].indexOf(a.priority)-
                     ['Critical','High','Medium','Low'].indexOf(b.priority))||String(a.name).localeCompare(String(b.name)));
    $('#watch').innerHTML='<p class="small muted">Registered candidate profiles · priority and status set by officers, not AI risk scores.</p>'+
      (profiles.length?profiles.slice(0,10).map(p=>{
        const registered=String(p.name||'');
        const count=mentions.find(([name])=>name.toLocaleLowerCase()===registered.toLocaleLowerCase())?.[1]||0;
        return '<div style="padding:9px 0;border-bottom:1px solid #e3e9ee"><b>'+label(registered)+'</b>'+
          '<div class="small muted">Officer priority: '+label(p.priority)+' · '+label(p.status)+
          ' · '+count+' saved Inbox mention'+(count===1?'':'s')+'</div></div>';
      }).join(''):'<p class="small muted">No active or under-review candidate profiles in your permitted scope.</p>')+
      '<p class="small"><a class="watch-link" href="/social-listening?tab=watchlist" target="_top">Open Social Listening Candidate Watchlist →</a></p>'+
      '<p class="small muted">Monitoring priority and mentions are not evidence of wrongdoing.</p>';
    $('#watch').removeAttribute('data-insight');
    const topicCounts = {};
    filtered.forEach(f => (f.topics||[]).forEach(t => {topicCounts[t] = (topicCounts[t]||0)+1;}));
    const topics = asRows(topicCounts);
    const topicMax = Math.max(1,...topics.map(row=>row[1]));
    $('#issues').innerHTML = miniBars(topics.slice(0,8),topicMax);
    $('#cloud').innerHTML = topics.slice(0,12).map(([name],i) =>
      '<span style="font-size:'+(18-i%3*2)+'px">'+label(name)+'</span>').join('');
    $('#trend').innerHTML = trendSvg(asRows(addCounts(filtered,'day_counts')));$('#trend').setAttribute('data-insight','trend');
    const unverifiedLocations=asRows(addCounts(filtered,'geo_signal_counts'));
    const verifiedLocations=asRows(addCounts(filtered,'verified_incident_counts'));
    const verifiedTotal=verifiedLocations.reduce((sum,[,count])=>sum+count,0);
    $('#regions').innerHTML='<p class="small"><b>'+verifiedTotal+' verified incident-location post'+(verifiedTotal===1?'':'s')+
      '</b> · verified only after officer review.</p>'+
      (verifiedLocations.length?'<p class="small muted">Confirmed incident jurisdiction</p>'+
         verifiedLocations.map(([place,count])=>'<button type="button" class="insightclick region-bar" data-insight="geo-verified:'+encodeURIComponent(place)+'">'+
         '<div class="row small"><span>'+label(place)+'</span><b>'+count+'</b></div></button>').join(''):'')+
      '<p class="small muted">Unverified geographic references from saved Inbox assessments (not incident locations):</p>'+
      (unverifiedLocations.length?unverifiedLocations.slice(0,12).map(([place,count])=>
       '<button type="button" class="insightclick region-bar" data-insight="geo:'+encodeURIComponent(place)+'">'+
       '<div class="row small"><span>'+label(place)+'</span><b>'+count+'</b></div>'+
       '<div class="track"><div class="fill" style="width:'+(count/Math.max(1,...unverifiedLocations.map(x=>x[1]))*100)+'%"></div></div></button>').join(''):
      '<p class="small muted">No location references have been saved in the selected Inbox evidence.</p>')+
      '<p class="small muted">Profile addresses and candidate constituencies are never interpreted as incident locations.</p>';
    $('#regions').removeAttribute('data-insight');
    $('#regions').querySelectorAll('.region-bar').forEach(btn=>btn.setAttribute('type','button'));
    const sentimentCounts=addCounts(filtered,'sentiment_counts');
    const sentimentRows=['POSITIVE','NEUTRAL','NEGATIVE','UNCLASSIFIED']
      .map(name=>[name,Number(sentimentCounts[name]||0)]);
    const classified=sentimentRows.slice(0,3).reduce((n,r)=>n+r[1],0);
    const total=classified+sentimentRows[3][1];
    $('#sentimentExplain').textContent=classified+' of '+total+' relevant posts have saved sentiment labels. Unclassified is NOT Neutral; no AI calls are made on this page.';
    const maxSentiment=Math.max(1,...sentimentRows.map(r=>r[1]));
    $('#sentiments').innerHTML=sentimentRows.map(([name,count])=>
      '<button type="button" class="insightclick" data-insight="sentiment:'+name+
      '"><div class="row small"><span>'+label(name==='UNCLASSIFIED'?'Unclassified':name)+
      '</span><b>'+count+'</b></div><div class="track"><div class="fill" style="width:'+
      (count/maxSentiment*100)+'%"></div></div></button>').join('');
    const platforms = asRows(addCounts(filtered,'platform_counts'));
    $('#platforms').innerHTML = platforms.map(([name,count]) =>
      '<button class="insightclick" data-insight="platform:'+label(name)+'"><div class="row small"><span>'+label(name)+
      '</span><b>'+count+'</b></div><div class="track"><div class="fill" style="width:'+
      (count/Math.max(1,...platforms.map(row=>row[1]))*100)+
      '%;background:#5588a8"></div></div></button>').join('') ||
      '<p class="small muted">No saved platforms for this view.</p>';
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
        if (access?.geographic_scope !== 'Nationwide' && $('#geo')) {
          const region = access.province || 'Assigned region';
          $('#geo').options[0].textContent = region + ' — regional access only';
          $('#geo').disabled = true;
        }
      } catch {ui.canReview=false;}
      await refresh();
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
    try {
      const history = await request('/api/smart-radar/history/'+encodeURIComponent(id));
      model.history = (history.events||[]).map(e=>({
        title: String(e.action||'Review action'), when: String(e.created_at||''),
        note: e.note || 'Officer action recorded.'
      }));
    } catch {model.history=[];}
    return model;
  }
  ui.openFinding = async (id, origin) => {
    if(busy) return;
    busy=true;
    try {
      const model = await fetchFinding(id);
      if(!model) throw Error('Finding not found');
      ui.openFindingOriginal(id,origin);
      const originals = $('#drawerBody').querySelectorAll('.source');
      model.posts.forEach((post,i)=>{
        const href=safeUrl(post[3]);
        if(!href||!originals[i])return;
        const a=document.createElement('a');a.href=href;a.target='_blank';a.rel='noopener noreferrer';
        a.textContent='View original source →';a.className='source-link';
        originals[i].appendChild(a);
      });
    } catch(error){ui.notify('Cannot load source evidence: '+error.message);}
    finally{busy=false;}
  };
  ui.insightView = id => id.startsWith('platform:') ?
    ui.view().filter(f=>Object.entries(f.platform_counts||{}).some(([k,v])=>k.toLowerCase()===id.slice(9).toLowerCase()&&v>0)) :
    id.startsWith('sentiment:') ?
    ui.view().filter(f=>Number(f.sentiment_counts?.[id.slice(10).toUpperCase()]||0)>0) :
    id.startsWith('geo:') ?
    ui.view().filter(f=>Number(f.geo_signal_counts?.[decodeURIComponent(id.slice(4))]||0)>0) :
    id.startsWith('geo-verified:') ?
    ui.view().filter(f=>Number(f.verified_incident_counts?.[decodeURIComponent(id.slice(13))]||0)>0) :
    ui.view();
  ui.insightMatchesPost = (id,post) => id.startsWith('platform:') ?
    String(post[5]||'').toLowerCase()===id.slice(9).toLowerCase() :
    id.startsWith('sentiment:') ?
    String(post[6]||'UNCLASSIFIED').toUpperCase()===id.slice(10).toUpperCase() :
    id.startsWith('geo:') ?
    (post[7]||[]).includes(decodeURIComponent(id.slice(4))) :
    id.startsWith('geo-verified:') ?
    post[8]===decodeURIComponent(id.slice(13)) : true;
  ui.openInsight = async id => {
    if (id === 'watchlist') {window.top.location.assign('/watchlist');return;}
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