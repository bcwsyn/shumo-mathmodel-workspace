from __future__ import annotations

import argparse
import importlib
import importlib.metadata
import json
import platform
import shutil
import subprocess
import sys
import tempfile
import time
from pathlib import Path
from typing import Any


PACKAGES = {
    "numpy": "numpy",
    "scipy": "scipy",
    "pandas": "pandas",
    "matplotlib": "matplotlib",
    "sklearn": "scikit-learn",
    "openpyxl": "openpyxl",
    "yaml": "PyYAML",
}
TOOLS = {
    "typst": ["typst"],
    "drawio": ["drawio", "draw.io"],
    "pdftoppm": ["pdftoppm"],
    "mutool": ["mutool"],
    "magick": ["magick"],
}
RANK = {"VERIFIED": 0, "UNVERIFIED": 1, "FAILED": 2}


def worst(items: list[dict[str, Any]]) -> str:
    return max((item.get("status", "UNVERIFIED") for item in items), key=RANK.get, default="UNVERIFIED")


def load_runtime(path: Path) -> dict[str, str]:
    if not path.is_file():
        return {}
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeDecodeError, json.JSONDecodeError):
        return {}
    if not isinstance(data, dict):
        return {}
    return {str(key): str(value) for key, value in data.items() if isinstance(value, str)}


def run(command: list[str], timeout: int = 45) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        command,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        timeout=timeout,
        check=False,
    )


def resolve_tool(name: str, commands: list[str], runtime: dict[str, str]) -> tuple[Path | None, str]:
    configured = runtime.get(name)
    if configured:
        path = Path(configured).expanduser()
        return (path.resolve(), "runtime-config") if path.is_file() else (None, "runtime-config-missing")

    resolved = next((Path(value).resolve() for command in commands if (value := shutil.which(command))), None)
    if name == "pdftoppm" and resolved and resolved.suffix.lower() in {".cmd", ".bat"}:
        # Codex bundled runtimes may expose a stale wrapper while the real Poppler
        # executable lives below dependencies/native/poppler/Library/bin.
        for parent in resolved.parents:
            candidate = parent / "native" / "poppler" / "Library" / "bin" / "pdftoppm.exe"
            if candidate.is_file():
                return candidate.resolve(), "PATH-wrapper-recovery"
    return (resolved, "PATH") if resolved else (None, "not-found")


def probe_typst(path: Path) -> dict[str, Any]:
    try:
        version = run([str(path), "--version"], timeout=15)
        with tempfile.TemporaryDirectory(prefix="mathmodel-typst-") as tmp:
            root = Path(tmp)
            source = root / "main.typ"
            output = root / "probe.pdf"
            source.write_text("#set page(width: 80mm, height: 50mm)\n= Typst probe\n$1 + 1 = 2$\n", encoding="utf-8")
            compiled = run([str(path), "compile", str(source), str(output)], timeout=45)
            valid_pdf = output.is_file() and output.stat().st_size > 0 and output.read_bytes().startswith(b"%PDF")
        status = "VERIFIED" if version.returncode == 0 and compiled.returncode == 0 and valid_pdf else "FAILED"
        return {
            "status": status,
            "version": (version.stdout or version.stderr).strip(),
            "probe": "minimal Typst compile and PDF signature",
            "exit_code": compiled.returncode,
            "detail": (compiled.stderr or compiled.stdout).strip()[-500:],
        }
    except (OSError, subprocess.TimeoutExpired) as exc:
        return {"status": "FAILED", "probe": "minimal Typst compile", "detail": str(exc)}


def probe_drawio(path: Path) -> dict[str, Any]:
    xml = """<mxfile host=\"app.diagrams.net\"><diagram id=\"probe\" name=\"Page-1\"><mxGraphModel><root><mxCell id=\"0\"/><mxCell id=\"1\" parent=\"0\"/><mxCell id=\"2\" value=\"probe\" vertex=\"1\" parent=\"1\"><mxGeometry x=\"20\" y=\"20\" width=\"100\" height=\"40\" as=\"geometry\"/></mxCell></root></mxGraphModel></diagram></mxfile>"""
    try:
        with tempfile.TemporaryDirectory(prefix="mathmodel-drawio-") as tmp:
            root = Path(tmp)
            source = root / "probe.drawio"
            output = root / "probe.pdf"
            source.write_text(xml, encoding="utf-8")
            exported = run(
                [str(path), "--export", "--format", "pdf", "--output", str(output), str(source)],
                timeout=60,
            )
            for _ in range(50):
                if output.is_file() and output.stat().st_size > 0:
                    break
                time.sleep(0.1)
            valid_pdf = output.is_file() and output.stat().st_size > 0 and output.read_bytes().startswith(b"%PDF")
        return {
            "status": "VERIFIED" if exported.returncode == 0 and valid_pdf else "FAILED",
            "probe": "minimal DrawIO export and PDF signature",
            "exit_code": exported.returncode,
            "detail": (exported.stderr or exported.stdout).strip()[-500:],
        }
    except (OSError, subprocess.TimeoutExpired) as exc:
        return {"status": "FAILED", "probe": "minimal DrawIO export", "detail": str(exc)}


