# 知识库检索

**一套运行在本地的通用知识问答系统。装进 AI 编程工具，你可以直接跟你的书"聊天"。**

把书、笔记、文献放进本地文件夹，它就自动读完、记住、建立索引。之后你在聊天窗口提问，它像读过你所有书的研究助手一样跟你讨论——你可以问具体细节、比较不同书的说法、追问上下文、让它在多个来源之间做分析。每一段回答都标注来自哪本书，可以追溯到原文核实。

你不需要学任何操作，打字问就行。装一个 Skill，换一套书，就是一个新的知识库。

---
## 具体使用场景

### 文革研究

2026 年是文革爆发 60 周年。关于文革的材料汗牛充栋，围绕这段历史的立场分歧也极为尖锐。由于众所周知的原因，官方叙事对此讳莫如深，这更增加了从事实层面了解这段历史的难度。

本项目中已收录了关于文革的各类著作——学术通史、回忆录、档案汇编等，涵盖不同立场和视角。你也可以自行添加更多材料。系统运行在你的本地电脑上，通过语义搜索定位相关内容，并追溯到原文。

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

---

## 准备知识库

在 `~/knowledge-base` 目录下建好文件夹，把你的材料拖进去：

- `books/你的专题/` — 书籍文本（如 `books/历史/`、`books/哲学/`）
- `raw/你的专题/` — OCR 提取的原始文本
- `notes/` — 读书笔记
- `topics/` — 专题文件

> 如果你的知识库在其他位置，可以设置环境变量 `KB_ROOT` 指向它。例如知识库在 `D:\我的书`，就在终端运行：
> ```bash
> export KB_ROOT=/Users/你的用户名/我的书   # Mac
> $env:KB_ROOT="D:\我的书"                     # Windows
> ```

---

## 安装方法

### 如果你已经有 AI 编程工具

在终端粘贴下面这行命令，它会把 Skill 装到你的电脑上：

```bash
curl -fsSL https://raw.githubusercontent.com/shuiqiu94-creator/local-knowledge-search/main/install.sh | bash
```

装好之后打开聊天窗口，说"调用 local-knowledge-search 这个 Skill"，就可以直接提问了。

> 或者，你也可以把这个仓库文件夹设为 VS Code 的工作区，打开 Claude Code 聊天窗口输入"安装这个 Skill"，它会自动完成安装。

### 从零开始：配置 VS Code + Claude Code + DeepSeek

### 第 1 步：装 VS Code

**Mac 用户：** 打开 [code.visualstudio.com](https://code.visualstudio.com/)，下载 Mac 版安装包，拖到 Applications 文件夹。

**Windows 用户：** 打开 [code.visualstudio.com](https://code.visualstudio.com/)，下载 Windows 版安装包，双击安装（一路点"下一步"就行）。

### 第 2 步：获取 API Key（DeepSeek 的钥匙）

打开 [platform.deepseek.com/api_keys](https://platform.deepseek.com/api_keys)，登录后点"创建 API Key"，复制保存。这个 Key 就是 DeepSeek 的"钥匙"，后面配置要用。

### 第 3 步：配置环境变量（告诉电脑用 DeepSeek）

**Mac 用户：**

打开"启动台"搜索"终端"并打开，依次运行以下命令（把 `你的Key` 换成第 2 步复制的）：

```bash
echo 'export ANTHROPIC_BASE_URL=https://api.deepseek.com/anthropic' >> ~/.zshrc
echo 'export ANTHROPIC_AUTH_TOKEN=你的Key' >> ~/.zshrc
echo 'export ANTHROPIC_MODEL=deepseek-v4-pro' >> ~/.zshrc
echo 'export ANTHROPIC_DEFAULT_OPUS_MODEL=deepseek-v4-pro' >> ~/.zshrc
echo 'export ANTHROPIC_DEFAULT_SONNET_MODEL=deepseek-v4-pro' >> ~/.zshrc
echo 'export ANTHROPIC_DEFAULT_HAIKU_MODEL=deepseek-v4-flash' >> ~/.zshrc
echo 'export CLAUDE_CODE_SUBAGENT_MODEL=deepseek-v4-flash' >> ~/.zshrc
echo 'export CLAUDE_CODE_EFFORT_LEVEL=max' >> ~/.zshrc
source ~/.zshrc
```

**Windows 用户：**

搜索"PowerShell"并打开，依次运行以下命令（把 `你的Key` 换成第 2 步复制的）：

```powershell
$env:ANTHROPIC_BASE_URL="https://api.deepseek.com/anthropic"
$env:ANTHROPIC_AUTH_TOKEN="你的Key"
$env:ANTHROPIC_MODEL="deepseek-v4-pro"
$env:ANTHROPIC_DEFAULT_OPUS_MODEL="deepseek-v4-pro"
$env:ANTHROPIC_DEFAULT_SONNET_MODEL="deepseek-v4-pro"
$env:ANTHROPIC_DEFAULT_HAIKU_MODEL="deepseek-v4-flash"
$env:CLAUDE_CODE_SUBAGENT_MODEL="deepseek-v4-flash"
$env:CLAUDE_CODE_EFFORT_LEVEL="max"
```

### 第 4 步：安装 Claude Code 插件

打开 VS Code，按快捷键打开扩展商店：
- **Mac 用户：** 按 `Cmd+Shift+X`
- **Windows 用户：** 按 `Ctrl+Shift+X`

搜索 **Claude Code**，点绿色的"Install"。安装后左侧会出现一个 Claude 图标。

### 第 5 步：打开聊天窗口安装 Skill

点左侧的 Claude 图标，在聊天窗口里输入：

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
- GPT Plus 模型对中国敏感内容几乎没有过滤拦截，可以自由输出
- 你的书库数据在你本地，不需要上传给任何第三方
- 学术呈现协议（SKILL.md 中的十二条）保证了输出质量
- **注意**：此桥接方案仅在 Claude Code 接入有审查限制的模型（如 DeepSeek V4）时需要。如果你使用的是没有审查限制的模型（如直接使用 ChatGPT Plus、或 Claude Code 接入 Claude 模型），则不需要此桥接方案

## License

MIT
