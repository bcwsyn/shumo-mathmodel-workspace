#let body-font = ("Times New Roman", "SimSun", "NSimSun", "STSong")
#let song-font = ("SimSun", "NSimSun", "STSong", "Times New Roman")
#let hei-font = ("SimHei", "Microsoft YaHei", "SimSun")
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

#set document(
  title: "FAST 主动反射面形状调节的约束优化与接收性能分析",
  author: (),
)
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
#set enum(numbering: "1.")
#set table(inset: 0.42em)
#set math.equation(numbering: "(1)")
#show heading.where(level: 1): set align(center)
#show heading.where(level: 1): set text(size: 17.3pt, weight: "bold")
#show heading.where(level: 1): set block(above: 1.25em, below: 0.82em)
#show heading.where(level: 2): set text(size: 14.45pt, weight: "bold")
#show heading.where(level: 2): set block(above: 1.05em, below: 0.5em)
#show heading.where(level: 3): set text(size: 12.05pt, weight: "bold")
#show heading.where(level: 3): set block(above: 0.95em, below: 0.45em)
#show figure.caption: set text(size: 11pt, weight: "bold")
#show figure.where(kind: table): set figure.caption(position: top)
#show raw: set text(size: 8.5pt, font: ("Courier New", "Consolas", "SimSun"))
#show raw.where(block: true): set block(
  fill: luma(97%),
  stroke: 0.6pt + luma(72%),
  inset: 0.55em,
  above: 0.55em,
  below: 0.55em,
  breakable: true,
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
  block(above: 0.15em)[#body]
  keywords-cn(keywords)
  pagebreak()
}
#let references-cn() = [
  #heading(numbering: none, outlined: true)[参考文献]
  #{ set par(first-line-indent: 0pt, spacing: 0.38em); include("references.typ") }
]
#let appendix-cn(file: "sections/A_code.typ") = [
  #heading(numbering: none, outlined: true)[附录]
  #[
    #set heading(numbering: none)
    #include(file)
  ]
]

#counter(page).update(1)

#paper-title[FAST 主动反射面形状调节的约束优化与接收性能分析]

#abstract-cn[
  FAST 通过促动器带动索网节点，使局部球面在观测方向上形成近似旋转抛物面。其调节过程同时受促动器行程、下拉索定长和主索长度变化约束，理想面几何与工程可实现性不能分开处理。本文建立“理想面选择—严格可行调节—有限面板接收评价”的统一模型。

  对问题一，固定馈源焦点，在一参数旋转抛物面族中比较几何焦距、面积加权最小二乘焦距和硬件友好焦距，以促动器与主索最大归一化占用率为选择准则。正上方观测时得到硬件友好焦距 $140.325121 "m"$；理想节点直接投影的主索占用率为上限的 $1.5815$ 倍，说明必须进一步求可行工作面。

  对问题二，以 692 个工作区节点的径向位移为变量，建立面积加权平方贴合目标和 2165 条相关主索、692 个促动器的精确约束。采用三个严格可行起点的顺序凸化方法，并在每个候选步后回代原始非线性几何；随后在均方误差容差内精修最大节点误差。指定观测方向下，理想抛物面顶点为 $(-49.375757,-36.931066,-294.350722) "m"$。最终节点贴合理想面的均方根误差为 $0.062858 "m"$，最大主索相对变化为 $0.069999226%$，最大促动器绝对伸缩量为 $0.249123 "m"$，全部硬约束均满足。

  对问题三，将每块三角面板作确定性等面积细分，以三顶点平面法向计算镜面反射，并按入射投影面积加权。64 阶细分下，基准球面和调节工作面的接收比分别为 $0.00811012$ 和 $0.01075298$，工作面相对提高 $32.5872%$。从 32 阶增加到 64 阶时，工作面接收比仅变化 $1.40 times 10^(-5)$；改变投影口径半径和面板权重后，提升方向保持一致。结果表明，严格可行调节虽受主索约束主导，仍能稳定改善有限馈源条件下的接收性能。
][
  FAST #h(1em) 主动反射面 #h(1em) 顺序凸化 #h(1em) 几何光学 #h(1em) 射线追踪
]

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
