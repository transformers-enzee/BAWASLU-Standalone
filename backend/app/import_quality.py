"""Read-only import quality gate for the two BAWASLU source namespaces.

Do not fabricate provider IDs or turn collection times into publication times.
Imported source evidence is eligible for source-facing verification only when
source URL, platform, publication time, content and account are present.
"""
from dataclasses import dataclass

@dataclass(frozen=True)
class ImportQuality:
    source_id: str
    missing_fields: tuple[str,...]
    requires_manual_review: bool

def social_quality(row):
    from .source_ids import canonical_source_id
    required={
      "source_url": row.get("canonical_url"),
      "platform": row.get("platform"),
      "published_at": row.get("published_at"),
      "content": row.get("text_content"),
      "author_or_handle": row.get("observed_handle") or row.get("author_name")
    }
    missing=tuple(field for field,value in required.items() if not str(value or "").strip())
    return ImportQuality(canonical_source_id("social",row["id"]),missing,bool(missing))

def radar_quality(row):
    from .source_ids import canonical_source_id
    required={
      "source_url": row.get("source_url"),
      "platform": row.get("platform"),
      "published_at": row.get("published_at_raw"),
      "content": row.get("message_original"),
      "account": row.get("account_raw")
    }
    missing=tuple(field for field,value in required.items() if not str(value or "").strip())
    return ImportQuality(canonical_source_id("radar",row["pilot_post_id"]),missing,bool(missing))
