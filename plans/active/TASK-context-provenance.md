# TASK-context-provenance：上下文来源与状态

- 类型：Bugfix / Feature；高风险；范围 MOD-004 来源标记、去重与检索，相关测试和设计；不更改审批及证据判定算法。
- 依据：context §3–5、WP-13 T4。现有图邻接固定 confidence=0.9，丢失 inferred 来源和 verified 属性；证据未经有效性评估标 current；相同文件的多条选择原因丢失。
- 设计：每份正文保留 selections 数组，逐条注明选择方式、实体、关系来源、关系置信度与验证状态；推断来源不转化为已验证。设计状态标记为声明值，批准适用性未评估时为 unknown。证据新鲜度为 unknown；归档实体默认不作为邻接/关键词候选，显式请求时标 historical。相同文件保留所有原因及主体 ID，不复制正文。
- 验收：高置信推断关系仍为 inferred / 未验证；同文件多个选择理由均保留；证据不声称 current；归档仅在显式目标时带历史标记。
- 局限：context 不直接调用审批和证据适用性算法；应用编排必须显式传入 `source_assessments`。未传入时仍保持 unknown，不得据上下文标记声称已批准或有效；设计状态 draft。

- 本地验证：`PYTHONPATH=src pytest -q -o addopts=''`，93 passed；`git diff --check` 通过。执行记录见 `reports/evaluations/context-provenance.json`。

- 本轮结果：新增外部 provenance assessment 透传及缓存绑定；CLI 对任务 Evidence 使用 `evidence_validity` 生成评估，审批仍由调用方显式提供，缺失时保持 unknown。定向 18 项、全量测试结果见 `reports/evaluations/context-provenance-v2.json`。
