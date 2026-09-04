#v(1.1em)

```python
def factorize_tridiagonal(lower, diagonal, upper):
    """预分解三对角矩阵，供多个时间步复用。"""
    pivots = np.asarray(diagonal, dtype=float).copy()
    multipliers = np.empty(len(pivots) - 1, dtype=float)
    for j in range(1, len(pivots)):
        multipliers[j - 1] = lower[j - 1] / pivots[j - 1]
        pivots[j] -= multipliers[j - 1] * upper[j - 1]
    return ThomasFactors(pivots, multipliers, upper.copy())


def thomas_solve(factors, rhs):
    """对一个右端执行前向消元和回代。"""
    work = np.asarray(rhs, dtype=float).copy()
    for j in range(1, len(work)):
        work[j] -= factors.multipliers[j - 1] * work[j - 1]
    solution = np.empty_like(work)
    solution[-1] = work[-1] / factors.pivots[-1]
    for j in range(len(work) - 2, -1, -1):
        solution[j] = (
            work[j] - factors.upper[j] * solution[j + 1]
        ) / factors.pivots[j]
    return solution
```

```python
def duration_above_threshold(times_s, temperatures_c, threshold_c):
    """按分段线性插值计算严格超过阈值的累计时长。"""
    total = 0.0
    for t0, t1, y0, y1 in zip(
        times_s[:-1],
        times_s[1:],
        temperatures_c[:-1],
        temperatures_c[1:],
        strict=True,
    ):
        width = t1 - t0
        left, right = y0 > threshold_c, y1 > threshold_c
        if left and right:
            total += width
        elif left != right and not np.isclose(y0, y1):
            crossing = (threshold_c - y0) / (y1 - y0)
            total += width * (crossing if right else 1.0 - crossing)
    return float(total)
```

```python
def evaluate_design(materials, d2_mm, d4_mm, config):
    result = simulate(
        materials,
        (0.6, d2_mm, 3.6, d4_mm),
        config,
    )
    max_temp = float(np.max(result.skin_temp_c))
    duration = duration_above_threshold(
        result.times_s,
        result.skin_temp_c,
        44.0,
    )
    feasible = max_temp <= 47.0 + 1e-9 and duration <= 300.0 + 1e-9
    return DesignMetric(
        d2_mm,
        d4_mm,
        max_temp,
        duration,
        result.skin_temp_c[-1],
        feasible,
        config.target_dx_mm,
        config.dt_s,
    )


def enumerate_designs(materials, d2_values, d4_values, config, workers):
    tasks = [
        (materials, float(d2), float(d4), config)
        for d4 in d4_values
        for d2 in d2_values
    ]
    if workers <= 1:
        records = [_design_worker(task) for task in tasks]
    else:
        with ProcessPoolExecutor(max_workers=workers) as executor:
            records = list(executor.map(
                _design_worker,
                tasks,
                chunksize=16,
            ))
    return pd.DataFrame.from_records(records)
```

以上片段分别对应 Thomas 预分解、阈值累计时长和厚度笛卡尔积枚举。完整程序还包含输入校验、界面对齐网格、全隐式系统装配、参数标定、NSGA-II 交叉验证、稳健搜索和结果复验。
