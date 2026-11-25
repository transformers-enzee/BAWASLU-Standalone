"""Dependency-aware browser QA with conservative fallback to full regression."""
import json
import os
import re
import subprocess
import urllib.request

# Only explicitly mapped files qualify. Shared auth, schema, routes, API,
# fixtures, workflow/config, and unrecognized files trigger full coverage.
GROUPS = {
    "social": {
        "specs": [
            "social-listening-rules",
            "campaign-description-legacy",
            "assessment-operations-interaction",
            "assessment-pilot",
            "potential-violation-qa",
            "command-center",
            "management-briefing-interim"
        ],
        "files": [
            "backend/app/prism_discover.py",
            "backend/app/prism_full_export.py",
            "backend/app/prism_collection_budget.py",
            "backend/app/project_boolean.py",
            "backend/tests/test_prism_discover_idempotency.py",
            "backend/tests/test_prism_boolean_cost_guard_v17582.py",
            "frontend/src/pages/SocialListening.jsx",
            "frontend/src/pages/Watchlist.jsx",
            "frontend/src/pages/WatchlistPosts.jsx",
            "frontend/src/pages/WatchlistProfile.jsx",
            "frontend/src/components/intel/CampaignPanel.jsx",
            "frontend/src/components/intel/CapturedPostList.jsx",
            "frontend/src/components/intel/CampaignScheduleSummary.jsx",
            "frontend/src/components/intel/AssessmentProgressDialog.jsx",
            "frontend/src/components/intel/WatchlistMatchRow.jsx",
            "frontend/e2e/social-listening-rules.spec.js",
            "frontend/e2e/campaign-description-legacy.spec.js",
            "frontend/scripts/test-prism-boolean-guard-v17582.mjs"
        ]
    },
    "assessment": {
        "specs": [
            "social-listening-rules",
            "assessment-operations-interaction",
            "assessment-pilot",
            "potential-violation-qa",
            "command-center",
            "core-workflows",
            "management-briefing-interim",
            "ai-assistant-v2",
            "ai4",
            "ai5",
            "officer-readonly-acceptance"
        ],
        "files": [
            "backend/app/activation_assessment.py",
            "backend/app/auto_relevance.py",
            "backend/app/campaign_ai_readiness.py",
            "backend/app/assessment_claim_guard.py",
            "backend/app/assessment_job_reconcile.py",
            "backend/tests/test_assessment_claim_guard_v1673.py",
            "backend/tests/test_assessment_job_enqueue_v1650.py",
            "backend/tests/test_assessment_job_queue_v1651.py",
            "backend/tests/test_campaign_ai_readiness_v1657.py",
            "backend/tests/test_assessment_budget_guard_v1658.py",
            "frontend/src/components/intel/AssessmentOperationsPanel.jsx",
            "frontend/src/components/intel/AssessmentPilotPreview.jsx",
            "frontend/e2e/assessment-operations-interaction.spec.js",
            "frontend/e2e/assessment-pilot.spec.js"
        ]
    },
    "inbox": {
        "specs": [
            "potential-violation-qa",
            "core-workflows",
            "command-center",
            "management-briefing-interim",
            "officer-readonly-acceptance",
            "officer-decision-v1785",
            "ai5"
        ],
        "files": [
            "frontend/src/pages/Inbox.jsx",
            "frontend/src/pages/IntelligenceDetail.jsx",
            "frontend/src/components/intel/IntelligenceTable.jsx",
            "frontend/src/components/intel/PendingTriage.jsx",
            "frontend/src/components/intel/TriageReview.jsx",
            "frontend/src/components/intel/SentimentCorrection.jsx",
            "frontend/src/components/intel/DuplicatePanel.jsx",
            "frontend/e2e/potential-violation-qa.spec.js"
        ]
    },
    "assistant": {
        "specs": [
            "ai-assistant-v2",
            "ai4",
            "ai5",
            "assistant-knowledge-library",
            "officer-decision-v1785"
        ],
        "files": [
            "frontend/src/pages/AI4Assistant.jsx",
            "frontend/src/pages/AI5Assistant.jsx",
            "frontend/src/pages/AIAssistantV2.jsx",
            "frontend/src/pages/IntelligenceAssistant.jsx",
            "frontend/src/pages/UnifiedAIAssistant.jsx",
            "frontend/src/pages/OfficerDecisionAssistant.jsx",
            "frontend/e2e/ai-assistant-v2.spec.js",
            "frontend/e2e/ai4.spec.js",
            "frontend/e2e/ai5.spec.js",
            "frontend/e2e/assistant-knowledge-library.spec.js",
            "frontend/e2e/officer-decision-v1785.spec.js"
        ]
    },
    "command": {
        "specs": [
            "command-center",
            "management-briefing-interim",
            "potential-violation-qa"
        ],
        "files": [
            "frontend/src/pages/CommandCenter.jsx",
            "frontend/src/pages/SmartRadar.jsx",
            "frontend/src/components/intel/SmartRadarCharts.jsx",
            "frontend/src/components/intel/ManagementBriefings.jsx",
            "frontend/src/components/intel/TopicThemes.jsx",
            "frontend/src/components/intel/ActorIntelligence.jsx",
            "frontend/e2e/command-center.spec.js",
            "frontend/e2e/management-briefing-interim.spec.js"
        ]
    }
}

