# v159.1 final frontend version parity repair

The v159.0 frontend build failed because the v158.8 contract still checked the literal data-build-version 158.8 despite checking a minimum backend version. Compare the frontend build marker against the actual backend version on each release instead. Keeps minimum version 158.8 requirement and all acceptance export permission checks. No operational data changes.
