#import "../lib.typ": academic-table

= 四层传热模型与问题一求解

== 材料数据与物理结构

题目给出的四层热物性见 @tab-materials。第二层导热系数较大，但密度和比热容也较大；第四层导热系数最低，单位厚度增加的热阻最大。因此，仅按“导热系数越小越好”无法决定两层的最优分配，必须在瞬态方程中同时计算热阻与蓄热。

#academic-table(
  [四层防护服材料参数与厚度范围],
  (3.2em, 6em, 7.3em, 7.3em, 6em),
  ([层], [密度 / $("kg"/"m"^3)$], [比热容 / $("J"/("kg" dot "K"))$], [导热系数 / $("W"/("m" dot "K"))$], [厚度 / mm]),
  (
    [I], [300], [1377], [0.082], [0.6],
    [II], [862], [2100], [0.370], [0.6--25.0],
    [III], [74.2], [1726], [0.045], [3.6],
    [IV], [1.18], [1005], [0.028], [0.6--6.4],
  ),
) <tab-materials>

如 @fig-physical 所示，坐标 $x$ 从高温环境指向人体，$x=0$ 为第一层外表面，$x=L$ 为第四层人体侧表面。高温环境和 37°C 人体热库不直接固定材料表面温度，而是分别通过有限换热系数 $h_o,h_b$ 与服装相连。

#figure(
  image("../../figures/fig_model_heat_transfer.pdf", width: 100%, alt: "四层高温防护服的一维传热结构、坐标和双Robin边界"),
  caption: [四层高温防护服的一维传热结构与边界条件],
) <fig-physical>

该结构保留了材料内部蓄热、层间热阻和内外边界层三个影响温升的关键环节，同时把实验无法单独辨识的辐射和皮肤内部传热合并为等效边界参数。

== 一维非稳态传热模型

=== 控制方程与初始条件

对第 $i$ 层区间 $s_(i-1)<x<s_i$，能量守恒给出

$ rho_i c_i frac(partial T_i, partial t)
  = k_i frac(partial^2 T_i, partial x^2),
  quad i=1,2,3,4. $ <eq-pde>

式中，$rho_i,c_i,k_i$ 分别为第 $i$ 层材料的密度、比热容和导热系数。进入高温环境前，各层采用均匀初温

$ T_i(x,0)=T_0=37 degree"C". $ <eq-initial>

=== 层间连续与双 Robin 边界

在三个材料界面 $x=s_i$ 处，温度与法向热流连续：

$ T_i(s_i,t)=T_(i+1)(s_i,t), quad i=1,2,3, $ <eq-interface-temp>

$ k_i frac(partial T_i, partial x)(s_i^-,t)
  = k_(i+1) frac(partial T_(i+1), partial x)(s_i^+,t). $ <eq-interface-flux>

取进入人体方向的热流为正。外侧和人体侧边界分别为

$ -k_1 frac(partial T_1, partial x)(0,t)
  = h_o [T_e-T_1(0,t)], $ <eq-robin-out>

$ -k_4 frac(partial T_4, partial x)(L,t)
  = h_b [T_s(t)-T_b], quad T_s(t)=T_4(L,t). $ <eq-robin-body>

其中 $T_b=37 degree"C"$ 是人体深部热库温度，$T_s(t)$ 才是题目需要约束和拟合的皮肤外侧温度。双 Robin 边界是对边界层换热的等效描述；经典传热理论中，有限对流换热边界和串联热阻正是处理此类固体—流体耦合的基础形式，见文献 [1]。

=== 稳态闭式校验

当时间充分长时，各层热流相同，总热阻为

$ R_"tot"=frac(1,h_o)+sum_(i=1)^4 frac(d_i,k_i)+frac(1,h_b). $ <eq-resistance>

于是稳态热流和皮肤外侧温度为

$ q_infinity=frac(T_e-T_b,R_"tot"), quad
  T_(s,infinity)=T_b+frac(q_infinity,h_b). $ <eq-steady>

该闭式解不替代瞬态模型，而用于检查边界符号、参数初值和数值解的长期极限。

== 守恒型全隐式离散

=== 界面对齐的非均匀有限体积网格

各层分别划分控制体，使层间界面恰落在控制体面上。第 $j$ 个单元宽度为 $Delta x_j$，单位面积热容量为

$ C_j=rho_j c_j Delta x_j. $ <eq-capacity>

对于分属不同材料的相邻单元，按两侧半单元串联热阻定义面导通系数

$ G_(j+1/2)=
  lr(
    frac(Delta x_j,2k_j)
    +frac(Delta x_(j+1),2k_(j+1))
  )^(-1). $ <eq-face-g>

