import { createContext, useContext, useEffect, useMemo, useState } from 'react';

const LanguageContext=createContext(null);

const translations={
  en:{workspace:'Workspace',future_modules:'Future modules',soon:'SOON',home:'Home',watchlist:'Watchlist',social_listening:'Social Listening',intelligence_inbox:'Intelligence Inbox',intelligence_assistant:'BAWASLU Intelligence Assistant',add_intelligence:'Add Intelligence',data_sources:'Data Sources',validation:'Validation',administration:'Administration',intelligence_command:'Intelligence Command',secure_workspace:'Secure workspace',authorized_user:'Authorized user',election_supervision_intelligence:'Election supervision / Intelligence',add:'Add',loading_access:'Loading BAWASLU access...',inactive_access:'Your BAWASLU access is inactive.',select:'Select'},
  id:{workspace:'Ruang Kerja',future_modules:'Modul Mendatang',soon:'SEGERA',home:'Beranda',watchlist:'Daftar Pantauan',social_listening:'Pemantauan Media Sosial',intelligence_inbox:'Kotak Masuk Intelijen',intelligence_assistant:'Asisten Intelijen BAWASLU',add_intelligence:'Tambah Intelijen',data_sources:'Sumber Data',validation:'Validasi',administration:'Administrasi',intelligence_command:'Komando Intelijen',secure_workspace:'Ruang kerja aman',authorized_user:'Pengguna berwenang',election_supervision_intelligence:'Pengawasan Pemilu / Intelijen',add:'Tambah',loading_access:'Memuat akses BAWASLU...',inactive_access:'Akses BAWASLU Anda tidak aktif.',select:'Pilih'}
};

const valueLabels={id:{'Critical':'Kritis','High':'Tinggi','Medium':'Sedang','Low':'Rendah','Active':'Aktif','Inactive':'Tidak Aktif','Under Review':'Dalam Peninjauan','Pending Review':'Menunggu Peninjauan','Awaiting Validation':'Menunggu Validasi','Validated as Relevant Intelligence':'Divalidasi sebagai Intelijen Relevan','Request More Information':'Minta Informasi Tambahan','Not Relevant':'Tidak Relevan','Escalate for Further Review':'Eskalasi untuk Peninjauan Lanjutan','UNVERIFIED':'BELUM DIVERIFIKASI','HUMAN_VERIFIED':'DIVERIFIKASI MANUSIA','VERIFIED':'DIVERIFIKASI','OBSERVED':'TERAMATI','INFERRED':'INFERENSI','NO SIGNAL IDENTIFIED':'TIDAK ADA SINYAL TERIDENTIFIKASI','MONITOR':'PANTAU','REVIEW RECOMMENDED':'PENINJAUAN DIREKOMENDASIKAN','POTENTIAL REGULATORY ISSUE':'POTENSI ISU REGULASI','DISCOVERED':'DITEMUKAN','RELEVANT':'RELEVAN','NOT_RELEVANT':'TIDAK RELEVAN','PROMOTED':'DITAMBAHKAN KE INTELIJEN'}};

export function LanguageProvider({children}){
  const [language,setLanguageState]=useState(()=>localStorage.getItem('bawaslu-language')||'en');
  const setLanguage=next=>setLanguageState(next==='id'?'id':'en');
  useEffect(()=>{localStorage.setItem('bawaslu-language',language);document.documentElement.lang=language==='id'?'id':'en';},[language]);
  const api=useMemo(()=>({language,setLanguage,t:key=>translations[language]?.[key]??translations.en[key]??key,label:value=>valueLabels[language]?.[value]??value}),[language]);
  return <LanguageContext.Provider value={api}>{children}</LanguageContext.Provider>;
}

export function useLanguage(){const ctx=useContext(LanguageContext);if(!ctx)throw new Error('useLanguage must be used inside LanguageProvider');return ctx;}
