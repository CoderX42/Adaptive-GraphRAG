Adaptive-GraphRAG

自适应知识图谱增强检索系统 —— 让 RAG 从"死记硬背"升级为"关系推理"

---

## 一句话定位

一个轻量级、本地优先的智能文档问答系统，通过**自适应路由**动态选择检索策略（向量/图谱/混合），结合轻量级 GraphRAG 实现多跳关系推理，解决传统 RAG 无法回答"XX 和 YY 是什么关系"类问题的痛点。

---

## 核心创新点

| 特性 | 传统 RAG | 本项目 (Adaptive-GraphRAG) |
|------|---------|--------------------------|
| 检索策略 | 单一向量检索，一视同仁 | 智能路由：根据查询复杂度自动选择 Vector / Graph / Hybrid 模式 |
| 关系能力 | 无法推理实体关联 | 轻量 GraphRAG：基于 NetworkX 构建动态知识图谱，支持多跳路径推理 |
| 部署成本 | 依赖 OpenAI API / GPU | 零配置本地跑：Ollama 本地模型 + ChromaDB 文件存储，无需 Docker 和显卡 |

---

## 技术架构

```
用户请求 (Gradio UI / REST API)
         │
         ▼
   QueryClassifier ──► 规则引擎：关键词 + 正则表达式
         │
         ├─► VectorRetriever  ──► ChromaDB + Ollama Embedding
         ├─► GraphRetriever   ──► NetworkX（最短路径 / 邻域检索）
         └─► HybridFusionRetriever ──► RRF 融合（Reciprocal Rank Fusion）
         │
         ▼
   Ollama LLM（直接调用，无 LangChain）──► 带引用生成的回答
```

**技术栈**: `FastAPI` `Gradio` `ChromaDB` `NetworkX` `PyMuPDF` `Ollama` `Pydantic`

---

## 它能做什么？

**1. 智能关系问答**

问："张三是李四的上级，那么王五（李四的下属）需要向谁汇报？"

→ 系统自动识别为复杂关系查询，触发图谱多跳推理，返回"王五 → 李四 → 张三"的汇报链

**2. 自适应策略路由**

- 包含"关系、关联、影响、导致、为什么、如何"等关键词 → **图谱模式**
- 包含"什么是、谁是、是什么时候"等模式 → **向量模式**
- 混合信号 → **混合模式（RRF 融合）**

**3. PDF 文档秒级索引**

上传 PDF → 自动分块（可配置大小与重叠）→ 向量化存储 + 实体关系抽取 → 即可开始问答

---

## 工作流程

**文档上传 pipeline**:
```
PDF 文件
  ├── extract_pdf_pages()     ──► 页级文本
  ├── chunk_pages()            ──► 重叠分块
  ├── ChromaDB (VectorStore)   ──► 向量索引
  └── build_graph_from_chunks() ──► Ollama 抽取实体/关系 → NetworkX 图谱
```

**查询 pipeline**:
```
用户查询
  ├── QueryClassifier.classify() ──► 判定检索策略
  ├── VectorRetriever / GraphRetriever / HybridFusionRetriever
  └── generate_answer() ──► Ollama 生成带引用的回答
```

---

## 快速开始

```bash
# 1. 安装 Ollama 并拉取模型
ollama pull llama3.1:8b
ollama pull nomic-embed-text

# 2. 克隆并启动
git clone https://github.com/yourname/Adaptive-GraphRAG.git
cd Adaptive-GraphRAG
pip install -r requirements.txt
cp .env.example .env
python main.py

# 3. 浏览器访问 http://localhost:8000/ui
```

**REST API 文档**: http://localhost:8000/docs

---

## 项目状态

已支持自适应路由、轻量级图谱构建、本地模型部署与 Gradio 可视化界面。

适合场景: 个人简历项目、智能文档分析原型、本地化知识库探索。