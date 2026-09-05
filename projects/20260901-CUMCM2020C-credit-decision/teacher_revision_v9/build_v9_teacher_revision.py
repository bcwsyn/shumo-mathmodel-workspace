"""Build the non-destructive V9.0 teacher-feedback revision from V8.1.

The script retains all package parts except word/document.xml and the three
manually redrawn process-map PNGs.  Editable SVG originals are emitted beside
the document for team review and later reuse.
"""

from __future__ import annotations

import copy
import shutil
import zipfile
from pathlib import Path

from lxml import etree
from PIL import Image, ImageDraw, ImageFont


ROOT = Path(__file__).resolve().parent
SOURCE = Path(r"C:\Users\HP\OneDrive\xwechat_files\wxid_2bguojz3wpwl22_5ea0\msg\file\2026-09\全篇证据约束优化版_V8.1.docx")
OUT = ROOT / "deliverables" / "全篇证据约束优化版_V9.0_教师意见全面落实版.docx"
FIG = ROOT / "figures"

W = "http://schemas.openxmlformats.org/wordprocessingml/2006/main"
NS = {"w": W}
QN = lambda tag: f"{{{W}}}{tag}"

NAVY = "#17375E"
BLUE = "#2E73B9"
TEAL = "#168C8C"
GREEN = "#447A4C"
ORANGE = "#E68430"
PURPLE = "#7658A5"
INK = "#17324D"
MUTED = "#5B6B7D"
PANEL = "#F3F7FB"
LINE = "#AAB8C6"


def font(size: int, bold: bool = False):
    candidates = [
        r"C:\Windows\Fonts\msyhbd.ttc" if bold else r"C:\Windows\Fonts\msyh.ttc",
        r"C:\Windows\Fonts\simhei.ttf" if bold else r"C:\Windows\Fonts\simsun.ttc",
    ]
    for candidate in candidates:
        if Path(candidate).exists():
            return ImageFont.truetype(candidate, size)
    return ImageFont.load_default()


def text_center(draw: ImageDraw.ImageDraw, box, text: str, fnt, fill: str):
    left, top, right, bottom = box
    bbox = draw.multiline_textbbox((0, 0), text, font=fnt, spacing=6, align="center")
    x = (left + right - (bbox[2] - bbox[0])) / 2
    y = (top + bottom - (bbox[3] - bbox[1])) / 2 - 2
    draw.multiline_text((x, y), text, font=fnt, fill=fill, spacing=6, align="center")


def round_card(draw, xy, fill, title, body="", accent=None, title_size=34, body_size=24):
    x1, y1, x2, y2 = xy
    radius = 28
    draw.rounded_rectangle((x1 + 7, y1 + 9, x2 + 7, y2 + 9), radius=radius, fill="#DDE5EE")
    draw.rounded_rectangle((x1, y1, x2, y2), radius=radius, fill=fill, outline="#FFFFFF", width=2)
    if accent:
        draw.rounded_rectangle((x1, y1, x1 + 12, y2), radius=8, fill=accent)
    title_color = "#FFFFFF" if fill in {NAVY, BLUE, TEAL, GREEN, ORANGE, PURPLE} else INK
    if body:
        text_center(draw, (x1 + 30, y1 + 16, x2 - 20, y1 + 75), title, font(title_size, True), title_color)
        text_center(draw, (x1 + 24, y1 + 72, x2 - 18, y2 - 12), body, font(body_size), title_color)
    else:
        text_center(draw, (x1 + 18, y1 + 8, x2 - 18, y2 - 8), title, font(title_size, True), title_color)


def arrow(draw, start, end, color=BLUE, width=8, dashed=False):
    x1, y1 = start
    x2, y2 = end
    if dashed:
        steps = 12
        for i in range(0, steps, 2):
            a, b = i / steps, (i + 1) / steps
            draw.line((x1 + (x2 - x1) * a, y1 + (y2 - y1) * a,
                       x1 + (x2 - x1) * b, y1 + (y2 - y1) * b), fill=color, width=width)
    else:
        draw.line((x1, y1, x2, y2), fill=color, width=width)
    import math
    angle = math.atan2(y2 - y1, x2 - x1)
    length = 22
    spread = 0.55
    p1 = (x2 - length * math.cos(angle - spread), y2 - length * math.sin(angle - spread))
    p2 = (x2 - length * math.cos(angle + spread), y2 - length * math.sin(angle + spread))
    draw.polygon([(x2, y2), p1, p2], fill=color)


def section_label(draw, xy, text, fill):
    x1, y1, x2, y2 = xy
    draw.rounded_rectangle(xy, radius=18, fill=fill)
    text_center(draw, xy, text, font(25, True), "#FFFFFF")


def canvas(width, height, title, subtitle):
    im = Image.new("RGB", (width, height), "#FFFFFF")
    draw = ImageDraw.Draw(im)
    draw.rectangle((0, 0, width, 118), fill="#EEF4FA")
    draw.rectangle((0, 112, width, 118), fill=ORANGE)
    text_center(draw, (60, 14, width - 60, 78), title, font(46, True), NAVY)
    text_center(draw, (60, 70, width - 60, 108), subtitle, font(23), MUTED)
    return im, draw


