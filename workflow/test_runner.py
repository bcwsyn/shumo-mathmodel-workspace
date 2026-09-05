"""Synthetic control-plane tests; these are not scientific gate approvals."""
import contextlib
import io
import json
from pathlib import Path
import tempfile
import unittest

import runner as r


class WorkflowTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.project = self.root / "工程"
        self.source = self.root / "题面.txt"
        self.source.write_text("合成测试输入", encoding="utf-8")
        r.initialize(self.project, "mathmodel", "合成测试", [str(self.source)])

    def write(self, rel, text="synthetic evidence"):
        path = self.project / rel
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(text, encoding="utf-8")

    def fill(self, stage):
        s = next(s for s in r.load(self.project)["stages"] if s["id"] == stage)
        for pattern in s["required"]:
            self.write(pattern.replace("*", "synthetic.txt"))
        if stage == "G6":
            self.write("paper/references.tex")

    def pass_stage(self, gate):
        r.mutate(self.project, "start", gate)
        self.fill(gate)
        r.mutate(self.project, "submit", gate)
        r.mutate(self.project, "approve", gate, note="测试夹具批准，不代表真实用户验收")

    def test_input_copy_and_existing_project_protection(self):
        self.assertEqual(r.digest(self.source), r.digest(self.project / "inputs/题面.txt"))
        with self.assertRaises(r.WorkflowError):
            r.initialize(self.project, "mathmodel", "overwrite", [str(self.source)])
        with self.assertRaises(r.WorkflowError):
            r.initialize(self.root / "no-input", "mathmodel", "x", [])

    def test_gate_order_and_missing_evidence(self):
        with self.assertRaises(r.WorkflowError):
            r.mutate(self.project, "start", "G1")
        r.mutate(self.project, "start", "G0")
        with self.assertRaises(r.WorkflowError):
            r.mutate(self.project, "submit", "G0")
        self.assertEqual(r.current(r.load(self.project))["status"], "running")

    def test_wait_requires_decision_and_blocks_next(self):
        r.mutate(self.project, "start", "G0")
        self.fill("G0")
        r.mutate(self.project, "submit", "G0")
        for action, stage in [("start", "G1"), ("approve", "G0")]:
            with self.assertRaises(r.WorkflowError):
                r.mutate(self.project, action, stage)

    def test_changed_waiting_evidence_cannot_be_approved(self):
        r.mutate(self.project, "start", "G0")
        self.fill("G0")
        r.mutate(self.project, "submit", "G0")
        self.write("reports/G0_INPUT_REVIEW.md", "edited")
        with self.assertRaises(r.WorkflowError):
            r.mutate(self.project, "approve", "G0", note="批准")
        r.mutate(self.project, "reject", "G0", note="复核编辑")
        r.mutate(self.project, "submit", "G0")
        r.mutate(self.project, "approve", "G0", note="批准新版本")

    def test_input_change_addition_and_reopen(self):
        self.pass_stage("G0")
        self.write("inputs/new.txt")
        self.assertTrue(r.stale(self.project, r.load(self.project)))
        with self.assertRaises(r.WorkflowError):
            r.mutate(self.project, "start", "G1")
        r.mutate(self.project, "reopen", "G0", note="新增附件重新分析")
        state = r.load(self.project)
        self.assertEqual(state["stages"][0]["status"], "pending")
        self.assertEqual(len(state["input_history"]), 1)
        self.assertIn("inputs/new.txt", state["inputs"])

    def test_reopen_invalidates_downstream_preserving_history(self):
        self.pass_stage("G0")
        self.pass_stage("G1")
        r.mutate(self.project, "reopen", "G0", note="题意修正")
        state = r.load(self.project)
        self.assertTrue(all(s["status"] == "pending" for s in state["stages"]))
        self.assertTrue(state["stages"][1]["history"])

    def test_pause_fail_resume_retains_executor(self):
        r.mutate(self.project, "start", "G0", executor="fixture-worker")
        r.mutate(self.project, "pause", "G0", note="测试中断")
        r.mutate(self.project, "resume", "G0")
        r.mutate(self.project, "fail", "G0", note="测试异常")
        result = r.mutate(self.project, "resume", "G0")
        self.assertEqual(result["next"]["executor"], "fixture-worker")
        self.assertEqual(result["next"]["status"], "running")

    def test_lock_is_not_removed_by_competitor(self):
        lock = self.project / "workflow/state.lock"
        lock.write_text("held", encoding="utf-8")
        with self.assertRaises(r.WorkflowError):
            r.mutate(self.project, "start", "G0")
        self.assertEqual(lock.read_text(), "held")

    def test_outside_path_and_state_evidence_rejected(self):
        r.mutate(self.project, "start", "G0")
        self.fill("G0")
        for relative in ["../题面.txt", str(self.source), "workflow/state.json", "inputs/题面.txt"]:
            with self.assertRaises(r.WorkflowError):
                r.mutate(self.project, "submit", "G0", evidence=[relative])

    def test_only_g4_can_skip(self):
        with self.assertRaises(r.WorkflowError):
            r.mutate(self.project, "skip", "G0", note="skip")
        for gate in ("G0", "G1", "G2", "G3"):
            self.pass_stage(gate)
        r.mutate(self.project, "skip", "G4", note="用户批准跳过 G4")
        self.assertEqual(r.current(r.load(self.project))["id"], "G5")

    def test_source_dependencies_and_shared_artifact_review(self):
        for gate in ("G0", "G1"):
            self.pass_stage(gate)
        self.write("code/helpers/model.py", "version one")
        self.pass_stage("G2")
        r.mutate(self.project, "start", "G3")
        self.write("code/helpers/model.py", "version two")
        self.fill("G3")
        r.mutate(self.project, "submit", "G3")
        r.mutate(self.project, "approve", "G3", note="正式实验覆盖新源码")
        self.assertFalse(r.stale(self.project, r.load(self.project)))
        self.write("code/helpers/model.py", "unreviewed")
        with self.assertRaises(r.WorkflowError):
            r.mutate(self.project, "start", "G4")

    def test_bundle_requires_gates_and_checks_hashes(self):
        with self.assertRaises(r.WorkflowError):
            r.bundle(self.project, self.root / "early")
        for gate in [f"G{i}" for i in range(8)] + ["Final"]:
            self.pass_stage(gate)
        destination = self.root / "bundle"
        result = r.bundle(self.project, destination)
        self.assertEqual(result["status"], "BUNDLED")
        receipt = json.loads((destination / "bundle.json").read_text(encoding="utf-8"))
        for relative, sha in receipt["files"].items():
            self.assertEqual(r.digest(destination / relative), sha)
        with self.assertRaises(r.WorkflowError):
            r.bundle(self.project, destination)
        (self.project / "paper/build/final.pdf").unlink()
        with self.assertRaises(r.WorkflowError):
            r.bundle(self.project, self.root / "broken")

    def test_cli_errors_and_readonly_next(self):
        before = r.digest(self.project / "workflow/state.json")
        with contextlib.redirect_stdout(io.StringIO()), contextlib.redirect_stderr(io.StringIO()):
            self.assertEqual(r.main(["next", "--project", str(self.project)]), 0)
            self.assertEqual(r.main(["start", "--project", str(self.project), "--stage", "G1"]), 2)
            self.assertEqual(r.main(["templates"]), 0)
        self.assertEqual(before, r.digest(self.project / "workflow/state.json"))

    def test_conflicted_state_is_not_rebuilt(self):
        state = self.project / "workflow/state.json"
        state.write_text("<<<<<<< main\n", encoding="utf-8")
        with self.assertRaises(r.WorkflowError):
            r.load(self.project)


if __name__ == "__main__":
    unittest.main()
