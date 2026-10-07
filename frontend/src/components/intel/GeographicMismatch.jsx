import { useState } from 'react';
import JurisdictionFields from './JurisdictionFields';
import { Notice, err } from './Fields';

export default function GeographicMismatch({ item, canReview, onSaved, onRecordAction }) {
  const mismatch = item?.geographic_mismatch;
  const [reason, setReason] = useState('');
  const [changing, setChanging] = useState(false);
  const [geo, setGeo] = useState(null);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState('');

  if (!mismatch || mismatch.status === 'none') return null;

  const proposed = mismatch.proposed || {};
  const confirmed = item.jurisdiction_type === 'Multi-Region'
    ? (item.geographic_assignments || []).map(x => [x.regency_city, x.province].filter(Boolean).join(', ')).filter(Boolean).join(' · ')
    : [item.regency_city, item.province].filter(Boolean).join(', ');

  const proposedLocation = proposed.jurisdiction_type === 'Multi-Region'
    ? (proposed.geographic_assignments || []).map(x => [x.regency_city, x.province].filter(Boolean).join(', ')).filter(Boolean).join(' · ')
    : [proposed.regency_city || proposed.regency_city_name, proposed.province || proposed.province_name].filter(Boolean).join(', ');

  async function decide(decision) {
    if (!reason.trim()) { setError('An analyst note / reason is required.'); return; }
    setBusy(true); setError('');
    try {
      await onRecordAction('reviewGeographicMismatch', {
        decision,
        reason,
        ...(decision === 'CHANGE_JURISDICTION' ? (geo || {}) : {}),
        proposed
      }, item.id);
      setReason('');
      setChanging(false);
      setGeo(null);
      await onSaved();
    } catch (e) {
      setError(err(e));
    } finally {
      setBusy(false);
    }
  }

  const resolved = mismatch.status === 'resolved';

  return <section className="intel-card p-6 space-y-4" aria-label="Geographic mismatch review">
    <h2 className="font-semibold text-lg">{mismatch.status === 'pending' ? 'GEOGRAPHIC MISMATCH — REVIEW REQUIRED' : 'Geographic mismatch — human reviewed'}</h2>

    <div className="grid sm:grid-cols-2 gap-4 text-sm">
      <div><span className="intel-label">Confirmed jurisdiction</span>{item.jurisdiction_type || 'Unresolved'} · {confirmed || 'National'}</div>
      <div><span className="intel-label">AI/source-supported jurisdiction · NOT authoritative</span>{proposed.jurisdiction_type || 'Unresolved'} · {proposedLocation || 'No location recorded'}</div>
    </div>

    <div className="text-sm">
      <span className="intel-label">Supporting source-location evidence</span>
      <p className="whitespace-pre-wrap">{mismatch.supporting_text || proposed.supporting_text || proposed.evidence || 'No supporting text recorded.'}</p>
    </div>

    {proposed.confidence !== undefined && proposed.confidence !== '' && <p className="text-sm"><span className="intel-label">AI confidence</span>{String(proposed.confidence)}</p>}

    {mismatch.status === 'pending' && <p className="text-sm text-muted-foreground">Final validation is blocked until an authorized human resolves this mismatch. Source evidence cannot change the confirmed jurisdiction automatically.</p>}

    {resolved && <div className="text-sm space-y-1">
      <p>Decision: {mismatch.decision || 'Human reviewed'}</p>
      <p>Reviewed by {mismatch.reviewed_by || 'authorized reviewer'}{mismatch.reviewed_at ? ` · ${new Date(mismatch.reviewed_at).toLocaleString('en-GB')}` : ''}</p>
      {mismatch.reason && <p>Reason: {mismatch.reason}</p>}
    </div>}

    <Notice error={error}/>

    {canReview && mismatch.status === 'pending' && <div className="space-y-3 border-t pt-4">
      <label className="block">
        <span className="intel-label">Analyst note / reason *</span>
        <textarea className="intel-input" required value={reason} onChange={e => setReason(e.target.value)} />
      </label>

      <div className="flex flex-wrap gap-2">
        <button type="button" className="intel-ghost" disabled={busy} onClick={() => decide('KEEP_CONFIRMED_JURISDICTION')}>KEEP CONFIRMED JURISDICTION</button>
        <button type="button" className="intel-ghost" disabled={busy} onClick={() => {
          setChanging(true);
          setGeo({
            jurisdiction_type: proposed.jurisdiction_type || 'Unresolved',
            province_code: proposed.province_code || '',
            regency_city_code: proposed.regency_city_code || '',
            geographic_assignments: proposed.geographic_assignments || []
          });
        }}>CHANGE JURISDICTION</button>
      </div>

      {changing && <div className="space-y-3">
        <JurisdictionFields value={geo || { jurisdiction_type:'Unresolved', province_code:'', regency_city_code:'', geographic_assignments:[] }} onChange={setGeo}/>
        <button type="button" className="intel-button" disabled={busy} onClick={() => decide('CHANGE_JURISDICTION')}>{busy ? 'Saving...' : 'Confirm changed jurisdiction'}</button>
        <button type="button" className="intel-ghost" onClick={() => setChanging(false)}>Cancel</button>
      </div>}
    </div>}
  </section>;
}
