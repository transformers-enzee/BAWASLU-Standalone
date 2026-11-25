"""Conservative QA routing; unknown, shared and workflow changes run full regression."""
import json
import os
import re
import subprocess

SOCIAL_SPECS = "e2e/social-listening-rules.spec.js e2e/campaign-description-legacy.spec.js e2e/assessment-operations-interaction.spec.js e2e/command-center.spec.js e2e/system-regression.spec.js e2e/release-readiness.spec.js"
SOCIAL_FILES = {
    "backend/app/prism_discover.py", "backend/app/prism_full_export.py",
    "backend/app/prism_collection_budget.py", "backend/app/project_boolean.py",
    "backend/app/activation_assessment.py",
    "backend/tests/test_prism_discover_idempotency.py",
    "backend/tests/test_prism_boolean_cost_guard_v17582.py",
    "frontend/src/components/intel/CampaignPanel.jsx",
    "frontend/src/components/intel/AssessmentProgressDialog.jsx",
    "frontend/e2e/social-listening-rules.spec.js",
    "frontend/scripts/test-prism-boolean-guard-v17582.mjs",
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
def choose(event, base):
    if event != "push" or not re.fullmatch(r"[0-9a-f]{40}", base or "") or base == "0"*40:
        return "full"
    try:
        changes = git("diff", "--name-only", base, "HEAD").splitlines()
        relevant = [p for p in changes if not version_only(p, base)]
    except (OSError, subprocess.CalledProcessError):
        return "full"
    return "social" if relevant and set(relevant) <= SOCIAL_FILES else "full"
def main():
    scope = choose(os.getenv("EVENT"), os.getenv("BASE_SHA"))
    result = {"scope": scope, "shards": json.dumps(["1/1"] if scope == "social" else ["1/2", "2/2"]), "specs": SOCIAL_SPECS if scope == "social" else ""}
    with open(os.environ["GITHUB_OUTPUT"], "a", encoding="utf-8") as out:
        for key, value in result.items():
            print(f"{key}={value}", file=out)
    print("Playwright scope:", scope)
if __name__ == "__main__":
    main()
