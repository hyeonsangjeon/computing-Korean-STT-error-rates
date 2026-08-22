import re
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


class TestReleaseMetadata(unittest.TestCase):
    def test_version_changelog_citation_and_classifier_agree(self):
        pyproject = (ROOT / "pyproject.toml").read_text(encoding="utf-8")
        changelog = (ROOT / "CHANGELOG.md").read_text(encoding="utf-8")
        citation = (ROOT / "CITATION.cff").read_text(encoding="utf-8")

        version_match = re.search(r'^version = "([^"]+)"$', pyproject, re.MULTILINE)
        self.assertIsNotNone(version_match)
        version = version_match.group(1)
        self.assertEqual(version, "0.0.0.20")
        self.assertIn("## [{}] - 2026-08-22".format(version), changelog)
        self.assertIn("version: {}".format(version), citation)
        self.assertIn("date-released: 2026-08-22", citation)
        self.assertIn("Development Status :: 4 - Beta", pyproject)

    def test_zero_one_release_is_explicitly_deferred(self):
        policy = (ROOT / "docs" / "release-policy.md").read_text(encoding="utf-8")

        self.assertIn("0.0.0.20", policy)
        self.assertIn("0.0.0.21", policy)
        self.assertIn("0.1.0", policy)
        self.assertIn("두 patch release", policy)
        self.assertIn("experimental", policy)

    def test_source_distribution_manifest_keeps_public_validation_materials(self):
        manifest = (ROOT / "MANIFEST.in").read_text(encoding="utf-8")

        for path in ("CHANGELOG.md", "CITATION.cff", "CONTRIBUTING.md", "SECURITY.md"):
            with self.subTest(path=path):
                self.assertIn(path, manifest)
        self.assertIn("recursive-include benchmarks *.py", manifest)
        self.assertIn("recursive-include docs *.json *.md", manifest)

    def test_trusted_publisher_identity_flow_is_preserved(self):
        workflow = (ROOT / ".github" / "workflows" / "publish-to-pypi.yml").read_text(
            encoding="utf-8"
        )

        self.assertIn("id-token: write", workflow)
        self.assertIn("pypa/gh-action-pypi-publish", workflow)
        self.assertIn("environment:\n      name: pypi", workflow)
        self.assertNotIn("PYPI_API_TOKEN", workflow)


if __name__ == "__main__":
    unittest.main()
