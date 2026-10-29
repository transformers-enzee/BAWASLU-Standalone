import { useCallback, useEffect, useState } from 'react';

// Integration controls must always operate on the authenticated Standalone host.
// A build-time external API override could silently target another database.
const API = '';
async function api(path, options = {}) {
  const token = window.localStorage.getItem('bawaslu_access_token');
  if (!token) throw new Error('Please sign in with an authorized National Administrator account.');
  const response = await fetch(API + '/api/integration/' + path, {
    ...options,
    cache: 'no-store',
    headers: { Authorization: 'Bearer ' + token, ...(options.body ? {'Content-Type':'application/json'} : {}) }
  });
  const data = await response.json().catch(() => ({}));
  if (!response.ok) throw new Error(response.status === 403 ? 'National Administrator access is required.' : data.detail || 'Integration request failed');
  return data;
}
const cell = 'px-3 py-2 border-b border-slate-200 text-left text-sm';
export default function IntegrationReadiness() {
  const [metrics, setMetrics] = useState(null);
  const [preview, setPreview] = useState(null);
  const [queue, setQueue] = useState(null);
  const [offset, setOffset] = useState(0);
  const [confirm, setConfirm] = useState(false);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState('');
  const [notice, setNotice] = useState('');
  const refresh = useCallback(async (nextOffset=offset) => {
    setBusy(true); setError('');
    try {
      const [m,p,q] = await Promise.all([
        api('readiness'),api('source-id-backfill/preview'),
        api('provenance-review-queue?limit=25&offset='+nextOffset)
      ]);
      setMetrics(m); setPreview(p); setQueue(q); setOffset(nextOffset); setConfirm(false);
    } catch(e) {
      setMetrics(null); setPreview(null); setQueue(null); setConfirm(false);
      setError(e.message);
    }
    finally {setBusy(false);}
  },[offset]);
  useEffect(()=>{refresh(0);},[]);
  async function applyBackfill() {
    if (!confirm || !preview || !metrics?.release_gates?.database_population_verified || busy || preview.conflicting_nonblank_ids !== 0 || preview.eligible_missing_ids < 1) return;
    setBusy(true); setError(''); setNotice('');
    try {
      const result=await api('source-id-backfill/apply',{
        method:'POST', body:JSON.stringify({confirm:true,expected_missing:preview.eligible_missing_ids})
      });
      setNotice('Historical canonical IDs repaired: '+result.updated+'. Refreshing live counts.');
      await refresh(0);
    } catch(e){setError(e.message);setConfirm(false);setBusy(false);}
  }
  return <main className="max-w-6xl mx-auto px-3 sm:px-6 py-6 space-y-6">
    <header><h1 className="text-2xl font-bold text-slate-900">Integration Readiness</h1>
      <p className="text-sm text-slate-600 mt-1">National Administrator only. Read-only source review; no paid searches or inferred metadata.</p></header>
    {error && <p role="alert" className="p-3 bg-red-50 text-red-800 rounded">{error}</p>}
    {notice && <p role="status" className="p-3 bg-emerald-50 text-emerald-800 rounded">{notice}</p>}
    <button className="px-4 py-2 bg-slate-900 text-white rounded disabled:opacity-50" onClick={()=>refresh(0)} disabled={busy}>{busy?'Working…':'Refresh readiness'}</button>
    {metrics && <p className="text-xs text-slate-600">API host: this Standalone service · Database engine: {metrics.database_engine || "unknown"} · Database: {metrics.database_name || "unknown"} · Schema: {metrics.database_schema || "unknown"}</p>}
    {metrics?.data_source_status==='empty_or_uninitialized' && <p role="alert" className="p-4 rounded border border-red-300 bg-red-50 text-red-900 font-medium">Staging database mismatch or empty app database: this environment has zero Social Listening and Intelligence records. Do not treat zero missing fields as complete, and do not run historical repair here. Verify the deployed service DATABASE_URL points to the intended Render PostgreSQL instance.</p>}
    {metrics && <section className="bg-white border rounded-xl p-4">
      <h2 className="font-semibold text-lg mb-3">Staging quality</h2>
      <div className="grid grid-cols-2 md:grid-cols-4 gap-3 text-sm">
        <div><p className="text-slate-500">Social posts</p><p className="text-2xl font-semibold">{metrics.social_posts?.total ?? '—'}</p></div>
        <div><p className="text-slate-500">Missing publication time</p><p className="text-2xl font-semibold">{metrics.social_posts?.missing_publication ?? '—'}</p></div>
        <div><p className="text-slate-500">Missing original content</p><p className="text-2xl font-semibold">{metrics.social_posts?.missing_content ?? '—'}</p></div>
        <div><p className="text-slate-500">Missing canonical IDs</p><p className="text-2xl font-semibold">{metrics.promotion_lineage?.eligible_backfill ?? '—'}</p></div>
      </div>
      <p className="text-sm mt-3 text-slate-600">Release status: {metrics.release_gates?.database_population_verified === false ? 'Data source unverified' : metrics.release_gates?.promoted_source_id_integrity?'ID integrity passed':'ID backfill required'} · {metrics.release_gates?.database_population_verified === false ? 'Provenance cannot be assessed' : metrics.release_gates?.social_source_provenance_complete?'Provenance complete':'Provenance review required'}. Final role/browser UAT remains mandatory.</p>
    </section>}
    {metrics && <section className="bg-white border rounded-xl p-4 space-y-3">
      <h2 className="font-semibold text-lg">Classification and processing quality</h2>
      <p className="text-xs text-slate-600">Read-only counts of saved records. No paid AI calls, inferred sentiment, or verified jurisdiction are implied. Job attempts are not token-cost accounting.</p>
      <div className="grid grid-cols-2 md:grid-cols-4 gap-3 text-sm">
        <div><p className="text-slate-500">Saved assessments</p><p className="text-xl font-semibold">{metrics.assessment_quality?.total ?? '—'}</p></div>
        <div><p className="text-slate-500">AI-relevant</p><p className="text-xl font-semibold">{metrics.assessment_quality?.relevant ?? '—'}</p></div>
        <div><p className="text-slate-500">Sentiment classified</p><p className="text-xl font-semibold">{metrics.assessment_quality?.sentiment_classified ?? '—'}</p></div>
        <div><p className="text-slate-500">Potential issue signals absent</p><p className="text-xl font-semibold">{metrics.assessment_quality?.no_potential_issue_signals ?? '—'}</p></div>
        <div><p className="text-slate-500">Campaign evidence links</p><p className="text-xl font-semibold">{metrics.campaign_source_quality?.linked ?? '—'}</p></div>
        <div><p className="text-slate-500">Missing campaign source URLs</p><p className="text-xl font-semibold">{metrics.campaign_source_quality?.missing_url ?? '—'}</p></div>
        <div><p className="text-slate-500">Repeated-text groups</p><p className="text-xl font-semibold">{metrics.campaign_duplicate_text?.duplicate_groups ?? '—'}</p></div>
        <div><p className="text-slate-500">Assessment jobs with errors</p><p className="text-xl font-semibold">{metrics.assessment_jobs?.with_error_message ?? '—'}</p></div>
        <div><p className="text-slate-500">AI assessment attempts</p><p className="text-xl font-semibold">{metrics.assessment_jobs?.attempts ?? '—'}</p></div>
        <div><p className="text-slate-500">Accepted potential issue signals</p><p className="text-xl font-semibold">{metrics.assessment_signal_diagnostics?.accepted_signals ?? '—'}</p></div>
        <div><p className="text-slate-500">Smart Radar pilot posts</p><p className="text-xl font-semibold">{metrics.smart_radar_pilot_posts ?? '—'}</p></div>
      </div>
    </section>}
    {preview && <section className="bg-white border rounded-xl p-4 space-y-3">
      <h2 className="text-lg font-semibold">Historical source-ID repair</h2>
      <p className="text-sm text-slate-700">Linked: {preview.linked}. Eligible missing IDs: {preview.eligible_missing_ids}. Conflicts: {preview.conflicting_nonblank_ids}. Only saved Social Listening promotion links may be repaired.</p>
      {!!preview.proposed_links?.length && <div className="overflow-x-auto"><table className="w-full text-sm"><thead><tr><th className={cell}>Existing social source</th><th className={cell}>Intelligence row</th></tr></thead><tbody>{preview.proposed_links.map(link=><tr key={link.source_id}><td className={cell}>{link.source_id}</td><td className={cell}>{link.intelligence_row_id}</td></tr>)}</tbody></table></div>}
      <label className="flex gap-2 items-start text-sm">
        <input type="checkbox" checked={confirm} disabled={busy || preview.eligible_missing_ids<1 || preview.conflicting_nonblank_ids>0} onChange={e=>setConfirm(e.target.checked)} className="mt-1"/>
        I reviewed the current preview and authorize updating exactly {preview.eligible_missing_ids} blank canonical source IDs. Existing populated IDs and evidence will not be overwritten.
      </label>
      <button className="px-4 py-2 rounded bg-amber-700 text-white disabled:opacity-40" disabled={!confirm||busy||preview.eligible_missing_ids<1||preview.conflicting_nonblank_ids>0} onClick={applyBackfill}>Apply reviewed ID repair</button>
    </section>}
    {queue && <section className="bg-white border rounded-xl p-4 space-y-3">
      <h2 className="text-lg font-semibold">Source provenance review queue</h2>
      <p className="text-sm text-slate-600">{queue.total} records require review · {queue.remaining_after_page} remaining after this page. Source content and URLs are not included.</p>
      <div className="overflow-x-auto"><table className="w-full"><thead><tr><th className={cell}>Canonical source ID</th><th className={cell}>Platform</th><th className={cell}>Missing fields</th></tr></thead>
      <tbody>{queue.results.map(item=><tr key={item.source_id}><td className={cell}>{item.source_id}</td><td className={cell}>{item.platform}</td><td className={cell}>{item.missing_fields.join(', ')}</td></tr>)}</tbody></table></div>
      <div className="flex gap-3">
        <button className="px-3 py-2 border rounded disabled:opacity-40" disabled={busy||offset===0} onClick={()=>refresh(Math.max(0,offset-25))}>Previous</button>
        <button className="px-3 py-2 border rounded disabled:opacity-40" disabled={busy||!queue.has_more} onClick={()=>refresh(offset+25)}>Next</button>
      </div>
    </section>}
  </main>;
}