def diagram_one_png(path: Path):
    im, draw = canvas(2400, 1330, "中小微企业信贷决策的证据约束流程", "共同特征外推 · 利率需求响应 · 有限情景稳健配置")
    panels = [(55, 180, 585, 1130), (620, 180, 1180, 1130), (1215, 180, 1780, 1130), (1815, 180, 2345, 1130)]
    titles = [("数据基础", BLUE), ("信用评价", TEAL), ("授信配置", ORANGE), ("压力决策", PURPLE)]
    for (x1, y1, x2, y2), (name, color) in zip(panels, titles):
        draw.rounded_rectangle((x1, y1, x2, y2), radius=34, fill=PANEL, outline="#D6E0EB", width=2)
        section_label(draw, (x1 + 22, y1 + 24, x2 - 22, y1 + 84), name, color)
    round_card(draw, (95, 315, 545, 490), "#FFFFFF", "企业与发票信息", "销项 / 进项发票\n信贷记录与信誉评价", accent=BLUE)
    round_card(draw, (95, 575, 545, 750), "#DCEAF8", "共同字段筛选", "仅保留两批企业均可获得的\n发票经营特征", accent=BLUE)
    round_card(draw, (95, 835, 545, 1010), "#FFFFFF", "特征账本", "口径、数据来源、时间窗口\n均留痕可复核", accent=BLUE)
    arrow(draw, (320, 490), (320, 575), BLUE)
    arrow(draw, (320, 750), (320, 835), BLUE)
    round_card(draw, (660, 300, 1140, 475), NAVY, "OOF 评级概率", "Logistic + XGBoost\n5 折折外预测", accent=ORANGE)
    round_card(draw, (660, 560, 1140, 735), TEAL, "等级概率融合", "权重 w = 0.80\n经保序映射得到 CRI", accent=ORANGE)
    round_card(draw, (660, 820, 1140, 1005), "#FFFFFF", "跨样本外推与漂移诊断", "冻结源样本管线；检查均值漂移、\n尾部越界与阈值敏感性", accent=TEAL, title_size=30)
    arrow(draw, (900, 475), (900, 560), TEAL)
    arrow(draw, (900, 735), (900, 820), TEAL)
    round_card(draw, (1255, 300, 1740, 475), ORANGE, "利率需求响应", "企业级保序回归\n利率—流失率曲线", accent=NAVY)
    round_card(draw, (1255, 560, 1740, 735), NAVY, "组合授信 MIP", "额度、利率、预算、评级\n与组合风险约束", accent=ORANGE)
    round_card(draw, (1255, 820, 1740, 1005), "#FFFFFF", "可行性与角点解释", "先检验风险约束可行性；\n线性收益下的上限额度需说明", accent=ORANGE, title_size=30)
    arrow(draw, (1498, 475), (1498, 560), ORANGE)
    arrow(draw, (1498, 735), (1498, 820), ORANGE)
    round_card(draw, (1855, 300, 2305, 475), PURPLE, "脆弱性量化", "六项风险指标\n百分位与主观权重融合", accent=ORANGE)
    round_card(draw, (1855, 560, 2305, 735), PURPLE, "三类有限压力情景", "需求压力 / 供给压力 / 联合压力\n通过风险与留存通道传导", accent=ORANGE, title_size=30)
    round_card(draw, (1855, 820, 2305, 1005), NAVY, "有限情景最大最小配置", "以最坏情景收益为准；\n情景不是概率分布假设", accent=PURPLE, title_size=30)
    arrow(draw, (2080, 475), (2080, 560), PURPLE)
    arrow(draw, (2080, 735), (2080, 820), PURPLE)
    arrow(draw, (545, 660), (660, 660), BLUE)
    arrow(draw, (1140, 650), (1255, 650), TEAL)
    arrow(draw, (1740, 650), (1855, 650), ORANGE)
    draw.rounded_rectangle((220, 1190, 2180, 1255), radius=22, fill="#FFF3E5", outline="#F2C58B", width=2)
    text_center(draw, (250, 1198, 2150, 1248), "输出：可解释的风险排序、授信方案、情景下行边界与可复现证据（不将成熟算法组合表述为新算法）", font(27, True), INK)
    im.save(path)


