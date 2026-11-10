import {useState} from 'react';
import {Pencil,CheckCircle2} from 'lucide-react';
/** One auditable correction component shared by Social Listening and Inbox. */
export default function SentimentCorrection({campaignId,resultId,value,canEdit=true,onSaved,language='id'}){
 const [editing,setEditing]=useState(false);
 const [label,setLabel]=useState(String(value||'NEUTRAL').toUpperCase());
 const [reason,setReason]=useState('');
 const [busy,setBusy]=useState(false);
 const [error,setError]=useState('');
 const [notice,setNotice]=useState('');
 const id=language==='id';
 if(!canEdit||!campaignId||!resultId)return null;
 async function save(){
  if(busy||reason.trim().length<10)return;
  setBusy(true);setError('');setNotice('');
  try{
   const token=window.localStorage.getItem('bawaslu_access_token')||'';
   const response=await fetch('/api/officer-sentiment/correct',{
    method:'POST',cache:'no-store',
    headers:{Authorization:'Bearer '+token,'Content-Type':'application/json'},
    body:JSON.stringify({campaign_id:Number(campaignId),result_id:Number(resultId),
      sentiment:label,rationale:reason.trim()})
   });
   const data=await response.json().catch(()=>({}));
   if(!response.ok)throw Error(data.detail||'Unable to save correction');
   const correction=data.correction;
   onSaved?.(correction);
   setEditing(false);setReason('');
   setNotice(id?'Koreksi sentimen tersimpan dan tercatat.':'Sentiment correction saved and audited.');
  }catch(e){setError(e.message||'Correction failed')}finally{setBusy(false)}
 }
 return <div className="mt-2" aria-label="Manual sentiment correction">
  {!editing&&<button type="button" onClick={()=>{setEditing(true);setLabel(['POSITIVE','NEGATIVE','NEUTRAL'].includes(String(value).toUpperCase())?String(value).toUpperCase():'NEUTRAL');setError('');setNotice('')}} className="inline-flex items-center gap-1 rounded-md border border-[#d6e0e7] px-2 py-1.5 text-xs text-[#801b24] hover:bg-[#fdf2f3]"><Pencil size={12}/>{id?'Ubah sentimen manual':'Correct sentiment'}</button>}
  {editing&&<div className="mt-1 space-y-2 rounded-lg border border-[#dfccd0] bg-white p-3 text-xs">
    <p className="font-semibold text-[#801b24]">{id?'Koreksi oleh petugas':'Officer correction'}</p>
    <label className="block space-y-1">{id?'Sentimen yang benar':'Correct sentiment'}
     <select className="intel-input block mt-1 w-full" value={label} onChange={e=>setLabel(e.target.value)}>
      <option value="POSITIVE">{id?'Positif':'Positive'}</option>
      <option value="NEUTRAL">{id?'Netral':'Neutral'}</option>
      <option value="NEGATIVE">{id?'Negatif':'Negative'}</option>
     </select>
    </label>
    <label className="block space-y-1">{id?'Alasan perubahan (wajib)':'Reason for change (required)'}
     <textarea className="intel-input block w-full mt-1" rows={2} maxLength={1000}
      value={reason} onChange={e=>setReason(e.target.value)}
      placeholder={id?'Jelaskan bukti atau konteks sumber…':'Explain the source evidence or context…'}/>
    </label>
    <p className="text-[#64748b]">{id?'Label AI asli tetap tersimpan; koreksi diperlihatkan di kedua modul.':'Original AI label is preserved; the correction appears in both modules.'}</p>
    <div className="flex gap-2">
     <button type="button" className="intel-button text-xs" disabled={busy||reason.trim().length<10} onClick={save}><CheckCircle2 size={13} className="inline mr-1"/>{busy?'…':id?'Simpan koreksi':'Save correction'}</button>
     <button type="button" className="intel-ghost text-xs" onClick={()=>setEditing(false)} disabled={busy}>{id?'Batal':'Cancel'}</button>
    </div>
   </div>}
  {error&&<p className="text-xs text-red-700 mt-1" role="alert">{error}</p>}
  {notice&&<p className="text-xs text-green-700 mt-1" role="status">{notice}</p>}
 </div>;
}
