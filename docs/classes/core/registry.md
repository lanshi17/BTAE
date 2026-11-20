---
id: CLASS-REGISTRY-001
type: Class
name: Registry
design_status: reviewed
implementation_status: implemented
verification_status: pending
implementation:
  - path: src/epe/core/registry.py
    symbol: Registry
verification:
  - test_id: TEST-CORE-001
    path: tests/unit/test_core.py
---

# Registry

`Registry` 保存一次解析批次的实体和关系只读视图。它负责稳定 ID 的查找和规范化输出，不读取仓库、不执行代码，也不授予审批权限。

## 不变量

- 同一快照中实体 ID 唯一，重复声明产生诊断并拒绝发布。
- 关系先收集端点，再校验悬空端点、来源类型、置信度和自环。
- 批次失败不覆盖调用方持有的旧快照。

实现映射与关系校验由 `core.registry.build_registry` 完成；持久化由应用层负责。
