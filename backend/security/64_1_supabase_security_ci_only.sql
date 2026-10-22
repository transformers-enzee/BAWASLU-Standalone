-- BAWASLU Build 64.1: EPHEMERAL CI/STAGING TEST ONLY.
-- Never wire this file into Render startup or Alembic production upgrades.
-- BAWASLU frontend uses its own API; direct PostgREST roles must not access
-- backend-owned evidence, authentication, user or intelligence tables.
BEGIN;
DO $guard$
BEGIN
  IF current_database() <> 'bawaslu_security_ci' OR
     current_setting('bawaslu.stage_approved',true) IS DISTINCT FROM 'yes' OR
     current_setting('bawaslu.stage_name',true) IS DISTINCT FROM 'CI_EPHEMERAL'
  THEN
    RAISE EXCEPTION 'Blocked: this security test script is only for the ephemeral CI database';
  END IF;
  IF current_user <> 'postgres' THEN
    RAISE EXCEPTION 'Expected CI-owned postgres role';
  END IF;
END
$guard$;

REVOKE ALL PRIVILEGES ON TABLE
  public.access_grants,
  public.alembic_version,
  public.audit_events,
  public.data_sources,
  public.entity_relationships,
  public.evidence_files,
  public.external_data_connectors,
  public.intelligence_items,
  public.intelligence_sequences,
  public.issue_categories,
  public.migration_batches,
  public.migration_staging_records,
  public.session_tokens,
  public.social_listening_provider_usage,
  public.social_listening_results,
  public.social_listening_rules,
  public.social_listening_runs,
  public.source_accounts,
  public.triage_generations,
  public.users,
  public.watchlist_items,
  public.monitoring_campaigns,
  public.campaign_runs,
  public.campaign_evidence,
  public.evidence_assessments,
  public.evidence_reviews,
  public.issue_category_phrases
FROM anon, authenticated;

ALTER TABLE public.access_grants ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.alembic_version ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.audit_events ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.data_sources ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.entity_relationships ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.evidence_files ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.external_data_connectors ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.intelligence_items ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.intelligence_sequences ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.issue_categories ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.migration_batches ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.migration_staging_records ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.session_tokens ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.social_listening_provider_usage ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.social_listening_results ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.social_listening_rules ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.social_listening_runs ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.source_accounts ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.triage_generations ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.users ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.watchlist_items ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.monitoring_campaigns ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.campaign_runs ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.campaign_evidence ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.evidence_assessments ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.evidence_reviews ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.issue_category_phrases ENABLE ROW LEVEL SECURITY;
COMMIT;
