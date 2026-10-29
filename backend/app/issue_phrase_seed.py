"""Conservative starter taxonomy phrases for unconfigured BAWASLU campaigns.

Only used during migration when the entire issue phrase table is empty.
Existing admin vocabulary, including deliberately inactive rows, wins.
Matching phrases are provisional hints with allegation-context checks; they do
not make legal findings, create flag reviews, or trigger AI requests.
"""
from sqlalchemy import text

STARTER_PHRASES={
    'Election Administration':('kesalahan daftar pemilih','logistik pemilu hilang'),
    'Campaign':('kampanye di tempat ibadah','kampanye di luar jadwal'),
    'Disinformation':('hoaks pemilu','berita bohong pemilu'),
    'Electoral Violation':('politik uang','intimidasi pemilih'),
    'Public Order':('kericuhan di tps','ancaman kepada pemilih'),
}

def seed_default_issue_phrases(connection):
    # All-or-nothing initial seed: never undo an administrator's manual
    # configuration by reintroducing rows they removed or disabled.
    if connection.execute(text('SELECT COUNT(*) FROM issue_category_phrases')).scalar():
        return 0
    inserted=0
    for name,phrases in STARTER_PHRASES.items():
        row=connection.execute(text(
            'SELECT id FROM issue_categories WHERE name=:name AND active=TRUE'
        ),{'name':name}).first()
        if not row:continue
        for phrase in phrases:
            result=connection.execute(text("""
                INSERT INTO issue_category_phrases
                    (category_id,phrase,normalized_phrase,active,created_at,updated_at)
                VALUES (:cid,:phrase,:normalized,TRUE,CURRENT_TIMESTAMP,CURRENT_TIMESTAMP)
                ON CONFLICT (category_id,normalized_phrase) DO NOTHING
            """),{'cid':row[0],'phrase':phrase,'normalized':phrase.casefold()})
            inserted+=max(0,result.rowcount or 0)
    return inserted
