"""Source-controlled assistant workflow contract for management/operations.

Read-only and schema-free: no case assignment, legal determination or sending.
Explicit source opt-outs are enforced server-side and may not be bypassed by
heuristic answer routing. Source labels say what was ACTUALLY consulted.
"""
import re

WORKFLOW_MODES=('AUTO','RESEARCH','STRATEGY_DRAFTING')
SOURCE_KEYS=('smartRadar','publicWeb','legalReferences','attachments')
CITE=re.compile(r'\[(INT-[A-Za-z0-9:_-]+|SOCIAL-[0-9]+|DOC-[0-9]+-P[0-9]+|ATT-[a-f0-9]{32}-S[0-9]+)\]')


def infer_workflow(question,previous='',history=None):
    """Choose an answer workflow from the request, not the user's workspace.

    This is presentation guidance, not an authorization or legal classification.
    Follow-up editing retains the draft workflow without trusting AI answers as facts.
    """
    current=str(question or '').strip().casefold()
    draft=(r'\b(draft|write|compose|memo|email|letter|report|briefing|'
           r'summarise|summarize|rewrite|revise|polish|translate|'
           r'surat|nota dinas|ringkas|persingkat|terjemahkan|'
           r'buatkan laporan|buatkan memo|balas email)\b')
    strategy=(r'\b(strategy|strategic|options|recommend|recommendation|'
              r'tactic|tactics|action plan|roadmap|solution|milestone|'
              r'strategi|opsi|rekomendasi|solusi|taktik|rencana aksi|'
              r'rencana tindak lanjut|langkah tindak lanjut)\b')
    if re.search(draft,current,re.I) or re.search(strategy,current,re.I):
        return 'STRATEGY_DRAFTING'
    if re.search(r'\b(shorten|make it shorter|change the tone|turn it into|'
                 r'ubah menjadi|jadikan|perpendek)\b',current,re.I):
        recent=[str(x.get('text') or '') for x in (history or [])
                if isinstance(x,dict) and x.get('role')=='user']
        recent.append(str(previous or ''))
        if any(re.search(draft+'|'+strategy,x,re.I) for x in recent[-5:]):
            return 'STRATEGY_DRAFTING'
    return 'RESEARCH'


def normalize_workflow_request(body):
    if not isinstance(body,dict):
        raise ValueError('Assistant request must be an object')
    requested_workflow=str(body.get('workflowMode') or 'RESEARCH').upper()
    if requested_workflow not in WORKFLOW_MODES:
        raise ValueError('Choose Research & Analysis or Strategy & Drafting')
    raw=body.get('sourceSelection')
    explicit=raw is not None
    if raw is None:
        raw={'smartRadar':True,'publicWeb':False,'legalReferences':True,'attachments':True}
    if not isinstance(raw,dict) or any(k not in SOURCE_KEYS for k in raw):
        raise ValueError('Invalid assistant source selector')
    if any(type(v) is not bool for v in raw.values()):
        raise ValueError('Source selection must use true/false values')
    sources={k:bool(raw.get(k,False)) for k in SOURCE_KEYS}
    if not any(sources.values()):
        raise ValueError('Select at least one authorized source category')
    workflow=(infer_workflow(body.get('question'),body.get('previousQuestion'),
             body.get('conversationContext')) if requested_workflow=='AUTO' else requested_workflow)
    return {'workflow':workflow,'requested_workflow':requested_workflow,
            'sources':sources,'explicit':explicit}


def workflow_system_directive(workflow):
    if workflow=='STRATEGY_DRAFTING':
        return (
            '\n\nMANAGEMENT STRATEGY & DRAFTING WORKFLOW (DRAFT ONLY): '
            'Begin with source-supported findings and state contrary evidence and unknowns. '
            'When the user requests strategic options, compare at least two defensible nonpartisan oversight options, including '
            'a lower-intervention option when plausible. State concrete trade-offs, '
            'recommend a CONDITIONAL option, and explain its evidence gate. '
            'For an action plan or strategy request, propose a reviewing owner ROLE (never invent '
            'a named assignee), milestone or proposed review interval (label '
            'as a proposal, not an official deadline), expected deliverable, '
            'and explicit management review checkpoint. '
            'For a requested summary, memo, report or email, lead with the deliverable itself; provide '
            'a polished DRAFT suitable for officer review, carrying citations '
            'and unresolved caveats rather than implying approval or delivery. '
            'Follow-up edits can shorten or reformat the preceding draft, but '
            'prior assistant assertions are NOT evidence; recheck against this '
            'turn’s authorized source records. Never send a message, create '
            'an assignment, make a legal determination or claim official approval.')
    return (
        '\n\nRESEARCH & ANALYSIS WORKFLOW: Describe what selected sources '
        'actually report, separate allegation vs officer-reviewed events vs '
        'inference, list source citations per material finding, identify '
        'contradictions, potential duplicate reporting, missing incident '
        'location and timestamp limitations. Compare dates only on a '
        'specified consistent basis and never infer trends from a bounded '
        'sample. Present what remains uncertain before recommending '
        'bounded officer verification.')


