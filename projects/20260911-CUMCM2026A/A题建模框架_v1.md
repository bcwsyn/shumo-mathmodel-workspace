# 2026 CUMCM A题：药材烘干模型与求解框架 v1

## Material Passport

- Origin Skill: academic-research-suite / experiment-agent
- Origin Mode: plan
- Origin Date: 2026-09-11
- Verification Status: 题面与附件结构已核对；数值结果尚未求解与收敛验证
- Version Label: model_plan_v1

## 1. 模型选择结论

主模型采用**一维轴对称圆柱坐标下的热传导—水分扩散非线性偏微分方程**，差分/有限体积法是其数值离散方式。常微分方程（集总参数模型）只作为对照，不作为正式结果模型。

原因如下：药材半径为 \(R=0.02\,\mathrm m\)，问题 1 初始参数给出

\[
\alpha=\frac{k}{\rho c_p}=1.6886\times10^{-7}\ \mathrm{m^2/s},
\qquad
D(C_0)=4.9377\times10^{-9}\ \mathrm{m^2/s}.
\]

对应的热、质 Biot 数为

\[
Bi_T=\frac{hR}{k}=1.3889,
\qquad
Bi_C=\frac{h_mR}{D(C_0)}=3.2404.
\]

二者均明显大于 0.1，说明药材内部温度和水分浓度存在不可忽略的径向梯度。特征扩散时间约为

\[
\tau_T=\frac{R^2}{\alpha}=2368.9\ \mathrm s,
\qquad
\tau_C=\frac{R^2}{D(C_0)}=8.1010\times10^4\ \mathrm s.
\]

因此，30 min 内温度已经显著向内部传播，而水分变化主要集中在靠近表面的区域；这也正是题目要求给出径向分布的原因。

## 2. 数据和统一假设

### 2.1 已核对的数据

- 附件 1：241 个观测时刻，\(t=0\sim14400\,\mathrm s\)，步长 60 s；给出烘房温度 \(T_a(t)\) 和水分浓度 \(C_a(t)\)。
- 附件 2：145 个观测时刻，\(t=0\sim259200\,\mathrm s\)，步长 1800 s；给出药材半径 \(R(t)\)。
- 问题 1 初值：\(T(r,0)=28\,^{\circ}\mathrm C\)，\(C(r,0)=2.55\,\mathrm{kg/kg}\)。
- 附件 1 在 9000 s 以后基本稳定在 \(50\,^{\circ}\mathrm C\) 和 \(0.05\,\mathrm{kg/kg}\) 附近；超过 14400 s 后暂按 \(T_a=50\,^{\circ}\mathrm C\)、\(C_a=0.05\,\mathrm{kg/kg}\) 延拓。

### 2.2 建模假设

1. 药材为均匀、各向同性圆柱体，初始长 0.25 m、半径 0.02 m。
2. 只研究圆柱中部截面的径向变化。由于 \(L/R=12.5\)，并且题目只要求“到中心的距离”，忽略轴向传热传质和端面效应。
3. 药材表面与烘房空气之间分别满足牛顿冷却边界和对流传质边界。
4. 题目未给蒸发潜热及热湿耦合源项，故能量方程不额外加入相变潜热项；温度和水分通过物性参数发生间接耦合。
5. 附件 1 的边界数据在观测点间采用分段线性插值。确定性主结果使用原始输入，不先做平滑。
6. 问题 1—3 半径固定；问题 4 使用附件 2 的实测半径并按单调三次 Hermite 插值（PCHIP）得到 \(R(t)\)，区间外保持末值。

## 3. 问题 1：常物性热湿传递模型

令 \(r\in[0,R]\) 为到圆柱轴线的距离，\(T(r,t)\) 为药材温度，\(C(r,t)\) 为干基水分浓度。

### 3.1 温度方程

\[
\rho c_p\frac{\partial T}{\partial t}
=\frac{1}{r}\frac{\partial}{\partial r}
\left(kr\frac{\partial T}{\partial r}\right),
\quad 0<r<R.
\]

初始条件和边界条件为

\[
T(r,0)=28,
\qquad
\left.\frac{\partial T}{\partial r}\right|_{r=0}=0,
\qquad
k\left.\frac{\partial T}{\partial r}\right|_{r=R}
=h\,[T_a(t)-T(R,t)].
\]

问题 1 使用 \(\rho=820\,\mathrm{kg/m^3}\)、\(c_p=2600\,\mathrm{J/(kg\cdot K)}\)、\(k=0.36\,\mathrm{W/(m\cdot K)}\)、\(h=25\,\mathrm{W/(m^2\cdot K)}\)。

### 3.2 水分方程

\[
\frac{\partial C}{\partial t}
=\frac{1}{r}\frac{\partial}{\partial r}
\left[rD(C)\frac{\partial C}{\partial r}\right],
\qquad
D(C)=7\times10^{-9}\exp\left(-\frac{0.89}{C}\right).
\]

初始条件和边界条件为

