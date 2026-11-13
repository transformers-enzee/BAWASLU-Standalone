import React from 'react';

const LABELS={
 LEGAL_OUTCOME_OR_ACTION:['Legal conclusion or action','Kesimpulan atau tindakan hukum'],
 ELIGIBLE_LEGAL_SOURCE_MISSING:['Missing legal reference','Rujukan hukum belum tersedia'],
 CITATION_INTEGRITY:['Citation integrity','Integritas kutipan'],
 ARTICLE_OR_CLAIM_ATTRIBUTION:['Article or claim attribution','Kutipan pasal atau klaim'],
 PASSAGE_POLARITY:['Possible passage reversal','Kemungkinan perbedaan makna'],
 NUMERIC_OR_DATE:['Unsupported date or quantity','Tanggal atau jumlah tanpa dukungan'],
 ELECTION_SCOPE:['Election-type applicability','Kesesuaian jenis pemilihan'],
 DOCUMENT_REVIEW_PENDING:['Document review pending','Dokumen belum ditelaah'],
 SOURCE_RELEVANCE:['Source topic relevance','Relevansi topik rujukan'],
 VERSION_OR_EFFECTIVE_DATE:['Document version/date metadata','Metadata versi atau tanggal berlaku']
};
function Item({issue,id}){
 const title=LABELS[issue.code]||[issue.code,issue.code];
 return <li className="rounded-lg border border-[#e2e7eb] bg-white px-3 py-2">
  <div className="flex flex-wrap gap-2 items-center">
   <span className="rounded bg-[#f2e9e0] px-2 py-0.5 font-semibold text-[#80563a]">{issue.priority}</span>
   <span className="font-semibold text-[#33475b]">{title[id?1:0]}</span>
  </div>
  {issue.source_ids?.length>0&&<p className="mt-1 text-[#697d8e]">{id?'Halaman/sumber terkait':'Related cited sources'}: {issue.source_ids.join(', ')}</p>}
  {issue.detail_kinds?.length>0&&<p className="mt-1 text-[#697d8e]">{id?'Periksa jenis klaim':'Inspect claim details'}: {issue.detail_kinds.join(', ')}</p>}
 </li>;
}
export default function AssistantLegalReviewSummary({summary,language='id'}){
 if(!summary?.applicable)return null;
 const id=language!=='en';
 const issues=Array.isArray(summary.issues)?summary.issues:[];
 return <section data-testid="assistant-legal-review-summary" aria-label={id?'Ringkasan tinjauan hukum':'Legal review summary'}
  className="mt-2 rounded-lg border border-[#e1d2c2] bg-[#fffaf3] p-3 text-[#684c32]">
  <p className="font-semibold">{id?'Ringkasan pemeriksaan hukum':'Legal reference review'} · {issues.length} {id?'kelompok masalah':'issue groups'}</p>
  <p className="mt-1">{id?'P1/P2/P3 menunjukkan urutan pemeriksaan, bukan tingkat pelanggaran. Pemeriksaan dan persetujuan petugas tetap diperlukan.':'P1/P2/P3 indicate review order, not violation severity. Officer verification and approval remain necessary.'}</p>
  {issues.length>0?<ol data-testid="assistant-legal-review-priorities" className="mt-2 space-y-2">
   {issues.slice(0,3).map(issue=><Item key={issue.code} issue={issue} id={id}/>)}
  </ol>:<p className="mt-2">{id?'Tidak ada masalah leksikal tambahan yang terdeteksi. Ini bukan validasi hukum.':'No additional lexical warning was detected. This is not legal validation.'}</p>}
  {issues.length>3&&<details data-testid="assistant-legal-review-more" className="mt-2">
   <summary className="cursor-pointer font-semibold">{id?'Lihat masalah pemeriksaan lainnya':'See remaining review issues'} · {issues.length-3}</summary>
   <ol className="mt-2 space-y-2">{issues.slice(3).map(issue=><Item key={issue.code} issue={issue} id={id}/>)}</ol>
  </details>}
  <p className="mt-2 text-[#846445]">{id?'Tidak ada kesimpulan hukum atau tindakan otomatis. Pastikan dokumen resmi, keberlakuan, dan fakta kasus.':'No automatic legal conclusions or case actions. Verify official documents, current law and case facts.'}</p>
 </section>;
}
