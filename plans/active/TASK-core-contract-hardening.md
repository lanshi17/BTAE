# Core 关系与生命周期契约强化

- 类型：Bugfix；风险：medium；涉及 MOD-001、MOD-002、MOD-007。
- `verified` 关系必须有 verifier、method、timestamp、version；状态迁移必须带 expected revision 并返回新对象，不修改调用方快照。
- 本地测试覆盖缺字段、完整验证事实、revision 冲突和不可变迁移。
