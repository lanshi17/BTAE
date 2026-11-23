---
id: MOD-003
type: Module
name: EPE Graph
version: 0.1
design_status: draft
implementation_status: implemented
verification_status: passed
---

# graph：知识图谱与变更影响

## 1. 定位与范围

组织设计、实现、测试与证据之间的可查询关系，生成带版本的完整图快照。对应 PRD-004、PRD-010，支撑 AC-04、AC-10，后续支撑影响分析与上下文。

V0.2 交付全量重建、双向查询、依赖与循环分析；当前还提供有预算的基础影响传播、增量计划和实际增量重建（清单差异、删除/移动路径、解析器或 Schema 变化的全量回退）。支持由调用者指定历史 generation 分析删除或移动前的影响；自动识别紧邻旧版本和独立准确率评测仍属于后续范围。图不决定授权，不将实际依赖自动改为设计约束，不生成没有来源的“确定关系”。

## 2. 逻辑组件

| 组件 | 职责 |
| --- | --- |
| Graph Builder | 将已校验注册快照与代码事实组合为确定性图；增量重建复用未变化 AST 事实 |
| Graph Query | ID 定位、正反邻接、路径和模块依赖查询 |
| Snapshot Coordinator | 计算快照版本与完整性，提供可发布载荷 |
| Impact Analyzer | V0.3 按关系语义传播变化并给出原因 |
| Incremental Planner | 根据 manifest 差异确定重解析集合和重建回退条件 |

循环查找是图算法，是否属于阻断违规由 verification 的 Architecture Validator 使用规则判定。静态解析盲区在 `unknown_is_blocking: true`（默认推荐）时使架构结论为 fail/unknown；不能把动态依赖漏报解释为无违规。禁止依赖规则使用 `fnmatch` 路径模式，规则端点缺失或为空属于策略故障。

## 3. 对外接口草案

```text
build_snapshot(registry, code_facts, input_manifest, build_options) -> GraphBuildResult
neighbors(snapshot, entity_id, relation_types, direction) -> QueryResult
dependency_cycles(snapshot, module_scope) -> CycleReport
trace_path(snapshot, source_id, target_id, filters) -> PathResult
analyze_impact(snapshot, changed_entities, change_kind, budget) -> ImpactReport  # V0.3
```

结果包含快照摘要、范围、诊断、盲区和来源路径。snapshot 不匹配当前输入时返回 stale / unknown 诊断；不得用旧索引回答“当前无影响”。

## 4. 构图与身份规则

先校验实体和引用，再将显式关系与静态事实分别纳入图。未注册符号保留内部定位键和未纳管状态，不自动产生有工程身份的 Class。不同来源的同一事实保留为独立关系记录，冲突事实不得按 confidence 静默覆盖。完整关系记录用于去重和稳定排序；注册阶段拒绝完全重复声明。当前快照绑定构图版本，算法升级后须重建；历史快照不自动补充丢失的来源。

可在 `engineering/epe.yaml` 使用 `managed.module_roots: {MOD-001: [src/package]}` 显式配置 Module 到仓库相对目录的映射；配置后每个纳管 Python 文件必须恰好归入一个 Module。重叠或无效映射使构图失败，未归属文件作为静态盲区；跨模块内部导入生成带原始文件与行号的模块依赖，不生成模块自环。未配置时不推断归属，无法证明模块级循环已被检查。外部依赖和动态未知依赖保留单独标记，不伪装成已确认的内部节点。

规范化输出按实体 ID、关系端点/类型/来源排序，内容指纹不包含构建时间。相同输入删除缓存后重建应得到相同内容；NetworkX 仅作为算法实现选择，不进入持久化公共契约。

### 路径查询契约

`trace_path` 在调用方提供的图快照中按有向关系进行广度优先搜索，支持反向或双向及关系类型过滤；结果包含快照摘要、端点、原始边、行进方向、是否找到、节点展开数与是否截断。多个最短路径按稳定排序择一，不表示唯一或最可信路径。相同端点和类型的不同来源保留为独立边，完全相同的记录去重；路径结果仅展示所选路径，完整来源可通过邻接查询获取。展开预算为正整数；预算耗尽与完整搜索无路径分别报告。路径含推断、未知来源或低置信度边时标记 candidate；搜索结果附图内静态分析诊断，缺失路径不证明真实工程不存在依赖。CLI 仅加载新鲜图且要求两端已注册为图节点。

## 5. 发布、存储与并发

