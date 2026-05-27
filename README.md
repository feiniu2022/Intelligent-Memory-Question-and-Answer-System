# 智能记忆问答 Agent

基于 LangGraph StateGraph 的生产级智能体，具备长期记忆、RAG 检索增强、安全护栏、用户认证、审计日志和异步 API 服务。

## 架构

```
用户输入
    ↓
┌─────────────────┐
│  input_guardrail │  ← 输入安全护栏（注入检测/长度限制/不安全内容）
└────────┬────────┘
         ↓ pass
┌─────────────────┐
│     agent       │  ← LLM ReAct 推理 + 工具调用（消息裁剪+重试）
└────────┬────────┘
         ↓ tool_calls?
┌─────────────────┐
│ inject_user_id  │  ← 自动注入 user_id 到工具参数
└────────┬────────┘
         ↓
┌─────────────────┐
│      tools      │  ← 5 个工具（记忆搜索/保存/列表 + 知识库搜索/列表）
└────────┬────────┘
         ↓
┌─────────────────┐
│   summarize     │  ← 对话历史摘要（超阈值自动压缩）
└────────┬────────┘
         ↓ (循环回 agent)
    无 tool_calls?
         ↓
┌──────────────────┐
│ output_guardrail │  ← 输出护栏（PII 脱敏：手机号/身份证/邮箱/银行卡）
└──────────────────┘
         ↓
       输出
```

## 技术栈

| 模块 | 技术 |
|------|------|
| Agent 框架 | LangGraph StateGraph + ToolNode |
| LLM | DeepSeek V4 Pro (OpenAI 兼容) |
| Embeddings | Ollama qwen3-embedding:4b |
| 向量存储 | ChromaDB |
| 混合检索 | BM25 + 向量 + RRF 融合 |
| RAG 增强 | HyDE 假设文档嵌入 (检索 score 0.64→0.91) |
| 对话持久化 | SqliteSaver |
| 用户认证 | JWT + bcrypt |
| 审计日志 | SQLite (全操作可追溯) |
| 安全护栏 | 输入注入检测 + PII 脱敏 |
| API 服务 | FastAPI + SSE 流式 |
| 配置管理 | pydantic-settings + .env |
| 日志 | 结构化 logger |

## 核心特性

- **LangGraph StateGraph**：自定义图节点（输入护栏→Agent→工具注入→摘要→输出护栏），非黑盒 `create_react_agent`
- **用户认证**：JWT 令牌 + bcrypt 密码哈希，注册/登录/鉴权完整流程
- **审计日志**：每次对话/检索/文档操作自动记录（用户/动作/时间/IP），全操作可追溯
- **对话历史摘要**：当消息超过阈值时，自动调用 LLM 压缩旧消息为摘要，防止 token 爆炸
- **混合检索记忆**：BM25 关键词 + 向量语义 + RRF 融合排序
- **RAG 流水线**：多格式文档加载（TXT/MD/PDF/DOCX/PPTX）→ HyDE 生成 → 向量检索 → 上下文增强生成
- **安全护栏**：输入端注入检测 + 长度限制 + 不安全内容拦截；输出端 PII 脱敏
- **消息裁剪**：自动保留最近 N 条消息 + system prompt
- **错误重试**：tenacity 指数退避，LLM 调用失败自动重试 3 次
- **对话持久化**：SqliteSaver 保存对话上下文，重启不丢失
- **异步 API**：FastAPI 15+ 端点，支持 SSE 流式输出
- **E2E 测试**：48 个测试用例覆盖认证/护栏/数据库/API

## 快速开始

```bash
# 1. 安装依赖
pip install -r requirements.txt

# 2. 配置环境
cp .env.example .env
# 编辑 .env，填入你的 API Key

# 3. 启动 Ollama（用于 Embeddings）
ollama pull qwen3-embedding:4b
ollama serve

# 4a. CLI 模式
python main.py

# 4b. API 服务
python server.py

# 5. 运行测试
pytest tests/ -v
```

