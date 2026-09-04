= 符号与坐标系

主要符号见 @tab:symbols。

#figure(
  table(
    columns: (5em, 1fr, 5em),
    align: (center, left, center),
    stroke: none,
    table.hline(y: 0, stroke: 0.8pt),
    table.hline(y: 1, stroke: 0.5pt),
    table.header([*符号*], [*含义*], [*单位*]),
    [$R_i$], [节点 $i$ 的基准半径], [m],
    [$R$], [全部节点基准半径的均值], [m],
    [$F$], [题面给定的焦面距离参数，$F=0.466R$], [m],
    [$q$], [焦面球半径，$q=R-F$], [m],
    [$bold(u)$], [从球心指向天体的单位向量], [—],
    [$bold(k)$], [工作反射面轴向单位向量，$bold(k)=-bold(u)$], [—],
    [$bold(P)$], [馈源平面中心和抛物面焦点], [m],
    [$bold(n)_i$], [节点 $i$ 的基准径向单位向量], [—],
    [$y_i$], [节点沿 $bold(n)_i$ 向球心的位移], [m],
    [$sigma_i$], [促动器顶端向球心的伸缩量], [m],
    [$L_i$], [第 $i$ 根下拉索基准长度], [m],
    [$l_(i j)$], [主索边 $(i,j)$ 的基准长度], [m],
    [$epsilon$], [主索相对变化上限，$0.0007$], [—],
    [$w_i$], [由相邻面板面积分配得到的节点权重], [$"m"^2$],
    table.hline(stroke: 0.8pt),
  ),
  caption: [主要符号说明],
) <tab:symbols>

方位角 $alpha$ 和仰角 $beta$ 转换为

$ bold(u) = (cos beta cos alpha, cos beta sin alpha, sin beta), quad bold(k)=-bold(u). $

焦面中心取为

$ bold(P)=q bold(k), quad q=R-F. $

对任意坐标 $bold(x)$，定义沿工作面轴的坐标与离轴距离

$ t=bold(x) dot bold(k), quad rho(bold(x))=sqrt(norm(bold(x))^2-t^2). $

300 m 工作节点集合固定按基准位置选择：

$ cal(I)(bold(k))={i: bold(x)_i dot bold(k)>0, rho(bold(x)_i)<=150}. $

节点调整后坐标为

$ bold(x)_i(y_i)=bold(x)_i-y_i bold(n)_i. $

全文约定 $y_i>0$ 和 $sigma_i>0$ 都表示向球心方向移动。口径外节点令 $y_i=0$，但与活动节点关联的主索仍进入约束集合。
