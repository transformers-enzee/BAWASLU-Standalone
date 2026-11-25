"""Atomic, non-billable eligibility predicate for ordinary pending AI jobs.

The selection query and the actual row claim can be separated in time. This
correlated SQL condition checks the *latest* saved relevance when claiming
the job, preventing a newly classified record from becoming a paid request.
Explicit reanalysis is intentionally separate and still needs its own budget
reservation.
"""
from sqlalchemy import and_,exists,func,case
from .models import AIAssessmentJob,EvidenceAssessment

_VALID=('RELEVANT','HIGHLY_RELEVANT','IRRELEVANT','UNCERTAIN')
_PRELIMINARY=('PRISM_PENDING_OPENAI','PRISM_OPENAI_TOPIC_CLASSIFIER')

def no_latest_relevance_classification(db):
    latest_id=(db.query(EvidenceAssessment.id)
        .filter(EvidenceAssessment.campaign_id==AIAssessmentJob.campaign_id,
                EvidenceAssessment.result_id==AIAssessmentJob.result_id)
        .order_by(case((func.upper(func.coalesce(EvidenceAssessment.model_version,'' )).in_(_PRELIMINARY),1),else_=0).asc(),
                  EvidenceAssessment.assessment_version.desc(),
                  EvidenceAssessment.id.desc())
        .limit(1).correlate(AIAssessmentJob).scalar_subquery())
    return ~exists().where(and_(
        EvidenceAssessment.id==latest_id,
        ~func.upper(func.coalesce(EvidenceAssessment.model_version,'')).in_(_PRELIMINARY),
        func.upper(func.coalesce(EvidenceAssessment.relevance_label,'')).in_(_VALID)))
