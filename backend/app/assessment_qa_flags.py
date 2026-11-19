"""Conservative, read-only relevance explanation QA flags.

These are review flags, never automated classification overrides. A mention of
an election does not by itself establish BAWASLU jurisdiction or a violation.
"""
import re

ELECTION_ANCHOR = re.compile(
    r"\b(?:pemilu|pilpres|pilkada|cawapres|capres|caleg|"
    r"bawaslu|kpu|election|electoral|presidential election)\b", re.I)
NEGATES_ELECTION = re.compile(
    r"(?:does not discuss|does not mention|does not pertain to|"
    r"not related to|lacks explicit)[^.!?]{0,105}"
    r"(?:elector|election|candidate|pilpres|pemilu|politic)", re.I)


def relevance_explanation_flags(post_text, relevance_label, explanation):
    """Return reason codes for officer QA; do not infer a correct label."""
    text = str(post_text or "")
    rationale = str(explanation or "")
    label = str(relevance_label or "").upper()
    flags = []
    if ELECTION_ANCHOR.search(text) and label == "IRRELEVANT":
        flags.append("ELECTION_MENTION_DISMISSED")
        if NEGATES_ELECTION.search(rationale):
            flags.append("EXPLANATION_CONTRADICTS_ELECTION_MENTION")
    elif ELECTION_ANCHOR.search(text) and label == "UNCERTAIN":
        if NEGATES_ELECTION.search(rationale):
            flags.append("UNCERTAIN_EXPLANATION_OMITS_ELECTION_MENTION")
    if not rationale.strip() and label in ("RELEVANT", "IRRELEVANT", "UNCERTAIN"):
        flags.append("MISSING_EXPLANATION")
    return flags