def diagram_two_png(path: Path):
    im, draw = canvas(2350, 1070, "信用评价与 CRI 构造流程", "分类器输出被严格解释为评级概率；本文不将其标注为已校准违约概率")
    sections = [(70, 180, 530, 860), (570, 180, 1130, 860), (1170, 180, 1700, 860), (1740, 180, 2280, 860)]
    labels = [("共同特征", BLUE), ("折外训练", TEAL), ("融合映射", ORANGE), ("边界说明", PURPLE)]
    for xy, (label, color) in zip(sections, labels):
        draw.rounded_rectangle(xy, radius=34, fill=PANEL, outline="#D6E0EB", width=2)
        section_label(draw, (xy[0] + 20, xy[1] + 22, xy[2] - 20, xy[1] + 82), label, color)
    round_card(draw, (110, 330, 490, 500), "#FFFFFF", "32 维发票经营特征", "销项、进项、作废率、\n集中度与时间结构", accent=BLUE, title_size=30)
    round_card(draw, (110, 590, 490, 760), "#DCEAF8", "预处理与标准化", "缺失、异常、尺度口径\n仅由训练折拟合", accent=BLUE, title_size=30)
    arrow(draw, (300, 500), (300, 590), BLUE)
    round_card(draw, (610, 295, 1090, 455), NAVY, "Logistic", "线性、可解释的基分类器", accent=ORANGE)
    round_card(draw, (610, 570, 1090, 730), TEAL, "XGBoost", "非线性补充分类器", accent=ORANGE)
    draw.rounded_rectangle((710, 770, 990, 815), radius=16, fill="#FFFFFF")
    text_center(draw, (720, 776, 980, 810), "5 折 OOF 预测", font(23, True), MUTED)
    arrow(draw, (490, 420), (610, 375), BLUE)
    arrow(draw, (490, 680), (610, 650), BLUE)
    round_card(draw, (1210, 310, 1660, 475), ORANGE, "等级概率融合", "w · p_Logistic + (1−w) · p_XGBoost\nw = 0.80", accent=NAVY, title_size=30, body_size=22)
    round_card(draw, (1210, 575, 1660, 740), NAVY, "保序映射 CRI", "评级概率 → [0, 1]\nCRI 越高，信用越好", accent=ORANGE, title_size=30)
    arrow(draw, (1090, 375), (1210, 390), TEAL)
    arrow(draw, (1090, 650), (1210, 650), TEAL)
    arrow(draw, (1435, 475), (1435, 575), ORANGE)
    round_card(draw, (1780, 300, 2240, 475), PURPLE, "可报告结论", "AUC、F1、Kappa 与\n风险方向一致性", accent=ORANGE)
    round_card(draw, (1780, 575, 2240, 760), "#FFFFFF", "不得过度解释", "未做违约率校准；\n不能宣称 PD 置信区间、\n覆盖率或 Bootstrap 上界", accent=PURPLE, title_size=30)
    arrow(draw, (1660, 390), (1780, 390), ORANGE)
    arrow(draw, (1660, 650), (1780, 650), ORANGE)
    draw.rounded_rectangle((260, 915, 2090, 975), radius=20, fill="#E8F4F2", outline="#A7D8CE", width=2)
    text_center(draw, (285, 920, 2065, 970), "证据链：共同字段 → 折外预测 → 融合权重 → 保序 CRI → 独立结果核验", font(28, True), INK)
    im.save(path)


def diagram_three_png(path: Path):
    im, draw = canvas(2350, 1200, "脆弱性驱动的有限情景稳健配置", "以压力测试刻画下行边界；不将三类情景误作连续不确定集或概率分布")
    cols = [(60, 175, 560, 985), (605, 175, 1125, 985), (1170, 175, 1700, 985), (1745, 175, 2290, 985)]
    labels = [("脆弱性", GREEN), ("情景传导", PURPLE), ("授信收益", ORANGE), ("稳健决策", NAVY)]
    for xy, (label, color) in zip(cols, labels):
        draw.rounded_rectangle(xy, radius=34, fill=PANEL, outline="#D6E0EB", width=2)
        section_label(draw, (xy[0] + 20, xy[1] + 22, xy[2] - 20, xy[1] + 82), label, color)
    round_card(draw, (100, 290, 520, 445), GREEN, "六项脆弱性指标", "行业、规模、集中度、\n作废、波动、区域风险", accent=ORANGE, title_size=30)
    round_card(draw, (100, 555, 520, 710), "#FFFFFF", "百分位与主观权重", "标准化后求加权平均\n得到企业脆弱性 Vᵢ", accent=GREEN, title_size=30)
    round_card(draw, (100, 820, 520, 930), "#E8F4EA", "Vᵢ ∈ [0,1]", accent=GREEN, title_size=32)
    arrow(draw, (310, 445), (310, 555), GREEN)
    arrow(draw, (310, 710), (310, 820), GREEN)
    round_card(draw, (645, 285, 1085, 445), PURPLE, "三类有限压力情景", "需求压力 / 供给压力 /\n联合压力", accent=ORANGE, title_size=30)
    round_card(draw, (645, 555, 1085, 730), "#FFFFFF", "风险与留存双通道", "qᵢ,s = min{1, qᵢ + δₛVᵢ}\nretᵢ(r,s) = retᵢ(r)(1−γₛVᵢ)", accent=PURPLE, title_size=27, body_size=21)
    round_card(draw, (645, 820, 1085, 930), "#EEE7F7", "参数由压力口径设定", accent=PURPLE, title_size=28)
    arrow(draw, (865, 445), (865, 555), PURPLE)
    arrow(draw, (865, 730), (865, 820), PURPLE)
    round_card(draw, (1210, 285, 1660, 445), ORANGE, "统一的授信变量", "额度 xᵢ、利率 r、\n准入与预算约束", accent=NAVY, title_size=30)
    round_card(draw, (1210, 555, 1660, 730), NAVY, "情景单位收益", "利息收入 − 预期损失\n− 流失造成的收益折减", accent=ORANGE, title_size=30)
    round_card(draw, (1210, 820, 1660, 930), "#FFF0E4", "组合风险约束", accent=ORANGE, title_size=30)
    arrow(draw, (1435, 445), (1435, 555), ORANGE)
    arrow(draw, (1435, 730), (1435, 820), ORANGE)
    round_card(draw, (1785, 285, 2250, 445), NAVY, "有限情景最大最小", "max  minₛ Πₛ(x, r)\n选择最坏情景收益最大的方案", accent=PURPLE, title_size=30, body_size=22)
    round_card(draw, (1785, 555, 2250, 730), "#FFFFFF", "可行性优先", "原风险上限不可行时，\n先报告最小可行风险阈值", accent=NAVY, title_size=30)
    round_card(draw, (1785, 820, 2250, 930), "#E5EDF6", "报告：下行边界与管理建议", accent=NAVY, title_size=28)
    arrow(draw, (2017, 445), (2017, 555), NAVY)
    arrow(draw, (2017, 730), (2017, 820), NAVY)
    arrow(draw, (520, 635), (645, 635), GREEN)
    arrow(draw, (1085, 635), (1210, 635), PURPLE)
    arrow(draw, (1660, 635), (1785, 635), ORANGE)
    draw.rounded_rectangle((250, 1050, 2110, 1115), radius=20, fill="#FFF3E5", outline="#F2C58B", width=2)
    text_center(draw, (275, 1056, 2085, 1110), "边界：当前模型是有限情景压力测试 + 稳健配置；CVaR、相关违约、分布鲁棒优化等属于后续扩展方向", font(26, True), INK)
    im.save(path)


