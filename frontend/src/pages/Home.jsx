import { Link } from 'react-router-dom';
import { useEffect, useMemo, useState } from 'react';
import { ArrowUpRight, AlertTriangle, MapPin, ShieldAlert, Eye, Inbox, RefreshCw } from 'lucide-react';
import { useIntel, useRegistry } from '@/components/intel/useIntel';
import { base44 } from '@/api/base44Client';
import { Notice } from '@/components/intel/Fields';
import { useLanguage } from '@/lib/LanguageContext';

const pending=x=>['Pending Review','Awaiting Validation'].includes(x.review_status);
const verified=x=>x.review_status==='Validated as Relevant Intelligence';
const stamp=x=>new Date(x.publication_datetime||x.collection_datetime||x.updated_date||x.created_date||0).getTime()||0;
const place=x=>x.jurisdiction_confirmed===true?([x.regency_city,x.province].filter(Boolean).join(', ')||'National'):'Lokasi belum dikonfirmasi';
const signal=x=>{
  const approved=x.human_approved_triage?.values?.supervision_signal;
  const human=String(approved||x.supervision_screening?.supervision_signal||'').toUpperCase();
  if(human==='POTENTIAL REGULATORY ISSUE')return {kind:'reviewed',label:'Sinyal ditinjau petugas'};
  const proposed=String(x.ai_suggestions?.supervision_signal||'').toUpperCase();
  const decision=x.ai_suggestions?._decisions?.supervision_signal?.status;
  if(decision==='Human Rejected')return null;
  if(!approved&&['POTENTIAL REGULATORY ISSUE','REVIEW RECOMMENDED'].includes(proposed))return {kind:'ai',label:'Saran AI • belum diverifikasi'};
  return null;
};
const high=x=>x.priority==='Critical'||x.priority==='High';
const ago=x=>{if(!x)return '—';const d=new Date(x);return Number.isNaN(d.getTime())?'—':d.toLocaleDateString('id-ID',{day:'numeric',month:'short',year:'numeric'})};
function Section({title,subtitle,to,children}){return <section className="intel-card p-4 sm:p-5 min-w-0"><div className="flex items-start justify-between gap-3 mb-4"><div className="min-w-0"><h2 className="text-base font-semibold text-[#173851]">{title}</h2>{subtitle&&<p className="text-xs text-[#70869a] mt-1">{subtitle}</p>}</div>{to&&<Link to={to} className="shrink-0 text-xs font-semibold text-[#176e8e] hover:underline flex items-center gap-1">Lihat semua <ArrowUpRight size={13}/></Link>}</div>{children}</section>}
function Empty({children}){return <div className="rounded-lg border border-dashed border-[#dce6ec] px-4 py-7 text-center text-sm text-[#70869a]">{children}</div>}
function Record({item,detail}){return <Link to={'/intelligence/'+item.id} className="flex items-start justify-between gap-3 py-3 border-b border-[#edf2f5] last:border-0 hover:bg-[#fafcfd]"><div className="min-w-0"><p className="text-sm font-semibold text-[#1f3c50] line-clamp-2">{item.title||'Intelijen tanpa judul'}</p><p className="text-xs text-[#77899a] mt-1">{place(item)} · {ago(item.publication_datetime||item.updated_date||item.created_date)}</p>{detail&&<p className="text-xs text-[#97642b] mt-1">{detail}</p>}</div><ArrowUpRight size={15} className="shrink-0 mt-1 text-[#176e8e]"/></Link>}

