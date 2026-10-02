import json
import re
import pkgutil
import html
import importlib.util
import contextlib
import io
import unittest
from pathlib import Path

import nlptutti as nt


ROOT = Path(__file__).resolve().parents[1]


class TestDocumentationExamples(unittest.TestCase):
    def test_readme_and_corpus_snippets_share_manual_contract(self):
        readme = (ROOT / "README.md").read_text(encoding="utf-8")
        comparison = readme.split("### 3. 두 STT 시스템 비교", 1)[1].split("```python", 1)[1].split("```", 1)[0].strip()
        corpus_doc = (ROOT / "docs/corpus-and-validation.md").read_text(encoding="utf-8")
        corpus = corpus_doc.split("```python", 1)[1].split("```", 1)[0].strip()
        contract = json.loads((ROOT / "docs/manual-examples.json").read_text(encoding="utf-8"))
        for name, snippet in (("comparison", comparison), ("sentence-errors", corpus)):
            output = io.StringIO()
            with contextlib.redirect_stdout(output):
                exec(compile(snippet, "documentation:" + name, "exec"), {})
            self.assertEqual(output.getvalue(), contract[name])
        spec = importlib.util.spec_from_file_location("manual_checker", ROOT / ".github/scripts/verify_manual_examples.py")
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        parser = module.Examples()
        parser.feed('<pre data-nlptutti-example="comparison"><code>' + html.escape(comparison) + '</code></pre>')
        self.assertEqual(parser.examples["comparison"], comparison)

    def test_installed_sample_matches_documentation_fixture(self):
        installed = json.loads(pkgutil.get_data("nlptutti", "comparison_sample.json").decode("utf-8"))
        example = json.loads((ROOT / "examples/comparison_input.json").read_text(encoding="utf-8"))
        self.assertEqual(installed, example)

    def test_readme_comparison_fixture_has_documented_results(self):
        document = json.loads(
            (ROOT / "examples" / "comparison_input.json").read_text(encoding="utf-8")
        )
        report = nt.compare_systems(
            document["references"],
            document["systems"],
            rate_mode="standard",
        )
        baseline, candidate = report["systems"]

        self.assertEqual(round(baseline["metrics"]["cer"]["micro"], 4), 0.2353)
        self.assertEqual(baseline["metrics"]["wer"]["micro"], 0.4)
        self.assertEqual(baseline["metrics"]["crr"]["micro"], 0.76)
        self.assertEqual(candidate["metrics"]["cer"]["micro"], 0.0)
        self.assertEqual(candidate["metrics"]["wer"]["micro"], 0.0)
        self.assertEqual(candidate["metrics"]["crr"]["micro"], 1.0)

    def test_readme_exposes_the_verified_first_run_path(self):
        readme = (ROOT / "README.md").read_text(encoding="utf-8")

        required_fragments = [
            "python -m pip install -U nlptutti",
            "metrics.get_cer(",
            "metrics.compare_systems(",
            "examples/comparison_input.json",
            "--output-dir comparison-report",
            "# baseline 0.2353 0.4",
            "# candidate 0.0 0.0",
        ]
        for fragment in required_fragments:
            with self.subTest(fragment=fragment):
                self.assertIn(fragment, readme)

    def test_repository_readme_links_target_existing_files(self):
        readme = (ROOT / "README.md").read_text(encoding="utf-8")
        repository_links = re.findall(
            r"github\.com/hyeonsangjeon/computing-Korean-STT-error-rates/"
            r"blob/main/([^#)]+)",
            readme,
        )

        self.assertTrue(repository_links)
        for repository_link in repository_links:
            with self.subTest(repository_link=repository_link):
                self.assertTrue((ROOT / repository_link).is_file())


if __name__ == "__main__":
    unittest.main()
