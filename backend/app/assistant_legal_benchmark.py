"""Synthetic-only legal-answer signal acceptance harness for QA.

Fixed developer-labeled scenarios. These are not BAWASLU-approved legal texts,
human gold answers, or live model responses. Zero DB/model/network activity.
No personally identifying records or real post contents are included.
"""
import json
from collections import Counter
from .assistant_grounding import audit_assistant_answer
from .assistant_answer_quality import evaluate_answer_quality

CORPUS=json.loads(r'''[
  {
    "id": "S01",
    "category": "SOURCE_ELIGIBILITY",
    "question": "What legal law applies?",
    "answer": "General report [DOC-1-P1].",
    "documents": [
      {
        "record_id": "DOC-1-P1",
        "record_type": "PDF_KNOWLEDGE",
        "document_type": "REPORT",
        "title": "Synthetic electoral guidance",
        "source_excerpt": "General case report.",
        "review_status": "OFFICER_REVIEWED",
        "legal_election_type": "BOTH",
        "legal_version_label": "Synthetic v1",
        "legal_effective_date": "2026-01-01"
      }
    ],
    "expected_present": [
      "ELIGIBLE_LEGAL_SOURCE_MISSING"
    ],
    "expected_absent": [
      "PASSAGE_POLARITY"
    ],
    "expected_status": "OFFICER_REVIEW_REQUIRED"
  },
  {
    "id": "S02",
    "category": "SOURCE_ELIGIBILITY",
    "question": "What legal law applies?",
    "answer": "Pasal 21 [DOC-1-P1].",
    "documents": [
      {
        "record_id": "DOC-1-P1",
        "record_type": "PDF_KNOWLEDGE",
        "document_type": "REGULATION",
        "title": "Synthetic electoral guidance",
        "source_excerpt": "Pasal 21 provides election procedures.",
        "review_status": "OFFICER_REVIEWED",
        "legal_election_type": "BOTH",
        "legal_version_label": "Synthetic v1",
        "legal_effective_date": "2026-01-01"
      }
    ],
    "expected_present": [],
    "expected_absent": [
      "ELIGIBLE_LEGAL_SOURCE_MISSING"
    ],
    "expected_status": "OFFICER_REVIEW_REQUIRED"
  },
  {
    "id": "S03",
    "category": "SOURCE_ELIGIBILITY",
    "question": "What legal law applies?",
    "answer": "The documents provide relevant context.",
    "documents": [
      {
        "record_id": "DOC-1-P1",
        "record_type": "PDF_KNOWLEDGE",
        "document_type": "REGULATION",
        "title": "Synthetic electoral guidance",
        "source_excerpt": "Pasal 21 provides election procedures.",
        "review_status": "OFFICER_REVIEWED",
        "legal_election_type": "BOTH",
        "legal_version_label": "Synthetic v1",
        "legal_effective_date": "2026-01-01"
      }
    ],
    "expected_present": [
      "ELIGIBLE_LEGAL_SOURCE_MISSING"
    ],
    "expected_absent": [],
    "expected_status": "OFFICER_REVIEW_REQUIRED"
  },
  {
    "id": "S04",
    "category": "SOURCE_ELIGIBILITY",
    "question": "What legal law applies?",
    "answer": "Pasal 21 [DOC-1-P1] [DOC-2-P1].",
    "documents": [
      {
        "record_id": "DOC-1-P1",
        "record_type": "PDF_KNOWLEDGE",
        "document_type": "REGULATION",
        "title": "Synthetic electoral guidance",
        "source_excerpt": "Pasal 21 election procedures.",
        "review_status": "OFFICER_REVIEWED",
        "legal_election_type": "BOTH",
        "legal_version_label": "Synthetic v1",
        "legal_effective_date": "2026-01-01"
      },
      {
        "record_id": "DOC-2-P1",
        "record_type": "PDF_KNOWLEDGE",
        "document_type": "REPORT",
        "title": "Synthetic electoral guidance",
        "source_excerpt": "General context report.",
        "review_status": "OFFICER_REVIEWED",
        "legal_election_type": "BOTH",
        "legal_version_label": "Synthetic v1",
        "legal_effective_date": "2026-01-01"
      }
    ],
    "expected_present": [],
    "expected_absent": [
      "ELIGIBLE_LEGAL_SOURCE_MISSING"
    ],
    "expected_status": "OFFICER_REVIEW_REQUIRED"
  },
  {
    "id": "C01",
    "category": "CITATION_INTEGRITY",
    "question": "What legal law applies?",
    "answer": "Pasal 21 [DOC-1-P1] [DOC-99-P1].",
    "documents": [
      {
        "record_id": "DOC-1-P1",
        "record_type": "PDF_KNOWLEDGE",
        "document_type": "REGULATION",
        "title": "Synthetic electoral guidance",
        "source_excerpt": "Pasal 21 election procedures.",
        "review_status": "OFFICER_REVIEWED",
        "legal_election_type": "BOTH",
        "legal_version_label": "Synthetic v1",
        "legal_effective_date": "2026-01-01"
      }
    ],
    "expected_present": [
      "CITATION_INTEGRITY"
    ],
    "expected_absent": [],
    "expected_status": "OFFICER_REVIEW_REQUIRED"
  },
  {
    "id": "C02",
    "category": "CITATION_INTEGRITY",
    "question": "What legal law applies?",
    "answer": "Pasal 21 [DOC-1-P1].",
    "documents": [
      {
        "record_id": "DOC-1-P1",
        "record_type": "PDF_KNOWLEDGE",
        "document_type": "REGULATION",
        "title": "Synthetic electoral guidance",
        "source_excerpt": "Pasal 21 election procedures.",
        "review_status": "OFFICER_REVIEWED",
        "legal_election_type": "BOTH",
        "legal_version_label": "Synthetic v1",
        "legal_effective_date": "2026-01-01"
      }
    ],
    "expected_present": [],
    "expected_absent": [
      "CITATION_INTEGRITY"
    ],
    "expected_status": "OFFICER_REVIEW_REQUIRED"
  },
  {
    "id": "A01",
    "category": "CLAIM_ATTRIBUTION",
    "question": "What legal law applies?",
    "answer": "Pasal 30 [DOC-1-P1].",
    "documents": [
      {
        "record_id": "DOC-1-P1",
        "record_type": "PDF_KNOWLEDGE",
        "document_type": "REGULATION",
        "title": "Synthetic electoral guidance",
        "source_excerpt": "Pasal 21 describes election procedures.",
        "review_status": "OFFICER_REVIEWED",
        "legal_election_type": "BOTH",
        "legal_version_label": "Synthetic v1",
        "legal_effective_date": "2026-01-01"
      }
    ],
    "expected_present": [
      "ARTICLE_OR_CLAIM_ATTRIBUTION"
    ],
    "expected_absent": [],
    "expected_status": "OFFICER_REVIEW_REQUIRED"
  },
  {
    "id": "A02",
    "category": "CLAIM_ATTRIBUTION",
    "question": "What legal law applies?",
    "answer": "Pasal 21 [DOC-1-P1].",
    "documents": [
      {
        "record_id": "DOC-1-P1",
        "record_type": "PDF_KNOWLEDGE",
        "document_type": "REGULATION",
        "title": "Synthetic electoral guidance",
        "source_excerpt": "Pasal 21 describes election procedures.",
        "review_status": "OFFICER_REVIEWED",
        "legal_election_type": "BOTH",
        "legal_version_label": "Synthetic v1",
        "legal_effective_date": "2026-01-01"
      }
    ],
    "expected_present": [],
    "expected_absent": [
      "ARTICLE_OR_CLAIM_ATTRIBUTION"
    ],
    "expected_status": "OFFICER_REVIEW_REQUIRED"
  },
  {
    "id": "A03",
    "category": "CLAIM_ATTRIBUTION",
    "question": "What legal law applies?",
    "answer": "Pasal 21 applies. Background [DOC-1-P1].",
    "documents": [
      {
        "record_id": "DOC-1-P1",
        "record_type": "PDF_KNOWLEDGE",
        "document_type": "REGULATION",
        "title": "Synthetic electoral guidance",
        "source_excerpt": "Pasal 21 describes election procedures.",
        "review_status": "OFFICER_REVIEWED",
        "legal_election_type": "BOTH",
        "legal_version_label": "Synthetic v1",
        "legal_effective_date": "2026-01-01"
      }
    ],
    "expected_present": [
      "ARTICLE_OR_CLAIM_ATTRIBUTION"
    ],
    "expected_absent": [],
    "expected_status": "OFFICER_REVIEW_REQUIRED"
  },
  {
    "id": "A04",
    "category": "CLAIM_ATTRIBUTION",
    "question": "What legal law applies?",
    "answer": "Officials must report immediately. Background [DOC-1-P1].",
    "documents": [
      {
        "record_id": "DOC-1-P1",
        "record_type": "PDF_KNOWLEDGE",
        "document_type": "REGULATION",
        "title": "Synthetic electoral guidance",
        "source_excerpt": "Officials must report election incidents.",
        "review_status": "OFFICER_REVIEWED",
        "legal_election_type": "BOTH",
        "legal_version_label": "Synthetic v1",
        "legal_effective_date": "2026-01-01"
      }
    ],
    "expected_present": [
      "ARTICLE_OR_CLAIM_ATTRIBUTION"
    ],
    "expected_absent": [],
    "expected_status": "OFFICER_REVIEW_REQUIRED"
  },
  {
    "id": "A05",
    "category": "CLAIM_ATTRIBUTION",
    "question": "What legal law applies?",
    "answer": "Officials must report [DOC-1-P1].",
    "documents": [
      {
        "record_id": "DOC-1-P1",
        "record_type": "PDF_KNOWLEDGE",
        "document_type": "REGULATION",
        "title": "Synthetic electoral guidance",
        "source_excerpt": "Officials must report election incidents.",
        "review_status": "OFFICER_REVIEWED",
        "legal_election_type": "BOTH",
        "legal_version_label": "Synthetic v1",
        "legal_effective_date": "2026-01-01"
      }
    ],
    "expected_present": [],
    "expected_absent": [
      "ARTICLE_OR_CLAIM_ATTRIBUTION"
    ],
    "expected_status": "OFFICER_REVIEW_REQUIRED"
  },
  {
    "id": "P01",
    "category": "PASSAGE_POLARITY",
    "question": "What legal law applies?",
    "answer": "Officials must report [DOC-1-P1].",
    "documents": [
      {
        "record_id": "DOC-1-P1",
        "record_type": "PDF_KNOWLEDGE",
        "document_type": "REGULATION",
        "title": "Synthetic electoral guidance",
        "source_excerpt": "Officials must not report incidents.",
        "review_status": "OFFICER_REVIEWED",
        "legal_election_type": "BOTH",
        "legal_version_label": "Synthetic v1",
        "legal_effective_date": "2026-01-01"
      }
    ],
    "expected_present": [
      "PASSAGE_POLARITY"
    ],
    "expected_absent": [],
    "expected_status": "OFFICER_REVIEW_REQUIRED"
  },
  {
    "id": "P02",
    "category": "PASSAGE_POLARITY",
    "question": "What legal law applies?",
    "answer": "Officials must report [DOC-1-P1].",
    "documents": [
      {
        "record_id": "DOC-1-P1",
        "record_type": "PDF_KNOWLEDGE",
        "document_type": "REGULATION",
        "title": "Synthetic electoral guidance",
        "source_excerpt": "Officials must report incidents.",
        "review_status": "OFFICER_REVIEWED",
        "legal_election_type": "BOTH",
        "legal_version_label": "Synthetic v1",
        "legal_effective_date": "2026-01-01"
      }
    ],
    "expected_present": [],
    "expected_absent": [
      "PASSAGE_POLARITY"
    ],
    "expected_status": "OFFICER_REVIEW_REQUIRED"
  },
  {
    "id": "P03",
    "category": "PASSAGE_POLARITY",
    "question": "Apa kewajiban hukum?",
    "answer": "Petugas wajib melapor [DOC-1-P1].",
    "documents": [
      {
        "record_id": "DOC-1-P1",
        "record_type": "PDF_KNOWLEDGE",
        "document_type": "REGULATION",
        "title": "Synthetic electoral guidance",
        "source_excerpt": "Petugas tidak wajib melapor.",
        "review_status": "OFFICER_REVIEWED",
        "legal_election_type": "BOTH",
        "legal_version_label": "Synthetic v1",
        "legal_effective_date": "2026-01-01"
      }
    ],
    "expected_present": [
      "PASSAGE_POLARITY"
    ],
    "expected_absent": [],
    "expected_status": "OFFICER_REVIEW_REQUIRED"
  },
  {
    "id": "P04",
    "category": "PASSAGE_POLARITY",
    "question": "What legal law applies?",
    "answer": "Officials must report [DOC-1-P1].",
    "documents": [
      {
        "record_id": "DOC-1-P1",
        "record_type": "PDF_KNOWLEDGE",
        "document_type": "REGULATION",
        "title": "Synthetic electoral guidance",
        "source_excerpt": "Officials must not register.",
        "review_status": "OFFICER_REVIEWED",
        "legal_election_type": "BOTH",
        "legal_version_label": "Synthetic v1",
        "legal_effective_date": "2026-01-01"
      }
    ],
    "expected_present": [],
    "expected_absent": [
      "PASSAGE_POLARITY"
    ],
    "expected_status": "OFFICER_REVIEW_REQUIRED"
  },
  {
    "id": "P05",
    "category": "PASSAGE_POLARITY",
    "question": "What legal law applies?",
    "answer": "Officials must report [DOC-1-P1].",
    "documents": [
      {
        "record_id": "DOC-1-P1",
        "record_type": "PDF_KNOWLEDGE",
        "document_type": "REGULATION",
        "title": "Synthetic electoral guidance",
        "source_excerpt": "Officials must report. Other officials must not report.",
        "review_status": "OFFICER_REVIEWED",
        "legal_election_type": "BOTH",
        "legal_version_label": "Synthetic v1",
        "legal_effective_date": "2026-01-01"
      }
    ],
    "expected_present": [],
    "expected_absent": [
      "PASSAGE_POLARITY"
    ],
    "expected_status": "OFFICER_REVIEW_REQUIRED"
  },
  {
    "id": "N01",
    "category": "NUMERIC_DATE",
    "question": "What legal law applies?",
    "answer": "The deadline is 30 days [DOC-1-P1].",
    "documents": [
      {
        "record_id": "DOC-1-P1",
        "record_type": "PDF_KNOWLEDGE",
        "document_type": "REGULATION",
        "title": "Synthetic electoral guidance",
        "source_excerpt": "Deadline is 14 days.",
        "review_status": "OFFICER_REVIEWED",
        "legal_election_type": "BOTH",
        "legal_version_label": "Synthetic v1",
        "legal_effective_date": "2026-01-01"
      }
    ],
    "expected_present": [
      "NUMERIC_OR_DATE"
    ],
    "expected_absent": [],
    "expected_status": "OFFICER_REVIEW_REQUIRED"
  },
  {
    "id": "N02",
    "category": "NUMERIC_DATE",
    "question": "What legal law applies?",
    "answer": "The deadline is 14 days [DOC-1-P1].",
    "documents": [
      {
        "record_id": "DOC-1-P1",
        "record_type": "PDF_KNOWLEDGE",
        "document_type": "REGULATION",
        "title": "Synthetic electoral guidance",
        "source_excerpt": "Deadline is 14 days.",
        "review_status": "OFFICER_REVIEWED",
        "legal_election_type": "BOTH",
        "legal_version_label": "Synthetic v1",
        "legal_effective_date": "2026-01-01"
      }
    ],
    "expected_present": [],
    "expected_absent": [
      "NUMERIC_OR_DATE"
    ],
    "expected_status": "OFFICER_REVIEW_REQUIRED"
  },
  {
    "id": "N03",
    "category": "NUMERIC_DATE",
    "question": "What legal law applies?",
    "answer": "This regulation is effective 2026-11-01 [DOC-1-P1].",
    "documents": [
      {
        "record_id": "DOC-1-P1",
        "record_type": "PDF_KNOWLEDGE",
        "document_type": "REGULATION",
        "title": "Synthetic electoral guidance",
        "source_excerpt": "This regulation is effective 2026-10-01.",
        "review_status": "OFFICER_REVIEWED",
        "legal_election_type": "BOTH",
        "legal_version_label": "Synthetic v1",
        "legal_effective_date": "2026-01-01"
      }
    ],
    "expected_present": [
      "NUMERIC_OR_DATE"
    ],
    "expected_absent": [],
    "expected_status": "OFFICER_REVIEW_REQUIRED"
  },
  {
    "id": "N04",
    "category": "NUMERIC_DATE",
    "question": "What legal law applies?",
    "answer": "This regulation is effective 2026-11-01 [DOC-1-P1].",
    "documents": [
      {
        "record_id": "DOC-1-P1",
        "record_type": "PDF_KNOWLEDGE",
        "document_type": "REGULATION",
        "title": "Synthetic electoral guidance",
        "source_excerpt": "This regulation is effective 2026-11-01.",
        "review_status": "OFFICER_REVIEWED",
        "legal_election_type": "BOTH",
        "legal_version_label": "Synthetic v1",
        "legal_effective_date": "2026-01-01"
      }
    ],
    "expected_present": [],
    "expected_absent": [
      "NUMERIC_OR_DATE"
    ],
    "expected_status": "OFFICER_REVIEW_REQUIRED"
  },
  {
    "id": "N05",
    "category": "NUMERIC_DATE",
    "question": "Apa batas waktu menurut hukum?",
    "answer": "Batas waktu 30 hari [DOC-1-P1].",
    "documents": [
      {
        "record_id": "DOC-1-P1",
        "record_type": "PDF_KNOWLEDGE",
        "document_type": "REGULATION",
        "title": "Synthetic electoral guidance",
        "source_excerpt": "Batas waktu 14 hari.",
        "review_status": "OFFICER_REVIEWED",
        "legal_election_type": "BOTH",
        "legal_version_label": "Synthetic v1",
        "legal_effective_date": "2026-01-01"
      }
    ],
    "expected_present": [
      "NUMERIC_OR_DATE"
    ],
    "expected_absent": [],
    "expected_status": "OFFICER_REVIEW_REQUIRED"
  },
  {
    "id": "N06",
    "category": "NUMERIC_DATE",
    "question": "What legal law applies?",
    "answer": "The threshold is 25% [DOC-1-P1].",
    "documents": [
      {
        "record_id": "DOC-1-P1",
        "record_type": "PDF_KNOWLEDGE",
        "document_type": "REGULATION",
        "title": "Synthetic electoral guidance",
        "source_excerpt": "The threshold is 10 percent.",
        "review_status": "OFFICER_REVIEWED",
        "legal_election_type": "BOTH",
        "legal_version_label": "Synthetic v1",
        "legal_effective_date": "2026-01-01"
      }
    ],
    "expected_present": [
      "NUMERIC_OR_DATE"
    ],
    "expected_absent": [],
    "expected_status": "OFFICER_REVIEW_REQUIRED"
  },
  {
    "id": "E01",
    "category": "ELECTION_SCOPE",
    "question": "Which Pemilu law applies?",
    "answer": "Pasal 21 [DOC-1-P1].",
    "documents": [
      {
        "record_id": "DOC-1-P1",
        "record_type": "PDF_KNOWLEDGE",
        "document_type": "REGULATION",
        "title": "Pilkada regulation",
        "source_excerpt": "Pasal 21 election procedure.",
        "review_status": "OFFICER_REVIEWED",
        "legal_election_type": "PILKADA",
        "legal_version_label": "Synthetic v1",
        "legal_effective_date": "2026-01-01"
      }
    ],
    "expected_present": [
      "ELECTION_SCOPE"
    ],
    "expected_absent": [],
    "expected_status": "OFFICER_REVIEW_REQUIRED"
  },
  {
    "id": "E02",
    "category": "ELECTION_SCOPE",
    "question": "Which Pemilu law applies?",
    "answer": "Pasal 21 [DOC-1-P1].",
    "documents": [
      {
        "record_id": "DOC-1-P1",
        "record_type": "PDF_KNOWLEDGE",
        "document_type": "REGULATION",
        "title": "Pemilu regulation",
        "source_excerpt": "Pasal 21 election procedure.",
        "review_status": "OFFICER_REVIEWED",
        "legal_election_type": "PEMILU",
        "legal_version_label": "Synthetic v1",
        "legal_effective_date": "2026-01-01"
      }
    ],
    "expected_present": [],
    "expected_absent": [
      "ELECTION_SCOPE"
    ],
    "expected_status": "OFFICER_REVIEW_REQUIRED"
  },
  {
    "id": "E03",
    "category": "ELECTION_SCOPE",
    "question": "Which Pemilu law applies?",
    "answer": "Pasal 21 [DOC-1-P1].",
    "documents": [
      {
        "record_id": "DOC-1-P1",
        "record_type": "PDF_KNOWLEDGE",
        "document_type": "REGULATION",
        "title": "Pilkada regulation",
        "source_excerpt": "Pasal 21 election procedure.",
        "review_status": "OFFICER_REVIEWED",
        "legal_election_type": "BOTH",
        "legal_version_label": "Synthetic v1",
        "legal_effective_date": "2026-01-01"
      }
    ],
    "expected_present": [],
    "expected_absent": [
      "ELECTION_SCOPE"
    ],
    "expected_status": "OFFICER_REVIEW_REQUIRED"
  },
  {
    "id": "E04",
    "category": "ELECTION_SCOPE",
    "question": "Which Pemilu law applies?",
    "answer": "Pasal 21 [DOC-1-P1].",
    "documents": [
      {
        "record_id": "DOC-1-P1",
        "record_type": "PDF_KNOWLEDGE",
        "document_type": "REGULATION",
        "title": "Pilkada regulation",
        "source_excerpt": "Pasal 21 election procedure.",
        "review_status": "OFFICER_REVIEWED",
        "legal_election_type": "UNSPECIFIED",
        "legal_version_label": "Synthetic v1",
        "legal_effective_date": "2026-01-01"
      }
    ],
    "expected_present": [
      "ELECTION_SCOPE"
    ],
    "expected_absent": [],
    "expected_status": "OFFICER_REVIEW_REQUIRED"
  },
  {
    "id": "R01",
    "category": "DOCUMENT_REVIEW",
    "question": "What legal law applies?",
    "answer": "Pasal 21 [DOC-1-P1].",
    "documents": [
      {
        "record_id": "DOC-1-P1",
        "record_type": "PDF_KNOWLEDGE",
        "document_type": "REGULATION",
        "title": "Synthetic electoral guidance",
        "source_excerpt": "Pasal 21 election procedure.",
        "review_status": "UNREVIEWED",
        "legal_election_type": "BOTH",
        "legal_version_label": "Synthetic v1",
        "legal_effective_date": "2026-01-01"
      }
    ],
    "expected_present": [
      "DOCUMENT_REVIEW_PENDING"
    ],
    "expected_absent": [],
    "expected_status": "OFFICER_REVIEW_REQUIRED"
  },
  {
    "id": "R02",
    "category": "DOCUMENT_REVIEW",
    "question": "What legal law applies?",
    "answer": "Pasal 21 [DOC-1-P1].",
    "documents": [
      {
        "record_id": "DOC-1-P1",
        "record_type": "PDF_KNOWLEDGE",
        "document_type": "REGULATION",
        "title": "Synthetic electoral guidance",
        "source_excerpt": "Pasal 21 election procedure.",
        "review_status": "OFFICER_REVIEWED",
        "legal_election_type": "BOTH",
        "legal_version_label": "Synthetic v1",
        "legal_effective_date": "2026-01-01"
      }
    ],
    "expected_present": [],
    "expected_absent": [
      "DOCUMENT_REVIEW_PENDING"
    ],
    "expected_status": "OFFICER_REVIEW_REQUIRED"
  },
  {
    "id": "T01",
    "category": "SOURCE_RELEVANCE",
    "question": "What legal law governs Riau bribery?",
    "answer": "General regulation [DOC-1-P1].",
    "documents": [
      {
        "record_id": "DOC-1-P1",
        "record_type": "PDF_KNOWLEDGE",
        "document_type": "REGULATION",
        "title": "Synthetic electoral guidance",
        "source_excerpt": "National voter registration procedures.",
        "review_status": "OFFICER_REVIEWED",
        "legal_election_type": "BOTH",
        "legal_version_label": "Synthetic v1",
        "legal_effective_date": "2026-01-01"
      }
    ],
    "expected_present": [
      "SOURCE_RELEVANCE"
    ],
    "expected_absent": [],
    "expected_status": "OFFICER_REVIEW_REQUIRED"
  },
  {
    "id": "T02",
    "category": "SOURCE_RELEVANCE",
    "question": "What legal law governs Riau bribery?",
    "answer": "General regulation [DOC-1-P1].",
    "documents": [
      {
        "record_id": "DOC-1-P1",
        "record_type": "PDF_KNOWLEDGE",
        "document_type": "REGULATION",
        "title": "Synthetic electoral guidance",
        "source_excerpt": "Riau bribery reporting procedures.",
        "review_status": "OFFICER_REVIEWED",
        "legal_election_type": "BOTH",
        "legal_version_label": "Synthetic v1",
        "legal_effective_date": "2026-01-01"
      }
    ],
    "expected_present": [],
    "expected_absent": [
      "SOURCE_RELEVANCE"
    ],
    "expected_status": "OFFICER_REVIEW_REQUIRED"
  },
  {
    "id": "L01",
    "category": "LEGAL_OUTCOME",
    "question": "What legal actions apply?",
    "answer": "The violation is proven. The official must prosecute [DOC-1-P1].",
    "documents": [
      {
        "record_id": "DOC-1-P1",
        "record_type": "PDF_KNOWLEDGE",
        "document_type": "REGULATION",
        "title": "Synthetic electoral guidance",
        "source_excerpt": "Pasal 21 election procedure.",
        "review_status": "OFFICER_REVIEWED",
        "legal_election_type": "BOTH",
        "legal_version_label": "Synthetic v1",
        "legal_effective_date": "2026-01-01"
      }
    ],
    "expected_present": [
      "LEGAL_OUTCOME_OR_ACTION"
    ],
    "expected_absent": [],
    "expected_status": "OFFICER_REVIEW_REQUIRED"
  },
  {
    "id": "L02",
    "category": "LEGAL_OUTCOME",
    "question": "What legal actions apply?",
    "answer": "Pasal 21 [DOC-1-P1].",
    "documents": [
      {
        "record_id": "DOC-1-P1",
        "record_type": "PDF_KNOWLEDGE",
        "document_type": "REGULATION",
        "title": "Synthetic electoral guidance",
        "source_excerpt": "Pasal 21 election procedure.",
        "review_status": "OFFICER_REVIEWED",
        "legal_election_type": "BOTH",
        "legal_version_label": "Synthetic v1",
        "legal_effective_date": "2026-01-01"
      }
    ],
    "expected_present": [],
    "expected_absent": [
      "LEGAL_OUTCOME_OR_ACTION"
    ],
    "expected_status": "OFFICER_REVIEW_REQUIRED"
  },
  {
    "id": "V01",
    "category": "VERSION_METADATA",
    "question": "What legal law applies?",
    "answer": "Pasal 21 [DOC-1-P1].",
    "documents": [
      {
        "record_id": "DOC-1-P1",
        "record_type": "PDF_KNOWLEDGE",
        "document_type": "REGULATION",
        "title": "Synthetic electoral guidance",
        "source_excerpt": "Pasal 21 election procedure.",
        "review_status": "OFFICER_REVIEWED",
        "legal_election_type": "BOTH",
        "legal_version_label": "",
        "legal_effective_date": ""
      }
    ],
    "expected_present": [
      "VERSION_OR_EFFECTIVE_DATE"
    ],
    "expected_absent": [],
    "expected_status": "OFFICER_REVIEW_REQUIRED"
  },
  {
    "id": "V02",
    "category": "VERSION_METADATA",
    "question": "What legal law applies?",
    "answer": "Pasal 21 [DOC-1-P1].",
    "documents": [
      {
        "record_id": "DOC-1-P1",
        "record_type": "PDF_KNOWLEDGE",
        "document_type": "REGULATION",
        "title": "Synthetic electoral guidance",
        "source_excerpt": "Pasal 21 election procedure.",
        "review_status": "OFFICER_REVIEWED",
        "legal_election_type": "BOTH",
        "legal_version_label": "Synthetic v1",
        "legal_effective_date": "2026-01-01"
      }
    ],
    "expected_present": [],
    "expected_absent": [
      "VERSION_OR_EFFECTIVE_DATE"
    ],
    "expected_status": "OFFICER_REVIEW_REQUIRED"
  },
  {
    "id": "X01",
    "category": "NONLEGAL_CONTROL",
    "question": "Summarize these saved social posts",
    "answer": "Source [SOCIAL-1].",
    "documents": [
      {
        "record_id": "SOCIAL-1",
        "record_type": "SOCIAL_LISTENING",
        "source_excerpt": "Saved public discussion."
      }
    ],
    "expected_present": [],
    "expected_absent": [],
    "expected_status": "NOT_APPLICABLE"
  },
  {
    "id": "X02",
    "category": "SOURCE_ELIGIBILITY",
    "question": "What legal law applies?",
    "answer": "Pasal 21 [DOC-99-P1].",
    "documents": [
      {
        "record_id": "DOC-1-P1",
        "record_type": "PDF_KNOWLEDGE",
        "document_type": "REGULATION",
        "title": "Synthetic electoral guidance",
        "source_excerpt": "Pasal 21 election procedure.",
        "review_status": "OFFICER_REVIEWED",
        "legal_election_type": "BOTH",
        "legal_version_label": "Synthetic v1",
        "legal_effective_date": "2026-01-01"
      }
    ],
    "expected_present": [
      "ELIGIBLE_LEGAL_SOURCE_MISSING",
      "CITATION_INTEGRITY"
    ],
    "expected_absent": [],
    "expected_status": "OFFICER_REVIEW_REQUIRED"
  }
]''')
EXPECTED_SCHEMA="BAWASLU_SYNTHETIC_LEGAL_SIGNAL_BENCHMARK_V1530"

