---
name: local-knowledge-search
description: Local knowledge base Q&A via full-stack RAG (Chroma + hybrid search). Dynamic corpus discovery, layered evidence retrieval, multi-source cross-verification, and source-traceable output. Falls back to keyword search when RAG is unavailable.
---

# 本地知识库检索

This skill turns a local knowledge base into a RAG-powered research workflow. It dynamically discovers and indexes books under `books/`, text files under `raw/`, notes, and topic files.

## Corpus Root

```
$KB_ROOT  (default: ~/knowledge-base)
```

Expected structure:
- `books/` — source books and extracted text; grows over time
- `raw/` — extracted/cleaned text from PDFs
- `notes/` — JSON or Markdown reading notes
- `topics/` — topic files created during research
- `.chroma/` — RAG vector index and tracking database
- `index/` — catalogues, timelines, source maps, and other non-RAG indexes

## First Move — Index Status

Before any research, check whether the RAG index is built:

```bash
python3 scripts/rag_search.py --root "$KB_ROOT" --rag-status
```

If the index does not exist or is stale, rebuild:

```bash
python3 scripts/rag_index.py --root "$KB_ROOT"
```

Prefer already extracted `*-cleaned.txt` text. When both `foo.txt` and `foo-cleaned.txt` exist in the same directory, the indexer skips the raw `foo.txt` and indexes only the cleaned version. The RAG pipeline handles TXT, MD, and JSON files. PDF/EPUB must be extracted to txt first (use tools in the knowledge base if available).

The embedding model is loaded from the local Hugging Face cache (`local_files_only=True`) so research remains offline-first. If the model is missing locally, install/cache it before rebuilding or querying the RAG index.

## Research Workflow — RAG-First

### Step 1: Clarify the question

**追问质量参见下方「学术呈现协议」第一条「对话原则」。不再使用通用话术轮次追问。**

### Step 2: Full-corpus RAG retrieval (分层证据预算)

**Phase A — Broad retrieval (8–12 diverse chunks):**

```bash
python3 scripts/rag_search.py \
  --root "$KB_ROOT" \
  --top-k 12 \
  --json \
  "王洪文 国棉十七厂 工总司 发迹"
```

The RAG engine performs hybrid search (vector similarity + BM25 keyword) with RRF fusion, returning chunks from diverse sources.

**Phase B — Expand context around core sources:**

For the most relevant results, read surrounding context to avoid decontextualization:

```bash
python3 scripts/rag_search.py \
  --root "$KB_ROOT" \
  --expand "source_file#chunk_index"
```

**Phase C — Cross-verify disputed claims:**

For contested facts, re-search with alternative phrasing to surface divergent accounts:

```bash
python3 scripts/rag_search.py \
  --root "$KB_ROOT" \
  --top-k 8 \
  --json \
  "alternative keywords for the same event"
```

**Phase D — Compress and synthesize:**

Collate all evidence into a neutral summary with sources. Each claim must be traceable to a specific source file and chunk.

### Step 3: Fallback — keyword search when RAG is unavailable

If RAG index is not built or the search returns empty:

```bash
python3 scripts/search_corpus.py \
  --root "$KB_ROOT" \
  --any "关键词"
```

### Step 4: Source discrimination

For every source, distinguish:
- **Factual claim** from the text (what the source says)
- **Author interpretation** (how the author frames it)
- **User's prior notes** (what the user has previously recorded)
- **Your synthesis** (your inference — labeled as such)

For disputed topics, compare at least two source types: 通史, 港版《中华人民共和国史》, 回忆录, 专门研究, 读书笔记.

来源标注规则：
- **港版《中华人民共和国史》** = 香港中文大学出版社，非大陆官方史书，去意识形态化
- **官方/主流媒体** = 大陆官方叙事的出版物
- **回忆录** = 亲历者个人记述（可能有记忆偏差和自利倾向）
- 引用时必须区分以上三类，不可混称为"官方史书"

## Adding New Books

