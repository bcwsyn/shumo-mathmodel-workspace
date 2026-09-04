= 问题三：馈源接收比

== 面板反射几何

对基准面或问题二的调节工作面，每块三角面板由三个节点坐标确定。设入射电磁波传播方向为 $bold(d)=bold(k)$，三顶点叉积得到单位法向 $bold(m)$。面板顶点顺序不保证一致，因此把法向统一翻到天体侧，使 $bold(d) dot bold(m)<0$。镜面反射方向为

$ bold(r)=bold(d)-2(bold(d) dot bold(m))bold(m). $ <eq:reflection>

馈源接收平面通过 $bold(P)$，法向为 $bold(u)=-bold(k)$。从面板采样点 $bold(p)$ 出发的反射线与馈源平面交于

$ tau=frac((bold(P)-bold(p)) dot bold(u),bold(r) dot bold(u)), quad
bold(q)_p=bold(p)+tau bold(r). $ <eq:receiver-plane>

只有 $tau>0$ 且

$ norm(bold(q)_p-bold(P))<=0.5 "m" $

时，该采样微单元被有效馈源圆盘接收。

== 确定性面板细分

仅用面板中心会使命中判定对三角形边界过于敏感。本文把每块母三角形作 $m$ 阶等面积细分，共得到 $m^2$ 个微三角形，并以各微三角形重心代表位置。所有微单元沿用母面板法向；跨越 300 m 口径边界的面板按微单元重心是否满足 $rho(bold(p))<=150 "m"$ 部分计入。

微单元 $s$ 的能量权重取入射投影面积

$ omega_s=A_s abs(bold(d) dot bold(m)_s). $

接收比定义为

$ eta=frac(sum_s omega_s cal(I)_s,sum_s omega_s), $ <eq:reception>

其中 $cal(I)_s$ 是由 @eq:receiver-plane 给出的命中指示量。投影面积加权是正式口径，面板等权只用于敏感性对照。整体计算结构见 @fig:ray-model。

#figure(
  image("../figures/fig_model_raytrace.pdf", width: 96%),
  caption: [面板确定性细分与馈源接收比计算结构],
) <fig:ray-model>

== 细分收敛

对基准球面和调节工作面分别取 $m=2,4,8,16,32,64$，结果见 @tab:ray-convergence。

#figure(
  table(
    columns: (1fr, 1.15fr, 1.15fr),
    align: center,
    stroke: none,
    table.hline(y: 0, stroke: 0.8pt),
    table.hline(y: 1, stroke: 0.5pt),
    table.header([*细分阶数 $m$*], [*基准面接收比*], [*工作面接收比*]),
    [2], [0.01558945], [0.02659522],
    [4], [0.01006153], [0.01256800],
    [8], [0.00786994], [0.00781574],
    [16], [0.00800792], [0.01126826],
    [32], [0.00811106], [0.01076696],
    [64], [0.00811012], [0.01075298],
    table.hline(stroke: 0.8pt),
  ),
  caption: [三角面板细分阶数与接收比],
) <tab:ray-convergence>

粗细分时，少量微单元跨过半径 0.5 m 的命中边界会导致比例明显跳动；当 $m$ 增加到 32 和 64 后，两表面均趋于稳定。基准面从 32 阶到 64 阶的变化为 $9.42 times 10^(-7)$，工作面变化为 $1.40 times 10^(-5)$，分别约占最终值的 $0.012%$ 和 $0.130%$。

图 @fig:receiver-results 左图显示收敛过程，右图给出面板中心反射线在馈源平面的落点。调节面在中心附近形成更密集的落点，但由于每块约 10 m 尺度的三角面板仍按一个平面法向反射，而馈源半径仅 0.5 m，所以在本文的有限平面面板模型下，接收比绝对值仍较小。

#figure(
  image("../figures/receiver_results.pdf", width: 96%),
  caption: [细分收敛与馈源平面反射落点],
) <fig:receiver-results>

== 接收比比较

64 阶投影面积加权下，

$ eta_"base"=0.00811012, quad eta_"work"=0.01075298. $

绝对提升为

$ Delta eta=eta_"work"-eta_"base"=0.00264286, $

相对提升为

$ frac(eta_"work"-eta_"base",eta_"base")=32.5872%. $

因此，问题二的严格可行调节在相同离散和能量口径下改善了馈源接收性能。该结论描述的是题目给定几何和本文理想镜面假设下的相对变化，不等同于包含衍射、遮挡和馈源方向图的实际天线效率。
