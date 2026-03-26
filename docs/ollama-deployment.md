# Ollama 部署与本地大模型配置

本文说明如何在本机安装并运行 [Ollama](https://ollama.com/)，拉取与本项目匹配的**对话模型**与**嵌入模型**，并完成与 Adaptive-GraphRAG 的对接。

---

## 1. 本项目对 Ollama 的依赖

| 用途 | 说明 | 环境变量 |
|------|------|----------|
| 对话与结构化抽取 | 回答用户问题、文档摘要、从文本块抽取实体关系 | `LLM_MODEL` |
| 文本向量 | ChromaDB 通过 Ollama 调用嵌入接口，为 PDF 分块建索引 | `EMBEDDING_MODEL` |

服务地址默认 `http://localhost:11434`，对应环境变量 `OLLAMA_HOST`。

---

## 2. 安装 Ollama

### macOS / Windows

从官网下载安装包：<https://ollama.com/download>

安装完成后，菜单栏或系统托盘应出现 Ollama 图标；首次使用会自动在后台启动服务。

### Linux

```bash
curl -fsSL https://ollama.com/install.sh | sh
```

安装后通常以 systemd 用户服务或手动 `ollama serve` 方式运行，详见 [官方 Linux 文档](https://github.com/ollama/ollama/blob/main/docs/linux.md)。

### 验证服务是否可用

```bash
curl -s http://localhost:11434/api/tags
```

若返回 JSON（含 `models` 列表），说明 HTTP 服务正常。

---

## 3. 拉取推荐模型

Adaptive-GraphRAG 需要**两类**模型（名称需与 `.env` 中一致）：

### 3.1 对话模型（LLM）

用于问答、摘要、实体关系抽取。示例（任选其一或按本机资源调整）：

```bash
ollama pull llama3.1:8b
# 或其他，例如：ollama pull qwen2.5:7b
```

### 3.2 嵌入模型（Embedding）

用于向量检索，**必须**与 `EMBEDDING_MODEL` 一致，推荐使用：

```bash
ollama pull nomic-embed-text
```

### 查看已安装模型

```bash
ollama list
```

列表中的 **NAME** 列（如 `llama3.1:8b`、`nomic-embed-text:latest`）写入 `.env` 时，一般使用**不含 `:latest` 的短名**即可（与 `ollama run` 一致）；若只显示带标签名，可复制完整名到 `LLM_MODEL`。

---

## 4. 与项目配置对齐

1. 复制环境变量模板：

   ```bash
   cp .env.example .env
   ```

2. 编辑 `.env`，至少检查以下项：

   | 变量 | 建议 |
   |------|------|
   | `OLLAMA_HOST` | 本机默认 `http://localhost:11434`；若 Ollama 跑在另一台机器，改为该机 IP + 端口 |
   | `LLM_MODEL` | 与 `ollama list` 中对话模型名称一致，例如 `llama3.1:8b` |
   | `EMBEDDING_MODEL` | 与已拉取的嵌入模型一致，例如 `nomic-embed-text` |

3. 可选：`config.py` 中的默认值会在未设置 `.env` 时生效；**以 `.env` 为准**时，请保证变量名与 [pydantic-settings](https://docs.pydantic.dev/latest/concepts/pydantic_settings/) 的字段对应（本项目使用大写环境名，如 `LLM_MODEL`）。

---

## 5. 快速自测

### 对话

```bash
ollama run llama3.1:8b "用一句话介绍 RAG"
```

将 `llama3.1:8b` 换成你的 `LLM_MODEL`。

### 嵌入（HTTP）

```bash
curl -s http://localhost:11434/api/embed -d '{"model":"nomic-embed-text","input":"test"}' | head -c 120
```

应返回包含 `embeddings` 的 JSON，而非 404。

---

## 6. 资源与选型建议

- **内存**：8B 级别模型建议 **≥16GB** 系统内存；更小模型（如 3B）可降低要求。
- **GPU**：有 NVIDIA GPU 时 Ollama 会自动尝试 GPU 加速；无 GPU 时以 CPU 运行，首次推理可能较慢。
- **仅 CPU**：可选用参数量更小的模型，或接受较长响应时间。

更多模型列表见：<https://ollama.com/library>

---

## 7. 常见问题

### 连接被拒绝（Connection refused）

- 确认 Ollama 应用已启动，或 Linux 上已执行 `ollama serve`。
- 防火墙是否放行 `11434`（远程访问时）。

### 项目报错 404（嵌入或对话）

- **模型未下载**：对应用 `ollama pull <模型名>`。
- **名称不一致**：`LLM_MODEL` / `EMBEDDING_MODEL` 必须与 `ollama list` 中可用名称匹配。
- **嵌入**：本项目使用 Chroma 自带的 Ollama 嵌入客户端，**`OLLAMA_HOST` 只需填写根地址**（如 `http://localhost:11434`），不要手动拼接 `/api/embed` 路径。

### 远程 Ollama

若推理服务跑在局域网其他主机：

1. 在该主机上配置 Ollama 监听 `0.0.0.0:11434`（需查阅 Ollama 官方文档中的环境变量，如 `OLLAMA_HOST`）。
2. 在本项目 `.env` 中设置 `OLLAMA_HOST=http://<服务器IP>:11434`。

注意网络安全，避免将未鉴权的 Ollama 暴露到公网。

---

## 8. 参考链接

- Ollama 官网：<https://ollama.com/>
- API 说明：<https://github.com/ollama/ollama/blob/main/docs/api.md>
- 模型库：<https://ollama.com/library>

完成上述步骤后，回到仓库根目录执行 `python main.py` 即可启动 Adaptive-GraphRAG。
