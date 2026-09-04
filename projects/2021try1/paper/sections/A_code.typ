== 附录 A：支撑材料文件清单

支撑材料建议包含以下内容：

+ `code/`：全部 Python 源程序；
+ `tests/`：正常、边界和失败输入测试；
+ `data/raw/`：题目附件的只读数值副本；
+ `results/result.xlsx`：题目要求的三工作表结果文件；
+ `results/`：正式优化、约束回代、射线收敛和敏感性表；
+ `figures/`：论文使用的数据图 PDF 与可编辑流程图源文件；
+ `README.md`：解释器、依赖和一键复现命令。

所有文件名、文件夹名和文档属性均不得包含参赛者、学校或赛区身份信息。

== 附录 B：完整源程序

以下代码与支撑材料中的源文件保持一致。为控制正文篇幅，程序只在附录出现。

=== 几何、数据与约束模块

==== `fast_geometry.py`

#raw(read("../support/code/fast_geometry.py"), lang: "python", block: true)

=== 问题一至问题三基础模块

==== `problem1.py`

#raw(read("../support/code/problem1.py"), lang: "python", block: true)

==== `problem2.py`

#raw(read("../support/code/problem2.py"), lang: "python", block: true)

==== `problem3.py`

#raw(read("../support/code/problem3.py"), lang: "python", block: true)

=== 正式约束优化与射线追踪

==== `optimization.py`

#raw(read("../support/code/optimization.py"), lang: "python", block: true)

==== `raytrace.py`

#raw(read("../support/code/raytrace.py"), lang: "python", block: true)

=== 正式实验与绘图入口

==== `g3_run.py`

#raw(read("../support/code/g3_run.py"), lang: "python", block: true)

==== `g3_plot.py`

#raw(read("../support/code/g3_plot.py"), lang: "python", block: true)

=== 最小验证入口

==== `g2_smoke.py`

#raw(read("../support/code/g2_smoke.py"), lang: "python", block: true)

==== `g2_plot.py`

#raw(read("../support/code/g2_plot.py"), lang: "python", block: true)
