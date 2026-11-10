import {useState} from 'react';
import {Pencil,CheckCircle2} from 'lucide-react';
import {useLanguage} from '@/lib/LanguageContext';

/** Shared audited sentiment override. Language always follows the UI setting. */
export default function SentimentCorrection({campaignId,resultId,value,canEdit=true,onSaved}){
 const {language}=useLanguage();
 const isEnglish=language==='en';
 const [editing,setEditing]=useState(false);
 const [label,setLabel]=useState(String(value||'NEUTRAL').toUpperCase());
 const [busy,setBusy]=useState(false);
 const [error,setError]=useState('');
 const [notice,setNotice]=useState('');
 if(!canEdit||!campaignId||!resultId)return null;
 async function save(){
  if(busy)return;
  setBusy(true);setError('');setNotice('');
  try{
   const token=window.localStorage.getItem('bawaslu_access_token')||'';
   const response=await fetch('/api/officer-sentiment/correct',{
    method:'POST',cache:'no-store',
    headers:{Authorization:'Bearer '+token,'Content-Type':'application/json'},
    body:JSON.stringify({campaign_id:Number(campaignId),result_id:Number(resultId),sentiment:label})
   });
   const data=await response.json().catch(()=>({}));
   if(!response.ok)throw Error(data.detail||(
     isEnglish?'Unable to save sentiment correction.':'Tidak dapat menyimpan koreksi sentimen.'));
   const correction=data.correction;
   onSaved?.(correction);
   setEditing(false);
   setNotice(isEnglish?'Sentiment updated.':'Sentimen diperbarui.');
  }catch(e){setError(e.message||(
    isEnglish?'Could not update sentiment.':'Gagal memperbarui sentimen.'))}
  finally{setBusy(false)}
 }
 return <div className="mt-2" data-i18n-exempt lang={isEnglish?'en':'id'} aria-label={isEnglish?'Manual sentiment correction':'Koreksi sentimen manual'}>
  {!editing&&<button type="button" onClick={()=>{
     setEditing(true);
     setLabel(['POSITIVE','NEGATIVE','NEUTRAL'].includes(String(value).toUpperCase())?
       String(value).toUpperCase():'NEUTRAL');
     setError('');setNotice('');
    }} className="inline-flex items-center gap-1 rounded-md border border-[#d6e0e7] px-2 py-1.5 text-xs text-[#801b24] hover:bg-[#fdf2f3]">
    <Pencil size={12}/>{isEnglish?'Change sentiment':'Ubah sentimen'}
   </button>}
  {editing&&<div className="mt-1 space-y-2 rounded-lg border border-[#dfccd0] bg-white p-3 text-xs">
    <p className="font-semibold text-[#801b24]">{isEnglish?'Change sentiment':'Ubah sentimen'}</p>
    <label className="block space-y-1">{isEnglish?'Correct sentiment':'Sentimen yang benar'}
     <select className="intel-input block mt-1 w-full" value={label} onChange={e=>setLabel(e.target.value)}>
      <option value="POSITIVE">{isEnglish?'Positive':'Positif'}</option>
      <option value="NEUTRAL">{isEnglish?'Neutral':'Netral'}</option>
      <option value="NEGATIVE">{isEnglish?'Negative':'Negatif'}</option>
     </select>
    </label>
    <div className="flex gap-2">
     <button type="button" className="intel-button text-xs" disabled={busy} onClick={save}>
      <CheckCircle2 size={13} className="inline mr-1"/>{busy?'…':isEnglish?'Save':'Simpan'}
     </button>
     <button type="button" className="intel-ghost text-xs" onClick={()=>setEditing(false)} disabled={busy}>
      {isEnglish?'Cancel':'Batal'}
     </button>
    </div>
   </div>}
  {error&&<p className="text-xs text-red-700 mt-1" role="alert">{error}</p>}
  {notice&&<p className="text-xs text-green-700 mt-1" role="status">{notice}</p>}
 </div>;
}