`.engineering/generations/<content_digest>/entities.json`、`graph.json` 和 `current.json` 均为派生视图。构建先完整写入临时 generation，再原子切换 `current.json`；旧 generation 保留，读取时校验指针、generation 内容摘要及 manifest；指针存在时兼容根视图不参与读取，不发布半张图。

计算由 graph 完成，临时目录、写锁和指针发布通过 core 的 SnapshotStore 端口由 adapters 实现。指针是提交点：先写兼容视图再切换指针，失败时保留旧指针；复用同名 generation 前比较完整图与实体载荷，发现不一致则拒绝发布。兼容视图不是事务性接口；查询旧 generation 时必须检查输入版本。遗留临时文件不可视为成功快照；当前尚未保证断电后目录项持久性。

读取当前或指定历史 generation 时，除内容摘要、解析配置和输入清单外，还校验节点、边、来源、置信度与 `verified` 的最小结构。损坏记录返回 `EPE-GRAPH-SHAPE`/历史读取诊断，不让查询消费者把坏边当作“无路径”。

默认允许依赖表禁止 graph 直接依赖 parsers/adapters；当前本地实现中的兼容导入已在 `engineering/policies/architecture.yaml` 的 `allowed_imports` 显式记录，作为待重构例外，并由架构检查追踪。Python 相对导入按纳管代码根和包层级解析；`from package import module` 在目标唯一时不猜测多个候选并保留 unknown 诊断。

## 6. V0.3 影响传播

代码变化经 `realizes` 反向寻找设计，再沿消费者依赖和验证关系找到契约、测试和 Evidence；设计变化经 `realizes` 正向找到实现。`depends_on` 的消费者影响采用反向遍历。

传播矩阵草案：`realizes` 双向，`depends_on` 反向，`verified_by`、`evidenced_by`、`conforms_to`、`specifies`、`affects` 正向；其余关系不自动传播。Source 与其图内 Symbol 按路径双向关联。推断或未知来源、低于 1 的置信度及缺失置信度使整条后续路径保持候选，同一节点另有确定路径时可升级；此处的确定性描述传播所依赖的来源和置信度，不代表关系的 `verified` 状态或审批通过。缺失起点或动态依赖等静态盲区使报告标记 incomplete。

每个结果记录起点、传播路径、关系来源、确定/候选类别和原因。限制遍历预算、去重及循环；触及预算上限标为 truncated，不能声称召回完整。对删除节点使用变更前快照，否则会丢失旧依赖。历史分析需要当前图新鲜，分别返回历史与当前报告；用户指定完整 generation 摘要及可选的新实体 ID，系统验证历史快照自洽但不推断它与当前图的时间邻接或实体身份。历史结果不能作为当前无影响证明。

增量计划仅对完整且摘要、代码事实覆盖、解析器版本、Python 版本及代码根一致的快照计算差异；不兼容或损坏时返回全量重建。增量更新必须与同输入全量重建比较内容等价；发现解析器版本、Schema、包根或规则变化时可回退全量重建。无法确定时扩大范围而非自动复用 Evidence。

## 7. 验证设计

- 多次打乱输入顺序，快照内容一致；缓存删除后仍可重建。
- 输入含悬空边或解析 incomplete 时拒绝完整快照发布。
- 两个模块构成循环时返回可解释路径；无法解析导入保留未知项。
- 构建中断或第二写者进入，读者仍只见上一完整 generation。
- V0.3 比较设计变更、代码变更、删除/移动实体的传播结果与独立标注集合。
- 影响预算耗尽后返回部分结果与截断标志，不能清空未知范围。

拟议测试位置：`tests/unit/graph/`、`tests/integration/graph_snapshot/`。

## 8. 工作包与交付条件

WP-05 交付基础图；WP-10 验证发布与恢复；WP-12 交付双向影响和增量等价性。V0.2 不以 impact analyze 命令尚未实现阻塞基础 MVP，但必须明确 unsupported。

交付条件：可重建、带来源、可解释依赖、无部分发布，满足 AC-10；后续影响准确性指标使用独立基准，不以自身图作为唯一真值。

上游：core 注册快照与解析事实。下游：verification、context 和查询命令。返回[模块索引](../README.md)。

### 增量事实复用的完整性约束

增量构图仅复用内容摘要、清单摘要、代码事实覆盖及文件摘要一致，且解析器版本、Python 主次版本和代码根匹配的完整快照；旧格式或不一致的快照回退全量解析。复用时保留解析诊断与动态依赖盲区。发布前核对解析事实与当前输入清单；缺项、重复、解析不完整或输入摘要变化时拒绝发布。摘要只检测未同步的意外损坏，不能认证可被任意修改并重新计算摘要的缓存；派生缓存应由可信环境管理。
