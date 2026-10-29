"""Privileged read-only historical Shahrin accuracy QA. Never runs inference."""
from sqlalchemy import text
from sqlalchemy.exc import SQLAlchemyError

QUERY=text("""
WITH scored AS (
 SELECT a.prompt_version,a.model,a.qa_id,
        trim(h.category) AS human_category,
        trim(a.result_json::jsonb->>'primary_category') AS prediction,
        h.review_status AS label_review_status
 FROM pilot_smart_radar.qa_ai_assessments a
 JOIN pilot_smart_radar.qa_source_posts sp ON sp.qa_id=a.qa_id
 JOIN pilot_smart_radar.qa_imported_human_categories h
    ON h.source_url=sp.source_url AND h.original_excel_row=sp.original_excel_row
 LEFT JOIN pilot_smart_radar.qa_prompt_cohort cohort ON cohort.qa_id=a.qa_id
 WHERE coalesce(cohort.cohort,'') NOT ILIKE '%holdout%'
)
SELECT prompt_version,model,count(*)::integer AS evaluated,
       count(*) FILTER (WHERE lower(prediction)=lower(human_category))::integer AS correct,
       count(*) FILTER (WHERE prediction IS NULL OR prediction='')::integer AS missing_prediction,
       count(*) FILTER (WHERE label_review_status!='approved')::integer AS unsigned_labels
FROM scored GROUP BY prompt_version,model
ORDER BY count(*) DESC,prompt_version DESC
LIMIT 25
""")

CONFUSION_QUERY=text("""
WITH scored AS (
 SELECT a.prompt_version, a.model, a.qa_id,
        coalesce(cohort.cohort,'UNASSIGNED') AS cohort,
        trim(h.category) AS human_category,
        trim(a.result_json::jsonb->>'primary_category') AS prediction
 FROM pilot_smart_radar.qa_ai_assessments a
 JOIN pilot_smart_radar.qa_source_posts sp ON sp.qa_id=a.qa_id
 JOIN pilot_smart_radar.qa_imported_human_categories h
   ON h.source_url=sp.source_url AND h.original_excel_row=sp.original_excel_row
 LEFT JOIN pilot_smart_radar.qa_prompt_cohort cohort ON cohort.qa_id=a.qa_id
 WHERE coalesce(cohort.cohort,'') NOT ILIKE '%holdout%'
)
SELECT prompt_version,model,cohort,
       human_category AS expected_category,
       coalesce(prediction,'MISSING') AS predicted_category,
       count(*)::integer AS error_count
FROM scored
WHERE lower(coalesce(prediction,''))<>lower(coalesce(human_category,''))
GROUP BY prompt_version,model,cohort,human_category,prediction
ORDER BY count(*) DESC,prompt_version DESC
LIMIT 30
""")

def summarize_version_stats(rows):
    results=[]
    for item in rows:
        row=dict(item)
        total=int(row.get('evaluated') or 0)
        correct=int(row.get('correct') or 0)
        unsigned=int(row.get('unsigned_labels') or 0)
        results.append({'prompt_version':str(row.get('prompt_version') or ''),
            'model':str(row.get('model') or ''),'evaluated':total,'correct':correct,
            'incorrect_or_missing':max(total-correct,0),
            'accuracy_percent':round(100*correct/total,1) if total else None,
            'unsigned_reference_labels':unsigned,
            'missing_predictions':int(row.get('missing_prediction') or 0),
            'accuracy_target_met':bool(total>=13 and total==correct and unsigned==0),
            'sufficient_sample_for_acceptance':total>=13})
    return results

def qa_history_summary(db,p):
    if p.get('role')!='National Administrator' or (
            (p.get('permissions') or {}).get('administration') is not True):
        raise PermissionError('Only national administrators may inspect private QA aggregates')
    try:
        rows=db.execute(QUERY).mappings().all()
        errors=db.execute(CONFUSION_QUERY).mappings().all()
    except SQLAlchemyError:
        db.rollback()
        raise ValueError('Historical QA records are not available from this database')
    patterns=[{'prompt_version':str(x['prompt_version']),
        'model':str(x['model']),'cohort':str(x['cohort']),
        'expected_category':str(x['expected_category']),
        'predicted_category':str(x['predicted_category']),
        'error_count':int(x['error_count'])} for x in errors]
    return {'available':True,'versions':summarize_version_stats(rows),
        'error_patterns':patterns,'error_patterns_are_aggregates_only':True,
        'reference_labels_must_be_signed_off_before_acceptance':True,
        'target_accuracy_percent':100,
        'reference_status':'PENDING_ANALYST_SIGNOFF_IF_UNSIGNED',
        'holdout_policy':'EXCLUDED_FROM_DEVELOPMENT_COMPARISONS',
        'assessment_method':'SAVED_PREDICTIONS_VERSUS_IMPORTED_SHAHRIN_LABELS',
        'no_new_predictions_generated':True,'paid_provider_called':False}
