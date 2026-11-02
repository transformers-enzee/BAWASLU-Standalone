import {useEffect,useMemo,useRef,useState} from 'react';
import {
 LayoutDashboard,Radio,Inbox,Sparkles,Settings,Database,ShieldCheck,Menu,X,
 BookOpen,RotateCcw,Plus,ArrowRight,CheckCircle2,Flag,Search,Send,ChevronRight,
 BarChart3,Users,Eye,FileText,HelpCircle,Globe,SlidersHorizontal,MessageCircle,
 MapPin,Clock,Activity,LockKeyhole,Check,AlertTriangle,Play
} from 'lucide-react';
import {bi,originalPosts,profileNames,regionNames,sampleCampaigns,topicOptions,walkthrough} from './data.js';
import './demo.css';

const sections=[
 {key:'command',icon:LayoutDashboard,name:bi('Command Centre','Pusat Komando')},
 {key:'social',icon:Radio,name:bi('Social Listening','Pemantauan Media Sosial')},
 {key:'inbox',icon:Inbox,name:bi('Intelligence Inbox','Kotak Masuk Intelijen')},
 {key:'watchlist',icon:Users,name:bi('Candidate Watchlist','Daftar Pantauan Kandidat')},
 {key:'assistant',icon:Sparkles,name:bi('BAWASLU Intelligence Assistant','Asisten Intelijen BAWASLU')},
 {key:'validation',icon:ShieldCheck,name:bi('Validation','Validasi')},
 {key:'sources',icon:Database,name:bi('Data Sources','Sumber Data')},
 {key:'admin',icon:Settings,name:bi('Administration','Administrasi')}
];
const demoPosts=Array.from({length:72},(_,i)=>{
 const p=originalPosts[i%originalPosts.length],n=Math.floor(i/originalPosts.length);
 const date=new Date(p.day+'T00:00:00Z');date.setUTCDate(date.getUTCDate()+n);
 return {...p,id:'DEMO-'+String(i+1).padStart(3,'0'),day:date.toISOString().slice(0,10),
   engagement:p.engagement+((n*73+i*19)%530),user:n?p.user+'_'+(n+1):p.user};
});
const sentimentColors={POSITIVE:'#15b87a',NEUTRAL:'#f5b92d',NEGATIVE:'#ed454c'};
const isSelected=(status)=>status==='reviewed';
function Chart({posts,language}){
 const dates=[...new Set(posts.map(p=>p.day))].sort();
 const rows=dates.map(d=>({date:d,n:posts.filter(p=>p.day===d).length})).slice(-25);
 if(!rows.length)return <div className="d-muted">{language==='id'?'Belum ada catatan.':'No records yet.'}</div>;
 const width=500,height=205,left=45,top=15,bottom=34,right=15;
 const max=Math.max(4,Math.ceil(Math.max(...rows.map(x=>x.n),1)/4)*4);
 const x=i=>left+(rows.length<2?(width-left-right)/2:i*(width-left-right)/(rows.length-1));
 const y=n=>top+(height-top-bottom)*(1-n/max);
 const line=rows.map((r,i)=>(i?'L':'M')+x(i).toFixed(1)+' '+y(r.n).toFixed(1)).join(' ');
 const area=line+' L'+x(rows.length-1)+' '+y(0)+' L'+x(0)+' '+y(0)+' Z';
 return <svg className="d-svg" viewBox={'0 0 '+width+' '+height} role="img" aria-label={language==='id'?'Grafik aktivitas percakapan contoh':'Sample conversation activity line chart'}>
  {[0,1,2,3,4].map(i=><g key={i}><line x1={left} x2={width-right} y1={y(i*max/4)} y2={y(i*max/4)} stroke="#e1e9ec"/><text x={left-8} y={y(i*max/4)+4} textAnchor="end" fill="#678092" fontSize="10">{i*max/4}</text></g>)}
  <path d={area} fill="#219c86" fillOpacity=".13"/><path d={line} fill="none" stroke="#178b7d" strokeWidth="2.5" strokeLinejoin="round"/>
  {rows.map((r,i)=><circle key={r.date} cx={x(i)} cy={y(r.n)} r="3.2" fill="#168b7b"><title>{r.date+' · '+r.n+' '+(language==='id'?'unggahan':'posts')}</title></circle>)}
  {[0,Math.floor((rows.length-1)/2),rows.length-1].filter((v,i,a)=>a.indexOf(v)===i).map(i=><text key={i} x={x(i)} y={height-7} textAnchor="middle" fill="#648095" fontSize="10">{rows[i].date}</text>)}
  <text transform="translate(12 116) rotate(-90)" fontSize="10" fill="#668294" textAnchor="middle">{language==='id'?'Unggahan':'Posts'}</text>
 </svg>;
}
function StatusPill({status,language}){
 const values={
  pending:bi('Review needed','Perlu peninjauan'),
  reviewed:bi('Reviewed','Ditinjau'),
  NEGATIVE:bi('Negative','Negatif'),NEUTRAL:bi('Neutral','Netral'),POSITIVE:bi('Positive','Positif')
 };
 return <span className={'d-pill '+(status==='pending'||status==='NEGATIVE'?'red':status==='reviewed'||status==='POSITIVE'?'green':'')}>{values[status]?.[language]||status}</span>;
}
function Donut({posts,language,onChoose}){
 const rows=['POSITIVE','NEUTRAL','NEGATIVE'].map(s=>[s,posts.filter(p=>p.sentiment===s).length]);
 const total=posts.length||1,stop1=rows[0][1]/total*100,stop2=(rows[0][1]+rows[1][1])/total*100;
 const gradient='conic-gradient('+sentimentColors.POSITIVE+' 0 '+stop1+'%,'+sentimentColors.NEUTRAL+' '+stop1+'% '+stop2+'%,'+sentimentColors.NEGATIVE+' '+stop2+'% 100%)';
 return <div style={{display:'flex',alignItems:'center',justifyContent:'center',gap:20,flexWrap:'wrap',padding:'12px 0'}}>
   <div className="d-donut" style={{background:gradient}} role="img" aria-label={language==='id'?'Distribusi sentimen data contoh':'Sample sentiment distribution'}><div className="d-donut-inner"><strong>{posts.length}</strong><small>{language==='id'?'unggahan':'posts'}</small></div></div>
   <div className="d-legend">{rows.map(([s,n])=><button type="button" key={s} onClick={()=>onChoose?.(s)}><span className="d-dot" style={{background:sentimentColors[s]}}/><span style={{flex:1}}><StatusPill status={s} language={language}/></span><strong>{n} ({Math.round(n/total*100)}%)</strong></button>)}</div>
 </div>;
}
function DemoApp(){
 const [language,setLanguage]=useState('id');
 const [page,setPage]=useState('command'),[socialTab,setSocialTab]=useState('overview'),[mobile,setMobile]=useState(false);
 const [search,setSearch]=useState(''),[sentiment,setSentiment]=useState('ALL'),[region,setRegion]=useState('all');
 const [campaign,setCampaign]=useState('all'),[campaigns,setCampaigns]=useState(sampleCampaigns);
 const [activated,setActivated]=useState(false),[reviews,setReviews]=useState({}),[tracked,setTracked]=useState(['Kandidat A','Kandidat B','Kandidat C']);
 const [drawer,setDrawer]=useState(null),[modal,setModal]=useState(null),[toast,setToast]=useState('');
 const [guideStep,setGuideStep]=useState(0),[guideOpen,setGuideOpen]=useState(false);
 const [inboxTab,setInboxTab]=useState('all'),[sourceTab,setSourceTab]=useState('overview');
 const [assistantQuery,setAssistantQuery]=useState(''),[messages,setMessages]=useState([]);
 const [newCandidate,setNewCandidate]=useState(''),[newCampaign,setNewCampaign]=useState('');
 const [demoSettings,setDemoSettings]=useState({notifications:true,compact:false});
 const [reviewDecision,setReviewDecision]=useState('reviewed');
 const mainRef=useRef(null);
 const L=(en,id)=>language==='id'?id:en;
 const W=x=>typeof x==='object'&&x!==null&&'en' in x?x[language]:String(x??'');
 const topicName=id=>W(topicOptions.find(t=>t.id===id)?.label||bi('Other','Lainnya'));
 const currentCampaign=campaigns.find(c=>c.id===campaign);
 const scoped=useMemo(()=>demoPosts.filter(p=>(campaign==='all'||p.campaign===campaign)&&(region==='all'||p.region===region)),[campaign,region]);
 const filtered=useMemo(()=>scoped.filter(p=>(sentiment==='ALL'||p.sentiment===sentiment)&&(!search||[p.user,p.id,p.candidate,p.region,p.body.en,p.body.id,p.platform].some(x=>String(x).toLowerCase().includes(search.toLowerCase())))),[scoped,sentiment,search]);
 const pending=scoped.filter(p=>p.issue&&!isSelected(reviews[p.id]||p.status));
 const reviewed=scoped.filter(p=>isSelected(reviews[p.id]||p.status));
 const setNav=(to)=>{setPage(to);setMobile(false);setDrawer(null);setModal(null);setSearch('');setSentiment('ALL');mainRef.current?.scrollTo?.({top:0,behavior:'instant'});window.scrollTo(0,0);};
 const notify=msg=>{setToast(msg);};
 const openPost=p=>{setReviewDecision(reviews[p.id]||p.status);setDrawer({type:'post',post:p});};
 const saveReview=()=>{if(drawer?.type!=='post')return;setReviews(v=>({...v,[drawer.post.id]:reviewDecision}));notify(L('Demo review saved in this browser only.','Peninjauan simulasi tersimpan hanya di peramban ini.'));setDrawer(null);};
 const reset=()=>{setReviews({});setCampaign('all');setRegion('all');setSentiment('ALL');setSearch('');setTracked(['Kandidat A','Kandidat B','Kandidat C']);setCampaigns(sampleCampaigns);setMessages([]);setActivated(false);setDemoSettings({notifications:true,compact:false});notify(L('Demo reset. No live data was affected.','Demo diatur ulang. Tidak ada data langsung yang terpengaruh.'));};
 const startGuide=index=>{setGuideStep(index);setGuideOpen(true);setNav(walkthrough[index].page);};
 const advanceGuide=delta=>{const i=Math.max(0,Math.min(walkthrough.length-1,guideStep+delta));setGuideStep(i);setNav(walkthrough[i].page);};
 const suggestion=()=>{
  const normalized=assistantQuery.toLowerCase().trim();if(!normalized)return;
  const sentiments=['POSITIVE','NEUTRAL','NEGATIVE'].map(s=>[s,scoped.filter(p=>p.sentiment===s).length]);
  let text='';
  if(/sentimen|sentiment|positif|negative|netral/.test(normalized))text=L('From '+scoped.length+' illustrative records: '+sentiments.map(x=>x[0]+' '+x[1]).join(', ')+'. These values are local demo calculations, not AI analysis.','Dari '+scoped.length+' catatan contoh: '+sentiments.map(x=>({POSITIVE:'Positif',NEUTRAL:'Netral',NEGATIVE:'Negatif'}[x[0]])+' '+x[1]).join(', ')+'. Angka ini dihitung secara lokal, bukan hasil analisis AI baru.');
  else if(/pelanggaran|violation|risk|risiko|issue|isu/.test(normalized))text=L('There are '+pending.length+' simulated items awaiting review. Open Intelligence Inbox to inspect original illustrative texts and try a human review. An alert is not proof of a legal violation.','Ada '+pending.length+' item simulasi yang menunggu peninjauan. Buka Kotak Masuk Intelijen untuk memeriksa teks contoh dan mencoba peninjauan petugas. Peringatan bukan bukti pelanggaran hukum.');
  else if(/kandidat|candidate|watchlist|actor/.test(normalized))text=L('The simulated Watchlist contains '+tracked.length+' monitored profiles. These are fictional identities used for product training only.','Daftar Pantauan simulasi berisi '+tracked.length+' profil terpantau. Semua identitas bersifat fiktif dan hanya untuk pelatihan produk.');
  else if(/sumber|source|platform/.test(normalized))text=L('Illustrative evidence spans TikTok, Instagram, YouTube, X, Facebook, Threads and Online News. No external platform is queried.','Bukti contoh mencakup TikTok, Instagram, YouTube, X, Facebook, Threads, dan Berita Online. Tidak ada platform luar yang diakses.');
  else text=L('This is an offline demonstration. Try asking about sentiment, potential violations, candidates, or platforms. The answer uses only preloaded sample records and preset logic.','Ini demonstrasi offline. Coba tanyakan sentimen, potensi pelanggaran, kandidat, atau platform. Jawaban hanya menggunakan catatan contoh dan logika yang telah disiapkan.');
  setMessages(x=>[...x,{type:'me',id:language,en:normalized,idText:assistantQuery},{type:'bot',reply:text}]);setAssistantQuery('');
 };
 const statCard=(number,label,onClick)=> <button type="button" className="d-stat" onClick={onClick}><strong>{number}</strong><span>{label}</span></button>;
 const heading=(title,sub,icon)=> <div className="d-heading"><h2 style={{display:'flex',alignItems:'center',gap:9}}>{icon}{title}</h2>{sub&&<small>{sub}</small>}</div>;
 const badge=<span className="d-demo-tag">{L('SIMULATION','SIMULASI')}</span>;
 const postCard=p=><button key={p.id} type="button" className="d-record" onClick={()=>openPost(p)}>
   <div className="d-recordhead"><strong>{p.user}</strong><StatusPill language={language} status={p.sentiment}/></div>
   <small>{p.platform} · {p.day} · {p.id} · {p.region}</small>
   <p>{W(p.body)}</p><div style={{display:'flex',justifyContent:'space-between',alignItems:'center',gap:7,flexWrap:'wrap'}}>
    <span className="d-pill">{topicName(p.topic)}</span><span className="d-link">{L('Inspect evidence →','Periksa bukti →')}</span>
   </div>
 </button>;
 const filterBar=<div className="d-filterbar">
   <label className="d-field">{L('Campaign','Kampanye')}<select value={campaign} onChange={e=>setCampaign(e.target.value)}><option value="all">{L('All campaigns','Semua kampanye')}</option>{campaigns.map(c=><option key={c.id} value={c.id}>{W(c.name)}</option>)}</select></label>
   <label className="d-field">{L('Region','Wilayah')}<select value={region} onChange={e=>setRegion(e.target.value)}><option value="all">{L('All regions','Semua wilayah')}</option>{regionNames.map(x=><option key={x}>{x}</option>)}</select></label>
   <label className="d-field">{L('Sentiment','Sentimen')}<select value={sentiment} onChange={e=>setSentiment(e.target.value)}><option value="ALL">{L('All sentiments','Semua sentimen')}</option><option value="POSITIVE">{L('Positive','Positif')}</option><option value="NEUTRAL">{L('Neutral','Netral')}</option><option value="NEGATIVE">{L('Negative','Negatif')}</option></select></label>
   <label className="d-field">{L('Search','Pencarian')}<input value={search} onChange={e=>setSearch(e.target.value)} placeholder={L('Search sample records','Cari catatan contoh')}/></label>
  </div>;
 const hero=(title,sub,action)=><section className="d-hero"><div><div className="d-kicker">BAWASLU · {L('INTERACTIVE TRAINING DEMO','DEMO PELATIHAN INTERAKTIF')}</div><h1>{title}</h1><p>{sub}</p></div>{action}</section>;
 const command=<>
  {hero(L('Command Centre','Pusat Komando'),L('Understand what is happening, what requires attention and which evidence supports each signal.','Ketahui apa yang terjadi, apa yang perlu ditindaklanjuti, dan bukti yang mendukung setiap sinyal.'),<button className="d-btn" onClick={()=>setDrawer({type:'action'})}><Flag size={15}/>{L('Action Desk','Meja Tindakan')} <b>{pending.length}</b></button>)}
  <section id="metrics">{heading(L('Operational Overview','Ringkasan Operasional'),L('Click a metric to inspect details','Pilih metrik untuk melihat rincian'))}
   <div className="d-cardrow">
    {statCard(scoped.length,L('Captured posts','Unggahan terkumpul'),()=>setNav('social'))}
    {statCard(scoped.filter(p=>p.issue).length,L('Potential issues','Potensi isu'),()=>{setPage('inbox');setInboxTab('issues')})}
    {statCard(pending.length,L('Awaiting review','Menunggu peninjauan'),()=>setDrawer({type:'action'}))}
    {statCard(reviewed.length,L('Reviewed records','Catatan ditinjau'),()=>{setPage('validation')})}
   </div>
  </section>
  {filterBar}
  {heading(L('Five Intelligence Components','Lima Komponen Intelijen'),L('Information • Action • Review','Informasi • Tindakan • Peninjauan'))}
  <div className="d-issuegrid">{[
    [L('Potential Violations','Potensi Pelanggaran'),'campaign',scoped.filter(p=>p.issue).length],
    [L('Public Concerns','Kekhawatiran Publik'),'oversight',scoped.filter(p=>p.topic==='oversight').length],
    [L('Emerging Narratives','Narasi yang Berkembang'),'education',scoped.filter(p=>p.topic==='education').length],
    [L('Needs Attention','Perlu Perhatian'),'pending',pending.length],
    [L('Validated Intelligence','Intelijen Tervalidasi'),'reviewed',reviewed.length]
   ].map(([name,key,n])=><button key={key} className="d-issue" onClick={()=>setDrawer({type:'issue',key,title:name})}><span style={{color:'#087b6e'}}><Flag size={19}/></span><strong>{name}</strong><span className="d-pill">{n} {L('sample records','catatan contoh')}</span><p>{L('Explore linked illustrative evidence and simulated officer actions.','Jelajahi bukti contoh dan tindakan petugas simulasi.')}</p><span className="d-link">{L('View details and sources →','Lihat rincian dan sumber →')}</span></button>)}</div>
  <section id="themes">
  {heading(L('Trends & Geographic Intelligence','Tren dan Intelijen Geografis'))}
  <div className="d-grid2">
    <div className="d-panel"><h3>{L('Conversation Activity','Aktivitas Percakapan')}</h3><p>{L('Recorded sample-post publication dates','Tanggal terbit unggahan contoh')}</p><Chart posts={scoped} language={language}/><p>{L('Hover or focus a point for the exact date and count.','Arahkan kursor atau fokus pada titik untuk tanggal dan jumlah yang tepat.')}</p></div>
    <div className="d-panel"><h3>{L('Issue Distribution','Distribusi Isu')}</h3><p>{L('Most frequent conversation themes in this demo','Tema percakapan terbanyak dalam demo ini')}</p>{topicOptions.map(t=>{const n=scoped.filter(p=>p.topic===t.id).length;return <button className="d-record" key={t.id} style={{padding:'9px 11px',margin:'4px 0'}} onClick={()=>setDrawer({type:'issue',key:t.id,title:W(t.label)})}><div className="d-recordhead"><strong>{W(t.label)}</strong><b>{n}</b></div><div className="d-meter"><div style={{width:Math.round(n/(scoped.length||1)*100)+'%'}}/></div></button>})}</div>
    <div className="d-panel"><h3>{L('Geographic Signals','Sinyal Geografis')}</h3><p>{L('Source-region references, not verified incident locations','Referensi wilayah sumber, bukan lokasi kejadian terverifikasi')}</p><div className="d-regionmap"><MapPin color="#158a7b" size={30}/><div className="d-regions">{regionNames.map(r=><button className={'d-region '+(region===r?'active':'')} key={r} onClick={()=>setRegion(region===r?'all':r)}>{r} · {scoped.filter(p=>p.region===r).length}</button>)}</div></div><p>{L('Choose a region to filter the demo.','Pilih wilayah untuk memfilter demo.')}</p></div>
    <div className="d-panel"><h3>{L('Normalized Topics','Topik Ternormalisasi')}</h3><p>{L('Keyword examples derived from local sample records','Contoh kata kunci dari catatan lokal')}</p><div className="d-cloud">{topicOptions.map((t,i)=><button key={t.id} style={{fontSize:20+(3-i)*3}} onClick={()=>setDrawer({type:'issue',key:t.id,title:W(t.label)})}>{W(t.label)}</button>)}</div></div>
    <div className="d-panel"><h3>{L('Sentiment Distribution','Distribusi Sentimen')}</h3><p>{L('Only three sentiment categories are used in the demo.','Demo hanya menggunakan tiga kategori sentimen.')}</p><Donut posts={scoped} language={language} onChoose={s=>{setSentiment(s);setNav('social');setSentiment(s);setSocialTab('posts')}}/></div>
    <div className="d-panel"><h3>{L('Activity by Platform','Aktivitas Berdasarkan Platform')}</h3><p>{L('Sample post counts by source','Jumlah unggahan contoh berdasarkan sumber')}</p>{[...new Set(scoped.map(p=>p.platform))].map(platform=><div className="d-barline" key={platform}><span>{platform}</span><div className="d-meter"><div style={{width:scoped.filter(p=>p.platform===platform).length/(scoped.length||1)*100+'%'}}/></div><b>{scoped.filter(p=>p.platform===platform).length}</b></div>)}</div>
  </div></section>
 </>;
 const social=<>
  {hero(L('Social Listening','Pemantauan Media Sosial'),L('Explore collection campaigns, captured posts and candidate tracking using local example records.','Jelajahi kampanye pemantauan, unggahan terkumpul, dan pemantauan kandidat dengan catatan contoh lokal.'),<button className="d-btn" onClick={()=>setModal('campaign')}><Plus size={15}/>{L('Create campaign','Buat kampanye')}</button>)}
  <div className="d-tabs">{[['overview',L('Overview','Ringkasan')],['posts',L('Captured Posts','Unggahan Tersimpan')],['watchlist',L('Candidate Watchlist','Daftar Pantauan Kandidat')]].map(([key,title])=><button className={'d-tab '+(socialTab===key?'active':'')} onClick={()=>setSocialTab(key)} key={key}>{title}</button>)}</div>
  {socialTab==='watchlist'?watchlistInner():<>{filterBar}{socialTab==='overview'?<>
    <section id="campaigns">{heading(L('Campaigns & Collection','Kampanye dan Pengumpulan'))}
     <div className="d-grid3">{campaigns.map(c=><div className="d-panel" key={c.id}><h3>{W(c.name)}</h3><p>{L('Local sample monitoring scope','Cakupan pemantauan contoh lokal')}</p><strong>{demoPosts.filter(p=>p.campaign===c.id).length} {L('sample posts','unggahan contoh')}</strong><div style={{marginTop:13}}><button className="d-btn tiny" onClick={()=>setCampaign(c.id)}>{L('Select campaign','Pilih kampanye')}</button></div></div>)}</div>
    </section><div className="d-panel" style={{marginTop:16,background:'#f0faf7',borderColor:'#b9e3d5'}}><h3>{L('Collection Simulator','Simulator Pengumpulan')}</h3><p>{L('Click Activate to preview the collection workflow. This is not a real crawl; no credits or platform access are used.','Klik Aktifkan untuk mencoba alur pengumpulan. Ini bukan perayapan nyata; tidak menggunakan kredit atau akses platform.')}</p><button className="d-btn green" onClick={()=>{setActivated(true);notify(L('Simulation activated. No external collection occurred.','Simulasi diaktifkan. Tidak ada pengumpulan eksternal.'))}}><Play size={15}/>{activated?L('Simulation active','Simulasi aktif'):L('Activate (simulation)','Aktifkan (simulasi)')}</button></div>
    {heading(L('Captured Intelligence Summary','Ringkasan Intelijen Terkumpul'))}
    <div className="d-cardrow">{statCard(scoped.length,L('Sample records','Catatan contoh'),()=>setSocialTab('posts'))}{statCard(new Set(scoped.map(p=>p.platform)).size,L('Platforms','Platform'),()=>setSocialTab('posts'))}{statCard(scoped.filter(p=>p.issue).length,L('Attention signals','Sinyal perhatian'),()=>setNav('inbox'))}{statCard(tracked.length,L('Tracked profiles','Profil dipantau'),()=>setSocialTab('watchlist'))}</div>
    <div className="d-grid2"><div className="d-panel"><h3>{L('Conversation Activity','Aktivitas Percakapan')}</h3><Chart language={language} posts={scoped}/></div><div className="d-panel"><h3>{L('Sentiment Distribution','Distribusi Sentimen')}</h3><Donut posts={scoped} language={language} onChoose={v=>{setSentiment(v);setSocialTab('posts')}}/></div></div>
   </>:<><div className="d-notice">{L('Illustrative source posts only. Clicking a record opens its local evidence preview.','Hanya unggahan sumber contoh. Klik catatan untuk membuka pratinjau bukti lokal.')}</div><div style={{marginTop:13}} className="d-list">{filtered.slice(0,24).map(postCard)}</div><p className="d-muted">{L('Showing','Menampilkan')} {Math.min(24,filtered.length)} / {filtered.length}</p></>}</>}
 </>;
 function watchlistInner(){
  const counts=new Map(tracked.map(x=>[x,demoPosts.filter(p=>p.candidate===x).length]));
  return <section id="watchlist"><div className="d-heading"><h2>{L('Candidate Watchlist','Daftar Pantauan Kandidat')}</h2><button className="d-btn primary" onClick={()=>setModal('candidate')}><Plus size={15}/>{L('Add Candidate','Tambah Kandidat')}</button></div>
   <p className="d-muted">{L('Manage illustrative candidate identities. Tracking actions are temporary and do not connect to any profile or source.','Kelola identitas kandidat contoh. Tindakan pemantauan sementara dan tidak terhubung dengan profil atau sumber mana pun.')}</p>
   <div className="d-cardrow">{statCard(tracked.length,L('Active candidate tracking','Pemantauan kandidat aktif'),()=>setModal('candidate'))}{statCard(demoPosts.length,L('Illustrative mentions','Penyebutan contoh'),()=>setNav('social'))}{statCard(0,L('Verified violations','Pelanggaran terverifikasi'),()=>{})}{statCard(0,L('Real platform connections','Koneksi platform nyata'),()=>{})}</div>
   <div className="d-grid2">{tracked.map(c=><button className="d-record" key={c} onClick={()=>setDrawer({type:'candidate',name:c})}><div className="d-recordhead"><strong>{c} →</strong><span className="d-pill green">{L('Active tracking','Sedang dipantau')}</span></div><p>{L('National · ','Nasional · ')}{counts.get(c)} {L('sample mentions','penyebutan contoh')}</p><span className="d-link">{L('Open candidate profile →','Buka profil kandidat →')}</span></button>)}</div>
  </section>;
 }
 const inbox=<>
  {hero(L('Intelligence Inbox','Kotak Masuk Intelijen'),L('Review saved example evidence, distinguish AI suggestions from officer decisions and preserve original content.','Tinjau bukti contoh, bedakan saran AI dari keputusan petugas, dan pertahankan konten asli.'),<button className="d-btn" onClick={()=>setDrawer({type:'action'})}>{L('Review queue','Antrean peninjauan')} · {pending.length}</button>)}
  <div className="d-tabs">{[['all',L('All relevant','Semua relevan')],['issues',L('Potential issues','Potensi isu')],['pending',L('Needs review','Perlu ditinjau')],['reviewed',L('Reviewed','Ditinjau')]].map(([key,title])=><button key={key} className={'d-tab '+(inboxTab===key?'active':'')} onClick={()=>setInboxTab(key)}>{title}</button>)}</div>
  {filterBar}
  {heading(L('Simulated Intelligence Findings','Temuan Intelijen Simulasi'),L('Choose a record to inspect its evidence','Pilih catatan untuk memeriksa bukti'))}
  <div className="d-list">{filtered.filter(p=>inboxTab==='all'||inboxTab==='issues'&&p.issue||inboxTab==='pending'&&p.issue&&!isSelected(reviews[p.id]||p.status)||inboxTab==='reviewed'&&isSelected(reviews[p.id]||p.status)).slice(0,24).map(p=><button key={p.id} className="d-record" onClick={()=>openPost(p)}><div className="d-recordhead"><strong>{topicName(p.topic)}</strong><StatusPill status={reviews[p.id]||p.status} language={language}/></div><small>{p.id} · {p.platform} · {p.day} · {p.region}</small><p>{W(p.body)}</p><span className="d-link">{L('View intelligence & original example →','Lihat intelijen dan contoh asli →')}</span></button>)}</div>
 </>;
 const watch=<>{hero(L('Candidate Watchlist','Daftar Pantauan Kandidat'),L('Monitor candidate references and test candidate-profile workflows in the demo.','Pantau penyebutan kandidat dan coba alur profil kandidat dalam demo.'),<button className="d-btn" onClick={()=>setModal('candidate')}><Plus size={15}/>{L('Add Candidate','Tambah Kandidat')}</button>)}{watchlistInner()}</>;
 const assistant=<>
  {hero(L('BAWASLU Intelligence Assistant','Asisten Intelijen BAWASLU'),L('Practice asking intelligence questions against locally embedded examples. No AI API is called.','Latih pertanyaan intelijen menggunakan contoh lokal. Tidak ada panggilan ke API AI.'),<Sparkles size={30}/>)}
  {heading(L('Offline Guided Assistant','Asisten Panduan Offline'))}
  <div className="d-panel"><div className="d-notice amber">{L('Responses are preset training examples, not new AI analysis or verified findings.','Jawaban merupakan contoh pelatihan yang telah disiapkan, bukan analisis AI baru atau temuan terverifikasi.')}</div>
   <div style={{display:'flex',gap:8,flexWrap:'wrap',margin:'15px 0'}}>{[L('Summarize sentiment','Ringkas sentimen'),L('Show potential issues','Tampilkan potensi isu'),L('Which candidates are tracked?','Kandidat mana yang dipantau?'),L('Which platforms are included?','Platform apa saja yang dicakup?')].map(prompt=><button key={prompt} className="d-btn tiny" onClick={()=>setAssistantQuery(prompt)}>{prompt}</button>)}</div>
   <div className="d-chat" aria-live="polite">{messages.length?messages.map((m,i)=><div className={'d-bubble '+(m.type==='me'?'me':'')} key={i}>{m.type==='me'?m.idText:m.reply}</div>):<div className="d-bubble">{L('Welcome to the offline BAWASLU product tour. Ask about sample sentiment, issues, candidates or platforms.','Selamat datang di tur produk offline BAWASLU. Tanyakan sentimen, isu, kandidat, atau platform dalam data contoh.')}</div>}</div>
   <form className="d-chatinput" onSubmit={e=>{e.preventDefault();suggestion()}}><input aria-label={L('Ask the offline assistant','Tanya asisten offline')} value={assistantQuery} onChange={e=>setAssistantQuery(e.target.value)} placeholder={L('Ask a question about this demo...','Ajukan pertanyaan mengenai demo ini...')}/><button className="d-btn primary" type="submit"><Send size={15}/>{L('Send','Kirim')}</button></form>
  </div>
 </>;
 const validation=<>
  {hero(L('Validation & Review','Validasi dan Peninjauan'),L('Learn how officers validate findings. Every decision here stays in browser memory.','Pelajari cara petugas memvalidasi temuan. Semua keputusan hanya tersimpan dalam memori peramban.'),<ShieldCheck size={30}/>)}
  <div className="d-cardrow">{statCard(pending.length,L('Awaiting review','Menunggu peninjauan'),()=>setDrawer({type:'action'}))}{statCard(reviewed.length,L('Reviewed','Ditinjau'),()=>{})}{statCard(0,L('Legal determinations','Penetapan hukum'),()=>{})}{statCard(0,L('Data uploads','Unggahan data'),()=>{})}</div>
  {heading(L('Human Review Queue','Antrean Peninjauan Petugas'))}
  <div className="d-notice amber">{L('Demo decisions are not real legal findings or official submissions.','Keputusan dalam demo bukan temuan hukum atau pengajuan resmi.')}</div>
  <div className="d-list" style={{marginTop:12}}>{pending.slice(0,12).map(p=><button className="d-record" key={p.id} onClick={()=>openPost(p)}><div className="d-recordhead"><strong>{p.id} · {topicName(p.topic)}</strong><StatusPill status="pending" language={language}/></div><p>{W(p.body)}</p><span className="d-link">{L('Open review →','Buka peninjauan →')}</span></button>)}</div>
  {!pending.length&&<div className="d-notice">{L('All simulated items have been reviewed. Use Reset to practice again.','Semua item simulasi telah ditinjau. Gunakan Atur Ulang untuk berlatih lagi.')}</div>}
 </>;
 const sources=<>
  {hero(L('Data Sources','Sumber Data'),L('Explore supported channels and evidence lineage without connecting accounts.','Jelajahi kanal yang didukung dan asal-usul bukti tanpa menghubungkan akun.'),<Database size={30}/>)}
  <div className="d-tabs">{[['overview',L('Sources','Sumber')],['evidence',L('Evidence Records','Catatan Bukti')],['status',L('Connection Status','Status Koneksi')]].map(([key,title])=><button className={'d-tab '+(sourceTab===key?'active':'')} key={key} onClick={()=>setSourceTab(key)}>{title}</button>)}</div>
  {sourceTab==='overview'?<div className="d-grid3">{['TikTok','Instagram','YouTube','Facebook','X','Threads','Online News'].map(platform=><div className="d-panel" key={platform}><h3>{platform}</h3><p>{L('Supported product channel (sample only)','Kanal produk yang didukung (contoh saja)')}</p><span className="d-pill amber">{L('Demo only · offline','Hanya demo · offline')}</span></div>)}</div>:
    sourceTab==='evidence'?<div className="d-list">{demoPosts.slice(0,8).map(postCard)}</div>:<div className="d-notice">{L('No credentials, crawlers, databases, AI providers or integrations are active in demo mode.','Tidak ada kredensial, perayap, basis data, penyedia AI, atau integrasi yang aktif dalam mode demo.')}</div>}
 </>;
 const admin=<>
  {hero(L('Administration','Administrasi'),L('Preview roles and preferences without creating users or modifying live settings.','Pratinjau peran dan preferensi tanpa membuat pengguna atau mengubah pengaturan langsung.'),<Settings size={30}/>)}
  {heading(L('Workspace & Roles','Ruang Kerja dan Peran'))}
  <div className="d-grid2">
   <div className="d-panel"><h3>{L('Demo Officer','Petugas Demo')}</h3><p>{L('Example role: Viewer / Reviewer','Contoh peran: Pembaca / Peninjau')}</p><span className="d-pill green">{L('Local preview','Pratinjau lokal')}</span></div>
   <div className="d-panel"><h3>{L('Permissions','Izin Akses')}</h3><p>{L('Explore intelligence, perform simulated reviews, change language and open the user guide.','Jelajahi intelijen, lakukan peninjauan simulasi, ubah bahasa, dan buka panduan pengguna.')}</p></div>
  </div>
  {heading(L('Demo Preferences','Preferensi Demo'))}
  <div className="d-panel d-stack"><label><input type="checkbox" checked={demoSettings.notifications} onChange={e=>setDemoSettings(v=>({...v,notifications:e.target.checked}))}/> {L('Show demo confirmations','Tampilkan konfirmasi demo')}</label>
   <label><input type="checkbox" checked={demoSettings.compact} onChange={e=>setDemoSettings(v=>({...v,compact:e.target.checked}))}/> {L('Compact records preview','Pratinjau catatan ringkas')}</label>
   <div><button className="d-btn" onClick={reset}><RotateCcw size={15}/>{L('Reset all demo actions','Atur ulang semua tindakan demo')}</button></div>
   <p>{L('Settings are not stored, transferred or shared. Refreshing restores the initial demo state.','Pengaturan tidak disimpan, dikirim, atau dibagikan. Memuat ulang akan mengembalikan kondisi awal demo.')}</p>
  </div>
 </>;
 const content={command,social,inbox,watchlist:watch,assistant,validation,sources,admin}[page];
 useEffect(()=>{document.title='BAWASLU Smart Radar · Demo';},[]);
 return <div className={"d-app "+(demoSettings.compact?"compact":"")}>
  <aside className={'d-sidebar '+(mobile?'show':'')} aria-label={L('Demo navigation','Navigasi demo')}>
   <div className="d-brand"><div className="d-mark" aria-hidden="true">✦</div><div><strong>BAWASLU</strong><small>SMART RADAR</small></div></div>
   <div className="d-sidegroup"><div className="d-sidehead">{L('WORKSPACE','RUANG KERJA')}</div>{sections.slice(0,5).map(s=><button key={s.key} className={'d-navitem '+(page===s.key?'active':'')} onClick={()=>setNav(s.key)}><s.icon size={18}/>{W(s.name)}</button>)}</div>
   <div className="d-sidegroup"><div className="d-sidehead">{L('ADDITIONAL WORKSPACES','RUANG KERJA TAMBAHAN')}</div>{sections.slice(5).map(s=><button key={s.key} className={'d-navitem '+(page===s.key?'active':'')} onClick={()=>setNav(s.key)}><s.icon size={18}/>{W(s.name)}</button>)}</div>
   <div className="d-sidefooter"><strong>{L('BAWASLU Interactive Demo','Demo Interaktif BAWASLU')}</strong>{L('Illustrative data · No login · No live connections','Data contoh · Tanpa login · Tanpa koneksi langsung')}<div>Build v129.0 · {L('Demo preview','Pratinjau demo')}</div></div>
  </aside>
  <div className="d-main" ref={mainRef}>
   <header className="d-topbar"><div style={{display:'flex',alignItems:'center',gap:12}}><button className="d-btn d-mobile-menu" onClick={()=>setMobile(!mobile)} aria-label={L('Toggle menu','Buka atau tutup menu')}><Menu size={18}/></button><span className="d-toplabel">{L('ELECTION SUPERVISION / INTELLIGENCE','PENGAWASAN PEMILU / INTELIJEN')}</span></div><div className="d-actions">
    <div className="d-language" aria-label={L('Language','Bahasa')}><button aria-pressed={language==='en'} className={language==='en'?'sel':''} onClick={()=>setLanguage('en')}>EN</button><button aria-pressed={language==='id'} className={language==='id'?'sel':''} onClick={()=>setLanguage('id')}>ID</button></div>
    <button className="d-btn ghostlabel" onClick={()=>startGuide(0)}><BookOpen size={16}/> {L('User Guide','Panduan')}</button>
    <button className="d-btn primary ghostlabel" onClick={reset}><RotateCcw size={15}/>{L('Reset Demo','Atur Ulang')}</button>
   </div></header>
   <main className="d-content" id="demo-main">
    <div className="d-banner"><LockKeyhole size={20} flex="none"/><div style={{flex:1}}><strong>{L('SAFE INTERACTIVE TRAINING ENVIRONMENT','LINGKUNGAN PELATIHAN INTERAKTIF AMAN')}</strong><small>{L('Illustrative data only. No production records, network API calls, AI analysis, login, uploads or database writes.','Hanya data contoh. Tanpa catatan produksi, panggilan API jaringan, analisis AI, login, unggahan, atau penulisan basis data.')}</small></div>{badge}</div>
    {content}
    <footer className="d-footer">{L('BAWASLU Smart Radar · Self-contained demonstration · All actions are temporary','BAWASLU Smart Radar · Demonstrasi mandiri · Semua tindakan bersifat sementara')}</footer>
   </main>
  </div>
  {toast&&demoSettings.notifications&&<div role="status" className="d-notice" style={{position:'fixed',bottom:22,right:22,zIndex:120,maxWidth:380,boxShadow:'0 7px 35px #0002'}}>{toast} <button className="d-btn tiny" style={{marginLeft:8}} onClick={()=>setToast('')}>{L('Close','Tutup')}</button></div>}
  {drawer&&<div className="d-overlay" role="presentation" onMouseDown={e=>{if(e.target===e.currentTarget)setDrawer(null)}}><div className="d-drawer" role="dialog" aria-modal="true" aria-label={L('Demo details','Rincian demo')}>
   <div className="d-drawerhead"><div><h2>{drawer.type==='post'?L('Post Preview · AI Assessment','Pratinjau Unggahan · Penilaian AI'):drawer.type==='candidate'?drawer.name:drawer.type==='action'?L('Action Desk','Meja Tindakan'):drawer.title}</h2><span className="d-muted">{L('Demonstration only · no live evidence','Hanya demonstrasi · bukan bukti langsung')}</span></div><button className="d-btn" onClick={()=>setDrawer(null)} aria-label={L('Close details','Tutup rincian')}><X size={16}/></button></div>
   <div className="d-drawerbody">
    {drawer.type==='post'&&<div className="d-stack">
     <div className="d-notice amber">{L('Illustrative example, not an actual electoral allegation or legal determination.','Contoh ilustratif, bukan dugaan pemilu nyata atau penetapan hukum.')}</div>
     <div className="d-panel"><h3>{L('Original Source Provenance','Asal-usul Sumber Asli')}</h3><p>{drawer.post.id} · {drawer.post.platform} · {drawer.post.user} · {drawer.post.day}</p><p>{W(drawer.post.body)}</p><span className="d-pill">{drawer.post.region}</span></div>
     <div className="d-panel"><h3>{L('AI Assessment (sample)','Penilaian AI (contoh)')}</h3><p>{L('Topic','Topik')}: <strong>{topicName(drawer.post.topic)}</strong></p><p>{L('Sentiment','Sentimen')}: <StatusPill status={drawer.post.sentiment} language={language}/></p><p>{drawer.post.issue?L('This sample may warrant an independent officer review. The text alone does not establish wrongdoing.','Contoh ini dapat memerlukan peninjauan independen oleh petugas. Teks saja tidak membuktikan pelanggaran.'):L('Informational example without a detected potential violation.','Contoh informatif tanpa potensi pelanggaran yang terdeteksi.')}</p></div>
     <div className="d-panel"><h3>{L('Human Flag Review','Peninjauan Penandaan Petugas')}</h3><p>{L('A simulation decision does not create a real report.','Keputusan simulasi tidak membuat laporan nyata.')}</p>
      <label className="d-field">{L('Decision','Keputusan')}<select value={reviewDecision} onChange={e=>setReviewDecision(e.target.value)}><option value="pending">{L('Needs further review','Perlu peninjauan lanjutan')}</option><option value="reviewed">{L('Reviewed · no confirmed violation','Ditinjau · tanpa pelanggaran terkonfirmasi')}</option></select></label>
      <button className="d-btn green" style={{marginTop:12}} onClick={saveReview}><Check size={15}/>{L('Save simulated review','Simpan peninjauan simulasi')}</button>
     </div>
    </div>}
    {drawer.type==='action'&&<div className="d-list">{pending.slice(0,16).map(p=><button className="d-record" key={p.id} onClick={()=>openPost(p)}><div className="d-recordhead"><strong>{p.id} · {topicName(p.topic)}</strong><StatusPill status="pending" language={language}/></div><p>{W(p.body)}</p><span className="d-link">{L('Review evidence →','Tinjau bukti →')}</span></button>)}</div>}
    {drawer.type==='issue'&&<div className="d-list">{scoped.filter(p=>drawer.key==='pending'?p.issue&&!isSelected(reviews[p.id]||p.status):drawer.key==='reviewed'?isSelected(reviews[p.id]||p.status):drawer.key==='campaign'?p.issue:drawer.key==='education'?p.topic==='education':drawer.key==='oversight'?p.topic==='oversight':p.topic===drawer.key).slice(0,16).map(postCard)}</div>}
    {drawer.type==='candidate'&&<div className="d-stack">
      <div className="d-panel"><h3>{L('Candidate Activity Summary','Ringkasan Aktivitas Kandidat')}</h3><p>{L('This fictional profile appears in ','Profil fiktif ini disebut dalam ')}{demoPosts.filter(p=>p.candidate===drawer.name).length} {L('illustrative source posts. No account ownership or violations are inferred.','unggahan sumber contoh. Tidak ada kesimpulan mengenai kepemilikan akun atau pelanggaran.')}</p></div>
      <div className="d-panel"><h3>{L('Recorded Sentiment','Sentimen Tercatat')}</h3><Donut language={language} posts={demoPosts.filter(p=>p.candidate===drawer.name)}/></div>
      {demoPosts.filter(p=>p.candidate===drawer.name).slice(0,5).map(postCard)}
      <button className="d-btn" onClick={()=>{setTracked(x=>x.filter(c=>c!==drawer.name));setDrawer(null);notify(L('Candidate removed from the demo watchlist only.','Kandidat hanya dihapus dari daftar pantauan demo.'));}}>{L('Stop simulated tracking','Hentikan pemantauan simulasi')}</button>
     </div>}
   </div>
  </div></div>}
  {modal&&<div className="d-modalwrap" role="presentation" onMouseDown={e=>{if(e.target===e.currentTarget){setModal(null);setGuideOpen(false)}}}><div className="d-modal" role="dialog" aria-modal="true" aria-label={L('Demo dialog','Dialog demo')}>
   <div className="d-modalhead"><h2>{modal==='candidate'?L('Add Candidate','Tambah Kandidat'):L('Create Monitoring Campaign','Buat Kampanye Pemantauan')}</h2><button className="d-btn" onClick={()=>setModal(null)}><X size={15}/>{L('Close','Tutup')}</button></div>
   <div className="d-modalbody d-stack">
    <div className="d-notice">{L('This form is a training simulation; nothing is submitted to a server.','Formulir ini adalah simulasi pelatihan; tidak ada data yang dikirim ke server.')}</div>
    {modal==='candidate'?<>
     <p className="d-muted">{L('Select an existing fictional candidate or create a temporary sample profile.','Pilih kandidat fiktif yang sudah ada atau buat profil contoh sementara.')}</p>
     <div className="d-grid2">{profileNames.filter(n=>!tracked.includes(n)).map(n=><button className="d-record" key={n} onClick={()=>{setTracked(v=>[...v,n]);setModal(null);notify(L('Added to the demo Watchlist.','Ditambahkan ke Daftar Pantauan demo.'))}}><strong>{n}</strong><p>{L('Track sample profile','Pantau profil contoh')}</p></button>)}</div>
     <label className="d-field">{L('Fictional candidate name','Nama kandidat fiktif')}<input value={newCandidate} onChange={e=>setNewCandidate(e.target.value)} placeholder={L('Example: Candidate E','Contoh: Kandidat E')} maxLength={70}/></label>
     <button className="d-btn primary" disabled={!newCandidate.trim()||tracked.includes(newCandidate.trim())} onClick={()=>{setTracked(v=>[...v,newCandidate.trim()]);setNewCandidate('');setModal(null);notify(L('Demo candidate added locally.','Kandidat demo ditambahkan secara lokal.'))}}><Plus size={15}/>{L('Add demo candidate','Tambah kandidat demo')}</button>
    </>:<>
     <label className="d-field">{L('Campaign name','Nama kampanye')}<input maxLength={70} value={newCampaign} onChange={e=>setNewCampaign(e.target.value)} placeholder={L('Example monitoring campaign','Contoh kampanye pemantauan')}/></label>
     <button className="d-btn primary" disabled={!newCampaign.trim()} onClick={()=>{const id='custom-'+campaigns.length;setCampaigns(v=>[...v,{id,name:bi(newCampaign.trim(),newCampaign.trim())}]);setCampaign(id);setNewCampaign('');setModal(null);notify(L('Demo campaign created locally, with no live collection.','Kampanye demo dibuat secara lokal tanpa pengumpulan langsung.'))}}><Plus size={15}/>{L('Create sample campaign','Buat kampanye contoh')}</button>
    </>}
   </div>
  </div></div>}
  {guideOpen&&<div className="d-modalwrap" role="presentation" onMouseDown={e=>{if(e.target===e.currentTarget)setGuideOpen(false)}}><div className="d-modal" role="dialog" aria-modal="true" aria-label={L('Interactive user manual','Panduan pengguna interaktif')}>
    <div className="d-modalhead"><h2><BookOpen size={18} style={{display:'inline',verticalAlign:'middle',marginRight:8}}/>{L('Interactive User Manual','Panduan Pengguna Interaktif')}</h2><button className="d-btn" onClick={()=>setGuideOpen(false)}><X size={15}/>{L('Close','Tutup')}</button></div>
    <div className="d-modalbody d-stack"><div className="d-notice">{L('Step','Langkah')} {guideStep+1} / {walkthrough.length} · {L('Navigate each feature without submitting data.','Jelajahi setiap fitur tanpa mengirim data.')}</div>
     <div className="d-guideindex">{walkthrough.map((step,i)=><button key={i} className={'d-step '+(i===guideStep?'active':'')} onClick={()=>advanceGuide(i-guideStep)}><span className="d-circle">{i+1}</span><span><strong>{W(step.title)}</strong><small className="d-muted" style={{display:'block',marginTop:4}}>{W(sections.find(s=>s.key===step.page)?.name)}</small></span></button>)}</div>
     <div className="d-panel"><h3>{W(walkthrough[guideStep].title)}</h3><p>{W(walkthrough[guideStep].text)}</p></div>
     <div style={{display:'flex',justifyContent:'space-between',gap:8}}><button className="d-btn" disabled={guideStep===0} onClick={()=>advanceGuide(-1)}>{L('Previous','Sebelumnya')}</button><button className="d-btn primary" onClick={()=>guideStep===walkthrough.length-1?setGuideOpen(false):advanceGuide(1)}>{guideStep===walkthrough.length-1?L('Finish','Selesai'):L('Next step','Langkah berikutnya')} <ArrowRight size={14}/></button></div>
    </div>
  </div></div>}
 </div>;
}
export default DemoApp;
