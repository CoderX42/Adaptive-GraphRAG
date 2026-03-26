# 开源 RAG 项目整理

> 整理时间：2026-03

---

## 全栈 / 框架

| 项目 | GitHub | Stars | 特点 |
|------|--------|-------|------|
| **LangChain** | [langchain-ai/langchain](https://github.com/langchain-ai/langchain) | 65k+ | 全能型 LLM 开发框架，RAG 是核心模块之一 |
| **LlamaIndex** | [run-llama/llama_index](https://github.com/run-llama/llama_index) | 40k+ | 最流行的 RAG 框架，数据连接能力强，高度可定制 |
| **RAGFlow** | [infiniflow/ragflow](https://github.com/infiniflow/ragflow) | 22k+ | DeepWiki 出品，UI 友好，支持中文，Deep Search |
| **Quivr** | [Quivr/Quivr](https://github.com/Quivr/Quivr) | 20k+ | 定位"第二大脑"，专注个人知识库 |

---

## 轻量 / 专注检索

| 项目 | GitHub | Stars | 特点 |
|------|--------|-------|------|
| **FastRAG** | [IntelLabs/fastRAG](https://github.com/IntelLabs/fastRAG) | 3k+ | Intel 出品，优化检索效率，适合生产环境 |
| **AutoRAG** | [Marker-Inc-Korea/AutoRAG](https://github.com/Marker-Inc-Korea/AutoRAG) | 2k+ | 自动评估和优化 RAG 管道，选择最佳 RAG 策略 |
| **haystack** | [deepset-ai/haystack](https://github.com/deepset-ai/haystack) | 15k+ | deepset 出品，模块化 NLP 管道，支持多种数据库 |

---

## GraphRAG 专项

| 项目 | GitHub | Stars | 特点 |
|------|--------|-------|------|
| **Microsoft GraphRAG** | [microsoft/graphrag](https://github.com/microsoft/graphrag) | 20k+ | 微软开源，基于知识图谱的全局检索，实体抽取 + 社区摘要 |
| **Neo4j RAG** | [neo4j/neo4j-apoc-procedures](https://github.com/neo4j/neo4j-apoc-procedures) | - | 图数据库 + RAG 结合 Cypher 查询 |

---

## 对比参考

| 维度 | Adaptive-GraphRAG | LangChain / LlamaIndex | Microsoft GraphRAG | RAGFlow |
|------|-------------------|------------------------|------------------|---------|
| 部署难度 | **极低**（Ollama 一键） | 中等 | 高（需 Azure / OpenAI） | 中等 |
| 本地运行 | **✅ 完全本地** | 需自行配置 | 依赖云 API | 需 GPU |
| 知识图谱 | **✅ NetworkX** | 需额外集成 | ✅ 原生支持 | 有限 |
| 自适应路由 | **✅** | ❌ | ❌ | ❌ |
| UI 界面 | **✅ Gradio** | ❌ | ❌ | ✅ 好看的 UI |

---

## 总结

- **追求功能全面**：选 LangChain / LlamaIndex，生态成熟但有一定学习曲线
- **追求图谱能力**：选 Microsoft GraphRAG，适合大规模数据集的全局理解
- **追求快速部署**：选 RAGFlow，开箱即用 UI 好看
- **追求极简本地**：选 Adaptive-GraphRAG，无需 GPU，一条命令跑起来
