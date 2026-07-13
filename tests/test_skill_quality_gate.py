#!/usr/bin/env python3
from __future__ import annotations

from hashlib import sha256
import importlib.util
import json
import os
from pathlib import Path
import shutil
import subprocess
import tempfile
import unittest


ROOT = Path(__file__).resolve().parents[1]
SKILL_NAME = "lucas-deepwheel-skill-quality-gate"
SKILL = ROOT / "skills" / SKILL_NAME
SCANNER = SKILL / "scripts" / "skill_quality_gate.py"
RECONCILER = SKILL / "scripts" / "reconcile_release_state.py"
BEHAVIOR_CASE_IDS = (
    "consent_missing",
    "data_subject_unconfirmed",
    "minimum_input_missing",
    "safety_preflight_incomplete",
    "stop_condition",
    "blocked_output_suppression",
    "source_provenance_invalid",
)

scanner_spec = importlib.util.spec_from_file_location("quality_gate_scanner", SCANNER)
quality_gate_scanner = importlib.util.module_from_spec(scanner_spec)
assert scanner_spec.loader is not None
scanner_spec.loader.exec_module(quality_gate_scanner)


def run_gate(
    *args: str,
    executable: bool = False,
    env: dict[str, str | None] | None = None,
) -> subprocess.CompletedProcess[str]:
    command = [str(SCANNER)] if executable else ["python3", str(SCANNER)]
    command.extend(args)
    # env=None → inherit os.environ (unchanged behavior). When provided, apply the
    # given overrides on top of os.environ; a value of None removes that key so a
    # test can assert the "variable not set" branch deterministically.
    run_env: dict[str, str] | None = None
    if env is not None:
        run_env = {**os.environ}
        for key, value in env.items():
            if value is None:
                run_env.pop(key, None)
            else:
                run_env[key] = value
    return subprocess.run(
        command,
        cwd=ROOT,
        text=True,
        capture_output=True,
        check=False,
        env=run_env,
    )


def refresh_public_surface_manifest(publication: Path, target_skill: Path) -> None:
    path = publication / "docs" / "PUBLIC-SURFACE-REVIEW.json"
    data = json.loads(path.read_text(encoding="utf-8"))
    data["skill_name"] = target_skill.name
    data["capability_change"] = "internal_only"
    data["decision"] = "NO_CHANGE_REQUIRED"
    data["reason"] = "Synthetic fixture changes only; public positioning and workflow remain unchanged."
    data["reviewed_skill_sha256"] = quality_gate_scanner.tree_sha256(target_skill)
    data["updated_assets"] = []
    data["public_surface_sha256"] = quality_gate_scanner.listed_files_sha256(
        publication, data["public_files"]
    )
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def git_run(repo: Path, *args: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        ["git", *args], cwd=repo, text=True, capture_output=True, check=True
    )


def make_release_state_fixture(temp: Path) -> tuple[Path, Path, Path]:
    repo = temp / "repo"
    origin = temp / "origin.git"
    installed = temp / "installed" / "synthetic-skill"
    skill = repo / "skills" / "synthetic-skill"
    skill.mkdir(parents=True)
    (skill / "SKILL.md").write_text(
        '---\nname: synthetic-skill\ndescription: "Use when testing. Do not publish."\n---\n\n# Synthetic\n',
        encoding="utf-8",
    )
    (repo / "VERSION").write_text("0.1.0-rc.1\n", encoding="utf-8")
    git_run(repo, "init", "-b", "main")
    git_run(repo, "config", "user.name", "Synthetic Test")
    git_run(repo, "config", "user.email", "synthetic" + "@" + "example.invalid")
    git_run(repo, "add", ".")
    git_run(repo, "commit", "-m", "Initial synthetic state")
    subprocess.run(["git", "init", "--bare", str(origin)], text=True, capture_output=True, check=True)
    git_run(repo, "remote", "add", "origin", str(origin))
    git_run(repo, "push", "-u", "origin", "main")
    shutil.copytree(skill, installed)
    return repo, skill, installed


