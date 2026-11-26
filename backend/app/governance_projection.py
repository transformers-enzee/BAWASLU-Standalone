"""Read-only effective values and integrity fingerprints for officer governance.

No original provider rows or AI assessments are mutated. This projection is
separate from legacy Inbox and Command Centre displays until schema activation.
"""
import hashlib
import json

ASSESSMENT_FIELDS = {"relevance": "relevance_label", "sentiment": "sentiment"}
MAX_CORRECTIONS_PER_SOURCE = 500


def effective_assessment(assessment, corrections):
    """Represent field-level officer precedence without claiming entire-record verification."""
    values = {}
    for field, column in ASSESSMENT_FIELDS.items():
        ai_value = getattr(assessment, column, None) if assessment is not None else None
        values[field] = {
            "ai_value": ai_value, "effective_value": ai_value,
            "effective_basis": "AI_ASSESSMENT" if assessment is not None else "UNASSESSED",
            "officer_value": None, "officer_revision": None, "officer_reviewer_id": None,
        }
    # Only the highest approved revision for each field may supersede the AI.
    latest = {}
    for row in corrections:
        if row.field not in ASSESSMENT_FIELDS or row.status != "approved":
            continue
        if row.field not in latest or (row.revision, row.id) > (
                latest[row.field].revision, latest[row.field].id):
            latest[row.field] = row
    for field, correction in latest.items():
        values[field].update(
            effective_value=correction.human_value,
            effective_basis="OFFICER_APPROVED",
            officer_value=correction.human_value,
            officer_revision=correction.revision,
            officer_reviewer_id=correction.reviewer_id,
        )
    return {
        "fields": values,
        "assessment_id": getattr(assessment, "id", None),
        "assessment_version": getattr(assessment, "assessment_version", None),
        "model_version": getattr(assessment, "model_version", None),
        "record_human_verified": False,  # Field review != entire-record evidence verification
        "original_source_preserved": True,
        "unmapped_correction_fields": sorted({
            row.field for row in corrections if row.field not in ASSESSMENT_FIELDS
        }),
    }


def source_snapshot_fingerprint(source, assessment, corrections):
    """Hash every source + assessment column and all correction revisions."""
    def columns(obj):
        if obj is None:
            return None
        table = getattr(obj, "__table__", None)
        if table is not None:
            return {column.name: getattr(obj, column.name, None) for column in table.columns}
        return {key: val for key, val in vars(obj).items() if not key.startswith("_")}
    payload = {
        "source": columns(source),
        "assessment": columns(assessment),
        "corrections": [columns(c) for c in sorted(corrections, key=lambda c: (
            c.field, c.revision, c.id))],
    }
    encoded = json.dumps(payload, ensure_ascii=False, sort_keys=True, default=str)
    return hashlib.sha256(encoded.encode("utf-8")).hexdigest()
