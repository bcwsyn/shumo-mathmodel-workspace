= 问题一：理想抛物面的确定

== 固定焦点的一参数抛物面

数据恢复的平均基准球半径为 $R=300.400011 "m"$，题面焦面距离参数为 $F=0.466R$。正上方观测时取 $alpha=0 degree,beta=90 degree$，工作面轴 $bold(k)$ 指向反射面一侧，焦点固定为 $bold(P)=(R-F)bold(k)$。

令旋转抛物面的焦距为 $f>0$，顶点沿轴向的半径为

$ v=q+f, quad q=R-F, quad bold(V)=v bold(k). $

在以 $bold(k)$ 为轴的局部坐标中，候选抛物面写为

$ rho(bold(x))^2=4f[v-bold(x) dot bold(k)]. $ <eq:paraboloid>

当 $f=F$ 时有 $v=R$，顶点位于基准球面。固定焦点后只剩焦距 $f$ 一个自由度，避免了同时任意移动焦点和顶点造成的不唯一性。

== 节点目标位移

节点 $i$ 的径向射线记为 $bold(x)=lambda bold(n)_i$。令

$ c_i=bold(n)_i dot bold(k), quad a_i=1-c_i^2, $

把径向射线代入 @eq:paraboloid，得到

$ a_i lambda_i^2+4f c_i lambda_i-4f v=0. $ <eq:radial-root>

从正根中选取最接近基准半径 $R_i$ 的交点。轴线上 $a_i=0$ 时使用线性极限 $lambda_i=v/c_i$。理想目标位移为

$ y_i^star(f)=R_i-lambda_i(f), quad i in cal(I). $

节点面积权重 $w_i$ 由每块相邻三角面板面积各分配三分之一得到。这样，内圈连接面板较多的节点不会仅因拓扑度数而被重复计权。

== 下拉索与促动器映射

记促动器下端点为 $bold(a)_i$，基准态上端点为 $bold(b)_i$，促动器向外径向单位向量为 $bold(h)_i$。基准下拉索长度为

$ L_i=norm(bold(x)_i-bold(b)_i). $

促动器顶端向球心伸缩 $sigma_i$ 后的位置是 $bold(b)_i-sigma_i bold(h)_i$。下拉索定长条件为

$ norm(bold(x)_i-y_i bold(n)_i-bold(b)_i+sigma_i bold(h)_i)^2=L_i^2. $ <eq:actuator>

令 $bold(d)_i(y)=bold(x)_i-bold(b)_i-y bold(n)_i$，则 @eq:actuator 等价于

$ sigma_i^2+2[bold(h)_i dot bold(d)_i(y)]sigma_i+norm(bold(d)_i(y))^2-L_i^2=0. $

二次方程可能有两个根。本文选取在 $y=0$ 时等于零、随 $y$ 连续的根；判别式为负时，该目标节点在当前运动假设下不可达。

== 硬件友好焦距

对每个候选焦距，把 $y_i^star(f)$ 代入促动器映射和所有关联主索，定义

$ U_"act"(f)=max_(i in cal(I)) frac(abs(sigma_i(y_i^star)),0.6), $

$ U_"edge"(f)=max_((i,j) in cal(E)_cal(I))
frac(abs(norm(bold(x)_i(y_i^star)-bold(x)_j(y_j^star))/l_(i j)-1),0.0007), $

$ U(f)=max(U_"act"(f),U_"edge"(f)). $

先在 $f=F$ 附近作确定性网格搜索，再对最优邻域作一维有界精化。若多个焦距的 $U(f)$ 在数值容差内相同，则以面积加权位移均方误差作为第二判据。候选结果见 @tab:q1-candidates。

#figure(
  table(
    columns: (1.25fr, 1fr, 1fr, 1fr, 1fr),
    align: center,
    stroke: none,
    table.hline(y: 0, stroke: 0.8pt),
    table.hline(y: 1, stroke: 0.5pt),
    table.header([*候选*], [*$f$/m*], [*位移 MSE/$"m"^2$*], [*$U_"act"$*], [*$U_"edge"$*]),
    [几何焦距], [139.986405], [0.262893], [1.159033], [3.302666],
    [最小二乘], [140.386402], [0.041546], [0.666681], [1.873045],
    [硬件友好], [140.325121], [0.051657], [0.564544], [1.581528],
    table.hline(stroke: 0.8pt),
  ),
  caption: [正上方观测的理想抛物面候选比较],
) <tab:q1-candidates>

图 @fig:focal-search 给出两个观测方向下焦距与最大硬件占用率的关系。曲线最小点仍高于 1，且主索占用率明显大于促动器占用率，表明改变焦距只能缓解而不能消除离散索网冲突。

#figure(
  image("../figures/focal_model_comparison.pdf", width: 96%),
  caption: [两个观测方向的焦距与最大硬件占用率],
) <fig:focal-search>

综上，问题一取硬件友好焦距

$ f_1^star=140.325121 "m", $

对应顶点轴向半径 $v_1=300.738727 "m"$，顶点坐标为

$ bold(V)_1=(-0.000000,-0.000000,-300.738727) "m". $

该结果定义了工程意义下的理想目标，但 @tab:q1-candidates 中 $U_"edge">1$ 说明目标节点不能直接作为实际工作面。