这一谐均形式直接保证面热流唯一，比在界面把导热系数作算术平均更符合能量守恒。有限体积法的守恒构造可参见文献 [2]、[3]。

两端边界同样按“半个控制体导热热阻 + 边界换热热阻”串联：

$ G_(1/2)=lr(frac(1,h_o)+frac(Delta x_1,2k_1))^(-1), quad
  G_(N+1/2)=lr(frac(Delta x_N,2k_4)+frac(1,h_b))^(-1). $ <eq-boundary-g>

=== 全隐式时间推进

对内部单元在 $t_(n+1)$ 时刻离散，得到

$ -G_(j-1/2)T_(j-1)^(n+1)
  +lr(frac(C_j,Delta t)+G_(j-1/2)+G_(j+1/2))T_j^(n+1)
  -G_(j+1/2)T_(j+1)^(n+1)
  =frac(C_j,Delta t)T_j^n. $ <eq-implicit>

首、末单元右端分别增加 $G_(1/2)T_e$ 和 $G_(N+1/2)T_b$，从而形成

$ bold(A) bold(T)^(n+1)=bold(r)^n. $ <eq-linear-system>

矩阵 $bold(A)$ 为严格对角占优的三对角矩阵。全隐式格式对时间步无条件稳定，适合 5400 个以上时间步的重复推进。

=== Thomas 追赶法与边界温度恢复

设三对角系统的下、主、上对角元分别为 $a_j,b_j,c_j$，右端为 $r_j$。前向消元递推为

$ beta_1=b_1, quad
  beta_j=b_j-frac(a_j c_(j-1),beta_(j-1)), quad
  gamma_j=r_j-frac(a_j gamma_(j-1),beta_(j-1)). $ <eq-thomas-forward>

随后由

$ T_N=frac(gamma_N,beta_N), quad
  T_j=frac(gamma_j-c_j T_(j+1),beta_j) $ <eq-thomas-back>

逆向回代。系数矩阵在固定厚度、边界和时间步下不随时间改变，故 $beta_j$ 及消元乘子只需预计算一次；每个时间步的时间、存储复杂度均为 $O(N)$。

末控制体中心温度不等于人体侧边界面温度。由末半单元与人体换热热阻串联，有

$ q_b=G_(N+1/2)(T_N-T_b), quad
  T_s=T_b+frac(q_b,h_b). $ <eq-skin-recover>

实验拟合和两项安全约束均使用式 @eq-skin-recover 恢复的 $T_s$。

=== 安全指标与数值精度

对任一工作时段 $[0,t_f]$，定义

$ T_"max"=op("max")_(0<=t<=t_f) T_s(t), quad
  tau_44=integral_0^(t_f) bold(1)[T_s(t)>44] dif t. $ <eq-safety>

相邻离散时刻间采用线性插值确定阈值穿越比例；若曲线不单调，则累计所有超阈区间。快速搜索、正式计算和临界复核使用 @tab-grid 所列精度层级。

#academic-table(
  [数值网格层级与用途],
  (7em, 7em, 7em, 1fr),
  ([层级], [目标空间步长], [时间步长], [用途]),
  (
    [快速], [0.20--0.25 mm], [2.0 s], [完整枚举和临界带筛选],
    [正式], [0.10 mm], [1.0 s], [参数标定、边界候选复核],
    [细网格], [0.05 mm], [0.5 s], [最终临界厚度与约束回代],
  ),
  cell-align: (center, center, center, left),
) <tab-grid>

== 问题一的参数标定

=== 目标函数

问题一材料厚度和物性固定，只标定两个正参数。令

$ bold(theta)=(ln h_o,ln h_b), $

用对数参数化保证换热系数始终为正。实验 5401 个点中，1800 s 后的平台段占比很大。为兼顾早期上升速度、中期过渡和后期稳态，将时刻划为

$ I_1=[0,600], quad I_2=(600,1800], quad I_3=(1800,5400], $

并最小化阶段等权目标

$ J(bold(theta))=
  frac(1,3)sum_(r=1)^3 frac(1,abs(I_r))
  sum_(t_n in I_r)[T_s(t_n;bold(theta))-y_n]^2. $ <eq-calibration>

先用稳态热阻式给出物理合理初值，再在 $(ln h_o,ln h_b)$ 上执行粗搜索和三个起点的有界非线性最小二乘。最优点未触及 $1<=h_o<=500$、$1<=h_b<=100$ 的数值护栏。

=== 标定结果与残差

@tab-calibration 汇总了标定和可辨识性指标。Jacobian 条件数为 11.4401、参数相关系数为 0.66285，均未达到预设的严重不可辨识阈值；但单条实验轨迹仍不足以把两者解释成可跨装置复用的独立物性。

