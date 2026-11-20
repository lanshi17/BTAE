# 设计生成与契约校验

- 类型：Feature；风险：medium；涉及 MOD-005、MOD-008；依据 SPEC-001 CLI 及设计模块契约。
- `epe design create` 按支持的实体前缀写入安全草案模板，创建前预检路径和 ID，使用独占创建，不覆盖已有权威文件。`design validate` 计算 `epe-design-revision-v2`，契约引用必须存在且 YAML 中的 JSON Schema 可被当前校验器接受。
- 设计和契约在当前仓库均有实体/测试/CLI 追溯；不支持的语言契约和语义 D3 检查仍必须返回明确未知或未支持。

## 本地验证

此前 `PYTHONPATH=src python -m pytest -q`：37 项通过，覆盖设计生成幂等、实体发现、设计 revision、契约合法/非法 Schema、CLI 集成和审批签名；后续总体验证已扩展到 47 项，见 `reports/evaluations/iteration-all-modules-002.json`。