def run_legal_signal_benchmark():
    results=[]
    confusion=Counter()
    coverage=Counter()
    for case in CORPUS:
        visible,cited,ground=audit_assistant_answer(
            case["question"],case["documents"],case["answer"],
            profile="PDF_GUIDANCE",language="en")
        quality=evaluate_answer_quality(case["question"],case["documents"],
                                       visible,cited,profile="PDF_GUIDANCE",
                                       grounding=ground)
        review=quality["legal_review_summary"]
        observed={x["code"] for x in review["issues"]}
        present=set(case["expected_present"])
        absent=set(case["expected_absent"])
        if present & absent:
            raise ValueError("A case cannot expect the same signal present and absent")
        actual_status=review["status"]
        checks=[]
        for label in sorted(present):
            hit=label in observed
            confusion["TP" if hit else "FN"]+=1
            checks.append({"code":label,"expected":"PRESENT","matched":hit})
        for label in sorted(absent):
            hit=label not in observed
            confusion["TN" if hit else "FP"]+=1
            checks.append({"code":label,"expected":"ABSENT","matched":hit})
        status_matched=actual_status==case["expected_status"]
        coverage[case["category"]]+=1
        results.append({"id":case["id"],"category":case["category"],
                        "expected_signal_checks":checks,
                        "expected_status":case["expected_status"],
                        "observed_status":actual_status,
                        "status_matched":status_matched,
                        "case_matched":status_matched and all(x["matched"] for x in checks),
                        "observed_issue_codes":sorted(observed),
                        "expected_issue_present":sorted(present),
                        "expected_issue_absent":sorted(absent),
                        "synthetic_only":True})
    tp,tn,fp,fn=[confusion[k] for k in ("TP","TN","FP","FN")]
    checks=tp+tn+fp+fn
    match=tp+tn
    return {"schema":EXPECTED_SCHEMA,
            "dataset_kind":"DEVELOPER_LABELED_SYNTHETIC_SCENARIOS",
            "dataset_contains_real_case_data":False,
            "human_gold_answers_evaluated":0,
            "human_acceptance_complete":False,
            "real_model_answers_generated":False,
            "real_model_accuracy_measured":False,
            "real_corpus_legal_applicability_verified":False,
            "statistically_representative":False,
            "number_of_cases":len(results),
            "case_checks_matched":sum(x["case_matched"] for x in results),
            "case_checks_failed":sum(not x["case_matched"] for x in results),
            "labeled_signal_assertions":checks,
            "matched_signal_assertions":match,
            "signal_assertion_agreement_percent":round(100*match/checks,1) if checks else None,
            "synthetic_signal_precision":round(tp/(tp+fp),3) if tp+fp else None,
            "synthetic_signal_recall":round(tp/(tp+fn),3) if tp+fn else None,
            "signal_confusion":{"true_positive":tp,"true_negative":tn,
                                "false_positive":fp,"false_negative":fn},
            "category_counts":dict(sorted(coverage.items())),
            "cases":results,
            "paid_ai_calls":0,"database_writes":0,
            "crawls":0,
            "status":"SYNTHETIC_QA_ONLY_REQUIRES_INDEPENDENT_HUMAN_BENCHMARK"}
