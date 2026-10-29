# v102.5 SQLite bootstrap migration fix

Staging initial deployment failed because the base schema already had sentiment_confidence, sentiment_explanation and sentiment_model; the following Alembic migration tried to re-add them. Inspect columns before additive operations. This also handles partial migrations. Preserve existing columns in downgrade rather than dropping baseline fields. Production postgres is left untouched by this commit, and existing migration behavior is additive. Staging must be explicitly redeployed (autoDeploy disabled) and health verified before closure.
