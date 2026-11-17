"""Question-specific instructions, not a legal or platform-policy verdict."""
import re
LEGAL=re.compile(r"\b(?:hukum|pidana|pasal|perbawaslu|undang[ -]?undang|sanksi hukum|legal|electoral law|election law|statut(?:e|ory)|regulations?|pelanggaran pemilu|tindak lanjut hukum)\b",re.I)
PLATFORM=re.compile(r"\b(?:facebook|instagram|tiktok|tik tok|twitter|youtube|social media|media sosial|platform)\b",re.I)
POLICY=re.compile(r"\b(?:polic(?:y|ies)|community guidelines|community standards|terms of service|platform rules|content moderation|takedown|moderasi|penghapusan|aturan komunitas|ketentuan platform|kebijakan platform|aturan media sosial|kebijakan media sosial)\b",re.I)
ENFORCEMENT=re.compile(r"\b(?:viola(?:te|tion|ted)|breach(?:es|ed)?|melanggar|pelanggaran|report|laporkan|laporan|tindak lanjut)\b",re.I)
RULE=re.compile(r"\b(?:rules?|guidelines|policies|kebijakan|aturan)\b",re.I)

def assessment_scope(question):
    """A platform mention alone does not trigger a policy assessment."""
    q=str(question or "")[:1000]
    legal=bool(LEGAL.search(q))
    platform=bool(PLATFORM.search(q) and (POLICY.search(q) or
        (ENFORCEMENT.search(q) and RULE.search(q))))
    if legal and platform:return "MIXED_LEGAL_AND_PLATFORM"
    if legal:return "LEGAL_ONLY"
    if platform:return "PLATFORM_ONLY"
    return "GENERAL"

def assessment_instruction(question,response_profile):
    scope=assessment_scope(question)
    if scope=="GENERAL":return ""
    subject={
       "MIXED_LEGAL_AND_PLATFORM":"Separate electoral-law implications and platform moderation: neither determines the other.",
       "LEGAL_ONLY":"Address requested legal implications without inferring a platform-policy breach.",
       "PLATFORM_ONLY":"Address a provider's policy, not an election-law verdict.",
    }[scope]
    pdf=response_profile=="PDF_GUIDANCE"
    return (
       "OPERATIONAL ASSESSMENT (not approval): "+subject+" "
       "Answer in the user's language, concisely for a simple question. For a substantive assessment: "
       "1) OBSERVED RECORD: Describe precisely what authorized posts, formal records or PDF pages establish, "
       "attach exact selected source IDs to empirical claims and label unverified allegations. "
       "2) POSSIBLE RULE: Cite only an applicable provision actually present in selected eligible legal-reference PDF pages "
       "or an official current platform-policy source in supplied external research. An internal legal PDF cannot establish "
       "the text of Instagram, TikTok or Facebook community standards. If specific policy text or legal provisions "
       "are absent, disclose that text/currentness is unverified, not a definite breach or legal ruling. "
       "3) EVIDENCE GAPS: Identify missing context, provenance, incident jurisdiction, corroboration, rule version "
       "and applicability. 4) OFFICER NEXT CHECK: Preserve original content and timestamp, check incident locus "
       "and source context, verify the CURRENT official rule, and use authorized BAWASLU or platform review channels "
       "where warranted. Do not recommend automatic takedown, arrest or sanctions from monitoring signals. "
       +("For procedural PDF guidance, use only supplied PDF_KNOWLEDGE excerpts as documentary authority; "
          "keep the answer short and disclose gaps in platform policy evidence. " if pdf else
          "Put the assessment in direct_answer; avoid repeating the same material in observations, "
          "interpretation, next_checks, or limitations. ")
    )

def assessment_authority_inventory(evidence):
    """Supplied record counts are not a legal, policy or truth certification."""
    records=[r for r in (evidence or []) if isinstance(r,dict)]
    return {
      "social_post_count":sum(r.get("record_type")=="SOCIAL_LISTENING" for r in records),
      "formal_intelligence_count":sum(r.get("record_type")=="FORMAL_INTELLIGENCE" for r in records),
      "legal_reference_page_count":sum(r.get("record_type")=="PDF_KNOWLEDGE" and r.get("document_type") in {"REGULATION","SOP","GUIDANCE"} for r in records),
      "contextual_pdf_page_count":sum(r.get("record_type")=="PDF_KNOWLEDGE" and r.get("document_type") not in {"REGULATION","SOP","GUIDANCE"} for r in records),
      "official_policy_currentness_verified":False,
      "legal_applicability_verified":False,
      "source_truth_verified":False,
    }
