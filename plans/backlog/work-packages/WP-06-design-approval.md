# WP-06：设计、契约与批准适用性

**状态：** in_progress · **里程碑：** M2 · **实施：** in_progress
**负责模块：** [design](../../../docs/modules/design/README.md)、adapters
**前置：** WP-03；公共记录契约来自 WP-01 · **下游：** WP-07、WP-09
**说明：** 不依赖完整图（WP-05）；可与 WP-05 部分并行，但可信身份依赖 adapters。

## 1. 目标

校验设计/契约完整性；计算 DesignRevision；按可信来源导入批准记录并评估是否仍适用于当前内容。design **不授予**审批权限。

## 2. 任务分解

| 子任务 | 内容 |
| --- | --- |
| T1 | 模板驱动的设计校验（模块/组件/类必填章节由配置提供） |
| T2 | 契约语法与引用校验；缺校验器 → unsupported/unknown |
| T3 | DesignRevision / 指纹（遵循 D-03/D-04） |
| T4 | Approval 导入：验证记录 Schema、身份事实、追加存储 |
| T5 | `assess_approval`：匹配 / 过期 / 撤销 / 来源未知 / 内容错误 |
| T6 | 伪造 Frontmatter `approved` 不能单独通过适用性 |
| T7 | 可信源不可确认时 High 路径明确阻断（D-15） |

## 3. 拟议路径

```text
src/epe/design/validate.py
src/epe/design/contracts.py
src/epe/design/fingerprint.py
src/epe/design/approval.py
src/epe/adapters/identity.py
# 审计目录以 WP-01 D-02 为准，例如：
reports/approvals/   # 或冻结后的等价路径
tests/unit/design/
tests/fixtures/design_cases/
```

## 4. 适用性矩阵

| 条件 | ApprovalAssessment |
| --- | --- |
| 指纹匹配 + 可信身份 + 未撤销 | applicable |
| 设计或引用契约已变 | stale / not_applicable |
| 记录为 revoked | revoked |
| 身份来源不在信任配置 | untrusted_source |
| 记录字段非法 | invalid_record |

权限“是否允许此人批准”由 WP-07 判定；本包只提供内容与来源事实。

## 5. 验收映射

AC-05 的批准与缺设计部分（与 governance 联合）；design 模块 §8。

## 6. 完成门槛

- [ ] 导入批准不修改被批准设计字节
- [ ] 改设计后旧批准失效有测试
- [ ] 无可信源时 High 不可确认
- [ ] 不实现 design create 模板生成也可关闭本包（可标 deferred），但 validate/approve 记录路径必须可用
