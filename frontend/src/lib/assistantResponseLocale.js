/** Conversation-local presentation: question language, not app toggle/source language. */
const ID={
 findings_heading:'Temuan utama dari sumber',
 finding_label:'Temuan',
 needs_review:'Perlu verifikasi',
 verification_heading:'Tindakan verifikasi yang disarankan',
 review_notice:'Hasil AI adalah saran analitis. Pemeriksaan fakta dan keputusan resmi tetap menjadi kewenangan petugas.',
 implications_heading:'Implikasi pengawasan',
 limitations_heading:'Batas bukti',
 tags_heading:'Entitas dan isu yang teridentifikasi',
 tags_notice:'Tag disarankan AI berdasarkan sumber yang tersedia, bukan temuan hukum atau penetapan yurisdiksi.',
 candidate:'Kandidat',province:'Provinsi',suspected_violation:'Indikasi pelanggaran',
 bawaslu_issue:'Isu BAWASLU',electoral_issue:'Isu kepemiluan',
 province_mention:'Provinsi disebutkan · lokasi kejadian belum dipastikan',
 suspected_only:'Indikasi awal · perlu pemeriksaan petugas',
 stats_heading:'Lanskap percakapan pada bukti terpilih',
 stats_intro:'Statistik berasal dari unggahan relevan yang dapat diakses. Analisis AI menggunakan sebagian sumber tersebut.',
 sample_note:'Sampel · bukan survei publik',
 posts:'Unggahan dalam statistik', analysis_count:'unggahan dianalisis AI',
 engagement:'Interaksi tercatat',platforms:'Platform ditemukan',date_range:'Rentang tanggal',
 recorded_metrics:'memiliki metrik', valid_dates:'tanggal valid', sample_platforms:'Dalam sampel yang tersedia',
 sentiment_heading:'Komposisi label sentimen unggahan',
 platform_volume:'Volume unggahan menurut platform',
 daily_activity:'Aktivitas menurut tanggal unggah',
 platform_engagement:'Engagement tercatat menurut platform',
 topics_heading:'Tema pada label sumber',
 coverage_notice:'Angka menggambarkan unggahan dalam cakupan yang tersedia, bukan jumlah orang, preferensi pemilih, ataupun seluruh percakapan di internet.',
 source_tags_note:'Label topik berasal dari klasifikasi tersimpan dan belum tentu diverifikasi petugas.',
 activity_note:'Bukan tren seluruh percakapan daring; hanya tanggal dalam sampel.',
 metric_note:'Interaksi hanya dijumlahkan dari unggahan yang memiliki metrik tersimpan.',
 sources_heading:'Unggahan dan bukti sumber',
 sources_intro:'Dipilih berdasarkan relevansi terhadap pertanyaan dan konteks waktu; sumber belum tentu terverifikasi.',
 original_source:'Lihat sumber asli', source_engagement:'interaksi',no_engagement:'Metrik belum tersedia',
 prepare_from_source:'Buat penugasan dari sumber ini',
 action_title:'Saya bisa menyiapkan tindak lanjutnya',
 action_intro:'Pilih sumber penting. Saya siapkan penugasan, sarankan unit penerima, dan isi draf laporan dari analisis ini. Anda tinggal memeriksa dan mengonfirmasi.',
 steps_title:'Langkah kerja yang disiapkan',step:'Langkah',
 sources_action_heading:'Bukti yang bisa langsung ditugaskan',prepare_task:'Siapkan tugas & laporan',
 open_source:'Periksa sumber',prepare_review_title:'Penugasan siap ditinjau',
 not_saved_notice:'Belum ada tindakan yang disimpan sebelum Anda mengonfirmasi.',
 department_suggestion:'Saran unit berdasarkan tag',province_safety:'Sebutan provinsi belum tentu menunjukkan lokasi kejadian terverifikasi.',draft_details_note:'Temuan dan langkah verifikasi akan disalin sebagai draf untuk pemeriksaan petugas.',campaign_label:'Kampanye',
 department_label:'Departemen',team_label:'Tim tujuan',officer_label:'Petugas penerima (opsional)',
 case_title_label:'Judul kasus',primary_source_label:'Sumber utama',
 close:'Tutup',preview_draft:'Pratinjau draf',hide_draft:'Tutup pratinjau',
 summary_label:'Ringkasan eksekutif (dapat disunting)',
 confirm_notice:'Saya telah meninjau bahan ini dan ingin menyimpan penugasan serta draf laporan, bukan menetapkan pelanggaran.',
 submit_action:'Buat penugasan + draf laporan',officer_only:'Peran Anda belum memiliki izin membuat penugasan.',
 no_sources:'Belum ada rekaman yang dapat ditugaskan langsung. Periksa sumber terkait pada Inbox.',
 no_extra_ai:'Handoff ini menggunakan analisis yang tersedia, tanpa panggilan AI tambahan.',
 source_not_verified:'Sumber belum diverifikasi',
 legal_not_confirmed:'Klasifikasi AI bukan penetapan pelanggaran hukum',
 team_national:'Nasional',team_provincial:'Provinsi',
 officer_queue:'Antrean departemen',loading:'Memeriksa sumber dan izin…',
 workload_mine:'Tugas saya',workload_open:'Kasus aktif',workload_reports:'Laporan menunggu tinjauan',
 evidence_refs:'sumber rujukan',source_review_required:'perlu verifikasi petugas',
 language_setting:'Bahasa jawaban mengikuti pertanyaan',
 work_prompt:'Mulai dari pekerjaan yang ingin diselesaikan',
 work_priorities:'Pilih prioritas',work_assign:'Siapkan penugasan',work_report:'Siapkan laporan',
 preparing:'Menyiapkan…',scope:'Sumber jawaban',
 analysis_mode:'Kedalaman analisis',date_unknown:'Tanggal tidak tersedia',
 source_unknown:'Sumber',positive:'Positif',neutral:'Netral',negative:'Negatif',unknown:'Belum diketahui',
};
const EN={
 findings_heading:'Key evidence-backed findings',finding_label:'Finding',needs_review:'Needs verification',
 verification_heading:'Recommended verification actions',
 review_notice:'AI findings are suggestions. Factual verification and formal decisions remain with authorized officers.',
 implications_heading:'Oversight implications',limitations_heading:'Evidence limitations',
 tags_heading:'Detected entities and issues',
 tags_notice:'AI-suggested tags from available sources; not a legal finding or confirmed jurisdiction.',
 candidate:'Candidate',province:'Province',suspected_violation:'Suspected violation',
 bawaslu_issue:'BAWASLU issue',electoral_issue:'Electoral issue',
 province_mention:'Province mentioned · incident location unconfirmed',
 suspected_only:'Preliminary signal · officer review required',
 stats_heading:'Conversation landscape in retrieved evidence',
 stats_intro:'Statistics come from relevant accessible posts. AI analysis uses a smaller evidence subset.',
 sample_note:'Retrieved sample · not a public-opinion survey',
 posts:'Posts in statistics',analysis_count:'posts analyzed by AI',
 engagement:'Recorded interactions',platforms:'Platforms found',date_range:'Date range',
 recorded_metrics:'with recorded metrics',valid_dates:'valid dates',sample_platforms:'Within the retrieved sample',
 sentiment_heading:'Post sentiment labels',
 platform_volume:'Post volume by platform',
 daily_activity:'Activity by publication date',
 platform_engagement:'Recorded engagement by platform',topics_heading:'Stored source topics',
 coverage_notice:'Figures describe retrieved posts—not unique people, voter preferences or all online discussion.',
 source_tags_note:'Topic labels come from stored classifications and may not have been verified by officers.',
 activity_note:'This is not a market-wide trend; it covers dated posts in this sample only.',
 metric_note:'Engagement is summed only for posts with stored metrics.',
 sources_heading:'Original posts and source evidence',
 sources_intro:'Selected for relevance to the question and timing, not simply high engagement. Sources still require verification.',
 original_source:'View original source',source_engagement:'interactions',no_engagement:'Engagement unavailable',
 prepare_from_source:'Create an assignment from this source',
 action_title:'I can prepare the next steps',
 action_intro:'Choose a relevant source. I will prepare an assignment, recommend a department and draft a report from this analysis. You review and confirm.',
 steps_title:'Prepared verification steps',step:'Step',
 sources_action_heading:'Evidence ready for assignment',prepare_task:'Prepare assignment & report',
 open_source:'Inspect source',prepare_review_title:'Assignment ready for review',
 not_saved_notice:'Nothing will be saved until you confirm.',
 department_suggestion:'Suggested department from source tags',province_safety:'A province mentioned in a source is not a verified incident jurisdiction.',draft_details_note:'Findings and verification steps will be copied into an editable draft, not a legal determination.',campaign_label:'Campaign',
 department_label:'Department',team_label:'Receiving team',officer_label:'Receiving officer (optional)',
 case_title_label:'Case title',primary_source_label:'Primary source',
 close:'Close',preview_draft:'Preview draft',hide_draft:'Hide draft preview',
 summary_label:'Executive summary (editable)',
 confirm_notice:'I have reviewed this proposal and want to save an assignment and draft report, not make a legal determination.',
 submit_action:'Create assignment + draft report',officer_only:'Your role cannot create assignments.',
 no_sources:'No directly assignable source was returned. Check relevant evidence in Intelligence Inbox.',
 no_extra_ai:'This action reuses the existing analysis without an additional AI request.',
 source_not_verified:'Source not independently verified',
 legal_not_confirmed:'AI relevance is not legal verification',
 team_national:'National',team_provincial:'Province',
 officer_queue:'Department queue',loading:'Checking source and permissions…',
 workload_mine:'Assigned to me',workload_open:'Open cases',workload_reports:'Reports awaiting review',
 evidence_refs:'supporting sources',source_review_required:'officer verification required',
 language_setting:'Answer language follows your question',
 work_prompt:'Start with the work you want to complete',
 work_priorities:'Identify priorities',work_assign:'Prepare assignments',work_report:'Prepare a report',
 preparing:'Preparing…',scope:'Answer source',
 analysis_mode:'Analysis depth',date_unknown:'Date unavailable',
 source_unknown:'Source',positive:'Positive',neutral:'Neutral',negative:'Negative',unknown:'Unknown',
};
export function assistantLocale(code){
 const language=String(code||'id').toLowerCase().split('-')[0];
 return language;
}
export function textFor(code,overrides,key){
 const language=assistantLocale(code);
 if(language==='id')return ID[key]||EN[key]||key;
 if(language==='en')return EN[key]||ID[key]||key;
 const translated=overrides&&typeof overrides==='object'&&overrides[key];
 if(typeof translated==='string'&&translated.trim())return translated;
 // No pretend translation for unsupported language: stable UI label fallback.
 return EN[key]||ID[key]||key;
}
export function friendlySource(text,code,overrides){
 const t=key=>textFor(code,overrides,key);
 return String(text||'')
  .replaceAll('UNVERIFIED_SOCIAL_SOURCE',t('source_not_verified'))
  .replaceAll('AI_RELEVANCE_NOT_LEGAL_VERIFICATION',t('legal_not_confirmed'))
  .replaceAll('AIR_RELEVANCE_NOT_LEGAL_VERIFICATION',t('legal_not_confirmed'));
}
export const localeTagKey={
 CANDIDATE:'candidate',PROVINCE:'province',SUSPECTED_VIOLATION:'suspected_violation',
 BAWASLU_ISSUE:'bawaslu_issue',ELECTORAL_ISSUE:'electoral_issue'
};
export const numberLocale=code=>({id:'id-ID',en:'en-US',es:'es-ES',fr:'fr-FR',pt:'pt-BR',de:'de-DE',
  ja:'ja-JP',ko:'ko-KR',zh:'zh-CN',ar:'ar',ru:'ru-RU',th:'th-TH'}[assistantLocale(code)]||'en-US');
