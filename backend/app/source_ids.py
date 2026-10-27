"""Stable, namespace-safe identifiers for BAWASLU evidence and candidate records.

Never use source content, candidate display names or provider IDs as the only
canonical identity. Provider IDs can be missing, recycled or non-unique.
The source namespace and locally persisted row ID form the canonical reference.
"""
import re

_ID = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._:-]{0,127}$")

def canonical_source_id(namespace, record_id):
    if namespace not in {"social", "radar"}:
        raise ValueError("Unsupported source namespace")
    value = str(record_id or "").strip()
    if not _ID.fullmatch(value):
        raise ValueError("Invalid source record ID")
    if namespace == "social" and not value.isdecimal():
        raise ValueError("Social source ID must be the stored numeric row ID")
    return namespace + ":" + value

def canonical_candidate_id(record_id):
    value = str(record_id or "").strip()
    if not value.isdecimal() or int(value) <= 0:
        raise ValueError("Candidate identity must use the saved registry ID")
    return "candidate:" + str(int(value))

def parse_canonical_source_id(reference):
    namespace, separator, value = str(reference or "").partition(":")
    if not separator:
        raise ValueError("Missing source namespace")
    canonical = canonical_source_id(namespace, value)
    if canonical != reference:
        raise ValueError("Noncanonical source reference")
    return namespace, value
