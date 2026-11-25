"""Offline checks for dependency-aware browser scope selection."""
import unittest
from unittest.mock import patch
import subprocess
import playwright_scope as scope

class ScopeTests(unittest.TestCase):
    base = "1"*40
    def choose(self, changes):
        with patch.object(scope, "verified_base", return_value=True), patch.object(scope, "git", return_value=changes):
            return scope.choose("push", self.base)
    def test_social_only(self):
        name, specs = self.choose("backend/app/prism_discover.py\n")
        self.assertEqual(name, "social")
        self.assertIn("e2e/social-listening-rules.spec.js", specs)
        self.assertIn("e2e/targeted-smoke.spec.js", specs)
        self.assertNotIn("e2e/ai5.spec.js", specs)
    def test_assessment_cross_module(self):
        name, specs = self.choose("backend/app/auto_relevance.py\n")
        self.assertEqual(name, "assessment")
        for spec in ("potential-violation-qa", "ai5", "social-listening-rules"):
            self.assertIn(f"e2e/{spec}.spec.js", specs)
    def test_mixed_groups_deduplicated(self):
        name, specs = self.choose("frontend/src/pages/AI5Assistant.jsx\nfrontend/src/pages/CommandCenter.jsx\n")
        self.assertEqual(name, "assistant+command")
        self.assertEqual(len(specs), len(set(specs)))
        self.assertIn("e2e/command-center.spec.js", specs)
        self.assertIn("e2e/ai5.spec.js", specs)
    def test_unknown_and_shared_are_full(self):
        self.assertEqual(self.choose("frontend/src/pages/Inbox.jsx\nbackend/app/access.py\n"), ("full", []))
    def test_unverified_previous_commit_is_full(self):
        with patch.object(scope, "verified_base", return_value=False):
            self.assertEqual(scope.choose("push", self.base), ("full", []))
    def test_manual_pr_and_missing_base_are_full(self):
        for event, base in [("workflow_dispatch", self.base), ("pull_request", self.base), ("push", ""), ("push", "0"*40)]:
            self.assertEqual(scope.choose(event, base), ("full", []))
    def test_diff_failure_is_full(self):
        with patch.object(scope, "verified_base", return_value=True), patch.object(scope, "git", side_effect=subprocess.CalledProcessError(1, ["git"])):
            self.assertEqual(scope.choose("push", self.base), ("full", []))
    def test_version_only_ignored_but_shared_changes_not_ignored(self):
        for old, new, expected in [("ARG BAWASLU_BUILD_VERSION=183.0\n", "ARG BAWASLU_BUILD_VERSION=183.1\n", "social"), ("ARG BAWASLU_BUILD_VERSION=183.0\n", "ARG BAWASLU_BUILD_VERSION=183.1\nRUN new-command\n", "full")]:
            with patch.object(scope, "verified_base", return_value=True), patch.object(scope, "git", side_effect=["Dockerfile\nbackend/app/prism_discover.py\n", old, new]):
                self.assertEqual(scope.choose("push", self.base)[0], expected)
if __name__ == "__main__":
    unittest.main()
