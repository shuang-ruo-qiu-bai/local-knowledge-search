# 知识库检索

**一套运行在本地的通用知识问答系统。基于语义搜索，支持跨书对比、溯源引用。**

装进 AI 编程工具，把你的书放进文件夹，就可以向 AI 提问，它会从书中找到相关内容、对比不同来源、标注出处。

---
## 具体使用场景

### 文革研究

2026 年是文革爆发 60 周年。关于文革的材料汗牛充栋，围绕这段历史的立场分歧也极为尖锐。由于众所周知的原因，官方叙事对此讳莫如深，这更增加了从事实层面了解这段历史的难度。

本项目中已收录了关于文革的各类著作——学术通史、回忆录、档案汇编等，涵盖不同立场和视角。你也可以自行添加更多材料。系统运行在你的本地电脑上，通过语义搜索定位相关内容，并追溯到原文。

---

## 功能

- **提问式检索**：直接问，不用翻书找
- **跨书对比**：同一件事在不同书里怎么说，摆在一起看
- **来源溯源**：每段答案都标注来自哪本书，可追溯到原文
- **混合搜索**：语义理解 + 关键词匹配，找得更准
- **增量索引**：新增文件自动重建，不用每次都全量重跑

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

## 快速上手

### 第 1 步：装 VS Code

**Mac 用户：** 打开 [code.visualstudio.com](https://code.visualstudio.com/)，下载 Mac 版安装包，拖到 Applications 文件夹。

**Windows 用户：** 打开 [code.visualstudio.com](https://code.visualstudio.com/)，下载 Windows 版安装包，双击安装（一路点"下一步"就行）。

### 第 2 步：安装 Claude Code 插件

打开 VS Code，按快捷键打开扩展商店：
- **Mac 用户：** 按 `Cmd+Shift+X`
- **Windows 用户：** 按 `Ctrl+Shift+X`

在搜索框输入 **Claude Code**，点击绿色的"Install"按钮。安装后左侧会出现一个 Claude 图标，点击它就能打开聊天窗口，像 ChatGPT 一样直接打字提问。

### 第 3 步：获取 API Key

打开 [platform.deepseek.com/api_keys](https://platform.deepseek.com/api_keys)，登录后点"创建 API Key"，复制保存。

### 第 4 步：配置 DeepSeek V4

告诉 Claude Code 用 DeepSeek 的地址和你的 Key。

**Mac 用户：**

打开终端（在"启动台"搜索"终端"），依次运行以下命令（把 `你的Key` 换成第 3 步复制的）：

```bash
echo 'export ANTHROPIC_BASE_URL=https://api.deepseek.com/anthropic' >> ~/.zshrc
echo 'export ANTHROPIC_AUTH_TOKEN=你的Key' >> ~/.zshrc
echo 'export ANTHROPIC_MODEL=deepseek-v4-pro' >> ~/.zshrc
echo 'export CLAUDE_CODE_SUBAGENT_MODEL=deepseek-v4-flash' >> ~/.zshrc
source ~/.zshrc
```

**Windows 用户：**

搜索"PowerShell"并打开，依次运行以下命令（把 `你的Key` 换成第 3 步复制的）：

```powershell
$env:ANTHROPIC_BASE_URL="https://api.deepseek.com/anthropic"
$env:ANTHROPIC_AUTH_TOKEN="你的Key"
$env:ANTHROPIC_MODEL="deepseek-v4-pro"
$env:CLAUDE_CODE_SUBAGENT_MODEL="deepseek-v4-flash"
```

### 第 5 步：在聊天窗口安装 Skill

回到 VS Code，点左侧的 Claude 图标打开聊天窗口，输入：

```
安装 https://github.com/shuiqiu94-creator/local-knowledge-search 这个 Skill
```

Claude Code 会自动下载安装，你什么都不用做。

### 第 6 步：开始使用

安装完成后，在聊天窗口直接提问就行。

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
