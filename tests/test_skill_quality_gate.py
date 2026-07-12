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
BEHAVIOR_CASE_IDS = (
    "consent_missing",
    "data_subject_unconfirmed",
    "minimum_input_missing",
    "safety_preflight_incomplete",
    "stop_condition",
    "blocked_output_suppression",
    "source_provenance_invalid",
)


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

    def test_high_risk_skill_without_profile_is_blocked(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            target = Path(temp) / SKILL_NAME
            shutil.copytree(SKILL, target)
            (target / "agents" / "risk-profile.json").unlink()
            skill_md = target / "SKILL.md"
            text = skill_md.read_text(encoding="utf-8")
            text = text.replace(
                "Use when evaluating",
                "Use when evaluating a health nutrition genetic Skill",
                1,
            )
            skill_md.write_text(text, encoding="utf-8")
            result = run_gate(str(target))
        self.assertEqual(result.returncode, 2, result.stdout + result.stderr)
        self.assertIn("machine-readable risk profile is missing", result.stdout)

    def test_high_risk_skill_with_controls_can_be_clean(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            target = Path(temp) / SKILL_NAME
            shutil.copytree(SKILL, target)
            skill_md = target / "SKILL.md"
            text = skill_md.read_text(encoding="utf-8")
            text = text.replace(
                "Use when evaluating",
                "Use when evaluating a health nutrition genetic Skill",
                1,
            )
            text += "\n## 安全边界\n同意、来源、停止与专业复核必须明确。\n"
            skill_md.write_text(text, encoding="utf-8")
            profile = {
                "schema_version": 1,
                "risk_level": "high",
                "domains": ["health", "genetics", "nutrition"],
                "sensitive_data": ["genetic_data", "health_data"],
                "consent_required": True,
                "human_review_required": True,
                "source_provenance_required": True,
                "refusal_rules_required": True,
                "personalized_numeric_guidance_enabled": True,
                "numeric_safety_contract_required": True,
                "numeric_contract_path": "scripts/case_contract.py",
                "behavioral_safety_contract_required": True,
                "behavioral_safety_contract_path": "scripts/case_contract.py",
                "behavioral_test_path": "tests/test_skill_quality_gate.py",
                "behavioral_case_ids": list(BEHAVIOR_CASE_IDS),
            }
            (target / "agents" / "risk-profile.json").write_text(
                json.dumps(profile), encoding="utf-8"
            )
            contract = target / "scripts" / "case_contract.py"
            contract.write_text("print('synthetic contract')\n", encoding="utf-8")
            contract.chmod(contract.stat().st_mode | 0o100)
            result = run_gate(str(target))
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertIn("Skill Quality Gate: CLEAN", result.stdout)

    def test_high_risk_missing_entrypoint_boundary_is_blocked(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            target = Path(temp) / SKILL_NAME
            shutil.copytree(SKILL, target)
            skill_md = target / "SKILL.md"
            text = skill_md.read_text(encoding="utf-8")
            text = text.replace("安全边界", "边界章节")
            text = text.replace(
                "Use when evaluating",
                "Use when evaluating a genetic nutrition Skill",
                1,
            )
            text += "\n同意、来源、停止与专业复核必须明确。\n"
            skill_md.write_text(text, encoding="utf-8")
            profile = {
                "schema_version": 1,
                "risk_level": "high",
                "domains": ["health", "genetics", "nutrition"],
                "sensitive_data": ["genetic_data", "health_data"],
                "consent_required": True,
                "human_review_required": True,
                "source_provenance_required": True,
                "refusal_rules_required": True,
            }
            (target / "agents" / "risk-profile.json").write_text(
                json.dumps(profile), encoding="utf-8"
            )
            result = run_gate(str(target))
        self.assertEqual(result.returncode, 2, result.stdout + result.stderr)
        self.assertIn("high-risk boundary control is missing", result.stdout)

    def test_numeric_high_risk_skill_without_contract_is_blocked(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            target = Path(temp) / SKILL_NAME
            shutil.copytree(SKILL, target)
            skill_md = target / "SKILL.md"
            text = skill_md.read_text(encoding="utf-8")
            text = text.replace(
                "Use when evaluating",
                "Use when evaluating a genetic nutrition supplement dose Skill",
                1,
            )
            text += "\n## 安全边界\n同意、来源、停止与专业复核必须明确。\n"
            skill_md.write_text(text, encoding="utf-8")
            profile = {
                "schema_version": 1,
                "risk_level": "high",
                "domains": ["health", "nutrition"],
                "sensitive_data": ["health_data"],
                "consent_required": True,
                "human_review_required": True,
                "source_provenance_required": True,
                "refusal_rules_required": True,
            }
            (target / "agents" / "risk-profile.json").write_text(
                json.dumps(profile), encoding="utf-8"
            )
            result = run_gate(str(target))
        self.assertEqual(result.returncode, 2, result.stdout + result.stderr)
        self.assertIn("numeric high-risk guidance lacks a machine safety contract", result.stdout)

    def test_nonexecutable_numeric_contract_is_blocked(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            target = Path(temp) / SKILL_NAME
            shutil.copytree(SKILL, target)
            skill_md = target / "SKILL.md"
            text = skill_md.read_text(encoding="utf-8")
            text = text.replace(
                "Use when evaluating",
                "Use when evaluating a genetic nutrition supplement dose Skill",
                1,
            )
            text += "\n## 安全边界\n同意、来源、停止与专业复核必须明确。\n"
            skill_md.write_text(text, encoding="utf-8")
            profile = {
                "schema_version": 1,
                "risk_level": "high",
                "domains": ["health", "nutrition"],
                "sensitive_data": ["health_data"],
                "consent_required": True,
                "human_review_required": True,
                "source_provenance_required": True,
                "refusal_rules_required": True,
                "personalized_numeric_guidance_enabled": True,
                "numeric_safety_contract_required": True,
                "numeric_contract_path": "scripts/case_contract.py",
                "behavioral_safety_contract_required": True,
                "behavioral_safety_contract_path": "scripts/case_contract.py",
                "behavioral_test_path": "tests/test_skill_quality_gate.py",
                "behavioral_case_ids": list(BEHAVIOR_CASE_IDS),
            }
            (target / "agents" / "risk-profile.json").write_text(
                json.dumps(profile), encoding="utf-8"
            )
            contract = target / "scripts" / "case_contract.py"
            contract.write_text("print('synthetic contract')\n", encoding="utf-8")
            contract.chmod(0o644)
            result = run_gate(str(target))
        self.assertEqual(result.returncode, 2, result.stdout + result.stderr)
        self.assertIn("numeric safety contract is not executable", result.stdout)

    def test_high_risk_skill_without_behavior_contract_is_blocked(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            target = Path(temp) / SKILL_NAME
            shutil.copytree(SKILL, target)
            skill_md = target / "SKILL.md"
            text = skill_md.read_text(encoding="utf-8")
            text = text.replace(
                "Use when evaluating",
                "Use when evaluating a genetic nutrition Skill",
                1,
            )
            text += "\n## 安全边界\n同意、来源、停止与专业复核必须明确。\n"
            skill_md.write_text(text, encoding="utf-8")
            profile = {
                "schema_version": 1,
                "risk_level": "high",
                "domains": ["health", "nutrition"],
                "sensitive_data": ["health_data"],
                "consent_required": True,
                "human_review_required": True,
                "source_provenance_required": True,
                "refusal_rules_required": True,
                "personalized_numeric_guidance_enabled": False,
                "unreviewed_output_policy": "education_only",
                "numeric_safety_contract_required": True,
                "numeric_contract_path": "scripts/case_contract.py",
            }
            (target / "agents" / "risk-profile.json").write_text(
                json.dumps(profile), encoding="utf-8"
            )
            contract = target / "scripts" / "case_contract.py"
            contract.write_text("print('synthetic contract')\n", encoding="utf-8")
            contract.chmod(contract.stat().st_mode | 0o100)
            result = run_gate(str(target))
        self.assertEqual(result.returncode, 2, result.stdout + result.stderr)
        self.assertIn("high-risk behavioral safety contract is not required", result.stdout)

    def test_high_risk_skill_with_incomplete_behavior_cases_is_blocked(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            target = Path(temp) / SKILL_NAME
            shutil.copytree(SKILL, target)
            skill_md = target / "SKILL.md"
            text = skill_md.read_text(encoding="utf-8")
            text = text.replace(
                "Use when evaluating",
                "Use when evaluating a genetic nutrition Skill",
                1,
            )
            text += "\n## 安全边界\n同意、来源、停止与专业复核必须明确。\n"
            skill_md.write_text(text, encoding="utf-8")
            profile = {
                "schema_version": 1,
                "risk_level": "high",
                "domains": ["health", "nutrition"],
                "sensitive_data": ["health_data"],
                "consent_required": True,
                "human_review_required": True,
                "source_provenance_required": True,
                "refusal_rules_required": True,
                "personalized_numeric_guidance_enabled": False,
                "unreviewed_output_policy": "education_only",
                "numeric_safety_contract_required": True,
                "numeric_contract_path": "scripts/case_contract.py",
                "behavioral_safety_contract_required": True,
                "behavioral_safety_contract_path": "scripts/case_contract.py",
                "behavioral_test_path": "tests/test_behavior.py",
                "behavioral_case_ids": ["consent_missing"],
            }
            (target / "agents" / "risk-profile.json").write_text(
                json.dumps(profile), encoding="utf-8"
            )
            contract = target / "scripts" / "case_contract.py"
            contract.write_text("print('synthetic contract')\n", encoding="utf-8")
            contract.chmod(contract.stat().st_mode | 0o100)
            result = run_gate(str(target))
        self.assertEqual(result.returncode, 2, result.stdout + result.stderr)
        self.assertIn("high-risk behavior regression coverage is incomplete", result.stdout)

    def test_high_risk_publication_requires_behavior_test_file(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            publication = Path(temp) / "publication"
            shutil.copytree(ROOT, publication)
            target = publication / "skills" / SKILL_NAME
            skill_md = target / "SKILL.md"
            text = skill_md.read_text(encoding="utf-8")
            text = text.replace(
                "Use when evaluating",
                "Use when evaluating a genetic nutrition Skill",
                1,
            )
            text += "\n## 安全边界\n同意、来源、停止与专业复核必须明确。\n"
            skill_md.write_text(text, encoding="utf-8")
            profile = {
                "schema_version": 1,
                "risk_level": "high",
                "domains": ["health", "nutrition"],
                "sensitive_data": ["health_data"],
                "consent_required": True,
                "human_review_required": True,
                "source_provenance_required": True,
                "refusal_rules_required": True,
                "personalized_numeric_guidance_enabled": False,
                "unreviewed_output_policy": "education_only",
                "numeric_safety_contract_required": True,
                "numeric_contract_path": "scripts/case_contract.py",
                "behavioral_safety_contract_required": True,
                "behavioral_safety_contract_path": "scripts/case_contract.py",
                "behavioral_test_path": "tests/missing_high_risk_behavior.py",
                "behavioral_case_ids": list(BEHAVIOR_CASE_IDS),
            }
            (target / "agents" / "risk-profile.json").write_text(
                json.dumps(profile), encoding="utf-8"
            )
            contract = target / "scripts" / "case_contract.py"
            contract.write_text("print('synthetic contract')\n", encoding="utf-8")
            contract.chmod(contract.stat().st_mode | 0o100)
            result = run_gate(str(target), "--publication-dir", str(publication))
        self.assertEqual(result.returncode, 2, result.stdout + result.stderr)
        self.assertIn("high-risk behavior regression test file is missing", result.stdout)

    def test_high_risk_publication_test_must_contain_declared_cases(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            publication = Path(temp) / "publication"
            shutil.copytree(ROOT, publication)
            target = publication / "skills" / SKILL_NAME
            skill_md = target / "SKILL.md"
            text = skill_md.read_text(encoding="utf-8")
            text = text.replace(
                "Use when evaluating",
                "Use when evaluating a genetic nutrition Skill",
                1,
            )
            text += "\n## 安全边界\n同意、来源、停止与专业复核必须明确。\n"
            skill_md.write_text(text, encoding="utf-8")
            profile = {
                "schema_version": 1,
                "risk_level": "high",
                "domains": ["health", "nutrition"],
                "sensitive_data": ["health_data"],
                "consent_required": True,
                "human_review_required": True,
                "source_provenance_required": True,
                "refusal_rules_required": True,
                "personalized_numeric_guidance_enabled": False,
                "unreviewed_output_policy": "education_only",
                "numeric_safety_contract_required": True,
                "numeric_contract_path": "scripts/case_contract.py",
                "behavioral_safety_contract_required": True,
                "behavioral_safety_contract_path": "scripts/case_contract.py",
                "behavioral_test_path": "tests/high_risk_behavior.py",
                "behavioral_case_ids": list(BEHAVIOR_CASE_IDS),
            }
            (target / "agents" / "risk-profile.json").write_text(
                json.dumps(profile), encoding="utf-8"
            )
            contract = target / "scripts" / "case_contract.py"
            contract.write_text("print('synthetic contract')\n", encoding="utf-8")
            contract.chmod(contract.stat().st_mode | 0o100)
            (publication / "tests" / "high_risk_behavior.py").write_text(
                "# consent_missing only\n", encoding="utf-8"
            )
            result = run_gate(str(target), "--publication-dir", str(publication))
        self.assertEqual(result.returncode, 2, result.stdout + result.stderr)
        self.assertIn("high-risk behavior regression tests lack declared cases", result.stdout)

    def test_high_risk_signal_in_reference_is_detected(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            target = Path(temp) / SKILL_NAME
            shutil.copytree(SKILL, target)
            (target / "agents" / "risk-profile.json").unlink()
            (target / "references" / "domain.md").write_text(
                "Recommend a supplement dose.", encoding="utf-8"
            )
            result = run_gate(str(target))
        self.assertEqual(result.returncode, 2, result.stdout + result.stderr)
        self.assertIn("machine-readable risk profile is missing", result.stdout)

    def test_english_substrings_do_not_trigger_high_risk(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            target = Path(temp) / SKILL_NAME
            shutil.copytree(SKILL, target)
            (target / "agents" / "risk-profile.json").unlink()
            policy = target / "references" / "high-risk-domain-policy.md"
            if policy.exists():
                policy.unlink()
            skill_md = target / "SKILL.md"
            text = skill_md.read_text(encoding="utf-8")
            text += "\nSyntax, illegal characters, and system health check.\n"
            skill_md.write_text(text, encoding="utf-8")
            result = run_gate(str(target))
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertIn("Skill Quality Gate: CLEAN", result.stdout)

    def test_missing_bilingual_intro_asset_returns_concerns(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            publication = Path(temp) / "publication"
            shutil.copytree(ROOT, publication)
            target_skill = publication / "skills" / SKILL_NAME
            (publication / "assets" / "intro" / "quality-gate-hero-zh-CN.png").unlink()
            result = run_gate(
                str(target_skill),
                "--publication-dir",
                str(publication),
            )
        self.assertEqual(result.returncode, 1, result.stdout + result.stderr)
        self.assertIn("bilingual GitHub introduction asset is missing", result.stdout)

    def test_incomplete_publication_checklist_returns_concerns(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            publication = Path(temp) / "publication"
            shutil.copytree(ROOT, publication)
            checklist = publication / "docs" / "PUBLICATION-CHECKLIST.md"
            text = checklist.read_text(encoding="utf-8")
            text = text.replace("- [x]", "- [ ]", 1)
            checklist.write_text(text, encoding="utf-8")
            target_skill = publication / "skills" / SKILL_NAME
            result = run_gate(
                str(target_skill),
                "--publication-dir",
                str(publication),
            )
        self.assertEqual(result.returncode, 1, result.stdout + result.stderr)
        self.assertIn("publication checklist has incomplete items", result.stdout)

    def test_high_risk_publication_requires_approved_professional_signoff(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            publication = Path(temp) / "publication"
            shutil.copytree(ROOT, publication)
            target = publication / "skills" / SKILL_NAME
            skill_md = target / "SKILL.md"
            text = skill_md.read_text(encoding="utf-8")
            text = text.replace(
                "Use when evaluating",
                "Use when evaluating a health nutrition genetic Skill",
                1,
            )
            text += "\n## 安全边界\n同意、来源、停止与专业复核必须明确。\n"
            skill_md.write_text(text, encoding="utf-8")
            profile = {
                "schema_version": 1,
                "risk_level": "high",
                "domains": ["health", "genetics", "nutrition"],
                "sensitive_data": ["genetic_data", "health_data"],
                "consent_required": True,
                "human_review_required": True,
                "source_provenance_required": True,
                "refusal_rules_required": True,
                "personalized_numeric_guidance_enabled": True,
                "numeric_safety_contract_required": True,
                "numeric_contract_path": "scripts/case_contract.py",
                "behavioral_safety_contract_required": True,
                "behavioral_safety_contract_path": "scripts/case_contract.py",
                "behavioral_test_path": "tests/test_skill_quality_gate.py",
                "behavioral_case_ids": list(BEHAVIOR_CASE_IDS),
            }
            (target / "agents" / "risk-profile.json").write_text(
                json.dumps(profile), encoding="utf-8"
            )
            contract = target / "scripts" / "case_contract.py"
            contract.write_text("print('synthetic contract')\n", encoding="utf-8")
            contract.chmod(contract.stat().st_mode | 0o100)
            signoff = publication / "docs" / "PROFESSIONAL-SIGNOFF.md"
            signoff.write_text("# Sign-off\n\nStatus: PENDING\n", encoding="utf-8")
            pending = run_gate(
                str(target),
                "--publication-dir",
                str(publication),
            )
            digest_result = run_gate(str(target), "--print-skill-sha256")
            self.assertEqual(digest_result.returncode, 0, digest_result.stderr)
            digest = digest_result.stdout.strip()
            self.assertRegex(digest, r"^[0-9a-f]{64}$")
            signoff.write_text(
                "# Sign-off\n\nStatus: APPROVED\n\nTarget Skill SHA256: " + ("0" * 64) + "\n",
                encoding="utf-8",
            )
            mismatched = run_gate(
                str(target),
                "--publication-dir",
                str(publication),
            )
            signoff.write_text(
                "# Sign-off\n\nStatus: APPROVED\n\nTarget Skill SHA256: " + digest + "\n",
                encoding="utf-8",
            )
            approved = run_gate(
                str(target),
                "--publication-dir",
                str(publication),
            )
            profile["personalized_numeric_guidance_enabled"] = False
            profile["unreviewed_output_policy"] = "education_only_with_safety_routes"
            (target / "agents" / "risk-profile.json").write_text(
                json.dumps(profile), encoding="utf-8"
            )
            signoff.write_text("# Sign-off\n\nStatus: PENDING\n", encoding="utf-8")
            education_only_pending = run_gate(
                str(target),
                "--publication-dir",
                str(publication),
            )
        self.assertEqual(pending.returncode, 2, pending.stdout + pending.stderr)
        self.assertIn("high-risk professional sign-off is incomplete", pending.stdout)
        self.assertEqual(mismatched.returncode, 2, mismatched.stdout + mismatched.stderr)
        self.assertIn("professional sign-off target does not match current Skill", mismatched.stdout)
        self.assertEqual(approved.returncode, 0, approved.stdout + approved.stderr)
        self.assertIn("Skill Quality Gate: CLEAN", approved.stdout)
        self.assertEqual(education_only_pending.returncode, 1, education_only_pending.stdout + education_only_pending.stderr)
        self.assertIn("high-risk professional sign-off is incomplete", education_only_pending.stdout)

    def test_complete_publication_package_is_clean(self) -> None:
        result = run_gate(str(SKILL), "--publication-dir", str(ROOT))
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertIn("Skill Quality Gate: CLEAN", result.stdout)


if __name__ == "__main__":
    unittest.main()
