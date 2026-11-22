# EPE MVP 使用指南

## 安装与检查

在仓库根目录执行：

```bash
python -m pip install -e '.[test]'
epe --format json inspect
epe --format json policy validate
epe --format json host capabilities
```

源码外验证 wheel：

```bash
python -m pip wheel . --no-deps -w /tmp/epe-wheel
python -m venv /tmp/epe-wheel-venv
/tmp/epe-wheel-venv/bin/pip install /tmp/epe-wheel/*.whl
```

## 首次闭环

1. `epe init` 只创建缺失的治理文件；已有内容冲突会阻断且不覆盖。
2. 创建并校验实体设计：`epe design create CLASS-001`、`epe design validate CLASS-001`。
3. 创建 Task 和 ChangeSet，激活两者后运行 `epe graph build`。
4. 使用 `epe verify TASK-001` 执行验证策略并保存独立 Evidence。
5. 使用 `epe check --task TASK-001` 汇总设计、映射、架构、Evidence 和范围事实。
6. 只有 `check` 返回 `passed` 后，才能完成 ChangeSet 和 Task。

机器输出始终是一个 `CommandResult` JSON；退出码 0 表示通过，1 表示门禁阻断，2 表示参数/配置错误，3 表示执行/解析/存储故障，4 表示不支持，5 表示写入冲突。

## 查询与上下文

`epe context resolve TASK-001` 提供 C0–C3 分级上下文、遗漏和来源状态；`epe impact analyze ENTITY-ID` 提供有预算的影响传播。影响结果中的 candidate、truncated 和 incomplete 不能解释为完整确定影响。

## 宿主请求边界

`epe host request --host local-cli --operation verify ...` 只校验并转发结构化协议请求，不运行治理门禁，不写入 Task、Approval 或 Evidence。`start_implementation` 与 `finalize` 在本地宿主上明确返回 `unsupported`。Hermes 需要显式 argv bridge、capability handshake、可信身份和隔离实测；仓库当前不声称已完成这些集成。

## 已知限制

- CI 工作流会上传 JUnit 测试报告作为本次运行产物；artifact 保存不等于远程分支保护已启用。
- 当前 CI 工作流执行检查，但远程分支保护是否启用需要在托管平台单独确认。
- 本地 hash-chain 审计可以发现链内篡改和摘要不一致，不能防止有权限者同时重写整条链和记录。
- Linux `renameat2(RENAME_NOREPLACE)` 用于 Evidence bundle 的原子目录发布；其他平台未承诺相同语义。
- BTAE 的方法收益、成本和召回率尚无独立试点证明。
