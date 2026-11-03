// Derive summary figures from the same campaign records rendered in the list.
// Do not trust a separate metadata total when rows and count disagree.
export function monitoringCampaignSummary(campaigns=[],trackedCount=null){
 const rows=Array.isArray(campaigns)?campaigns:[];
 const posts=rows.reduce((sum,c)=>sum+(Number(c.evidence_count??c.captured_count)||0),0);
 const aliases={x:'X',twitter:'X','twitter-ai-search':'X',online_news:'News',news:'News'};
 const platforms=new Set(rows.flatMap(c=>Array.isArray(c.platforms)?c.platforms:[]).map(p=>aliases[String(p).toLowerCase()]||String(p).toLowerCase()).filter(Boolean));
 return {
  campaigns:rows.length,
  posts,
  platforms:platforms.size||null,
  candidates:Number.isFinite(trackedCount)?trackedCount:null
 };
}
