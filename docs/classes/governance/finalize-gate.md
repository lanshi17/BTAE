---
id: CLASS-GATE-001
type: Class
name: Finalize Gate
design_status: reviewed
implementation_status: implemented
verification_status: passed
implementation:
  - path: src/epe/governance/gates.py
    symbol: finalize_gate
verification:
  - test_id: TEST-GATE-001
    path: tests/unit/test_finalize_gate.py
---

# Finalize Gate

完成门禁聚合设计、映射、架构、证据有效性和范围事实。任何必需项为失败、未执行、stale、invalid 或 unknown 时返回 blocked；规则计算不修改源工件。

每个配置的检查必须具有匹配任务、ChangeSet、检查器版本与参数的当前有效证据；最新有效结果失败时阻断，历史失败不会因删除而被掩盖。相同时间的多个最新结果不能可靠排序时，只要存在失败即阻断。调用方必须提供经过验证的范围事实；实际路径通过基线清单与当前文件摘要比较得到，缺少或损坏基线时不能把 Git status 当作完整范围证明。