class QualityGateBehaviorTests(unittest.TestCase):
    def test_release_state_reconciler_reports_offline_match(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            repo, skill, installed = make_release_state_fixture(Path(temp))
            result = subprocess.run(
                [
                    "python3", str(RECONCILER), str(repo),
                    "--skill-dir", str(skill),
                    "--installed-skill-dir", str(installed),
                    "--offline", "--json",
                ],
                text=True,
                capture_output=True,
                check=False,
            )
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        payload = json.loads(result.stdout)
        self.assertEqual(payload["summary"]["verdict"], "CLEAN")
        statuses = {item["area"]: item["code"] for item in payload["statuses"]}
        self.assertEqual(statuses["local_worktree"], "MATCH")
        self.assertEqual(statuses["github_branch"], "MATCH")
        self.assertEqual(statuses["installation"], "MATCH")

    def test_release_state_reconciler_ignores_installed_version_marker(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            repo, skill, installed = make_release_state_fixture(Path(temp))
            (installed / ".installed-version").write_text("0.1.0-rc.1\n", encoding="utf-8")
            result = subprocess.run(
                [
                    "python3", str(RECONCILER), str(repo),
                    "--skill-dir", str(skill),
                    "--installed-skill-dir", str(installed),
                    "--offline", "--json",
                ],
                text=True,
                capture_output=True,
                check=False,
            )
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        payload = json.loads(result.stdout)
        statuses = {item["area"]: item["code"] for item in payload["statuses"]}
        self.assertEqual(statuses["installation"], "MATCH")

    def test_release_state_reconciler_detects_not_pushed_and_install_outdated(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            repo, skill, installed = make_release_state_fixture(Path(temp))
            git_run(repo, "switch", "-c", "agent/synthetic-change")
            (skill / "SKILL.md").write_text(
                (skill / "SKILL.md").read_text(encoding="utf-8") + "\nChanged capability.\n",
                encoding="utf-8",
            )
            git_run(repo, "add", ".")
            git_run(repo, "commit", "-m", "Change synthetic capability")
            result = subprocess.run(
                [
                    "python3", str(RECONCILER), str(repo),
                    "--skill-dir", str(skill),
                    "--installed-skill-dir", str(installed),
                    "--offline", "--json",
                ],
                text=True,
                capture_output=True,
                check=False,
            )
        self.assertEqual(result.returncode, 1, result.stdout + result.stderr)
        payload = json.loads(result.stdout)
        codes = {item["code"] for item in payload["statuses"]}
        self.assertIn("NOT PUSHED", codes)
        self.assertIn("INSTALL OUTDATED", codes)

    def test_release_state_reconciler_reports_pr_open_and_actions_failed(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            repo, skill, installed = make_release_state_fixture(root)
            main_sha = git_run(repo, "rev-parse", "HEAD").stdout.strip()
            git_run(repo, "switch", "-c", "agent/synthetic-change")
            (skill / "SKILL.md").write_text(
                (skill / "SKILL.md").read_text(encoding="utf-8") + "\nChanged capability.\n",
                encoding="utf-8",
            )
            git_run(repo, "add", ".")
            git_run(repo, "commit", "-m", "Change synthetic capability")
            head = git_run(repo, "rev-parse", "HEAD").stdout.strip()
            snapshot = {
                "default_branch": "main",
                "default_sha": main_sha,
                "branch_sha": head,
                "visibility": "PUBLIC",
                "pull_requests": [{"headRefOid": head, "number": 1}],
                "actions": [{"headSha": head, "status": "completed", "conclusion": "failure"}],
                "releases": [],
            }
            snapshot_path = root / "snapshot.json"
            snapshot_path.write_text(json.dumps(snapshot), encoding="utf-8")
            result = subprocess.run(
                [
                    "python3", str(RECONCILER), str(repo),
                    "--skill-dir", str(skill),
                    "--installed-skill-dir", str(installed),
                    "--github-snapshot", str(snapshot_path), "--json",
                ],
                text=True,
                capture_output=True,
                check=False,
            )
        self.assertEqual(result.returncode, 2, result.stdout + result.stderr)
        payload = json.loads(result.stdout)
        codes = {item["code"] for item in payload["statuses"]}
        self.assertIn("PR OPEN", codes)
        self.assertIn("ACTIONS FAILED", codes)

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

    def test_missing_public_surface_manifest_returns_visual_asset_stale(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            publication = Path(temp) / "publication"
            shutil.copytree(ROOT, publication)
            target_skill = publication / "skills" / SKILL_NAME
            (publication / "docs" / "PUBLIC-SURFACE-REVIEW.json").unlink()
            result = run_gate(
                str(target_skill),
                "--publication-dir",
                str(publication),
            )
        self.assertEqual(result.returncode, 1, result.stdout + result.stderr)
        self.assertIn("VISUAL ASSET STALE", result.stdout)

    def test_changed_skill_without_public_surface_review_returns_visual_asset_stale(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            publication = Path(temp) / "publication"
            shutil.copytree(ROOT, publication)
            target_skill = publication / "skills" / SKILL_NAME
            skill_md = target_skill / "SKILL.md"
            skill_md.write_text(
                skill_md.read_text(encoding="utf-8") + "\nSynthetic capability change.\n",
                encoding="utf-8",
            )
            result = run_gate(
                str(target_skill),
                "--publication-dir",
                str(publication),
            )
        self.assertEqual(result.returncode, 1, result.stdout + result.stderr)
        self.assertIn("VISUAL ASSET STALE", result.stdout)
        self.assertIn("capability fingerprint changed", result.stdout)

    def test_user_visible_review_requires_bilingual_editable_and_rendered_assets(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            publication = Path(temp) / "publication"
            shutil.copytree(ROOT, publication)
            target_skill = publication / "skills" / SKILL_NAME
            refresh_public_surface_manifest(publication, target_skill)
            manifest_path = publication / "docs" / "PUBLIC-SURFACE-REVIEW.json"
            manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
            manifest["capability_change"] = "user_visible"
            manifest["decision"] = "UPDATED"
            manifest["reason"] = "Synthetic user-visible capability requires a bilingual visual update."
            manifest["updated_assets"] = []
            manifest_path.write_text(
                json.dumps(manifest, ensure_ascii=False, indent=2) + "\n",
                encoding="utf-8",
            )
            result = run_gate(
                str(target_skill),
                "--publication-dir",
                str(publication),
            )
        self.assertEqual(result.returncode, 1, result.stdout + result.stderr)
        self.assertIn("VISUAL ASSET STALE", result.stdout)
        self.assertIn("bilingual editable/rendered asset update incomplete", result.stdout)

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
            refresh_public_surface_manifest(publication, target)
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
            refresh_public_surface_manifest(publication, target)
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


import re as _re

CJK_FILL = "山"


def cjk_block(n: int) -> str:
    return CJK_FILL * n


def copy_skill(temp: Path) -> Path:
    target = temp / SKILL_NAME
    shutil.copytree(SKILL, target)
    return target


def set_skill_type(target: Path, skill_type: str | None) -> None:
    """Set/remove agents/risk-profile.json skill_type; preserve meta_audit exemption."""
    path = target / "agents" / "risk-profile.json"
    data = json.loads(path.read_text(encoding="utf-8"))
    if skill_type is None:
        data.pop("skill_type", None)
    else:
        data["skill_type"] = skill_type
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")


def strip_runnable_commands(target: Path) -> str:
    """Remove fenced bash/sh/shell/console blocks from SKILL.md so first-success fails."""
    md = target / "SKILL.md"
    text = md.read_text(encoding="utf-8")
    stripped = _re.sub(
        r"```(?:bash|sh|shell|console)\b.*?```",
        "\n（命令示例，已移除）\n",
        text,
        flags=_re.S | _re.I,
    )
    md.write_text(stripped, encoding="utf-8")
    assert not quality_gate_scanner.has_runnable_command(stripped)
    return stripped


class TokenAndOnboardingTests(unittest.TestCase):
    # 1. gate 审自己（无 publication）：CLEAN、退出码 0、含 token 量级区块、不崩
    def test_self_audit_prints_token_magnitude_block(self) -> None:
        result = run_gate(str(SKILL))
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertIn("Skill Quality Gate: CLEAN", result.stdout)
        self.assertIn("Token consumption magnitude", result.stdout)
        self.assertIn("estimated", result.stdout)

    # 2. --json：payload 三键、token_layers 关键字段、无 info、无绝对路径
    def test_json_payload_has_token_layers_and_no_info_severity(self) -> None:
        result = run_gate(str(SKILL), "--json")
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        payload = json.loads(result.stdout)
        for key in ("summary", "findings", "token_layers"):
            self.assertIn(key, payload)
        for key in ("entry", "agent_facing_full", "all_text_full"):
            self.assertIn(key, payload["token_layers"])
        for item in payload["findings"]:
            self.assertIn(item["severity"], {"critical", "warning", "note"})
        self.assertNotIn(str(ROOT), result.stdout)

    # 3. tool、~45K 中文 entry、无引导、有 ```bash（隔离 first-success）→ large WARNING
    def test_tool_large_monolith_without_guidance_warns(self) -> None:
        skill_md = (
            "---\n"
            "name: " + SKILL_NAME + "\n"
            'description: "Use when auditing a Skill. Do not use for unrelated tasks."\n'
            "---\n\n"
            "# 门禁\n\n"
            "本 Skill 用于审计与检查目标 Skill 的质量。\n\n"
            "```bash\n"
            "echo run-me\n"
            "```\n\n"
            + cjk_block(45000) + "\n"
        )
        self.assertTrue(quality_gate_scanner.has_runnable_command(skill_md))
        self.assertFalse(quality_gate_scanner.has_progressive_disclosure(skill_md))
        with tempfile.TemporaryDirectory() as temp:
            target = copy_skill(Path(temp))
            set_skill_type(target, "tool")
            (target / "SKILL.md").write_text(skill_md, encoding="utf-8")
            result = run_gate(str(target))
        self.assertEqual(result.returncode, 1, result.stdout + result.stderr)
        self.assertIn("Skill Quality Gate: CONCERNS", result.stdout)
        self.assertIn("large skill without progressive disclosure", result.stdout)

    # 4. domain、refs+assets >40K、SKILL.md 点名并含引导 → CLEAN、无 large WARNING（O5 健康路径）
    def test_domain_large_with_guidance_is_clean(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            target = copy_skill(Path(temp))
            set_skill_type(target, "domain")
            (target / "references" / "overview.md").write_text(cjk_block(25000), encoding="utf-8")
            (target / "assets").mkdir(exist_ok=True)
            (target / "assets" / "spec.md").write_text(cjk_block(20000), encoding="utf-8")
            md = target / "SKILL.md"
            md.write_text(
                md.read_text(encoding="utf-8")
                + "\n\n阅读顺序：先读 references/overview.md，需要时读 assets/spec.md，按需读取。\n",
                encoding="utf-8",
            )
            result = run_gate(str(target))
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertIn("Skill Quality Gate: CLEAN", result.stdout)
        self.assertNotIn("large skill without progressive disclosure", result.stdout)

    # 5. tool、agent_facing >40K 但 SKILL.md 有 references/ 路径指针 → 无 big WARNING
    def test_tool_large_with_pointer_has_no_big_warning(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            target = copy_skill(Path(temp))
            set_skill_type(target, "tool")
            (target / "references" / "parta.md").write_text(cjk_block(22000), encoding="utf-8")
            (target / "references" / "partb.md").write_text(cjk_block(22000), encoding="utf-8")
            result = run_gate(str(target))
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertIn("Skill Quality Gate: CLEAN", result.stdout)
        self.assertNotIn("large skill without progressive disclosure", result.stdout)

    # 6. tool、references/atlas.md >30K、SKILL.md 点名 atlas.md → 无 heavy finding
    def test_tool_heavy_reference_named_is_clean(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            target = copy_skill(Path(temp))
            set_skill_type(target, "tool")
            (target / "references" / "atlas.md").write_text(cjk_block(31000), encoding="utf-8")
            md = target / "SKILL.md"
            md.write_text(
                md.read_text(encoding="utf-8") + "\n\n参见 references/atlas.md（按需读取）。\n",
                encoding="utf-8",
            )
            result = run_gate(str(target))
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertIn("Skill Quality Gate: CLEAN", result.stdout)
        self.assertNotIn("heavy file not guided", result.stdout)

    # 7. tool、references/atlas.md >30K、从不提 atlas → heavy WARNING，detail 含相对路径且不回显内容
    def test_tool_heavy_reference_unnamed_warns_with_relative_path(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            target = copy_skill(Path(temp))
            set_skill_type(target, "tool")
            (target / "references" / "atlas.md").write_text(cjk_block(31000), encoding="utf-8")
            result = run_gate(str(target))
        self.assertEqual(result.returncode, 1, result.stdout + result.stderr)
        self.assertIn("Skill Quality Gate: CONCERNS", result.stdout)
        self.assertIn("heavy file not guided", result.stdout)
        self.assertIn("references/atlas.md", result.stdout)
        self.assertNotIn(cjk_block(200), result.stdout)

    # 8. 同 7 但 domain → heavy 以 NOTE 降级，退出码 0、CLEAN
    def test_domain_heavy_reference_unnamed_is_note(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            target = copy_skill(Path(temp))
            set_skill_type(target, "domain")
            (target / "references" / "atlas.md").write_text(cjk_block(31000), encoding="utf-8")
            result = run_gate(str(target))
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertIn("Skill Quality Gate: CLEAN", result.stdout)
        self.assertIn("heavy file not guided", result.stdout)

    # 9. tool、无命令无 quickstart 无 examples 无 publication → first-success WARNING
    def test_tool_missing_first_success_warns(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            target = copy_skill(Path(temp))
            set_skill_type(target, "tool")
            strip_runnable_commands(target)
            result = run_gate(str(target))
        self.assertEqual(result.returncode, 1, result.stdout + result.stderr)
        self.assertIn("Skill Quality Gate: CONCERNS", result.stdout)
        self.assertIn("first-success path missing", result.stdout)

    # 10. 同 9 但 domain → first-success 仅 NOTE，退出码 0、CLEAN
    def test_domain_missing_first_success_is_note(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            target = copy_skill(Path(temp))
            set_skill_type(target, "domain")
            strip_runnable_commands(target)
            result = run_gate(str(target))
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertIn("Skill Quality Gate: CLEAN", result.stdout)
        self.assertIn("first-success path missing", result.stdout)

    # 11. 同 9 但 risk-profile.json 无 skill_type（未声明，像门禁本身）→ 仅 NOTE、CLEAN
    def test_undeclared_type_missing_first_success_is_note(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            target = copy_skill(Path(temp))
            set_skill_type(target, None)
            strip_runnable_commands(target)
            result = run_gate(str(target))
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertIn("Skill Quality Gate: CLEAN", result.stdout)
        self.assertIn("first-success path missing", result.stdout)

    # 12. tool、散文含 '详见 ./references/foo.md' 和 'run it with bash later'，无 fenced 块 → first-success 仍触发
    def test_prose_bash_and_path_are_not_commands(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            target = copy_skill(Path(temp))
            set_skill_type(target, "tool")
            strip_runnable_commands(target)
            md = target / "SKILL.md"
            md.write_text(
                md.read_text(encoding="utf-8")
                + "\n\n补充说明：详见 ./references/foo.md ，run it with bash later。\n",
                encoding="utf-8",
            )
            result = run_gate(str(target))
        self.assertEqual(result.returncode, 1, result.stdout + result.stderr)
        self.assertIn("Skill Quality Gate: CONCERNS", result.stdout)
        self.assertIn("first-success path missing", result.stdout)

    # 13. Part A：examples/ 非空即满足 first-success；Part B：--publication-dir 的 example-prompts.md 满足
    def test_examples_satisfy_first_success_locally_and_via_publication(self) -> None:
        # Part A: 裸 SKILL.md + 非空 examples/
        with tempfile.TemporaryDirectory() as temp:
            target = copy_skill(Path(temp))
            set_skill_type(target, "tool")
            strip_runnable_commands(target)
            examples = target / "examples"
            examples.mkdir(exist_ok=True)
            (examples / "example.md").write_text("# 示例\n用户可先跑这个。\n", encoding="utf-8")
            result_a = run_gate(str(target))
        self.assertEqual(result_a.returncode, 0, result_a.stdout + result_a.stderr)
        self.assertIn("Skill Quality Gate: CLEAN", result_a.stdout)
        self.assertNotIn("first-success path missing", result_a.stdout)
        # Part B: 裸 skill + --publication-dir（其 examples/example-prompts.md 存在）
        with tempfile.TemporaryDirectory() as temp:
            publication = Path(temp) / "publication"
            shutil.copytree(ROOT, publication)
            target_skill = publication / "skills" / SKILL_NAME
            set_skill_type(target_skill, "tool")
            strip_runnable_commands(target_skill)
            self.assertTrue((publication / "examples" / "example-prompts.md").is_file())
            result_b = run_gate(str(target_skill), "--publication-dir", str(publication))
        self.assertNotIn("first-success path missing", result_b.stdout)

    # 14. tool、entry >8000 但有 fenced 命令、references 被点名 → entry-heavy NOTE 但仍 CLEAN
    def test_tool_heavy_entry_is_note_not_verdict_change(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            target = copy_skill(Path(temp))
            set_skill_type(target, "tool")
            md = target / "SKILL.md"
            md.write_text(
                md.read_text(encoding="utf-8") + "\n\n" + cjk_block(6000) + "\n",
                encoding="utf-8",
            )
            result = run_gate(str(target))
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertIn("Skill Quality Gate: CLEAN", result.stdout)
        self.assertIn("entry SKILL.md is heavy", result.stdout)


FORBIDDEN_COPY = ("模拟", "首次上手实测", "smoke test", "从严", "放宽", "更严", "更松", "放松")


def big_monolith_skill_md(with_command: bool = True) -> str:
    """Large SKILL.md, no progressive disclosure, missing core sections."""
    command = "```bash\necho run\n```\n\n" if with_command else ""
    return (
        "---\n"
        "name: " + SKILL_NAME + "\n"
        'description: "Use when auditing a Skill. Do not use for unrelated tasks."\n'
        "---\n\n"
        "# 门禁\n\n" + command + cjk_block(45000) + "\n"
    )


class AudiencePerspectiveStageReportTests(unittest.TestCase):
    # ── A：视角（audience）恒等与页脚 ──────────────────────────────────
    def test_default_final_is_identity(self) -> None:
        text = run_gate(str(SKILL))
        self.assertEqual(text.returncode, 0, text.stdout + text.stderr)
        self.assertIn("Skill Quality Gate: CLEAN", text.stdout)
        self.assertIn("视角未声明", text.stdout)
        payload = json.loads(run_gate(str(SKILL), "--json").stdout)
        self.assertEqual(payload["summary"]["verdict"], "CLEAN")
        self.assertNotIn("stage", payload["summary"])
        self.assertIn("audience", payload)
        self.assertIsNone(payload["audience"]["mode"])
        self.assertEqual(payload["audience"]["source"], "default")
        for item in payload["findings"]:
            self.assertFalse(item["title"].startswith("audience."))
            self.assertEqual(set(item.keys()), {"severity", "title", "detail"})

    def test_default_footer_wording_not_misleading(self) -> None:
        result = run_gate(str(SKILL))
        self.assertIn("视角未声明", result.stdout)
        self.assertIn("自然严重度", result.stdout)
        self.assertIn("--audience public", result.stdout)
        self.assertIn("--audience private", result.stdout)
        self.assertNotIn("不含门面", result.stdout)
        self.assertNotIn("不审门面", result.stdout)
        for word in FORBIDDEN_COPY:
            self.assertNotIn(word, result.stdout)

    def test_findings_keep_three_keys_all_modes(self) -> None:
        modes = (
            [],
            ["--audience", "public"],
            ["--audience", "private"],
            ["--audience", "private", "--publication-dir", str(ROOT)],
            ["--stage", "start"],
        )
        for extra in modes:
            payload = json.loads(run_gate(str(SKILL), "--json", *extra).stdout)
            for item in payload["findings"]:
                self.assertEqual(
                    set(item.keys()), {"severity", "title", "detail"}, f"{extra}: {item}"
                )

    def test_public_activates_facade_lifts_first_success(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            target = copy_skill(Path(temp))
            set_skill_type(target, "domain")
            strip_runnable_commands(target)
            base = run_gate(str(target))
            pub = run_gate(str(target), "--audience", "public")
            pub_json = json.loads(
                run_gate(str(target), "--audience", "public", "--json").stdout
            )
        self.assertEqual(base.returncode, 0, base.stdout)
        self.assertIn("first-success path missing", base.stdout)
        self.assertEqual(pub.returncode, 1, pub.stdout)
        self.assertIn("Skill Quality Gate: CONCERNS", pub.stdout)
        self.assertIn("审计视角：public", pub.stdout)
        lifted = [
            f for f in pub_json["findings"] if f["title"] == "first-success path missing"
        ]
        self.assertEqual([f["severity"] for f in lifted], ["warning"])
        for word in FORBIDDEN_COPY:
            self.assertNotIn(word, pub.stdout)

    def test_public_lifts_usability_note_to_warning(self) -> None:
        findings = [
            quality_gate_scanner.finding(
                "note",
                "publication may miss a GitHub usability term",
                "Security",
                check_id="pub.usability_term",
            )
        ]
        quality_gate_scanner.apply_audience_perspective(findings, "public", True, True)
        self.assertEqual(findings[0]["severity"], "warning")

    def test_public_highstar_addon_note_when_troubleshooting_missing(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            pub = Path(temp) / "pub"
            pub.mkdir()
            (pub / "README.md").write_text("hello world Roadmap only\n", encoding="utf-8")
            public_findings = quality_gate_scanner.check_publication(
                pub, SKILL, SKILL_NAME, audience_public=True
            )
            default_findings = quality_gate_scanner.check_publication(
                pub, SKILL, SKILL_NAME, audience_public=False
            )
        addons = [f for f in public_findings if f["title"] == "pub.highstar_addon"]
        self.assertEqual(len(addons), 1)
        self.assertEqual(addons[0]["severity"], "note")
        self.assertNotIn(
            "pub.highstar_addon", [f["title"] for f in default_findings]
        )

    def test_public_no_publication_emits_unevaluated_note(self) -> None:
        result = run_gate(str(SKILL), "--audience", "public", "--json")
        payload = json.loads(result.stdout)
        titles = [f["title"] for f in payload["findings"]]
        self.assertIn("audience.publication_unevaluated", titles)
        self.assertNotIn("pub.highstar_addon", titles)
        self.assertEqual(result.returncode, 0, result.stdout)

    def test_private_suppresses_facade_to_summary_note_not_downgrade(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            target = copy_skill(Path(temp))
            set_skill_type(target, "tool")
            strip_runnable_commands(target)
            base = json.loads(run_gate(str(target), "--json").stdout)
            priv = json.loads(
                run_gate(str(target), "--audience", "private", "--json").stdout
            )
        base_first = [
            f for f in base["findings"] if f["title"] == "first-success path missing"
        ]
        self.assertEqual([f["severity"] for f in base_first], ["warning"])
        priv_titles = [f["title"] for f in priv["findings"]]
        self.assertNotIn("first-success path missing", priv_titles)
        self.assertIn("audience.facade_unaudited", priv_titles)
        self.assertEqual(priv["summary"]["verdict"], "CLEAN")

    def test_private_summary_note_distinguishes_scope_vs_unevaluated(self) -> None:
        payload = json.loads(
            run_gate(str(SKILL), "--audience", "private", "--json").stdout
        )
        notes = [
            f for f in payload["findings"] if f["title"] == "audience.facade_unaudited"
        ]
        self.assertEqual(len(notes), 1)
        detail = notes[0]["detail"]
        self.assertIn("已移出范围", detail)
        self.assertIn("未评估", detail)
        self.assertNotIn("关闭 9", detail)

    def test_private_never_touches_security(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            target = copy_skill(Path(temp))
            shaped_value = "s" + "k-" + ("A" * 24)
            (target / "leak-note.md").write_text(
                "value = " + shaped_value + "\n", encoding="utf-8"
            )
            result = run_gate(str(target), "--audience", "private")
        self.assertEqual(result.returncode, 2, result.stdout)
        self.assertIn("provider credential shaped value found", result.stdout)
        self.assertNotIn(shaped_value, result.stdout)

    def test_private_never_touches_description_boundary(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            target = copy_skill(Path(temp))
            md = target / "SKILL.md"
            text = md.read_text(encoding="utf-8")
            text = text.replace(
                "Do not use to execute risky target actions, auto-repair public assets, or replace real behavior tests.",
                "Avoid executing risky target actions, auto-repairing public assets, or replacing real behavior tests.",
                1,
            )
            md.write_text(text, encoding="utf-8")
            payload = json.loads(
                run_gate(str(target), "--audience", "private", "--json").stdout
            )
        do_not = [
            f
            for f in payload["findings"]
            if f["title"] == "description lacks do-not-use boundary"
        ]
        self.assertEqual([f["severity"] for f in do_not], ["warning"])

    def test_private_publishing_conflict_audits_facade_as_public(self) -> None:
        # UNIT: effective=public → LIFT (不 suppress) + conflict NOTE
        findings = [
            quality_gate_scanner.finding(
                "note",
                "first-success path missing",
                "x",
                check_id="onboarding.first_success",
            )
        ]
        quality_gate_scanner.apply_audience_perspective(findings, "private", True, True)
        by_title = {f["title"]: f["severity"] for f in findings}
        self.assertEqual(by_title.get("first-success path missing"), "warning")
        titles = [f["title"] for f in findings]
        self.assertIn("audience.private_publishing_conflict", titles)
        self.assertNotIn("audience.facade_unaudited", titles)
        # end-to-end: private + --publication-dir triggers publishing=strict conflict NOTE
        payload = json.loads(
            run_gate(
                str(SKILL),
                "--audience",
                "private",
                "--publication-dir",
                str(ROOT),
                "--json",
            ).stdout
        )
        e2e_titles = [f["title"] for f in payload["findings"]]
        self.assertIn("audience.private_publishing_conflict", e2e_titles)
        self.assertNotIn("audience.facade_unaudited", e2e_titles)

    def test_general_checks_identical_across_audiences(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            target = copy_skill(Path(temp))
            set_skill_type(target, "domain")
            (target / "SKILL.md").write_text(big_monolith_skill_md(), encoding="utf-8")
            severities = {}
            for extra in ([], ["--audience", "public"], ["--audience", "private"]):
                payload = json.loads(
                    run_gate(str(target), "--json", *extra).stdout
                )
                large = [
                    f["severity"]
                    for f in payload["findings"]
                    if f["title"] == "large skill without progressive disclosure"
                ]
                core = [
                    f["severity"]
                    for f in payload["findings"]
                    if f["title"] == "SKILL.md may miss a core section"
                ]
                severities[tuple(extra)] = (large, core[:1])
        # large_no_progressive stays note (domain) and core.section stays warning in all
        for key, (large, core) in severities.items():
            self.assertEqual(large, ["note"], key)
            self.assertEqual(core, ["warning"], key)

    def test_cli_audience_overrides_risk_profile(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            target = copy_skill(Path(temp))
            path = target / "agents" / "risk-profile.json"
            data = json.loads(path.read_text(encoding="utf-8"))
            data["audience"] = "private"
            path.write_text(json.dumps(data), encoding="utf-8")
            payload = json.loads(
                run_gate(str(target), "--audience", "public", "--json").stdout
            )
            text = run_gate(str(target), "--audience", "public")
        self.assertEqual(payload["audience"]["mode"], "public")
        self.assertEqual(payload["audience"]["source"], "cli")
        self.assertIn("overrides risk-profile:private", text.stdout)
        self.assertNotIn(
            "audience.private_publishing_conflict",
            [f["title"] for f in payload["findings"]],
        )

    def test_invalid_risk_profile_audience_falls_back_no_crash(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            target = copy_skill(Path(temp))
            path = target / "agents" / "risk-profile.json"
            data = json.loads(path.read_text(encoding="utf-8"))
            data["audience"] = "xyz"
            path.write_text(json.dumps(data), encoding="utf-8")
            result = run_gate(str(target), "--json")
            text = run_gate(str(target))
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        payload = json.loads(result.stdout)
        self.assertIsNone(payload["audience"]["mode"])
        self.assertEqual(payload["audience"]["source"], "default")
        self.assertFalse(
            any(f["title"].startswith("audience.") for f in payload["findings"])
        )
        self.assertIn("视角未声明", text.stdout)

    def test_no_simulation_or_strictness_wording(self) -> None:
        modes = (
            [],
            ["--audience", "public"],
            ["--audience", "private"],
            ["--audience", "private", "--publication-dir", str(ROOT)],
        )
        for extra in modes:
            text = run_gate(str(SKILL), *extra)
            report = run_gate(str(SKILL), "--report", *extra)
            for word in FORBIDDEN_COPY:
                self.assertNotIn(word, text.stdout, f"{extra} text has {word}")
                self.assertNotIn(word, report.stdout, f"{extra} report has {word}")
            self.assertIn("静态核验", report.stdout)
            self.assertIn("公开门面清单", report.stdout)

    def test_no_info_severity_and_no_keyerror_any_mode(self) -> None:
        json_modes = (
            ["--audience", "public"],
            ["--audience", "private"],
            ["--audience", "private", "--publication-dir", str(ROOT)],
            ["--stage", "start"],
            ["--stage", "final"],
        )
        for extra in json_modes:
            payload = json.loads(run_gate(str(SKILL), "--json", *extra).stdout)
            for item in payload["findings"]:
                self.assertIn(
                    item["severity"], {"critical", "warning", "note"}, f"{extra}: {item}"
                )
        for extra in (
            ["--audience", "public"],
            ["--audience", "private"],
            ["--stage", "start"],
            ["--report"],
        ):
            result = run_gate(str(SKILL), *extra)
            self.assertIn(result.returncode, (0, 1, 2), f"{extra}")
            self.assertTrue(result.stdout.strip(), f"{extra} produced no output")
        start = run_gate(str(SKILL), "--stage", "start")
        self.assertIn("要件全景", start.stdout)

    # ── B：--stage ────────────────────────────────────────────────────
    def test_stage_final_equals_no_stage(self) -> None:
        no_stage = run_gate(str(SKILL))
        final = run_gate(str(SKILL), "--stage", "final")
        self.assertEqual(no_stage.returncode, final.returncode)
        no_stage_json = json.loads(run_gate(str(SKILL), "--json").stdout)
        final_json = json.loads(
            run_gate(str(SKILL), "--stage", "final", "--json").stdout
        )
        self.assertEqual(no_stage_json["summary"], final_json["summary"])
        self.assertEqual(no_stage_json["findings"], final_json["findings"])

    def test_stage_start_never_blocks_on_critical(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            target = copy_skill(Path(temp))
            (target / "SKILL.md").unlink()
            text = run_gate(str(target), "--stage", "start")
            payload = json.loads(
                run_gate(str(target), "--stage", "start", "--json").stdout
            )
        self.assertEqual(text.returncode, 0, text.stdout)
        self.assertIn("Skill Quality Gate: DRAFTING", text.stdout)
        self.assertIn("◆地基", text.stdout)
        self.assertEqual(payload["summary"]["verdict"], "DRAFTING")
        self.assertEqual(payload["summary"]["stage"], "start")

    def test_stage_start_security_shown_but_exit_zero(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            target = copy_skill(Path(temp))
            shaped_value = "s" + "k-" + ("A" * 24)
            (target / "leak-note.md").write_text(
                "value = " + shaped_value + "\n", encoding="utf-8"
            )
            result = run_gate(str(target), "--stage", "start")
        self.assertEqual(result.returncode, 0, result.stdout)
        self.assertIn("Skill Quality Gate: DRAFTING", result.stdout)
        self.assertIn("provider credential shaped value found", result.stdout)
        self.assertNotIn(shaped_value, result.stdout)

    def test_stage_start_does_not_suppress_facade(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            target = copy_skill(Path(temp))
            set_skill_type(target, "tool")
            strip_runnable_commands(target)
            result = run_gate(
                str(target), "--stage", "start", "--audience", "private", "--json"
            )
        payload = json.loads(result.stdout)
        titles = [f["title"] for f in payload["findings"]]
        self.assertIn("first-success path missing", titles)
        self.assertNotIn("audience.facade_unaudited", titles)
        self.assertEqual(payload["summary"]["verdict"], "DRAFTING")
        self.assertEqual(result.returncode, 0)

    def test_stage_start_scaffold_subset_of_check_ids(self) -> None:
        for family_name, ids, _is_gh in quality_gate_scanner.SCAFFOLD_FAMILIES:
            for check_id in ids:
                self.assertIn(
                    check_id,
                    quality_gate_scanner.ALL_CHECK_IDS,
                    f"{family_name}: {check_id}",
                )

    def test_stage_start_gh_baseline_visible_by_default(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            target = copy_skill(Path(temp))
            set_skill_type(target, "domain")
            default_start = run_gate(str(target), "--stage", "start")
            private_start = run_gate(
                str(target), "--stage", "start", "--audience", "private"
            )
        self.assertIn("对外发布门面", default_start.stdout)
        self.assertNotIn("以后开源再看", default_start.stdout)
        self.assertIn("以后开源再看", private_start.stdout)
        self.assertIn("对外发布门面", private_start.stdout)

    # ── C：--report / 修复优先级 ──────────────────────────────────────
    def test_report_card_has_disclaimer_fingerprint_and_advice(self) -> None:
        result = run_gate(str(SKILL), "--report")
        out = result.stdout
        self.assertIn("静态机器扫描", out)
        self.assertIn("重跑", out)
        self.assertRegex(out, r"[0-9a-f]{64}")
        self.assertIn("可继续", out)
        self.assertIn("未完成·需人工", out)
        self.assertNotIn(str(ROOT), out)

    def test_report_and_json_mutually_exclusive(self) -> None:
        result = run_gate(str(SKILL), "--report", "--json")
        self.assertEqual(result.returncode, 2)

    def test_report_escapes_markdown_injection(self) -> None:
        findings = [
            quality_gate_scanner.finding(
                "warning", "weird `x` | title", "detail with | pipe and `code`"
            )
        ]
        summary = quality_gate_scanner.summarize(findings)
        notice = quality_gate_scanner.audience_notice(None, "default", False, False)
        report = quality_gate_scanner.render_report(
            findings, summary, "0" * 64, "final", notice, {0: "质量"}
        )
        self.assertIn("\\|", report)
        self.assertNotIn("`x`", report)
        rows = [line for line in report.splitlines() if line.startswith("| 🟡")]
        self.assertTrue(rows)
        for row in rows:
            self.assertEqual(row.count("|") - row.count("\\|"), 4, row)

    def test_remediation_plan_ordered_and_catchall(self) -> None:
        findings = [
            quality_gate_scanner.finding(
                "note", "n1", "d", check_id="pub.usability_term"
            ),
            quality_gate_scanner.finding(
                "warning", "w1", "d", check_id="onboarding.first_success"
            ),
            quality_gate_scanner.finding("critical", "c1", "d"),
            quality_gate_scanner.finding("warning", "w2", "d"),
        ]
        plan = quality_gate_scanner.build_remediation_plan(findings)
        self.assertEqual(len(plan), len(findings))
        self.assertEqual([e["title"] for e in plan], ["c1", "w1", "w2", "n1"])
        lanes = {e["title"]: e["lane"] for e in plan}
        self.assertEqual(lanes["c1"], "质量")
        self.assertEqual(lanes["w2"], "质量")
        self.assertEqual(lanes["w1"], "上手")
        self.assertEqual(lanes["n1"], "发布")

    def test_terminal_findings_keep_order_with_lane_tags(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            target = copy_skill(Path(temp))
            set_skill_type(target, "tool")
            strip_runnable_commands(target)
            result = run_gate(str(target))
        self.assertIn("first-success path missing", result.stdout)
        self.assertIn("[上手]", result.stdout)
        self.assertIn("建议修复顺序", result.stdout)
        self.assertIn("先修这条", result.stdout)
        self.assertNotIn(str(ROOT), result.stdout)

    def test_ci_self_audit_publication_dir_still_clean(self) -> None:
        # 主控收尾负责刷新 PUBLIC-SURFACE-REVIEW.json 指纹；本测试只焊死 audience 的
        # 附加物不改变 default 自审 findings（drift-tolerant，指纹刷新前后皆绿）。
        result = run_gate(str(SKILL), "--publication-dir", str(ROOT), "--json")
        payload = json.loads(result.stdout)
        self.assertIn("audience", payload)
        self.assertIsNone(payload["audience"]["mode"])
        self.assertEqual(payload["audience"]["source"], "default")
        titles = [f["title"] for f in payload["findings"]]
        self.assertNotIn("pub.highstar_addon", titles)
        self.assertFalse(any(t.startswith("audience.") for t in titles))
        for item in payload["findings"]:
            self.assertEqual(set(item.keys()), {"severity", "title", "detail"})
        for warning in [f for f in payload["findings"] if f["severity"] == "warning"]:
            self.assertEqual(
                warning["title"],
                "VISUAL ASSET STALE",
                "default self-audit must only be non-clean via fingerprint drift",
            )


# ── O6：命名前缀 / skill_type 降级 / O5 结构降级 / CORE 同义词的回归覆盖 ──────
#
# 关键约束：POLICY / 「interaction and onboarding」降级用的是全树扫描文本
# (scan_tree(skill))。真 Skill 的 copytree 无法让 POLICY finding 触发，因为它自带的
# scripts/skill_quality_gate.py 逐字含每个策略词条。所以策略类断言必须用一个「不含
# 这些词条」的新造最小 Skill（build_minimal_skill）；结构类（references 嵌套）与
# CORE 同义词只读 SKILL.md/结构，可复用 copy_skill。

TOOL_ONLY_POLICY_TITLES = (
    "missing or weak new user capability preflight",
    "missing or weak token budget policy",
    "missing or weak companion Skill routing",
    "missing or weak independent product entry",
    "missing or weak interaction and onboarding",
)


def build_minimal_skill(temp: Path, skill_type: str | None, *, name: str = "acme-x-tool") -> Path:
    """新造一个低风险最小 Skill，其全部文本刻意不含工具类策略词条，
    从而让 POLICY finding 真正触发，可按 skill_type 校验其严重度。"""
    target = temp / name
    (target / "agents").mkdir(parents=True)
    (target / "references").mkdir()
    (target / "SKILL.md").write_text(
        "---\n"
        f"name: {name}\n"
        'description: "Use when auditing a Skill. Do not use for unrelated tasks."\n'
        "---\n\n"
        "# Gate\n\nThis Skill audits a target Skill.\n"
        "```bash\necho run\n```\n",
        encoding="utf-8",
    )
    (target / "references" / "guide.md").write_text(
        "# Guide\nMinimal reference.\n", encoding="utf-8"
    )
    (target / "agents" / "openai.yaml").write_text("name: gate\n", encoding="utf-8")
    profile = {"schema_version": 1, "risk_level": "low", "risk_context": "meta_audit"}
    if skill_type is not None:
        profile["skill_type"] = skill_type
    (target / "agents" / "risk-profile.json").write_text(
        json.dumps(profile), encoding="utf-8"
    )
    return target


def severity_by_title(target: Path, *extra: str) -> dict[str, str]:
    payload = json.loads(run_gate(str(target), "--json", *extra).stdout)
    return {f["title"]: f["severity"] for f in payload["findings"]}


# O6.1 命名前缀检查两态
class NamingPrefixConventionTests(unittest.TestCase):
    def test_naming_prefix_warns_when_set_and_name_off_convention(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            target = Path(temp) / "acme-some-tool"
            shutil.copytree(SKILL, target)
            md = target / "SKILL.md"
            md.write_text(
                md.read_text(encoding="utf-8").replace(
                    "name: " + SKILL_NAME, "name: acme-some-tool", 1
                ),
                encoding="utf-8",
            )
            result = run_gate(
                str(target),
                "--json",
                env={"SKILL_QUALITY_GATE_NAME_PREFIX": "lucas-deepwheel-"},
            )
        payload = json.loads(result.stdout)
        naming = [
            f
            for f in payload["findings"]
            if f["title"]
            == "Skill name does not follow the configured naming convention"
        ]
        self.assertEqual([f["severity"] for f in naming], ["warning"])
        self.assertIn("lucas-deepwheel-", naming[0]["detail"])
        self.assertEqual(result.returncode, 1, result.stdout + result.stderr)

    def test_naming_prefix_warns_when_unset_is_note(self) -> None:
        result = run_gate(
            str(SKILL), "--json", env={"SKILL_QUALITY_GATE_NAME_PREFIX": None}
        )
        payload = json.loads(result.stdout)
        notes = [
            f
            for f in payload["findings"]
            if f["title"] == "no naming convention configured"
        ]
        self.assertEqual([f["severity"] for f in notes], ["note"])
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)

    def test_naming_prefix_clean_when_set_and_name_follows(self) -> None:
        result = run_gate(
            str(SKILL),
            "--json",
            env={"SKILL_QUALITY_GATE_NAME_PREFIX": "lucas-deepwheel-"},
        )
        payload = json.loads(result.stdout)
        naming = [
            f
            for f in payload["findings"]
            if "naming convention" in f["title"]
            or f["title"] == "no naming convention configured"
        ]
        self.assertEqual(naming, [])
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)


# O6.2 skill_type=domain 对工具类 POLICY 降级为 NOTE；tool/undeclared 保持 WARNING
class SkillTypePolicyDowngradeTests(unittest.TestCase):
    def test_tool_only_policy_downgrades_to_note_for_domain(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            target = build_minimal_skill(Path(temp), "domain")
            sev = severity_by_title(target)
        for title in TOOL_ONLY_POLICY_TITLES:
            self.assertEqual(sev.get(title), "note", title)
        # capability claims 不在工具类白名单：即便 domain 也保持 WARNING（不误降）。
        self.assertEqual(sev.get("missing or weak capability claims"), "warning")

    def test_tool_only_policy_stays_warning_for_tool(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            target = build_minimal_skill(Path(temp), "tool")
            sev = severity_by_title(target)
        for title in TOOL_ONLY_POLICY_TITLES:
            self.assertEqual(sev.get(title), "warning", title)

    def test_tool_only_policy_stays_warning_for_undeclared(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            target = build_minimal_skill(Path(temp), None)
            sev = severity_by_title(target)
        for title in TOOL_ONLY_POLICY_TITLES:
            self.assertEqual(sev.get(title), "warning", title)


# O6.3 O5 结构降级：references 嵌套 + 缺 onboarding 关键词（恢复/渐进）
class StructureAndOnboardingDowngradeTests(unittest.TestCase):
    def _nested_severity(self, skill_type: str | None) -> list[str]:
        with tempfile.TemporaryDirectory() as temp:
            target = copy_skill(Path(temp))
            set_skill_type(target, skill_type)
            nested = target / "references" / "nested"
            nested.mkdir()
            (nested / "deep.md").write_text("# deep\n", encoding="utf-8")
            payload = json.loads(run_gate(str(target), "--json").stdout)
        return [
            f["severity"]
            for f in payload["findings"]
            if f["title"] == "references are nested"
        ]

    def test_o5_references_nested_note_for_domain(self) -> None:
        self.assertEqual(self._nested_severity("domain"), ["note"])

    def test_o5_references_nested_warning_for_tool(self) -> None:
        self.assertEqual(self._nested_severity("tool"), ["warning"])

    def test_o5_references_nested_warning_for_undeclared(self) -> None:
        self.assertEqual(self._nested_severity(None), ["warning"])

    def test_o5_onboarding_keyword_note_for_domain(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            target = build_minimal_skill(Path(temp), "domain")
            payload = json.loads(run_gate(str(target), "--json").stdout)
        onboarding = [
            f
            for f in payload["findings"]
            if f["title"] == "missing or weak interaction and onboarding"
        ]
        self.assertEqual([f["severity"] for f in onboarding], ["note"])
        # 缺口明细含 onboarding 关键词（恢复/渐进）——确证审的是交互恢复这一维。
        self.assertIn("恢复", onboarding[0]["detail"])
        self.assertIn("渐进", onboarding[0]["detail"])

    def test_o5_onboarding_keyword_warning_for_tool(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            target = build_minimal_skill(Path(temp), "tool")
            payload = json.loads(run_gate(str(target), "--json").stdout)
        onboarding = [
            f["severity"]
            for f in payload["findings"]
            if f["title"] == "missing or weak interaction and onboarding"
        ]
        self.assertEqual(onboarding, ["warning"])


# O6.4 CORE_GROUPS 同义词：换措辞不误报缺章节
class CoreSectionSynonymTests(unittest.TestCase):
    def test_core_groups_accept_synonyms(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            target = copy_skill(Path(temp))
            md = target / "SKILL.md"
            md.write_text(
                "---\n"
                "name: " + SKILL_NAME + "\n"
                'description: "Use when auditing a Skill. Do not use for unrelated tasks."\n'
                "---\n\n"
                "# 门禁\n\n"
                "## 使用边界\n略\n"  # group 1 同义（另有 description 的 Use when）
                "## 不使用\n略\n"  # group 2 同义（另有 description 的 Do not）
                "## 生成流程\n略\n"  # group 3：生成流程 ≈ 标准流程
                "## 安全边界\n略\n"  # group 4
                "## 交付前自检\n略\n",  # group 5：交付前自检 ≈ 完成前验收
                encoding="utf-8",
            )
            payload = json.loads(run_gate(str(target), "--json").stdout)
        core = [
            f
            for f in payload["findings"]
            if f["title"] == "SKILL.md may miss a core section"
        ]
        self.assertEqual(core, [], core)


if __name__ == "__main__":
    unittest.main()
