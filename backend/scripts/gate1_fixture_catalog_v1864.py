"""v186.4: fictional QA scenarios for disposable Gate 1 PostgreSQL CI only.

Never seed shared Supabase or Render databases using these fixtures. The source
provider and marker exist exclusively for isolated acceptance tests.
"""
QA_SCENARIOS = (
    ("UNCERTAIN", "UNCERTAIN", "NEUTRAL",
     "Fictional local election forum: an unclear claim about a fictional campaign notice."),
    ("EXCLUDED", "IRRELEVANT", "NEUTRAL",
     "Fictional gardening discussion unrelated to election monitoring."),
    ("RELEVANT", "RELEVANT", "NEGATIVE",
     "Fictional election discussion: residents ask about a fictional candidate debate."),
    ("HIGHLY_RELEVANT", "HIGHLY_RELEVANT", "POSITIVE",
     "Fictional election forum: organizers announce a simulated election information session."),
    ("UNASSESSED", None, None,
     "Fictional election discussion with no saved AI assessment for a missing-label QA check."),
)