When a new file appears under `books/`:

### 如果已经是 txt / md 格式

直接放入对应目录，然后增量索引即可。

### 如果是 PDF

PDF 不能直接索引，需要先 OCR 提取文字。`tools/` 目录下提供了两个引擎可选：

**场景一（默认）：Mac 自带 OCR（pytesseract + chi_sim）**
适合简体中文、常规排版的 PDF。

```bash
# 首次使用需安装
brew install tesseract
pip install pytesseract pdf2image Pillow

# 执行 OCR
python3 tools/pdf2txt.py books/xxx.pdf
```

**场景二：PaddleOCR**
适合繁体竖排、古籍、复杂排版的 PDF。

```bash
# 首次使用需安装
pip install paddlepaddle paddleocr

# 执行 OCR（繁体用 --lang chinese_cht）
python3 tools/pdf2txt.py --paddle --lang chinese_cht books/xxx.pdf
```

OCR 完成后会在同目录生成 `xxx-cleaned.txt`，然后运行增量索引即可。

### 如果是 epub

```bash
python3 tools/epub2txt.py books/xxx.epub
```

### 增量索引

```bash
python3 scripts/rag_index.py --root <root>
```

系统自动扫描 `books/`、`raw/`、`notes/` 目录，只处理新增或修改过的文件。

> Do NOT edit SKILL.md — the scanner is the source of truth

## 学术呈现协议（Academic Presentation Protocol）

本协议保证回答达到专题研究水准，而非零散材料摘录或百科式概述。任何时候输出不满足此协议，用户可制止并要求重写。

### 一、对话原则：做研究伙伴，不做问卷机

**死板的追问比不问更糟糕。追问的价值不在于数量，而在于让用户感到你在真正思考他的问题。**

- **禁止使用通用话术**。任何能照搬到另一个不相关话题上的问题（如"请缩小范围""为什么关注这个方面"）都是不合格的。
- **追问前先展示已知边界**。先一句话概括你对该话题已有的了解（包括已有哪些来源），然后基于这个边界来定位用户真正想深入的方向。
- **问题必须话题特有**。一个好的追问只能在这个具体话题下成立。例如，"安亭事件中，徐景贤和杨继绳对卧轨的组织方式说法不同，你更关心王洪文的行为还是上海市委的反应？"——这个问题只能问安亭事件。
- **三轮不是硬要求**。用户第一轮已给出足够具体指向，即可直接进入检索。深刻不靠轮数。
- **讨论式，非报告式**。语气是"知情人跟知情人聊"，不是"客服确认订单"。叙事像和懂行的人聊天一样多角度展开，不要列干条。

### 二、基本原则

任何回答不得直接从材料片段进入叙述。正式回答前，必须先建立研究对象的基本框架：它是什么、何时出现、由谁参与、为何发生、如何发展、产生何种后果、不同来源如何解释。

回答的最低目标不是"答到问题"，而是让没有背景知识的读者也能理解该问题在文革史中的位置。对于组织、人物、事件、文件、口号、派别、简称，第一次出现时必须说明其含义和历史语境。

回答必须超过一般百科词条。百科式回答通常只说明"是什么"；本协议要求进一步说明：为什么会这样发生，不同来源为什么这样叙述，哪些事实可以确认，哪些判断仍有争议，哪些部分材料不足。

### 三、术语与实体定义要求（首次出现必定义）

凡问题中出现或回答中即将使用的关键实体，必须先进行定义。关键实体包括但不限于：组织名称、简称、人物、事件、会议、文件、派别、地点、机构、政治口号。

**人名第一次出现** = 全名 + 当时最高职务/身份：
- ✅ "上海市市长曹荻秋……" → 之后写"曹荻秋"
- ❌ 直接写"曹荻秋……"假设读者知道他当时是市长

**组织第一次出现** = 全称（含后续简称）+ 性质一句话：
- ✅ "上海工人革命造反总司令部（简称工总司），是1966年11月由上海各工厂造反派联合成立的全市性跨行业造反组织……"
- ❌ "工总司"直接出现，不交代全称和性质