\[
C(r,0)=2.55,
\qquad
\left.\frac{\partial C}{\partial r}\right|_{r=0}=0,
\qquad
-D(C_s)\left.\frac{\partial C}{\partial r}\right|_{r=R}
=h_m[C_s-C_a(t)],
\]

其中 \(C_s=C(R,t)\)，\(h_m=8\times10^{-7}\,\mathrm{m/s}\)。扩散项必须写成守恒形式 \(\nabla\cdot(D\nabla C)\)，不能在离散时把变系数 \(D(C)\) 简化为常数。

### 3.3 数值求解

- 空间上采用守恒型径向有限体积法，主输出节点为 \(r=0,0.001,\ldots,0.020\,\mathrm m\)，正好对应 0.1 cm 间隔。
- 圆心控制体使用轴对称零通量条件，避免直接计算 \(1/r\) 奇点。
- 表面控制体显式计入对流热通量和水分通量。
- 时间上采用隐式 BDF 或后向欧拉法；内部可自适应步进，在整数秒处取值。
- 非线性扩散系数按当前 \(C\) 更新，使用 Picard 迭代或由 BDF 求解器直接处理。
- 用 \(\Delta r=0.05\,\mathrm{cm}\)、更严格时间容差复算关键时刻；若所有表格点差异小于 \(5\times10^{-5}\)，才据此四舍五入到四位小数。

问题 1 的正式输出为 \(t=1,2,\ldots,1800\,\mathrm s\) 与 \(r=0,0.1,\ldots,2.0\,\mathrm{cm}\) 的完整矩阵，并从中抽取题面表 1、表 2 指定行列。

### 3.4 网格加密与有限体积验证

问题一进一步采用 \(\Delta r=0.1,0.05,0.025,0.0125\,\mathrm{cm}\) 四层控制体网格进行网格无关性检验。四层空间实验统一取 \(\Delta t=0.25\,\mathrm s\)，在题目指定的35个关键时空点比较相邻网格解。C→D 时温度最大绝对误差为 \(1.0160\times10^{-4}\,^{\circ}\mathrm C\)，最大相对误差为 0.000345%；水分浓度最大绝对误差为 \(1.5255\times10^{-3}\,\mathrm{kg/kg}\)，最大相对误差为 0.067905%。后者的最差位置为 100 s 的药材表面，反映了初始阶段陡峭水分边界层对空间分辨率的较高要求。两变量均满足最大相对误差小于0.1%的工程判据。

最终内部网格采用 \(\Delta r=0.0125\,\mathrm{cm}\)，时间步长进一步减小为 \(\Delta t=0.125\,\mathrm s\)。时间加密导致的35点最大变化分别为 \(3.70\times10^{-8}\,^{\circ}\mathrm C\) 和 \(4.87\times10^{-8}\,\mathrm{kg/kg}\)，可忽略不计。完整结果及论文用表述见 `solution/问题一_FVM网格加密报告.md`。

## 4. 问题 2—3：变物性双向耦合模型

问题 2 和问题 3 沿用同一组控制方程，但物性随 \(C,T\) 变化：

\[
\rho(C)=650+128C,
\]

\[
c_p(C)=1450+2736\frac{C}{C+1},
\qquad
k(C)=0.21+0.38\frac{C}{C+1},
\]

\[
D(C,T_K)=2.4\times10^{-3}
\exp\left(-\frac{0.45}{C}\right)
\exp\left(-\frac{3850}{T_K}\right),
\]

其中 \(T_K=T+273.15\) 必须使用 K。控制方程写为

\[
\rho(C)c_p(C)\frac{\partial T}{\partial t}
=\frac{1}{r}\frac{\partial}{\partial r}
\left[rk(C)\frac{\partial T}{\partial r}\right],
\]

\[
\frac{\partial C}{\partial t}
=\frac{1}{r}\frac{\partial}{\partial r}
\left[rD(C,T_K)\frac{\partial C}{\partial r}\right].
\]

这里 \(C\) 改变 \(\rho,c_p,k,D\)，而 \(T\) 改变 \(D\)，因此是双向弱耦合系统。问题 2 求到 3 h 并每秒输出；问题 3 继续使用同一状态积分，停止时刻定义为

\[
t_{\mathrm{dry}}=\inf\left\{t:\max_{0\le r\le R}C(r,t)\le0.15\right\}.
\]

不能只判断平均水分浓度，也不应先验地只判断中心点；程序应检查全部空间节点。若数值结果确认 \(C(r,t)\) 从中心到表面单调递减，再说明中心点是最终控制点。

## 5. 问题 4：给定收缩半径下的移动边界模型

令材料坐标 \(\xi=r/R(t)\in[0,1]\)，并假设径向收缩为仿射运动，固体速度为

\[
v_r(r,t)=\frac{\dot R(t)}{R(t)}r.
\]

对随固体运动的材料导数建模后，在固定 \(\xi\) 网格上有

