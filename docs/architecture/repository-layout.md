# 目录与工件组织

状态：目标布局草案。下列目录按需要建立，不表示目前存在；示例业务模块名不构成 BTAE 自身的实现划分。

```text
project/
├── README.md
├── AGENTS.md
├── pyproject.toml
├── docs/
│   ├── index.md
│   ├── constitution/         # principles、constraints、security
│   ├── intent/               # vision、requirements
│   ├── architecture/         # 总体、边界、依赖、decisions、models
│   ├── modules/              # 每个模块的 README 与协作契约
│   ├── components/           # 组件职责与协作设计
│   ├── classes/              # 核心类独立设计
│   ├── contracts/            # api、events、schemas、interfaces
│   └── standards/            # engineering、documentation、coding、testing
│                             # agent-protocol、templates
├── plans/
│   ├── active/
│   ├── backlog/
│   └── completed/
├── src/                      # 正式实现
├── tests/
│   ├── unit/
│   ├── integration/
│   ├── contract/
│   ├── architecture/
│   ├── acceptance/
│   ├── performance/
│   └── fixtures/
├── engineering/
│   ├── schemas/              # entity、relation、evidence 等机器定义
│   ├── policies/             # documentation、architecture、verification
│   └── workflows/            # feature、bugfix、refactor、exploration
├── .engineering/             # 可重建实体、图、影响和校验缓存
├── scripts/                  # CLI / CI 薄封装，避免重复实现核心逻辑
├── reports/
│   ├── tests/
│   ├── evaluations/
│   └── architecture/
└── archive/
    ├── designs/
    ├── plans/
    ├── decisions/
    └── migrations/
```

## 工件职责

- 模块文档维护边界、公共契约、依赖与集成责任；组件文档维护跨类协作；类文档维护核心类的职责、状态和行为约束。
- 设计意图写在 Markdown，结构与接口写在契约，实际行为由测试验证，不在多个工件复制整套相同内容。
- `engineering/` 是治理定义，`src/` 是正式实现，`.engineering/` 是派生数据。若项目本身开发 EPE，其引擎实现仍属于 `src/`。
- 报告与 Evidence 通过版本和摘要关联本地文件或 CI 产物；大型产物不必全部纳入 Git，但应定义保留期与失效处理。
- 归档保留原 ID、替代关系、归档原因与版本。历史设计不得进入默认当前上下文。
- `plans/completed/` 存放完成任务；`archive/plans/` 用于历史迁移或不再活跃维护的计划，避免两个目录承担同一状态语义。

## 当前模板与后续补充

Architecture、Module、Component、Class、Contract、Task / ChangeSet、ADR 和 Evidence 模板已位于 `engineering/templates/`，并由 `epe init` 只在缺失时创建。共同字段为稳定 ID、名称、来源、版本和适用状态；各类型保留自己的必填项，不强迫所有实体采用完全相同正文结构。新增模板仍需通过 Schema、解析和回归证据后再纳入正式规范。
