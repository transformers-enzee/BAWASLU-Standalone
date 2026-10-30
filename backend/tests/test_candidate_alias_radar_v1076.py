from app.processing_hints import normalize_candidate_signals
from app.candidate_registry import normalized,resolve_signals
from app.inbox_radar import compile_inbox_findings

def test_aliases_collapse():
 assert normalize_candidate_signals(['prabowo','Prabowo','Prabowo Subianto','Gibran','Gibran Rakabuming Raka','anisbaswedan','Anies Baswedan'])==['Prabowo Subianto','Gibran Rakabuming Raka','Anies Baswedan']

def test_normalization():
 assert normalized('Prabowo')==normalized('prabowo')

def test_not_automatic_creation():
 assert all(m['canonical_candidate_id'] is None for m in resolve_signals(['Gibran','prabowo'],{}))

def test_summary_simple():
 f=compile_inbox_findings([{'id':'23','campaign_id':'1','relevance_label':'RELEVANT','is_flagged':True,'potential_issues':[],'text_content':'dugaan pelanggaran'}])
 assert len(f)==1 and 'quote-validated' not in f[0]['summary']
