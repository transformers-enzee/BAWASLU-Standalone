import {useEffect,useState} from 'react';
import {base44} from '@/api/base44Client';
import {useLanguage} from '@/lib/LanguageContext';

const CATEGORIES=[
  {key:'source',en:'Source data',id:'Data sumber'},
  {key:'assessment',en:'AI assessment',id:'Penilaian AI'},
  {key:'quality',en:'Data quality',id:'Kualitas data'},
  {key:'manual',en:'Missing-source intake',id:'Bukti yang tidak tersedia'},
];
const label=(s)=>String(s||'').replaceAll('_',' ').replace(/\b\w/g,c=>c.toUpperCase());
const safeUrl=(u)=>{try{const x=new URL(u);return ['https:','http:'].includes(x.protocol)?x.href:null}catch{return null}};
const inputClass='intel-input mt-1 w-full';
export default function Gate1FullWorkbench({campaignId,detail,onSaved}){
  const {language}=useLanguage();
  const T=(en,id)=>language==='id'?id:en;
  const [tab,setTab]=useState('source');
  const [view,setView]=useState(null);
  const [manualList,setManualList]=useState(null);
  const [selected,setSelected]=useState('');
  const [value,setValue]=useState('');
  const [mode,setMode]=useState('CORRECTED');
  const [verification,setVerification]=useState('UNVERIFIED');
  const [reference,setReference]=useState('');
  const [fieldReason,setFieldReason]=useState('');
  const [pending,setPending]=useState([]);
  const [reason,setReason]=useState('');
  const [busy,setBusy]=useState(false);
  const [error,setError]=useState('');
  const [message,setMessage]=useState('');
  const [secondaryReason,setSecondaryReason]=useState('');
  const [manual,setManual]=useState({platform:'youtube',title:'',text_content:'',source_url:'',author_name:'',observed_at:'',reason:'',evidence_url:''});
  useEffect(()=>{
    if(!detail?.result_id||String(campaignId)!=='9'){setView(null);return}
    let active=true;setError('');setPending([]);setSelected('');setMessage('');setView(null);
    base44.inboxHumanReview.fullReview(campaignId,detail.result_id).then(x=>{if(active)setView(x)})
      .catch(e=>{if(active)setError(e.message||'Unable to load full review')});
    return ()=>{active=false};
  },[campaignId,detail?.result_id,detail?.assessment_id,detail?.source_integrity_digest,detail?.information_review_revision]);
  useEffect(()=>{
    if(String(campaignId)!=='9'||tab!=='manual')return;
    let active=true;
    base44.inboxHumanReview.manualIntake(campaignId).then(x=>{if(active)setManualList(x)})
      .catch(e=>{if(active)setError(e.message||'Manual intake unavailable')});
    return ()=>{active=false};
  },[campaignId,tab]);
  const fields=view?.field_groups?.[tab]||[];
  const item=view?.fields?.[selected];
  function choose(field){setSelected(field);setValue('');setFieldReason('');setReference('');setMode('CORRECTED');setVerification('UNVERIFIED')}
  function add(){
    if(!selected||!fieldReason.trim()||fieldReason.trim().length<10){setError(T('Select a field and provide a reason of 10+ characters.','Pilih bidang dan tulis alasan minimal 10 karakter.'));return}
    if(mode!=='UNAVAILABLE'&&!value.trim()){setError(T('Enter the proposed corrected value.','Isi nilai koreksi.'));return}
    if(verification==='SOURCE_CONFIRMED'&&!safeUrl(reference)){setError(T('Source-confirmed edits need a valid supporting URL.','Koreksi terverifikasi memerlukan URL sumber yang valid.'));return}
    const patch={field:selected,value:value.trim(),mode,verification,evidence_url:reference.trim(),field_reason:fieldReason.trim()};
    setPending(old=>[...old.filter(x=>x.field!==selected),patch]);
    setError('');setSelected('');setValue('');setReference('');setFieldReason('');
  }
  async function save(){
    if(!view?.can_edit||!pending.length||reason.trim().length<10||busy)return;
    if(!window.confirm(T('Save these field changes to the QA audit ledger only? Original provider and AI records stay unchanged.','Simpan koreksi hanya ke audit QA? Data sumber dan AI asli tidak berubah.')))return;
    setBusy(true);setError('');setMessage('');
    try{
      await base44.inboxHumanReview.saveFullReview(campaignId,detail.result_id,{
        fields:pending,expected_revision:view.revision,expected_assessment_id:detail.assessment_id,
        expected_source_digest:detail.source_integrity_digest,reason:reason.trim()
      });
      const latest=await base44.inboxHumanReview.fullReview(campaignId,detail.result_id);
      setView(latest);setPending([]);setReason('');
      setMessage(T('Field changes saved. Any high-impact changes require independent review.','Koreksi tersimpan. Perubahan penting memerlukan pemeriksaan independen.'));
      onSaved?.();
    }catch(e){setError(e.message||'Unable to save field changes')}
    finally{setBusy(false)}
  }
  async function review(status){
    if(!view?.secondary_review_required||secondaryReason.trim().length<10||busy)return;
    setBusy(true);setError('');setMessage('');
    try{
      await base44.inboxHumanReview.secondFullReview(campaignId,detail.result_id,{
        status,expected_revision:view.revision,expected_assessment_id:detail.assessment_id,
        expected_source_digest:detail.source_integrity_digest,reason:secondaryReason.trim()
      });
      setView(await base44.inboxHumanReview.fullReview(campaignId,detail.result_id));
      setSecondaryReason('');
      setMessage(T('Independent review decision recorded.','Keputusan pemeriksa independen dicatat.'));
      onSaved?.();
    }catch(e){setError(e.message||'Independent review failed')}
    finally{setBusy(false)}
  }
  async function saveManual(){
    if(busy||!manual.title.trim()||manual.text_content.trim().length<10||manual.reason.trim().length<10)return;
    if(!window.confirm(T('Create an officer-supplied QA evidence proposal only? It will not be imported into Social Listening.','Buat usulan bukti QA dari petugas saja? Tidak diimpor ke Social Listening.')))return;
    setBusy(true);setError('');setMessage('');
    try{
      await base44.inboxHumanReview.addManualIntake(campaignId,manual);
      setManualList(await base44.inboxHumanReview.manualIntake(campaignId));
      setManual({platform:'youtube',title:'',text_content:'',source_url:'',author_name:'',observed_at:'',reason:'',evidence_url:''});
      setMessage(T('Manual evidence proposal saved as UNVERIFIED.','Usulan bukti manual disimpan sebagai BELUM TERVERIFIKASI.'));
    }catch(e){setError(e.message||'Unable to save manual proposal')}
    finally{setBusy(false)}
  }
  if(String(campaignId)!=='9'||!detail?.qa_audit_only)return null;
  return <section className="border-t pt-4 space-y-3" data-testid="gate1-full-field-workbench">
    <div className="flex flex-wrap items-start justify-between gap-2">
      <div><h4 className="font-semibold text-base">{T('Full data validation & enrichment','Validasi dan pelengkapan seluruh data')}</h4>
        <p className="text-xs text-slate-500">{T('Compare original values with officer proposals. Saved changes appear only in this campaign’s QA view.','Bandingkan nilai asli dan usulan petugas. Koreksi hanya muncul dalam tampilan QA kampanye ini.')}</p>
      </div>
      <span className="text-xs rounded-md border border-amber-200 bg-amber-50 p-2 text-amber-900">QA · Audit only</span>
    </div>
    <div role="tablist" className="flex flex-wrap gap-2" aria-label="Full review categories">
      {CATEGORIES.map(c=><button key={c.key} role="tab" aria-selected={tab===c.key} type="button" className={'intel-ghost text-xs '+(tab===c.key?'font-bold border-[#801b24]':'')} onClick={()=>{setTab(c.key);setSelected('');setError('')}}>{T(c.en,c.id)}</button>)}
    </div>
    {error&&<p className="rounded-md bg-red-50 p-2 text-xs text-red-800" role="alert">{error}</p>}
    {message&&<p className="rounded-md bg-green-50 p-2 text-xs text-green-800" role="status">{message}</p>}
    {tab!=='manual'&&<>
      {!view?<p role="status" className="text-sm">{T('Loading field-level QA…','Memuat QA tingkat bidang…')}</p>:<>
        <p className="text-xs text-slate-500">{T('Edit revision','Revisi koreksi')}: #{view.revision} · {T('Original source remains immutable','Sumber asli tetap dipertahankan')}. {view.stale?T('Snapshot changed — refresh required.','Snapshot berubah — perlu dimuat ulang.'):''}</p>
        <div className="max-h-56 overflow-y-auto rounded-lg border divide-y" data-testid="gate1-effective-field-list">
          {fields.map(field=><div key={field} className="p-2 text-xs space-y-1">
            <div className="flex items-center justify-between gap-2">
              <strong>{label(field)}</strong>
              <span className={view.fields?.[field]?.basis==='QA_OFFICER_ENRICHMENT'?'text-amber-800':'text-slate-500'}>{view.fields?.[field]?.basis||'ORIGINAL'}</span>
            </div>
            <p className="break-words text-slate-500">{T('Original','Asli')}: {String(view.fields?.[field]?.original||'—').slice(0,250)}</p>
            {view.fields?.[field]?.basis==='QA_OFFICER_ENRICHMENT'&&<p className="break-words text-slate-900">{T('Officer effective','Nilai petugas')}: {String(view.fields[field].effective||'UNAVAILABLE').slice(0,350)} · {view.fields[field].verification}</p>}
          </div>)}
        </div>
        {view.can_edit&&<div className="rounded-lg border p-3 space-y-2" data-testid="gate1-full-field-editor">
          <label className="block text-xs font-semibold">{T('Choose a field','Pilih bidang')}
            <select className={inputClass} value={selected} onChange={e=>choose(e.target.value)}>
              <option value="">{T('Select a field to correct or supplement','Pilih bidang untuk dikoreksi atau dilengkapi')}</option>
              {fields.map(field=><option key={field} value={field}>{label(field)}</option>)}
            </select>
          </label>
          {selected&&<>
            <p className="text-xs text-slate-500">{T('Current effective value','Nilai efektif saat ini')}: {String(item?.effective||'—').slice(0,500)}</p>
            <label className="block text-xs font-semibold">{T('Corrected / supplemented value','Nilai koreksi / pelengkap')}
              <textarea className={inputClass} rows={selected==='text_content'||selected==='transcript'?4:2} value={value} onChange={e=>setValue(e.target.value)} placeholder={T('Enter what the officer verified or found missing','Isi temuan atau pelengkapan petugas')} disabled={mode==='UNAVAILABLE'}/>
            </label>
            <div className="grid grid-cols-1 sm:grid-cols-2 gap-2">
              <label className="text-xs font-semibold">{T('Change type','Jenis perubahan')}
                <select className={inputClass} value={mode} onChange={e=>setMode(e.target.value)}>
                  {['CORRECTED','SUPPLEMENTED','MISSING_PROVIDER','UNAVAILABLE'].map(x=><option key={x} value={x}>{label(x)}</option>)}
                </select>
              </label>
              <label className="text-xs font-semibold">{T('Verification level','Tingkat verifikasi')}
                <select className={inputClass} value={verification} onChange={e=>setVerification(e.target.value)}>
                  {['UNVERIFIED','OFFICER_SUPPLIED','SOURCE_CONFIRMED'].map(x=><option key={x} value={x}>{label(x)}</option>)}
                </select>
              </label>
            </div>
            <label className="block text-xs font-semibold">{T('Supporting source URL','URL sumber pendukung')}
              <input className={inputClass} value={reference} onChange={e=>setReference(e.target.value)} placeholder="https://..." type="url"/>
            </label>
            <label className="block text-xs font-semibold">{T('Reason for this field','Alasan untuk bidang ini')}
              <textarea className={inputClass} rows={2} value={fieldReason} onChange={e=>setFieldReason(e.target.value)} placeholder={T('Explain the mismatch or missing information (10+ characters)','Jelaskan ketidaksesuaian atau data yang hilang (10+ karakter)')}/>
            </label>
            <button type="button" className="intel-ghost text-xs" onClick={add} disabled={fieldReason.trim().length<10}>{T('Add to review batch','Tambahkan ke paket tinjauan')}</button>
          </>}
        </div>}
        {pending.length>0&&<div className="rounded-lg bg-slate-50 border p-3 space-y-2" data-testid="gate1-pending-fields">
          <strong className="text-sm">{T('Pending corrections','Koreksi yang akan disimpan')} ({pending.length})</strong>
          {pending.map(p=><div key={p.field} className="flex justify-between items-start gap-2 text-xs">
            <p>{label(p.field)}: {p.mode==='UNAVAILABLE'?'UNAVAILABLE':p.value.slice(0,90)} · {p.verification}</p>
            <button type="button" onClick={()=>setPending(old=>old.filter(x=>x.field!==p.field))} className="underline text-red-800">{T('Remove','Hapus')}</button>
          </div>)}
          <textarea className={inputClass} rows={2} value={reason} onChange={e=>setReason(e.target.value)} placeholder={T('Overall review explanation (10+ characters)','Penjelasan keseluruhan (10+ karakter)')}/>
          <button className="intel-ghost text-xs" type="button" disabled={busy||reason.trim().length<10||view.stale} onClick={save}>{T('Save all as audited QA corrections','Simpan semua koreksi QA dengan audit')}</button>
        </div>}
        {view.history?.length>0&&<div className="space-y-2" data-testid="gate1-full-audit-history">
          <h5 className="font-semibold text-sm">{T('Field-level revision history','Riwayat revisi bidang')}</h5>
          {view.history.slice(0,12).map(h=><div key={h.revision} className="rounded-md border p-2 text-xs space-y-1">
            <strong>#{h.revision}</strong> · {T('Officer','Petugas')} {h.actor_id} · {h.at} {h.stale?'· STALE':''}
            <p>{h.fields?.map(f=>label(f.field)).join(', ')} · {h.reason}</p>
          </div>)}
        </div>}
        {view.secondary_review_required&&<div className="rounded-lg border border-amber-200 bg-amber-50 p-3 space-y-2" data-testid="gate1-secondary-review">
          <h5 className="font-semibold text-sm">{T('Independent review required','Memerlukan tinjauan independen')}</h5>
          <p className="text-xs">{T('Sensitive identity, geography or potential-violation changes require approval by another authorized administrator.','Perubahan identitas, geografi, atau dugaan pelanggaran memerlukan persetujuan administrator lain.')}</p>
          <p className="text-xs">{T('Current decision','Keputusan saat ini')}: <strong>{view.secondary_review?.status}</strong> {view.secondary_review?.reviewer_id?'· '+view.secondary_review.reviewer_id:''}</p>
          {view.can_edit&&<><textarea className={inputClass} rows={2} value={secondaryReason} onChange={e=>setSecondaryReason(e.target.value)} placeholder={T('Independent reviewer reason (10+ characters)','Alasan pemeriksa independen (10+ karakter)')}/>
            <div className="flex flex-wrap gap-2">
              <button type="button" className="intel-ghost text-xs" onClick={()=>review('APPROVED')} disabled={busy||secondaryReason.trim().length<10}>{T('Approve as second reviewer','Setujui sebagai pemeriksa kedua')}</button>
              <button type="button" className="intel-ghost text-xs" onClick={()=>review('REJECTED')} disabled={busy||secondaryReason.trim().length<10}>{T('Reject change batch','Tolak paket koreksi')}</button>
            </div></>}
        </div>}
      </>}
    </>}
    {tab==='manual'&&<div className="space-y-3" data-testid="gate1-manual-intake">
      <p className="rounded-md bg-amber-50 border border-amber-200 p-3 text-xs text-amber-900">{T('When the provider API misses a post, register an officer-supplied UNVERIFIED proposal. This is not automatically added to Social Listening or used for published intelligence.','Jika API penyedia tidak menemukan unggahan, catat usulan bukti BELUM TERVERIFIKASI dari petugas. Tidak otomatis masuk Social Listening atau intelijen terbit.')}</p>
      {detail.can_review_information&&<div className="space-y-2">
        {['platform','title','text_content','source_url','author_name','observed_at','evidence_url','reason'].map(key=><label key={key} className="block text-xs font-semibold">{label(key)}
          {['text_content','reason'].includes(key)?<textarea className={inputClass} rows={2} value={manual[key]} onChange={e=>setManual(x=>({...x,[key]:e.target.value}))}/>:<input className={inputClass} value={manual[key]} onChange={e=>setManual(x=>({...x,[key]:e.target.value}))} placeholder={key.includes('url')?'https://...':''}/>}
        </label>)}
        <button type="button" className="intel-ghost text-xs" onClick={saveManual} disabled={busy||manual.reason.trim().length<10||manual.text_content.trim().length<10||!manual.title.trim()}>{T('Record unverified manual evidence proposal','Catat usulan bukti manual belum terverifikasi')}</button>
      </div>}
      <div className="space-y-2"><h5 className="font-semibold text-sm">{T('Manual proposals (not official evidence)','Usulan manual (bukan bukti resmi)')}</h5>
        {(manualList?.items||[]).map(x=><div key={x.id} className="rounded-md border p-2 text-xs space-y-1">
          <strong>#{x.id} · {x.title}</strong> · QA_UNVERIFIED
          <p>{x.platform} · {x.officer_id} · {x.created_at}</p>
          <p>{x.text_content?.slice(0,200)}</p>
          {safeUrl(x.source_url)&&<a href={safeUrl(x.source_url)} target="_blank" rel="noopener noreferrer" className="underline">{T('Open supplied source','Buka sumber tambahan')}</a>}
        </div>)}
        {manualList?.items?.length===0&&<p className="text-xs text-slate-500">{T('No manual proposals yet.','Belum ada usulan manual.')}</p>}
      </div>
    </div>}
  </section>;
}
