# 代码证据与运行清单规范

## 运行清单

在 `code/audit_manifest.json` 中记录可直接执行的入口，不写 shell 字符串：

```json
{
  "entries": [
    {
      "name": "main-smoke",
      "stages": ["g2", "g3", "final"],
      "script": "code/main.py",
      "args": ["--smoke"],
      "timeout_seconds": 120,
      "expected_artifacts": ["results/problem1_baseline.json"]
    }
  ],
  "interfaces": [
    {
      "name": "example-solver",
      "kind": "python-package",
      "status": "VERIFIED",
      "evidence": "安装包版本与 g2 最小调用日志"
    }
  ]
}
```

路径必须相对于项目根，并解析在项目根内部。`name` 必须唯一。`stages` 只使用 `g2`、`g3`、`final`。

## 证据层级

从强到弱依次为：

1. 当前解释器中的实际成功运行及产物哈希。
2. 当前安装版本的本机反射、帮助信息或最小调用。
3. 对应版本的官方文档或用户提供的接口文档。
4. 第三方示例、模型记忆或相似库经验，只能作为线索，不能标记为 `VERIFIED`。

## 必须标为 UNVERIFIED 的情况

- 只写了代码但没有运行。
- API 需要网络或凭据且当前无法调用。
- 只运行 Mock、桩函数或模拟响应。
- 只验证了一条成功路径，关键异常或边界路径未覆盖。
- 运行日志、退出码或对应产物已经丢失。

## 必须标为 FAILED 的情况

- 解释器路径不存在或启动失败。
- import、语法、入口运行或预期产物失败。
- 报告声称使用的版本与实际环境不一致。
- 正式结果来自模拟数据、手工填写或无法关联到运行记录。
- fallback 吞掉异常并继续输出“成功”。

## 其他生成代码风险

审计时同时检查：数据泄露、随机种子缺失、硬编码本机路径、秘密写入源码、宽泛异常、未检查求解器状态、测试与实现共享同一错误公式、缓存冒充新运行、输出覆盖原始数据，以及图表与结果数据断链。
