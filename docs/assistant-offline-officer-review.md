# BAWASLU Offline AI Assistant Officer Review

This is a **local, human-led review**, not an AI judge or automatic legal determination. Do not upload source passages, saved answers, review packets or completed submissions to GitHub Actions, issues, pull requests, or public artifacts.

1. On an authorized officer workstation, export an explicitly selected, permission-scoped saved-reply human review packet from the application. Confirm current access to each original answer and source, including exact PDF pages and document versions. Do not use arbitrary saved history or synthetic fixtures as evidence of real-answer accuracy.
2. From the `backend` directory, run:

   ```bash
   python -m app.assistant_human_review_template --packet /secure/review-packet.json --output /secure/blank-submissions.json
   ```

3. Independently read each **original** saved answer and its authorized source documents. For every dimension in `ratings`, replace `null` with `PASS`, `FAIL`, or `NOT_ASSESSABLE`. Confirm a citation identifies the correct source **and** that its claims are actually supported; identifier matching alone is insufficient.
4. Set each boolean attestation to `true` only after personally completing the stated review. Keep unresolved issues and missing source access as incomplete or `NOT_ASSESSABLE`; never fill ratings automatically.
5. Compile a redacted aggregate on the same trusted workstation:

   ```bash
   python -m app.assistant_human_review_cli --packet /secure/review-packet.json --submissions /secure/completed-submissions.json --output /secure/review-counts.json
   ```

The output intentionally cannot establish independent verification, representativeness, genuine model provenance, formal legal sign-off, or release approval. Check the answer revision token and current source authorization before rating. Preserve private inputs within approved storage; the aggregated counts alone do not establish model accuracy.

**Important:** The review packet contains selected answer identifiers and revision tokens. Even without raw answer text it is sensitive operational metadata; do not commit it.
