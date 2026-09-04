from __future__ import annotations

import argparse
import ast
import hashlib
import importlib.util
import json
import os
import platform
import re
import shutil
import subprocess
import sys
import time
import tokenize
from pathlib import Path
from typing import Any


STAGES = {"preflight", "g2", "g3", "final"}
RANK = {"VERIFIED": 0, "UNVERIFIED": 1, "FAILED": 2}


def arguments() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Audit generated Python code with runtime evidence.")
    parser.add_argument("--root", default=".")
    parser.add_argument("--stage", choices=sorted(STAGES), default="g2")
    parser.add_argument("--python", dest="python_path")
    parser.add_argument("--code-dir", default="code")
    parser.add_argument("--manifest", default="code/audit_manifest.json")
    parser.add_argument("--output")
    return parser.parse_args()


def read_json(path: Path) -> dict[str, Any]:
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError:
        return {}
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise ValueError(f"invalid JSON {path}: {exc}") from exc
    if not isinstance(data, dict):
        raise ValueError(f"JSON root must be an object: {path}")
    return data


def project_path(root: Path, value: str) -> Path:
    path = (root / value).resolve()
    try:
        path.relative_to(root)
    except ValueError as exc:
        raise ValueError(f"path escapes project root: {value}") from exc
    return path


def find_python(root: Path, explicit: str | None) -> tuple[Path | None, str]:
    candidates: list[tuple[str, str | None]] = [
        ("--python", explicit),
        ("MATHMODEL_PYTHON", os.environ.get("MATHMODEL_PYTHON")),
    ]
    runtime = root / ".codex" / "runtime.local.json"
    if runtime.is_file():
        try:
            candidates.append((str(runtime), str(read_json(runtime).get("python") or "")))
        except ValueError:
            candidates.append((str(runtime), None))
    candidates.extend(
        [
            ("workspace .venv", str(root / ".venv" / "Scripts" / "python.exe")),
            ("workspace .venv", str(root / ".venv" / "bin" / "python")),
        ]
    )
    for source, value in candidates:
        if value and Path(value).expanduser().is_file():
            return Path(value).expanduser().resolve(), source
    fallback = shutil.which("python") or shutil.which("python3")
    return (Path(fallback).resolve(), "PATH candidate") if fallback else (None, "not found")


def execute(command: list[str], cwd: Path, timeout: int = 120) -> dict[str, Any]:
    started = time.time()
    try:
        result = subprocess.run(
            command,
            cwd=cwd,
            shell=False,
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            timeout=timeout,
        )
        return {
            "command": command,
            "exit_code": result.returncode,
            "duration_seconds": round(time.time() - started, 3),
            "stdout": result.stdout,
            "stderr": result.stderr,
        }
    except subprocess.TimeoutExpired as exc:
        return {
            "command": command,
            "exit_code": None,
            "duration_seconds": round(time.time() - started, 3),
            "stdout": exc.stdout or "",
            "stderr": (exc.stderr or "") + f"\nTIMEOUT after {timeout}s",
        }
    except OSError as exc:
        return {
            "command": command,
            "exit_code": None,
            "duration_seconds": round(time.time() - started, 3),
            "stdout": "",
            "stderr": str(exc),
        }


