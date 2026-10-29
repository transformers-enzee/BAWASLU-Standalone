(() => {
  'use strict';
  const ui = window.__bawaslu;
  const $ = selector => document.querySelector(selector);
  const escapeHtml = value => String(value ?? '').replace(/[&<>"']/g, char => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[char]));
  const label = value => escapeHtml(value);
  let dashboard = null;
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
    const ttl = path.includes('/history/') ? 10000 : path.includes('/finding/') ? 60000 : 30000;
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
      summary: f.summary || '', insights: f.insights || {},
      violation: (f.players || []).includes('violations'),
      posts: [], source_count: Number(f.supporting_posts ?? 0),
      human_reviewed: Boolean(f.human_reviewed), history: [],
      priority_score: f.priority_score, priority_label: f.priority_label || 'Not AI-scored',
      platform_counts: f.platform_counts || {}, day_counts: f.day_counts || {},
      actor_mentions: f.actor_mentions || {}, next_followup: f.next_followup || '',
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
      'The current evidence-linked staging view contains ' + filtered.length + ' intelligence groups covering ' +
      nPosts + ' original source posts. ' + pending + ' group(s) await officer review and ' +
      reviewed + ' have a recorded review. Source claims remain unverified until assessed.' :
      'Loading authorised staging data...';
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
    $('#watch').innerHTML = '<p class="small"><b>Candidate Watchlist</b> — Activated candidate profiles are managed in a separate module. Their own verified posts and mentions by others are tracked separately.</p><div class="divider"></div>' +
      '<a class="watch-link" href="/watchlist" target="_top">Open Candidate Watchlist →</a>' +
      '<p class="small muted">A mention alone is not evidence of wrongdoing.</p>';
    $('#watch').removeAttribute('data-insight');
    const topicCounts = {};
    filtered.forEach(f => (f.topics||[]).forEach(t => {topicCounts[t] = (topicCounts[t]||0)+1;}));
    const topics = asRows(topicCounts);
    const topicMax = Math.max(1,...topics.map(row=>row[1]));
    $('#issues').innerHTML = miniBars(topics.slice(0,8),topicMax);
    $('#cloud').innerHTML = topics.slice(0,12).map(([name],i) =>
      '<span style="font-size:'+(18-i%3*2)+'px">'+label(name)+'</span>').join('');
    $('#trend').innerHTML = trendSvg(asRows(addCounts(filtered,'day_counts')));$('#trend').setAttribute('data-insight','trend');
    $('#regions').innerHTML = '<p class="small muted">Incident-level geography has not been verified for this pilot batch. No province totals are inferred from account locations.</p>';
    $('#regions').removeAttribute('data-insight');
    $('#sentimentExplain').textContent = 'No post-level sentiment labels are supplied by the current Smart Radar pilot API.';
    $('#sentiments').innerHTML = '<p class="small muted">No verified sentiment distribution available.</p>';
    const platforms = asRows(addCounts(filtered,'platform_counts'));
    $('#platforms').innerHTML = platforms.map(([name,count]) =>
      '<button class="insightclick" data-insight="platform:'+label(name)+'"><div class="row small"><span>'+label(name)+
      '</span><b>'+count+'</b></div><div class="track"><div class="fill" style="width:'+
      (count/Math.max(1,...platforms.map(row=>row[1]))*100)+
      '%;background:#5588a8"></div></div></button>').join('') ||
      '<p class="small muted">No saved platforms for this view.</p>';
    $('#trendsAiSummary').textContent = nPosts + ' linked posts are distributed across ' + filtered.length +
      ' preliminary groups. The activity and platform charts use saved source data. No independent geographic or sentiment conclusions have been generated.';
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
    ui.setData((dashboard.findings || []).map(mapFinding));
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
      const regionalPilotBlocked = error.message.includes('Pilot records require verified jurisdiction before regional access');
      const region = access?.province || 'your assigned region';
      const role = access?.role || 'Viewer';
      if (regionalPilotBlocked) {
        const jurisdiction=$('#geo');
        if (jurisdiction) {
          jurisdiction.options[0].textContent=region+' — regional access only';
          jurisdiction.disabled=true;
        }
        const scope=$('#scopeLabel');
        if (scope) scope.textContent=region+' · Restricted pilot';
      }
      const message = regionalPilotBlocked
        ? 'Smart Radar pilot data is not available for ' + region + ' (' + role + '). These national pilot posts have no verified event-level jurisdiction and cannot be displayed as regional intelligence. No authorised regional findings are available in this pilot view.'
        : 'Unable to load authorised Smart Radar data: ' + error.message;
      ui.setData([]);
      // setData renders the frozen prototype and rewrites scopeLabel to National.
      // Apply the verified access scope after that render, never to the source data.
      if (regionalPilotBlocked && $('#scopeLabel')) $('#scopeLabel').textContent=region+' · Restricted pilot';
      if (regionalPilotBlocked) {
        const welcome=$('.noticebar');
        if (welcome) {
          welcome.setAttribute('aria-label','Pilot data unavailable for regional Viewer');
          const intro=welcome.querySelector('p');
          if (intro) intro.textContent='No verified regional pilot baseline is available for this account. The national pilot cannot be used to claim new East Java issues.';
        }
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
      post.pilot_post_id || '',
      post.platform || ''
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
    ui.view();
  ui.openInsight = async id => {
    if (id === 'watchlist') {window.top.location.assign('/watchlist');return;}
    if (busy) return;
    busy=true;
    try {
      const rows=ui.insightView(id);
      await Promise.all(rows.map(f=>fetchFinding(f.id)));
      ui.openPanel('insight',id);
      const sources=$('#drawerBody').querySelectorAll('.source');
      const posts=rows.flatMap(f=>(f.posts||[]).filter(p=>!id.startsWith('platform:')||String(p[5]||'').toLowerCase()===id.slice(9).toLowerCase()));
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
    const map={closed:'close',investigating:'investigate',monitoring:'monitor',escalated:'escalate',reopen:'reopen',update:'update'};
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