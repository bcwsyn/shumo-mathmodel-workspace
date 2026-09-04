= 问题二：严格可行工作面优化

== 指定方向的理想目标

对 $alpha=36.795 degree,beta=78.169 degree$ 重新构造 $bold(u),bold(k),bold(P)$ 和投影口径。离散节点分布相对观测轴并非严格旋转对称，因此不能简单旋转问题一的数值结果，而应使用同一硬件友好准则重新搜索焦距。

指定方向下得到

$ f_2^star=140.325843 "m", $

$ bold(V)_2=(-49.375757,-36.931066,-294.350722) "m". $

投影口径内有 692 个活动节点，与它们关联的主索为 2165 条，其中包含跨口径边界的主索。理想目标本身的最大促动器伸缩量为 $0.338250 "m"$，但最大主索相对变化为 $0.110593%$，超过 $0.07%$ 上限，因此进入约束工作面优化。

== 优化模型

决策变量为活动节点的径向位移 $bold(y)=(y_i)_(i in cal(I))$。口径外节点固定为零。第一阶段最小化面积加权贴合误差

$ min_bold(y) J(bold(y))=
frac(sum_(i in cal(I)) w_i(y_i-y_i^star)^2,sum_(i in cal(I)) w_i). $ <eq:l2-objective>

对每个活动节点，促动器连续根必须存在且满足

$ -0.6<=sigma_i(y_i)<=0.6. $ <eq:stroke-limit>

对所有与活动节点关联的主索，要求

$ (1-epsilon)l_(i j)
<=norm(bold(x)_i-y_i bold(n)_i-bold(x)_j+y_j bold(n)_j)
<=(1+epsilon)l_(i j), $ <eq:edge-limit>

其中跨边界端点的 $y_j=0$。约束 @eq:stroke-limit 和 @eq:edge-limit 均在调整后坐标上精确计算，而不是只检查线性化子问题。

得到最优加权误差 $J^star$ 后，在

$ J(bold(y))<=J^star(1+10^(-6))+10^(-12) $

条件下求

$ min_(bold(y),z) z, quad abs(y_i-y_i^star)<=z, $

从而在几乎不损失平均贴合度的前提下降低最坏节点误差。

== 多起点顺序凸化

直接目标位移不可行，而零位移基准球面严格可行。首先沿目标射线二分求最大可行缩放比例，再构造零位移、半缩放目标和最大可行缩放目标三个起点。对每个起点重复以下过程：

+ 在当前严格可行点处，对主索长度和促动器映射作一阶线性化；
+ 在信赖域内求解稀疏凸二次子问题；
+ 把候选位移代回下拉索、促动器和主索的原始非线性几何；
+ 若候选严格可行且目标下降，则接受步长；否则回溯并缩小信赖域；
+ 当最大位移步长或目标改进低于阈值时停止。

该流程如 @fig:optimization-flow 所示。凸子问题由 CVXPY 建模，L2 阶段使用 OSQP 求解；L∞ 精修使用锥优化后端。求解器状态只用于诊断，最终可行性以原始几何回代为准。

#figure(
  image("../figures/fig_flow_optimization.pdf", width: 96%),
  caption: [严格可行顺序凸化与二阶段精修流程],
) <fig:optimization-flow>

== 调节结果

三个起点均得到可行迭代序列，其中零位移起点的 L2 目标最小。正式结果见 @tab:q2-summary。

#figure(
  table(
    columns: (1.45fr, 1fr, 1.45fr, 1fr),
    align: (left, right, left, right),
    stroke: none,
    table.hline(y: 0, stroke: 0.8pt),
    table.hline(y: 1, stroke: 0.5pt),
    table.header([*指标*], [*数值*], [*指标*], [*数值*]),
    [面积加权 MSE/$"m"^2$], [0.00395116], [RMSE/m], [0.062858],
    [最大节点误差/m], [0.132109], [活动节点数], [692],
    [位移最小值/m], [-0.249123], [位移最大值/m], [0.210278],
    [伸缩最小值/m], [-0.249123], [伸缩最大值/m], [0.210278],
    [促动器占用率], [0.415206], [主索占用率], [0.999988950],
    table.hline(stroke: 0.8pt),
  ),
  caption: [指定方向下严格可行工作面的主要结果],
) <tab:q2-summary>

图 @fig:displacement-stroke 左图把理想目标和约束优化后的实际位移按离轴距离排列。中部节点基本贴合理想面，而靠近口径边缘的节点需要偏离目标以保护跨边界主索。右图显示促动器伸缩量集中在约 $-0.25$ 至 $0.21 "m"$，远未触碰 $plus.minus 0.6 "m"$ 行程上限。

#figure(
  image("../figures/displacement_and_stroke.pdf", width: 96%),
  caption: [理想/实际节点位移与促动器伸缩量分布],
) <fig:displacement-stroke>

全部 2165 条相关主索均逐条回代。按绝对相对变化排序的最紧五条边见 @tab:tight-edges。

#figure(
  table(
    columns: (1fr, 1fr, 1.25fr, 1.25fr),
    align: center,
    stroke: none,
    table.hline(y: 0, stroke: 0.8pt),
    table.hline(y: 1, stroke: 0.5pt),
    table.header([*左节点*], [*右节点*], [*相对变化/%*], [*绝对变化/%*]),
    [A94], [A95], [0.069999226], [0.069999226],
    [A93], [A94], [0.069999221], [0.069999221],
    [D265], [D266], [0.069999195], [0.069999195],
    [D163], [D164], [-0.069999194], [0.069999194],
    [D152], [D170], [-0.069999193], [0.069999193],
    table.hline(stroke: 0.8pt),
  ),
  caption: [最接近主索变化上限的五条边],
) <tab:tight-edges>

图 @fig:constraint-usage 进一步给出全部边的约束占用分布。大量边落在上限附近，说明主索而非促动器是决定工作面形状的活跃约束。最大相对变化为 $0.069999226%<0.07%$，仍位于允许范围内。

#figure(
  image("../figures/constraint_usage.pdf", width: 96%),
  caption: [相关主索绝对相对长度变化及分布],
) <fig:constraint-usage>

最终把理想顶点、692 个调整后节点坐标和相同顺序的促动器伸缩量写入规定的三张结果表。内部计算保留双精度，表中显示六位小数；写出后重新读取首尾行并核对编号顺序。
