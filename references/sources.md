# 来源和设计审查

2026-10-13 根据 NakanoIchirou 的设计讨论与明确要求编写，重点包括三层取代早期四层、客观史不随遗忘消失、T＜0 统一、手动批量归档、检查点幕后补全、玩家名单决定权及低负担 Grill Me。最新确认的核心设计优先于早期扩展建议。

本版依据可读取的原讨论重新编写。早期 v0.1 附件正文没有取得，因此不将本版称为该附件的逐行修订。私人讨论及其链接不包含在公开发布包中。

find-skills 查找 `agent memory` 与 `context compression` 后，核查了以下上游原文，而非只看搜索标题：

| 来源 | 借鉴 | 本版不采用 |
| --- | --- | --- |
| [LangChain deep-agents-memory](https://github.com/langchain-ai/langchain-skills/blob/main/config/skills/deep-agents-memory/SKILL.md) | 草稿与跨会话持久记录分开；读取范围明确 | 不安装框架，不以路径前缀路由证明硬隔离 |
| [Agentmemory remember](https://github.com/rohitg00/agentmemory/blob/main/plugin/skills/remember/SKILL.md) | 保留具体概念、来源及版本替代线索 | 不让自动去重代替玩家批准，不把编码知识库视作角色认知 |
| [context-compression](https://github.com/muratcankoylan/Agent-Skills-for-Context-Engineering/blob/main/skills/context-compression/SKILL.md) | 只合并增量；保留标识符；评估完整任务成本 | 不逐轮检测阈值，不将其他任务压缩率移植为叙事保证 |
| [Smart Memory](https://github.com/senjinthedragon/Smart-Memory) | 场景归档、跨章节事件进展、来源定位 | 不采用默认自动运行、多记忆层、角色卡并行权威 |

检视 [epistemic.js](https://github.com/senjinthedragon/Smart-Memory/blob/main/epistemic.js) 的 `buildEpistemicBlock`：它会将 unaware 内容及 believes-but-false 信息写入角色提示词。这里模型实际看到了不应知道的客观信息；本版只导出获准第三层内容，真伪、原因和未知秘密留在世界侧。

三层设计可自洽的前提是：宏观层不等于全部事件，第三层不等于全部历史心理档案的直接注入，事实与AI心理推断不能混合，版本和原文溯源不另立叙事权威。引用标识用于关联三层内的共同事件，不建立第四份完整故事。

本版的 JSON 文件工具仅为可回滚操作与角色包检查提供机械辅助；摘要仍是 LLM 按 Skill 做的语义提取。没有复制上游实现，没有安装这些候选 Skill，没有新增 API 服务、数据库或向量检索。
