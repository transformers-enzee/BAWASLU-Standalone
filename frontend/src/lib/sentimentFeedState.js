/**
 * Keep officer corrections authoritative in the live Captured Posts feed.
 * Corrections are campaign-specific, immutable server entries; this layer
 * only overlays the current page until the backend returns the saved value.
 */
export const sentimentCorrectionKey=(campaignId,resultId)=>String(campaignId)+':'+String(resultId);

export function correctedSentimentPost(post,correction){
 if(!correction||!post)return post;
 return {
  ...post,
  sentiment:String(correction.sentiment||post.sentiment||'UNCLASSIFIED').toUpperCase(),
  sentiment_correction:correction,
  sentiment_details:{
   ...(post.sentiment_details||{}),
   confidence:'HUMAN_REVIEWED',
   status:'OFFICER_CORRECTED',
   model:'OFFICER_CORRECTION',
   explanation:correction.rationale||''
  }
 };
}

export function overlaySentimentCorrections(posts,campaignId,byKey){
 return (posts||[]).map(post=>{
  const correction=byKey.get(sentimentCorrectionKey(campaignId,post.id));
  return correction?correctedSentimentPost(post,correction):post;
 });
}
