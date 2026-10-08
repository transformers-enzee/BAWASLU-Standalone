import { useState } from 'react';
import JurisdictionFields from './JurisdictionFields';
import { Notice, err } from './Fields';
import { useLanguage } from '@/lib/LanguageContext';

export default function GeographicMismatch({ item, canReview, onSaved, onRecordAction }) {
  const {t}=useLanguage();
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
    if (!reason.trim()) { setError(t('analyst_reason_required')); return; }
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

  return <section className="intel-card p-6 space-y-4" aria-label={t('geographic_mismatch')}>
    <h2 className="font-semibold text-lg">{mismatch.status === 'pending' ? t('geographic_mismatch_required') : t('geographic_mismatch_reviewed')}</h2>

    <div className="grid sm:grid-cols-2 gap-4 text-sm">
      <div><span className="intel-label">{t('confirmed_jurisdiction')}</span>{item.jurisdiction_type || t('unresolved')} · {confirmed || t('national')}</div>
      <div><span className="intel-label">{t('ai_source_jurisdiction')}</span>{proposed.jurisdiction_type || t('unresolved')} · {proposedLocation || t('no_location_recorded')}</div>
    </div>

    <div className="text-sm">
      <span className="intel-label">{t('supporting_location_evidence')}</span>
      <p className="whitespace-pre-wrap">{mismatch.supporting_text || proposed.supporting_text || proposed.evidence || t('no_supporting_text')}</p>
    </div>

    {proposed.confidence !== undefined && proposed.confidence !== '' && <p className="text-sm"><span className="intel-label">{t('ai_confidence')}</span>{String(proposed.confidence)}</p>}

    {mismatch.status === 'pending' && <p className="text-sm text-muted-foreground">{t('final_validation_blocked')}</p>}

    {resolved && <div className="text-sm space-y-1">
      <p>{t('decision_label')}: {mismatch.decision || t('human_reviewed')}</p>
      <p>{t('reviewed_by')} {mismatch.reviewed_by || t('authorized_reviewer')}{mismatch.reviewed_at ? ` · ${new Date(mismatch.reviewed_at).toLocaleString('en-GB')}` : ''}</p>
      {mismatch.reason && <p>{t('reason')}: {mismatch.reason}</p>}
      {mismatch.resulting_jurisdiction&&<p>{t('resulting_jurisdiction')}: {mismatch.resulting_jurisdiction.jurisdiction_type || t('unresolved')} · {[mismatch.resulting_jurisdiction.regency_city,mismatch.resulting_jurisdiction.province].filter(Boolean).join(', ') || t('national')}</p>}
    </div>}
    {mismatch.review_reopened&&<p className="text-sm font-semibold text-[#a04724]">{t('review_reopened')}</p>}

    <Notice error={error}/>

    {canReview && mismatch.status === 'pending' && <div className="space-y-3 border-t pt-4">
      <label className="block">
        <span className="intel-label">{t('analyst_note_reason')}</span>
        <textarea className="intel-input" required value={reason} onChange={e => setReason(e.target.value)} />
      </label>

      <div className="flex flex-wrap gap-2">
        <button type="button" className="intel-ghost" disabled={busy} onClick={() => decide('KEEP_CONFIRMED_JURISDICTION')}>{t('keep_confirmed_jurisdiction')}</button>
        <button type="button" className="intel-ghost" disabled={busy} onClick={() => {
          setChanging(true);
          setGeo({
            jurisdiction_type: proposed.jurisdiction_type || 'Unresolved',
            province_code: proposed.province_code || '',
            regency_city_code: proposed.regency_city_code || '',
            geographic_assignments: proposed.geographic_assignments || []
          });
        }}>{t('change_jurisdiction')}</button>
      </div>

      {changing && <div className="space-y-3">
        <JurisdictionFields value={geo || { jurisdiction_type:'Unresolved', province_code:'', regency_city_code:'', geographic_assignments:[] }} onChange={setGeo}/>
        <button type="button" className="intel-button" disabled={busy} onClick={() => decide('CHANGE_JURISDICTION')}>{busy ? t('saving') : t('confirm_changed_jurisdiction')}</button>
        <button type="button" className="intel-ghost" onClick={() => setChanging(false)}>{t('cancel')}</button>
      </div>}
    </div>}
  </section>;
}
