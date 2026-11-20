# POLRI demo subdomain — independent read-only copy of /demo (v175.44)

The goal is to keep the existing BAWASLU /demo and operational services untouched while preparing a separate, public-facing **unofficial prototype** at polri.nadicom.io. The existing BAWASLU example labels, screenshots, and frozen sample content have NOT yet been changed to POLRI; new brand/logo review is a separate approval step. Do not imply POLRI endorsement until authorized.

## Technical architecture
- Use `Dockerfile.polri-demo`, NOT the root `Dockerfile`.
- Build only the Vite frontend, serve it as static files through Nginx on port 10000. Only /demo and static assets are served; / redirects to /demo/ and /api is denied.
- The demo app's `realBridge.js` intercepts data calls and uses a sanitized fixed snapshot. The standalone build skips the demo feedback POST widget because this static service has no backend.
- No DATABASE_URL, Supabase keys, OpenAI keys, SocialCrawl keys, migrations, server authentication, workers, live customer records, or paid AI calls.
- This is a PUBLIC offline demo, not an authenticated production service. Never include confidential records or claim live results. Existing frozen training data must be approved for public display before DNS activation.

## Deployment
1. GitHub Actions workflow `POLRI subdomain - offline demo image` must succeed for the intended SHA.
2. In Render workspace Transformers, create a **new web service from Existing Image** (not a second source Docker build) using the image `ghcr.io/transformers-enzee/bawaslu-standalone:polri-demo-sha-<approved-commit>`, leave credentials empty only if the GHCR package is publicly accessible. Use Singapore, port 10000, preferably `polri-demo` service name. Do not configure environment secrets or attach Supabase.
3. Confirm Render URL responds / -> /demo/, /demo/ launches local snapshot, /api/ gives 403, /healthz = 200, and main BAWASLU login still works.
4. Add custom domain `polri.nadicom.io` to the NEW Render demo service's Settings > Custom Domains. In the nadicom.io DNS zone, set the CNAME `polri` to the Render target provided in that service's domain instructions, without changing bawaslu.nadicom.io. Verify HTTPS and DNS propagation. Do not assume the account's DNS provider or target.
5. Before sharing externally, approve demo data and replace any BAWASLU identity/wording with an explicitly authorized POLRI identity and logo; do not use an official-looking insignia without authorization.

## Maintenance
- The GitHub workflow creates a new image, but deliberately NEVER auto-deploys to Render. Review/demo QA and an explicit Render image deployment are required for updates.
- Keep the BAWASLU production and staging services independent. Avoid using mutable `:polri-demo` tag for approvals; use the immutable SHA tag.
