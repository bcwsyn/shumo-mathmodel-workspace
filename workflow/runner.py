"""File-based checkpoints for Codex; no model calls or experiment execution."""
from __future__ import annotations

import argparse
from contextlib import contextmanager
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import shutil
import sys
import tempfile

TEMPLATES = Path(__file__).resolve().parent / "templates"
DONE = {"approved", "skipped"}


class WorkflowError(Exception):
    pass


def now():
    return datetime.now(timezone.utc).isoformat()


def digest(path):
    with path.open("rb") as stream:
        return hashlib.file_digest(stream, "sha256").hexdigest()


def read_json(path):
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError) as exc:
        raise WorkflowError(f"无法读取 JSON：{path}: {exc}") from exc


def file_at(project, relative):
    rel = Path(relative)
    if rel.is_absolute() or ".." in rel.parts or not rel.parts:
        raise WorkflowError(f"需要项目内相对路径：{relative}")
    candidate = project / rel
    # Reject symlinks/junctions even when their destination is inside the project.
    for part in [candidate, *candidate.parents]:
        if part == project:
            break
        if part.is_symlink() or (hasattr(part, "is_junction") and part.is_junction()):
            raise WorkflowError(f"不能登记链接路径：{relative}")
    if not candidate.resolve().is_relative_to(project.resolve()):
        raise WorkflowError(f"路径越出项目：{relative}")
    return candidate


def snapshot(project, paths):
    result = {}
    for relative in sorted(set(paths)):
        path = file_at(project, relative)
        if not path.is_file() or path.stat().st_size == 0:
            raise WorkflowError(f"文件缺失或为空：{relative}")
        result[Path(relative).as_posix()] = digest(path)
    return result


def load(project):
    state = read_json(project / "workflow/state.json")
    if not isinstance(state, dict) or state.get("schema") != 1 or not state.get("stages"):
        raise WorkflowError("未知或不完整状态文件；不能自动重建")
    expected = [f"G{i}" for i in range(8)] + ["Final"]
    if [s["id"] for s in state["stages"]] != expected:
        raise WorkflowError("阶段顺序异常；检查状态文件或 Git 冲突")
    pending_seen = False
    for stage in state["stages"]:
        if stage["status"] not in DONE | {"pending", "running", "paused", "failed", "waiting"}:
            raise WorkflowError("未知阶段状态")
        if pending_seen and stage["status"] != "pending":
            raise WorkflowError("状态顺序不一致；检查并行修改或 Git 冲突")
        if stage["status"] not in DONE:
            pending_seen = True
    return state


def save(project, state):
    target = project / "workflow/state.json"
    fd, name = tempfile.mkstemp(prefix="state-", suffix=".tmp", dir=target.parent)
    try:
        with os.fdopen(fd, "w", encoding="utf-8", newline="\n") as stream:
            json.dump(state, stream, ensure_ascii=False, indent=2)
            stream.write("\n")
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(name, target)
    finally:
        if os.path.exists(name):
            os.unlink(name)


@contextmanager
def locked(project):
    path = project / "workflow/state.lock"
    try:
        stream = path.open("x", encoding="utf-8")
    except FileExistsError as exc:
        raise WorkflowError("状态锁存在；检查持有者，不自动删锁") from exc
    try:
        with stream:
            stream.write(f"pid={os.getpid()} time={now()}\n")
            stream.flush()
            yield
    finally:
        path.unlink()


def event(state, action, stage=None, detail=""):
    state["revision"] += 1
    state["events"].append({"revision": state["revision"], "time": now(),
                            "action": action, "stage": stage, "detail": detail})


def current(state):
    return next((s for s in state["stages"] if s["status"] not in DONE), None)


def changed(project, records):
    issues = []
    for relative, sha in records.items():
        path = file_at(project, relative)
        if not path.is_file() or digest(path) != sha:
            issues.append(relative)
    return issues


def stale(project, state):
    # A later approved stage may legitimately supersede a shared source file.
    # Validate the latest reviewed version, retaining older fingerprints in history.
    records = {p: (sha, "G0") for p, sha in state["inputs"].items()}
    for stage in state["stages"]:
        if stage["status"] in DONE or stage["status"] == "waiting":
            for p, sha in stage["evidence"].items():
                records[p] = (sha, stage["id"])
    actual_inputs = {p.relative_to(project).as_posix() for p in (project / "inputs").rglob("*") if p.is_file()}
    issues = [{"stage": "G0", "path": p} for p in sorted(actual_inputs - state["inputs"].keys())]
    for p, (sha, gate) in records.items():
        if changed(project, {p: sha}):
            issues.append({"stage": gate, "path": p})
    return issues