def svg_text(x, y, text, size=26, fill=INK, weight="400", anchor="middle"):
    lines = text.split("\n")
    spans = "".join(f'<tspan x="{x}" dy="{0 if i == 0 else size * 1.3}">{line}</tspan>' for i, line in enumerate(lines))
    return f'<text x="{x}" y="{y}" font-family="Microsoft YaHei, Noto Sans CJK SC, sans-serif" font-size="{size}" font-weight="{weight}" fill="{fill}" text-anchor="{anchor}">{spans}</text>'


def write_svg(path: Path, title: str, subtitle: str, groups, width=2400, height=1200):
    parts = [f'''<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" viewBox="0 0 {width} {height}">
<defs><marker id="a" markerWidth="12" markerHeight="12" refX="10" refY="6" orient="auto"><path d="M0,0 L12,6 L0,12 z" fill="{BLUE}"/></marker><filter id="s"><feDropShadow dx="5" dy="7" stdDeviation="5" flood-color="#9BAABA" flood-opacity=".36"/></filter></defs>
<rect width="100%" height="100%" fill="white"/><rect width="100%" height="118" fill="#EEF4FA"/><rect y="112" width="100%" height="6" fill="{ORANGE}"/>
{svg_text(width/2, 55, title, 46, NAVY, "700")}{svg_text(width/2, 98, subtitle, 23, MUTED)}''']
    for group in groups:
        parts.append(group)
    parts.append("</svg>")
    path.write_text("\n".join(parts), encoding="utf-8")


def rect(x1, y1, x2, y2, fill, label, body="", label_size=28):
    foreground = "#FFFFFF" if fill in {NAVY, BLUE, TEAL, GREEN, ORANGE, PURPLE} else INK
    center = (x1 + x2) / 2
    content = f'<rect x="{x1}" y="{y1}" width="{x2-x1}" height="{y2-y1}" rx="28" fill="{fill}" stroke="#FFFFFF" stroke-width="2" filter="url(#s)"/>'
    content += svg_text(center, y1 + 58 if body else (y1+y2)/2+10, label, label_size, foreground, "700")
    if body:
        content += svg_text(center, y1 + 112, body, 22, foreground)
    return content


def svg_arrow(x1, y1, x2, y2, color=BLUE):
    return f'<line x1="{x1}" y1="{y1}" x2="{x2}" y2="{y2}" stroke="{color}" stroke-width="8" marker-end="url(#a)"/>'


