"""Read-only structural evidence audit. Does not execute models or certify science."""
from __future__ import annotations

import argparse
from datetime import datetime
import hashlib
import json
import math
from pathlib import Path, PureWindowsPath
import re
import struct
import sys

STAGES = ["G1", "G2", "G3", "G4", "G5", "G6", "G7", "Final"]


class EvidenceError(ValueError):
    pass


def need(condition, message):
    if not condition:
        raise EvidenceError(message)


def text(value, label):
    need(isinstance(value, str) and bool(value.strip()), f"{label}: 需要非空文本")
    need(value.strip().lower() not in {"todo", "tbd", "待填写", "待补充", "..."}, f"{label}: 占位符")
    return value


def number(value, label):
    need(type(value) in {float, int} and math.isfinite(value), f"{label}: 需要有限数值")
    return value


def array(value, label, nonempty=False):
    need(isinstance(value, list) and (not nonempty or bool(value)), f"{label}: 需要{'非空' if nonempty else ''}数组")
    return value


def enum(value, choices, label):
    need(isinstance(value, str) and value in choices, f"{label}: 枚举值非法")


def read_json(path):
    def invalid(value):
        raise EvidenceError(f"JSON 非有限常量：{value}")
    return json.loads(path.read_text(encoding="utf-8-sig"), parse_constant=invalid)


def sha(path):
    with path.open("rb") as stream:
        return hashlib.file_digest(stream, "sha256").hexdigest()


def index(rows, label, nonempty=False):
    result = {}
    for item in array(rows, label, nonempty):
        need(isinstance(item, dict), f"{label}: 成员须为对象")
        key = text(item.get("id"), f"{label}.id")
        need(key not in result, f"{label}: 重复 ID {key}")
        result[key] = item
    return result