def required_files(project, stage):
    paths = []
    for pattern in stage["required"]:
        matches = sorted(p for p in project.glob(pattern) if p.is_file())
        if not matches:
            raise WorkflowError(f"{stage['id']} 缺少必需产物：{pattern}")
        paths.extend(p.relative_to(project).as_posix() for p in matches)
    if stage["id"] == "G6":
        refs = list((project / "paper").glob("*.bib"))
        if (project / "paper/references.tex").is_file():
            refs.append(project / "paper/references.tex")
        if not refs:
            raise WorkflowError("G6 缺少 references.tex 或 .bib 参考文献源")
        paths.extend(p.relative_to(project).as_posix() for p in refs)
    # Collect editable source dependencies, not only the top-level entry point.
    scopes = {
        "G2": {"code": {".py", ".json"}, "tests": {".py"}},
        "G3": {"code": {".py", ".json"}, "tests": {".py"}},
        "G6": {"paper": {".tex", ".bib", ".cls", ".sty"}},
    }
    for directory, suffixes in scopes.get(stage["id"], {}).items():
        paths.extend(p.relative_to(project).as_posix() for p in (project / directory).rglob("*")
                     if p.is_file() and p.suffix in suffixes and "__pycache__" not in p.parts)
    return paths


def initialize(project, template_id, title, inputs):
    if template_id not in {p.stem for p in TEMPLATES.glob("*.json")}:
        raise WorkflowError(f"未知模板：{template_id}")
    template = read_json(TEMPLATES / f"{template_id}.json")
    sources = [Path(p).resolve() for p in inputs]
    if not sources or any(not p.is_file() or p.stat().st_size == 0 for p in sources):
        raise WorkflowError("必须提供至少一个实际非空输入文件")
    if len({p.name.casefold() for p in sources}) != len(sources):
        raise WorkflowError("输入文件同名，请先区分名称")
    if project.exists():
        raise WorkflowError("目标目录已存在；不覆盖或自动接管旧项目")
    project.mkdir(parents=True)
    for name in ("inputs", "reports", "code", "tests", "logs", "results", "figures", "paper", "workflow"):
        (project / name).mkdir()
    for source in sources:
        shutil.copy2(source, project / "inputs" / source.name)
    state = {"schema": 1, "title": title, "template": template["id"],
             "template_version": template["version"], "revision": 0, "events": [],
             "inputs": snapshot(project, [f"inputs/{p.name}" for p in sources]),
             "stages": [{**s, "status": "pending", "evidence": {}, "history": []}
                        for s in template["stages"]]}
    for source in sources:
        if digest(source) != state["inputs"][f"inputs/{source.name}"]:
            raise WorkflowError("复制期间输入变化；保留新目录供检查")
    event(state, "init", detail=title)
    save(project, state)
    (project / "README.md").write_text(f"# {title}\n\n使用团队总仓库的 workflow/runner.py status/next 查看阶段。\n", encoding="utf-8")
    (project / "plan.md").write_text("# 项目方案\n\n新项目使用 XeLaTeX；逐阶段审批。\n审批唯一记录：workflow/state.json（通过 status 查看）。\n科研方案由当前阶段技能补充。\n", encoding="utf-8")
    (project / "todo.md").write_text("# 科研待办\n\n阶段执行和批准状态以 workflow/state.json 为准。\n此处记录具体科研任务，避免复制第二份审批表。\n", encoding="utf-8")
    return view(project, state)


def view(project, state):
    stage = current(state)
    return {"title": state["title"], "revision": state["revision"],
            "complete": stage is None, "stale": stale(project, state),
            "stages": [{"id": s["id"], "name": s["name"], "status": s["status"]} for s in state["stages"]],
            "next": None if stage is None else {
                "id": stage["id"], "status": stage["status"], "skills": stage["skills"],
                "required": stage["required"], "executor": stage.get("executor", "unknown"),
                "evidence": stage["evidence"],
                "instruction": "读取对应 SKILL.md 执行当前阶段；提交证据后等待真实用户批准。"
            }}


