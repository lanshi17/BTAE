---
id: CLASS-PARSER-001
type: Class
name: Python AST Parser
design_status: reviewed
implementation_status: implemented
verification_status: passed
implementation:
  - path: src/epe/parsers/python.py
    symbol: parse_python
verification:
  - test_id: TEST-PARSER-001
    path: tests/unit/test_parsers.py
---

# Python AST Parser

解析器只消费字节并产生符号、静态导入和盲区事实；它不 import 目标模块、不执行顶层代码，也不把路径自动提升为工程实体身份。

语法错误会使当前文件结果不完整。动态导入、反射和星号导出以 warning/analysis gap 保留，交给图与门禁决定是否需要扩大检查范围。
