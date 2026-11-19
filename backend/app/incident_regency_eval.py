"""Deterministic source-location benchmark against explicitly supplied labels.

This is not model-assisted geolocation or accuracy proof on production posts.
"""
from .incident_regency_candidates import incident_regency_candidates

def evaluate_labeled_incident_regencies(cases):
    """Return micro-precision/recall and exact-match counts on labeled cases."""
    tp=fp=fn=exact=0
    examples=0
    for entry in cases:
        if not isinstance(entry,dict):
            raise ValueError('Labeled cases must be objects')
        expected=set(entry.get('expected_regency_codes') or [])
        actual={item['regency_city_code'] for item in
                incident_regency_candidates(entry.get('text',''))}
        tp+=len(actual & expected)
        fp+=len(actual - expected)
        fn+=len(expected - actual)
        exact+=actual==expected
        examples+=1
    return {
        'labeled_cases':examples,
        'exact_match_cases':exact,
        'exact_match_rate':round(exact/examples,4) if examples else None,
        'true_positives':tp,'false_positives':fp,'false_negatives':fn,
        'micro_precision':round(tp/(tp+fp),4) if tp+fp else None,
        'micro_recall':round(tp/(tp+fn),4) if tp+fn else None,
        'micro_f1':round(2*tp/(2*tp+fp+fn),4) if 2*tp+fp+fn else None,
        'evaluation_basis':'EXPLICITLY_LABELED_CASES_ONLY',
        'source_truth_not_inferred':True,
        'not_real_world_accuracy_without_representative_labels':True,
        'paid_provider_called':False,
        'database_queries':0,
    }