#academic-table(
  [问题一参数标定与拟合指标],
  (1fr, 8em),
  ([指标], [数值]),
  (
    [外侧等效换热系数 $h_o$], [$120.991689 " W"/("m"^2 dot "K")$],
    [人体侧等效换热系数 $h_b$], [$8.364912 " W"/("m"^2 dot "K")$],
    [全时段 RMSE], [$0.002627 degree"C"$],
    [全时段 MAE], [$0.002317 degree"C"$],
    [最大绝对误差], [$0.007755 degree"C"$],
    [Jacobian 条件数], [11.4401],
    [参数相关系数], [0.66285],
    [优化函数评价次数], [17],
  ),
  cell-align: (left, center),
) <tab-calibration>

@fig-q1-fit 显示模型曲线在升温段与平台段均紧贴实验值。极低 RMSE 一方面说明双 Robin 边界能够同时解释瞬态和稳态，另一方面也受原始温度只保留两位小数影响，不能据此宣称完成独立外部验证。

#figure(
  image("../../figures/q1_model_fit.pdf", width: 88%, alt: "问题一实验值与模型值随时间变化的拟合曲线"),
  caption: [问题一实验皮肤温度与模型计算值],
) <fig-q1-fit>

残差诊断见 @fig-q1-residual。残差幅度小且围绕零分布，其中离散平台主要对应两位小数的测量量化，而非物理温度完全静止。该现象支持把误差解释为“模型误差与测量分辨率共同作用”，而不是继续增加接触热阻或辐射参数来追逐更低误差。

#figure(
  image("../../figures/q1_residual_diagnostics.pdf", width: 88%, alt: "问题一拟合残差的时间序列和分布"),
  caption: [问题一拟合残差的时序与分布诊断],
) <fig-q1-residual>

== 温度场结果与数值验证

=== 四层瞬态温度场

@fig-q1-field 给出 0--5400 s 的完整温度场。外表面首先升温，热锋随后穿过四层向人体侧传播；约 1800 s 后皮肤温度接近平台。不同材料中的等温线疏密差异同时反映导热系数和体积热容，第四层虽热扩散率较高，但因导热系数最低仍提供显著热阻。

#figure(
  image("../../figures/q1_temperature_field.pdf", width: 95%, alt: "四层防护服温度随厚度位置和时间变化的二维温度场"),
  caption: [问题一四层介质的温度时空分布],
) <fig-q1-field>

典型时刻剖面见 @fig-q1-profile。各界面温度连续，而不同材料内温度梯度发生变化，这正是式 @eq-interface-flux 所要求的“热流连续、梯度按导热系数调整”。人体侧边界面温度由式 @eq-skin-recover 恢复，不以末控制体中心值代替。

#figure(
  image("../../figures/q1_temperature_profiles.pdf", width: 88%, alt: "多个典型时刻沿四层厚度方向的温度剖面"),
  caption: [问题一典型时刻的厚度方向温度剖面],
) <fig-q1-profile>

=== 收敛、守恒和稳态校核

@tab-checks 给出关键验证。正式标定采用 0.10 mm/1 s 网格；继续细化到 0.05 mm/0.5 s 且保持正式参数不变时，RMSE 仍处于同一量级。能量平衡与界面热流残差接近机器舍入水平，5400 s 皮肤温度与稳态热阻闭式值一致，说明离散、边界符号和边界面温度恢复相互闭合。

#academic-table(
  [问题一网格收敛与物理一致性校核],
  (1fr, 8em, 8em),
  ([校核项目], [设置或结果], [关键指标]),
  (
    [粗网格重标定], [0.20 mm / 2.0 s], [RMSE $0.002956 degree"C"$],
    [正式网格重标定], [0.10 mm / 1.0 s], [RMSE $0.002627 degree"C"$],
    [细网格固定正式参数], [0.05 mm / 0.5 s], [RMSE $0.003091 degree"C"$],
    [全过程能量平衡], [最大残差], [$2.34 times 10^(-9) " W"/"m"^2$],
    [三个材料界面], [最大热流失配], [$6.31 times 10^(-11) " W"/"m"^2$],
    [5400 s 与稳态解], [$48.082215 degree"C"$], [差 $-6.97 times 10^(-10) degree"C"$],
  ),
  cell-align: (left, center, center),
) <tab-checks>

由此，问题一得到经过实验标定和多重数值检验的公共传热模型。完整输出包含 5401 个时刻、152 个控制体的温度场，以及皮肤温度、残差和校核信息，供后续厚度设计复用。
