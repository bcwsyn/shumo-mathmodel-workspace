from __future__ import annotations

import argparse
import hashlib
import json
import re
import sys
import zipfile
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path


TEXT_EXTS = {".txt", ".m", ".py", ".cpp", ".c", ".h", ".htm", ".html", ".md"}
UNSUPPORTED_EXTS = {".doc", ".ppt", ".rar", ".vip"}


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def safe_name(path: Path) -> str:
    value = "__".join(path.parts)
    return re.sub(r"[^0-9A-Za-z._\-\u4e00-\u9fff]+", "_", value)


def read_text(path: Path) -> tuple[str, str]:
    data = path.read_bytes()
    for encoding in ("utf-8-sig", "utf-8", "gb18030", "gbk", "big5"):
        try:
            return data.decode(encoding), encoding
        except UnicodeDecodeError:
            pass
    return data.decode("utf-8", errors="replace"), "utf-8-replace"


def extract_pdf(path: Path) -> tuple[str, int, int]:
    from pypdf import PdfReader

    reader = PdfReader(str(path))
    chunks = []
    nonempty = 0
    for number, page in enumerate(reader.pages, start=1):
        text = page.extract_text() or ""
        if text.strip():
            nonempty += 1
        chunks.append(f"\n\n===== PAGE {number} =====\n\n{text}")
    return "".join(chunks).lstrip(), len(reader.pages), nonempty


def scan(source: Path, library: Path) -> None:
    source = source.resolve()
    library = library.resolve()
    extracted_pdf = library / "extracted" / "pdf"
    extracted_text = library / "extracted" / "text"
    for directory in (
        extracted_pdf,
        extracted_text,
        library / "drafts" / "papers",
        library / "drafts" / "methods",
        library / "approved" / "papers",
        library / "approved" / "methods",
    ):
        directory.mkdir(parents=True, exist_ok=True)

    records = []
    for path in sorted((p for p in source.rglob("*") if p.is_file()), key=lambda p: str(p).lower()):
        relative = path.relative_to(source)
        ext = path.suffix.lower()
        record = {
            "path": relative.as_posix(),
            "extension": ext,
            "size": path.stat().st_size,
            "sha256": sha256(path),
            "status": "indexed",
        }
        try:
            if ext == ".pdf":
                text, pages, nonempty = extract_pdf(path)
                destination = extracted_pdf / f"{safe_name(relative)}.txt"
                destination.write_text(text, encoding="utf-8")
                record.update(pages=pages, text_pages=nonempty, extracted=str(destination.relative_to(library).as_posix()))
            elif ext in TEXT_EXTS:
                text, encoding = read_text(path)
                destination = extracted_text / f"{safe_name(relative)}.txt"
                destination.write_text(text, encoding="utf-8")
                record.update(encoding=encoding, characters=len(text), extracted=str(destination.relative_to(library).as_posix()))
            elif ext == ".zip":
                with zipfile.ZipFile(path) as archive:
                    record["members"] = archive.namelist()
                record["status"] = "listed-not-extracted"
            elif ext in UNSUPPORTED_EXTS:
                record["status"] = "needs-conversion"
            elif ext == ".mat":
                record["status"] = "metadata-only"
            else:
                record["status"] = "unhandled"
        except Exception as exc:
            record["status"] = "error"
            record["error"] = f"{type(exc).__name__}: {exc}"
        records.append(record)

    payload = {
        "source": str(source),
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "counts": dict(Counter(record["status"] for record in records)),
        "files": records,
    }
    (library / "inventory.json").write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")

    lines = ["# 学习资料清单", "", f"- 来源：`{source}`", f"- 文件数：{len(records)}", "", "| 状态 | 数量 |", "| --- | ---: |"]
    for status, count in sorted(payload["counts"].items()):
        lines.append(f"| {status} | {count} |")
    lines.extend(["", "## 需转换或失败", ""])
    for record in records:
        if record["status"] in {"needs-conversion", "error", "unhandled"}:
            lines.append(f"- `{record['path']}`：{record['status']} {record.get('error', '')}".rstrip())
    (library / "inventory.md").write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(json.dumps(payload["counts"], ensure_ascii=False))


def search(library: Path, query: str) -> None:
    terms = [term.lower() for term in re.split(r"\s+", query.strip()) if term]
    roots = [library / "approved", library / "drafts"]
    hits = []
    for root in roots:
        if not root.exists():
            continue
        for path in root.rglob("*.md"):
            text = path.read_text(encoding="utf-8", errors="replace")
            lowered = text.lower()
            score = sum(lowered.count(term) for term in terms)
            if score:
                hits.append((score, path, text))
    for score, path, text in sorted(hits, key=lambda item: (-item[0], str(item[1])))[:20]:
        title = next((line.lstrip("# ") for line in text.splitlines() if line.startswith("#")), path.stem)
        print(f"{score}\t{path}\t{title}")


def main() -> None:
    parser = argparse.ArgumentParser(description="Index and search a local mathematical-modeling study library.")
    subparsers = parser.add_subparsers(dest="command", required=True)
    scan_parser = subparsers.add_parser("scan")
    scan_parser.add_argument("--source", required=True, type=Path)
    scan_parser.add_argument("--library", required=True, type=Path)
    search_parser = subparsers.add_parser("search")
    search_parser.add_argument("--library", required=True, type=Path)
    search_parser.add_argument("--query", required=True)
    args = parser.parse_args()
    if args.command == "scan":
        scan(args.source, args.library)
    else:
        search(args.library.resolve(), args.query)


if __name__ == "__main__":
    main()
