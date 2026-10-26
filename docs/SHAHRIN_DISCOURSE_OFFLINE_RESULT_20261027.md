# Shahrin reference matching: negative offline result

Date: 2026-10-27. Development-only audit; sealed holdout untouched. No model inference.

- Cohort: 13 Shahrin-labelled development posts; reference candidates limited to eligible exemplars with distinct source hashes and URLs.
- Existing token-Jaccard nearest example matched the target's Shahrin category for **4/13 (30.8%)**.
- Seven interpretable discourse-feature signatures (court, allegation, institutional process, inclusive access, oversight, digital information, voter register), ranked by feature Jaccard and then lexical similarity, matched for **2/13 (15.4%)**.
- This is *nearest-reference category agreement*, **not AI classifier accuracy**. The patterns were exploratory; this is not a valid prospective accuracy estimate.
- Failure mode: coarse feature overlap conflates distinct statement intents, and feature ties can rank unrelated examples ahead of lexical matches.

Decision: Do not wire discourse-feature ranking into V11 or enable its paid test. Keep `BAWASLU_QA_V2_PAID_TEST_APPROVED` unset. Retain `smart_radar_qa_discourse_audit.py` as diagnostic-only code. Any further methodology should undergo independent human review for inconsistent near-duplicate labels, and a development-only, no-provider benchmark before paid tests.
