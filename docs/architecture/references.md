# 参考资料与证据边界

以下来源来自项目初始方案，供后续规格和实现借鉴。本次文档整理未执行联网核查；外部项目当前能力、论文内容和统计数字均需进一步确认。

| 来源 | 拟借鉴内容 |
| --- | --- |
| [GitHub Spec Kit](https://github.github.com/spec-kit/) | Constitution、规格、计划与开发工作流 |
| [AWS Kiro](https://aws.amazon.com/documentation-overview/kiro/) | Steering、规格与 Agent Hooks |
| [RepoDoc](https://arxiv.org/abs/2604.26523) | 工程知识图谱、文档生成与增量维护 |
| [ARDoCo](https://ardoco.de/) | 架构文档、模型与代码的追溯 |
| [Pact](https://docs.pact.io/) | 消费者与提供者之间的可执行交互契约 |
| [Building Evolutionary Architectures](https://www.oreilly.com/library/view/building-evolutionary-architectures/9781492097532/ch04.html) | 架构适应度函数与持续治理 |
| [Google：Grounding AI Agents in Contracts](https://research.google/pubs/grounding-ai-agents-in-contracts-an-empirical-evaluation-of-spec-driven-test-generation/) | 契约约束下的测试生成 |

## 待核实研究主张

初始方案提及以下结果，保留为核查线索，不作为本项目已验证结论：

- ARDoCo / TransArC 在五个开源项目上报告约 0.82 的文档到代码追溯 F1；需确认论文版本、任务定义和实验范围。
- “Specification Artifacts in Open-Source Pull Request Workflows Do Not Reduce Defects” 涉及 119 个仓库和 88,052 个 PR；需补齐正式论文链接、研究设计及规格工件定义。
- Google 契约约束测试生成研究报告缺陷检出率提高 9.8 个百分点、分支覆盖率提高 2.5 个百分点；需核对基线、统计不确定性和生产 Bug 评估条件。
- RepoDoc 的增量维护与 Spec Kit 的多工作流能力需核对对应版本，不能将本项目目标功能归因于未经确认的现有能力。

即便上述结果被确认，也不能直接推导“BTAE 优于 SDD”。规格工件存在与完整规格驱动流程不同，测试生成收益与长期架构维护收益也不同；本项目采用独立对照与消融实验验证自身假设。
