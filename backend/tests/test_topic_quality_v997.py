"""No paid calls or stored-label mutations: flag questionable topic labels."""
from app.topic_quality import topic_quality_flags

def test_genuine_reputation_complaint_is_not_automatically_rejected():
    text='Ratusan massa meminta Bawaslu bertanggung jawab atas buruknya kualitas Pemilu.'
    assert topic_quality_flags(text,['BAWASLU Reputation'])==[]

def test_routine_discussion_not_proven_reputation():
    assert 'REPUTATION_LABEL_REQUIRES_SOURCE_REVIEW' in topic_quality_flags(
        'DISKUSI PUBLIK BAWASLU 9 JULI 2026',['BAWASLU Reputation'])

def test_hashtag_only_cannot_establish_electoral_operations():
    flags=topic_quality_flags('ROASTING 3 CAPRES #pemilu #bawaslu #pilkada',
                               ['Electoral Operations'])
    assert 'ELECTORAL_LABEL_REQUIRES_SOURCE_REVIEW' in flags

def test_source_grounded_operational_post_is_not_flagged():
    assert topic_quality_flags('Bawaslu mengawasi rekapitulasi suara pemilu di TPS',
                               ['Electoral Operations'])==[]
