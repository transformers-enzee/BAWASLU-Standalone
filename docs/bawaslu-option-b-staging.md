# BAWASLU Option B — GitHub-built image → existing Render staging

## Purpose and safety boundary
Use GitHub Actions to build the **existing Dockerfile** and publish a prebuilt staging image to GitHub Container Registry (GHCR). Render can then run that image without consuming Render-side build minutes. This affects **BAWASLU staging only**; no production, GovIntel, or Supabase setting is changed by this repository commit.

- Render staging service: `bawaslu-standalone-staging` (`srv-dbhfo9gu01pc73b7am6g`)
- Current URL to preserve: `https://bawaslu-standalone-staging.onrender.com`
- Image: `ghcr.io/transformers-enzee/bawaslu-standalone:staging`
- Immutable release tags: `ghcr.io/transformers-enzee/bawaslu-standalone:sha-<commit SHA>`
- Workflow: `.github/workflows/bawaslu-option-b-image.yml`
- Branch: `architecture-v2-foundation-20261015`

## Phase 1 — Verify GitHub image build (no Render deploy)
1. Open the **BAWASLU Option B - prebuilt staging image** GitHub Actions workflow on the development branch.
2. The initial push of this workflow triggers one image build. Later use **Run workflow** with **deploy_staging = false** to build release batches on demand.
3. Confirm the `Build and publish immutable staging image` step succeeds. Confirm the GHCR package exists and contains a `staging` tag and an immutable `sha-...` tag.
4. GitHub Actions may require organization permission to publish packages. Resolve any permission issue in GitHub, not by switching Render back to source builds.
5. Keep the GHCR package **private** unless the project owner explicitly approves publishing the built image. For a private package, Render needs a GitHub registry credential with `read:packages` access. If public visibility is approved, Render can pull a public GHCR image without a credential.

**Do not proceed if the image has not been built and shown to be pullable.** Image availability, registry storage, workflow quotas and any credentials can affect costs or reliability.

## Phase 2 — One-time Render dashboard change (human intervention)
This connected Render tool does not expose an update-source operation, so a Render workspace administrator must complete the following on the existing service:

1. Confirm that **staging** uses the intended isolated database and that a backup exists. The existing Dockerfile startup command runs `alembic upgrade head` automatically; a new image can perform schema migrations when first started. Do not switch sources until this risk is reviewed.
2. Open `https://dashboard.render.com/web/srv-dbhfo9gu01pc73b7am6g`, then **Settings → Build → Source → Edit**.
3. Change the source from the Git repository to **Existing Image**, using `ghcr.io/transformers-enzee/bawaslu-standalone:staging`. Attach a GitHub Container Registry credential if the image is private.
4. Keep the same service, URL, environment variables, region and access settings. Do not create a replacement public service or modify production.
5. **Saving the source change automatically starts an initial deployment.** Verify the deploy uses a prebuilt image (not a Render build), then inspect startup logs, migrations, health and authentication before proceeding.
6. In GitHub repository **Settings → Secrets and variables → Actions**, store the **Render staging deploy hook** as a secret named `RENDER_STAGING_DEPLOY_HOOK`, and set an Actions variable `BAWASLU_STAGING_IMAGE_READY` to `true` **only after** confirming the staging source is image-backed.

Never place the deploy hook, registry token, database credentials or officer records in repository files or chat. Use GitHub/Render settings to store credentials.

## Phase 3 — Future bulk deployments
1. Complete normal GitHub offline QA and Playwright checks for the staged release commit.
2. On GitHub Actions, open **BAWASLU Option B - prebuilt staging image**, select the approved development branch, and run with **deploy_staging = true**.
3. The workflow builds and pushes a prebuilt `linux/amd64` image, then uses the **staging-only** deploy hook to request the exact `sha-...` image. It refuses to deploy unless the ready variable and hook secret are configured.
4. Verify Render's final deploy status and the application's health, login, data access, API, AI Assistant and PDF behavior. A successful GitHub deploy-hook request is **not** proof the web app became healthy.
5. If verification fails, use Render's existing rollback or redeploy a previously successful immutable GHCR tag. Keep older image tags available for rollback.

## Exclusions and rollback
- Do not trigger `mcp__Render__trigger_deploy` while the service is still Git-backed: it will attempt a Render build and may hit the same quota.
- Never change the Render production service or GovIntel as part of this setup.
- Do not apply repository `render.yaml` as a Blueprint for this migration: it targets a different service and contains legacy database settings.
- A Render source switch may cause a brief interruption and database migrations; officer data must not be changed as part of a test run.
- GitHub Actions for public repositories has generally included standard runner minutes, but GHCR package visibility/storage and hosting costs must be checked under the organization's account terms.
