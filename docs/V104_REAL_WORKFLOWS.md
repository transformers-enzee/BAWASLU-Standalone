# v104 actual functional work across the 3 open items

12: The real production campaign assessment prompt now requests 1-2 quote-backed player drafts in the *same* paid inference response when source warrants; never forces a hallucinated quote, and no extra provider request is made for a summary. Saved historical results remain unchanged; live production sample and officer review still required.

13: Shared source-lineage resolver supports canonical radar:* sources using existing nationwide-protected, cached original pilot source rows, while keeping separate IDs and explicitly reporting no social mapping. The approved V6.2 Radar UI remains untouched. Not a fabricated crosswalk.

14: The actual v18 exemplar-audit path is now available when an immutable admin-approved v18 prompt exists, with model-key/feature-flag gates and 15-item per-request bound. v17 scores immutable; v18 is a new independent run, and benchmark accuracy is not improved until executed. Historic optional pilot prompt changes did not cover this QA path.