def source_consultation(selection,evidence=(),cited=(),public_urls=(),environment='LIVE'):
    evidence=[r for r in evidence or [] if isinstance(r,dict)]
    ids={str(r.get('record_id') or '') for r in evidence}
    cited_ids={str(x) for x in cited or []}&ids
    types={str(r.get('record_type') or '') for r in evidence}
    groups={
        'smartRadar': [r for r in evidence if r.get('record_type') not in ('PDF_KNOWLEDGE','CHAT_ATTACHMENT')],
        'attachments':[r for r in evidence if r.get('record_type')=='CHAT_ATTACHMENT'],
        'legalReferences': [r for r in evidence if r.get('record_type')=='PDF_KNOWLEDGE'],
    }
    result=[]
    for key,label in [('smartRadar','Saved SmartRadar/BAWASLU intelligence'),
                      ('publicWeb','Public web/social research'),
                      ('legalReferences','Authorized legal/reference library'),
                      ('attachments','Conversation attachments')]:
        requested=bool(selection.get(key))
        matched=groups.get(key,[])
        if key=='publicWeb':
            urls=[x for x in (public_urls or []) if isinstance(x,str) and x.startswith('https://')][:6]
            actually=bool(urls)
            count=len(urls)
            basis='LIVE_PUBLIC_LOOKUP' if actually else 'NOT_CONSULTED'
        else:
            actually=bool(matched)
            count=len(matched)
            basis=('SIMULATED_DEMO' if environment=='SIMULATED' else
                   'USER_SUPPLIED_UNVERIFIED' if key=='attachments' else
                   'FIXED_SAVED_SNAPSHOT') if actually else 'NOT_CONSULTED'
        result.append({'key':key,'label':label,
                       'requested':requested,
                       'status':('NOT_SELECTED' if not requested else
                                 'CONSULTED' if actually else 'SELECTED_NOT_CONSULTED'),
                       'basis':basis if requested else 'NOT_SELECTED',
                       'selected_count':count if requested else 0,
                       'cited_source_ids':[r['record_id'] for r in matched
                           if r.get('record_id') in cited_ids][:12]
                           if requested else [],
                       'urls':urls if key=='publicWeb' and requested else [],
                       'warning':('Public search returned no attributable URLs; do not claim live verification.'
                           if key=='publicWeb' and requested and not actually else
                           'Uploaded legal PDF pages are not independently certified as current official law.'
                           if key=='legalReferences' and actually else
                           'Conversation uploads/links are user-supplied. Their contents and legal force are not independently verified.'
                           if key=='attachments' and actually else '')})
    return result


def structured_findings(findings,evidence,cited,limit=5):
    """Conservative claim ledger: cites only validated IDs, never upgrades allegations."""
    allowed={str(r.get('record_id')):r for r in evidence or [] if isinstance(r,dict)}
    cited=set(cited or [])&set(allowed)
    observations=[x for x in (findings or {}).get('observations',[])
                  if isinstance(x,str) and x.strip()][:limit]
    out=[]
    for text in observations:
        refs=list(dict.fromkeys(x for x in CITE.findall(text) if x in cited))[:4]
        record_types={str(allowed[ref].get('record_type') or '') for ref in refs}
        kind=('REPORTED_ALLEGATION_OR_OBSERVATION' if 'SOCIAL_LISTENING' in record_types
              else 'USER_ATTACHED_UNVERIFIED_SOURCE' if 'CHAT_ATTACHMENT' in record_types
              else 'DOCUMENTARY_REFERENCE_REQUIRES_AUTHORITY_CHECK' if 'PDF_KNOWLEDGE' in record_types
              else 'SAVED_OFFICER_RECORD_NOT_SOURCE_AUTHENTICATION' if refs
              else 'ANALYTICAL_INFERENCE_UNCITED')
        out.append({'text':text[:900],'source_ids':refs,
                    'evidence_class':kind,
                    'support_status':'SOURCE_LINKED_NOT_FACT_VERIFIED' if refs else 'NO_VALIDATED_CITATION',
                    'requires_officer_review':True})
    return out


def drafting_notice(workflow):
    return ('DRAFT_ONLY_STAFF_REVIEW_AND_SEND'
            if workflow=='STRATEGY_DRAFTING' else 'ANALYSIS_ONLY_NO_AUTOMATED_ACTION')


_REVISE=re.compile(
    r'\b(shorten|shorter|condense|rewrite|rephrase|polish|convert|turn (?:it|this) into|'
    r'make (?:it|this) an? email|turn .{0,95}? into|email draft|write (?:a |an )?(?:memo|email)|draft (?:a |an )?(?:memo|email)|change (?:the )?audience|'
    r'ringkas|persingkat|perpendek|ubah menjadi|jadikan|'
    r'buat versi|revisi|sunting|format ulang)\b',re.I)


def retrieval_question_for_revision(question,previous='',history=None):
    """Follow-up drafting retains the latest substantive USER topic only.

    Earlier assistant text is never used as evidence. This determines which
    currently authorized records must be retrieved again for each turn.
    """
    current=str(question or '').strip()
    if not _REVISE.search(current):
        return current
    earlier=[str(m.get('text') or '').strip() for m in (history or [])
             if isinstance(m,dict) and m.get('role')=='user' and str(m.get('text') or '').strip()]
    if previous and str(previous).strip() not in earlier:
        earlier.append(str(previous).strip())
    topic=next((q for q in reversed(earlier) if not _REVISE.search(q)),None)
    return topic[:1000] if topic else current
