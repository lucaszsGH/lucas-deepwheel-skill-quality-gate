#!/usr/bin/env python3
from __future__ import annotations

import json
from pathlib import Path
import shutil
import subprocess
import tempfile
import unittest


ROOT = Path(__file__).resolve().parents[1]
SKILL_NAME = "lucas-deepwheel-skill-quality-gate"
SKILL = ROOT / "skills" / SKILL_NAME
SCANNER = SKILL / "scripts" / "skill_quality_gate.py"


def run_gate(*args: str, executable: bool = False) -> subprocess.CompletedProcess[str]:
    command = [str(SCANNER)] if executable else ["python3", str(SCANNER)]
    command.extend(args)
    return subprocess.run(
        command,
        cwd=ROOT,
        text=True,
        capture_output=True,
        check=False,
    )


class QualityGateBehaviorTests(unittest.TestCase):
    def test_clean_skill_returns_zero(self) -> None:
        result = run_gate(str(SKILL))
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertIn("Skill Quality Gate: CLEAN", result.stdout)

    def test_direct_executable_entrypoint_works(self) -> None:
        result = run_gate(str(SKILL), executable=True)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertIn("Skill Quality Gate: CLEAN", result.stdout)

    def test_missing_skill_returns_block_and_two_without_absolute_path(self) -> None:
        missing = ROOT / "does-not-exist"
        result = run_gate(str(missing))
        self.assertEqual(result.returncode, 2)
        self.assertIn("Skill Quality Gate: BLOCK", result.stdout)
        self.assertNotIn(str(ROOT), result.stdout)

    def test_warning_returns_concerns_and_one(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            target = Path(temp) / SKILL_NAME
            shutil.copytree(SKILL, target)
            (target / "agents" / "openai.yaml").unlink()
            result = run_gate(str(target))
        self.assertEqual(result.returncode, 1, result.stdout + result.stderr)
        self.assertIn("Skill Quality Gate: CONCERNS", result.stdout)

    def test_same_named_scanner_file_is_not_skipped(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            target = Path(temp) / SKILL_NAME
            shutil.copytree(SKILL, target)
            shaped_value = "s" + "k-" + ("A" * 24)
            suspect = target / "scripts" / "skill_quality_gate.py"
            suspect.write_text("value = " + shaped_value + "\n", encoding="utf-8")
            result = run_gate(str(target))
        self.assertEqual(result.returncode, 2)
        self.assertIn("provider credential shaped value found", result.stdout)
        self.assertNotIn(shaped_value, result.stdout)

    def test_generic_home_path_is_reported_without_echoing_value(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            target = Path(temp) / SKILL_NAME
            shutil.copytree(SKILL, target)
            local_value = "/" + "Users/" + "example/work"
            (target / "local-note.md").write_text(local_value + "\n", encoding="utf-8")
            result = run_gate(str(target))
        self.assertEqual(result.returncode, 1)
        self.assertIn("macOS home path found", result.stdout)
        self.assertNotIn(local_value, result.stdout)

    def test_explicit_missing_publication_returns_block(self) -> None:
        missing = ROOT / "missing-publication"
        result = run_gate(str(SKILL), "--publication-dir", str(missing))
        self.assertEqual(result.returncode, 2)
        self.assertIn("publication directory is missing", result.stdout)
        self.assertNotIn(str(ROOT), result.stdout)

    def test_json_output_keeps_exit_semantics_and_safe_details(self) -> None:
        missing = ROOT / "missing-json-target"
        result = run_gate(str(missing), "--json")
        self.assertEqual(result.returncode, 2)
        payload = json.loads(result.stdout)
        self.assertEqual(payload["summary"]["verdict"], "BLOCK")
        self.assertNotIn(str(ROOT), result.stdout)

    def test_publication_audit_does_not_require_quality_gate_files(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            publication = Path(temp) / "generic-publication"
            shutil.copytree(ROOT, publication)
            optional_product_files = (
                ".github/RELEASE_TEMPLATE.md",
                "docs/CLI.md",
                "scripts/validate-lucas-deepwheel-quality-gate.py",
                "tests/test_skill_quality_gate.py",
            )
            for relative in optional_product_files:
                path = publication / relative
                if path.exists():
                    path.unlink()
            target_skill = publication / "skills" / SKILL_NAME
            result = run_gate(
                str(target_skill),
                "--publication-dir",
                str(publication),
            )
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertIn("Skill Quality Gate: CLEAN", result.stdout)

    def test_complete_publication_package_is_clean(self) -> None:
        result = run_gate(str(SKILL), "--publication-dir", str(ROOT))
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertIn("Skill Quality Gate: CLEAN", result.stdout)


if __name__ == "__main__":
    unittest.main()
