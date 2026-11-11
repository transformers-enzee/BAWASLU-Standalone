(() => {
  'use strict';
  const ui = window.__bawaslu;
  const $ = selector => document.querySelector(selector);
  const escapeHtml = value => String(value ?? '').replace(/[&<>"']/g, char => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[char]));
  const label = value => escapeHtml(value);
  let dashboard = null;
  let activityWindow='30';
  const refreshingPlayers=new Set();
  let issueDistribution = null;
  let canManageWatchlist=false, monitoringProvince='', provinceGeo=null, provinceGeoFailed=false;
  let watchOffset=0;
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
    const eligible = method === 'GET' && (path === '/api/smart-radar/dashboard' || path === '/api/oversight/legal-summary' || path.startsWith('/api/smart-radar/finding/') || path.startsWith('/api/smart-radar/history/'));
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
      // Bound read requests: surface a retryable error rather than leaving the drawer loading forever.
      const signal = options.signal || (path.startsWith('/api/smart-radar/finding/') ? AbortSignal.timeout(20000) : undefined);
      const response = await fetch(path, {
        ...options, signal, cache: 'no-store', headers: {
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
  const countPosts = rows => rows.reduce((sum, row) => sum + Number(row.source_count ?? row.supporting_posts ?? 0), 0);
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
      id: String(f.id), kind:f.kind || '', title: f.title || String(f.id),
      p: (f.perspectives || [])[0] || 'operations',
      perspectives: f.perspectives || ['operations'], players: f.players || [],
      player: (f.players || [])[0] || 'narratives', topics: f.topics || [],
      geo: 'all', published_at: f.published_at || '',
      day: 0, status: f.status || 'awareness',
      summary: f.summary || '', insights: f.insights || {}, ai_summary: Boolean(f.ai_summary), ai_model: f.ai_model || '', summary_evidence_sample: f.summary_evidence_sample || null,
      violation: (f.players || []).includes('violations'),
      posts: [], source_count: Number(f.supporting_posts ?? 0), supporting_posts: Number(f.supporting_posts ?? 0),
      human_reviewed: Boolean(f.human_reviewed), history: [], history_loaded:false, history_loading:false,
      priority_score: f.priority_score, priority_label: f.priority_label || '',
      platform_counts: f.platform_counts || {}, day_counts: f.day_counts || {},
      actor_mentions: f.actor_mentions || {},
      sentiment_counts: f.sentiment_counts || {},
      geo_signal_counts: f.geo_signal_counts || {},
      province_breakdown: f.province_breakdown || {},
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
  const sentimentPalette={POSITIVE:'#15b87a',NEUTRAL:'#f5bd36',NEGATIVE:'#ef4444',UNCLASSIFIED:'#9ca3af'};
  const platformPalette={youtube:'#ff0033',tiktok:'#04c8c8',facebook:'#1877f2',instagram:'#dd2a7b',twitter:'#6366f1',x:'#6366f1',threads:'#8957e5',online_news:'#f59e0b',news:'#f59e0b',reddit:'#ff4500',linkedin:'#0a66c2'};
  function donut(rows,prefix,palette) {
    const grouped=new Map();
    for(const [raw,count] of rows){
      const key=String(raw||'').toLowerCase()==='twitter'?'x':String(raw||'').toLowerCase();
      grouped.set(key,(grouped.get(key)||0)+Number(count||0));
    }
    const valid=[...grouped].filter(([,n])=>n>0);
    const total=valid.reduce((n,[,v])=>n+v,0);
    if(!total)return '<p class="small muted">No classified evidence available.</p>';
    const shade=name=>palette[String(name).toUpperCase()]||palette[String(name).toLowerCase()]||'#64748b';
    let offset=0;
    const stops=valid.map(([name,count])=>{const start=offset;offset+=count/total*100;return shade(name)+' '+start.toFixed(2)+'% '+offset.toFixed(2)+'%';});
    const legend=valid.map(([name,count])=>'<button type="button" class="insightclick" data-insight="'+prefix+encodeURIComponent(name)+'" style="display:flex;gap:9px;align-items:center;width:100%;padding:5px;text-align:left">'+
      '<span style="width:12px;height:12px;border-radius:50%;flex:none;background:'+shade(name)+'"></span>'+
      '<span style="flex:1">'+label(prefix==='platform:'?({x:'X',instagram:'Instagram',facebook:'Facebook',tiktok:'TikTok',youtube:'YouTube',threads:'Threads',online_news:'Online News'}[String(name).toLowerCase()]||name):String(name).toUpperCase())+'</span><b>'+count+' <span class="muted">('+Math.round(count/total*100)+'%)</span></b></button>').join('');
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
    const head='<p class="small muted"><b>'+confirmed+'</b> <span>posts have human-verified incident geography. Map colours represent saved unverified location references, not incident locations.</span></p>';
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
    const sorted=[...rows].sort((a,b)=>a[0].localeCompare(b[0]));
    const latest=new Date(sorted[sorted.length-1][0]+'T00:00:00Z');
    const days=Number(activityWindow);
    const cutoff=new Date(latest.getTime()-(days-1)*86400000).toISOString().slice(0,10);
    const dates=(activityWindow==='all'?sorted:sorted.filter(([d])=>d>=cutoff)).slice(-90);
    if(!dates.length)return '<p class="small muted">No publication dates in this period.</p>';
    const W=480,H=220,left=48,right=15,top=15,bottom=45,plotW=W-left-right,plotH=H-top-bottom;
    const peak=Math.max(1,...dates.map(x=>Number(x[1])||0));
    const step=Math.max(1,Math.ceil(peak/4));
    const ceiling=step*4;
    const pts=dates.map(([day,count],i)=>({
      day,count:Number(count)||0,
      x:left+(dates.length>1?i*plotW/(dates.length-1):plotW/2),
      y:top+plotH-(Number(count)||0)/ceiling*plotH
    }));
    const path=pts.map((p,i)=>(i?'L':'M')+p.x.toFixed(2)+' '+p.y.toFixed(2)).join(' ');
    const area=path+' L'+pts[pts.length-1].x.toFixed(2)+' '+(top+plotH)+' L'+pts[0].x.toFixed(2)+' '+(top+plotH)+' Z';
    const ticks=Array.from({length:5},(_,i)=>i*step);
    const marks=[0,Math.floor((dates.length-1)/2),dates.length-1].filter((n,i,a)=>a.indexOf(n)===i);
    return '<div style="position:relative"><svg viewBox="0 0 '+W+' '+H+'" width="100%" role="img" aria-label="Conversation activity by publication date; horizontal axis shows date and vertical axis shows recorded post count">'+
      ticks.map(v=>{const y=(top+plotH-v/ceiling*plotH).toFixed(2);return '<line x1="'+left+'" y1="'+y+'" x2="'+(W-right)+'" y2="'+y+'" stroke="#e5ebec" stroke-width="1"/><text x="'+(left-9)+'" y="'+(Number(y)+4)+'" text-anchor="end" font-size="11" fill="#667b85">'+v+'</text>';}).join('')+
      '<path d="'+area+'" fill="#278d7a" fill-opacity=".10"/>'+
      '<path d="'+path+'" fill="none" stroke="#278d7a" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round"/>'+
      '<line x1="'+left+'" y1="'+top+'" x2="'+left+'" y2="'+(top+plotH)+'" stroke="#a9b8bf"/>'+
      '<line x1="'+left+'" y1="'+(top+plotH)+'" x2="'+(W-right)+'" y2="'+(top+plotH)+'" stroke="#a9b8bf"/>'+
      pts.map(p=>'<circle tabindex="0" data-activity-day="'+label(p.day)+'" data-activity-count="'+p.count+'" role="button" aria-label="'+label(p.day)+': '+p.count+' posts" cx="'+p.x.toFixed(2)+'" cy="'+p.y.toFixed(2)+'" r="4" fill="#278d7a" fill-opacity=".01" stroke="transparent" stroke-width="5"><title>'+label(p.day)+': '+p.count+' posts</title></circle>').join('')+
      marks.map(n=>'<text x="'+pts[n].x.toFixed(2)+'" y="'+(H-22)+'" text-anchor="'+(n===0?'start':n===dates.length-1?'end':'middle')+'" font-size="10" fill="#667b85">'+label(pts[n].day)+'</text>').join('')+
      '<text x="'+(left+plotW/2)+'" y="'+(H-5)+'" text-anchor="middle" font-size="11" fill="#516875">Date</text>'+
      '<text transform="translate(12 '+(top+plotH/2)+') rotate(-90)" text-anchor="middle" font-size="11" fill="#516875">Posts</text></svg>'+
      '<div id="activityTooltip" role="status" style="display:none;position:absolute;top:0;right:0;background:#14354c;color:white;padding:8px 12px;border-radius:8px;pointer-events:none"></div></div>'+
      '<p class="small muted">Hover or focus the line for the exact date and recorded post count.</p>';
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
    const aiTopics=issueDistribution?.[perspective];
    const analysis=$('#geo')?.value==='all'?(aiTopics?.topics||[]):[];
    const pendingLabel=aiTopics?.refresh_pending?'Saved matching topics · updating new evidence':'Current saved AI topics';
    const topicsLoading=!aiTopics&&($('#geo')?.value==='all');
    const highest=Math.max(1,...analysis.map(x=>x.count));
    const colors={POSITIVE:'#15b87a',NEGATIVE:'#ef4444',NEUTRAL:'#f5bd36',MIXED:'#8b5cf6'};
    $('#issues').innerHTML='<div class="small muted" style="margin-bottom:8px">'+
      (perspective==='operations'?'Electoral Operations':'Bawaslu Reputation')+
      ' · '+label(pendingLabel)+'</div>'+
      (analysis.length?analysis.map(t=>{
        const pct=Math.max(0,Math.min(100,Number(t.count||0)/highest*100));
        return '<button type="button" class="issue-theme" data-issue-id="'+Number(t.id)+'" data-issue-perspective="'+perspective+'" data-issue-title="'+encodeURIComponent(t.title)+
          '" aria-label="View supporting posts for '+label(t.title)+'" style="display:block;width:100%;text-align:left;padding:12px 14px;margin:9px 0;background:#fff;border:1px solid #dce7e8;border-radius:10px;cursor:pointer;color:#17334a" title="'+label(t.description||'')+'">'+
          '<div style="display:flex;justify-content:space-between;gap:12px;align-items:start"><strong data-ai-theme data-i18n-exempt style="font-size:12px;line-height:1.5">'+label(t.title)+'</strong><strong>'+Number(t.count||0)+'</strong></div>'+
          '<div class="small muted" style="margin:5px 0">'+label(t.sentiment||'NEUTRAL')+'</div>'+
          '<div style="background:#e9eef0;border-radius:8px;height:7px"><div style="height:7px;border-radius:8px;background:'+(colors[t.sentiment]||colors.NEUTRAL)+';width:'+pct+'%"></div></div></button>';
      }).join('')+
        '<p class="small muted">Others: '+Number(aiTopics?.others||0)+' · '+Number(aiTopics?.total||0)+' classified saved sources</p>':
        (topicsLoading?'<p class="small muted">Loading saved AI topic classifications…</p>':
          '<p class="small muted">No saved topic classifications for this selection.</p>'))+
      '<p class="small muted" style="margin-top:8px">Select an issue to inspect matching saved posts.</p>';
    const keywords=($('#geo')?.value||'all')==='all'?(dashboard?.main_keyword_cloud||[]):[];
    const maxKeyword=Math.max(1,...keywords.map(x=>Number(x.count||0)));
    $('#cloud').innerHTML=keywords.length?keywords.map(x=>{
      const count=Number(x.count||0);
      const size=13+Math.round(18*Math.sqrt(count/maxKeyword));
      return '<span title="'+label(count+' saved posts')+'" style="font-size:'+size+'px;display:inline-block;margin:4px 7px;line-height:1.3">'+label(x.keyword)+'</span>';
    }).join(''):'<span class="small muted">'+(($('#geo')?.value||'all')==='all'?'No configured main keywords matched the relevant saved posts.':'Main-keyword cloud is national only; regional keywords are not inferred.')+'</span>';

    const dayRows=asRows(addCounts(filtered,'day_counts')).sort((a,b)=>a[0].localeCompare(b[0]));
    $('#trend').innerHTML=trendSvg(dayRows);
    $('#trend').removeAttribute('data-insight');
    const unverifiedLocations=asRows(addCounts(filtered,'geo_signal_counts'));
    const verifiedLocations=asRows(addCounts(filtered,'verified_incident_counts'));
    $('#regions').innerHTML=geoHeatmap(unverifiedLocations,verifiedLocations);
    $('#regions').removeAttribute('data-insight');
    const sentimentCounts=addCounts(filtered,'sentiment_counts');
    // Unclassified is not neutral: preserve the saved Inbox sentiment truth.
    const unlabeled=Number(sentimentCounts.UNCLASSIFIED||0);
    const sentimentRows=[
      ['POSITIVE',Number(sentimentCounts.POSITIVE||0)],
      ['NEUTRAL',Number(sentimentCounts.NEUTRAL||0)],
      ['NEGATIVE',Number(sentimentCounts.NEGATIVE||0)],
      ['UNCLASSIFIED',unlabeled]
    ];
    $('#sentimentExplain').textContent=unlabeled
      ? unlabeled+' saved post'+(unlabeled===1?' has':'s have')+' no reliable sentiment classification; shown separately from Neutral.'
      : 'Sentiment counts use saved classifications only.';
    $('#sentiments').innerHTML=donut(sentimentRows,'sentiment:',sentimentPalette);
    const platforms=asRows(addCounts(filtered,'platform_counts'));
    $('#platforms').innerHTML=donut(platforms,'platform:',platformPalette);
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
  function renderLegalOversight(data){
    const legal=$('#legalCaseQueue'),platform=$('#platformRulesQueue'),steps=$('#legalFollowup');
    if(!legal||!platform||!steps)return;
    const cases=Array.isArray(data?.review_queue)?data.review_queue:[];
    const count=Number(data?.suspected_cases_in_sample||0);
    const countText=count+' candidates from '+Number(data?.sampled_relevant_posts||0)+' retrieved posts (sample only)';
    const link=post=>'/inbox?campaign_id='+encodeURIComponent(post.campaign_id||'')+
      '&result_id='+encodeURIComponent(post.source_id||'');
    // These are two independent decisions: an allegation under election law
    // must NOT automatically appear as a social platform-rules breach.
    if(!cases.length){
      legal.innerHTML='<p class="small muted">No legal-violation signals in the retrieved review sample. This does not prove that none exist.</p>';
    }else{
      legal.innerHTML='<p class="small muted">'+label(countText)+'</p>'+
        cases.slice(0,5).map(post=>'<div style="padding:9px 0;border-bottom:1px solid #e5eaf0">'+
          '<div style="font-weight:650;font-size:13px">'+label(post.excerpt.slice(0,120))+'</div>'+
          '<div class="small muted">'+label(post.platform)+' · Source #'+label(post.source_id)+
          ' · Human review: '+label(post.human_flag_status)+'</div>'+
          '<a href="'+link(post)+'" target="_top" rel="noopener noreferrer" class="small">Inspect evidence & assign legal review ↗</a>'+
          '</div>').join('');
    }
    const screening=data?.platform_policy_screening||{};
    const platformCases=Array.isArray(screening.review_queue)?screening.review_queue:[];
    const direct=Number(screening.review_signal_count_in_sample||0);
    const contextual=Number(screening.reported_or_contextual_count_in_sample||0);
    const sample=Number(screening.screened_posts_in_sample||0);
    const policies=Array.isArray(screening.policy_links)?screening.policy_links:[];
    const screeningSummary='<div class="small muted" style="margin-bottom:9px">'+
       label(direct)+' direct review signals · '+label(contextual)+
       ' reported/quoted-context signals among '+label(sample)+' supported-platform posts (sample only)</div>';
    const disclaimer='<p class="small muted" style="margin-bottom:8px">Text-only screening, not a confirmed policy breach. Ordinary political criticism or negative sentiment does not establish a violation. Verify the original content and current policy before reporting.</p>';
    const policyLibrary=policies.length?
       '<div style="padding-top:10px;border-top:1px solid #e5eaf0">'+
         '<strong class="small">Official platform policies</strong><div class="small" style="display:flex;flex-wrap:wrap;gap:10px;margin-top:6px">'+
         policies.map(policy=>'<a href="'+label(safeUrl(policy.policy_url))+
           '" target="_blank" rel="noopener noreferrer">'+label(policy.platform)+' ↗</a>').join('')+
         '</div><p class="small muted">Policy links were checked on 2026-11-10; confirm current versions before enforcement.</p></div>':'';
    if(!platformCases.length){
      platform.innerHTML=screeningSummary+disclaimer+
        '<p class="small muted">No direct threat, privacy-exposure or coordinated-harassment call was detected by these limited text checks. This does not prove the posts comply with all community rules.</p>'+policyLibrary;
    }else{
      platform.innerHTML=screeningSummary+disclaimer+
        platformCases.slice(0,6).map(post=>{
          const contextual=post.status==='CONTEXT_REVIEW_REQUIRED';
          const cues=Array.isArray(post.review_categories)?post.review_categories:[];
          const categories=cues.map(key=>post.category_labels?.[key]?.en||key).join(' · ');
          const official=safeUrl(post.policy_url);
          return '<div style="padding:10px 0;border-bottom:1px solid #e5eaf0">'+
            '<div style="display:flex;gap:8px;flex-wrap:wrap;align-items:center">'+
            '<strong>'+label(post.platform)+'</strong>'+
            '<span class="small muted">'+(contextual?'News/quotation context – verify':'Source-text signal – inspect')+'</span></div>'+
            '<div class="small" style="font-weight:600;color:#8b2733;margin:4px 0">'+label(categories)+'</div>'+
            '<div class="small" style="color:#32465a">'+label((post.excerpt||'').slice(0,155))+'</div>'+
            '<p class="small muted" style="margin:4px 0">Source #'+label(post.source_id)+' · No platform or legal breach determined.</p>'+
            '<a href="'+link(post)+'" target="_top" rel="noopener noreferrer" class="small">Inspect original evidence ↗</a>'+
            (official?' · <a href="'+label(official)+'" target="_blank" rel="noopener noreferrer" class="small">Read official platform rules ↗</a>':'')+
            '</div>';
        }).join('')+policyLibrary;
    }
    const stepsList=Array.isArray(data?.legal_follow_up_steps)?data.legal_follow_up_steps:[];
    const refs=(data?.legal_references||[]).slice(0,3);
    steps.innerHTML='<ol style="padding-left:20px;margin:8px 0">'+stepsList.map(x=>'<li style="margin-bottom:6px">'+label(x)+'</li>').join('')+'</ol>'+
      (refs.length?'<div class="small muted">Uploaded PDF references (authority/currentness not yet validated): '+
        refs.map(r=>label(r.title)+' · p.'+Number(r.page)).join(' · ')+'</div>':
        '<div class="small muted">No matched uploaded legal PDF. Check current official law and platform policies before any formal decision.</div>');
  }
  async function refreshLegalOversight(epoch){
    try{
      const data=await request('/api/oversight/legal-summary');
      if(epoch!==dashboardEpoch)return;
      renderLegalOversight(data);
    }catch(e){
      if(epoch!==dashboardEpoch)return;
      if($('#legalCaseQueue'))$('#legalCaseQueue').textContent='Legal review data unavailable: '+String(e.message||'error');
      if($('#platformRulesQueue'))$('#platformRulesQueue').textContent='Platform policy review data unavailable.';
    }
  }
  let dashboardEpoch=0;
  async function refresh() {
    const epoch=++dashboardEpoch;
    // Render the evidence dashboard first; expensive issue analysis never blocks first paint.
    const primary=await request('/api/smart-radar/dashboard');
    if(epoch!==dashboardEpoch)return;
    if(primary.mode!=='SAVED_INBOX_SOURCE_OF_TRUTH')throw Error('Radar returned a non-Inbox evidence feed');
    if(!Array.isArray(primary.findings))throw Error('Incomplete authorized dashboard response');
    dashboard=primary;
    // Legal/policy review is supplementary and never delays the main dashboard.
    refreshLegalOversight(epoch);
    // Geographic options reflect saved source mentions, not confirmed incident location.
    const geoSelect=$('#geo');
    if(geoSelect&&!geoSelect.disabled){
      const current=geoSelect.value;
      const provinces=Object.entries(dashboard.geo_signal_counts||{})
        .filter(([name,count])=>name&&Number(count)>0&&name.toLowerCase()!=='indonesia')
        .map(([name])=>name).sort((a,b)=>a.localeCompare(b));
      geoSelect.innerHTML='<option value="all">Indonesia — National</option>'+provinces.map(name=>
        '<option value="'+label(name)+'">'+label(name)+'</option>').join('');
      geoSelect.value=provinces.includes(current)?current:'all';
    }
    ui.setData((dashboard.findings||[]).map(mapFinding));
    document.body.classList.add('bawaslu-ready');
    // Refresh auxiliary topics after main paint. Failures must not clear existing topics.
    request('/api/smart-radar/issue-distribution').then(topics=>{
      if(epoch!==dashboardEpoch)return;
      issueDistribution=topics;
      decorate();
    }).catch(error=>console.warn('AI issue topics unavailable',error.message));
  }
  function issuePostHeadline(post){
    const explicit=String(post.title||post.headline||'').replace(/\s+/g,' ').trim();
    if(explicit && !/^post\s*\d+\s*[·:-]\s*(?:social:)?\d+$/i.test(explicit))return explicit.slice(0,155);
    const text=String(post.text||'').replace(/https?:\/\/\S+/g,' ').replace(/\s+/g,' ').trim();
    if(!text)return 'Saved source post';
    // A source-grounded heading, not a new AI claim or a guessed violation.
    const sentenceEnd=text.search(/[.!?](?:\s|$)/);
    const first=sentenceEnd>=28&&sentenceEnd<=150?text.slice(0,sentenceEnd+1):text;
    if(first.length<=122)return first;
    const boundary=first.slice(0,123).lastIndexOf(' ');
    return (boundary>70?first.slice(0,boundary):first.slice(0,120)).replace(/[\s,;:.]+$/,'')+'…';
  }
  let issueLastFocus=null;
  function closeIssueModal(){
    const modal=document.getElementById('issueSourceModal');
    if(!modal)return;
    modal.remove();
    if(issueLastFocus?.isConnected)issueLastFocus.focus();
    issueLastFocus=null;
  }
  document.addEventListener('keydown',event=>{if(event.key==='Escape')closeIssueModal();});
  document.addEventListener('click',event=>{
    const toggle=event.target.closest?.('[data-issue-post-toggle]');
    if(!toggle)return;
    const paragraph=document.getElementById(toggle.getAttribute('aria-controls'));
    if(!paragraph)return;
    const expanded=paragraph.classList.toggle('expanded');
    toggle.setAttribute('aria-expanded',String(expanded));
    toggle.textContent=expanded?'See less ↑':'See more ↓';
  });
  document.addEventListener('click',async event=>{
    const hit=event.target.closest?.('[data-issue-id]');
    if(!hit)return;
    event.preventDefault();
    closeIssueModal();
    issueLastFocus=hit;
    const name=decodeURIComponent(hit.dataset.issueTitle||'');
    const modal=document.createElement('div');
    modal.id='issueSourceModal';
    modal.setAttribute('role','dialog');
    modal.setAttribute('aria-modal','true');
    modal.setAttribute('aria-label','Supporting posts: '+name);
    modal.style.cssText='position:fixed;inset:0;z-index:10000;background:rgba(8,27,40,.65);display:flex;align-items:center;justify-content:center;padding:18px';
    modal.innerHTML='<div class="issue-source-dialog">'+
      '<div class="issue-source-dialog-header">'+
      '<div><strong style="font-size:17px;line-height:1.4">'+label(name)+'</strong><p class="small muted" style="margin:6px 0 0">Saved source posts related to this issue</p></div>'+
      '<button type="button" data-close-issue aria-label="Close supporting posts" class="issue-source-close">✕ Close</button></div>'+
      '<div data-issue-content role="status" class="issue-source-list">Loading source posts…</div></div>';
    document.body.appendChild(modal);
    modal.addEventListener('click',e=>{if(e.target===modal||e.target.closest('[data-close-issue]'))closeIssueModal();});
    modal.querySelector('[data-close-issue]')?.focus();
    const content=modal.querySelector('[data-issue-content]');
    try{
      const result=await request('/api/smart-radar/issue-distribution/posts?perspective='+encodeURIComponent(hit.dataset.issuePerspective)+'&topic_id='+encodeURIComponent(hit.dataset.issueId));
      if(!modal.isConnected)return;
      const posts=result.posts||[];
      content.removeAttribute('role');
      content.innerHTML='<p class="small muted" style="margin:0 0 16px">'+Number(result.total||0)+' matching saved posts'+(Number(result.total||0)>posts.length?' · Showing first '+posts.length:'')+'</p>'+
        (posts.length?posts.map((p,i)=>{
          const detailId='issue-post-description-'+i;
          const heading=issuePostHeadline(p);
          return '<article class="issue-source-card"><h3 class="issue-source-heading">'+label(heading)+'</h3>'+
            '<p id="'+detailId+'" class="issue-source-description">'+label(p.text||'')+'</p>'+
            '<button type="button" class="issue-source-expand" data-issue-post-toggle aria-expanded="false" aria-controls="'+detailId+'" hidden>See more ↓</button>'+
            '</article>';
        }).join(''):'<p>No saved posts currently assigned to this issue.</p>');
      content.querySelectorAll('[data-issue-post-toggle]').forEach(button=>{
        const paragraph=document.getElementById(button.getAttribute('aria-controls'));
        if(paragraph && (paragraph.scrollHeight>paragraph.clientHeight+2 || paragraph.textContent.length>260)){
          button.hidden=false;
        }
      });
    }catch(error){if(modal.isConnected)content.innerHTML='<p role="alert">Could not load posts: '+label(error.message)+'</p>';}
  });
  document.addEventListener('click',async event=>{
    const button=event.target.closest?.('[data-refresh-player]');
    if(!button)return;
    event.preventDefault();event.stopPropagation();
    const player=button.dataset.refreshPlayer;
    if(!['violations','concerns','narratives'].includes(player)||refreshingPlayers.has(player))return;
    if(!window.confirm('Regenerate only the '+player+' AI intelligence summary using OpenAI? A paid request may be charged.'))return;
    refreshingPlayers.add(player);button.disabled=true;button.textContent='⟳';
    try{
      const result=await request('/api/smart-radar/summarize-live?player='+encodeURIComponent(player)+'&force=true',
        {method:'POST',body:'{}'});
      await refresh();
      const resultText=(result.generated||[]).length+' intelligence summaries regenerated; '+(result.remaining||0)+' findings remaining.';
      const toast=$('#toast');if(toast){toast.textContent=resultText;toast.style.display='block';}
    }catch(error){
      const toast=$('#toast');if(toast){toast.textContent='AI regeneration failed: '+error.message;toast.style.display='block';}console.warn('Player refresh failed',player,error);
    }finally{refreshingPlayers.delete(player);button.disabled=false;button.textContent='↻';}
  });
  document.addEventListener('change',event=>{
    if(event.target?.id!=='activityTimeframe')return;
    activityWindow=event.target.value;
    decorate();
  });
  async function boot() {
    let access = null;
    try {
      // Access lookup and initial dashboard request are independent; start together.
      const dashboardLoading=refresh();
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
      await dashboardLoading;
      fetch('/indonesia-provinces.geojson',{cache:'force-cache'})
        .then(r=>{if(!r.ok)throw Error('Map unavailable');return r.json()})
        .then(data=>{if(!Array.isArray(data?.features))throw Error('Invalid map');provinceGeo=data;decorate()})
        .catch(()=>{provinceGeoFailed=true;decorate()});

    } catch (error) {
      document.body.classList.add('bawaslu-ready');
      const region = access?.province || 'your assigned scope';
      const message = 'Unable to load authorized Intelligence Inbox evidence for Smart Radar: '+error.message;
      // Do not fabricate zero intelligence on failed reads; retain last valid data.
      if (access?.geographic_scope !== 'Nationwide' && $('#scopeLabel')) {
        $('#scopeLabel').textContent=region+' · Source-scope restricted';
      }
      const retiredExecutive=$('#executive');if(retiredExecutive)retiredExecutive.textContent=message;
      const status=$('#startup-status');
      if(status){status.innerHTML='<strong>Command Centre data temporarily unavailable</strong><p>'+label(message)+'</p><button type="button" id="retryRadarLoad" style="margin-top:10px;padding:9px 14px;background:#117f6d;color:white;border:0;border-radius:8px;cursor:pointer">Retry loading</button>';status.classList.add('error');status.setAttribute('role','alert');}
      document.body.classList.add('bawaslu-ready');
    }
  }
  document.addEventListener('click',e=>{if(e.target?.id==='retryRadarLoad'){const status=$('#startup-status');if(status){status.classList.remove('error');status.textContent='Retrying authorised intelligence…';}document.body.classList.remove('bawaslu-ready');clearReadCache();boot();}});
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
      if($('#historyLoading') && $('#overlay')?.classList.contains('open'))
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
         !$('#overlay').classList.contains('open'))return;
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
    ui.view().filter(f=>{const kind=decodeURIComponent(id.slice(10)).toUpperCase();return Number(f.sentiment_counts?.[kind]||0)>0;}) :
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