def file_hash(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def worst(items: list[dict[str, Any]]) -> str:
    status = "VERIFIED"
    for item in items:
        candidate = str(item.get("status", "VERIFIED"))
        if RANK.get(candidate, 1) > RANK[status]:
            status = candidate
    return status


class CodeScanner(ast.NodeVisitor):
    def __init__(self, filename: str, stage: str) -> None:
        self.filename = filename
        self.stage = stage
        self.imports: set[str] = set()
        self.findings: list[dict[str, Any]] = []

    def add(self, node: ast.AST, rule: str, detail: str, status: str = "UNVERIFIED") -> None:
        self.findings.append(
            {
                "file": self.filename,
                "line": getattr(node, "lineno", None),
                "rule": rule,
                "detail": detail,
                "status": status,
            }
        )

    def visit_Import(self, node: ast.Import) -> None:
        self.imports.update(alias.name.split(".")[0] for alias in node.names)
        self.generic_visit(node)

    def visit_ImportFrom(self, node: ast.ImportFrom) -> None:
        if node.module and node.level == 0:
            self.imports.add(node.module.split(".")[0])
        self.generic_visit(node)

    def visit_ExceptHandler(self, node: ast.ExceptHandler) -> None:
        if node.type is None:
            self.add(node, "bare-except", "bare except can hide failures")
        if len(node.body) == 1 and isinstance(node.body[0], ast.Pass):
            self.add(node, "silent-except", "exception is discarded with pass", "FAILED")
        self.generic_visit(node)

    def visit_Call(self, node: ast.Call) -> None:
        if isinstance(node.func, ast.Name) and node.func.id in {"eval", "exec"}:
            self.add(node, "dynamic-execution", f"{node.func.id} requires justification")
        for keyword in node.keywords:
            if keyword.arg == "shell" and isinstance(keyword.value, ast.Constant) and keyword.value.value is True:
                self.add(node, "shell-true", "subprocess shell=True weakens command evidence")
        self.generic_visit(node)

    def visit_Constant(self, node: ast.Constant) -> None:
        if isinstance(node.value, str):
            value = node.value.strip()
            if re.match(r"^[A-Za-z]:[\\/]", value) or value.startswith(("/home/", "/Users/")):
                self.add(node, "absolute-path", value[:160])
        self.generic_visit(node)

    def _visit_function(self, node: ast.FunctionDef | ast.AsyncFunctionDef) -> None:
        if not node.name.startswith("_"):
            args = [*node.args.posonlyargs, *node.args.args, *node.args.kwonlyargs]
            typed = all(arg.annotation is not None for arg in args if arg.arg not in {"self", "cls"})
            if not typed or node.returns is None:
                self.add(node, "maintainability-type-hints", f"公开函数 {node.name} 缺少完整参数或返回值类型标注；请确认它是否属于核心 API")

            docstring = ast.get_docstring(node, clean=False) or ""
            if not docstring.strip():
                self.add(node, "maintainability-api-docstring", f"公开函数 {node.name} 缺少 docstring；核心 API 应使用 Google/NumPy 风格")

        line_count = (getattr(node, "end_lineno", node.lineno) or node.lineno) - node.lineno + 1
        if line_count > 80:
            self.add(node, "maintainability-function-length", f"函数 {node.name} 长度为 {line_count} 行，超过 80 行且需给出特殊理由", "FAILED")
        elif line_count > 50:
            self.add(node, "maintainability-function-length", f"函数 {node.name} 长度为 {line_count} 行，超过 50 行，建议拆分或记录算法连续性理由")

        parameter_count = len(node.args.posonlyargs) + len(node.args.args) + len(node.args.kwonlyargs)
        if parameter_count > 8:
            self.add(node, "maintainability-parameter-count", f"函数 {node.name} 有 {parameter_count} 个参数，建议使用配置对象或拆分")

        branch_nodes = (ast.If, ast.For, ast.AsyncFor, ast.While, ast.Try, ast.With, ast.AsyncWith, ast.IfExp, ast.BoolOp, ast.Match)
        complexity = 1 + sum(1 for item in ast.walk(node) if isinstance(item, branch_nodes))
        if complexity > 15:
            self.add(node, "maintainability-complexity", f"函数 {node.name} 估算圈复杂度为 {complexity}，超过 15")
        self.generic_visit(node)

    def visit_FunctionDef(self, node: ast.FunctionDef) -> None:
        self._visit_function(node)

    def visit_AsyncFunctionDef(self, node: ast.AsyncFunctionDef) -> None:
        self._visit_function(node)


def scan(root: Path, code_dir: Path, stage: str) -> tuple[list[dict[str, Any]], set[str], list[dict[str, Any]]]:
    files: list[dict[str, Any]] = []
    imports: set[str] = set()
    findings: list[dict[str, Any]] = []
    if not code_dir.is_dir():
        return files, imports, findings
    for path in sorted(code_dir.rglob("*.py")):
        relative = str(path.relative_to(root))
        try:
            text = path.read_text(encoding="utf-8")
            tree = ast.parse(text, filename=relative)
            scanner = CodeScanner(relative, stage)
            scanner.visit(tree)
            imports.update(scanner.imports)
            findings.extend(scanner.findings)
            module_docstring = ast.get_docstring(tree, clean=False) or ""
            if not module_docstring.strip():
                findings.append(
                    {
                        "file": relative,
                        "line": 1,
                        "rule": "maintainability-module-docstring",
                        "detail": "模块缺少说明用途、输入和输出的文档字符串",
                        "status": "UNVERIFIED",
                    }
                )
            effective_lines = [line for line in text.splitlines() if line.strip() and not line.lstrip().startswith("#")]
            try:
                comments = [token.string for token in tokenize.generate_tokens(iter(text.splitlines(True)).__next__) if token.type == tokenize.COMMENT]
            except (IndentationError, tokenize.TokenError):
                comments = []
            if len(effective_lines) > 40 and not comments:
                findings.append(
                    {
                        "file": relative,
                        "line": 1,
                        "rule": "maintainability-design-comments",
                        "detail": "超过 40 个有效行但未发现解释公式、约束、单位或设计理由的注释",
                        "status": "UNVERIFIED",
                    }
                )
            for number, line in enumerate(text.splitlines(), 1):
                if re.search(r"\b(TODO|TBD|PLACEHOLDER|NotImplementedError)\b", line, re.I):
                    findings.append(
                        {"file": relative, "line": number, "rule": "placeholder", "detail": line.strip()[:160], "status": "FAILED"}
                    )
                if re.search(r"\b(mock|dummy|synthetic|模拟数据|随机生成数据)\b", line, re.I):
                    findings.append(
                        {"file": relative, "line": number, "rule": "simulated-data", "detail": line.strip()[:160], "status": "UNVERIFIED"}
                    )
            files.append({"path": relative, "status": "VERIFIED", "sha256": file_hash(path)})
        except (OSError, UnicodeDecodeError, SyntaxError) as exc:
            files.append({"path": relative, "status": "FAILED", "reason": str(exc)})
    return files, imports, findings


def module_available(python: Path, root: Path, name: str) -> tuple[bool, dict[str, Any]]:
    code = (
        "import importlib.util,json;"
        f"s=importlib.util.find_spec({name!r});"
        "print(json.dumps({'found':bool(s),'origin':getattr(s,'origin',None)},ensure_ascii=False))"
    )
    evidence = execute([str(python), "-c", code], root, 30)
    payload: dict[str, Any] = {}
    if evidence["exit_code"] == 0:
        try:
            payload = json.loads(evidence["stdout"].strip())
        except json.JSONDecodeError:
            pass
    return bool(payload.get("found")), {"probe": evidence, **payload}


def quality_tools(python: Path, root: Path, code_dir: Path, stage: str) -> list[dict[str, Any]]:
    if stage == "preflight":
        return [{"tool": "quality-gate", "status": "VERIFIED", "reason": "preflight does not require project code"}]

    checks: list[dict[str, Any]] = []
    tests_dir = root / "tests"
    targets = [str(code_dir.relative_to(root))]
    if tests_dir.is_dir():
        targets.append(str(tests_dir.relative_to(root)))

    ruff_found, ruff_probe = module_available(python, root, "ruff")
    if ruff_found:
        result = execute([str(python), "-m", "ruff", "check", *targets], root, 300)
        checks.append({"tool": "ruff", "status": "VERIFIED" if result["exit_code"] == 0 else "FAILED", **result})
    else:
        checks.append({"tool": "ruff", "status": "UNVERIFIED", "reason": "ruff is not installed in the selected interpreter", "probe": ruff_probe})

    pytest_found, pytest_probe = module_available(python, root, "pytest")
    test_files = sorted(tests_dir.rglob("test_*.py")) if tests_dir.is_dir() else []
    if not test_files:
        checks.append({"tool": "pytest", "status": "FAILED", "reason": "tests/test_*.py not found"})
    elif pytest_found:
        result = execute([str(python), "-m", "pytest", "-q", str(tests_dir.relative_to(root))], root, 600)
        checks.append({"tool": "pytest", "status": "VERIFIED" if result["exit_code"] == 0 else "FAILED", **result})
    else:
        checks.append({"tool": "pytest", "status": "UNVERIFIED", "reason": "pytest is not installed in the selected interpreter", "probe": pytest_probe})

    boundary_text = "\n".join(path.read_text(encoding="utf-8", errors="ignore") for path in test_files).lower()
    categories = {
        "normal": ["smoke", "baseline", "valid", "normal", "正常", "基线"],
        "boundary": ["empty", "missing", "nan", "zero", "negative", "extreme", "boundary", "shape", "single", "duplicate", "空", "缺失", "零", "负", "极端", "边界", "形状", "重复"],
        "failure": ["invalid", "error", "raises", "fail", "infeasible", "异常", "错误", "不可行"],
    }
    detected = {name: [word for word in words if word in boundary_text] for name, words in categories.items()}
    checks.append(
        {
            "tool": "boundary-test-evidence",
            "status": "VERIFIED" if test_files and all(detected.values()) else "UNVERIFIED",
            "test_files": [str(path.relative_to(root)) for path in test_files],
            "detected_categories": detected,
            "reason": "keyword scan is supporting evidence; review assertions and independence manually",
        }
    )
    return checks


def check_imports(python: Path, root: Path, names: set[str], local: set[str]) -> list[dict[str, Any]]:
    checks: list[dict[str, Any]] = []
    for name in sorted(names):
        if name in sys.stdlib_module_names or name in local:
            checks.append({"module": name, "status": "VERIFIED", "source": "stdlib/local"})
            continue
        code = (
            "import importlib.util,json;"
            f"s=importlib.util.find_spec({name!r});"
            "print(json.dumps({'found':bool(s),'origin':getattr(s,'origin',None)},ensure_ascii=False))"
        )
        result = execute([str(python), "-c", code], root, 30)
        payload: dict[str, Any] = {}
        if result["exit_code"] == 0:
            try:
                payload = json.loads(result["stdout"].strip())
            except json.JSONDecodeError:
                pass
        checks.append(
            {
                "module": name,
                "status": "VERIFIED" if payload.get("found") else "FAILED",
                "origin": payload.get("origin"),
                "probe_exit_code": result["exit_code"],
                "probe_stderr": result["stderr"].strip(),
            }
        )
    return checks


def artifact(root: Path, value: str) -> dict[str, Any]:
    try:
        path = project_path(root, value)
    except ValueError as exc:
        return {"path": value, "status": "FAILED", "reason": str(exc)}
    if not path.is_file():
        return {"path": value, "status": "FAILED", "reason": "missing file"}
    stat = path.stat()
    return {
        "path": value,
        "status": "VERIFIED",
        "size_bytes": stat.st_size,
        "modified_unix": stat.st_mtime,
        "sha256": file_hash(path),
    }


def main() -> int:
    args = arguments()
    root = Path(args.root).resolve()
    output = project_path(root, args.output or f"reports/code-audit/{args.stage}/audit.json")
    output.parent.mkdir(parents=True, exist_ok=True)
    report: dict[str, Any] = {
        "schema_version": 1,
        "stage": args.stage,
        "generated_unix": time.time(),
        "project_root": str(root),
        "status": "UNVERIFIED",
        "checks": [],
    }

    python, source = find_python(root, args.python_path)
    if python is None:
        report["checks"].append({"check": "python-runtime", "status": "FAILED", "reason": source})
        report["status"] = "FAILED"
        output.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
        print(f"FAILED: {output}")
        return 1

    probe_code = (
        "import json,platform,sys;"
        "print(json.dumps({'executable':sys.executable,'version':sys.version,'platform':platform.platform()},ensure_ascii=False))"
    )
    probe = execute([str(python), "-c", probe_code], root, 30)
    runtime: dict[str, Any] = {
        "check": "python-runtime",
        "status": "VERIFIED" if probe["exit_code"] == 0 else "FAILED",
        "source": source,
        "requested": str(python),
    }
    if probe["exit_code"] == 0:
        try:
            runtime.update(json.loads(probe["stdout"].strip()))
        except json.JSONDecodeError:
            runtime.update({"status": "FAILED", "reason": "probe did not return JSON"})
    else:
        runtime["reason"] = probe["stderr"].strip()
    report["checks"].append(runtime)

    code_dir = project_path(root, args.code_dir)
    files, imports, findings = scan(root, code_dir, args.stage)
    file_status = worst(files)
    if args.stage != "preflight" and not files:
        file_status = "FAILED"
    report["checks"].append({"check": "python-files", "status": file_status, "files": files})

    local = {path.stem for path in code_dir.glob("*.py")} if code_dir.is_dir() else set()
    if code_dir.is_dir():
        local.update(path.name for path in code_dir.iterdir() if path.is_dir())
    import_checks = check_imports(python, root, imports, local)
    report["checks"].append({"check": "imports", "status": worst(import_checks), "modules": import_checks})
    report["checks"].append({"check": "static-risks", "status": worst(findings), "findings": findings})
    quality_checks = quality_tools(python, root, code_dir, args.stage)
    report["checks"].append({"check": "code-quality", "status": worst(quality_checks), "tools": quality_checks})

    manifest_path = project_path(root, args.manifest)
    try:
        manifest = read_json(manifest_path)
        manifest_error = None
    except ValueError as exc:
        manifest = {}
        manifest_error = str(exc)

    runs: list[dict[str, Any]] = []
    if args.stage != "preflight":
        if manifest_error:
            runs.append({"status": "FAILED", "reason": manifest_error})
        elif not manifest:
            runs.append({"status": "UNVERIFIED", "reason": f"missing manifest: {args.manifest}"})
        else:
            seen: set[str] = set()
            for entry in manifest.get("entries", []):
                if not isinstance(entry, dict) or args.stage not in entry.get("stages", []):
                    continue
                name = str(entry.get("name") or "")
                if not name or name in seen:
                    runs.append({"name": name, "status": "FAILED", "reason": "empty or duplicate name"})
                    continue
                seen.add(name)
                try:
                    script = project_path(root, str(entry["script"]))
                    entry_args = entry.get("args", [])
                    if not isinstance(entry_args, list) or not all(isinstance(value, str) for value in entry_args):
                        raise ValueError("args must be a string array")
                    timeout = int(entry.get("timeout_seconds", 120))
                    if timeout < 1 or timeout > 86400:
                        raise ValueError("timeout_seconds must be between 1 and 86400")
                    evidence = execute([str(python), str(script), *entry_args], root, timeout)
                    log_dir = output.parent / "logs"
                    log_dir.mkdir(parents=True, exist_ok=True)
                    (log_dir / f"{name}.stdout.log").write_text(evidence["stdout"], encoding="utf-8")
                    (log_dir / f"{name}.stderr.log").write_text(evidence["stderr"], encoding="utf-8")
                    artifacts = [artifact(root, str(value)) for value in entry.get("expected_artifacts", [])]
                    status = "VERIFIED" if evidence["exit_code"] == 0 and worst(artifacts) == "VERIFIED" else "FAILED"
                    runs.append(
                        {
                            "name": name,
                            "status": status,
                            "command": evidence["command"],
                            "exit_code": evidence["exit_code"],
                            "duration_seconds": evidence["duration_seconds"],
                            "artifacts": artifacts,
                        }
                    )
                except (KeyError, TypeError, ValueError) as exc:
                    runs.append({"name": name, "status": "FAILED", "reason": str(exc)})
            if not runs:
                runs.append({"status": "UNVERIFIED", "reason": f"no manifest entry for stage {args.stage}"})
    report["checks"].append({"check": "runtime-entries", "status": worst(runs), "runs": runs})

    interfaces: list[dict[str, Any]] = []
    for item in manifest.get("interfaces", []) if manifest else []:
        if not isinstance(item, dict):
            interfaces.append({"status": "FAILED", "reason": "interface record must be an object"})
            continue
        status = str(item.get("status", "UNVERIFIED"))
        if status not in RANK or (status == "VERIFIED" and not str(item.get("evidence", "")).strip()):
            status = "FAILED"
        interfaces.append({**item, "status": status})
    report["checks"].append({"check": "external-interfaces", "status": worst(interfaces), "interfaces": interfaces})

    report["status"] = worst(report["checks"])
    output.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"{report['status']}: {output}")
    return {"VERIFIED": 0, "UNVERIFIED": 2, "FAILED": 1}[report["status"]]


if __name__ == "__main__":
    raise SystemExit(main())
