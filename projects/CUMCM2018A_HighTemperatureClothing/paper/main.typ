#let body-font = ("Times New Roman", "SimSun", "NSimSun", "SimSun", "STSong")
#let song-font = ("SimSun", "NSimSun", "SimSun", "STSong", "Times New Roman")
#let hei-font = ("SimHei", "SimSun", "STSong")
#let kai-font = ("KaiTi", "STKaiti", "SimSun")

#let cn-numbering(..nums) = {
  let ns = nums.pos()
  if ns.len() == 1 {
    numbering("一、", ns.at(0))
  } else if ns.len() == 2 {
    numbering("1.1", ns.at(0), ns.at(1))
  } else {
    numbering("1.1.1", ns.at(0), ns.at(1), ns.at(2))
  }
}

#set document(title: "基于守恒型隐式有限体积法的高温防护服传热标定与稳健厚度优化", author: ())
#set page(
  paper: "a4",
  margin: (top: 2.5cm, bottom: 2.5cm, left: 2.5cm, right: 2.5cm),
  numbering: "1",
)
#set text(font: body-font, size: 12.05pt, lang: "zh")
#set par(
  first-line-indent: (amount: 2em, all: true),
  justify: true,
  leading: 0.72em,
  spacing: 0.35em,
)
#set heading(numbering: cn-numbering)
#set math.equation(numbering: "(1)")
#set enum(numbering: "1.")
#set table(inset: 0.45em)
#show heading.where(level: 1): set align(center)
#show heading.where(level: 1): set text(size: 17.3pt, weight: "bold")
#show heading.where(level: 1): set block(above: 1.25em, below: 0.82em)
#show heading.where(level: 2): set text(size: 14.45pt, weight: "bold")
#show heading.where(level: 2): set block(above: 1.15em, below: 0.55em)
#show heading.where(level: 3): set text(size: 12.05pt, weight: "bold")
#show heading.where(level: 3): set block(above: 1.15em, below: 0.55em)
#show figure.caption: it => text(size: 12pt, weight: "bold")[#it]
#show figure.where(kind: table): set figure.caption(position: top)
#show raw: set text(size: 10pt, font: ("Courier New", "Consolas", "SimSun"))
#show raw.where(block: true): set block(
  fill: luma(97%),
  stroke: 0.8pt + luma(70%),
  inset: 0.7em,
  above: 0.7em,
  below: 0.7em,
)

#let song = (body) => text(font: song-font, body)
#let hei = (body) => text(font: hei-font, weight: "bold", body)
#let kai = (body) => text(font: kai-font, body)
#let paper-title(body) = {
  align(center)[#text(size: 17.3pt, weight: "bold")[#body]]
  v(1em)
}
#let abstract-title() = align(center)[#text(size: 14pt, weight: "bold")[摘要]]
#let keywords-cn(body) = block(above: 1em)[
  #text(font: hei-font, size: 12pt, weight: "bold")[关键字：] #body
]
#let abstract-cn(body, keywords) = {
  abstract-title()
  block(above: 1.0em)[#body]
  keywords-cn(keywords)
  pagebreak()
}
#let toc-page() = {
  show outline.entry.where(level: 1): it => link(
    it.element.location(),
    block(above: 7pt)[
      #text(font: hei-font, size: 12pt, weight: "bold")[
        #grid(
          columns: (auto, 1fr, auto),
          column-gutter: 0.5em,
          [#it.prefix()#it.body()],
          [#repeat[.]],
          [#it.page()],
        )
      ]
    ],
  )
  outline(
    title: align(center)[#text(font: hei-font, size: 17.3pt, weight: "bold")[目录]],
    depth: 2,
  )
  pagebreak()
}
#let references-cn() = [
#heading(numbering: none, outlined: true)[参考文献]
#{ set par(first-line-indent: 0pt, spacing: 0.35em); include("references.typ") }
]
#let appendix-cn(file: "sections/A_code.typ") = [
#heading(numbering: none, outlined: true)[附录 A #h(1em) 核心代码]
#include(file)
]

