from __future__ import annotations

import argparse
import os
from pathlib import Path


def existing(path: Path) -> str:
    return str(path.resolve()) if path.exists() else ""


def find_paper() -> Path:
    current = Path.cwd()
    if (current / "main.tex").is_file():
        return current
    candidates = [
        path
        for path in current.rglob("main.tex")
        if len(path.relative_to(current).parts) <= 4
    ]
    return candidates[0].parent if candidates else current / "paper"


def main() -> None:
    parser = argparse.ArgumentParser(description="Run the LaTeX paper text gate with the selected Python interpreter.")
    parser.add_argument("paper_dir", nargs="?")
    parser.add_argument("--paper-dir", dest="paper_dir_option")
    parser.add_argument("--root-dir")
    parser.add_argument("--main")
    parser.add_argument("--sections-dir")
    parser.add_argument("--references")
    parser.add_argument("--figures-dir")
    parser.add_argument("--results-file")
    parser.add_argument("--problem-analysis")
    parser.add_argument("--all-results")
    parser.add_argument("--internal-term", action="append", default=[])
    parser.add_argument("--no-internal-check", action="store_true")
    args = parser.parse_args()

    paper = Path(args.paper_dir_option or args.paper_dir) if (args.paper_dir_option or args.paper_dir) else find_paper()
    root = Path(args.root_dir) if args.root_dir else (Path.cwd() if paper == Path(".") else paper.parent)
    entry = Path(args.main) if args.main else paper / "main.tex"
    if entry.suffix.lower() != ".tex":
        parser.error("this project uses LaTeX; --main must point to main.tex")

    sections = Path(args.sections_dir) if args.sections_dir else paper / "sections"
    references = Path(args.references) if args.references else paper / "references.tex"
    figures = Path(args.figures_dir) if args.figures_dir else root / "figures"
    results = Path(args.results_file) if args.results_file else root / "reports" / "RESULTS_REPORT.md"
    if not results.is_file():
        fallback = root / "RESULTS_REPORT.md"
        results = fallback if fallback.is_file() else results
    problem_analysis = Path(args.problem_analysis) if args.problem_analysis else root / "PROBLEM_ANALYSIS.md"
    all_results = Path(args.all_results) if args.all_results else figures / "all_results.json"
    os.environ.update(
        {
            "PAPER_DIR": str(paper.resolve()),
            "ROOT_DIR": str(root.resolve()),
            "MAIN_FILE": str(entry.resolve()),
            "SECTIONS_DIR": existing(sections),
            "REFERENCES_FILE": existing(references),
            "FIGURES_DIR": existing(figures),
            "RESULTS_FILE": existing(results),
            "PROBLEM_ANALYSIS_FILE": existing(problem_analysis),
            "ALL_RESULTS_FILE": existing(all_results),
            "NO_INTERNAL_CHECK": "1" if args.no_internal_check else "0",
            "EXTRA_INTERNAL_TERMS_STR": "\n".join(args.internal_term),
        }
    )

    legacy = Path(__file__).with_name("writing_check.sh")
    source = legacy.read_text(encoding="utf-8")
    marker = "python3 - <<'PY'\n"
    if marker not in source or not source.rstrip().endswith("PY"):
        raise RuntimeError("writing-check core marker is missing")
    body = source.split(marker, 1)[1].rsplit("\nPY", 1)[0]
    exec(compile(body, str(legacy) + ":python-core", "exec"), {"__name__": "__main__"})


if __name__ == "__main__":
    main()