export default function Home(){
 const {t}=useLanguage();
 const {items,loading,error,refresh}=useIntel();const watchState=useRegistry();
 const [province,setProvince]=useState(''),[regency,setRegency]=useState('');
 const [social,setSocial]=useState(null),[socialError,setSocialError]=useState(''),[socialLoading,setSocialLoading]=useState(true);
 const [lastUpdated,setLastUpdated]=useState('');
 const loadSocial=()=>{setSocialLoading(true);setSocialError('');return base44.functions.invoke('socialListening',{action:'queue',data:{state:''}}).then(r=>{setSocial(r.data||{});setLastUpdated(new Date().toISOString())}).catch(()=>{setSocial(null);setSocialError('Antrean Social Listening tidak tersedia')}).finally(()=>setSocialLoading(false))};
 useEffect(()=>{loadSocial()},[]);
 const provinces=useMemo(()=>[...new Set(items.filter(x=>x.jurisdiction_confirmed===true&&x.province).map(x=>x.province))].sort(),[items]);
 const regencies=useMemo(()=>[...new Set(items.filter(x=>x.jurisdiction_confirmed===true&&x.province===province&&x.regency_city).map(x=>x.regency_city))].sort(),[items,province]);
 const scoped=useMemo(()=>items.filter(x=>!province||(x.jurisdiction_confirmed===true&&x.province===province&&(!regency||x.regency_city===regency))),[items,province,regency]);
 const scopeActive=!!province;
 const viol=useMemo(()=>scoped.filter(x=>signal(x)).sort((a,b)=>Number(high(b))-Number(high(a))||stamp(b)-stamp(a)),[scoped]);
 const tasks=useMemo(()=>scoped.filter(x=>pending(x)||x.jurisdiction_confirmed!==true||x.geographic_mismatch_review?.status==='pending').sort((a,b)=>Number(high(b))-Number(high(a))||stamp(b)-stamp(a)),[scoped]);
 const latest=useMemo(()=>[...scoped].sort((a,b)=>stamp(b)-stamp(a)).slice(0,4),[scoped]);
 const topics=useMemo(()=>{const m=new Map();for(const x of scoped){for(const v of (Array.isArray(x.related_topics)?x.related_topics:[])){const name=String(typeof v==='string'?v:v?.name||v?.label||'').trim();if(name)m.set(name,(m.get(name)||0)+1)}}return [...m].sort((a,b)=>b[1]-a[1]).slice(0,5)},[scoped]);
 const regions=useMemo(()=>{const rows=new Map();for(const x of scoped){if(x.jurisdiction_confirmed!==true)continue;const assigned=x.jurisdiction_type==='Multi-Region'&&Array.isArray(x.geographic_assignments)?x.geographic_assignments:[x];const unique=new Set();for(const area of assigned){const p=String(area.province||'').trim(),r=String(area.regency_city||'').trim();if(!p||province&&p!==province||regency&&r!==regency)continue;const name=regency?r+', '+p:province?(r||p):p;const key=(regency||province?'detail:':'province:')+name;if(unique.has(key))continue;unique.add(key);const row=rows.get(key)||{name,records:0,signals:0,attention:0};row.records++;if(signal(x))row.signals++;if(pending(x))row.attention++;rows.set(key,row)}}return [...rows.values()].sort((a,b)=>b.signals-a.signals||b.attention-a.attention||b.records-a.records||a.name.localeCompare(b.name)).slice(0,8)},[scoped,province,regency]);
 const unmapped=useMemo(()=>scoped.filter(x=>x.jurisdiction_confirmed!==true||(!x.province&&x.jurisdiction_type!=='Multi-Region'&&x.jurisdiction_type!=='National')).length,[scoped]);
 const watch=watchState.items||[];
 const relevantWatch=watch.filter(x=>!province||(x.province===province&&(!regency||x.regency_city===regency)));
 const socialCounts=social?.counts||{};
 const socialItems=(social?.results||[]).filter(x=>['DISCOVERED','RELEVANT','MONITOR'].includes(x.review_state)).slice(0,3);
 const refreshAll=()=>{refresh();watchState.refresh();loadSocial()};
 return <div className="mx-auto max-w-[1360px] space-y-5 pb-8">
  <header className="flex flex-col lg:flex-row lg:items-end justify-between gap-4"><div className="min-w-0"><p className="text-[11px] uppercase tracking-[.18em] font-bold text-[#9a7e49]">BAWASLU · INTELLIGENCE COMMAND CENTER</p><h1 className="intel-heading mt-2">Situasi Pengawasan Pemilu</h1><p className="text-sm text-[#70869a] mt-1 max-w-2xl">Lihat perkembangan wilayah, sinyal yang perlu ditinjau, dan langkah pengawasan berikutnya — dalam satu tampilan.</p></div><button type="button" onClick={refreshAll} className="inline-flex self-start items-center gap-2 rounded-lg border border-[#cfdee6] bg-white px-3 py-2 text-xs font-semibold text-[#176e8e] hover:bg-[#f5fafc]"><RefreshCw size={14}/> Perbarui data</button></header>
  <div className="intel-card p-3 sm:p-4 flex flex-wrap items-center gap-3"><MapPin size={17} className="text-[#176e8e]"/><span className="text-xs font-semibold text-[#52697d]">Cakupan wilayah</span><select aria-label="Pilih provinsi" value={province} onChange={e=>{setProvince(e.target.value);setRegency('')}} className="min-w-[190px] rounded-lg border border-[#d3e0e8] bg-white px-3 py-2 text-sm text-[#173851]"><option value="">Seluruh wilayah berizin</option>{provinces.map(x=><option key={x} value={x}>{x}</option>)}</select>{province&&<select aria-label="Pilih kabupaten atau kota" value={regency} onChange={e=>setRegency(e.target.value)} className="min-w-[190px] rounded-lg border border-[#d3e0e8] bg-white px-3 py-2 text-sm text-[#173851]"><option value="">Seluruh Kabupaten/Kota</option>{regencies.map(x=><option key={x} value={x}>{x}</option>)}</select>}<span className="text-xs text-[#8192a3] ml-auto">{lastUpdated?'Social Listening diperbarui '+ago(lastUpdated):'Ringkasan data tersimpan'}</span></div>
  <Notice error={error}/>
  {loading?<div className="intel-card p-10 text-center text-sm text-[#718398]">{t('loading_intelligence')}</div>:error?null:<>
  <div className="grid grid-cols-2 lg:grid-cols-4 gap-3">
   {[[scoped.length,'Catatan intelijen',Eye,'/inbox'],[viol.length,'Indikasi perlu ditinjau',ShieldAlert,'/inbox'],[tasks.length,'Perlu tindak lanjut',Inbox,'/inbox'],[scoped.filter(verified).length,'Intelijen tervalidasi',MapPin,'/inbox']].map(([value,label,Icon,to])=><Link key={label} to={to} className="intel-card p-4 min-h-[112px] flex flex-col justify-between hover:border-[#a9c9d7]"><div className="flex items-start justify-between gap-2"><p className="text-xs font-medium text-[#72879a]">{label}</p><Icon size={16} className="shrink-0 text-[#176e8e]"/></div><strong className="text-[28px] leading-none text-[#163750] font-semibold mt-3">{value}</strong></Link>)}
  </div>
  <Section title="Ikhtisar Intelijen Wilayah" subtitle="Sebaran catatan berdasarkan penugasan wilayah yang dikonfirmasi; hanya wilayah dalam akses Anda" to="/inbox"><div className="grid md:grid-cols-[minmax(0,1.6fr)_minmax(200px,1fr)] gap-4"><div>{regions.length?<div className="divide-y divide-[#edf2f5]">{regions.map(x=><div key={x.name} className="grid grid-cols-[minmax(0,1fr)_55px_65px_75px] gap-2 items-center py-2.5 text-xs"><span className="font-semibold truncate text-[#244358]">{x.name}</span><span className="text-center text-[#496275]">{x.records} cat.</span><span className="text-center text-[#9a642e]">{x.signals} sinyal</span><span className="text-right text-[#496275]">{x.attention} tinjau</span></div>)}</div>:<Empty>Belum ada catatan dengan lokasi terkonfirmasi untuk ditampilkan.</Empty>}</div><div className="rounded-lg bg-[#f5f9fb] p-4"><p className="text-xs font-semibold text-[#36576d]">Cakupan pemantauan</p><p className="text-sm text-[#5b7184] mt-2">{province?(regency?regency+', '+province:province):'Seluruh wilayah yang diizinkan'}</p><p className="text-xs text-[#718398] mt-3">{unmapped} catatan belum dapat dipetakan secara pasti dalam cakupan pilihan.</p><p className="text-[11px] text-[#8497a6] mt-3">Catatan multi-wilayah dapat dihitung di beberapa wilayah; baris tidak untuk dijumlahkan sebagai total unik.</p></div></div></Section>
  <div className="grid lg:grid-cols-[1.28fr_1fr] gap-4 items-start">
   <Section title="Indikasi pelanggaran untuk ditinjau" subtitle="Sinyal prioritas dari Intelligence Inbox, bukan keputusan pelanggaran" to="/inbox">{viol.length?viol.slice(0,4).map(x=><Record key={x.id} item={x} detail={(signal(x)?.label||'')+' · '+(x.priority||'Prioritas belum ditetapkan')}/>):<Empty>Belum ada sinyal indikasi pelanggaran pada catatan yang tersedia.</Empty>}<p className="text-[11px] leading-5 text-[#8594a4] mt-3">Setiap indikasi membutuhkan pemeriksaan bukti dan penilaian petugas BAWASLU.</p></Section>
   <Section title="Membutuhkan perhatian Anda" subtitle="Catatan yang menunggu peninjauan atau konfirmasi wilayah" to="/inbox">{tasks.length?tasks.slice(0,4).map(x=><Record key={x.id} item={x} detail={pending(x)?'Menunggu peninjauan': 'Periksa atribusi lokasi'}/>):<Empty>Tidak ada tindak lanjut tertunda yang teridentifikasi.</Empty>}</Section>
  </div>
  <div className="grid lg:grid-cols-[1.28fr_1fr] gap-4 items-start">
   <Section title="Percakapan & temuan terbaru" subtitle="Intelijen tersimpan dalam wilayah yang dipilih" to="/inbox">{latest.length?latest.map(x=><Record key={x.id} item={x}/>):<Empty>Belum ada catatan intelijen dalam cakupan ini.</Empty>}</Section>
   <div className="space-y-4">
    <Section title="Isu utama yang tercatat" subtitle="Topik paling sering dikaitkan dengan intelijen" to="/inbox">{topics.length?<div className="space-y-3">{topics.map(([name,n],i)=><div key={name} className="flex items-center gap-3 text-sm"><span className="w-5 text-xs text-[#94a5b4]">{i+1}</span><span className="min-w-0 flex-1 truncate text-[#244358]">{name}</span><span className="font-semibold text-[#176e8e]">{n}</span></div>)}</div>:<Empty>Belum ada topik terstruktur.</Empty>}</Section>
    <Section title="Pemantauan akun & kandidat" subtitle="Ringkasan Watchlist dalam cakupan wilayah" to="/watchlist">{watchState.loading?<p className="text-sm text-[#718398]">Memuat Watchlist...</p>:watchState.error?<p className="text-sm text-[#9a5a1e]">Data Watchlist tidak tersedia.</p>:<div className="flex justify-between items-end"><div><strong className="text-2xl text-[#163750]">{relevantWatch.filter(x=>x.status==='Active').length}</strong><p className="text-xs text-[#72879a] mt-1">Pemantauan aktif</p></div><div className="text-right"><strong className="text-2xl text-[#163750]">{relevantWatch.filter(x=>x.status==='Under Review').length}</strong><p className="text-xs text-[#72879a] mt-1">Dalam peninjauan</p></div></div>}</Section>
   </div>
  </div>
  <Section title="Social Listening · antrean hasil tersimpan" subtitle={scopeActive?'Hasil tersimpan pada cakupan akun Anda; bagian ini tidak mengikuti filter wilayah':'Hasil tersimpan yang dapat diakses; maksimal 500 hasil terbaru, tanpa crawling baru'} to="/social-listening">{socialLoading?<p className="text-sm text-[#718398]">Memuat hasil Social Listening...</p>:socialError?<p role="alert" className="text-sm text-[#9a5a1e]">{socialError}</p>:<div className="grid md:grid-cols-[minmax(0,1fr)_minmax(0,2fr)] gap-5"><div className="grid grid-cols-3 gap-2">{[['DISCOVERED','Ditemukan'],['RELEVANT','Relevan'],['MONITOR','Dipantau']].map(([key,label])=><div key={key} className="rounded-lg bg-[#f5f9fb] p-3"><strong className="text-xl text-[#163750]">{Number(socialCounts[key]||0)}</strong><p className="text-[11px] text-[#718398] mt-1">{label}</p></div>)}</div><div className="min-w-0">{socialItems.length?socialItems.map(x=><div key={x.id} className="border-b border-[#edf2f5] last:border-0 py-2"><p className="text-sm text-[#244358] line-clamp-2">{x.text_content||'Konten tanpa teks'}</p><p className="text-xs text-[#8192a3] mt-1">{x.platform||x.provider} · {x.review_state} · {ago(x.published_at||x.collected_at)}</p></div>):<Empty>Belum ada hasil dalam antrean review.</Empty>}</div></div>}</Section>
  <p className="text-xs text-[#8394a4] leading-5"><AlertTriangle size={13} className="inline mr-1"/>Ringkasan intelijen memakai hingga 500 catatan terbaru yang dapat diakses; Social Listening memakai hingga 500 hasil tersimpan terbaru. Angka bukan total sepanjang waktu. Filter lokasi hanya mencakup intelijen berlokasi terkonfirmasi. Indikasi AI, bukti belum terverifikasi, dan hasil Social Listening tidak boleh dianggap sebagai temuan pelanggaran yang telah diputuskan.</p>
  </>}
 </div>;
}