## CLI 命令

| 命令 | 说明 |
|------|------|
| `load` | 加载 `data/txt_files/` 下所有文档到知识库 |
| `rag <问题>` | RAG 检索问答（HyDE 增强） |
| `memories` | 查看当前用户的所有长期记忆 |
| `files` | 查看已加载的知识库文件 |
| `quit` | 退出 |

## API 端点

### 认证

| 方法 | 路径 | 说明 | 认证 |
|------|------|------|------|
| POST | `/auth/register` | 用户注册 | 否 |
| POST | `/auth/login` | 用户登录 | 否 |
| GET | `/auth/me` | 获取当前用户信息 | 必须 |

### 审计

| 方法 | 路径 | 说明 | 认证 |
|------|------|------|------|
| GET | `/audit/logs` | 查询审计日志 | 必须 |

### 对话

| 方法 | 路径 | 说明 | 认证 |
|------|------|------|------|
| POST | `/chat` | Agent 对话 | 可选 |
| POST | `/chat/stream` | Agent 对话（SSE 流式） | 可选 |

### RAG

| 方法 | 路径 | 说明 | 认证 |
|------|------|------|------|
| POST | `/rag/query` | RAG 问答 | 可选 |
| POST | `/rag/query/stream` | RAG 问答（SSE 流式） | 可选 |

### 文档管理

| 方法 | 路径 | 说明 | 认证 |
|------|------|------|------|
| POST | `/knowledge/upload` | 上传文档 | 可选 |
| POST | `/knowledge/upload/multiple` | 批量上传 | 可选 |
| GET | `/knowledge/list` | 列出文档 | 可选 |
| GET | `/knowledge/search` | 搜索知识库 | 可选 |
| DELETE | `/knowledge/delete/{filename}` | 删除文档 | 可选 |
| DELETE | `/knowledge/clean` | 清空知识库 | 可选 |

> **可选认证**：携带 JWT Token 时使用 token 中的 user_id，否则使用请求参数中的 user_id（默认 default_user）

## 项目结构

```
zhinengwenda/
├── agent/
│   ├── memory_agent.py   # StateGraph Agent（图构建 + 护栏 + 裁剪 + 重试 + 摘要）
│   ├── tools.py          # 5 个工具定义
│   ├── state.py          # AgentState 类型定义
│   └── prompt.py         # 系统提示词
├── guardrails/
│   ├── input_guard.py    # 输入安全护栏（13种注入模式 + 长度限制 + 不安全内容）
│   └── output_guard.py   # 输出 PII 脱敏（手机号/身份证/邮箱/银行卡）
├── memory/
│   ├── hybrid_memory.py  # BM25+向量+RRF 混合检索
│   └── vector_store.py   # ChromaDB 封装
├── rag/
│   ├── document_loader.py # 多格式文档加载（5种格式）
│   ├── hyde.py           # HyDE 假设文档嵌入生成器
│   └── rag_service.py    # RAG 流水线
├── api/
│   ├── routes.py         # FastAPI 15 端点
│   └── schemas.py        # Pydantic 请求/响应模型
├── tests/
│   ├── test_auth.py      # 认证 E2E 测试
│   ├── test_auth_unit.py # JWT/密码 单元测试
│   ├── test_audit.py     # 审计日志 E2E 测试
│   ├── test_api.py       # API E2E 测试
│   ├── test_db.py        # 数据库 单元测试
│   └── test_guardrails.py # 护栏 单元测试
├── utils/
│   └── logger.py         # 结构化日志
├── auth.py               # JWT 认证（注册/登录/鉴权）
├── db.py                 # SQLite 数据库（用户表 + 审计日志表）
├── config.py             # pydantic-settings 配置
├── main.py               # CLI 入口（流式输出）
├── server.py             # FastAPI 入口（含 lifespan 数据库初始化）
└── .env.example          # 环境变量模板
```