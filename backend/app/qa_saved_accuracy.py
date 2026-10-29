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


REFERENCE_SIGNOFF_QUERY=text("""
SELECT count(*)::integer AS total_imported,
       count(*) FILTER (
         WHERE d.decision IN ('confirmed','corrected') AND
               d.approved_category IS NOT NULL AND
               (dupes.url_count IS NULL OR dupes.url_count=1 OR
                d.source_relation='distinct_comments')
       )::integer AS reviewed_approved,
       count(*) FILTER (
         WHERE d.decision='needs_context'
       )::integer AS needs_context,
       count(*) FILTER (
         WHERE dupes.url_count>1 AND d.decision IN ('confirmed','corrected')
           AND d.source_relation IS DISTINCT FROM 'distinct_comments'
       )::integer AS duplicate_source_unresolved
FROM pilot_smart_radar.qa_imported_human_categories h
JOIN pilot_smart_radar.qa_source_posts sp
 ON h.original_excel_row=sp.original_excel_row AND h.source_url=sp.source_url
LEFT JOIN pilot_smart_radar.qa_alignment_decisions d ON d.qa_id=sp.qa_id
LEFT JOIN (
 SELECT source_url,count(*)::integer url_count
 FROM pilot_smart_radar.qa_imported_human_categories
 GROUP BY source_url
) dupes ON dupes.source_url=h.source_url
""")

REVIEWED_ACCURACY_QUERY=text("""
WITH reviewed AS (
 SELECT a.prompt_version,a.model,a.qa_id,
        lower(trim(a.result_json::jsonb->>'primary_category')) AS predicted,
        lower(trim(d.approved_category)) AS approved,
        c.cohort
 FROM pilot_smart_radar.qa_ai_assessments a
 JOIN pilot_smart_radar.qa_alignment_decisions d ON d.qa_id=a.qa_id
 JOIN pilot_smart_radar.qa_source_posts sp ON sp.qa_id=a.qa_id
 LEFT JOIN pilot_smart_radar.qa_prompt_cohort c ON c.qa_id=a.qa_id
 LEFT JOIN (
  SELECT source_url,count(*)::integer url_count
  FROM pilot_smart_radar.qa_imported_human_categories
  GROUP BY source_url
 ) dupes ON dupes.source_url=sp.source_url
 WHERE d.decision IN ('confirmed','corrected')
   AND d.approved_category IS NOT NULL
   AND (dupes.url_count IS NULL OR dupes.url_count=1
        OR d.source_relation='distinct_comments')
   AND coalesce(c.cohort,'') NOT ILIKE '%holdout%'
)
SELECT prompt_version,model,
       count(*)::integer reviewed_posts,
       count(*) FILTER (WHERE predicted=approved)::integer matched
FROM reviewed
GROUP BY prompt_version,model
ORDER BY count(*) DESC,prompt_version DESC
LIMIT 25
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
        reference=db.execute(REFERENCE_SIGNOFF_QUERY).mappings().first()
        reviewed=db.execute(REVIEWED_ACCURACY_QUERY).mappings().all()
    except SQLAlchemyError:
        db.rollback()
        raise ValueError('Historical QA records are not available from this database')
    patterns=[{'prompt_version':str(x['prompt_version']),
        'model':str(x['model']),'cohort':str(x['cohort']),
        'expected_category':str(x['expected_category']),
        'predicted_category':str(x['predicted_category']),
        'error_count':int(x['error_count'])} for x in errors]
    reference=reference or {}
    total=int(reference.get('total_imported') or 0)
    signed=int(reference.get('reviewed_approved') or 0)
    reviewed_scores=[{
        'prompt_version':str(row['prompt_version']),
        'model':str(row['model']),
        'reviewed_posts':int(row['reviewed_posts']),
        'matched':int(row['matched']),
        'accuracy_percent':round(100*int(row['matched'])/int(row['reviewed_posts']),1)
            if row['reviewed_posts'] else None,
        'official_acceptance_eligible':signed==total and total>0 and
            int(row['reviewed_posts'])>=13
    } for row in reviewed]
    return {'available':True,'versions':summarize_version_stats(rows),
        'reference_signoff':{
            'total_imported':total,'analyst_approved':signed,
            'remaining_unsigned':max(0,total-signed),
            'needs_context':int(reference.get('needs_context') or 0),
            'duplicate_source_unresolved':int(reference.get('duplicate_source_unresolved') or 0),
            'historical_results_unchanged':True},
        'analyst_reviewed_accuracy':reviewed_scores,
        'analyst_reviewed_accuracy_does_not_override_historical_scores':True,
        'error_patterns':patterns,'error_patterns_are_aggregates_only':True,
        'reference_labels_must_be_signed_off_before_acceptance':True,
        'target_accuracy_percent':100,
        'reference_status':'PENDING_ANALYST_SIGNOFF_IF_UNSIGNED',
        'holdout_policy':'EXCLUDED_FROM_DEVELOPMENT_COMPARISONS',
        'assessment_method':'SAVED_PREDICTIONS_VERSUS_IMPORTED_SHAHRIN_LABELS',
        'no_new_predictions_generated':True,'paid_provider_called':False}
