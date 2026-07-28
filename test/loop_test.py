"""Black-box lifecycle tests for the Project Loop state machine."""

import hashlib
import importlib.util
import json
import os
import subprocess
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
LOOP_PY = (
    ROOT
    / "plugins"
    / "project-loop"
    / "skills"
    / "project-loop"
    / "scripts"
    / "loop.py"
)
LOOP_SPEC = importlib.util.spec_from_file_location("project_loop_state_machine", LOOP_PY)
LOOP_MODULE = importlib.util.module_from_spec(LOOP_SPEC)
LOOP_SPEC.loader.exec_module(LOOP_MODULE)


class LoopLifecycleTest(unittest.TestCase):
    def setUp(self):
        self.sandbox = tempfile.TemporaryDirectory(prefix="project-loop-test-")
        self.project = Path(self.sandbox.name)

    def tearDown(self):
        self.sandbox.cleanup()

    def run_loop(self, *args):
        return subprocess.run(
            ["python3", str(LOOP_PY), *args],
            cwd=self.project,
            capture_output=True,
            text=True,
            check=False,
        )

    def init_loop(self):
        result = self.run_loop("init")
        self.assertEqual(result.returncode, 0, result.stderr)

    @property
    def state_path(self):
        return self.project / "loop-project/loop.json"

    def read_state(self):
        return json.loads(self.state_path.read_text(encoding="utf-8"))

    def write_state(self, state):
        self.state_path.write_text(
            json.dumps(state, indent=2) + "\n", encoding="utf-8"
        )

    def prepare_g0(self):
        self.init_loop()
        result = self.run_loop("roles", "--confirm")
        self.assertEqual(result.returncode, 0, result.stderr)
        plan_dir = self.project / "loop-project/0-plan"
        (plan_dir / "brd.md").write_text(
            """# Business requirements

| ID | Outcome | For whom | Success measure | Cost of not doing it | Priority |
|----|---------|----------|-----------------|----------------------|----------|
| BR-001 | Verified lifecycle | builders | invalid transitions fail | false PASS | Must |

## Won't do this cycle
- Hosted dashboard
""",
            encoding="utf-8",
        )
        (plan_dir / "prd.md").write_text(
            """# Product specification

## Functional requirements
| ID | Requirement | Pattern | Traces to |
|----|-------------|---------|-----------|
| FR-001 | When a gate is passed, the system shall validate its predecessor | event-driven | BR-001 |

## Unwanted behaviour
| ID | Requirement | Traces to |
|----|-------------|-----------|
| FR-002 | If evidence is missing, then the system shall reject closure | BR-001 |

## Non-functional requirements
Deterministic results with stable exit codes.

## Non-goals
- Hosted dashboard
""",
            encoding="utf-8",
        )
        (plan_dir / "dod.md").write_text(
            """# Definition of Done

FROZEN AT G0. Changes after G0 require a human decision recorded in ledger.md.

## Project-level
- [ ] Lifecycle transitions are enforced
- [ ] Human approval is recorded

## Acceptance checklist
| ID | Requirement | How it is proven | Evidence artifact |
|----|-------------|------------------|-------------------|
| AC-001 | FR-001: predecessor is enforced | lifecycle test | QA report |
""",
            encoding="utf-8",
        )

    def enable_build_phase(self):
        self.init_loop()
        state = self.read_state()
        state["phase"] = 2
        state["gates"]["g0"] = {"passed": True, "at": "2026-07-28T00:00:00Z"}
        state["gates"]["g1"] = {"passed": True, "at": "2026-07-28T00:01:00Z"}
        state["frozen_roles"] = list(state["roles"]["enabled"])
        self.write_state(state)

    def run_git(self, *args):
        return subprocess.run(
            ["git", *args],
            cwd=self.project,
            capture_output=True,
            text=True,
            check=False,
        )

    def init_git_baseline(self):
        self.assertEqual(self.run_git("init", "-q").returncode, 0)
        (self.project / "README.md").write_text("# Fixture\n", encoding="utf-8")
        self.assertEqual(self.run_git("add", "README.md").returncode, 0)
        commit = self.run_git(
            "-c",
            "user.name=Project Loop Test",
            "-c",
            "user.email=test@example.invalid",
            "commit",
            "-qm",
            "baseline",
        )
        self.assertEqual(commit.returncode, 0, commit.stderr)

    def write_valid_report(self, task_id="TASK-001", changed_path="src/example.py"):
        task_path = self.project / f"loop-project/2-build/tasks/{task_id}.md"
        if task_path.exists():
            task_text = task_path.read_text(encoding="utf-8")
            task_text = task_text.replace("AC-00x", "AC-001").replace(
                "FR-00x", "FR-001"
            )
            task_path.write_text(task_text, encoding="utf-8")
        report_dir = self.project / "loop-project/2-build/reports"
        report_dir.mkdir(parents=True, exist_ok=True)
        (report_dir / f"{task_id}.report.md").write_text(
            f"""# REPORT {task_id}
Status: Done

## Summary
Implemented the task and recorded reproducible evidence.

## Files changed
- {changed_path} (new) — task implementation

## Commands run
$ python3 -m unittest
OK

## Reuse
Searched: "task implementation" — no reusable unit was needed.

## Acceptance
| AC | Proven by | Result |
|----|-----------|--------|
| AC-001 | lifecycle test | pass |

## Assumptions
none

## Risks
none

## Blocked
none
""",
            encoding="utf-8",
        )

    def write_valid_qa(self, task_id="TASK-001", qa_id="QA-001"):
        qa_dir = self.project / "loop-project/3-verify/qa"
        qa_dir.mkdir(parents=True, exist_ok=True)
        path = qa_dir / f"{qa_id}.md"
        path.write_text(
            f"""# {qa_id} — {task_id}
Tester pass. Date: 2026-07-28

## Commands run
$ python3 -m unittest
OK

## Acceptance verified independently
| AC | Re-ran | Result |
|----|--------|--------|
| AC-001 | lifecycle test | pass |

## Findings
none

## Observations
none

## Regression
Full suite: pass, 1 passed, 0 failed
""",
            encoding="utf-8",
        )
        return path

    def write_valid_verdict(self, task_id="TASK-001", verdict_id="V-001"):
        verdict_dir = self.project / "loop-project/3-verify/verdicts"
        verdict_dir.mkdir(parents=True, exist_ok=True)
        path = verdict_dir / f"{verdict_id}.md"
        checks = "\n".join(
            f"| {number} | Check {number} | pass | |" for number in range(1, 10)
        )
        path.write_text(
            f"""# VERDICT {verdict_id} — {task_id} — cycle 0
Date: 2026-07-28
Verdict: PASS

## Checks
| # | Check | Result | Note |
|---|-------|--------|------|
{checks}

## Orders
none

## Observations
none

## Loop state
Cycle 0 of 5 for {task_id}. Continue.
""",
            encoding="utf-8",
        )
        return path

    def write_valid_rework_verdict(self, task_id="TASK-001", verdict_id="V-001"):
        path = self.write_valid_verdict(task_id, verdict_id)
        text = path.read_text(encoding="utf-8")
        text = text.replace("Verdict: PASS", "Verdict: REWORK")
        text = text.replace("| 4 | Check 4 | pass | |", "| 4 | Check 4 | fail | duplicated code |")
        text = text.replace("## Orders\nnone", "## Orders\nR-001-01 (Sev-2, cause: craft)")
        path.write_text(text, encoding="utf-8")
        return path

    def write_valid_rework_order(self, order_id="R-001-01"):
        rework_dir = self.project / "loop-project/3-verify/rework"
        rework_dir.mkdir(parents=True, exist_ok=True)
        path = rework_dir / f"{order_id}.md"
        path.write_text(
            f"""## {order_id} — Sev-2 — Reuse the registered formatter
Finding-ID: duplicate-formatter
Domain: craft
DoD-impact: no
Finding: The implementation duplicates an existing formatter.
Evidence: src/example.py:10 duplicates the registered shared implementation.
Required: Reuse the registered formatter without changing observable behaviour.
Re-check: Run the unit suite and the duplicate-component check.
Cause: craft
""",
            encoding="utf-8",
        )
        return path

    def write_valid_blocked_verdict(self, task_id="TASK-001", verdict_id="V-001"):
        path = self.write_valid_verdict(task_id, verdict_id)
        text = path.read_text(encoding="utf-8")
        text = text.replace("Verdict: PASS", "Verdict: BLOCKED")
        text = text.replace("| 5 | Check 5 | pass | |", "| 5 | Check 5 | fail | contradictory spec |")
        text = text.replace(
            f"Cycle 0 of 5 for {task_id}. Continue.",
            f"Cycle 0 of 5 for {task_id}. Blocked pending a human scope decision.",
        )
        path.write_text(text, encoding="utf-8")
        return path

    def write_valid_security_report(self, task_id="TASK-001", report_id="SEC-001"):
        path = self.project / f"loop-project/3-verify/qa/{report_id}.md"
        path.write_text(
            f"""# {report_id} — {task_id}
Adversary pass. Date: 2026-07-28

## Commands run
$ python3 -m unittest
OK

## Acceptance verified independently
| AC | Re-ran | Result |
|----|--------|--------|
| AC-001 | hostile-input lifecycle test | pass |

## Findings
none

## Observations
none

## Regression
Full suite: pass, 1 passed, 0 failed
""",
            encoding="utf-8",
        )
        return path

    def write_valid_ui_report(self, task_id="TASK-001", report_id="UI-001"):
        path = self.project / f"loop-project/3-verify/qa/{report_id}.md"
        path.write_text(
            f"""# {report_id} — {task_id}
UI Critic pass. Date: 2026-07-28

Surfaces examined: task lifecycle screen
How: running app at http://127.0.0.1:3000

## Anti-generic bans
No banned patterns were present.

## Token discipline
Computed values matched the token set.

## Data stress
Zero, long, null, and RTL data passed.

## Required states
Default, focus, disabled, loading, empty, and error states passed.

## The one deliberate decision
Density remained consistent across three surfaces.

## Copy
No banned register, placeholders, or ceiling violations.

## Findings
none

## Coverage
Lifecycle task list, task detail, and verdict state were examined.
""",
            encoding="utf-8",
        )
        return path

    def write_valid_product_owner_report(self, report_id="PO-001"):
        path = self.project / f"loop-project/3-verify/verdicts/{report_id}.md"
        path.write_text(
            f"""# PRODUCT OWNER {report_id} — project outcome
Verdict: PASS

## Business requirements
BR-001 met its success measure.

## Evidence
Observed the verified lifecycle reject invalid transitions in the running system.
""",
            encoding="utf-8",
        )
        return path

    def prepare_valid_pass(self, extra_dod_ac=False):
        self.enable_build_phase()
        self.init_git_baseline()
        task = self.run_loop("task", "new", "Proven task")
        self.assertEqual(task.returncode, 0, task.stderr)
        source = self.project / "src/example.py"
        source.parent.mkdir(parents=True, exist_ok=True)
        source.write_text("VALUE = 1\n", encoding="utf-8")
        if extra_dod_ac:
            dod = self.project / "loop-project/0-plan/dod.md"
            dod.write_text(
                dod.read_text(encoding="utf-8")
                + "\n| AC-002 | FR-002: second requirement | lifecycle test | QA report |\n",
                encoding="utf-8",
            )
        self.write_valid_report()
        qa_path = self.write_valid_qa()
        verdict_path = self.write_valid_verdict()
        g2 = self.run_loop("gate", "g2", "--pass")
        self.assertEqual(g2.returncode, 0, g2.stdout + g2.stderr)
        verdict = self.run_loop(
            "verdict",
            "TASK-001",
            "pass",
            "--file",
            str(verdict_path.relative_to(self.project)),
            "--qa",
            str(qa_path.relative_to(self.project)),
        )
        self.assertEqual(verdict.returncode, 0, verdict.stdout + verdict.stderr)
        dod = self.project / "loop-project/0-plan/dod.md"
        state = self.read_state()
        state["dod_hash"] = hashlib.sha256(dod.read_bytes()).hexdigest()
        self.write_state(state)
        return qa_path, verdict_path

    def test_task_creation_is_refused_before_g1(self):
        self.init_loop()

        result = self.run_loop("task", "new", "Premature task")

        self.assertEqual(result.returncode, 2)
        self.assertIn("tasks can only be created after G1", result.stderr)
        self.assertFalse(
            (self.project / "loop-project/2-build/tasks/TASK-001.md").exists()
        )

    def test_task_creation_is_refused_after_g2(self):
        self.enable_build_phase()
        state = self.read_state()
        state["phase"] = 3
        state["gates"]["g2"] = {"passed": True, "at": "2026-07-28T00:02:00Z"}
        self.write_state(state)

        result = self.run_loop("task", "new", "Late task")

        self.assertEqual(result.returncode, 2)
        self.assertIn("only be created during Phase 2", result.stderr)

    def test_parallel_task_creation_keeps_every_state_update(self):
        self.enable_build_phase()
        processes = [
            subprocess.Popen(
                ["python3", str(LOOP_PY), "task", "new", f"Parallel task {number}"],
                cwd=self.project,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
            )
            for number in range(8)
        ]
        results = [process.communicate(timeout=20) + (process.returncode,)
                   for process in processes]

        for stdout, stderr, returncode in results:
            self.assertEqual(returncode, 0, stdout + stderr)
        state = self.read_state()
        self.assertEqual(len(state["tasks"]), 8)
        self.assertEqual(
            sorted(state["tasks"]),
            [f"TASK-{number:03d}" for number in range(1, 9)],
        )
        self.assertEqual(
            len(list((self.project / "loop-project/2-build/tasks").glob("TASK-*.md"))),
            8,
        )

    def test_force_init_archives_the_existing_loop_instead_of_mixing_state(self):
        self.init_loop()
        old_task = self.project / "loop-project/2-build/tasks/TASK-001.md"
        old_task.write_text("# old task\n", encoding="utf-8")
        state = self.read_state()
        state["tasks"]["TASK-001"] = {"title": "Old", "verdict": "PASS"}
        self.write_state(state)

        result = self.run_loop("init", "--force")

        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        archives = sorted(self.project.glob("loop-project.archive-*"))
        self.assertEqual(len(archives), 1)
        self.assertTrue((archives[0] / "2-build/tasks/TASK-001.md").exists())
        self.assertFalse(old_task.exists())
        self.assertEqual(self.read_state()["tasks"], {})
        self.assertIn("Archived previous loop", result.stdout)

    def test_init_rejects_a_symlinked_loop_root_that_escapes_the_project(self):
        with tempfile.TemporaryDirectory(prefix="project-loop-external-") as external:
            (self.project / "loop-project").symlink_to(
                Path(external), target_is_directory=True
            )

            result = self.run_loop("init")

            self.assertEqual(result.returncode, 2)
            self.assertIn("loop-project must be a real directory inside the project", result.stderr)
            self.assertFalse((Path(external) / "loop.json").exists())

    def test_force_init_archives_an_escaping_root_symlink_without_writing_through_it(self):
        with tempfile.TemporaryDirectory(prefix="project-loop-external-") as external:
            external_path = Path(external)
            (self.project / "loop-project").symlink_to(
                external_path, target_is_directory=True
            )

            result = self.run_loop("init", "--force")

            self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
            self.assertFalse((external_path / "loop.json").exists())
            self.assertTrue((self.project / "loop-project/loop.json").is_file())
            archives = list(self.project.glob("loop-project.archive-*"))
            self.assertEqual(len(archives), 1)
            self.assertTrue(archives[0].is_symlink())

    def test_init_rejects_a_nested_phase_symlink_without_seeding_external_files(self):
        with tempfile.TemporaryDirectory(prefix="project-loop-phase-external-") as external:
            (self.project / "loop-project").mkdir()
            (self.project / "loop-project/0-plan").symlink_to(
                Path(external), target_is_directory=True
            )

            result = self.run_loop("init")

            self.assertEqual(result.returncode, 2)
            self.assertIn("loop-project already exists", result.stderr)
            self.assertFalse((Path(external) / "research.md").exists())

    def test_task_creation_rejects_a_nested_owned_symlink(self):
        self.enable_build_phase()
        tasks = self.project / "loop-project/2-build/tasks"
        tasks.rmdir()
        with tempfile.TemporaryDirectory(prefix="project-loop-task-external-") as external:
            tasks.symlink_to(Path(external), target_is_directory=True)

            result = self.run_loop("task", "new", "Escaping task card")

            self.assertEqual(result.returncode, 2)
            self.assertIn("loop-project contains a symlink", result.stderr)
            self.assertFalse((Path(external) / "TASK-001.md").exists())

    def test_ledger_write_rejects_a_symlinked_file(self):
        self.init_loop()
        ledger = self.project / "loop-project/ledger.md"
        ledger.unlink()
        with tempfile.TemporaryDirectory(prefix="project-loop-ledger-external-") as external:
            external_ledger = Path(external) / "ledger.md"
            external_ledger.write_text("unchanged\n", encoding="utf-8")
            ledger.symlink_to(external_ledger)

            result = self.run_loop("block", "Must not escape")

            self.assertEqual(result.returncode, 2)
            self.assertIn("loop-project contains a symlink", result.stderr)
            self.assertEqual(
                external_ledger.read_text(encoding="utf-8"), "unchanged\n"
            )

    def test_invalid_state_shape_fails_with_a_clear_error(self):
        self.init_loop()
        state = self.read_state()
        state["phase"] = 99
        self.write_state(state)

        result = self.run_loop("status")

        self.assertEqual(result.returncode, 2)
        self.assertIn("loop.json has invalid phase", result.stderr)
        self.assertNotIn("Traceback", result.stderr)

    def test_gate_pass_refuses_out_of_order_transition(self):
        self.init_loop()

        result = self.run_loop("gate", "g3", "--pass")

        self.assertEqual(result.returncode, 2)
        self.assertIn("G3 requires G2 to have passed", result.stderr)

    def test_a_gate_cannot_be_passed_twice(self):
        self.init_loop()
        state = self.read_state()
        state["phase"] = 2
        state["gates"]["g0"] = {"passed": True, "at": "2026-07-28T00:00:00Z"}
        state["gates"]["g1"] = {"passed": True, "at": "2026-07-28T00:01:00Z"}
        self.write_state(state)

        result = self.run_loop("gate", "g1", "--pass")

        self.assertEqual(result.returncode, 2)
        self.assertIn("G1 has already passed", result.stderr)

    def test_g3_requires_at_least_one_task(self):
        self.init_loop()
        state = self.read_state()
        for gate in ("g0", "g1", "g2"):
            state["gates"][gate] = {"passed": True, "at": "2026-07-28T00:00:00Z"}
        state["phase"] = 3
        dod = self.project / "loop-project/0-plan/dod.md"
        state["dod_hash"] = hashlib.sha256(dod.read_bytes()).hexdigest()
        self.write_state(state)
        (self.project / "README.md").write_text("# Test project\n", encoding="utf-8")

        result = self.run_loop("gate", "g3", "--pass")

        self.assertEqual(result.returncode, 1)
        self.assertIn("FAIL  tasks exist", result.stdout)
        self.assertNotEqual(self.read_state()["status"], "PASS")

    def test_g0_pass_requires_explicit_human_approval(self):
        self.prepare_g0()

        result = self.run_loop("gate", "g0", "--pass")

        self.assertEqual(result.returncode, 2)
        self.assertIn("G0 requires human approval", result.stderr)
        self.assertFalse(self.read_state()["gates"]["g0"]["passed"])

    def test_human_can_approve_g0_after_checks_pass(self):
        self.prepare_g0()

        approval = self.run_loop("approve", "g0", "--by", "Test Human")

        self.assertEqual(approval.returncode, 0, approval.stderr)
        recorded = self.read_state()["approvals"]["g0"]
        self.assertTrue(recorded["approved"])
        self.assertEqual(recorded["by"], "Test Human")

        result = self.run_loop("gate", "g0", "--pass")
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertTrue(self.read_state()["gates"]["g0"]["passed"])

    def test_role_roster_is_frozen_when_g0_passes(self):
        self.prepare_g0()
        roles = self.run_loop("roles", "--enable", "adversary")
        self.assertEqual(roles.returncode, 0, roles.stderr)
        approval = self.run_loop("approve", "g0", "--by", "Test Human")
        self.assertEqual(approval.returncode, 0, approval.stderr)
        passed = self.run_loop("gate", "g0", "--pass")
        self.assertEqual(passed.returncode, 0, passed.stderr)

        result = self.run_loop("roles", "--disable", "adversary")

        self.assertEqual(result.returncode, 2)
        self.assertIn("role roster was frozen at G0", result.stderr)
        state = self.read_state()
        self.assertIn("adversary", state["frozen_roles"])
        self.assertIn("adversary", state["roles"]["enabled"])

    def test_human_approval_rejects_a_blank_identity(self):
        self.prepare_g0()

        result = self.run_loop("approve", "g0", "--by", "")

        self.assertEqual(result.returncode, 2)
        self.assertIn("approver identity must not be blank", result.stderr)
        self.assertNotIn("g0", self.read_state()["approvals"])

    def test_g0_approval_is_invalidated_when_approved_artifacts_change(self):
        self.prepare_g0()
        approval = self.run_loop("approve", "g0", "--by", "Test Human")
        self.assertEqual(approval.returncode, 0, approval.stderr)
        dod = self.project / "loop-project/0-plan/dod.md"
        dod.write_text(
            dod.read_text(encoding="utf-8") + "\nApproved scope changed afterward.\n",
            encoding="utf-8",
        )

        result = self.run_loop("gate", "g0", "--pass")

        self.assertEqual(result.returncode, 2)
        self.assertIn("G0 approval is stale", result.stderr)
        self.assertFalse(self.read_state()["gates"]["g0"]["passed"])

    def test_task_records_the_git_baseline_when_created(self):
        self.enable_build_phase()
        self.assertEqual(self.run_git("init", "-q").returncode, 0)
        (self.project / "README.md").write_text("# Fixture\n", encoding="utf-8")
        self.assertEqual(self.run_git("add", "README.md").returncode, 0)
        commit = self.run_git(
            "-c",
            "user.name=Project Loop Test",
            "-c",
            "user.email=test@example.invalid",
            "commit",
            "-qm",
            "fixture",
        )
        self.assertEqual(commit.returncode, 0, commit.stderr)
        expected_sha = self.run_git("rev-parse", "HEAD").stdout.strip()

        result = self.run_loop("task", "new", "Baseline-aware task")

        self.assertEqual(result.returncode, 0, result.stderr)
        task = self.read_state()["tasks"]["TASK-001"]
        self.assertEqual(task["base_sha"], expected_sha)

    def test_verify_detects_committed_changes_outside_the_task_write_set(self):
        self.enable_build_phase()
        self.assertEqual(self.run_git("init", "-q").returncode, 0)
        (self.project / "README.md").write_text("# Fixture\n", encoding="utf-8")
        self.assertEqual(self.run_git("add", "README.md").returncode, 0)
        base = self.run_git(
            "-c",
            "user.name=Project Loop Test",
            "-c",
            "user.email=test@example.invalid",
            "commit",
            "-qm",
            "base",
        )
        self.assertEqual(base.returncode, 0, base.stderr)
        task = self.run_loop("task", "new", "Scoped task")
        self.assertEqual(task.returncode, 0, task.stderr)
        (self.project / "outside.txt").write_text("out of scope\n", encoding="utf-8")
        self.assertEqual(self.run_git("add", "outside.txt").returncode, 0)
        changed = self.run_git(
            "-c",
            "user.name=Project Loop Test",
            "-c",
            "user.email=test@example.invalid",
            "commit",
            "-qm",
            "out of scope change",
        )
        self.assertEqual(changed.returncode, 0, changed.stderr)
        self.write_valid_report(changed_path="outside.txt")

        result = self.run_loop("verify", "TASK-001")

        self.assertEqual(result.returncode, 1)
        self.assertIn("outside write-set: outside.txt", result.stdout)

    def test_verify_fails_closed_when_a_git_task_has_no_commit_baseline(self):
        self.enable_build_phase()
        self.assertEqual(self.run_git("init", "-q").returncode, 0)
        task = self.run_loop("task", "new", "Unanchored task")
        self.assertEqual(task.returncode, 0, task.stderr)
        self.write_valid_report()

        result = self.run_loop("verify", "TASK-001")

        self.assertEqual(result.returncode, 1)
        self.assertIn("FAIL  Git baseline valid", result.stdout)

    def test_verify_detects_skip_markers_in_a_new_untracked_test_file(self):
        self.enable_build_phase()
        self.assertEqual(self.run_git("init", "-q").returncode, 0)
        (self.project / "README.md").write_text("# Fixture\n", encoding="utf-8")
        self.assertEqual(self.run_git("add", "README.md").returncode, 0)
        base = self.run_git(
            "-c",
            "user.name=Project Loop Test",
            "-c",
            "user.email=test@example.invalid",
            "commit",
            "-qm",
            "base",
        )
        self.assertEqual(base.returncode, 0, base.stderr)
        task = self.run_loop("task", "new", "Test integrity")
        self.assertEqual(task.returncode, 0, task.stderr)
        test_file = self.project / "src/example.test.js"
        test_file.parent.mkdir(parents=True, exist_ok=True)
        test_file.write_text('test.skip("works", () => {});\n', encoding="utf-8")
        self.write_valid_report(changed_path="src/example.test.js")

        result = self.run_loop("verify", "TASK-001")

        self.assertEqual(result.returncode, 1)
        self.assertIn("skip/only marker added", result.stdout)

    def test_verify_rejects_weakening_a_preexisting_test(self):
        self.enable_build_phase()
        self.init_git_baseline()
        test_file = self.project / "src/example.test.js"
        test_file.parent.mkdir(parents=True, exist_ok=True)
        test_file.write_text(
            'test("value", () => expect(value).toBe(42));\n', encoding="utf-8"
        )
        self.assertEqual(self.run_git("add", "src/example.test.js").returncode, 0)
        commit = self.run_git(
            "-c",
            "user.name=Project Loop Test",
            "-c",
            "user.email=test@example.invalid",
            "commit",
            "-qm",
            "existing test contract",
        )
        self.assertEqual(commit.returncode, 0, commit.stderr)
        task = self.run_loop("task", "new", "Weaken existing test")
        self.assertEqual(task.returncode, 0, task.stderr)
        test_file.write_text(
            'test("value", () => expect(value).toBeTruthy());\n', encoding="utf-8"
        )
        self.write_valid_report(changed_path="src/example.test.js")

        result = self.run_loop("verify", "TASK-001")

        self.assertEqual(result.returncode, 1)
        self.assertIn("pre-existing test modified", result.stdout)

    def test_verify_rejects_a_changed_symlink_that_escapes_the_project(self):
        self.enable_build_phase()
        self.init_git_baseline()
        task = self.run_loop("task", "new", "Escaping source link")
        self.assertEqual(task.returncode, 0, task.stderr)
        with tempfile.TemporaryDirectory(prefix="project-loop-source-external-") as external:
            external_file = Path(external) / "secret.py"
            external_file.write_text("SECRET = 1\n", encoding="utf-8")
            source = self.project / "src"
            source.mkdir()
            (source / "escape.py").symlink_to(external_file)
            self.write_valid_report(changed_path="src/escape.py")

            result = self.run_loop("verify", "TASK-001")

        self.assertEqual(result.returncode, 1)
        self.assertIn("FAIL  changed paths confined", result.stdout)
        self.assertIn("resolves outside the project", result.stdout)

    def test_g2_rejects_a_report_that_exists_but_is_not_valid(self):
        self.enable_build_phase()
        task = self.run_loop("task", "new", "Reported task")
        self.assertEqual(task.returncode, 0, task.stderr)
        report = self.project / "loop-project/2-build/reports/TASK-001.report.md"
        report.write_text("# not a valid report\n", encoding="utf-8")

        result = self.run_loop("gate", "g2", "--pass")

        self.assertEqual(result.returncode, 1)
        self.assertIn("FAIL  every REPORT schema-valid", result.stdout)
        self.assertFalse(self.read_state()["gates"]["g2"]["passed"])

    def test_g2_rejects_a_report_for_the_wrong_task(self):
        self.enable_build_phase()
        task = self.run_loop("task", "new", "Reported task")
        self.assertEqual(task.returncode, 0, task.stderr)
        self.write_valid_report(task_id="TASK-001")
        report = self.project / "loop-project/2-build/reports/TASK-001.report.md"
        report.write_text(
            report.read_text(encoding="utf-8").replace(
                "# REPORT TASK-001", "# REPORT TASK-002"
            ),
            encoding="utf-8",
        )

        result = self.run_loop("gate", "g2", "--pass")

        self.assertEqual(result.returncode, 1)
        self.assertIn("REPORT heading does not name TASK-001", result.stdout)

    def test_g2_rejects_a_done_report_with_a_failed_acceptance_result(self):
        self.enable_build_phase()
        task = self.run_loop("task", "new", "Failed acceptance")
        self.assertEqual(task.returncode, 0, task.stderr)
        self.write_valid_report()
        report = self.project / "loop-project/2-build/reports/TASK-001.report.md"
        report.write_text(
            report.read_text(encoding="utf-8").replace(
                "| AC-001 | lifecycle test | pass |",
                "| AC-001 | lifecycle test | fail |",
            ),
            encoding="utf-8",
        )

        result = self.run_loop("gate", "g2", "--pass")

        self.assertEqual(result.returncode, 1)
        self.assertIn("Acceptance result must be pass", result.stdout)

    def test_g2_rejects_a_report_whose_acceptance_ids_do_not_match_the_task(self):
        self.enable_build_phase()
        task = self.run_loop("task", "new", "Wrong acceptance mapping")
        self.assertEqual(task.returncode, 0, task.stderr)
        self.write_valid_report()
        report = self.project / "loop-project/2-build/reports/TASK-001.report.md"
        report.write_text(
            report.read_text(encoding="utf-8").replace("AC-001", "AC-002"),
            encoding="utf-8",
        )

        result = self.run_loop("gate", "g2", "--pass")

        self.assertEqual(result.returncode, 1)
        self.assertIn("acceptance does not exactly match", result.stdout)

    def test_pass_verdict_is_refused_without_worker_qa_and_judge_artifacts(self):
        self.enable_build_phase()
        task = self.run_loop("task", "new", "Unproven task")
        self.assertEqual(task.returncode, 0, task.stderr)
        state = self.read_state()
        state["phase"] = 3
        state["gates"]["g2"] = {"passed": True, "at": "2026-07-28T00:02:00Z"}
        self.write_state(state)

        result = self.run_loop(
            "verdict",
            "TASK-001",
            "pass",
            "--file",
            "loop-project/3-verify/verdicts/V-001.md",
            "--qa",
            "loop-project/3-verify/qa/QA-001.md",
        )

        self.assertEqual(result.returncode, 1)
        self.assertIn("Worker REPORT missing", result.stdout)
        self.assertIsNone(self.read_state()["tasks"]["TASK-001"]["verdict"])

    def test_pass_verdict_is_refused_without_tester_qa(self):
        self.enable_build_phase()
        task = self.run_loop("task", "new", "Unverified task")
        self.assertEqual(task.returncode, 0, task.stderr)
        self.write_valid_report()
        state = self.read_state()
        state["phase"] = 3
        state["gates"]["g2"] = {"passed": True, "at": "2026-07-28T00:02:00Z"}
        self.write_state(state)

        result = self.run_loop(
            "verdict",
            "TASK-001",
            "pass",
            "--file",
            "loop-project/3-verify/verdicts/V-001.md",
            "--qa",
            "loop-project/3-verify/qa/QA-001.md",
        )

        self.assertEqual(result.returncode, 1)
        self.assertIn("Tester QA missing", result.stdout)
        self.assertIsNone(self.read_state()["tasks"]["TASK-001"]["verdict"])

    def test_pass_verdict_is_refused_without_judge_verdict_artifact(self):
        self.enable_build_phase()
        task = self.run_loop("task", "new", "Unjudged task")
        self.assertEqual(task.returncode, 0, task.stderr)
        self.write_valid_report()
        qa_path = self.write_valid_qa()
        state = self.read_state()
        state["phase"] = 3
        state["gates"]["g2"] = {"passed": True, "at": "2026-07-28T00:02:00Z"}
        self.write_state(state)

        result = self.run_loop(
            "verdict",
            "TASK-001",
            "pass",
            "--file",
            "loop-project/3-verify/verdicts/V-001.md",
            "--qa",
            str(qa_path.relative_to(self.project)),
        )

        self.assertEqual(result.returncode, 1)
        self.assertIn("Judge verdict missing", result.stdout)
        self.assertIsNone(self.read_state()["tasks"]["TASK-001"]["verdict"])

    def test_pass_verdict_rejects_qa_for_a_different_acceptance_set(self):
        self.enable_build_phase()
        self.init_git_baseline()
        task = self.run_loop("task", "new", "Exact QA mapping")
        self.assertEqual(task.returncode, 0, task.stderr)
        source = self.project / "src/example.py"
        source.parent.mkdir(parents=True, exist_ok=True)
        source.write_text("VALUE = 1\n", encoding="utf-8")
        self.write_valid_report()
        qa_path = self.write_valid_qa()
        qa_path.write_text(
            qa_path.read_text(encoding="utf-8").replace("AC-001", "AC-002"),
            encoding="utf-8",
        )
        verdict_path = self.write_valid_verdict()

        result = self.run_loop(
            "verdict",
            "TASK-001",
            "pass",
            "--file",
            str(verdict_path.relative_to(self.project)),
            "--qa",
            str(qa_path.relative_to(self.project)),
        )

        self.assertEqual(result.returncode, 1)
        self.assertIn("QA acceptance does not exactly match", result.stdout)
        self.assertIsNone(self.read_state()["tasks"]["TASK-001"]["verdict"])

    def test_pass_verdict_rejects_an_evidence_directory_symlink_escape(self):
        self.enable_build_phase()
        task = self.run_loop("task", "new", "Escaped evidence")
        self.assertEqual(task.returncode, 0, task.stderr)
        self.write_valid_report()
        qa_dir = self.project / "loop-project/3-verify/qa"
        qa_dir.rmdir()
        outside = self.project / "outside-evidence"
        outside.mkdir()
        qa_dir.symlink_to(outside, target_is_directory=True)
        qa_path = self.write_valid_qa()
        verdict_path = self.write_valid_verdict()
        state = self.read_state()
        state["phase"] = 3
        state["gates"]["g2"] = {"passed": True, "at": "2026-07-28T00:02:00Z"}
        self.write_state(state)

        result = self.run_loop(
            "verdict",
            "TASK-001",
            "pass",
            "--file",
            str(verdict_path.relative_to(self.project)),
            "--qa",
            str(qa_path.relative_to(self.project)),
        )

        self.assertEqual(result.returncode, 2)
        self.assertIn("loop-project contains a symlink", result.stderr)
        self.assertIsNone(self.read_state()["tasks"]["TASK-001"]["verdict"])

    def test_valid_worker_qa_and_judge_artifacts_record_task_pass(self):
        self.prepare_valid_pass()
        task_state = self.read_state()["tasks"]["TASK-001"]
        self.assertEqual(task_state["verdict"], "PASS")
        self.assertEqual(task_state["qa_file"], "loop-project/3-verify/qa/QA-001.md")
        self.assertEqual(
            task_state["verdict_file"],
            "loop-project/3-verify/verdicts/V-001.md",
        )

    def test_pass_verdict_rejects_duplicate_judge_check_numbers(self):
        self.enable_build_phase()
        task = self.run_loop("task", "new", "Suspicious verdict")
        self.assertEqual(task.returncode, 0, task.stderr)
        self.write_valid_report()
        qa_path = self.write_valid_qa()
        verdict_path = self.write_valid_verdict()
        verdict_path.write_text(
            verdict_path.read_text(encoding="utf-8").replace(
                "| 2 | Check 2 |", "| 1 | Check 2 |"
            ),
            encoding="utf-8",
        )
        g2 = self.run_loop("gate", "g2", "--pass")
        self.assertEqual(g2.returncode, 0, g2.stdout + g2.stderr)

        result = self.run_loop(
            "verdict",
            "TASK-001",
            "pass",
            "--file",
            str(verdict_path.relative_to(self.project)),
            "--qa",
            str(qa_path.relative_to(self.project)),
        )

        self.assertEqual(result.returncode, 1)
        self.assertIn("Judge verdict valid", result.stdout)
        self.assertIsNone(self.read_state()["tasks"]["TASK-001"]["verdict"])

    def test_g3_refuses_a_forged_pass_without_valid_evidence(self):
        self.enable_build_phase()
        task = self.run_loop("task", "new", "Forged task")
        self.assertEqual(task.returncode, 0, task.stderr)
        self.write_valid_report()
        state = self.read_state()
        state["phase"] = 3
        state["gates"]["g2"] = {"passed": True, "at": "2026-07-28T00:02:00Z"}
        state["tasks"]["TASK-001"]["verdict"] = "PASS"
        dod = self.project / "loop-project/0-plan/dod.md"
        state["dod_hash"] = hashlib.sha256(dod.read_bytes()).hexdigest()
        self.write_state(state)
        (self.project / "README.md").write_text("# Test project\n", encoding="utf-8")

        result = self.run_loop("gate", "g3", "--pass")

        self.assertEqual(result.returncode, 1)
        self.assertIn("FAIL  PASS evidence independently valid", result.stdout)
        self.assertNotEqual(self.read_state()["status"], "PASS")

    def test_g3_refuses_pass_when_recorded_evidence_was_changed(self):
        qa_path, _ = self.prepare_valid_pass()
        qa_path.write_text(
            qa_path.read_text(encoding="utf-8") + "\nTampered after verdict.\n",
            encoding="utf-8",
        )

        result = self.run_loop("gate", "g3", "--pass")

        self.assertEqual(result.returncode, 1)
        self.assertIn("FAIL  PASS evidence hashes intact", result.stdout)
        self.assertNotEqual(self.read_state()["status"], "PASS")

    def test_g3_refuses_pass_when_the_task_acceptance_changed_after_verdict(self):
        self.prepare_valid_pass()
        card = self.project / "loop-project/2-build/tasks/TASK-001.md"
        card.write_text(
            card.read_text(encoding="utf-8").replace("AC-001", "AC-002"),
            encoding="utf-8",
        )

        result = self.run_loop("gate", "g3", "--pass")

        self.assertEqual(result.returncode, 1)
        self.assertIn("FAIL  PASS evidence hashes intact", result.stdout)
        self.assertIn("task: content changed after verdict", result.stdout)
        self.assertNotEqual(self.read_state()["status"], "PASS")

    def test_g3_refuses_pass_when_source_changed_after_task_verdict(self):
        self.prepare_valid_pass()
        source = self.project / "src/example.py"
        source.write_text("VALUE = 2\n", encoding="utf-8")

        result = self.run_loop("gate", "g3", "--pass")

        self.assertEqual(result.returncode, 1)
        self.assertIn("FAIL  PASS result snapshots intact", result.stdout)
        self.assertNotEqual(self.read_state()["status"], "PASS")

    def test_g3_refuses_a_final_source_path_owned_by_no_passing_task(self):
        self.prepare_valid_pass()
        extra = self.project / "src/unreviewed.py"
        extra.write_text("UNREVIEWED = True\n", encoding="utf-8")

        result = self.run_loop("gate", "g3", "--pass")

        self.assertEqual(result.returncode, 1)
        self.assertIn("FAIL  every final changed path attributed", result.stdout)
        self.assertIn("src/unreviewed.py", result.stdout)
        self.assertNotEqual(self.read_state()["status"], "PASS")

    def test_g3_refuses_pass_when_a_delivered_file_mode_changed(self):
        self.prepare_valid_pass()
        source = self.project / "src/example.py"
        source.chmod(0o755)

        result = self.run_loop("gate", "g3", "--pass")

        self.assertEqual(result.returncode, 1)
        self.assertIn("FAIL  PASS result snapshots intact", result.stdout)
        self.assertNotEqual(self.read_state()["status"], "PASS")

    def test_g3_requires_qa_coverage_for_every_frozen_acceptance_row(self):
        self.prepare_valid_pass(extra_dod_ac=True)

        result = self.run_loop("gate", "g3", "--pass")

        self.assertEqual(result.returncode, 1)
        self.assertIn("FAIL  frozen DoD acceptance covered", result.stdout)
        self.assertIn("AC-002", result.stdout)
        self.assertNotEqual(self.read_state()["status"], "PASS")

    def test_g3_rejects_placeholder_security_evidence_when_adversary_is_enabled(self):
        self.prepare_valid_pass()
        state = self.read_state()
        state["roles"]["enabled"].append("adversary")
        state["frozen_roles"].append("adversary")
        self.write_state(state)
        security = self.project / "loop-project/3-verify/qa/SEC-001.md"
        security.write_text("# placeholder\n", encoding="utf-8")

        result = self.run_loop("gate", "g3", "--pass")

        self.assertEqual(result.returncode, 1)
        self.assertIn("FAIL  adversary evidence valid", result.stdout)
        self.assertNotEqual(self.read_state()["status"], "PASS")

    def test_g3_rejects_placeholder_ui_evidence_when_ui_critic_is_enabled(self):
        self.prepare_valid_pass()
        state = self.read_state()
        state["roles"]["enabled"].append("ui-critic")
        state["frozen_roles"].append("ui-critic")
        self.write_state(state)
        ui = self.project / "loop-project/3-verify/qa/UI-001.md"
        ui.write_text("# placeholder\n", encoding="utf-8")

        result = self.run_loop("gate", "g3", "--pass")

        self.assertEqual(result.returncode, 1)
        self.assertIn("FAIL  UI critique evidence valid", result.stdout)
        self.assertNotEqual(self.read_state()["status"], "PASS")

    def test_g3_accepts_schema_valid_security_and_ui_evidence(self):
        self.prepare_valid_pass()
        state = self.read_state()
        state["roles"]["enabled"].extend(["adversary", "ui-critic", "product-owner"])
        state["frozen_roles"].extend(["adversary", "ui-critic", "product-owner"])
        self.write_state(state)
        self.write_valid_security_report()
        self.write_valid_ui_report()
        self.write_valid_product_owner_report()

        result = self.run_loop("gate", "g3", "--pass")

        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertEqual(self.read_state()["status"], "PASS")

    def test_g3_rejects_placeholder_business_acceptance_when_product_owner_enabled(self):
        self.prepare_valid_pass()
        state = self.read_state()
        state["roles"]["enabled"].append("product-owner")
        state["frozen_roles"].append("product-owner")
        self.write_state(state)
        product_owner = self.project / "loop-project/3-verify/verdicts/PO-001.md"
        product_owner.write_text("# placeholder\n", encoding="utf-8")

        result = self.run_loop("gate", "g3", "--pass")

        self.assertEqual(result.returncode, 1)
        self.assertIn("FAIL  business acceptance valid", result.stdout)
        self.assertNotEqual(self.read_state()["status"], "PASS")

    def test_pass_verdict_runs_scope_verification_instead_of_trusting_claims(self):
        self.enable_build_phase()
        self.assertEqual(self.run_git("init", "-q").returncode, 0)
        (self.project / "README.md").write_text("# Fixture\n", encoding="utf-8")
        self.assertEqual(self.run_git("add", "README.md").returncode, 0)
        base = self.run_git(
            "-c",
            "user.name=Project Loop Test",
            "-c",
            "user.email=test@example.invalid",
            "commit",
            "-qm",
            "base",
        )
        self.assertEqual(base.returncode, 0, base.stderr)
        task = self.run_loop("task", "new", "Scoped task")
        self.assertEqual(task.returncode, 0, task.stderr)
        (self.project / "outside.txt").write_text("out of scope\n", encoding="utf-8")
        self.assertEqual(self.run_git("add", "outside.txt").returncode, 0)
        changed = self.run_git(
            "-c",
            "user.name=Project Loop Test",
            "-c",
            "user.email=test@example.invalid",
            "commit",
            "-qm",
            "out of scope",
        )
        self.assertEqual(changed.returncode, 0, changed.stderr)
        self.write_valid_report(changed_path="outside.txt")
        qa_path = self.write_valid_qa()
        verdict_path = self.write_valid_verdict()
        g2 = self.run_loop("gate", "g2", "--pass")
        self.assertEqual(g2.returncode, 0, g2.stdout + g2.stderr)

        result = self.run_loop(
            "verdict",
            "TASK-001",
            "pass",
            "--file",
            str(verdict_path.relative_to(self.project)),
            "--qa",
            str(qa_path.relative_to(self.project)),
        )

        self.assertEqual(result.returncode, 1)
        self.assertIn("mechanical task verification", result.stdout)
        self.assertIsNone(self.read_state()["tasks"]["TASK-001"]["verdict"])

    def test_pass_verdict_fails_closed_on_a_secret_without_git(self):
        self.enable_build_phase()
        task = self.run_loop("task", "new", "Secret-bearing task")
        self.assertEqual(task.returncode, 0, task.stderr)
        source = self.project / "src/example.py"
        source.parent.mkdir(parents=True, exist_ok=True)
        credential_name = "api" + "_key"
        credential_value = "live-" + "secret-value-123456789"
        source.write_text(
            f'{credential_name} = "{credential_value}"\n',
            encoding="utf-8",
        )
        self.write_valid_report()
        qa_path = self.write_valid_qa()
        verdict_path = self.write_valid_verdict()
        g2 = self.run_loop("gate", "g2", "--pass")
        self.assertEqual(g2.returncode, 0, g2.stdout + g2.stderr)

        result = self.run_loop(
            "verdict",
            "TASK-001",
            "pass",
            "--file",
            str(verdict_path.relative_to(self.project)),
            "--qa",
            str(qa_path.relative_to(self.project)),
        )

        self.assertEqual(result.returncode, 1)
        self.assertIn("FAIL  no secrets introduced", result.stdout)
        self.assertIsNone(self.read_state()["tasks"]["TASK-001"]["verdict"])

    def test_rework_verdict_requires_a_schema_valid_order_artifact(self):
        self.enable_build_phase()
        task = self.run_loop("task", "new", "Needs rework")
        self.assertEqual(task.returncode, 0, task.stderr)
        self.write_valid_report()
        verdict_path = self.write_valid_rework_verdict()
        state = self.read_state()
        state["phase"] = 3
        state["gates"]["g2"] = {"passed": True, "at": "2026-07-28T00:02:00Z"}
        self.write_state(state)

        result = self.run_loop(
            "verdict",
            "TASK-001",
            "rework",
            "--file",
            str(verdict_path.relative_to(self.project)),
        )

        self.assertEqual(result.returncode, 1)
        self.assertIn("rework order artifact", result.stdout)
        self.assertIsNone(self.read_state()["tasks"]["TASK-001"]["verdict"])

    def test_rework_verdict_records_order_and_increments_cycle(self):
        self.enable_build_phase()
        task = self.run_loop("task", "new", "Needs rework")
        self.assertEqual(task.returncode, 0, task.stderr)
        self.write_valid_report()
        verdict_path = self.write_valid_rework_verdict()
        order_path = self.write_valid_rework_order()
        state = self.read_state()
        state["phase"] = 3
        state["gates"]["g2"] = {"passed": True, "at": "2026-07-28T00:02:00Z"}
        self.write_state(state)

        result = self.run_loop(
            "verdict",
            "TASK-001",
            "rework",
            "--file",
            str(verdict_path.relative_to(self.project)),
            "--order",
            str(order_path.relative_to(self.project)),
        )

        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        task_state = self.read_state()["tasks"]["TASK-001"]
        self.assertEqual(task_state["verdict"], "REWORK")
        self.assertEqual(task_state["cycles"], 1)
        self.assertEqual(
            task_state["rework_files"],
            ["loop-project/3-verify/rework/R-001-01.md"],
        )

    def test_legacy_cycle_command_is_retired_without_mutating_state(self):
        self.enable_build_phase()
        task = self.run_loop("task", "new", "No evidence bypass")
        self.assertEqual(task.returncode, 0, task.stderr)

        result = self.run_loop("cycle", "TASK-001")

        self.assertEqual(result.returncode, 2)
        self.assertIn("cycle is retired", result.stderr)
        task_state = self.read_state()["tasks"]["TASK-001"]
        self.assertEqual(task_state["cycles"], 0)
        self.assertIsNone(task_state["verdict"])

    def test_rework_that_requires_a_dod_change_blocks_immediately(self):
        self.enable_build_phase()
        task = self.run_loop("task", "new", "Frozen finish line")
        self.assertEqual(task.returncode, 0, task.stderr)
        self.write_valid_report()
        verdict_path = self.write_valid_rework_verdict()
        order_path = self.write_valid_rework_order()
        order_path.write_text(
            order_path.read_text(encoding="utf-8")
            .replace("Finding-ID: duplicate-formatter", "Finding-ID: scope-contradiction")
            .replace(
                "Required: Reuse the registered formatter without changing observable behaviour.",
                "Required: Change the Definition of Done to remove AC-001.",
            ),
            encoding="utf-8",
        )

        result = self.run_loop(
            "verdict",
            "TASK-001",
            "rework",
            "--file",
            str(verdict_path.relative_to(self.project)),
            "--order",
            str(order_path.relative_to(self.project)),
        )

        self.assertEqual(result.returncode, 1)
        state = self.read_state()
        self.assertEqual(state["status"], "BLOCKED")
        self.assertIn("frozen Definition of Done", state["blocked_reason"])

    def test_recurring_sev1_security_finding_blocks_on_second_occurrence(self):
        self.enable_build_phase()
        task = self.run_loop("task", "new", "Recurring security flaw")
        self.assertEqual(task.returncode, 0, task.stderr)
        self.write_valid_report()
        verdict_path = self.write_valid_rework_verdict()
        order_path = self.write_valid_rework_order()
        order_path.write_text(
            order_path.read_text(encoding="utf-8")
            .replace("Sev-2", "Sev-1")
            .replace("Finding-ID: duplicate-formatter", "Finding-ID: missing-authorization")
            .replace(
                "Finding: The implementation duplicates an existing formatter.",
                "Finding: Authorization is missing on the protected endpoint.",
            ),
            encoding="utf-8",
        )
        command = (
            "verdict",
            "TASK-001",
            "rework",
            "--file",
            str(verdict_path.relative_to(self.project)),
            "--order",
            str(order_path.relative_to(self.project)),
        )

        first = self.run_loop(*command)
        second = self.run_loop(*command)

        self.assertEqual(first.returncode, 0, first.stdout + first.stderr)
        self.assertEqual(second.returncode, 1, second.stdout + second.stderr)
        state = self.read_state()
        self.assertEqual(state["status"], "BLOCKED")
        self.assertIn("Sev-1 security finding", state["blocked_reason"])
        self.assertEqual(
            state["tasks"]["TASK-001"]["security_sev1_findings"][
                "missing-authorization"
            ],
            2,
        )

    def test_changing_a_finding_label_does_not_reset_recurrence(self):
        self.enable_build_phase()
        task = self.run_loop("task", "new", "Relabelled recurring flaw")
        self.assertEqual(task.returncode, 0, task.stderr)
        self.write_valid_report()
        verdict_path = self.write_valid_rework_verdict()
        order_path = self.write_valid_rework_order()
        command = (
            "verdict",
            "TASK-001",
            "rework",
            "--file",
            str(verdict_path.relative_to(self.project)),
            "--order",
            str(order_path.relative_to(self.project)),
        )

        first = self.run_loop(*command)
        order_path.write_text(
            order_path.read_text(encoding="utf-8").replace(
                "Finding-ID: duplicate-formatter",
                "Finding-ID: duplicate-formatter-renamed",
            ),
            encoding="utf-8",
        )
        second = self.run_loop(*command)
        order_path.write_text(
            order_path.read_text(encoding="utf-8").replace(
                "Finding-ID: duplicate-formatter-renamed",
                "Finding-ID: duplicate-formatter-renamed-again",
            ),
            encoding="utf-8",
        )
        third = self.run_loop(*command)

        self.assertEqual(first.returncode, 0, first.stdout + first.stderr)
        self.assertEqual(second.returncode, 0, second.stdout + second.stderr)
        self.assertEqual(third.returncode, 1, third.stdout + third.stderr)
        state = self.read_state()
        self.assertEqual(state["status"], "BLOCKED")
        self.assertEqual(
            state["tasks"]["TASK-001"]["findings"]["duplicate-formatter"], 3
        )

    def test_rework_requires_an_artifact_for_every_order_cited_by_judge(self):
        self.enable_build_phase()
        task = self.run_loop("task", "new", "Two findings")
        self.assertEqual(task.returncode, 0, task.stderr)
        self.write_valid_report()
        verdict_path = self.write_valid_rework_verdict()
        verdict_path.write_text(
            verdict_path.read_text(encoding="utf-8").replace(
                "R-001-01 (Sev-2, cause: craft)",
                "R-001-01 (Sev-2, cause: craft)\nR-001-02 (Sev-2, cause: code)",
            ),
            encoding="utf-8",
        )
        order_path = self.write_valid_rework_order()
        state = self.read_state()
        state["phase"] = 3
        state["gates"]["g2"] = {"passed": True, "at": "2026-07-28T00:02:00Z"}
        self.write_state(state)

        result = self.run_loop(
            "verdict",
            "TASK-001",
            "rework",
            "--file",
            str(verdict_path.relative_to(self.project)),
            "--order",
            str(order_path.relative_to(self.project)),
        )

        self.assertEqual(result.returncode, 1)
        self.assertIn("missing artifact for cited order R-001-02", result.stdout)
        self.assertIsNone(self.read_state()["tasks"]["TASK-001"]["verdict"])

    def test_two_sequential_task_passes_survive_unrelated_later_task_changes(self):
        self.enable_build_phase()
        self.init_git_baseline()

        first = self.run_loop("task", "new", "First task")
        self.assertEqual(first.returncode, 0, first.stderr)
        first_card = self.project / "loop-project/2-build/tasks/TASK-001.md"
        first_card.write_text(
            first_card.read_text(encoding="utf-8").replace("src/**", "src/one.py"),
            encoding="utf-8",
        )
        source_dir = self.project / "src"
        source_dir.mkdir()
        (source_dir / "one.py").write_text("ONE = 1\n", encoding="utf-8")
        self.write_valid_report("TASK-001", "src/one.py")
        qa1 = self.write_valid_qa("TASK-001", "QA-001")
        verdict1 = self.write_valid_verdict("TASK-001", "V-001")
        passed1 = self.run_loop(
            "verdict",
            "TASK-001",
            "pass",
            "--file",
            str(verdict1.relative_to(self.project)),
            "--qa",
            str(qa1.relative_to(self.project)),
        )
        self.assertEqual(passed1.returncode, 0, passed1.stdout + passed1.stderr)
        self.assertEqual(self.run_git("add", "src/one.py").returncode, 0)
        commit1 = self.run_git(
            "-c",
            "user.name=Project Loop Test",
            "-c",
            "user.email=test@example.invalid",
            "commit",
            "-qm",
            "first task",
        )
        self.assertEqual(commit1.returncode, 0, commit1.stderr)

        second = self.run_loop("task", "new", "Second task")
        self.assertEqual(second.returncode, 0, second.stderr)
        second_card = self.project / "loop-project/2-build/tasks/TASK-002.md"
        second_card.write_text(
            second_card.read_text(encoding="utf-8").replace("src/**", "src/two.py"),
            encoding="utf-8",
        )
        (source_dir / "two.py").write_text("TWO = 2\n", encoding="utf-8")
        self.write_valid_report("TASK-002", "src/two.py")
        qa2 = self.write_valid_qa("TASK-002", "QA-002")
        verdict2 = self.write_valid_verdict("TASK-002", "V-002")
        passed2 = self.run_loop(
            "verdict",
            "TASK-002",
            "pass",
            "--file",
            str(verdict2.relative_to(self.project)),
            "--qa",
            str(qa2.relative_to(self.project)),
        )
        self.assertEqual(passed2.returncode, 0, passed2.stdout + passed2.stderr)

        g2 = self.run_loop("gate", "g2", "--pass")
        self.assertEqual(g2.returncode, 0, g2.stdout + g2.stderr)
        dod = self.project / "loop-project/0-plan/dod.md"
        state = self.read_state()
        state["dod_hash"] = hashlib.sha256(dod.read_bytes()).hexdigest()
        self.write_state(state)

        result = self.run_loop("gate", "g3", "--pass")

        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertEqual(self.read_state()["status"], "PASS")

    def test_migrate_audits_a_baseline_for_pre_hardening_tasks(self):
        self.enable_build_phase()
        self.init_git_baseline()
        task = self.run_loop("task", "new", "Legacy task")
        self.assertEqual(task.returncode, 0, task.stderr)
        state = self.read_state()
        state["tasks"]["TASK-001"].pop("base_sha")
        state.pop("frozen_roles", None)
        self.write_state(state)

        result = self.run_loop(
            "migrate",
            "--by",
            "Test Human",
            "--reason",
            "Accept the current checkout as the legacy task boundary.",
        )

        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        state = self.read_state()
        self.assertTrue(state["tasks"]["TASK-001"]["base_sha"])
        self.assertTrue(state["migrations"])

    def test_blocked_verdict_stops_loop_until_human_unblocks_it(self):
        self.enable_build_phase()
        task = self.run_loop("task", "new", "Contradictory task")
        self.assertEqual(task.returncode, 0, task.stderr)
        verdict_path = self.write_valid_blocked_verdict()
        state = self.read_state()
        state["phase"] = 3
        state["gates"]["g2"] = {"passed": True, "at": "2026-07-28T00:02:00Z"}
        self.write_state(state)

        blocked = self.run_loop(
            "verdict",
            "TASK-001",
            "blocked",
            "--file",
            str(verdict_path.relative_to(self.project)),
            "--reason",
            "The frozen requirements contradict each other.",
        )

        self.assertEqual(blocked.returncode, 0, blocked.stdout + blocked.stderr)
        state = self.read_state()
        self.assertEqual(state["status"], "BLOCKED")
        self.assertEqual(state["tasks"]["TASK-001"]["verdict"], "BLOCKED")

        resumed = self.run_loop(
            "unblock",
            "--by",
            "Test Human",
            "--decision",
            "Keep FR-001 and remove the conflicting non-goal.",
        )

        self.assertEqual(resumed.returncode, 0, resumed.stdout + resumed.stderr)
        state = self.read_state()
        self.assertEqual(state["status"], "ACTIVE")
        self.assertIsNone(state["blocked_reason"])
        self.assertEqual(state["unblocks"][-1]["by"], "Test Human")


