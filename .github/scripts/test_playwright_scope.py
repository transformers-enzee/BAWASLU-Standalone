"""Offline checks for conservative browser scope selection."""
import unittest
from unittest.mock import patch
import subprocess
import playwright_scope as scope

class ScopeTests(unittest.TestCase):
    base = "1"*40
    def test_social_only(self):
        with patch.object(scope, "git", return_value="backend/app/prism_discover.py\n"):
            self.assertEqual(scope.choose("push", self.base), "social")
    def test_shared_or_unknown(self):
        with patch.object(scope, "git", return_value="backend/app/access.py\n"):
            self.assertEqual(scope.choose("push", self.base), "full")
    def test_manual_pr_and_missing_base_are_full(self):
        for event, base in [("workflow_dispatch", self.base), ("pull_request", self.base), ("push", ""), ("push", "0"*40)]:
            self.assertEqual(scope.choose(event, base), "full")
    def test_diff_failure_is_full(self):
        with patch.object(scope, "git", side_effect=subprocess.CalledProcessError(1, ["git"])):
            self.assertEqual(scope.choose("push", self.base), "full")
    def test_version_only_ignored_but_shared_changes_not_ignored(self):
        for old, new, expected in [("ARG BAWASLU_BUILD_VERSION=182.8\n", "ARG BAWASLU_BUILD_VERSION=182.9\n", "social"), ("ARG BAWASLU_BUILD_VERSION=182.8\n", "ARG BAWASLU_BUILD_VERSION=182.9\nRUN new-command\n", "full")]:
            with patch.object(scope, "git", side_effect=["Dockerfile\nbackend/app/prism_discover.py\n", old, new]):
                self.assertEqual(scope.choose("push", self.base), expected)
if __name__ == "__main__":
    unittest.main()
