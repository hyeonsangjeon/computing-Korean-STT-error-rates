import re
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def _project_version():
    pyproject = (ROOT / "pyproject.toml").read_text(encoding="utf-8")
    match = re.search(r'^version = "([^"]+)"$', pyproject, re.MULTILINE)
    if match is None:
        raise AssertionError("pyproject.toml project version not found")
    return match.group(1)


class TestCommunityMetadata(unittest.TestCase):
    def test_citation_matches_package_metadata(self):
        citation = (ROOT / "CITATION.cff").read_text(encoding="utf-8")
        pyproject = (ROOT / "pyproject.toml").read_text(encoding="utf-8")

        self.assertIn("cff-version: 1.2.0", citation)
        self.assertIn("version: {}".format(_project_version()), citation)
        self.assertIn("license: MIT", citation)
        self.assertIn('name = "hyeonsangjeon"', pyproject)
        self.assertIn("alias: hyeonsangjeon", citation)

    def test_required_community_files_and_templates_exist(self):
        required = [
            "CONTRIBUTING.md",
            "CITATION.cff",
            "SECURITY.md",
            ".github/ISSUE_TEMPLATE/provider_adapter.yml",
            ".github/ISSUE_TEMPLATE/metric_correctness.yml",
            ".github/ISSUE_TEMPLATE/documentation.yml",
            ".github/ISSUE_TEMPLATE/config.yml",
        ]
        for relative_path in required:
            with self.subTest(relative_path=relative_path):
                self.assertTrue((ROOT / relative_path).is_file())

    def test_privacy_and_license_boundaries_are_documented(self):
        contributing = (ROOT / "CONTRIBUTING.md").read_text(encoding="utf-8")
        security = (ROOT / "SECURITY.md").read_text(encoding="utf-8")

        self.assertIn("실제 사용자, 고객, 회사 내부 transcript", contributing)
        self.assertIn("데이터·모델·가중치", contributing)
        self.assertIn("private vulnerability report", security)
        self.assertIn("실제 고객 transcript", security)


if __name__ == "__main__":
    unittest.main()
