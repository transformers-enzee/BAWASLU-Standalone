/* Read-only BAWASLU prototype bridge.
   Findings, counts, and evidence derive exclusively from the fixed saved-assessment snapshot.
   No keyword-based fabrication of findings, verified violations or incident geography. */
(function(){
 'use strict';
 const snapshotElement=document.getElementById('bawaslu-demo-snapshot');
 const originalRows=JSON.parse(snapshotElement.textContent);
 // Match the live Inbox radar: one social source cannot inflate findings across campaigns.
 const seenSources=new Set();
 const rows=originalRows.filter(p=>{if(seenSources.has(p.sourceId))return false;seenSources.add(p.sourceId);return true;});
 const metaElement=document.getElementById('bawaslu-demo-metadata');
 const meta=metaElement?JSON.parse(metaElement.textContent):{campaigns:[],watchlist:[]};
 const originalFetch=window.fetch.bind(window);
 const json=(data,status=200)=>new Response(JSON.stringify(data),{status,headers:{'Content-Type':'application/json'}});
 const countBy=(rows,fn)=>{const out={};for(const p of rows){const key=String(fn(p)||'');if(key)out[key]=(out[key]||0)+1;}return out;};
 const topicID={ 'Public Concern':'Kekhawatiran Publik','Public Information':'Informasi Publik',
  'Electoral Operations':'Operasional Pemilu','Campaign Rules':'Aturan Kampanye',
  'BAWASLU Reputation':'Reputasi BAWASLU','Election Administration':'Administrasi Pemilu'};
 const enID=new Map(Object.entries(topicID));
 const watchlist=(meta.watchlist||[]).map(x=>({...x,geographic_scope:'Nationwide',candidate_aliases:x.candidate_aliases||[]}));
 const campaignList=meta.campaigns||[];
 const demoAccounts=[{"id":"DEMO-ACCOUNT-1","watchlist_id":"DEMO-WATCH-004","platform":"instagram","handle":"@gibran_rakabuming","url":""},{"id":"DEMO-ACCOUNT-2","watchlist_id":"DEMO-WATCH-002","platform":"tiktok","handle":"@aniesbaswedan","url":""},{"id":"DEMO-ACCOUNT-3","watchlist_id":"DEMO-WATCH-002","platform":"tiktok","handle":"@aniesbaswedan","url":""},{"id":"DEMO-ACCOUNT-4","watchlist_id":"DEMO-WATCH-002","platform":"tiktok","handle":"@aniesbaswedan","url":""},{"id":"DEMO-ACCOUNT-5","watchlist_id":"DEMO-WATCH-002","platform":"tiktok","handle":"@aniesbaswedan","url":""},{"id":"DEMO-ACCOUNT-6","watchlist_id":"DEMO-WATCH-002","platform":"instagram","handle":"@aniesbaswedan","url":""},{"id":"DEMO-ACCOUNT-7","watchlist_id":"DEMO-WATCH-005","platform":"instagram","handle":"@prabowo","url":""},{"id":"DEMO-ACCOUNT-8","watchlist_id":"DEMO-WATCH-003","platform":"instagram","handle":"@dedimulyadi71","url":""},{"id":"DEMO-ACCOUNT-9","watchlist_id":"DEMO-WATCH-003","platform":"tiktok","handle":"@dedimulyadiofficial","url":""},{"id":"DEMO-ACCOUNT-10","watchlist_id":"DEMO-WATCH-003","platform":"youtube","handle":"@KANGDEDIMULYADICHANNEL","url":""},{"id":"DEMO-ACCOUNT-11","watchlist_id":"DEMO-WATCH-006","platform":"tiktok","handle":"@purbayayudhis","url":""},{"id":"DEMO-ACCOUNT-12","watchlist_id":"DEMO-WATCH-005","platform":"facebook","handle":"@PrabowoSubianto","url":""}];
 const demoOwned=[{"id":"DEMO-OWN-001","watchlist_id":"DEMO-WATCH-004","account_id":"DEMO-ACCOUNT-1","platform":"instagram","author_name":"Gibran Rakabuming","published_at":"2026-09-30T13:29:07.000Z","text":"Menerima perwakilan jemaat Gereja Kristen Protestan Indonesia (GKPI) Rajeg di Jakarta untuk mendengar aspirasi jemaat yang beberapa waktu yang lalu mengalami pembubaran ibadah secara paksa.\n\nSaya berpesan agar jemaat tetap tenang dan menjaga suasana yang rukun juga kondusif. Kami pastikan, penyelesaian persoalan ini akan terus mengedepankan kerukunan, pengurusan perizinan sesuai ketentuan yang berlaku, serta komunikasi yang baik dengan masyarakat sekitar, untuk memastikan seluruh masyarakat dapat melaksanakan ibadah secara aman dan nyaman.","relation":"OWN_POST","saved_assessments":[]},{"id":"DEMO-OWN-002","watchlist_id":"DEMO-WATCH-004","account_id":"DEMO-ACCOUNT-1","platform":"instagram","author_name":"Gibran Rakabuming","published_at":"2026-09-29T13:18:45.000Z","text":"Saya memahami kekhawatiran orang tua terhadap kondisi kesehatan anak-anak mereka. Oleh karena itu, saya harus menemui para orang tua, dan menyampaikan permohonan maaf secara langsung, sekaligus memastikan bahwa seluruh anak-anak yang terdampak keracunan makanan di SDN Pasusukan, Kecamatan Bawang mendapatkan penanganan yang diperlukan.\n\nSaya pastikan setiap keluhan keluarga akan ditindaklanjuti, investigasi segera dituntaskan dan hasilnya disampaikan secara terbuka kepada keluarga korban, serta pengawasan diperkuat agar kejadian serupa tidak terulang.","relation":"OWN_POST","saved_assessments":[]},{"id":"DEMO-OWN-003","watchlist_id":"DEMO-WATCH-004","account_id":"DEMO-ACCOUNT-1","platform":"instagram","author_name":"Gibran Rakabuming","published_at":"2026-09-29T06:31:09.000Z","text":"Saya memastikan seluruh korban yang terdampak keracunan makanan di Kabupaten Batang mendapatkan penanganan medis secara optimal hingga benar-benar pulih tanpa terbebani biaya pengobatan.\n\nSekali lagi, saya menghanturkan permohonan maaf untuk anak-anak dan keluarga yang terdampak, saya akan memastikan setiap pasien mendapatkan pelayanan sesuai kebutuhan medis dan tidak akan dipulangkan sebelum kondisinya benar benar pulih.","relation":"OWN_POST","saved_assessments":[]},{"id":"DEMO-OWN-004","watchlist_id":"DEMO-WATCH-004","account_id":"DEMO-ACCOUNT-1","platform":"instagram","author_name":"Gibran Rakabuming","published_at":"2026-09-28T12:13:24.000Z","text":"Bertolak ke Kabupaten Batang, Jawa Tengah untuk memastikan korban dugaan keracunan makanan mendapat penanganan yang terbaik.\n\nSeiring dengan investigasi yang tengah berjalan, seluruh pasien yang masih menjalani pengobatan harus mendapatkan pelayanan hingga pulih tanpa biaya yang membebani keluarga. Saya meminta investigasi dilakukan secara menyeluruh dan transparan, disertai dengan evaluasi menyeluruh terhadap pelaksanaan program, dan pengawasan keamanan pangan.","relation":"OWN_POST","saved_assessments":[]},{"id":"DEMO-OWN-005","watchlist_id":"DEMO-WATCH-004","account_id":"DEMO-ACCOUNT-1","platform":"instagram","author_name":"Gibran Rakabuming","published_at":"2026-09-27T13:15:22.000Z","text":"Datang ke kediaman keluarga almarhum Dafi Arahman, korban banjir bandang yang terjadi di Kabupaten Solok beberapa waktu lalu.\n\nSaya juga sempat melakukan panggilan video dengan Affan Alqadri, kakak almarhum yang sedang menjalani perawatan di RSUP Dr. M. Djamil, Padang.\n\nDi tengah penanganan bencana, negara tidak hanya memastikan kebutuhan darurat warga terpenuhi, namun juga memberikan perhatian kepada keluarga korban juga masyarakat yang terdampak lewat pemenuhan kebutuhan dasar, serta peningkatan kewaspadaan terhadap potensi hujan dan longsor susulan agar masyarakat tetap terlindungi.","relation":"OWN_POST","saved_assessments":[]},{"id":"DEMO-OWN-006","watchlist_id":"DEMO-WATCH-004","account_id":"DEMO-ACCOUNT-1","platform":"instagram","author_name":"Gibran Rakabuming","published_at":"2026-09-27T10:44:29.000Z","text":"Menunaikan salat Jumat bersama warga terdampak banjir bandang di Masjid Raya Al Mukarramah, Koto Gaek Guguak, Kabupaten Solok.\n\nUsai salat, saya makan siang bersama warga sambil berdialog untuk mendengarkan aspirasi dan menyerap kebutuhan masyarakat dalam proses penanganan pascabencana agar masyarakat dapat kembali menjalani aktivitas dengan aman dan nyaman.","relation":"OWN_POST","saved_assessments":[]},{"id":"DEMO-OWN-007","watchlist_id":"DEMO-WATCH-004","account_id":"DEMO-ACCOUNT-1","platform":"instagram","author_name":"Gibran Rakabuming","published_at":"2026-09-27T07:58:02.000Z","text":"Penanganan medis bagi para korban yang terdampak banjir bandang di Kabupaten Solok harus dilakukan secara tuntas. Seiring dengan upaya antisipasi munculnya berbagai penyakit pasca banjir melalui kesiapan obat-obatan, pemberian vitamin, serta penguatan pelayanan kesehatan bagi masyarakat terdampak.\n\nKoordinasi antara pemerintah pusat, pemerintah daerah dan tenaga kesehatan harus terus diperkuat agar pelayanan kesehatan dapat menjangkau warga yang berada di posko maupun lokasi pengungsian mandiri, dengan memberikan perhatian khusus kepada kelompok rentan seperti ibu hamil, lansia dan penyandang disabilititas. Agar kebutuhan medis mereka dapat terpenuhi secara baik.","relation":"OWN_POST","saved_assessments":[]},{"id":"DEMO-OWN-008","watchlist_id":"DEMO-WATCH-004","account_id":"DEMO-ACCOUNT-1","platform":"instagram","author_name":"Gibran Rakabuming","published_at":"2026-09-27T04:33:29.000Z","text":"Di Posko Utama Penanggulangan Bencana Kabupaten Solok, Sumatra Barat, saya menekankan bahwa penguatan koordinasi dan konsolidasi seluruh unsur akan menjadi prioritas agar penanganan di setiap wilayah terdampak bencana dapat dilakukan secara optimal.\n\nSaya juga meminta unsur Forkopimda dan perwakilan pemerintah pusat untuk memaksimalkan pemenuhan kebutuhan dasar para pengungsi, pembersihan material banjir guna memulihkan akses dan aktivitas masyarakat, serta meningkatkan kewaspadaan terhadap potensi hujan.","relation":"OWN_POST","saved_assessments":[]},{"id":"DEMO-OWN-009","watchlist_id":"DEMO-WATCH-004","account_id":"DEMO-ACCOUNT-1","platform":"instagram","author_name":"Gibran Rakabuming","published_at":"2026-09-26T13:42:34.000Z","text":"Di tengah masa tanggap darurat, perhatian utama harus diarahkan kepada perlindungan dan pemenuhan kebutuhan warga terdampak.\n\nDi Posko Pengungsi Balai Pemuda Kayu Aro, Saya berdialog dengan warga, sekaligus memastikan penanganan pasca bencana seperti pembangunan kembali rumah yang rusak, dan pengurusan dokumen kependudukan yang hilang dapat dilakukan dengan cepat, dan sesuai dengan kebutuhan agar masyarakat dapat kembali beraktivitas dengan aman.","relation":"OWN_POST","saved_assessments":[]},{"id":"DEMO-OWN-010","watchlist_id":"DEMO-WATCH-004","account_id":"DEMO-ACCOUNT-1","platform":"instagram","author_name":"Gibran Rakabuming","published_at":"2026-09-26T11:37:30.000Z","text":"Di Kabupaten Solok, Sumatera Barat. Saya meninjau langsung sejumlah infrastruktur dan fasilitas publik yang terdampak banjir bandang, agar penanganan pascabencana berjalan dengan cepat, terkoordinasi, dan sesuai dengan kebutuhan masyarakat.\n\nSaya terus mendorong percepatan perbaikan akses utama, termasuk jalan dan Jembatan Arosuka, disusul dengan pemulihan permukiman, lahan pertanian, masjid, fasilitas umum, serta infrastruktur lainnya agar mobilitas masyarakat dapat kembali berjalan dengan aman.","relation":"OWN_POST","saved_assessments":[]},{"id":"DEMO-OWN-011","watchlist_id":"DEMO-WATCH-004","account_id":"DEMO-ACCOUNT-1","platform":"instagram","author_name":"Gibran Rakabuming","published_at":"2026-09-20T11:37:45.000Z","text":"Saya menyampaikan rasa terima kasih dan apresiasi kepada Tim Dokter RSCM (Prof. Dr. dr. Setyo Handryastuti, Sp.A(K), Prof. Dr. dr. Tjhin Wiguna, Sp.KJ(K), Prof. Dr. dr. Rinawati Rohsiswanto, Sp.A(K), dr. Fatima Safira Alatas, Sp.A(K), Dr. dr. Kristiana Siste, Sp.KJ(K)), Kemenkes, Dinkes Sumut  serta seluruh pihak yang telah terlibat dalam proses rujukan, perawatan, hingga pemulihan Agnesia dan Febiona.\n\nSaat ini Agnesia dan Febiona telah kembali ke rumah masing-masing di Kab. Karo dan akan masuk sekolah kembali.\n\nPerkataan oknum SPPG ini sangat disayangkan. Mari kita bersama menjaga ruang publik yang aman dan ramah bagi semua. Jangan sampai anak-anak justru menjadi korban perundungan.","relation":"OWN_POST","saved_assessments":[]},{"id":"DEMO-OWN-012","watchlist_id":"DEMO-WATCH-004","account_id":"DEMO-ACCOUNT-1","platform":"instagram","author_name":"Gibran Rakabuming","published_at":"2026-09-19T02:40:50.000Z","text":"Pertemuan saya dengan Deputi Perdana Menteri sekaligus Menteri Kemajuan Desa dan Wilayah Malaysia Dato’ Seri Dr. Ahmad Zahid Hamidi di Jakarta, Kamis (17/9/2026) kemarin membahas tentang penguatan kerjasama strategis Indonesia-Malaysia dalam industri halal, pembangunan kawasan pedesaan, hingga perlindungan Pekerja Migran Indonesia (PMI).\n\nSaya juga mendorong dengan positif percepatan pembentukan ASEAN Halal Council, pertukaran pengalaman dan praktik baik dalam pembangunan pedesaan, perlindungan yang baik untuk PMI di Malaysia, dan perluasan kesempatan kerja pada sektor formal, khususnya bagi tenaga kerja dengan keterampilan menengah dan tinggi.","relation":"OWN_POST","saved_assessments":[]},{"id":"DEMO-OWN-013","watchlist_id":"DEMO-WATCH-002","account_id":"DEMO-ACCOUNT-2","platform":"tiktok","author_name":"Anies Rasyid Baswedan","published_at":"2026-10-14T05:24:31.000Z","text":"Di Singapura sudah tidak ada hutan dan tidak ada kebakaran kok bisa seluruh Singapura tertutup asap?","relation":"OWN_POST","saved_assessments":[]},{"id":"DEMO-OWN-014","watchlist_id":"DEMO-WATCH-002","account_id":"DEMO-ACCOUNT-2","platform":"tiktok","author_name":"Anies Rasyid Baswedan","published_at":"2026-10-21T05:30:07.000Z","text":"Pencegahan mungkin kurang 'heroik'. Tapi, mau sampai kapan?","relation":"OWN_POST","saved_assessments":[]},{"id":"DEMO-OWN-015","watchlist_id":"DEMO-WATCH-002","account_id":"DEMO-ACCOUNT-2","platform":"tiktok","author_name":"Anies Rasyid Baswedan","published_at":"2026-05-22T11:00:01.000Z","text":"Sesuai request, silahkan dimanfaatkan ya templatenya. :) #CapCut","relation":"OWN_POST","saved_assessments":[]},{"id":"DEMO-OWN-016","watchlist_id":"DEMO-WATCH-002","account_id":"DEMO-ACCOUNT-2","platform":"tiktok","author_name":"Anies Rasyid Baswedan","published_at":"2026-11-01T05:12:56.000Z","text":"Boleh berbeda pendapat, tapi jangan berbeda dalam kejujuran 🇮🇩 Selamat berakhir pekan","relation":"OWN_POST","saved_assessments":[]},{"id":"DEMO-OWN-017","watchlist_id":"DEMO-WATCH-002","account_id":"DEMO-ACCOUNT-2","platform":"tiktok","author_name":"Anies Rasyid Baswedan","published_at":"2026-10-31T05:28:52.000Z","text":"Hak perempuan bukan bonus. Ia adalah hak yg harus dijamin.  Dari pendidikan hingga kebutuhan dasar, tak boleh ada perempuan yang tertinggal hanya karena keterbatasan akses.  Sebab, memuliakan perempuan berarti memuliakan kemanusiaan.","relation":"OWN_POST","saved_assessments":[]},{"id":"DEMO-OWN-018","watchlist_id":"DEMO-WATCH-002","account_id":"DEMO-ACCOUNT-2","platform":"tiktok","author_name":"Anies Rasyid Baswedan","published_at":"2026-10-30T10:57:26.000Z","text":"Mari aktif di dalam menyuarakan akal sehat, kebenaran dan hati nurani. Bersuaralah..","relation":"OWN_POST","saved_assessments":[]},{"id":"DEMO-OWN-019","watchlist_id":"DEMO-WATCH-002","account_id":"DEMO-ACCOUNT-2","platform":"tiktok","author_name":"Anies Rasyid Baswedan","published_at":"2026-10-28T04:56:55.000Z","text":"Selamat Hari Sumpah Pemuda. 🇮🇩 Gantian sekarang kalian mau nyumpah apa?","relation":"OWN_POST","saved_assessments":[]},{"id":"DEMO-OWN-020","watchlist_id":"DEMO-WATCH-002","account_id":"DEMO-ACCOUNT-2","platform":"tiktok","author_name":"Anies Rasyid Baswedan","published_at":"2026-10-27T12:46:42.000Z","text":"Coba pakai sound hibernasi.. Kok rasanya lumayan sesusi ya. 😃","relation":"OWN_POST","saved_assessments":[]},{"id":"DEMO-OWN-021","watchlist_id":"DEMO-WATCH-002","account_id":"DEMO-ACCOUNT-2","platform":"tiktok","author_name":"Anies Rasyid Baswedan","published_at":"2026-10-27T06:19:17.000Z","text":"By the way itu saya yang ngomong. Hehe. Ib @ntsana","relation":"OWN_POST","saved_assessments":[]},{"id":"DEMO-OWN-022","watchlist_id":"DEMO-WATCH-002","account_id":"DEMO-ACCOUNT-2","platform":"tiktok","author_name":"Anies Rasyid Baswedan","published_at":"2026-10-26T10:55:30.000Z","text":"Begitu katanya ciri-ciri orang yang namanya berawalan huruf R. Saya ikutan deh 😅","relation":"OWN_POST","saved_assessments":[]},{"id":"DEMO-OWN-023","watchlist_id":"DEMO-WATCH-005","account_id":"DEMO-ACCOUNT-7","platform":"instagram","author_name":"Prabowo Subianto","published_at":"2026-10-28T11:23:05.000Z","text":"Sumpah Pemuda\n\n1. Kami Putra dan Putri Indonesia, mengaku bertumpah darah yang satu, tanah air Indonesia.\n2. Kami Putra dan Putri Indonesia, mengaku berbangsa yang satu, bangsa Indonesia.\n3. Kami Putra dan Putri Indonesia, menjunjung bahasa persatuan, bahasa Indonesia.","relation":"OWN_POST","saved_assessments":[]},{"id":"DEMO-OWN-024","watchlist_id":"DEMO-WATCH-005","account_id":"DEMO-ACCOUNT-7","platform":"instagram","author_name":"Prabowo Subianto","published_at":"2026-10-12T16:37:42.000Z","text":"Selamat memperingati Hari Museum Indonesia, 12 Oktober 2026.","relation":"OWN_POST","saved_assessments":[]},{"id":"DEMO-OWN-025","watchlist_id":"DEMO-WATCH-005","account_id":"DEMO-ACCOUNT-12","platform":"facebook","author_name":"Prabowo Subianto","published_at":"2026-10-30T12:47:07.000Z","text":"Menerima para atlet kebanggaan Indonesia yang telah berjuang mengharumkan nama bangsa pada Asian Games ke-20 dan Asian Para Games ke-5 Aichi-Nagoya 2026 di Istana Merdeka, Jakarta.\n\nSaya menyampaikan rasa bangga, penghargaan, dan terima kasih yang sebesar-besarnya kepada seluruh atlet, pelatih, serta seluruh anggota kontingen Indonesia yang telah berjuang dengan penuh semangat, disiplin, dan dedikasi hingga berhasil mempersembahkan 39 medali pada Asian Games dan 73 medali pada Asian Para Games.\n\nDi balik setiap medali, ada kerja keras, pengorbanan, dan semangat pantang menyerah. Prestasi ini bukan hanya kebanggaan bagi para atlet, tetapi juga kehormatan bagi seluruh rakyat Indonesia.\n\nSaya berharap pencapaian ini menjadi motivasi bagi kita semua untuk terus memperkuat pembinaan olahraga nasional, melahirkan lebih banyak atlet unggul, dan membawa Indonesia meraih prestasi yang semakin tin","relation":"OWN_POST","saved_assessments":[]},{"id":"DEMO-OWN-026","watchlist_id":"DEMO-WATCH-005","account_id":"DEMO-ACCOUNT-12","platform":"facebook","author_name":"Prabowo Subianto","published_at":"2026-10-28T11:33:47.000Z","text":"Sumpah Pemuda:\n\nSatu, kami putra dan putri Indonesia, mengaku bertumpah darah yang satu, tanah air Indonesia.\n\nDua, kami putra dan putri Indonesia, mengaku berbangsa yang satu, bangsa Indonesia.\n\nTiga, kami putra dan putri Indonesia, menjunjung bahasa persatuan, bahasa Indonesia.","relation":"OWN_POST","saved_assessments":[]},{"id":"DEMO-OWN-027","watchlist_id":"DEMO-WATCH-006","account_id":"DEMO-ACCOUNT-11","platform":"tiktok","author_name":"Purbaya Yudhi Sadewa","published_at":"2025-09-27T07:24:01.000Z","text":"Gen Z, Gaskeun 👍👍👍 #purbayayudhisadewa","relation":"OWN_POST","saved_assessments":[]},{"id":"DEMO-OWN-028","watchlist_id":"DEMO-WATCH-006","account_id":"DEMO-ACCOUNT-11","platform":"tiktok","author_name":"Purbaya Yudhi Sadewa","published_at":"2025-09-27T06:28:55.000Z","text":"Terima kasih teman teman Gen Z atas doa yang diberikan kepada saya.  Terima kasih dukungannya, saya akan pastikan doa anda akan terkabul, kita sama-sama menjadi kaya bersama.  Gen Z jangan takut, Indonesia Akan Cerah. 👍🙏 #purbayayudhisadewa","relation":"OWN_POST","saved_assessments":[]},{"id":"DEMO-OWN-029","watchlist_id":"DEMO-WATCH-006","account_id":"DEMO-ACCOUNT-11","platform":"tiktok","author_name":"Purbaya Yudhi Sadewa","published_at":"2026-10-05T05:19:03.000Z","text":"Hari minggu kemarin, Sarapan Kupat Tahu Gempol Bandung, Mantap 👍👍👍 #purbayayudhisadewa #pys","relation":"OWN_POST","saved_assessments":[]},{"id":"DEMO-OWN-030","watchlist_id":"DEMO-WATCH-006","account_id":"DEMO-ACCOUNT-11","platform":"tiktok","author_name":"Purbaya Yudhi Sadewa","published_at":"2026-09-16T08:48:06.000Z","text":"Ngasih makan ikan. Sebelum mancing. Siapa yang mau ikut mancing bareng? Ikan nya besar-besar, ada ikan mujaer, ikan nila.  Bakal strike ini. Siap-siap ya Guys. #purbayayudhisadewa #pys","relation":"OWN_POST","saved_assessments":[]},{"id":"DEMO-OWN-031","watchlist_id":"DEMO-WATCH-006","account_id":"DEMO-ACCOUNT-11","platform":"tiktok","author_name":"Purbaya Yudhi Sadewa","published_at":"2026-09-14T11:43:22.000Z","text":"Udah siap belum? 😃😃😃 #purbayayudhisadewa #pys","relation":"OWN_POST","saved_assessments":[]},{"id":"DEMO-OWN-032","watchlist_id":"DEMO-WATCH-006","account_id":"DEMO-ACCOUNT-11","platform":"tiktok","author_name":"Purbaya Yudhi Sadewa","published_at":"2026-09-12T07:24:14.000Z","text":"Happy weekend guys. Kalian pada kemana? Jangan lupa ngopi ya #purbayayudhisadewa #menkeu #kitakayabersama","relation":"OWN_POST","saved_assessments":[]},{"id":"DEMO-OWN-033","watchlist_id":"DEMO-WATCH-006","account_id":"DEMO-ACCOUNT-11","platform":"tiktok","author_name":"Purbaya Yudhi Sadewa","published_at":"2026-09-11T03:46:19.000Z","text":"Selamat Pagi Guys Besok udah weekend lagi. Sudah ada rencana kalian mau weekend kemana? #purbayayudhisadewa #menkeu #kitakayabersama","relation":"OWN_POST","saved_assessments":[]},{"id":"DEMO-OWN-034","watchlist_id":"DEMO-WATCH-006","account_id":"DEMO-ACCOUNT-11","platform":"tiktok","author_name":"Purbaya Yudhi Sadewa","published_at":"2026-09-10T06:05:40.000Z","text":"Udah lama ga pake Mercy Lama. Waktu kerja di Danarekasa. Awet, masih ada. Masih bagus dan ganteng. Lumayan gas tipis-tipis dari Rumah ke Kantor. Coming soon ya Part 2 nya. #purbayayudhisadewa #menkeu #kitakayabersama","relation":"OWN_POST","saved_assessments":[]},{"id":"DEMO-OWN-035","watchlist_id":"DEMO-WATCH-006","account_id":"DEMO-ACCOUNT-11","platform":"tiktok","author_name":"Purbaya Yudhi Sadewa","published_at":"2026-09-08T12:42:36.000Z","text":"Siang tadi bertemu Menteri Pertanian Pak Amran di Kantor Kemenkeu. Membahas sejumlah program strategis di bidang Pertanian. #purbayayudhisadewa #menkeu #kitakayabersama","relation":"OWN_POST","saved_assessments":[]},{"id":"DEMO-OWN-036","watchlist_id":"DEMO-WATCH-006","account_id":"DEMO-ACCOUNT-11","platform":"tiktok","author_name":"Purbaya Yudhi Sadewa","published_at":"2026-09-04T09:26:10.000Z","text":"Iseng-iseng Join Trend Spiderman. Siapa disini yang udah nonton film Spider-Man: Brand New Day? #purbayayudhisadewa #menkeu #kitakayabersama","relation":"OWN_POST","saved_assessments":[]}];
 const normalizeCandidate=value=>{
  const s=String(value||'').trim();
  if(/gibran/i.test(s))return 'Gibran Rakabuming Raka';
  if(/prabowo/i.test(s))return 'Prabowo Subianto';
  if(/anies|anis baswedan/i.test(s))return 'Anies Baswedan';
  if(/ganjar/i.test(s))return 'Ganjar Pranowo';
  if(/cak imin|muhaimin/i.test(s))return 'Muhaimin Iskandar';
  if(/jokowi|joko widodo/i.test(s))return 'Joko Widodo';
  if(/ahok/i.test(s))return 'Ahok';
  return s;
 };
 // Replicate the live Inbox's source-first interpretation: an unanchored
 // topical mention is source awareness, NOT an invented recurring incident.
 const anchors={
  'Voter register accuracy':['daftar pemilih','pdpb','daftar pemilih tetap'],
  'Election money politics':['politik uang','serangan fajar'],
  'BAWASLU institutional trust':['reputasi bawaslu','kepercayaan publik terhadap bawaslu','kritik terhadap bawaslu','citra bawaslu','bawaslu tidak netral','bawaslu berpihak'],
  'Election dispute proceedings':['sengketa pemilu','sengketa pilkada','putusan dkpp'],
  'Candidate nomination process':['proses pencalonan','pendaftaran calon','verifikasi calon'],
  'Participatory election oversight':['pengawasan partisipatif','pengawas partisipatif']
 };
 const anchorFor=value=>{
  const text=String(value||'').toLocaleLowerCase('id-ID');
  if(['selamat hari','sumpah pemuda','dirgahayu','selamat ulang tahun','ucapan selamat','memperingati hari'].some(t=>text.includes(t))&&!['pelanggaran','dugaan','laporan','pengawasan pemilu','sengketa','kecurangan'].some(t=>text.includes(t)))return '';
  return Object.entries(anchors).find(([,terms])=>terms.some(term=>text.includes(term)))?.[0]||'';
 };
 const classify=p=>{
   // These are recorded assessment signals, NOT legal or officer findings.
   if((p.signals||[]).length)return {kind:'source_review',player:'violations',name:'Saved potential issue',id:'Potensi isu tersimpan',key:'violation:'+p.sourceId};
   if((p.concerns||[]).length){
    const topic=String(p.topics?.[0]||'');
    return {kind:'discussion',player:'concerns',name:'Monitored public discussion',id:'Percakapan publik terpantau',key:'concern:'+(topic||p.sourceId)};
   }
   const anchor=anchorFor(p.text);
   if(anchor)return {kind:'narrative_candidate',player:'narratives',name:'Topic-based discussion · '+anchor,id:'Percakapan berdasarkan topik · '+anchor,key:'narrative:'+anchor};
   return {kind:'source_awareness',player:null,name:'Relevant source for officer review',id:'Sumber relevan untuk ditinjau petugas',key:'awareness:'+p.sourceId};
 };
 const inOperations=p=>(p.signals||[]).length>0||(p.topics||[]).includes('Electoral Operations')||(!(p.topics||[]).includes('BAWASLU Reputation')&&!(p.concerns||[]).length);
 const inReputation=p=>(p.topics||[]).includes('BAWASLU Reputation')||((p.concerns||[]).length>0&&!(p.signals||[]).length);
 let reviews={};
 function assemble(){
  const groups=new Map();
  for(const p of rows){
   const cat=classify(p),group=groups.get(cat.key)||{code:cat,rows:[]};
   group.rows.push(p);groups.set(cat.key,group);
  }
  const findings=[...groups.values()].map((g,i)=>{
   const records=g.rows,cat=g.code,topic=records[0]?.topics?.[0]||'';
   const topicName=cat.player==='violations'?String(records[0]?.signals?.[0]?.category||'Election Administration'):topic;
   const title=cat.name+(topicName?': '+topicName:'');
   const titleId=cat.id+(topicName?': '+(topicID[topicName]||topicName):'');
   const n=records.length;
   const summary=cat.player==='violations'?'Saved assessment records describe a reported issue. The allegation requires independent officer verification.':
     cat.player==='concerns'?n+' saved relevant posts contain public-concern signals; these are unverified source claims.':
     cat.player==='narratives'?n+' saved relevant posts share the topic '+topicName+'. This is a discussion pattern, not a verified incident.':
     'This relevant source is available for officer review; its topic was not established by the saved assessment.';
   const summaryId=cat.player==='violations'?'Penilaian tersimpan mencatat isu yang dilaporkan. Dugaan memerlukan verifikasi independen oleh petugas.':
     cat.player==='concerns'?n+' unggahan relevan tersimpan memuat sinyal kekhawatiran publik; klaim sumber ini belum terverifikasi.':
     cat.player==='narratives'?n+' unggahan relevan tersimpan memiliki topik '+(topicID[topicName]||topicName)+'. Ini pola percakapan, bukan kejadian terverifikasi.':
     'Sumber relevan ini tersedia untuk ditinjau petugas; topiknya belum ditetapkan dalam penilaian tersimpan.';
   enID.set(title,titleId);enID.set(summary,summaryId);
   const actors={};for(const p of records)for(const raw of p.candidates||[]){const name=normalizeCandidate(raw);if(name)actors[name]=(actors[name]||0)+1;}
   const key='INBOX-DEMO-'+i;
   const result={id:key,kind:cat.kind,title,summary,ai_summary:false,ai_model:'',
    perspectives:[...(records.some(inOperations)?['operations']:[]),...(records.some(inReputation)?['reputation']:[])],
    players:cat.player?[cat.player]:[],topics:[...new Set(records.flatMap(p=>p.topics||[]))],
    status:reviews[key]||((cat.player==='violations'||cat.player==='concerns')?'pending':'awareness'),
    published_at:records.map(p=>p.date||'').sort().slice(-1)[0]||'',
    source_ids:records.map(p=>p.sourceId),supporting_posts:n,
    human_reviewed:reviews[key]==='reviewed',source_evidence_verified:false,
    review_suggested:cat.player==='violations'||cat.player==='concerns',
    review_basis:'Saved Inbox assessment, officer triage required',
    sentiment_counts:countBy(records,p=>p.sentiment||'UNCLASSIFIED'),
    platform_counts:countBy(records,p=>p.platform),
    day_counts:countBy(records,p=>String(p.date||'').slice(0,10)),
    actor_mentions:actors,geo_signal_counts:{},verified_incident_counts:{},province_breakdown:{},
    priority_score:null,priority_label:'Not AI-scored',next_followup:'',
    insights:{operations:summary,reputation:summary},summary_id:summaryId,
    recurring_discussion:records.length>=2,source_assessment_versions:records.map(p=>({source_id:p.sourceId,assessment_version:p.assessmentVersion||1}))};
   return {...result,records};
  });
  return findings.sort((a,b)=>Number(b.status==='pending')-Number(a.status==='pending')||b.supporting_posts-a.supporting_posts);
 }
 const evidence=p=>({
   canonical_source_id:p.sourceId,account_raw:p.author||'Sumber publik contoh',
   published_at_raw:p.date||'',message_original:p.text||'',platform:p.platform||'',
   source_url:'',sentiment:p.sentiment||'UNCLASSIFIED',source_verification_status:'SAVED_INBOX_ASSESSMENT_UNVERIFIED',
   geographic_mentions_unverified:[],verified_incident_province:'',candidate_names:p.candidates||[],
   original_category_hint:(p.topics||[]).join(', '),review_status:p.reviewState||'UNREVIEWED'
 });
 const candidates=()=>{
  const c={};for(const p of rows)for(const raw of p.candidates||[]){
   const name=normalizeCandidate(raw);if(name)c[name]=(c[name]||0)+1;
  }return Object.entries(c).sort((a,b)=>b[1]-a[1]).slice(0,10);
 };
 const cloud=()=>{
  const words=[...new Set(campaignList.flatMap(c=>c.primary_keywords||[]))].filter(w=>w.length>=3);
  return words.map(keyword=>({keyword,count:rows.filter(p=>String(p.text||'').toLowerCase().includes(keyword.toLowerCase())).length}))
   .filter(x=>x.count).sort((a,b)=>b.count-a.count).slice(0,24);
 };
 const publicFindings=()=>assemble().map(({records,...f})=>f);
 function payload(){
   const findings=publicFindings();
   return {batch_id:null,source_total:rows.length,source_unique_urls:0,
    findings,platform_counts:countBy(rows,p=>p.platform),candidate_mentions:candidates(),
    main_keyword_cloud:cloud(),sentiment_counts:countBy(rows,p=>p.sentiment||'UNCLASSIFIED'),
    geo_signal_counts:{},verified_incident_counts:{},
    watchlist_profiles:watchlist,watchlist_source:'SAVED_PRODUCTION_DERIVED_SNAPSHOT',
    reviewed_total:findings.filter(x=>x.human_reviewed).length,
    mode:'SAVED_INBOX_SOURCE_OF_TRUTH',scoring_ready:false,
    feed_source:'FIXED_SAVED_ASSESSMENTS',inbox_source_scope:'APPROVED_RELEVANT_SNAPSHOT',snapshot_as_of:'2026-11-03',
    inbox_window_limit:300,truncated_to_inbox_window:originalRows.length>=300,
    sentiment_coverage:{classified:rows.filter(x=>['POSITIVE','NEGATIVE','NEUTRAL'].includes(x.sentiment)).length,
      unclassified:rows.filter(x=>!['POSITIVE','NEGATIVE','NEUTRAL'].includes(x.sentiment)).length},
    geographic_scope_note:'No verified incident provinces inferred from source profiles.',
    disclaimer:'Read-only training snapshot of saved assessments. No legal verdict or source verification implied.',
    jurisdictions:[],timezone:'Asia/Jakarta',paid_provider_called:false};
 }
 function distribution(){
   const groups={};
   for(const p of rows){
     const label=p.topics?.[0]||((p.concerns||[]).length?'Public Concern':'Other');
     if(!groups[label])groups[label]=[];
     groups[label].push(p);
   }
   const sorted=Object.entries(groups).sort((a,b)=>b[1].length-a[1].length);
   const topics=sorted.slice(0,5).map(([label,rs],i)=>{
     const title=label==='Other'?'Other saved relevant sources':label;
     enID.set(title,label==='Other'?'Sumber relevan tersimpan lainnya':(topicID[label]||label));
     return {id:i+1,title,count:rs.length,sentiment:Object.entries(countBy(rs,p=>p.sentiment)).sort((a,b)=>b[1]-a[1])[0]?.[0]||'NEUTRAL',
       description:'Saved AI topic classifications; verify original evidence.'};
   });
   enID.set('Saved AI topic classifications; verify original evidence.','Klasifikasi topik AI tersimpan; periksa bukti asli.');
   return {operations:{topics,others:sorted.slice(5).reduce((n,x)=>n+x[1].length,0),total:rows.length,refresh_pending:false},
     reputation:{topics,others:sorted.slice(5).reduce((n,x)=>n+x[1].length,0),total:rows.length,refresh_pending:false}};
 }
 function request(path,method,opts){
   const u=new URL(path,location.origin),p=u.pathname;
   if(p==='/api/smart-radar/dashboard')return payload();
   if(p==='/api/smart-radar/issue-distribution')return distribution();
   if(p==='/api/smart-radar/issue-distribution/posts'){
     const ids=Object.entries(rows.reduce((a,x)=>{const key=x.topics?.[0]||((x.concerns||[]).length?'Public Concern':'Other');(a[key]??=[]).push(x);return a},{})).sort((a,b)=>b[1].length-a[1].length);
     const index=Math.max(0,Number(u.searchParams.get('topic_id')||1)-1);
     const found=ids[index]?.[1]||[];
     return {total:found.length,posts:found.slice(0,100).map(p=>({title:p.text.slice(0,110),text:p.text,platform:p.platform,published_at:p.date}))};
   }
   if(p.startsWith('/api/smart-radar/finding/')){
     const id=decodeURIComponent(p.split('/').pop()),f=assemble().find(x=>x.id===id);
     if(!f)return {detail:'Finding not in fixed snapshot'};
     const {records,...head}=f;return {...head,posts:records.map(evidence)};
   }
   if(p.startsWith('/api/smart-radar/history/'))return {events:[]};
   if(p==='/api/smart-radar/decision'){
     try{const body=JSON.parse(opts?.body||'{}');reviews[String(body.finding_id||'')]='reviewed'}catch(_){}
     return {ok:true,demo:true};
   }
   if(p==='/api/functions/registry'){
     let body={};try{body=JSON.parse(opts?.body||'{}')}catch(_){}
     if(body.action==='list')return {items:watchlist,accounts:demoAccounts,sources:[],categories:[],relationships:[]};
     if(body.action==='myAccess')return {access:{status:'Active',permissions:{view_intelligence:true,manage_watchlist:true,human_validation:true},geographic_scope:'Nationwide'}};
     if(body.action==='watchlistCapturedFeed'){
       const selected=watchlist.find(x=>String(x.id)===String(body.id||'')),name=String(selected?.name||'').toLowerCase();
       const campaign=String(body.data?.campaign_id||'');
       const own=demoOwned.filter(p=>String(p.watchlist_id)===String(selected?.id||''));
       const ownIds=new Set(own.map(p=>p.id));
       const earned=name?rows.filter(p=>(p.candidates||[]).some(x=>normalizeCandidate(x).toLowerCase()===name)&&
         (!campaign||String(p.campaignId)===campaign)&&!ownIds.has(p.id)):[];
       const others=earned.map(p=>({id:p.id,platform:p.platform,author_name:p.author,published_at:p.date,text:p.text,relation:'THIRD_PARTY_MENTION',saved_assessments:[{sentiment:p.sentiment,assessment_version:p.assessmentVersion}]}));
       // Keep own-account evidence independent of campaign mentions. The original
       // live registry also permits registered-account posts beyond campaign links.
       const unique=new Map([...own,...others].map(p=>[p.id,p]));
       const all=[...unique.values()].sort((a,b)=>String(b.published_at||'').localeCompare(String(a.published_at||'')));
       const page=Math.max(1,Number(body.data?.page||1)),size=50,offset=(page-1)*size;
       return {posts:all.slice(offset,offset+size),total:all.length,own_posts:own.length,mentions_by_others:others.length,
         linked_accounts:demoAccounts.filter(a=>a.watchlist_id===selected?.id).length,paid_provider_called:false};
     }
     if(body.action==='watchlistSyncStatus')return {enabled:false,manual_fetch_available:false,accounts:[]};
     if(body.action==='createWatchlist'){const item={id:'DEMO-WATCH-NEW-'+watchlist.length,name:body.data?.name||'Kandidat Demo',type:'Candidate',status:'Under Review',priority:'Medium'};watchlist.push(item);return {item,demo:true};}
     if(body.action==='updateWatchlist'){const row=watchlist.find(x=>String(x.id)===String(body.id));if(row)Object.assign(row,body.data||{});return {item:row||null,demo:true};}
     return {items:watchlist,accounts:demoAccounts};
   }
   if(p==='/api/functions/socialListening'){
     let body={};try{body=JSON.parse(opts?.body||'{}')}catch(_){}
     if(body.action==='campaignCandidateSuggestions'){
       const source=rows.filter(x=>!body.data?.campaign_id||x.campaignId===body.data.campaign_id);
       return {candidates:Object.entries(source.reduce((a,p)=>{for(const raw of p.candidates||[]){const name=normalizeCandidate(raw);(a[name]??={name,matching_posts:0,source_ids:[]}).matching_posts++;if(a[name].source_ids.length<5)a[name].source_ids.push(p.sourceId);}return a},{})).map(x=>x[1]).sort((a,b)=>b.matching_posts-a.matching_posts).slice(0,10)};
     }
     return {ok:true,demo:true,items:[],posts:[]};
   }
   if(p==='/api/presentation/translate'){
     let body={};try{body=JSON.parse(opts?.body||'{}')}catch(_){}
     const text=String(body.text||''),lang=body.language||body.target_language||'id';
     return {text:lang==='id'?(enID.get(text)||text):text,language:lang,translation_only:true,demo:true};
   }
   if(p==='/api/health')return {ok:true,build_version:'DEMO'};
   return {ok:true,demo:true,items:[],posts:[],findings:[]};
 }
 window.fetch=async(input,opts={})=>{
   const src=typeof input==='string'?input:input?.url||'';
   const u=new URL(src,location.href),method=String(opts.method||input?.method||'GET').toUpperCase();
   if(u.pathname.startsWith('/api/'))return json(request(src,method,opts));
   if(u.origin===location.origin&&['GET','HEAD'].includes(method)&&!u.pathname.startsWith('/api/'))return originalFetch(input,opts);
   return json({detail:'Demo: external access and mutations blocked'},403);
 };
 window.__BAWASLU_DEMO_REPLICA__=true;
})();