class LoopInternalTest(unittest.TestCase):
    def test_content_normalisation_does_not_erase_everything_after_line_comment(self):
        first = LOOP_MODULE.normalise_content("// context\nconst value = 1;\n")
        second = LOOP_MODULE.normalise_content("// context\nconst value = 2;\n")

        self.assertNotEqual(first, second)

    def test_changed_files_preserves_hostile_git_filenames(self):
        with tempfile.TemporaryDirectory(prefix="project-loop-git-path-") as directory:
            project = Path(directory)

            def git(*args):
                return subprocess.run(
                    ["git", *args],
                    cwd=project,
                    capture_output=True,
                    text=True,
                    check=False,
                )

            self.assertEqual(git("init", "-q").returncode, 0)
            (project / "README.md").write_text("# Fixture\n", encoding="utf-8")
            self.assertEqual(git("add", "README.md").returncode, 0)
            committed = git(
                "-c",
                "user.name=Project Loop Test",
                "-c",
                "user.email=test@example.invalid",
                "commit",
                "-qm",
                "baseline",
            )
            self.assertEqual(committed.returncode, 0, committed.stderr)
            baseline = git("rev-parse", "HEAD").stdout.strip()
            hostile = "src/weird -> name\nfile.py"
            (project / "src").mkdir()
            (project / hostile).write_text("VALUE = 1\n", encoding="utf-8")

            previous = os.getcwd()
            os.chdir(project)
            try:
                files = LOOP_MODULE.changed_files(baseline)
            finally:
                os.chdir(previous)

            self.assertIn(hostile, files)

    def test_git_history_secret_scan_finds_a_deleted_token(self):
        with tempfile.TemporaryDirectory(prefix="project-loop-history-") as directory:
            project = Path(directory)

            def git(*args):
                return subprocess.run(
                    ["git", *args],
                    cwd=project,
                    capture_output=True,
                    text=True,
                    check=False,
                )

            self.assertEqual(git("init", "-q").returncode, 0)
            leaked = project / "leaked.txt"
            leaked.write_text("ghp_" + "A" * 24 + "\n", encoding="utf-8")
            self.assertEqual(git("add", "leaked.txt").returncode, 0)
            commit = git(
                "-c",
                "user.name=Project Loop Test",
                "-c",
                "user.email=test@example.invalid",
                "commit",
                "-qm",
                "accidental secret",
            )
            self.assertEqual(commit.returncode, 0, commit.stderr)
            leaked.unlink()
            self.assertEqual(git("add", "-u").returncode, 0)
            removed = git(
                "-c",
                "user.name=Project Loop Test",
                "-c",
                "user.email=test@example.invalid",
                "commit",
                "-qm",
                "remove secret",
            )
            self.assertEqual(removed.returncode, 0, removed.stderr)

            previous = os.getcwd()
            os.chdir(project)
            try:
                findings = LOOP_MODULE.check_git_history_secrets()
            finally:
                os.chdir(previous)

            self.assertTrue(any("github token" in finding for finding in findings))


if __name__ == "__main__":
    unittest.main()
