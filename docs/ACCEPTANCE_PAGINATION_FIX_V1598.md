# v159.8 — align frontend QA with paginated audit history

v159.7 passed 1,048 backend tests but failed frontend QA because the v159.6 static contract still expected the old warning that older items were inaccessible. The UI now offers Older records navigation and explicitly notes that older submissions are available on the next page. Update the old contract to assert the new accurate wording, preserving the rest of its approval safeguards and QA. No database mutation and no human acceptance claimed.