VERSION_FILES = {
    "Dockerfile": r"(ARG BAWASLU_BUILD_VERSION=)[0-9.]+",
    "backend/app/main.py": r"('BAWASLU_BUILD_VERSION',')[0-9.]+",
    "frontend/scripts/test-ai5-v1794.mjs": r"(ARG BAWASLU_BUILD_VERSION=|'BAWASLU_BUILD_VERSION',')[0-9.]+",
}
def git(*args):
    return subprocess.check_output(["git", *args], text=True)
def version_only(path, base):
    pattern = VERSION_FILES.get(path)
    if not pattern:
        return False
    old, new = git("show", f"{base}:{path}"), git("show", f"HEAD:{path}")
    return re.sub(pattern, r"\g<1>VERSION", old) == re.sub(pattern, r"\g<1>VERSION", new)

def verified_base(base):
    """An unfinished or failed previous release cannot be a targeted QA baseline."""
    repo = os.getenv("GH_REPO", "")
    token = os.getenv("GH_TOKEN", "")
    if not repo or not token or not re.fullmatch(r"[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+", repo):
        return False
    try:
        req = urllib.request.Request(
            f"https://api.github.com/repos/{repo}/actions/workflows/playwright.yml/runs?head_sha={base}&per_page=10",
            headers={"Authorization": f"Bearer {token}", "Accept": "application/vnd.github+json"})
        with urllib.request.urlopen(req, timeout=8) as response:
            runs = json.load(response).get("workflow_runs", [])
        matches = [run for run in runs if run.get("head_sha") == base
                   and run.get("head_branch") == "architecture-v2-foundation-20261015"]
        return bool(matches and matches[0].get("conclusion") == "success")
    except Exception:
        print("Previous QA status unavailable; running full regression.")
        return False

def choose(event, base):
    if event != "push" or not re.fullmatch(r"[0-9a-f]{40}", base or "") or base == "0"*40:
        return "full", []
    if not verified_base(base):
        return "full", []
    try:
        changes = git("diff", "--name-only", base, "HEAD").splitlines()
        relevant = [p for p in changes if not version_only(p, base)]
    except (OSError, subprocess.CalledProcessError):
        return "full", []
    groups = set()
    for path in relevant:
        matched = {name for name, data in GROUPS.items() if path in data["files"]}
        if not matched:
            return "full", []
        groups.update(matched)
    if not groups:
        return "full", []
    specs = sorted({spec for name in groups for spec in GROUPS[name]["specs"]} | {"targeted-smoke"})
    return "+".join(sorted(groups)), [f"e2e/{spec}.spec.js" for spec in specs]

def main():
    scope, specs = choose(os.getenv("EVENT"), os.getenv("BASE_SHA"))
    shards = ["1/3", "2/3", "3/3"] if scope == "full" else (["1/2", "2/2"] if len(specs) >= 7 else ["1/1"])
    result = {"scope": scope, "shards": json.dumps(shards), "specs": " ".join(specs)}
    with open(os.environ["GITHUB_OUTPUT"], "a", encoding="utf-8") as out:
        for key, value in result.items():
            print(f"{key}={value}", file=out)
    print("Playwright scope:", scope, "; selected:", ", ".join(specs) or "all specs")
if __name__ == "__main__":
    main()
