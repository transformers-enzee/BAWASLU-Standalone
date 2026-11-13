# BAWASLU v151.2 - legal question trigger regression correction

v151.1 introduced citation-coverage status for legal questions without a PDF, but CI exposed that the existing _LEGAL_QUESTION regular expression did not recognize the standalone English word "law". "Explain the applicable law" incorrectly produced NO_CITED_EVIDENCE and no officer source-review step.

This patch adds the standalone word to the existing word-boundary-based legal-question detector. Focused tests cover "law", "laws", election law and Indonesian hukum along with ordinary nonlegal workflow queries to guard against accidental legal guidance. No changes to paid AI, social crawl, authorization policy, legal action behavior, reporting data or database schema.

The original v151.1 formal record evidence-chain checklist and source-coverage updates remain intact. Next sequential build 151.2, staging only.