#let three-line-table(caption, columns, header, body, inset: (x: 0.35em, y: 0.52em), cell-align: center) = {
  let col-count = header.len()
  let body-rows = calc.floor(body.len() / col-count)
  let bottom-y = body-rows + 1
  let styled-header = header.map(cell => strong(cell))

  block(width: 100%, breakable: false)[
    #align(center)[
      #box[
        #align(center)[#text(font: hei-font, size: 10.5pt, weight: "bold")[#caption]]
        #v(0.6em)
        #table(
          columns: columns,
          align: cell-align,
          stroke: none,
          inset: inset,
          table.hline(y: 0, stroke: 0.8pt),
          table.hline(y: 1, stroke: 0.5pt),
          table.hline(y: bottom-y, stroke: 0.8pt),
          ..styled-header,
          ..body,
        )
      ]
    ]
  ]
}

#counter(page).update(1)

#paper-title[基于守恒型隐式有限体积法的高温防护服传热标定与稳健厚度优化]

#abstract-cn[
  
  高温防护服的设计需兼顾瞬态升温、层间传热与边界换热。本文建立一维非稳态热传导模型，以双Robin边界描述外界环境和人体热库的换热作用，层间满足温度和热流连续。空间离散采用界面对齐的有限体积网格，时间推进为全隐式格式，三对角方程组由Thomas追赶法求解。
  
  针对问题一：首先以实验测得的皮肤温度曲线为拟合目标，对外侧和人体侧等效换热系数进行标定，采用分阶段等权最小二乘避免稳态数据主导；然后通过稳态热阻闭式解和多套网格的收敛性检验验证数值格式；最终得到*$h_o=120.991689$*、*$h_b=8.364912 " W"/("m"^2 dot "K")$*，全时段拟合 RMSE 为 *$0.002627 degree"C"$*。能量平衡最大残差为 *$2.34 times 10^(-9) " W"/"m"^2$*，层间热流最大失配为 *$6.31 times 10^(-11) " W"/"m"^2$*，能量平衡残差和界面热流失配均接近机器精度，温度场计算结果与理论稳态值一致。

    针对问题二：固定环境$65 degree"C"$、工作60分钟、第四层厚度5.5 mm，在最高皮肤温度不超过$47 degree"C"$且超过$44 degree"C"$的累计时长不超过300 s的约束下，对第二层 $0.6$--$25.0$ mm范围内的245个离散厚度逐一枚举；然后用细网格复核临界厚度；最终名义最小厚度为*17.6 mm*，此时最高温度 *$44.07684 degree"C"$*，超温时长293.5 s，而相邻更薄档位17.5 mm的超温时长为334.5 s，证实离散最小性。但在定义的联合不利情景下，即使第二层取至上限25.0 mm仍无法满足时长约束，该范围内不存在稳健可行解。

  针对问题三，环境升至 $80 degree"C"$、工作 30 min，第二、四层同时可调，完整扫描 $245 times 59=14,455$个厚度组合，按总厚度最小、同厚度下面密度最小的字典序规则优选；然后用NSGA-II进行20次随机种子交叉验证，其前沿与枚举前沿完全重合；最终名义最优为*$(d_2,d_4)=(19.3,6.4)$ mm*，总厚度 *25.7 m*。在联合 10% 不利情景下，稳健设计为 *$(23.5,6.4)$ mm*，峰值和超温时长仍满足约束。

  整体上，标定后的机理模型配合守恒型离散和低维完全枚举，为防护服厚度设计提供了可追溯的数值基准，并明确区分了名义边界解与考虑不确定性的稳健方案。
][
  高温防护服 #h(1em) 一维非稳态热传导 #h(1em) 隐式有限体积法 #h(1em) Thomas 算法 #h(1em) 厚度枚举优化 #h(1em) 稳健设计
]

#toc-page()

#include("sections/1_restatement.typ")
#include("sections/2_analysis.typ")
#include("sections/3_assumptions.typ")
#include("sections/4_symbols.typ")
#include("sections/5_problem1.typ")
#include("sections/6_problem2.typ")
#include("sections/7_problem3.typ")
#include("sections/8_sensitivity.typ")
#include("sections/9_evaluation.typ")

#pagebreak()
#references-cn()
#pagebreak()
#appendix-cn()
