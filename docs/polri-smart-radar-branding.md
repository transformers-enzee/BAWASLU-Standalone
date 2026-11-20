# POLRI Smart Radar standalone demo branding (v175.53)
- Scope: only Dockerfile.polri-demo / VITE_POLRI_DEMO=1. The operational BAWASLU application and /demo remain unchanged.
- Browser title: Smart Radar. Organization: POLRI. Demo guide: explicitly unofficial and read-only.
- A small stylized POLRI emblem image, recreated from the supplied POLRI emblem reference, is committed as frontend/public/polri-logo.png to avoid build-time external download failures. It should be replaced with an approved canonical high-resolution logo asset before formal institutional distribution.
- Source example evidence is unchanged; provenance remains clear as a sanitized BAWASLU training snapshot, not genuine POLRI intelligence.
- The POLRI image build must complete and browser QA must pass before changing the existing POLRI Render service to the immutable SHA image. Do not modify BAWASLU staging or production or attach a database.
