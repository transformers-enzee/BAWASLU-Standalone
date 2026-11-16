# v160.3 — Local standalone citation checks for platform-policy verdicts

Existing v160.1 review signals caught definitive platform-policy verdicts supported by legal PDF citations on the same line, but missed a PDF citation on the immediately following standalone line. The verifier now checks this second, narrow local-attribution form. A subsequent narrative sentence or an uncited/unselected/document-ineligible source cannot act as a claim-local legal citation.

The signal is warning-only and requires independent officer verification of provider rules and original content. It does not establish breach, legal applicability, provider policy currentness, human accuracy or formal client signoff. Adversarial regression tests cover English/Indonesian wording, quoted claims, uncertainty, reports, excluded references and mixed document types. No model credits or live data writes are involved.