def probe_pdftoppm(path: Path, typst: Path | None) -> dict[str, Any]:
    if not typst:
        try:
            version = run([str(path), "-v"], timeout=15)
            return {
                "status": "UNVERIFIED" if version.returncode == 0 else "FAILED",
                "probe": "version only; Typst unavailable for conversion probe",
                "exit_code": version.returncode,
                "detail": (version.stderr or version.stdout).strip()[-500:],
            }
        except (OSError, subprocess.TimeoutExpired) as exc:
            return {"status": "FAILED", "probe": "version", "detail": str(exc)}

    try:
        with tempfile.TemporaryDirectory(prefix="mathmodel-poppler-") as tmp:
            root = Path(tmp)
            source = root / "main.typ"
            pdf = root / "input.pdf"
            png_stem = root / "page"
            source.write_text("PDF raster probe", encoding="utf-8")
            built = run([str(typst), "compile", str(source), str(pdf)], timeout=45)
            converted = run(
                [str(path), "-f", "1", "-singlefile", "-png", "-r", "72", str(pdf), str(png_stem)],
                timeout=45,
            )
            png = png_stem.with_suffix(".png")
            valid_png = png.is_file() and png.stat().st_size > 0 and png.read_bytes().startswith(b"\x89PNG")
        return {
            "status": "VERIFIED" if built.returncode == 0 and converted.returncode == 0 and valid_png else "FAILED",
            "probe": "real PDF-to-PNG conversion and PNG signature",
            "exit_code": converted.returncode,
            "detail": (converted.stderr or converted.stdout).strip()[-500:],
        }
    except (OSError, subprocess.TimeoutExpired) as exc:
        return {"status": "FAILED", "probe": "real PDF-to-PNG conversion", "detail": str(exc)}


def probe_optional(path: Path, name: str) -> dict[str, Any]:
    args = ["-v"] if name == "mutool" else ["-version"]
    try:
        result = run([str(path), *args], timeout=15)
        return {
            "status": "VERIFIED" if result.returncode == 0 else "FAILED",
            "probe": "version call",
            "exit_code": result.returncode,
            "detail": (result.stderr or result.stdout).strip()[-500:],
        }
    except (OSError, subprocess.TimeoutExpired) as exc:
        return {"status": "FAILED", "probe": "version call", "detail": str(exc)}


def main() -> int:
    parser = argparse.ArgumentParser(description="Check the active Typst-based math-modeling environment.")
    parser.add_argument("--output")
    parser.add_argument("--runtime-config", default=".codex/runtime.local.json")
    args = parser.parse_args()

    runtime_path = Path(args.runtime_config).resolve()
    runtime = load_runtime(runtime_path)

    packages: list[dict[str, Any]] = []
    for module, distribution in PACKAGES.items():
        try:
            importlib.import_module(module)
            try:
                version = importlib.metadata.version(distribution)
            except importlib.metadata.PackageNotFoundError:
                version = "unknown"
            packages.append({"module": module, "distribution": distribution, "status": "VERIFIED", "version": version})
        except ModuleNotFoundError:
            packages.append({"module": module, "distribution": distribution, "status": "UNVERIFIED", "version": None})
        except Exception as exc:  # binary extension/import-time failures are evidence failures
            packages.append({"module": module, "distribution": distribution, "status": "FAILED", "version": None, "detail": str(exc)})

    resolved: dict[str, Path | None] = {}
    sources: dict[str, str] = {}
    for name, commands in TOOLS.items():
        resolved[name], sources[name] = resolve_tool(name, commands, runtime)

    tools: list[dict[str, Any]] = []
    for name in TOOLS:
        path = resolved[name]
        if not path:
            tools.append({"name": name, "status": "UNVERIFIED", "path": None, "source": sources[name], "probe": "not run"})
            continue
        if name == "typst":
            evidence = probe_typst(path)
        elif name == "drawio":
            evidence = probe_drawio(path)
        elif name == "pdftoppm":
            evidence = probe_pdftoppm(path, resolved.get("typst"))
        else:
            evidence = probe_optional(path, name)
        tools.append({"name": name, "path": str(path), "source": sources[name], **evidence})

    pip = run([sys.executable, "-m", "pip", "--version"], timeout=30)
    configured_python = runtime.get("python")
    python_matches = not configured_python or Path(configured_python).resolve() == Path(sys.executable).resolve()
    python_check = {
        "status": "VERIFIED" if python_matches else "FAILED",
        "executable": sys.executable,
        "version": sys.version,
        "platform": platform.platform(),
    }
    if not python_matches:
        python_check["configured"] = configured_python

    tool_by_name = {item["name"]: item for item in tools}
    raster_candidates = [tool_by_name[name] for name in ("pdftoppm", "mutool", "magick")]
    raster_status = "VERIFIED" if any(item["status"] == "VERIFIED" for item in raster_candidates) else worst(raster_candidates)
    capabilities = {
        "python_baseline": worst([python_check, {"status": "VERIFIED" if pip.returncode == 0 else "FAILED"}, *packages]),
        "paper_typst": tool_by_name["typst"]["status"],
        "drawio_export": tool_by_name["drawio"]["status"],
        "pdf_raster": raster_status,
    }
    report_status = max(capabilities.values(), key=RANK.get)
    report = {
        "status": report_status,
        "policy": {"paper_engine": "typst", "latex_checked": False},
        "runtime_config": str(runtime_path) if runtime_path.is_file() else None,
        "python": python_check,
        "pip": {"status": "VERIFIED" if pip.returncode == 0 else "FAILED", "output": (pip.stdout or pip.stderr).strip()},
        "packages": packages,
        "tools": tools,
        "capabilities": capabilities,
    }
    if args.output:
        output = Path(args.output)
        output.parent.mkdir(parents=True, exist_ok=True)
        output.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
        print(output.resolve())
    else:
        print(json.dumps(report, ensure_ascii=False, indent=2))
    return 0 if report_status == "VERIFIED" else 1


if __name__ == "__main__":
    raise SystemExit(main())