def mutate(project, action, stage_id=None, evidence=(), note="", executor="unknown"):
    with locked(project):
        state = load(project)
        stage = next((s for s in state["stages"] if s["id"] == stage_id), None)
        if stage is None:
            raise WorkflowError("需要有效阶段 ID")
        if action == "reopen":
            if not note.strip():
                raise WorkflowError("重新打开需要原因")
            idx = state["stages"].index(stage)
            first = current(state)
            if first and idx > state["stages"].index(first):
                raise WorkflowError("不能重开尚未进入的下游阶段")
            for item in state["stages"][idx:]:
                item["history"].append({k: v for k, v in item.items() if k != "history"})
                item.update(status="pending", evidence={})
                item.pop("decision", None)
            # Input changes must be reviewed again at G0; archive the old fingerprint.
            if idx == 0:
                state.setdefault("input_history", []).append(state["inputs"])
                state["inputs"] = snapshot(project, [p.relative_to(project).as_posix()
                                                       for p in (project / "inputs").rglob("*") if p.is_file()])
                if not state["inputs"]:
                    raise WorkflowError("输入不可为空")
        else:
            if stage != current(state):
                raise WorkflowError("只能操作当前阶段，不能跳过前置审批")
            issues = stale(project, state)
            # During work, allow updates to shared artifacts only when this stage
            # will explicitly register the replacement version in its submission.
            replacing = {Path(p).as_posix() for p in evidence}
            if action == "submit":
                replacing.update(required_files(project, stage))
            remaining = [i for i in issues if not (action == "submit" and
                         i["path"] in replacing and not i["path"].startswith("inputs/"))]
            if remaining and action not in {"reject", "fail", "pause"}:
                raise WorkflowError(f"证据变化，需 reopen 并复核：{remaining}")
            status = stage["status"]
            if action == "start" and status == "pending":
                stage.update(status="running", executor=executor)
            elif action == "resume" and status in {"paused", "failed", "running"}:
                stage["status"] = "running"
            elif action in {"pause", "fail"} and status == "running":
                if not note.strip():
                    raise WorkflowError("暂停/失败需要原因")
                stage["status"] = "paused" if action == "pause" else "failed"
            elif action == "submit" and status == "running":
                paths = required_files(project, stage) + list(evidence)
                if any(Path(p).as_posix().startswith(("inputs/", "workflow/")) for p in paths):
                    raise WorkflowError("输入与状态不能作为可替换阶段产物")
                stage.update(evidence=snapshot(project, paths), status="waiting")
            elif action in {"approve", "reject"} and status == "waiting":
                if not note.strip():
                    raise WorkflowError("需要记录真实用户的批准/修改意见")
                stage["history"].append({"time": now(), "evidence": stage["evidence"],
                                         "action": action, "decision": note})
                stage["status"] = "approved" if action == "approve" else "running"
                stage["decision"] = note
                if action == "reject":
                    stage["evidence"] = {}
            elif action == "skip" and stage_id == "G4" and status in {"pending", "running"}:
                if not note.strip():
                    raise WorkflowError("跳过 G4 需要真实用户批准原文")
                stage.update(status="skipped", decision=note)
            else:
                raise WorkflowError(f"不允许的状态转换：{status} -> {action}")
        event(state, action, stage_id, note)
        save(project, state)
        return view(project, state)


def manifest(project, state):
    issues = stale(project, state)
    if issues:
        raise WorkflowError(f"产物变化：{issues}")
    records = dict(state["inputs"])
    for stage in state["stages"]:
        if stage["status"] in DONE:
            records.update(stage["evidence"])
    return {"schema": 1, "revision": state["revision"], "complete": current(state) is None,
            "files": dict(sorted(records.items()))}


def bundle(project, destination):
    with locked(project):
        state = load(project)
        data = manifest(project, state)
        if not data["complete"]:
            raise WorkflowError("尚未完成所有阶段审批，不能生成交付包")
        if destination.exists() or destination.is_relative_to(project):
            raise WorkflowError("交付目标必须是项目外的新目录")
        destination.mkdir(parents=True)
        # On copy failure the directory remains, without a completion receipt.
        for relative, sha in data["files"].items():
            source = file_at(project, relative)
            target = destination / relative
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(source, target)
            if digest(target) != sha:
                raise WorkflowError(f"归档期间文件变化：{relative}；保留目录供检查")
        (destination / "workflow").mkdir(exist_ok=True)
        shutil.copy2(project / "workflow/state.json", destination / "workflow/state.json")
        data["files"]["workflow/state.json"] = digest(destination / "workflow/state.json")
        (destination / "MANIFEST.md").write_text(
            "# 已登记交付文件 SHA-256\n\n" + "\n".join(f"- `{sha}`  `{p}`" for p, sha in sorted(data["files"].items())) + "\n",
            encoding="utf-8")
        (destination / "bundle.json").write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
        return {"destination": str(destination), "files": len(data["files"]), "status": "BUNDLED"}


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("action", choices=["templates", "init", "status", "next", "start", "submit", "approve", "reject", "pause", "fail", "resume", "reopen", "skip", "manifest", "bundle"])
    parser.add_argument("--project", type=Path)
    parser.add_argument("--template", default="mathmodel")
    parser.add_argument("--title", default="数学建模项目")
    parser.add_argument("--input", action="append", default=[])
    parser.add_argument("--stage")
    parser.add_argument("--evidence", action="append", default=[])
    parser.add_argument("--note", default="")
    parser.add_argument("--executor", default="unknown")
    parser.add_argument("--destination", type=Path)
    args = parser.parse_args(argv)
    try:
        if args.action == "templates":
            result = [read_json(p) for p in sorted(TEMPLATES.glob("*.json"))]
        else:
            if args.project is None:
                raise WorkflowError("需要 --project")
            project = args.project.resolve()
            if args.action == "init":
                result = initialize(project, args.template, args.title, args.input)
            elif args.action in {"status", "next"}:
                result = view(project, load(project))
            elif args.action == "manifest":
                result = manifest(project, load(project))
            elif args.action == "bundle":
                if args.destination is None:
                    raise WorkflowError("需要 --destination")
                result = bundle(project, args.destination.resolve())
            else:
                result = mutate(project, args.action, args.stage, args.evidence, args.note, args.executor)
        print(json.dumps(result, ensure_ascii=False, indent=2))
        return 0
    except (WorkflowError, OSError, ValueError, KeyError, TypeError) as exc:
        print(json.dumps({"error": str(exc)}, ensure_ascii=False), file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
