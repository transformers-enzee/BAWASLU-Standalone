# BAWASLU v149.2 - Offline Independent Officer Scoring Workbench

## Purpose
Close the workflow gap between v148.6 original question-answer-evidence exports and v148.7 local multi-reviewer consolidation. This is a tool for **genuine** officer review, not synthetic evaluation or automated scoring.

## Delivered
- AI Assistant now includes a collapsed **Prepare independent officer scoring sheet** panel.
- Import exactly one v148.5-compatible evidence packet JSON locally. Validation checks the original question, answer, expected four dimensions and noncryptographic packet ID. Each file is capped at 2 MB.
- Read the original AI question/answer, cited IDs and available source URLs. Actual source verification takes place outside the software; no claim of correctness or legal currentness is made.
- Enter reviewer ID and personally assign four scores (0/1/N/A), reference the original evidence for scores 0/1 and provide a 12+ character explanation for every score.
- Export a completed CSV compatible with existing v148.7 Human answer-review consolidation. The CSV intentionally contains only scoring fields and packet ID, not the answer or source excerpts.
- The reviewer must explicitly check a self-attestation box before export. Any score edit resets the check. Identity, authorization and signature are **not verified** by this local UI.
- Validation is shared with the existing CSV importer; formula-leading spreadsheet cells are escaped. No API call, Supabase write, AI charge, crawler or local browser storage is involved.

## Officer procedure
1. Log into the staging AI Assistant with the authorized account.
2. Prepare an original saved-source question and manually select **Send**. Sending may use paid AI credit; preparation alone does not.
3. Export its **JSON evidence packet** and retain it securely.
4. Reviewer A loads the packet into the new scoring workbench, personally checks original sources, completes all four rating dimensions, attests and exports CSV.
5. Reviewer B independently repeats step 4 using a separate account/identity and the same original evidence packet.
6. An authorized coordinator imports the one original packet plus both reviewer CSV files into **Human answer-review consolidation**. Disagreement needs an independent adjudicator using the existing adjudication CSV columns.
7. Keep all case records and source excerpts in approved custody. The minimized aggregate contains no answers or excerpts. Human acceptance remains incomplete until genuine personnel verify outcomes.

## Acceptance and limits
- Four completed ratings and a locally claimed reviewer ID do not equal authenticated officer approval.
- Human acceptance: **0/3 DONE** until actual AI answers are rated, real officer casework approved and legal PDFs reviewed.
- Tests must verify CSV roundtrip through the current consolidation parser, N/A, incomplete inputs, formula injection defenses, zero provider calls and no raw-answer data in scoring CSV.
- The batch updates only the staging branch \`architecture-v2-foundation-20261015\` with sequential build v149.2. Render exact-commit deployment must be verified independently before claiming LIVE.
