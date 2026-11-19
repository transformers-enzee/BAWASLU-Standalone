"""Offline, human-entered Assistant answer review aggregation.

No generation, no storage. Reviewer input is *self-attested*, NOT verified
independent expert review, model provenance, or legal authority. Only aggregate
counts are returned; source passages, answer text, and reviewer identifiers
are not exported.
"""
from collections import Counter
from .assistant_saved_reply_human_packet import DIMENSIONS

VALID_RATINGS={"PASS","FAIL","NOT_ASSESSABLE"}


def compile_human_review_scores(packet,submissions):
    """Score only complete self-attested human entries; preserve all gaps."""
    if not isinstance(packet,dict) or packet.get("schema")!="BAWASLU_AUTHORIZED_SAVED_REPLY_REVIEW_PACKET_V17488":
        raise ValueError("Only permission-scoped saved-reply review packets are supported")
    tasks=packet.get("items")
    if not isinstance(tasks,list) or not 1<=len(tasks)<=5:
        raise ValueError("Packet must contain one to five review tasks")
    if not isinstance(submissions,list) or len(submissions)>5:
        raise ValueError("Submissions must be a bounded list")
    known=set()
    for task in tasks:
        if not isinstance(task,dict):
            raise ValueError("Invalid packet task")
        thread_id=task.get("thread_id")
        index=task.get("answer_message_index")
        if not isinstance(thread_id,str) or not isinstance(index,int) or isinstance(index,bool) or not 1<=index<=59:
            raise ValueError("Invalid packet task identifier")
        key=(thread_id,index)
        if key in known:
            raise ValueError("Duplicate packet task")
        known.add(key)
    seen=set()
    outcomes=Counter()
    dimension_counts={name:Counter() for name in DIMENSIONS}
    for item in submissions:
        if not isinstance(item,dict):
            raise ValueError("Invalid reviewer submission")
        thread_id=item.get("thread_id")
        index=item.get("answer_message_index")
        if not isinstance(thread_id,str) or not isinstance(index,int) or isinstance(index,bool):
            raise ValueError("Invalid submitted selection identifier")
        key=(thread_id,index)
        if key not in known or key in seen:
            raise ValueError("Submission outside selected packet or duplicated")
        seen.add(key)
        ratings=item.get("ratings")
        # No partial ratings can be silently counted as full completion.
        if not isinstance(ratings,dict) or set(ratings)!=set(DIMENSIONS):
            outcomes["INCOMPLETE_REVIEW"]+=1
            continue
        if any(not isinstance(value,str) or value not in VALID_RATINGS
               for value in ratings.values()):
            outcomes["INCOMPLETE_REVIEW"]+=1
            continue
        if (item.get("source_access_rechecked") is not True or
                item.get("source_material_reviewed") is not True or
                item.get("original_answer_reviewed") is not True or
                item.get("independent_review_attested") is not True):
            outcomes["INCOMPLETE_REVIEW"]+=1
            continue
        for name in DIMENSIONS:
            dimension_counts[name][ratings[name]]+=1
        if "FAIL" in ratings.values():
            outcomes["HUMAN_REPORTED_ISSUES"]+=1
        elif "NOT_ASSESSABLE" in ratings.values():
            outcomes["HUMAN_REPORTED_NOT_ASSESSABLE"]+=1
        else:
            outcomes["HUMAN_REPORTED_ALL_DIMENSIONS_PASS"]+=1
    outcomes["NOT_SUBMITTED"]=len(tasks)-len(submissions)
    return {
        "schema":"BAWASLU_HUMAN_REVIEW_COUNTS_V17492",
        "selected_replies":len(tasks),
        "complete_self_attested_reviews":sum(outcomes[key] for key in (
            "HUMAN_REPORTED_ISSUES","HUMAN_REPORTED_NOT_ASSESSABLE",
            "HUMAN_REPORTED_ALL_DIMENSIONS_PASS")),
        "review_disposition_counts":dict(sorted(outcomes.items())),
        "dimension_rating_counts":{k:dict(sorted(v.items()))
                                   for k,v in dimension_counts.items()},
        "human_attestation_is_independently_verified":False,
        "server_source_access_is_not_reviewer_inspection":True,
        "source_truth_verified_by_system":False,
        "review_sample_is_representative":False,
        "formal_legal_signoff":False,
        "formal_client_acceptance":False,
        "release_approved":False,
        "model_output_provenance_verified":False,
        "model_calls":0,
        "database_writes":0,
    }