def make_svgs():
    groups1 = []
    for x, label, color in [(55, "数据基础", BLUE), (620, "信用评价", TEAL), (1215, "授信配置", ORANGE), (1815, "压力决策", PURPLE)]:
        groups1.append(f'<rect x="{x}" y="180" width="530" height="950" rx="34" fill="{PANEL}" stroke="#D6E0EB" stroke-width="2"/>')
        groups1.append(f'<rect x="{x+22}" y="204" width="486" height="60" rx="18" fill="{color}"/>{svg_text(x+265, 245, label, 25, "#FFFFFF", "700")}')
    groups1 += [
        rect(95, 315, 545, 490, "#FFFFFF", "企业与发票信息", "销项 / 进项发票\n信贷记录与信誉评价"),
        rect(95, 575, 545, 750, "#DCEAF8", "共同字段筛选", "仅保留两批企业均可获得的\n发票经营特征"),
        rect(95, 835, 545, 1010, "#FFFFFF", "特征账本", "口径、来源、时间窗口均留痕"),
        rect(660, 300, 1140, 475, NAVY, "OOF 评级概率", "Logistic + XGBoost\n5 折折外预测"),
        rect(660, 560, 1140, 735, TEAL, "等级概率融合", "权重 w = 0.80\n经保序映射得到 CRI"),
        rect(660, 820, 1140, 1005, "#FFFFFF", "跨样本外推与漂移诊断", "冻结源样本管线；检查均值漂移、\n尾部越界与阈值敏感性", 26),
        rect(1255, 300, 1740, 475, ORANGE, "利率需求响应", "企业级保序回归\n利率—流失率曲线"),
        rect(1255, 560, 1740, 735, NAVY, "组合授信 MIP", "额度、利率、预算、评级\n与组合风险约束"),
        rect(1255, 820, 1740, 1005, "#FFFFFF", "可行性与角点解释", "先检验风险约束可行性；\n线性收益下的上限额度需说明", 26),
        rect(1855, 300, 2305, 475, PURPLE, "脆弱性量化", "六项风险指标\n百分位与主观权重融合"),
        rect(1855, 560, 2305, 735, PURPLE, "三类有限压力情景", "需求 / 供给 / 联合压力\n经风险与留存通道传导", 26),
        rect(1855, 820, 2305, 1005, NAVY, "有限情景最大最小配置", "以最坏情景收益为准；\n情景不是概率分布假设", 26),
        svg_arrow(320, 490, 320, 575), svg_arrow(320, 750, 320, 835), svg_arrow(900, 475, 900, 560, TEAL), svg_arrow(900, 735, 900, 820, TEAL),
        svg_arrow(1498, 475, 1498, 560, ORANGE), svg_arrow(1498, 735, 1498, 820, ORANGE), svg_arrow(2080, 475, 2080, 560, PURPLE), svg_arrow(2080, 735, 2080, 820, PURPLE),
        svg_arrow(545, 660, 660, 660), svg_arrow(1140, 650, 1255, 650, TEAL), svg_arrow(1740, 650, 1855, 650, ORANGE),
        '<rect x="220" y="1190" width="1960" height="65" rx="22" fill="#FFF3E5" stroke="#F2C58B" stroke-width="2"/>' + svg_text(1200, 1233, "输出：风险排序、授信方案、下行边界与可复现证据（不将成熟算法组合表述为新算法）", 27, INK, "700"),
    ]
    write_svg(FIG / "figure1_evidence_constrained_credit_flow.svg", "中小微企业信贷决策的证据约束流程", "共同特征外推 · 利率需求响应 · 有限情景稳健配置", groups1, 2400, 1330)
    # SVGs for figures 2 and 8 deliberately preserve the same visual grammar and editable text boxes.
    groups2 = [
        rect(110, 330, 490, 500, "#FFFFFF", "32 维发票经营特征", "销项、进项、作废率、\n集中度与时间结构", 29),
        rect(110, 590, 490, 760, "#DCEAF8", "预处理与标准化", "缺失、异常、尺度口径\n仅由训练折拟合", 29),
        rect(610, 295, 1090, 455, NAVY, "Logistic", "线性、可解释的基分类器"),
        rect(610, 570, 1090, 730, TEAL, "XGBoost", "非线性补充分类器"),
        rect(1210, 310, 1660, 475, ORANGE, "等级概率融合", "w · p_Logistic + (1−w) · p_XGBoost\nw = 0.80", 28),
        rect(1210, 575, 1660, 740, NAVY, "保序映射 CRI", "评级概率 → [0, 1]\nCRI 越高，信用越好", 29),
        rect(1780, 300, 2240, 475, PURPLE, "可报告结论", "AUC、F1、Kappa 与\n风险方向一致性", 29),
        rect(1780, 575, 2240, 760, "#FFFFFF", "不得过度解释", "未做违约率校准；不能宣称\nPD 置信区间、覆盖率或\nBootstrap 上界", 28),
        svg_arrow(300, 500, 300, 590), svg_arrow(490, 420, 610, 375), svg_arrow(490, 680, 610, 650), svg_arrow(1090, 375, 1210, 390, TEAL), svg_arrow(1090, 650, 1210, 650, TEAL), svg_arrow(1435, 475, 1435, 575, ORANGE), svg_arrow(1660, 390, 1780, 390, ORANGE), svg_arrow(1660, 650, 1780, 650, ORANGE),
        '<rect x="260" y="915" width="1830" height="60" rx="20" fill="#E8F4F2" stroke="#A7D8CE" stroke-width="2"/>' + svg_text(1175, 955, "证据链：共同字段 → 折外预测 → 融合权重 → 保序 CRI → 独立结果核验", 28, INK, "700"),
    ]
    write_svg(FIG / "figure2_cri_construction_flow.svg", "信用评价与 CRI 构造流程", "分类器输出被严格解释为评级概率；本文不将其标注为已校准违约概率", groups2, 2350, 1070)
    groups3 = [
        rect(100, 290, 520, 445, GREEN, "六项脆弱性指标", "行业、规模、集中度、\n作废、波动、区域风险", 29),
        rect(100, 555, 520, 710, "#FFFFFF", "百分位与主观权重", "标准化后求加权平均\n得到企业脆弱性 Vᵢ", 29),
        rect(100, 820, 520, 930, "#E8F4EA", "Vᵢ ∈ [0,1]", "", 31),
        rect(645, 285, 1085, 445, PURPLE, "三类有限压力情景", "需求压力 / 供给压力 /\n联合压力", 29),
        rect(645, 555, 1085, 730, "#FFFFFF", "风险与留存双通道", "qᵢ,s = min{1, qᵢ + δₛVᵢ}\nretᵢ(r,s) = retᵢ(r)(1−γₛVᵢ)", 27),
        rect(645, 820, 1085, 930, "#EEE7F7", "参数由压力口径设定", "", 27),
        rect(1210, 285, 1660, 445, ORANGE, "统一的授信变量", "额度 xᵢ、利率 r、\n准入与预算约束", 29),
        rect(1210, 555, 1660, 730, NAVY, "情景单位收益", "利息收入 − 预期损失\n− 流失造成的收益折减", 29),
        rect(1210, 820, 1660, 930, "#FFF0E4", "组合风险约束", "", 29),
        rect(1785, 285, 2250, 445, NAVY, "有限情景最大最小", "max  minₛ Πₛ(x, r)\n选择最坏情景收益最大的方案", 28),
        rect(1785, 555, 2250, 730, "#FFFFFF", "可行性优先", "原风险上限不可行时，\n先报告最小可行风险阈值", 29),
        rect(1785, 820, 2250, 930, "#E5EDF6", "报告：下行边界与管理建议", "", 27),
        svg_arrow(310, 445, 310, 555, GREEN), svg_arrow(310, 710, 310, 820, GREEN), svg_arrow(865, 445, 865, 555, PURPLE), svg_arrow(865, 730, 865, 820, PURPLE), svg_arrow(1435, 445, 1435, 555, ORANGE), svg_arrow(1435, 730, 1435, 820, ORANGE), svg_arrow(2017, 445, 2017, 555, NAVY), svg_arrow(2017, 730, 2017, 820, NAVY), svg_arrow(520, 635, 645, 635, GREEN), svg_arrow(1085, 635, 1210, 635, PURPLE), svg_arrow(1660, 635, 1785, 635, ORANGE),
        '<rect x="250" y="1050" width="1860" height="65" rx="20" fill="#FFF3E5" stroke="#F2C58B" stroke-width="2"/>' + svg_text(1180, 1093, "边界：有限情景压力测试 + 稳健配置；CVaR、相关违约、分布鲁棒优化属于后续扩展方向", 26, INK, "700"),
    ]
    write_svg(FIG / "figure8_finite_scenario_robust_flow.svg", "脆弱性驱动的有限情景稳健配置", "以压力测试刻画下行边界；不将三类情景误作连续不确定集或概率分布", groups3, 2350, 1200)


