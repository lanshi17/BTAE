# WP-02：工程骨架、领域模型与最小端口

**状态：** in_progress · **里程碑：** M1 · **实施：** in_progress
**负责模块：** [core](../../../docs/modules/core/README.md)、[adapters](../../../docs/modules/adapters/README.md)、[cli](../../../docs/modules/cli/README.md)
**前置：** WP-01 · **下游：** WP-03 起全部实现包

## 1. 目标

建立可安装的 `epe` 包骨架、与 Schema 一致的领域模型、注册/关系/状态能力，以及文件/Git/Clock 最小端口实现；暴露能区分“已支持 / 未支持”的 CLI 入口。

## 2. 任务分解

| 子任务 | 内容 |
| --- | --- |
| T1 | 补 Registry / RelationshipManager / LifecycleManager 核心类设计（`docs/classes/`） |
| T2 | 建立 `pyproject.toml`、`src/epe/` 包布局与依赖约束（core 零内部依赖） |
| T3 | 实现 Entity/Relation/Diagnostic/InputManifest 等值对象与 Schema 加载 |
| T4 | 实现 `register_batch`、关系校验、状态迁移、`canonical_manifest` |
| T5 | 定义并实现 Repository / Git / Clock 端口；adapters 提供受限读与真实 Git 事实 |
| T6 | CLI 入口：`epe --help`、`epe inspect` 最小只读；其余命令返回明确 unsupported |
| T7 | 单元/契约测试：重复 ID、commit=null、dirty 含未跟踪、旧 revision 冲突 |

## 3. 拟议包布局

```text
pyproject.toml
src/epe/
  __init__.py
  __main__.py
  core/
    models/
    registry.py
    relations.py
    lifecycle.py
    ports.py
    diagnostics.py
    manifest.py
  adapters/
    filesystem.py
    git_info.py
    clock.py
  cli/
    main.py
    inspect_cmd.py
    result.py
tests/
  unit/core/
  unit/adapters/
  contract/schema_models/
  fixtures/
```

## 4. 接口冻结要点（相对 WP-01）

- `RegistryBuildResult`：snapshot、diagnostics、input_version、complete
- 重复 ID **永不覆盖**，即使内容相同
- Git：无提交 → `commit=null`；dirty 必须包含未跟踪纳管文件
- `transition(..., expected_revision)`：revision 不匹配则拒绝
- 端口接口在 core；adapters 只依赖 core

## 5. 验收映射

| 场景 | AC / 模块 |
| --- | --- |
| 模型拒绝未知字段与非法枚举 | WP-01 Schema；AC-02 基础 |
| 重复注册冲突 | AC-02 |
| inspect 只读、不写权威工件 | AC-01/09 预备 |
| unsupported 命令不空成功 | AC-09 预备；cli 模块 |
| core 包导入图无内部依赖边 | 模块依赖表 |

## 6. 完成门槛

- [ ] 本地可 `pip install -e .`（或项目选定等价方式）并运行 `epe inspect`
- [ ] 核心类设计文档存在且与代码符号映射声明一致（实现状态仍可为 in_progress）
- [ ] T7 测试有真实执行记录（手工日志亦可，路径写入计划备注）
- [ ] 未实现命令列表与 SPEC §8 对齐并返回 status=unsupported / 退出码 4

## 7. 明确不做

解析 Markdown/AST、构图、门禁求值、Evidence 写入、CI。
