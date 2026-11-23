# TASK-parse-batch-contract：解析批次契约

- 类型：Feature；风险：中高；范围 MOD-002 批量解析协调器、文档解析结果元数据、测试和解析器设计；不改动现有下游字段语义。
- 依据：parsers §2–6、WP-03 T1/T6/T7。现有接口仅能逐文件解析，调用方无法统一判断部分失败、排除或输入摘要。
- 设计：新增 `ParseBatch`，包含规范化结果、成功/失败/排除/不支持统计、诊断、输入摘要和 `complete`。输入接受 `(relative_path, bytes)`；扩展名按 Markdown/YAML/Python 分发，未知扩展统计 unsupported，重复路径和越界路径产生 error。文档结果增加 `digest` 与 `source`，旧构造方式保持兼容。批次输出按路径排序、无随机 ID；任一错误或不支持项使 `complete=False`。解析器不执行输入代码、不写权威工件。
- 验收：全成功批次、语法/编码失败、未知扩展、重复路径和不支持扩展均有可定位统计；相同输入顺序不同输出相同；下游可依据 complete 阻止发布。
- 状态：draft，不构成审批。

- 本地验证：`PYTHONPATH=src pytest -q -o addopts=''`，100 passed；`git diff --check` 通过。执行记录见 `reports/evaluations/parse-batch-contract.json`。

- 契约补充：YAML/JSON 结构化结果现在与 Markdown/Python 结果统一暴露 `source`（其值为规范化相对路径），并保留 `path` 兼容字段；新增回归断言。
- JSON 扩展名使用严格 JSON 语法解析，重复对象键、非标准 NaN/Infinity 和 YAML 风格未加引号键均返回 `EPE-JSON-PARSE`，不再经 YAML 宽松解析接受。
