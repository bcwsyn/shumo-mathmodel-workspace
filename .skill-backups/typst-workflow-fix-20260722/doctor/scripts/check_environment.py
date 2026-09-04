from __future__ import annotations

import argparse
import importlib.metadata
import importlib.util
import json
import platform
import shutil
import subprocess
import sys
from pathlib import Path


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
    "xelatex": ["xelatex"],
    "drawio": ["drawio", "draw.io"],
    "pdftoppm": ["pdftoppm"],
    "mutool": ["mutool"],
    "magick": ["magick"],
}


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


def main() -> int:
    parser = argparse.ArgumentParser(description="Check the active math-modeling environment.")
    parser.add_argument("--output")
    parser.add_argument("--runtime-config", default=".codex/runtime.local.json")
    args = parser.parse_args()

    runtime_path = Path(args.runtime_config).resolve()
    runtime = load_runtime(runtime_path)

    packages = []
    for module, distribution in PACKAGES.items():
        found = importlib.util.find_spec(module) is not None
        version = None
        if found:
            try:
                version = importlib.metadata.version(distribution)
            except importlib.metadata.PackageNotFoundError:
                version = "unknown"
        packages.append({"module": module, "distribution": distribution, "status": "VERIFIED" if found else "UNVERIFIED", "version": version})

    tools = []
    for name, commands in TOOLS.items():
        configured = runtime.get(name)
        if configured and Path(configured).is_file():
            resolved = str(Path(configured).resolve())
            source = "runtime-config"
        else:
            resolved = next((value for command in commands if (value := shutil.which(command))), None)
            source = "PATH" if resolved else "not-found"
        tools.append({"name": name, "status": "VERIFIED" if resolved else "UNVERIFIED", "path": resolved, "source": source})

    pip = subprocess.run(
        [sys.executable, "-m", "pip", "--version"],
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        timeout=30,
    )
    configured_python = runtime.get("python")
    python_matches = not configured_python or Path(configured_python).resolve() == Path(sys.executable).resolve()
    report = {
        "status": "VERIFIED",
        "runtime_config": str(runtime_path) if runtime_path.is_file() else None,
        "python": {"executable": sys.executable, "version": sys.version, "platform": platform.platform()},
        "pip": {"status": "VERIFIED" if pip.returncode == 0 else "FAILED", "output": (pip.stdout or pip.stderr).strip()},
        "packages": packages,
        "tools": tools,
    }
    if pip.returncode != 0 or not python_matches:
        report["status"] = "FAILED"
    if not python_matches:
        report["python"]["configuration_status"] = "FAILED"
        report["python"]["configured"] = configured_python
    if args.output:
        output = Path(args.output)
        output.parent.mkdir(parents=True, exist_ok=True)
        output.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
        print(output.resolve())
    else:
        print(json.dumps(report, ensure_ascii=False, indent=2))
    return 0 if report["status"] == "VERIFIED" else 1


if __name__ == "__main__":
    raise SystemExit(main())
