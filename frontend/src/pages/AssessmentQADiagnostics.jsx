import {useEffect,useState} from 'react';
import {Link} from 'react-router-dom';
import {AlertTriangle,CheckCircle2,ClipboardCheck,FlaskConical,RefreshCw} from 'lucide-react';

const API='/api/intelligence-assessment-qa';
const auth=()=>({Authorization:'Bearer '+(window.localStorage.getItem('bawaslu_access_token')||'')});
async function call(path,body){
  const response=await fetch(API+path,{
    method:body?'POST':'GET',cache:'no-store',
    headers:{...auth(),...(body?{'Content-Type':'application/json'}:{})},
    ...(body?{body:JSON.stringify(body)}:{})
  });
  const data=await response.json().catch(()=>({}));
  if(!response.ok)throw new Error(typeof data.detail==='string'?data.detail:'Assessment QA request failed');
  return data;
}
const cls='rounded-xl border border-slate-200 bg-white p-4 sm:p-5';
const btn='rounded-lg border border-slate-300 bg-white px-3 py-2 text-sm font-medium hover:bg-slate-50 focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-slate-700 disabled:opacity-50';
const fmt=value=>value===undefined||value===null?'—':typeof value==='string'?value:JSON.stringify(value);

export default function AssessmentQAWorkbench(){
  const [catalog,setCatalog]=useState(null),[selected,setSelected]=useState(''),[raw,setRaw]=useState(''),
    [result,setResult]=useState(null),[error,setError]=useState(''),[busy,setBusy]=useState(false);
  const active=catalog?.cases.find(c=>c.id===selected);

  async function refresh(){
    setBusy(true);setError('');
    try{
      const data=await call('/catalog');
      setCatalog(data);
      const scenario=data.cases.find(x=>x.id===selected)||data.cases[0];
      if(scenario){setSelected(scenario.id);setRaw(JSON.stringify(scenario.sample_predictions,null,2))}
      setResult(null);
    }catch(e){setError(e.message);setCatalog(null)}
    finally{setBusy(false)}
  }
  useEffect(()=>{refresh()},[]);
  function choose(scenario){
    setSelected(scenario.id);setRaw(JSON.stringify(scenario.sample_predictions,null,2));
    setResult(null);setError('');
  }
  async function compare(){
    setError('');setResult(null);
    let predictions;
    try{
      predictions=JSON.parse(raw);
      if(!predictions||typeof predictions!=='object'||Array.isArray(predictions))
        throw new Error('Enter a JSON object of field names and predicted values.');
    }catch(e){setError('Invalid prediction JSON: '+e.message);return}
    setBusy(true);
    try{setResult(await call('/evaluate',{case_id:selected,predictions}))}
    catch(e){setError(e.message)}
    finally{setBusy(false)}
  }

  return <main data-testid="intelligence-assessment-qa-workbench" data-i18n-exempt="true" className="mx-auto max-w-7xl space-y-5 pb-8">
    <header className="space-y-2">
      <Link to="/administration/assessment-qa" className="text-sm text-slate-600 underline underline-offset-4">Back to Administration</Link>
      <div className="flex flex-wrap items-start gap-3 justify-between">
        <div>
          <p className="flex items-center gap-2 text-xs font-bold uppercase tracking-widest text-[#8b2430]"><FlaskConical size={16}/> SmartRadar · QA</p>
          <h1 className="mt-1 text-2xl font-bold text-slate-900">Advanced Assessment Diagnostics</h1>
          <p className="mt-1 text-sm text-slate-600">Raw → Information → Insights · v183.6</p>
        </div>
        <button type="button" className={btn+' flex items-center gap-2'} onClick={refresh} disabled={busy}><RefreshCw size={16}/> Refresh fixtures</button>
      </div>
    </header>

    <section className="rounded-xl border border-amber-300 bg-amber-50 p-4 text-sm text-amber-950" data-testid="assessment-qa-synthetic-warning">
      <div className="font-semibold flex items-center gap-2"><AlertTriangle size={18}/> Developer diagnostics · synthetic and offline</div>
      <p className="mt-1">These eight examples and their reference labels are illustrative, not officer-validated gold data. The sample predictions are deliberately simulated; this page does not invoke an AI model, charge OpenAI credits, read officer evidence, save corrections or train anything. Paste actual model predictions manually if you want to score them against these examples.</p>
    </section>
    {error&&<p role="alert" className="rounded-lg border border-red-300 bg-red-50 p-3 text-sm text-red-800" data-testid="assessment-qa-error">{error}</p>}
    {!catalog&&!error&&<p role="status" className="text-sm text-slate-600">Loading assessment QA catalog…</p>}
    {!catalog&&error&&<div className={cls}>
      <p className="text-sm text-slate-700">Access requires an active Nationwide National Administrator. On staging, enable <code className="bg-slate-100 px-1 rounded">BAWASLU_ASSESSMENT_QA_ENABLED=1</code> in Render; keep it disabled in production.</p>
    </div>}
    {catalog&&<>
      <div className="grid gap-3 sm:grid-cols-3">
        {[
          [Object.keys(catalog.field_groups).length,'Assessment groups'],
          [catalog.insight_variables.length,'Command Centre variables'],
          [catalog.cases.length,'Synthetic QA scenarios'],
        ].map(([value,label])=><div key={label} className={cls}><p className="text-2xl font-bold text-slate-900">{value}</p><p className="text-xs text-slate-600">{label}</p></div>)}
      </div>
      <div className="grid gap-4 lg:grid-cols-[260px_1fr]">
        <aside className={cls+' self-start'} aria-label="Synthetic assessment scenarios">
          <h2 className="font-semibold text-slate-900">Test scenarios</h2>
          <p className="text-xs text-slate-500 mt-1 mb-3">Select a risk to inspect the expected assessment.</p>
          <div className="space-y-2">
            {catalog.cases.map((item,i)=><button key={item.id} type="button"
              data-testid={'assessment-case-'+item.id}
              aria-current={item.id===selected?'true':undefined}
              onClick={()=>choose(item)}
              className={'block w-full rounded-lg border px-3 py-3 text-left text-sm '+(item.id===selected?'border-[#8b2430] bg-[#fff5f3] font-semibold text-[#7e1d26]':'border-slate-200 text-slate-800 hover:bg-slate-50')}>
                <span className="text-xs text-slate-500">{String(i+1).padStart(2,'0')} · {item.focus}</span>
                <span className="block mt-1">{item.title}</span>
            </button>)}
          </div>
        </aside>
        <div className="space-y-4">
          {active&&<>
            <section className={cls} data-testid="assessment-source-card">
              <p className="text-xs uppercase tracking-wide font-semibold text-slate-500">Synthetic source · {active.source_id}</p>
              <h2 className="font-semibold mt-2">{active.title}</h2>
              <p className="mt-2 rounded-lg bg-slate-50 px-4 py-3 text-sm text-slate-800 leading-relaxed">{active.source_text}</p>
              <p className="mt-3 text-xs text-amber-900"><strong>Reviewer rationale:</strong> {active.review_note}</p>
            </section>
            <section className={cls+' space-y-3'}>
              <div>
                <h2 className="font-semibold">Compare field-level predictions</h2>
                <p className="text-xs text-slate-600 mt-1">Edit or paste a JSON object keyed by contract field. No predictions are sent to a model or saved to the database.</p>
              </div>
              <label className="block text-sm font-semibold text-slate-800" htmlFor="assessment-predictions-json">Prediction JSON (synthetic example loaded)</label>
              <textarea id="assessment-predictions-json" data-testid="assessment-predictions-json"
                value={raw} onChange={e=>{setRaw(e.target.value);setResult(null)}}
                rows={10} spellCheck={false}
                className="w-full rounded-lg border border-slate-300 bg-slate-50 p-3 font-mono text-xs text-slate-900 focus-visible:outline focus-visible:outline-2 focus-visible:outline-slate-700"/>
              <div className="flex flex-wrap items-center gap-2">
                <button type="button" data-testid="assessment-compare" className="rounded-lg bg-[#8b2430] px-4 py-2 text-sm font-semibold text-white hover:bg-[#6b1a25] disabled:opacity-50" onClick={compare} disabled={busy}>{busy?'Evaluating…':'Compare predictions (free)'}</button>
                <button type="button" className={btn} onClick={()=>{setRaw(JSON.stringify(active.sample_predictions,null,2));setResult(null)}}>Load planted-error example</button>
                <button type="button" className={btn} onClick={()=>{setRaw(JSON.stringify(active.expected,null,2));setResult(null)}}>Load passing reference</button>
              </div>
            </section>
            {result&&<section className={cls+' space-y-3'} data-testid="assessment-qa-results" aria-live="polite">
              <div className="flex items-center gap-2 flex-wrap justify-between">
                <h2 className="font-semibold flex items-center gap-2"><ClipboardCheck size={18}/> Field comparison</h2>
                <span className="text-sm text-slate-700">{result.matched_fields}/{result.compared_fields} matched · {Math.round(result.coverage*100)}% coverage</span>
              </div>
              <p className="text-xs text-slate-500">Agreement is a comparison with illustrative reference fields, not a validated AI accuracy measure.</p>
              <div className="overflow-auto rounded-lg border border-slate-200">
                <table className="w-full text-left text-sm">
                  <thead className="bg-slate-50"><tr>{['Variable','Expected','Submitted','Result'].map(x=><th key={x} className="p-3 font-semibold whitespace-nowrap">{x}</th>)}</tr></thead>
                  <tbody>{result.details.map(x=><tr key={x.field} className="border-t border-slate-100">
                    <td className="p-3"><div className="font-medium">{x.field}</div><div className="text-[11px] text-slate-500">{x.group}</div></td>
                    <td className="p-3 font-mono text-xs">{fmt(x.expected)}</td>
                    <td className="p-3 font-mono text-xs">{fmt(x.actual)}</td>
                    <td className="p-3"><span className={'text-xs font-semibold '+(x.status==='MATCH'?'text-green-700':x.status==='MISSING'?'text-slate-600':'text-red-700')}>{x.status==='MATCH'&&<CheckCircle2 size={14} className="inline mr-1"/>}{x.status}</span></td>
                  </tr>)}</tbody>
                </table>
              </div>
              {result.extra_fields_not_scored.length>0&&<p className="text-xs text-amber-800">Additional valid fields not scored in this scenario: {result.extra_fields_not_scored.join(', ')}</p>}
              {result.override_preview&&<div className="rounded-lg border border-slate-200 bg-slate-50 p-3 space-y-1" data-testid="assessment-override-preview">
                <h3 className="font-semibold text-sm">Human override precedence — in-memory preview</h3>
                <p className="text-sm">Original AI: <b>{result.override_preview.ai_value}</b></p>
                <p className="text-sm">Proposed / unapproved → effective: <b>{result.override_preview.unapproved_effective_value}</b></p>
                <p className="text-sm">Approved → effective: <b>{result.override_preview.approved_effective_value}</b></p>
                <p className="text-xs text-slate-600">This is a demonstration only; no officer correction has been stored or applied to Command Centre.</p>
              </div>}
            </section>}
            <section className={cls}>
              <h2 className="font-semibold mb-2">Expected fields for this case</h2>
              <div className="grid gap-2 sm:grid-cols-2">{Object.entries(active.expected).map(([name,value])=><div key={name} className="rounded-lg border border-slate-100 p-2"><p className="text-xs text-slate-500">{name}</p><p className="font-mono text-sm break-all">{fmt(value)}</p></div>)}</div>
            </section>
          </>}
        </div>
      </div>
      <div className="grid gap-4 lg:grid-cols-2">
        <details className={cls}><summary className="cursor-pointer font-semibold">All 10 assessment groups · data dictionary</summary>
          <div className="space-y-3 mt-3">{Object.entries(catalog.field_groups).map(([group,fields])=><div key={group}><h3 className="text-sm font-medium">{group.replaceAll('_',' ')}</h3><p className="mt-1 text-xs text-slate-600 break-words">{fields.join(' · ')}</p></div>)}</div>
        </details>
        <details className={cls}><summary className="cursor-pointer font-semibold">15 Command Centre synthesis variables</summary>
          <p className="text-xs text-slate-600 mt-2">These variables are defined in the contract but not automatically generated by this simulator.</p>
          <ol className="list-decimal pl-5 mt-2 text-sm text-slate-700 space-y-1">{catalog.insight_variables.map(x=><li key={x}>{x.replaceAll('_',' ')}</li>)}</ol>
        </details>
      </div>
    </>}
  </main>;
}