def para_text(p):
    return "".join(p.xpath(".//w:t/text()", namespaces=NS))


def set_para_text(p, text):
    ts = p.xpath(".//w:t", namespaces=NS)
    if not ts:
        run = etree.SubElement(p, QN("r"))
        ts = [etree.SubElement(run, QN("t"))]
    ts[0].text = text
    for t in ts[1:]:
        t.text = ""


def clone_after(anchor, text):
    new_p = copy.deepcopy(anchor)
    set_para_text(new_p, text)
    anchor.addnext(new_p)
    return new_p


def clone_after_from(prototype, anchor, text):
    new_p = copy.deepcopy(prototype)
    set_para_text(new_p, text)
    anchor.addnext(new_p)
    return new_p


def page_break_before(p):
    ppr = p.find(QN("pPr"))
    if ppr is None:
        ppr = etree.Element(QN("pPr"))
        p.insert(0, ppr)
    if ppr.find(QN("pageBreakBefore")) is None:
        ppr.append(etree.Element(QN("pageBreakBefore")))


def first_paragraph(paragraphs, prefix):
    normalized_prefix = "".join(prefix.split())
    for p in paragraphs:
        normalized_text = "".join(para_text(p).split())
        if normalized_text.startswith(normalized_prefix):
            return p
    raise RuntimeError(f"missing paragraph: {prefix}")


def replace_all(p, old, new):
    current = para_text(p)
    if old not in current:
        raise RuntimeError(f"expected text not found: {old}")
    set_para_text(p, current.replace(old, new))