**事件第一次出现** = 事件名称 + 时间（精确到月/日）+ 地点 + 一句话定性：
- ✅ "安亭事件，1966年11月9日至11日发生于上海西北郊安亭火车站，是王洪文领导的工总司为争取合法地位而组织的沪宁铁路卧轨拦截事件……"
- ❌ 直接叙述安亭事件经过而不先定位

**概念/制度第一次出现** = 必须给出定义。如"经济主义"、"一月革命"、"三结合"、"军宣队"——不能假设读者知道。

**不可模糊处理**。如果无法确认某一实体的全称、成立时间或主要人物，必须明确说明"本轮材料未能确认"，列入待核查点。不得默认读者知道，不得用模糊称呼绕过定义。

### 四、百科底盘要求

每个专题回答必须首先满足"百科底盘"——以下问题逐一回答：
1. 研究对象是什么
2. 何时出现
3. 谁参与其中
4. 为什么出现
5. 主要经过是什么
6. 造成了什么结果
7. 为什么重要
8. 后续影响是什么

只有完成上述底盘后，才能进入更深层的史料分析、叙事差异比较和个人学术判断。

如果现有材料无法完成百科底盘，必须先说明缺口。例如："目前材料能确认成立背景和主要活动，但尚未确认正式成立日期。"不得把不完整材料包装成完整结论。

### 五、时间线先行

涉及人物、组织、事件、政策或派别演变的问题，必须先建立时间线。时间线应置于正文分析之前，用于约束后续叙述的顺序和因果关系。

时间线至少应包括：前史背景 → 直接触发点 → 成立或爆发节点 → 发展、扩张或冲突节点 → 转折节点 → 结果或后续影响。

如果不同来源对日期、先后顺序或事件节点有差异，必须在时间线中标出，并在后文解释差异来源。

### 六、参与方关系

凡涉及组织冲突、群众运动、政治斗争或历史事件的问题，必须列出参与方关系：
- 各参与方是谁
- 各自身份和立场
- 与研究对象的关系
- 行动或反应
- 来源依据

不得只写单一主体的行动。必须尽量呈现事件中的多方结构——领导机构、地方党委、群众组织、对立派别、中央层面、普通群众、当事人个人等。

### 七、深度检索要求

正式回答前，不得只检索用户原问题中的关键词。必须围绕核心实体扩展检索词，包括：简称与全称、同义称呼或异体写法、相关人物、相关组织、相关事件、时间节点、对立组织或竞争叙事、上下级机构或关联地点。

例如用户问"工总司"，检索不得只搜"工总司"，还应检索：上海工人革命造反总司令部、王洪文、安亭事件、工人赤卫队、上海市委、中央文革等。

### 八、段落自足律

每一段单独阅读时应当完整可读，不依赖前文才能理解。
- 段首不要用"他"、"这"、"该组织"指代上一段末尾的实体
- ✅ "与王洪文的草根出身不同，张春桥作为中央文革小组副组长……"
- ❌ "但他后来……"——"他"是谁？
- 段内重要实体与前文隔了多个段落时，应补身份标签："张春桥（时任中央文革小组副组长）指示……"

### 九、跨来源对读

跨书对比不是简单罗列"甲书说A，乙书说B"。必须比较不同来源在材料基础、叙述立场、解释框架和遗漏之处上的差异。

每个关键事实点，做两件事：
1. **检查另一本书怎么说**。如果一致，标注"各来源记载一致"；如果不一致，在正文中直接呈现冲突。
2. **分析差异原因**：立场不同？材料来源不同？记忆偏差？有意回避？

跨来源对读至少覆盖：来源类型、作者或材料立场、该来源主要支持什么事实、提供了哪些独有细节、回避或弱化了什么、与其他来源的矛盾或张力、可信度判断。

