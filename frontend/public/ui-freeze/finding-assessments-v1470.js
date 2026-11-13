/* v147.0: evidence-scoped assessments inside an opened finding drawer.
 * No persistent new navigation item, verdict, takedown, or write action.
 */
(()=>{'use strict';
 const ui=window.__bawaslu;
 if(!ui||typeof ui.openFinding!=='function')return;
 const escapeHtml=value=>String(value??'').replace(/[&<>"']/g,ch=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[ch]));
 const safeUrl=value=>{try{const url=new URL(value,location.origin);return url.origin===location.origin||url.protocol==='https:'?url.href:'';
 }catch{return ''}};
 const el=selector=>document.querySelector(selector);
 let lang='en',serial=0;
 let cached=null,tokenSeen='';
 const text=(en,id)=>lang==='id'?id:en;
 window.addEventListener('message',event=>{
   if(event.origin!==location.origin)return;
   if(event.data?.type==='BAWASLU_UI_LANGUAGE'&&['en','id'].includes(event.data.language)){
     lang=event.data.language;
     if(cached)install(cached.id,cached.result);
   }
 });
 const renderStatus=value=>({
   REVIEW_INDICATED:text('Review indicated','Perlu ditinjau'),
   CONTEXT_REVIEW_REQUIRED:text('Context review required','Periksa konteks'),
   NO_DIRECT_SIGNAL_IDENTIFIED:text('No direct signal','Tidak ada indikasi langsung')
 }[value]||escapeHtml(value||''));

 const REVIEW_LABELS={"NO_SAVED_SOURCE_EVIDENCE":["No saved evidence","Bukti tersimpan tidak tersedia"],"SOURCE_COUNT_RECONCILIATION":["Reconcile finding source counts","Cocokkan jumlah sumber dan temuan"],"CONFLICTING_SAVED_SOURCE_METADATA":["Conflicting saved source metadata","Metadata sumber tersimpan berbeda"],"ORIGINAL_POST_VERIFICATION":["Verify original post text and URL","Periksa teks dan URL postingan asli"],"REVIEWED_LEGAL_REFERENCE_REQUIRED":["Locate reviewed official legal reference","Cari rujukan hukum resmi yang ditelaah"],"LEGAL_VERSION_METADATA_INCOMPLETE":["Check version and effective date","Periksa versi dan tanggal berlaku"],"POSSIBLE_ELECTION_TYPE_MISMATCH":["Verify Pemilu/Pilkada applicability","Periksa kesesuaian Pemilu/Pilkada"],"ELECTION_TYPE_METADATA_UNKNOWN":["Confirm applicable election type","Konfirmasi jenis pemilihan"],"LEGAL_CURRENTNESS_AND_AUTHORITY_UNVERIFIED":["Verify legal force and authority","Periksa keberlakuan hukum dan kewenangan"],"PLATFORM_POST_CONTEXT_REVIEW":["Review original post in policy context","Tinjau postingan asli dan aturan platform"],"CURRENT_PLATFORM_POLICY_UNVERIFIED":["Check current official platform rules","Periksa aturan platform resmi terkini"],"PLATFORM_POLICY_REFERENCE_UNAVAILABLE":["Find unsupported platform's official policy","Cari kebijakan resmi platform yang belum didukung"]};
 function readinessHtml(readiness){
  if(!readiness||readiness.schema!=='BAWASLU_COMMAND_CENTRE_FINDING_READINESS_V1531')return '';
  const issues=Array.isArray(readiness.issues)?readiness.issues:[];
  const render=row=>{
   const names=REVIEW_LABELS[row.code]||[row.code,row.code];
   const refs=(row.legal_page_ids||[]).map(escapeHtml);
   return '<li class="small" style="margin:7px 0"><strong>'+escapeHtml(row.priority)+' · '+
    escapeHtml(names[lang==='id'?1:0])+'</strong>'+
    (refs.length?'<span class="tiny muted" style="display:block">'+text('Cited pages: ','Halaman rujukan: ')+refs.join(', ')+'</span>':'')+
    (Number(row.affected_count||0)>1?'<span class="tiny muted"> · '+Number(row.affected_count)+'</span>':'')+'</li>';
  };
  return '<section data-testid="finding-review-readiness" class="soft" style="padding:12px;margin:12px 0">'+
   '<strong>'+text('Officer review priorities','Prioritas pemeriksaan petugas')+
   ' · '+issues.length+'</strong>'+
   '<p class="tiny muted">'+text('P1/P2/P3 are review order, not violation severity. No automated legal/platform decision.','P1/P2/P3 adalah urutan pemeriksaan, bukan tingkat pelanggaran. Tidak ada keputusan hukum/platform otomatis.')+'</p>'+
   (issues.length?'<ol style="padding-left:20px">'+issues.slice(0,3).map(render).join('')+'</ol>'+
    (issues.length>3?'<details data-testid="finding-review-more"><summary>'+text('More checks','Pemeriksaan lainnya')+
      ' · '+(issues.length-3)+'</summary><ol style="padding-left:20px">'+issues.slice(3).map(render).join('')+'</ol></details>':''):
    '<p class="tiny muted">'+text('No additional source gaps detected. Official law and platform currentness remain unverified.','Tidak terdeteksi celah sumber tambahan. Keberlakuan hukum dan aturan platform tetap belum diverifikasi.')+'</p>')+
   '</section>';
 }
 function legalHtml(data){
   const refs=data.approved_reference_pages||[];
   const steps=data.recommended_follow_up||[];
   return '<p class="small muted">'+escapeHtml(data.notice)+'</p>'+
    '<p class="tiny muted">'+text('References: officer-reviewed legal PDFs only; no current statutory article or legal effect has been verified.',
         'Rujukan: hanya PDF hukum yang ditelaah petugas; pasal dan keberlakuannya belum diverifikasi.')+'</p>'+
    '<p class="small"><strong>'+text('Current assessment:','Hasil penilaian:')+'</strong> '+(
      data.status==='PRELIMINARY_REVIEW_RECOMMENDED'?
       text('A saved potential-violation signal requires officer legal review.','Indikasi dugaan pelanggaran tersimpan, diperlukan telaah hukum petugas.'):
       text('No potential-violation flag for this finding. This does not prove legal compliance.','Tidak ada penanda dugaan pelanggaran untuk temuan ini. Bukan bukti kepatuhan hukum.')
    )+'</p>'+
    '<h4>'+text('Reviewed document page references','Rujukan halaman dokumen yang ditelaah')+'</h4>'+
    (refs.length?refs.map(row=>
      '<div class="soft small"><strong>'+escapeHtml(row.title)+' · '+text('page','halaman')+' '+Number(row.page)+'</strong>'+
      '<p>'+escapeHtml(String(row.excerpt||'').slice(0,450))+'</p><div class="tiny muted">'+escapeHtml(row.record_id)+' · '+
      text('Officer-reviewed upload, legal currency not verified.','Dokumen telah ditelaah, keberlakuan hukum belum diverifikasi.')+
      ' · '+escapeHtml(row.match_method||'KEYWORD')+
      (row.legal_version_label?' · '+text('Recorded version: ','Versi tercatat: ')+escapeHtml(row.legal_version_label):'')+
      (row.legal_effective_date?' · '+text('Recorded effective date: ','Tanggal berlaku tercatat: ')+escapeHtml(row.legal_effective_date):'')+
      ' · '+text('Election type: ','Jenis pemilihan: ')+escapeHtml(row.legal_election_type||'UNSPECIFIED')+
      ' <a href="/assistant" target="_top" rel="noopener noreferrer">'+text('Open Knowledge Library','Buka Pustaka Pengetahuan')+' ↗</a></div></div>').join(''):
      '<p class="small muted">'+text('No matching officer-reviewed regulation or SOP. Upload and review current official rules before citing any provision.','Tidak ada peraturan atau SOP cocok yang telah ditelaah. Unggah dan tinjau aturan resmi terkini sebelum mengutip pasal.')+'</p>')+
    '<h4>'+text('Follow-up considerations','Pertimbangan tindak lanjut')+'</h4><ol style="padding-left:22px">'+
    steps.map(s=>'<li class="small" style="margin:8px 0">'+escapeHtml(s)+'</li>').join('')+'</ol>'+
    '<p class="tiny muted">'+text('No article, deadline, offence or legal verdict has been automatically established.','Tidak ada pasal, tenggat, unsur pelanggaran, atau putusan hukum yang ditetapkan otomatis.')+'</p>';
 }
 function policyHtml(data){
   const rows=data.potential_review_queue||[];
   const links=data.policy_references||[];
   const counts=data.status_counts||{};
   return '<p class="small muted">'+escapeHtml(data.notice)+'</p>'+
    '<p class="small"><strong>'+text('Saved sources screened:','Sumber yang ditelaah:')+'</strong> '+Number(data.source_count_assessed||0)+
    ' · '+Number(counts.REVIEW_INDICATED||0)+' '+text('direct review cues','indikasi perlu ditelaah')+
    ' · '+Number(counts.CONTEXT_REVIEW_REQUIRED||0)+' '+text('context checks','butuh pemeriksaan konteks')+'</p>'+
    (rows.length?rows.map(row=>{
       const link=safeUrl(row.source_url),policy=safeUrl(row.policy_url);
       const labels=(row.categories||[]).map(key=>row.category_labels?.[key]?.[lang]||key);
       return '<div class="soft small"><strong>'+escapeHtml(row.platform)+' · '+renderStatus(row.status)+'</strong>'+
         '<div>'+labels.map(escapeHtml).join(', ')+'</div><p>'+escapeHtml(row.excerpt||'')+'</p>'+
         (row.source_text_conflict?'<p class="tiny muted">'+
          text('Conflicting saved excerpts: verify the original post before taking action.',
               'Kutipan tersimpan berbeda: periksa postingan asli sebelum bertindak.')+'</p>':'')+
         (row.policy_scope_note?'<p class="tiny muted">'+escapeHtml(row.policy_scope_note)+'</p>':'')+
         (link?'<a href="'+escapeHtml(link)+'" rel="noopener noreferrer" target="_blank">'+text('Original post','Postingan asli')+' ↗</a> · ':'')+
         (policy?'<a href="'+escapeHtml(policy)+'" rel="noopener noreferrer" target="_blank">'+text('Platform policy','Aturan platform')+' ↗</a>':'')+
         '</div>';
     }).join('')+(data.queue_is_sample?'<p class="tiny muted">'+text('Showing the first 12 source signals only.','Hanya 12 indikasi pertama ditampilkan.')+'</p>':''):
     '<p class="small muted">'+text('No direct harmful-content pattern detected in saved source text. This does not certify policy compliance.','Tidak ada pola langsung terdeteksi dari teks tersimpan. Bukan sertifikasi kepatuhan aturan platform.')+'</p>')+
    (links.length?'<h4>'+text('Official policy entrypoints (versions unverified)','Tautan aturan resmi (versi belum diverifikasi)')+'</h4>'+
     links.map(row=>'<p class="small"><a href="'+escapeHtml(safeUrl(row.policy_url))+
     '" rel="noopener noreferrer" target="_blank">'+escapeHtml(row.platform)+' ↗</a>'+
     (row.policy_scope_note?'<span class="tiny muted"> · '+escapeHtml(row.policy_scope_note)+'</span>':'')+'</p>').join(''):'')+
    '<p class="tiny muted">'+text('Ordinary political criticism and negative sentiment are not platform-rule breaches.','Kritik politik dan sentimen negatif biasa bukan pelanggaran aturan platform.')+'</p>';
 }
 function install(id, result){
   const drawer=el('#drawerBody'),overlay=el('#overlay');
   if(!drawer||!overlay?.classList.contains('open')||!ui.db().some(f=>f.id===id))return;
   el('#findingAssessments')?.remove();
   const panel=document.createElement('section');
   panel.id='findingAssessments';
   panel.setAttribute('aria-label',text('Finding assessments and recommendations','Penilaian dan rekomendasi temuan'));
   panel.style.cssText='margin:22px 0;padding:18px;border:1px solid #dce5ec;border-radius:12px;background:#fff';
   const provenance=result.source_provenance||{};
   const matches=provenance.source_count_matches_finding;
   const missing=Number(provenance.missing_original_text||0)+Number(provenance.missing_original_url||0);
   const follow=result.follow_up||{};
   const linked=(follow.source_actions||[]);
   const followHtml='<h4>'+text('Officer casework follow-up','Tindak lanjut penugasan petugas')+'</h4>'+
     '<p class="tiny muted">'+text(
       'Opens existing Inbox casework. Source access and evidence are rechecked; no assignment, legal decision or takedown happens automatically.',
       'Membuka penugasan Inbox. Hak akses dan bukti diperiksa kembali; tidak ada penugasan, keputusan hukum atau takedown otomatis.')+'</p>'+
     (linked.length?linked.map(source=>{
       const url=source.casework_url?safeUrl(source.casework_url):'';
       const existing=Number(source.existing_case_id||0);
       const title=existing?text('Open existing assignment','Buka penugasan yang ada')+
         ' #'+existing:text('Start source-linked officer review','Mulai telaah petugas berdasarkan sumber');
       return '<div class="soft small" style="margin:8px 0"><strong>Social #'+escapeHtml(source.source_id)+
         ' · '+text('Campaign','Kampanye')+' #'+escapeHtml(source.campaign_id)+'</strong>'+
         (existing?' · '+escapeHtml(source.existing_case_status||''):'')+
         (url?'<p><a href="'+escapeHtml(url)+'" target="_top" rel="noopener noreferrer">'+title+' ↗</a></p>':
           '<p class="tiny muted">'+text('Read-only access: assignment creation is not permitted.','Akses hanya-baca: pembuatan penugasan tidak diizinkan.')+'</p>')+
         '</div>';
     }).join(''):
     '<p class="tiny muted">'+text('No eligible saved social post for contextual casework.','Tidak ada postingan tersimpan yang memenuhi syarat penugasan berbasis sumber.')+'</p>')+
     (follow.source_actions_sampled?'<p class="tiny muted">'+
       text('Showing first eight source actions; inspect the other evidence in this finding.','Menampilkan delapan tindakan sumber pertama; periksa bukti lainnya pada temuan ini.')+'</p>':'')+
     '<p class="tiny muted">'+text('Visible existing assignments: ','Penugasan yang dapat diakses: ')+
       Number(follow.visible_existing_case_count||0)+'</p>';
   panel.innerHTML='<h3 style="margin:0 0 6px">'+text('Assessments & Recommendations','Penilaian & Rekomendasi')+'</h3>'+
    '<p class="tiny muted">'+text('Saved source evidence only · Preliminary assessment · Officer decision required','Hanya bukti tersimpan · Penilaian awal · Keputusan petugas diperlukan')+'</p>'+
    '<p class="tiny muted">'+text('Unique Inbox sources assessed: ','Sumber unik Inbox yang ditelaah: ')+
     Number(result.source_count_assessed||0)+
     ' · '+text('Duplicate links removed: ','Tautan duplikat dihapus: ')+Number(provenance.duplicate_links_removed||0)+
     (matches===false?' · '+text('Source count mismatch: review evidence mapping','Jumlah sumber tidak sesuai: periksa pemetaan bukti'):'')+
     (missing?' · '+text('Missing original text/URL: ','Teks/URL asli tidak tersedia: ')+missing:'')+
     (provenance.conflicting_source_metadata_requires_review?
      ' · '+text('Conflicting saved source evidence (text/URL/platform): ',
                 'Bukti sumber tersimpan berbeda (teks/URL/platform): ')+
      [provenance.source_text_conflicts||0,provenance.source_url_conflicts||0,
       provenance.source_platform_conflicts||0].join('/'):'')+
     '</p>'+
    readinessHtml(result.review_readiness)+
    '<div role="tablist" aria-label="Assessment categories" style="display:flex;gap:8px;margin:12px 0">'+
    '<button type="button" role="tab" data-review-tab="legal" aria-selected="true" class="button primary">'+text('Legal Assessment','Penilaian Hukum')+'</button>'+
    '<button type="button" role="tab" data-review-tab="policy" aria-selected="false" class="button">'+text('Platform Policy','Aturan Platform')+'</button></div>'+
    '<div data-review-detail role="tabpanel"></div>'+
    '<div data-officer-casework>'+followHtml+'</div>'+
    '<p class="small" style="margin-top:14px"><a href="/inbox?casework=1" target="_top" rel="noopener noreferrer">'+
    text('Browse my authorized casework queue','Buka antrean penugasan sesuai hak akses')+' ↗</a></p>';
   drawer.appendChild(panel);
   const renderTab=kind=>{
     panel.querySelector('[data-review-detail]').innerHTML=kind==='legal'?legalHtml(result.legal):policyHtml(result.platform_policy);
     panel.querySelectorAll('[data-review-tab]').forEach(b=>{
       const chosen=b.dataset.reviewTab===kind;
       b.setAttribute('aria-selected',String(chosen));b.classList.toggle('primary',chosen);
     });
   };
   panel.addEventListener('click',event=>{
     const button=event.target.closest('[data-review-tab]');
     if(button)renderTab(button.dataset.reviewTab);
   });
   renderTab('legal');
 }
 const previous=ui.openFinding;
 ui.openFinding=async function(id,origin){
   const run=++serial;
   cached=null;
   await previous(id,origin);
   if(run!==serial||!el('#overlay')?.classList.contains('open'))return;
   const drawer=el('#drawerBody');
   if(!drawer||!ui.db().some(f=>f.id===id)||!drawer.querySelector('.source'))return;
   const token=localStorage.getItem('bawaslu_access_token')||'';
   if(token!==tokenSeen){cached=null;tokenSeen=token;}
   const loading=document.createElement('p');
   loading.id='findingAssessments';
   loading.className='soft small';
   loading.setAttribute('role','status');
   loading.textContent=text('Loading source-linked assessments…','Memuat penilaian berdasarkan sumber…');
   drawer.appendChild(loading);
   try{
     const response=await fetch('/api/finding-assessments/'+encodeURIComponent(id),{
       cache:'no-store',headers:{Authorization:'Bearer '+token},signal:AbortSignal.timeout(20000)
     });
     const result=await response.json().catch(()=>({}));
     if(!response.ok)throw Error(typeof result.detail==='string'?result.detail:'Assessment unavailable');
     if(run!==serial||!el('#overlay')?.classList.contains('open')||
         (localStorage.getItem('bawaslu_access_token')||'')!==token)return;
     cached={id,result};
     install(id,result);
   }catch(error){
     if(run!==serial||!loading.isConnected)return;
     loading.textContent=text('Assessment unavailable. Original finding evidence remains accessible.','Penilaian tidak tersedia. Bukti temuan asli tetap dapat diakses.')+
       ' ('+String(error.message||'')+')';
   }
 };
 const refresh=ui.refreshDrawer;
 ui.refreshDrawer=function(){
   refresh?.();
   if(cached&&localStorage.getItem('bawaslu_access_token')===tokenSeen)
      install(cached.id,cached.result);
 };
})();