def update_document_xml(data: bytes) -> bytes:
    root = etree.fromstring(data)
    body = root.find(QN("body"))
    paragraphs = body.xpath("./w:p", namespaces=NS)
    # Remove the table of contents entirely and let Chapter 1 start on a fresh page.
    toc_start = first_paragraph(paragraphs, "目 录")
    chapter_one_candidates = [
        p for p in paragraphs
        if "".join(para_text(p).split()).startswith("".join("1  问题重述与总体分析".split()))
    ]
    if len(chapter_one_candidates) != 2:
        raise RuntimeError("could not distinguish the directory entry from Chapter 1")
    chapter_one = chapter_one_candidates[-1]
    start_i, end_i = paragraphs.index(toc_start), paragraphs.index(chapter_one)
    for p in paragraphs[start_i:end_i]:
        body.remove(p)
    page_break_before(chapter_one)

    paragraphs = body.xpath("./w:p", namespaces=NS)
    set_para_text(first_paragraph(paragraphs, "信用风险迁移、利率需求响应"), "共同特征跨样本外推、利率需求响应与有限情景稳健配置的信贷决策框架")
    replace_all(first_paragraph(paragraphs, "关键词："), "信用风险迁移", "共同特征外推")

    p = first_paragraph(paragraphs, "对问题二，附件2企业")
    set_para_text(p, "问题二：对无信贷记录企业，本文将问题一中固定的共同字段处理、评级概率融合与保序映射管线直接外推至目标样本，并以漂移诊断与人工复核控制应用风险。该设计只保证输入字段的一致性，不引入领域自适应、重要性加权、目标域校准或半监督适配，因此不将其表述为新的迁移学习算法。")
    p = first_paragraph(paragraphs, "图1  中小微企业信贷决策")
    set_para_text(p, "图1  中小微企业信贷决策的整体方法学流程图。图中展示从企业与发票信息输入、信用风险评价和共同特征外推，到压力情景下有限情景稳健决策与解释检验的求解链。图形制作说明：流程结构与视觉版式曾使用生成式 AI 辅助构思，作者依据本文模型、公式与复现结果人工矢量重绘，未使用带水印生成图像；工具与复核说明见附录B及文献[9]。")

    replace_all(first_paragraph(paragraphs, "5  问题二："), "风险迁移", "共同特征跨样本外推")
    replace_all(first_paragraph(paragraphs, "5.1  冻结模型"), "冻结模型迁移", "冻结模型外推")
    p = first_paragraph(paragraphs, "问题二不重新拟合分类器")
    set_para_text(p, "问题二面向无信贷记录企业。本文冻结问题一的共同字段处理、评级概率融合和 CRI 映射，在目标企业上作跨样本外推；同时检查源、目标样本的特征漂移与尾部越界。这里的“外推”仅指在同一特征口径下使用既有模型，并不等同于领域自适应或概率校准迁移。")
    p = first_paragraph(paragraphs, "主要变量的源域")
    set_para_text(p, "跨样本外推的合理性与边界：附件一、附件二共享企业发票记录及其可构造经营特征。为避免使用目标企业不可得的人工信誉评级等信息，本文仅以共同字段作为模型输入；这提高了应用合理性，但不证明目标域已被适配。因而结果应解释为保守的风险排序与授信配置依据，而非经过校准的目标域违约概率。")
    p = first_paragraph(paragraphs, "绝对漂移最大的变量")
    set_para_text(p, "外推检验采用均值漂移、极端范围越界与阈值敏感性三类可复核证据。当前结果只说明未观察到均值层面的外推反证，不构成目标域准确率、覆盖率或概率校准的证明；因此仍保留 OOD 标记和人工复核机制。")

    p = first_paragraph(paragraphs, "第一，标签语义清晰")
    set_para_text(p, "本文的价值不在于提出新的分类器、整数规划算法或稳健优化理论，而在于把共同字段约束、信用风险评价、利率流失响应、组合授信配置和压力检验组织为一条可复核的决策链。其贡献属于应用整合与建模流程创新：")
    anchor = p
    for text in [
        "（1）共同字段约束：主动舍弃目标企业不可得的人工信誉评级，仅使用两批企业共有的发票经营特征，避免将不可迁移字段作为“捷径”。",
        "（2）风险—流失—授信联动：在风险排序之外，联动考虑利率引起的客户流失、额度与组合风险约束，回答“给谁贷、贷多少、收多少利率”的业务问题。",
        "（3）可行性先行：在压力情景下先检验风险上限的可行性；若原约束不可行，明确报告最小可行阈值及降低预算、增加担保或改善回收率等管理路径。",
    ]:
        anchor = clone_after(anchor, text)

    p = first_paragraph(body.xpath("./w:p", namespaces=NS), "源域仅有123家企业")
    set_para_text(p, "模型局限性：第一，信用评价使用的分类器和 CRI 映射服务于等级排序，本文未进行违约率校准，不能把其表述为严格的违约概率或置信上界。第二，共同字段外推未采用重要性加权、领域自适应、对抗式迁移、迁移校准、半监督学习或层次贝叶斯迁移模型；漂移识别、保守配置与人工复核是风险控制措施，而不是完整的目标域适配。第三，压力参数、回收率等仍含决策假设，应随业务数据更新。")
    p = first_paragraph(body.xpath("./w:p", namespaces=NS), "额度收益按贷款金额")
    set_para_text(p, "从优化结构看，授信配置是把风险排序和利率响应嵌入业务约束的标准混合整数规划；线性收益结构会使部分企业取额度上限，属于可解释的角点解而非新的优化性质。问题三采用有限情景下的最大最小配置，适合称为“情景压力测试+稳健配置”；本文未构造连续不确定集、CVaR、相关违约、机会约束或 Wasserstein 分布鲁棒优化，因此不宣称稳健优化理论创新。")
    p = first_paragraph(body.xpath("./w:p", namespaces=NS), "实际部署时")
    set_para_text(p, "后续可进一步：在拥有目标域标签或外部验证样本后，补充概率校准、覆盖率与稳定性检验；对跨样本外推，引入重要性加权、层次贝叶斯或领域自适应并作消融比较；对组合风险，引入 CVaR、相关违约、回收率与预算不确定性，或以分布鲁棒优化扩展有限情景压力测试。")
    replace_all(first_paragraph(body.xpath("./w:p", namespaces=NS), "本文以发票经营行为"), "风险迁移", "共同特征跨样本外推")
    replace_all(first_paragraph(body.xpath("./w:p", namespaces=NS), "问题二将问题一冻结模型"), "冻结模型迁移", "冻结的共同字段融合管线外推")
    p = first_paragraph(body.xpath("./w:p", namespaces=NS), "上述结果表明")
    set_para_text(p, "本文的主要贡献并非提出新的基础算法，而是形成了一套共同字段约束下、可解释、可复核且能够显式报告可行性边界的授信决策流程。分类、保序回归、混合整数规划与有限情景最大最小配置均为成熟工具；本文的创新定位是这些工具在风险、流失、额度和压力约束之间的应用整合。")
    paragraphs = body.xpath("./w:p", namespaces=NS)
    ref_heading = first_paragraph(paragraphs, "附录B 参考文献")
    set_para_text(ref_heading, "附录C 参考文献")
    appendix_anchor = ref_heading
    appendix_heading = copy.deepcopy(ref_heading)
    set_para_text(appendix_heading, "附录B 生成式 AI 辅助使用与人工复核说明")
    ref_heading.addprevious(appendix_heading)
    ai_texts = [
        "1. 使用范围：本稿修订中使用 OpenAI Codex [9] 辅助进行任务组织、文字表述核对和流程图版式构思。它不作为数据来源，也不替代作者对模型、参数、代码或研究结论的判断。",
        "2. 图形处理：图1、图2和图8的最终流程图由作者依据本文模型、公式与复现结果人工重绘为可编辑 SVG，并导出嵌入文档；未直接采用带水印的生成式图像。",
        "3. 人工复核：所有数据口径、特征定义、模型设置、运行结果、图表数值和结论均由作者结合项目代码与复现输出逐项核对。当前可复现运行的核心结果记录于附录A；生成式 AI 输出不构成研究证据。",
    ]
    normal_prototype = first_paragraph(body.xpath("./w:p", namespaces=NS), "本文的主要贡献并非")
    anchor = appendix_heading
    for text in ai_texts:
        anchor = clone_after_from(normal_prototype, anchor, text)

    # Add a transparent, citable reference entry after existing references.
    paragraphs = body.xpath("./w:p", namespaces=NS)
    last_ref = paragraphs[-2] if paragraphs[-1].tag == QN("sectPr") else paragraphs[-1]
    clone_after(last_ref, "[9] OpenAI. Codex Documentation [EB/OL]. https://help.openai.com/en/collections/14937394-codex, 2026-09-04.")
    return etree.tostring(root, xml_declaration=True, encoding="UTF-8", standalone=True)


def build_docx():
    make_svgs()
    pngs = {
        "word/media/image1.png": FIG / "figure1_evidence_constrained_credit_flow.png",
        "word/media/image2.png": FIG / "figure2_cri_construction_flow.png",
        "word/media/image8.png": FIG / "figure8_finite_scenario_robust_flow.png",
    }
    diagram_one_png(pngs["word/media/image1.png"])
    diagram_two_png(pngs["word/media/image2.png"])
    diagram_three_png(pngs["word/media/image8.png"])
    OUT.parent.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(SOURCE, "r") as zin, zipfile.ZipFile(OUT, "w", zipfile.ZIP_DEFLATED) as zout:
        for info in zin.infolist():
            payload = zin.read(info.filename)
            if info.filename == "word/document.xml":
                payload = update_document_xml(payload)
            elif info.filename in pngs:
                payload = pngs[info.filename].read_bytes()
            zout.writestr(info, payload)
    print(OUT)


if __name__ == "__main__":
    build_docx()