class Audit:
    def __init__(self, project):
        self.project = Path(project).resolve()
        self.files = {}
        self.metrics = {}
        self.run_data = set()

    def path(self, relative):
        text(relative, "path")
        rel = Path(relative.replace("\\", "/"))
        need(not rel.is_absolute() and not PureWindowsPath(relative).drive
             and ".." not in rel.parts, f"禁止项目外路径：{relative}")
        candidate = self.project / rel
        need(candidate.resolve().is_relative_to(self.project), f"路径越界：{relative}")
        for part in [candidate, *candidate.parents]:
            if part == self.project:
                break
            need(not part.is_symlink() and not (hasattr(part, "is_junction") and part.is_junction()),
                 f"证据不可使用链接：{relative}")
        return candidate

    def ref(self, value, label):
        need(isinstance(value, dict), f"{label}: 需要文件引用对象")
        path = self.path(value.get("path"))
        claimed = value.get("sha256")
        need(isinstance(claimed, str) and re.fullmatch(r"[0-9a-fA-F]{64}", claimed), f"{label}: SHA256 非法")
        need(path.is_file() and path.stat().st_size > 0, f"{label}: 缺文件/空文件 {path}")
        actual = sha(path)
        need(actual == claimed.lower(), f"{label}: 文件哈希变化 {value['path']}")
        self.files[path.relative_to(self.project).as_posix()] = actual
        return path

    def refs(self, values, label, nonempty=False):
        return [self.ref(v, label) for v in array(values, label, nonempty)]

    def timestamp(self, value, label):
        dt = datetime.fromisoformat(text(value, label))
        need(dt.tzinfo is not None, f"{label}: 时间需带时区")
        return dt

    def review(self, value, outputs, label):
        record = read_json(self.ref(value, label))
        need(record["status"] == "reviewed", f"{label}: 未完成实际检查")
        text(record.get("reviewer"), f"{label}.reviewer")
        text(record.get("findings"), f"{label}.findings")
        self.timestamp(record.get("reviewed_at"), label)
        reviewed = set(self.refs(record.get("outputs"), label, True))
        need(set(outputs) <= reviewed, f"{label}: 未覆盖全部本次导出物")
        return reviewed

    def experiments(self, rows, models, level):
        experiments = index(rows, "experiments", True)
        for key, ex in experiments.items():
            label = f"experiment {key}"
            need(ex.get("model_id") in models, f"{label}: 未知模型")
            enum(ex.get("role"), {"baseline", "improved", "ablation", "stress"}, label)
            enum(ex.get("status"), {"planned", "succeeded", "failed", "not_applicable"}, label)
            text(ex.get("reason"), label)
            protocol = read_json(self.ref(ex.get("protocol"), label + ".protocol"))
            need(isinstance(protocol, dict), f"{label}: protocol 应为 JSON 对象")
            protocol_inputs = set(self.refs(protocol.get("inputs"), label + ".protocol.inputs", True))
            for field in ("split", "preprocessing", "budget", "metrics", "conditions"):
                need(bool(protocol.get(field)), f"{label}: protocol 缺 {field}")
            if ex["status"] == "not_applicable":
                self.ref(ex.get("rationale"), label + ".rationale")
            if ex["status"] == "succeeded":
                record = read_json(self.ref(ex.get("run_record"), label + ".run_record"))
                need(type(record["exit_code"]) is int and record["exit_code"] == 0, f"{label}: 成功实验退出码非零")
                for arg in array(record.get("command"), label + ".command", True):
                    text(arg, label + ".argv")
                interpreter = text(record.get("python"), label + ".python")
                need(Path(interpreter).is_absolute() or PureWindowsPath(interpreter).is_absolute(), f"{label}: 解释器须为绝对路径")
                start = self.timestamp(record.get("started_at"), label)
                finish = self.timestamp(record.get("finished_at"), label)
                need(finish >= start, f"{label}: 结束早于开始")
                inputs = set(self.refs(record.get("inputs"), label + ".inputs", True))
                need(inputs == protocol_inputs, f"{label}: 运行输入与比较协议不一致")
                self.refs(record.get("code"), label + ".code", True)
                self.ref(record.get("log"), label + ".log")
                need("seed" in record and (record["seed"] is None or type(record["seed"]) is int), f"{label}: seed 非法")
                self.run_data.update(self.refs(record.get("artifacts", []), label + ".artifacts"))
                metric_path = self.ref(ex.get("metrics"), label + ".metrics")
                self.run_data.add(metric_path)
                metrics = read_json(metric_path)
                need(isinstance(metrics, dict) and bool(metrics), f"{label}: 空指标")
                self.metrics[key] = {name: number(v, f"{label}.{name}") for name, v in metrics.items()}
            if level >= 2:
                need(ex["status"] != "planned", f"{label}: 正式实验仍未执行")
        for key in models:
            relevant = [e for e in experiments.values() if e["model_id"] == key]
            if level >= 1:
                need(any(e["role"] == "baseline" and e["status"] == "succeeded" for e in relevant), f"{key}: 缺成功基线")
            if level >= 2:
                for role in ("improved", "ablation", "stress"):
                    need(any(e["role"] == role and e["status"] in {"succeeded", "not_applicable"} for e in relevant), f"{key}: 缺 {role} 结果/不适用依据")
        return experiments

    def check(self, ledger, stage):
        level = STAGES.index(stage)
        need(type(ledger.get("schema_version")) is int and ledger["schema_version"] == 1, "未知 schema_version")
        models = index(ledger.get("models"), "models", True)
        for key, model in models.items():
            for field in ("question", "baseline", "change", "mechanism", "assumptions", "verification_plan", "failure_modes", "complexity", "selection_reason"):
                text(model.get(field), f"{key}.{field}")
            self.ref(model.get("derivation"), key + ".derivation")
            enum(model.get("contribution_type"), {"application", "method", "theory"}, key)
            enum(model.get("literature_status"), {"verified", "unknown"}, key)
            literature = self.refs(model.get("literature"), key + ".literature")
            if model["contribution_type"] in {"method", "theory"} or model["literature_status"] == "verified":
                need(model["literature_status"] == "verified" and bool(literature), f"{key}: 创新声明缺文献核验")
        experiments = self.experiments(ledger.get("experiments"), models, level)
        if level < 2:
            return
        claims = index(ledger.get("claims"), "claims", True)
        for key, claim in claims.items():
            need(claim.get("model_id") in models, f"{key}: 未知模型")
            for field in ("statement", "limitations"):
                text(claim.get(field), key + "." + field)
            enum(claim.get("kind"), {"empirical", "theoretical"}, key)
            enum(claim.get("verdict"), {"supported", "not_supported", "inconclusive"}, key)
            self.ref(claim.get("analysis"), key + ".analysis")
            ids = array(claim.get("experiment_ids"), key, claim["kind"] == "empirical")
            for eid in ids:
                need(eid in self.metrics and experiments[eid]["model_id"] == claim["model_id"], f"{key}: 主张引用失败/缺失/其他模型实验")
            if "comparison" in claim:
                cmp = claim["comparison"]
                a, b = cmp["baseline_id"], cmp["candidate_id"]
                need(a != b and a in ids and b in ids, f"{key}: 比较缺主张关联")
                need(experiments[a]["role"] == "baseline" and experiments[b]["role"] == "improved", f"{key}: 比较角色不符")
                need(experiments[a]["protocol"]["sha256"].lower() == experiments[b]["protocol"]["sha256"].lower(), f"{key}: 基线与改进协议不一致")
                enum(cmp.get("direction"), {"min", "max"}, key)
                threshold = number(cmp.get("minimum_gain"), key)
                need(threshold >= 0, f"{key}: minimum_gain 不能为负")
                av, bv = self.metrics[a][cmp["metric"]], self.metrics[b][cmp["metric"]]
                gain = av - bv if cmp["direction"] == "min" else bv - av
                if claim["verdict"] == "supported":
                    need(gain > 0 and gain >= threshold, f"{key}: 指标未支持声称的改善")
        figures = index(ledger.get("figures"), "figures", True)
        need(any(f.get("kind") == "data" for f in figures.values()), "缺数据图")
        for key, figure in figures.items():
            enum(figure.get("kind"), {"data", "diagram"}, key)
            if level == 2 and figure["kind"] == "diagram":
                continue
            text(figure.get("purpose"), key)
            for cid in array(figure.get("claim_ids"), key):
                need(cid in claims, f"{key}: 未知主张")
            source = self.ref(figure.get("source"), key + ".source")
            if figure["kind"] == "diagram":
                need(source.suffix.lower() in {".svg", ".drawio"}, f"{key}: 缺可编辑图源")
            else:
                need(source.suffix.lower() in {".py", ".r", ".jl", ".m"}, f"{key}: 缺绘图源码")
            data = set(self.refs(figure.get("data"), key + ".data", figure["kind"] == "data"))
            need(data <= self.run_data, f"{key}: 图源数据不属于已登记的成功实验")
            outputs = self.refs(figure.get("exports"), key + ".exports", True)
            need(any(p.suffix.lower() in {".pdf", ".png"} for p in outputs), f"{key}: 缺 PDF/PNG 导出")
            width = number(figure.get("width_mm"), key + ".width_mm")
            need(width > 0, f"{key}: 无效显示宽度")
            for out in outputs:
                if out.suffix.lower() == ".pdf":
                    with out.open("rb") as stream:
                        need(stream.read(5) == b"%PDF-", f"{key}: 非 PDF 文件")
                if out.suffix.lower() == ".png":
                    with out.open("rb") as stream:
                        header = stream.read(24)
                    need(len(header) == 24 and header[:8] == b"\x89PNG\r\n\x1a\n" and header[12:16] == b"IHDR", f"{key}: 非 PNG")
                    pixels = struct.unpack(">I", header[16:20])[0]
                    need(type(figure.get("raster_width_px")) is int and figure["raster_width_px"] == pixels, f"{key}: 像素记录与 PNG 不符")
                    need(pixels * 25.4 / width >= 300, f"{key}: 有效 DPI 不足 300")
            self.ref(figure.get("content_review"), key + ".content_review")
            self.review(figure.get("visual_review"), outputs, key + ".visual_review")
        if level >= 3 and not any(f["kind"] == "diagram" for f in figures.values()):
            self.ref(ledger.get("diagram_waiver"), "diagram_waiver")
        if level < 4:
            return
        papers = index(ledger.get("paper"), "paper", True)
        for key, paper in papers.items():
            text(paper.get("purpose"), key)
            for cid in array(paper.get("claim_ids"), key, True):
                need(cid in claims and claims[cid]["verdict"] == "supported", f"{key}: 将未证实主张作为正文结论")
            for fid in array(paper.get("figure_ids"), key):
                need(fid in figures, f"{key}: 未知图片")
            if level < 5:
                continue
            source = self.ref(paper.get("source"), key + ".source")
            need(source.suffix.lower() in {".tex", ".md", ".txt", ".docx"}, f"{key}: 缺可编辑正文")
            numbers = array(paper.get("numbers"), key + ".numbers")
            need(not numbers or source.suffix.lower() != ".docx", f"{key}: DOCX 数字需提取并核对段落文本")
            content = source.read_text(encoding="utf-8-sig") if numbers else ""
            for entry in numbers:
                eid = entry["experiment_id"]
                need(eid in self.metrics, f"{key}: 引用未成功实验")
                expected = self.metrics[eid][entry["metric"]]
                decimals = entry["decimals"]
                need(type(decimals) is int and 0 <= decimals <= 10, f"{key}: decimals 超范围")
                scale = number(entry["scale"], key)
                need(scale in {1, 100}, f"{key}: scale 只能 1 或 100")
                value = number(entry["value"], key)
                need(abs(value - expected * scale) <= 0.5 * 10 ** (-decimals) + 1e-12, f"{key}: 正文数字与结果不一致")
                need(text(entry.get("text"), key) in content, f"{key}: 正文中找不到登记文本")
        if level >= 6:
            paths = self.review(ledger.get("layout_review"), [], "layout_review")
            need(any(p.suffix.lower() == ".pdf" for p in paths), "版式复核缺 PDF")


def audit(project, stage, ledger_path="reports/research_evidence.json"):
    checker = Audit(project)
    try:
        need(stage in STAGES, "未知阶段")
        ledger = read_json(checker.path(ledger_path))
        need(isinstance(ledger, dict), "台账需要 JSON 对象")
        checker.check(ledger, stage)
        return {"status": "STRUCTURAL_PASS", "stage": stage, "checked_files": checker.files,
                "limitation": "仅核对登记证据；未认证数学证明、创新性、运行真实性或视觉质量。"}
    except (EvidenceError, OSError, ValueError, KeyError, TypeError, AttributeError, OverflowError) as exc:
        return {"status": "FAIL", "stage": stage, "errors": [str(exc)]}


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--project", type=Path, required=True)
    parser.add_argument("--stage", choices=STAGES, required=True)
    parser.add_argument("--ledger", default="reports/research_evidence.json")
    args = parser.parse_args(argv)
    result = audit(args.project, args.stage, args.ledger)
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0 if result["status"] == "STRUCTURAL_PASS" else 2


if __name__ == "__main__":
    raise SystemExit(main())
