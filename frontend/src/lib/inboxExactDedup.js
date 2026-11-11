// Read-time presentation deduplication only. Never delete or rewrite source evidence.
// Two independent platforms can publish the same normalized article; display one
// representative per campaign while keeping both source IDs in the database.
export const normalizedEvidenceText = text => String(text || '')
  .normalize('NFKC').replace(/\s+/g, ' ').trim().toLocaleLowerCase('id-ID');

const reviewRank = row => {
  const review = String(row.flag_review_status || '').toUpperCase();
  if (['FLAG_CONFIRMED', 'FLAG_DISMISSED', 'FURTHER_INVESTIGATION'].includes(review)) return 3;
  if (row.is_flagged) return 2;
  return 1;
};

export function deduplicateInboxEvidence(rows = []) {
  const byKey = new Map();
  const unique = [];
  for (const row of rows) {
    const text = normalizedEvidenceText(row?.text_content);
    // Do not collapse a blank body or short generic one-line reactions.
    const key = text.length >= 40 ? String(row.campaign_id || '') + '\u0000' + text : null;
    if (!key || !byKey.has(key)) {
      unique.push(row);
      if (key) byKey.set(key, unique.length - 1);
      continue;
    }
    const index = byKey.get(key);
    const previous = unique[index];
    const scoreA = reviewRank(previous), scoreB = reviewRank(row);
    const aId = Number(previous.id), bId = Number(row.id);
    if (scoreB > scoreA || (scoreA === scoreB && Number.isFinite(aId) &&
        Number.isFinite(bId) && bId < aId)) unique[index] = row;
  }
  return unique;
}
