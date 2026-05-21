# 文革研究 Skill

文革历史研究的 RAG 工具包。基于 Chroma 向量数据库 + hybrid search（向量检索 + BM25），支持动态语料发现、分层证据检索、多来源交叉验证和溯源输出。

## 功能

- 全文索引：对 `books/文革/`、`raw/文革/`、`notes/`、`topics/`、`index/` 目录下的文本/ Markdown / JSON 文件建立向量索引
- 混合检索：语义向量 + BM25 关键词融合搜索
- 增量索引：新增或修改文件后自动重建
- 来源溯源：每条结果附带来源文件和 chunk ID

## 目录结构

```
skill/
├── SKILL.md                    ← 技能定义和学术呈现协议
├── scripts/
│   ├── rag_index.py            ← 构建/更新 Chroma 索引
│   ├── rag_search.py           ← 混合检索（向量 + BM25）
│   ├── search_corpus.py        ← 关键词回退搜索
│   └── inventory.py            ← 语料库盘点
├── references/
│   └── note_schema.md          ← 读书笔记模板
└── README.md                   ← 本文件
```

## 快速开始

### 1. 准备知识库

在你的知识库根目录下（默认为 `~/wenge-knowledge-base`）放置书籍文本：

```
knowledge-base/
├── books/文革/           ← 书籍文本（.txt / .md / .json）
├── raw/文革/             ← OCR 提取的原始文本
├── notes/                ← 研究笔记
├── topics/               ← 专题文件
└── index/                ← 目录索引
```

可以通过环境变量 `WENGE_KB_ROOT` 指定其他路径。

### 2. 安装依赖

```bash
pip install chromadb sentence-transformers rank-bm25
```

### 3. 建立索引

```bash
python3 scripts/rag_index.py --root "$WENGE_KB_ROOT"
```

### 4. 搜索

```bash
# 混合检索
python3 scripts/rag_search.py --root "$WENGE_KB_ROOT" --top-k 12 "搜索关键词"

# 展开上下文
python3 scripts/rag_search.py --root "$WENGE_KB_ROOT" --expand "source_file#chunk_index"

# 关键词回退搜索
python3 scripts/search_corpus.py --root "$WENGE_KB_ROOT" --any "关键词"
```

## 在 Claude Code 中使用

将本仓库克隆到 `~/.agents/skills/wenge-research/` 或 `~/.claude/skills/wenge-research/`，Claude Code 会自动识别。每个命令需要指定 `--root` 参数指向你的知识库。

## 接驳 ChatGPT Plus（免审查方案）

本 skill 的 RAG 索引可通过本地 API 桥接至 ChatGPT Plus 的 Custom GPT，从而：

- **用 GPT 的输出质量 + 你的本地书库数据**
- **避免某些模型的审查过滤**（仅在你使用的模型有审查限制时需要此方案。例如：Claude Code 接入 DeepSeek V4 等中国本地模型时会遇到审查过滤；ChatGPT Plus 本身对中国敏感内容几乎没有任何限制，不需要此桥接方案也能自由讨论）

### 架构

```
ChatGPT (Custom GPT)
  ↓ Action 调用
ngrok（公网隧道）
  ↓
本地 RAG API 服务
  ↓
Chroma 向量索引（你的书库）
```

### 步骤

1. 将 `scripts/rag_search.py` 封装为 Flask API（详见 [rag-gpt-bridge](https://github.com/your-org/rag-gpt-bridge) 项目）
2. 用 ngrok 暴露本地端口到公网
3. 在 ChatGPT Plus 中创建 Custom GPT，配置 Action 指向 ngrok URL
4. 在 Instructions 中写入「学术呈现协议」的十二条规则

详细搭建方案见 [`rag-gpt-bridge/PLAN.md`](../rag-gpt-bridge/PLAN.md)（同一仓库下的配套项目）。

### 为什么这个方案有效

- ChatGPT Plus 的 Custom GPT 可以调用外部 API，包括你的本地 RAG 服务
- GPT Plus 模型对中国文革相关内容几乎没有过滤拦截，可以自由输出
- 你的书库数据在你本地，不需要上传给任何第三方
- 学术呈现协议（SKILL.md 中的十二条）保证了输出质量
- **注意**：此桥接方案仅在 Claude Code 接入有审查限制的模型（如 DeepSeek V4）时需要。如果你使用的是没有审查限制的模型（如直接使用 ChatGPT Plus、或 Claude Code 接入 Claude 模型），则不需要此桥接方案

## License

MIT