\[
\rho(C)c_p(C)\frac{\partial \widetilde T}{\partial t}
=\frac{1}{R(t)^2\xi}\frac{\partial}{\partial\xi}
\left[\xi k(C)\frac{\partial \widetilde T}{\partial\xi}\right],
\]

\[
\frac{\partial \widetilde C}{\partial t}
=\frac{1}{R(t)^2\xi}\frac{\partial}{\partial\xi}
\left[\xi D(C,T_K)\frac{\partial \widetilde C}{\partial\xi}\right].
\]

表面对流边界相应变为

\[
\frac{k}{R(t)}\left.\frac{\partial\widetilde T}{\partial\xi}\right|_{\xi=1}
=h[T_a(t)-\widetilde T(1,t)],
\]

\[
-\frac{D}{R(t)}\left.\frac{\partial\widetilde C}{\partial\xi}\right|_{\xi=1}
=h_m[\widetilde C(1,t)-C_a(t)].
\]

问题 4 使用附录 4 的 \(\rho,c_p,k,D\) 经验式。该写法把 \(\xi\) 视为材料坐标，因此不会额外重复加入收缩对流项。最终将 \(\xi\) 网格映射回每一时刻的物理距离 \(r=R(t)\xi\) 后输出。

## 6. 贝叶斯与蒙特卡洛层的正确位置

题面没有提供药材内部温度或水分浓度观测，因此 \(k,h,h_m,D\) 等参数目前无法由附件 1 单独反演。附件 1 是边界输入，不是内部响应。故正式提交表格先使用题给参数的确定性解，不凭空构造“后验参数”。

贝叶斯层作为不确定性与稳健性分析：

\[
\log\theta_j\sim N(\log\theta_{j,0},s_j^2),
\quad
\theta=(k,h,h_m,\lambda_D),
\]

其中 \(\lambda_D\) 是经验扩散系数的乘性修正因子。若后续获得内部观测 \(y_T,y_C\)，使用

\[
p(\theta\mid y)\propto p(y\mid\theta)p(\theta)
\]

更新参数；观测误差用传感器精度确定，不能随意设定得过小。随后从后验抽样并重复求解 PDE，得到温度、水分浓度及烘干时长的 95% 可信区间。

在没有内部观测时，可采用拉丁超立方/蒙特卡洛抽样做**先验预测敏感性分析**，但必须明确称为先验传播而非后验推断。建议输出：

- \(t_{\mathrm{dry}}\) 的中位数与 95% 区间；
- 各参数对 \(t_{\mathrm{dry}}\) 的 PRCC 或 Sobol 敏感度；
- 名义解与不确定性带对比图。

这些区间不写入题目规定的 result 文件，以免改变确定性提交格式。

## 7. 验证与质量门槛

1. **解析基准**：把物性和环境边界冻结为常数，与无限圆柱经典级数解或高精度边值解比较。
2. **网格收敛**：比较 \(\Delta r=0.1,0.05,0.025\,\mathrm{cm}\)；表格取值在四位小数上稳定。
3. **时间收敛**：比较整数秒直接步进与更小内步长/更严格 BDF 容差。
4. **守恒检查**：逐步核对体平均能量和水分变化与表面对流通量的积分误差。
5. **物理边界**：检查 \(C\ge0\)，升温阶段温度不出现无来源超调，中心梯度为零，表面通量方向正确。
6. **全过程连续性**：问题 3 必须从问题 2 的同一状态连续积分，不能在 3 h 处重置初值。
7. **移动边界检查**：问题 4 的 \(R(t)\) 必须保持正值和非增趋势，并核对固定半径极限能退化到问题 2—3。

## 8. 实现顺序

1. 建立附件解析与单位转换模块，生成 \(T_a(t),C_a(t),R(t)\) 插值器。
2. 实现问题 1 常物性求解器，完成解析基准和网格收敛检查。
3. 写入 result1.xlsx，并自动抽取论文表 1、表 2。
4. 扩展到问题 2 的变物性耦合方程，写入 result2.xlsx。
5. 延续积分并用事件检测定位 \(t_{\mathrm{dry}}\)，写入 result3.xlsx。
6. 将空间域改为材料坐标 \(\xi\)，引入 \(R(t)\)，求解问题 4 并写入 result4.xlsx。
7. 最后再做参数不确定性、蒙特卡洛敏感性和论文图表，避免这些附加层干扰主结果。

## 9. 数值实验计划

- Title: 圆柱药材热湿耦合与收缩移动边界仿真
- Objective: 计算四问要求的径向时空分布与烘干结束时间
- Type: simulation
- Language/Framework: Python 3.13，NumPy、SciPy、openpyxl
- Working Directory: `E:\周军\数学建模\炜\26题目\CUMCM2026Problems\A题`
- Planned Entry Command: `D:\anaconda\python.exe solution\solve.py`
- Timeout: 初次全流程 30 min
- Primary Metric: 四个结果文件的维度、四位小数稳定性、守恒误差和干燥终止条件
- Success Criterion: 所有指定时空节点齐全；关键表格在网格加密后四位小数不变；无越界值；终止时全域 \(C\le0.15\)
