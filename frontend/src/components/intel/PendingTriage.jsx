import { useState } from 'react';
import { Sparkles } from 'lucide-react';
import { Notice, err } from './Fields';
import PendingSuggestionRow from './PendingSuggestionRow';
import WatchlistMatchRow from './WatchlistMatchRow';
import { triageReview } from './triageReview';
import { triagePresentation } from './triagePresentation';
import { useLanguage } from '@/lib/LanguageContext';

const sectionKey={
 'Source Understanding':'triage_source_understanding',
 'Intelligence Extraction':'triage_intelligence_extraction',
 'Supervision Screening':'triage_supervision_screening',
 'Evidence Assessment':'triage_evidence_assessment'
};

export default function PendingTriage({item,watchlist,generation,onSaved,onRecordAction}){
 const {t,label}=useLanguage();
 const [busy,setBusy]=useState(false),[error,setError]=useState('');
 const saved=item.ai_suggestions||{};
 const suggestions=item.source_type==='REGISTERED_OWNED_CHANNEL'&&saved.watchlist_match?.id===item.owned_channel?.candidate_id?{...saved,watchlist_match:null}:saved;
 const decisions=suggestions._decisions||{};
 const review=item.triage_review||triageReview(suggestions);
 const hasTriage=review.generated;
 const presentation=triagePresentation(suggestions);

 async function run(){
  setBusy(true);setError('');
  try{await onRecordAction('runTriage',{},item.id);await onSaved()}
  catch(e){setError(err(e))}
  finally{setBusy(false)}
 }

 async function decide(key,status,value,reason){
  setBusy(true);setError('');
  try{await onRecordAction('triageDecision',{key,status,value,reason},item.id);await onSaved()}
  catch(e){setError(err(e));return false}
  finally{setBusy(false)}
  return true;
 }

 const sourceLanguage=generation?.language_resolution?.label||item.language_resolution?.label||item.original_language||t('undetermined');
 const stateText=label(review.state)||review.state;

 return <section id="ai-triage-review" className="intel-card p-6 space-y-4 scroll-mt-6">
  <div>
   <h2 className="font-semibold text-lg">{t('ai_triage_review_title')}</h2>
   <p className="text-xs font-bold tracking-wide text-[#267291] mt-2">{t('ai_triage_only')}</p>
   <p className="text-xs text-[#708295] mt-2">{t('original_source_language')}: {sourceLanguage}. {t('suggestions_pending_note')}</p>
  </div>

  <p role="status" className="text-sm font-semibold text-[#29445d]">
   {t('review_state')}: {stateText}
   {review.generated?' · '+review.reviewed+' '+t('of_word')+' '+review.total+' '+t('suggestions_decided'):''}
   {review.legacy?' · '+t('legacy_unavailable'):''}
   {review.state==='REVIEW COMPLETE'?' · '+t('ready_final_validation'):''}
  </p>

  <Notice error={error}/>

  {generation&&<>
   <p className="text-xs text-[#617789]">{t('generation')}: {generation.triage_run_id} · Schema V{generation.triage_schema_version} · {generation.generator} ({generation.generator_version}) · {generation.generated_at}</p>
   {generation.source_cleaning?.applied&&<p className="rounded-lg border border-[#d7e5ec] bg-[#f7fbfd] px-3 py-2 text-xs text-[#4f7185]"><strong>{t('cleaned_source_used')}:</strong> {generation.source_cleaning.removed_chars} {t('boilerplate_removed')}</p>}
   {generation.generator==='openai-responses'
    ?<p className="rounded-lg border border-sky-200 bg-sky-50 px-3 py-2 text-xs text-[#315f76]"><strong>{t('production_ai_triage')}:</strong> {t('production_ai_note')}</p>
    :<p className="rounded-lg border border-amber-200 bg-amber-50 px-3 py-2 text-xs text-[#7b622c]"><strong>{generation.generator==='standalone-local-fallback'?t('production_ai_unavailable'):t('local_placeholder')}:</strong> {generation.generator==='standalone-local-fallback'?t('fallback_note'):t('local_placeholder_note')}</p>
   }
  </>}

  {presentation.invalid&&<p role="alert" className="text-sm text-red-700">{t('invalid_v3')}</p>}

  {!hasTriage?<>
   <p className="text-sm text-[#708295]">{t('no_ai_triage_saved')}</p>
   <button type="button" className="intel-ghost" disabled={busy||item.original_content?.trim().length<80} onClick={run}><Sparkles size={16}/>{busy?t('generating_suggestions'):t('generate_ai_triage')}</button>
  </>:<>
   <div className="grid gap-5">
    {suggestions._version>=2&&suggestions.source_facts&&<div className="rounded-lg border p-4 text-sm"><p className="intel-label">{t('triage_source_facts')}</p><p className="whitespace-pre-wrap break-words max-w-full overflow-hidden">{suggestions.source_facts}</p></div>}
    {!([2,3].includes(suggestions._version))&&<p className="text-xs text-[#a04724]">{t('legacy_prescreening_note')}</p>}
    {presentation.sections.map(section=>section.fields.some(k=>suggestions[k])&&<div key={section.title} className="space-y-3"><h3 className="text-sm font-bold text-[#29445d] border-b pb-2">{t(sectionKey[section.title]||section.title)}</h3>{section.fields.filter(k=>suggestions[k]).map(k=><PendingSuggestionRow key={k} name={k} value={suggestions[k]} confidence={suggestions.confidence} decision={decisions[k]} busy={busy} onDecide={decide}/>)}</div>)}
    {suggestions._version>=2&&<p className="text-xs text-[#617789]">{t('verification_unverified_note')}</p>}
    {!presentation.invalid&&suggestions.watchlist_match&&<WatchlistMatchRow match={suggestions.watchlist_match} decision={decisions.watchlist_match} items={watchlist} linkedId={item.watchlist_id} busy={busy} onDecide={decide}/>}
   </div>
   {!Object.keys(decisions).length&&<button type="button" className="intel-ghost" disabled={busy} onClick={run}>{t('regenerate_suggestions')}</button>}
  </>}
 </section>;
}