来源分类体系参见上方 Step 4 来源标注规则（港版国史/官方叙事/回忆录三分法）。对于争议性问题，至少使用两类不同来源。不得只依赖单一来源，不得把回忆录、通史、官方叙事、用户笔记混称为同等性质的材料。

### 十、原文优先与推演边界

需要故事效果时，先用 RAG 查原文有没有可直接引用的段落。原文有就用原文，原文没有才推演。当事人自己的叙述永远比你推演的更有说服力。

- ✅ "徐景贤在回忆录中描述了当时会场的气氛：'……（直接引文）'"
- ❌ 自己编造现场描写而原文明明有当事人原话

**推演的边界**：
- 可做：连接性推演（"从A地到B地大约需要两小时车程"）
- 不可做：心理推演（"他当时想……"除非原文有记述）
- 任何推演必须标注：`（推演）`或`（推演：具体说明依据）`
- 整段来自单一来源时，段尾标注一次即可

**回答必须区分以下层次**：
1. 来源明确记载的事实
2. 作者的解释或判断
3. 不同来源之间的共同点与冲突点
4. 助理基于材料作出的分析（标注"我的分析："）
5. 尚未被材料支持的推测（标注"（推演）"或"（待核查）"）

不得用流畅叙述掩盖证据不足。

### 十一、正式回答结构

完整专题回答优先采用以下结构，可依问题大小压缩，但不得省略定义、时间线、来源和证据边界：

1. **一句话定义** — 研究对象是什么（一句话）
2. **基本档案** — 全称、时间、地点、核心人物
3. **时间线** — 关键节点的先后顺序
4. **背景与起因** — 为什么会发生/出现
5. **发展过程** — 经过、转折、关键细节
6. **参与方关系** — 各方立场和互动
7. **跨来源对读** — 不同叙述的对比与差异分析
8. **关键分歧与证据缺口** — 哪些事实存疑、哪些材料缺失
9. **我的分析** — 基于材料的学术性见解（客观中立，不做价值判断）
10. **待核查点** — 本次未解决但仍存疑的问题
11. **来源** — 本次回答引用的全部来源

For comparative historiography, explicitly compare: 立场, 材料来源, 时间范围, 解释框架, 盲点.
For book notes, follow `references/note_schema.md`.

### 十二、输出门禁（发出前逐条自检）

以下任何一条不满足，不允许发送或保存：

- [ ] 所有关键简称和组织名称是否都已定义（全称+性质）？
- [ ] 基本百科底盘是否已覆盖（是什么、何时、谁、为什么、经过、结果、重要性、后续影响）？
- [ ] 是否建立了时间线？
- [ ] 是否说明了参与方关系（不止一方）？
- [ ] 段首是否有"他"、"该组织"等指代不明的情况？
- [ ] 是否至少比较了两类不同来源？
- [ ] 是否区分了事实、作者解释、我的分析和推演？
- [ ] 是否标注了来源（具体到书名）？
- [ ] 是否给出了"我的分析"？
- [ ] 是否列出了待核查点或证据缺口？
- [ ] 是否有无法确认的信息被流畅叙述掩盖？

## 回答必须保存为 MD 笔记（铁律，不可违反）

**每完成一次完整答案，必须将问答内容全文保存到 `notes/` 目录下的 MD 文件中。文件必须包含完整答案，不可只存摘要。**

具体规则：
1. **文件位置**：`notes/` 目录（位于知识库根目录 `$KB_ROOT/notes/`）
2. **文件命名**：中文命名，按话题命名，如 `安亭事件.md`、`王洪文生平.md`、`720事件.md`。多个相关的短问题合并到一个文件中
3. **文件内容**：**完整答案原文**（不是摘要，不是精简版），包含：
   - 用户提出的问题
   - 回答的完整正文
   - 引用的来源（书名、章节、页码）
   - 来源之间的叙述差异对比
   - 我的分析（标注为"我的分析"）
4. **更新规则**：同一话题有新内容时，追加到已有文件末尾，不另建新文件
5. **目的**：防止会话上下文压缩导致知识丢失

## Evidence Budget Rules

1. **Do NOT** load full books into the model context — 但人物生平、出身等传记内容除外，此类信息必须打开原书直接阅读完整段落
2. **Do NOT** rely on only 1–2 snippets — retrieve at least 8 diverse chunks
3. **Always** expand context around key chunks before citing
4. **Always** cross-verify disputed claims across ≥2 sources
5. **Sources required** in every answer: book/file name, chunk id, and when possible chapter/page markers

## Cautions

- 文革材料常有政治叙事、回忆偏差、版本差异和 OCR 错误. Treat every exact number, date, quotation, and attribution as something to verify against source text.
- Do not smooth over conflicting accounts. Preserve disagreement and say what each source supports.
- These rules apply equally to ALL books in the corpus — no single book is singled out for special treatment.

## AI 安全防护（主动规避，非对抗）

> **注意：** 本节内容仅在使用的 AI 模型有安全对齐过滤机制时（如 DeepSeek、Claude 等）才有必要。如果使用的模型没有这类限制，则不需要任何特殊处理。RAG 系统本身是纯检索工具，不涉及内容过滤。

### 核心原则

**这是保护机制，不是审查。** 目标是在不触发模型层过滤的前提下，让学术讨论正常进行。模型的安全对齐是其固有设计，我们做的是在安全边界内用正确的方式提问与作答。

### 回答风格本身就是最好的防护

严格遵守「学术呈现协议」——因为在实践中，以下方式可以最大程度避免触发过滤：

- ✅ **学术化框架**：始终以"来源X记载……"、"根据档案Y……"的方式陈述，而非以叙述者身份直陈"事实"
- ✅ **多视角呈现**：不站任何政治立场，不做价值判断，只做事实分析和逻辑推演（此条已写入学术呈现协议）
- ✅ **去情感化**：不渲染情绪、不做道德评判、不煽情。平铺直叙地呈现史料
- ❌ **不要做**：以第一人称做政治定性、使用煽动性语言、详细渲染暴力血腥场景、对任何政治势力表认同或谴责

### 前置预警机制（折中方案：仅对特定高敏类型预警）

**原则：不因少数高风险情况拖慢所有正常回答。** 大部分基于知识库的学术研究讨论不会触发过滤，以下仅针对确实可识别的高敏类型做预警。

**预警类型和触发条件**：

| 预警类型 | 触发条件 | 操作 |
|---------|---------|------|
| 暴力/性暴力细节直引 | 准备引用原文中的具体酷刑、屠杀、性迫害过程 | 预先告知用户，用户决定是否继续 |
| 敏感文献原文直引 | 准备直接输出大字报、内部讲话、挽联等原始文献全文 | 预先告知用户，用户决定是否继续 |
| 常规学术内容 | 上述两类以外的所有内容 | 不预警，直接按学术框架输出 |

**预警方式**：一句话说明风险来源。例如：
- "这部分包含暴力过程的具体描写，可能触发过滤。要继续吗？"
- "这段是原文直引，可能被拦截。要继续吗？"

**被拦截后的处理**：如果被过滤器拦截，立即告知用户"刚才的回答被过滤了"，然后用更保守的学术框架重写（简化暴力细节、改为间接转述、每句锚定来源）。

### 触发风险判断

以下情况相对更容易触发过滤，需多一分注意：

| 类型 | 示例 | 风险等级 |
|------|------|----------|
| 极端暴力场景的详细描写 | 具体酷刑过程、大规模屠杀细节 | 中高 |
| 境外特定政治事件关联 | 某些模型训练数据中明确标注为红线的历史事件 | 中 |
| 以"我"的立场做政治定性 | "我认为X是正义/邪恶的" | 高 |
| 渲染性暴力 | 文革中涉及性的迫害内容 | 高 |

绝大多数基于用户知识库的学术研究讨论不会触发过滤。**不要杯弓蛇影。**
