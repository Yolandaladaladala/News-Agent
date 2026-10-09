# XSTAR Loan News Agent — Research Rules V3

## 1. Research Objective

Agent 的目标不是简单收集新闻，而是在指定日期范围内，系统性识别对 XSTAR 及全球汽车、金融、科技产业具有重要意义的事件，经过来源核验、重要性评分、事件去重和编辑后，生成可追溯的新闻数据库及 Outlook 快报。

**核心原则：**

- Research completeness before summarization：先确保搜索覆盖，再进行总结。
- Primary sources before secondary reporting：优先一手权威来源。
- Evidence before confidence：有原文证据才能判定可信。
- Significance before volume：新闻质量优先于数量。
- No fabricated facts：不允许编造数字、日期、引用或链接。
- Human review before publication：自动筛选不等于正式发布批准。

## 2. Input Processing

支持三种输入模式，可以单独使用，也可以组合使用。

| 输入 | Agent 行为 |
|---|---|
| 日期区间 | 从零开展全球新闻研究 |
| Excel | 读取已有新闻，保留原始文字和格式，逐条检查或补充 |
| News List | 将每条标题、关键词或 URL 视为独立研究任务 |

用户提供的新闻线索必须优先处理，不得被一般关键词搜索覆盖。

如果输入包含 URL，先尝试打开原文；如果只有标题，先定位对应事件及原始报道；如果只有关键词，则执行多轮定向搜索。

**日期规则：**

- 开始和结束日期均包含在搜索区间内。
- 使用事件相关地区的当地日期判断发布日期。
- 区分事件发生日期、公告日期和媒体发布日期。
- 默认以首次公开发布的日期判断是否符合时间窗。
- 时间窗外的旧事件，只有在窗口内发生实质性新进展时才能作为新新闻。
- 无法确认日期的项目进入 Pending Review，不得自动纳入。

## 3. Research Coverage

搜索采用主题优先级与地理覆盖相结合的方式，不能只使用少量固定关键词。

### Tier P0 — Core Business

重点研究直接影响 XSTAR 业务及汽车金融市场的事件。

**Automotive Finance**
- Hire Purchase / Auto Loan
- Dealer Financing / Floor Stock Financing
- Loan Origination / Approval / Take-up
- Consumer Credit / Credit Risk
- Financing Rates / Funding Costs
- Delinquency / NPL / Default
- Leasing / Used-car Financing

**Banking & Regulation**
- Central Bank Policy
- Interest Rates / Monetary Policy
- Banking Liquidity / Lending
- Credit Regulation
- Digital Banking / Fintech
- Financial Institution Licensing

**Thailand & Southeast Asia**
- 泰国汽车销量、生产、出口
- 泰国银行及非银金融机构
- 家庭债务、消费信贷及汽车贷款
- 产业投资、外资政策及税收优惠
- 东南亚汽车制造与金融市场竞争

### Tier P1 — Strategic Industry

- 全球主要汽车制造商
- EV、HEV、PHEV、电池及充电基础设施
- 汽车工厂、产能、供应链及出口
- 重大召回、安全及监管事件
- 关税、贸易政策及国际产业竞争
- 重大投资、并购、IPO 和财报

### Tier P2 — Emerging Technology & Macro

- AI、机器人、自动驾驶及 Physical AI
- 半导体、算力及工业自动化
- 全球宏观经济与金融市场
- 重大地缘政治及能源政策
- 对汽车、金融或产业投资具有重大影响的技术突破

P2 新闻不因缺乏直接汽车金融关联而自动排除，但必须具有足够的战略重要性。

## 4. Geographic & Multilingual Search

默认覆盖六大地区：

1. North America — NA
2. Asia Pacific — APAC
3. Middle East — ME
4. Europe — EU
5. Latin America — LATAM
6. Africa — AFR

**泰国和东南亚具有更高搜索深度，但不意味着其他地区的重大事件可以被忽略。**

| 市场 | 必须尝试的语言 |
|---|---|
| 泰国 | 泰文、英文 |
| 中国 | 简体中文、英文 |
| 日本 | 日文、英文 |
| 韩国 | 韩文、英文 |
| 越南 | 越南文、英文 |
| 印尼 | 印尼文、英文 |
| 德国 | 德文、英文 |
| 法国 | 法文、英文 |
| 西班牙及拉美 | 西文、英文 |
| 巴西 | 葡文、英文 |
| 中东 | 阿文、英文 |

### Search Query Construction

每个搜索主题至少考虑四种查询方向：

**A. Event Discovery**

寻找日期区间内发生的重大事件。

**B. Primary Source Discovery**

针对监管机构、央行、车企、上市公司及行业协会的官方网站搜索。

**C. Local Language Discovery**

使用目标国家的本地语言搜索，而不是仅将英文关键词翻译一次。

**D. Follow-up Verification**

针对已发现事件搜索原始公告、独立报道和后续更新。

示例：

- `site:bot.or.th สินเชื่อรถยนต์ หนี้ครัวเรือน`
- `site:boi.go.th ยานยนต์ไฟฟ้า การลงทุน`
- `site:boj.or.th อุตสาหกรรมยานยนต์`
- `自動車 ローン 金利 政策`
- `자동차 금융 대출 금리`
- `crédito automotivo financiamento veículos Brasil`

上述示例是查询模式，不代表所列域名均已验证适用于相应主题。

**禁止：** 只搜索 `automotive news 2026`、`EV news` 等宽泛英文词，就认为已经完成全球研究。

## 5. Multi-pass Research Workflow

Agent 必须采用多轮研究，而不是一次搜索后立即总结。

### Pass 1 — Broad Discovery

按主题、地区及本地语言建立候选新闻池。

记录：

- 搜索词
- 搜索语言
- 搜索地区
- 搜索时间
- 搜索结果数量
- 发现的新闻 URL

### Pass 2 — Targeted Research

针对用户输入的线索及高价值候选新闻继续搜索：

- 原始公告
- 事件主体
- 具体金额和数字
- 事件发生及发布日期
- 相关政策或市场背景

### Pass 3 — Gap Analysis

检查是否存在明显覆盖缺口：

- 是否搜索了泰国央行、金融监管及汽车行业？
- 是否覆盖主要汽车制造商？
- 是否遗漏重要央行决议？
- 是否遗漏重大产业投资、关税或政策变化？
- 是否只有英文来源？
- 是否某个地区完全没有执行搜索？

没有相关新闻不等于搜索失败，但必须能区分 **已搜索且无合格结果** 与 **尚未搜索**。

### Pass 4 — Supplementary Search

对搜索不足的主题或地区执行补充搜索。

当搜索额度、API 限制或网页访问失败导致覆盖不足时，必须显示 Coverage Warning，不得声称研究完整。

## 6. Source Hierarchy

### Tier 1 — Primary Sources

优先使用：

- 政府及监管机构公告
- 中央银行
- 上市公司及企业官方新闻稿
- 证券交易所及正式申报文件
- 行业协会及官方统计
- 国际金融机构及政府统计机构

### Tier 2 — Established News Media

包括 Reuters、AP、CNA、Nikkei、Bloomberg、Financial Times 及目标市场的可信主流财经媒体。

这些媒体的权威性不意味着其每篇文章都免费可访问。

### Tier 3 — Specialist Media

汽车、EV、电池、金融科技及工业技术专业媒体。

可以用于发现事件，但涉及重大金额、监管决定或交易条款时，应尽量回溯原始资料。

### Source Selection Rules

- 同一事件优先官方原始来源。
- 官方来源内容不足时，可以用主流媒体补充。
- 转载媒体不视为独立证据。
- 付费或登录页面不能假装已读取完整正文。
- 不得把搜索结果摘要当作已核验原文。
- 不得因为媒体知名度高就跳过事实检查。

## 7. Evidence Verification

每条候选新闻必须记录：

| 字段 | 要求 |
|---|---|
| Original URL | 可追溯的真实链接 |
| Source Name | 实际来源名称 |
| Publication Date | 已确认的发布日期 |
| Original Title | 原文标题 |
| Evidence Excerpt | 可在正文定位的原文证据 |
| Key Facts | 主体、动作、数字及时间 |
| Access Status | Free / Paywall / Login / Failed |
| Verification Status | Verified / Partial / Pending / Rejected |

**Verified 必须满足：**

1. 能访问原始正文。
2. 能确认发布日期在目标时间范围内。
3. 核心事件得到正文支持。
4. 关键主体、动作及重要数字有对应证据。
5. 摘要不存在原文不支持的推断性陈述。

涉及重大金融数字时，必须检查：

- 币种与金额单位
- 百分比与百分点
- 同比、环比或累计口径
- 已完成、计划中或仍待批准
- 财年、季度及统计期间
- 交易估值与实际融资额的区别

**如果数字未核实，不能通过 AI 自信程度代替证据。**

## 8. Free-access Source Resolution

每条入选新闻应尽可能提供无需付费、无需登录、可以直接阅读的权威链接。

处理顺序：

1. 原始官方公告。
2. 官方统计或监管文件。
3. 免费可访问的权威媒体报道。
4. 其他可信专业媒体。

如果最初发现的是付费报道，执行标题、主体、关键数字及事件日期的替代来源搜索。

替代来源必须确实支持新闻内容，不能只因为标题相似就替换。

找不到可验证的免费链接时，标记为 Pending，不得伪造来源。

## 9. News Scoring

评分采用固定的 100 分制：

| 维度 | 满分 |
|---|---:|
| XSTAR Business Relevance | 30 |
| Industry / Market Impact | 25 |
| Source Credibility | 20 |
| Timeliness | 15 |
| Actionability | 10 |
| **Total** | **100** |

### Selection Rules

- **85–100：** High Priority
- **75–84：** Recommended
- **60–74：** Optional / Manual Review
- **0–59：** Excluded

默认自动入选条件：

`Score >= 75 AND Verification Status = Verified`

但高分不能绕过核验要求。

重要性排序必须考虑事件实质影响，不能仅按照国家或关键词出现频率排序。

## 10. Event Deduplication

去重分为三层：

**Level 1 — URL Deduplication**

标准化 URL，去除常见跟踪参数。

**Level 2 — Title Deduplication**

识别标题高度相似的报道。

**Level 3 — Event-level Deduplication**

根据事件主体、动作、发生日期、关键金额及地点判断是否为同一事件。

例如，同一车企宣布一座工厂投资，Reuters、当地媒体和公司官网分别报道，原则上应合并为一条新闻，并保留最可靠来源。

如果同一项目后来正式获批、追加投资或投产，则可能属于新的实质性进展。

事件级去重应保存判断依据；仅用标题相似度不能视为完整实现。

## 11. Editorial Standards

最终新闻必须使用专业、清晰、自然的中文。

### Headline

- 简洁、信息密度高。
- 尽量包含事件主体及核心变化。
- 不使用夸张标题。
- 不将计划写成已经完成。
- 不添加来源中不存在的金额或数字。

### Summary

建议包含：

1. 发生了什么。
2. 关键事实、数字或政策内容。
3. 对市场、行业或 XSTAR 业务的潜在影响。

业务影响应与事实陈述区分；不能把分析推断写成官方结论。

### Tags

根据内容选择准确的主题标签，例如：

汽车金融、央行、利率、EV、电池、销量、融资、IPO、并购、AI、机器人、政策、供应链。

不得为了增加标签数量而添加不相关主题。

## 12. Geographic Classification

Excel 使用固定地区代码：

| region_code | region_name_zh |
|---|---|
| NA | 北美地区 |
| APAC | 亚太地区 |
| ME | 中东地区 |
| EU | 欧洲地区 |
| LATAM | 拉美地区 |
| AFR | 非洲地区 |

地区按主要事件发生地或主要受影响市场确定，不按媒体所在地确定。

跨地区事件允许编辑选择主要地区。

默认展示顺序：

北美 → 亚太 → 中东 → 欧洲 → 拉美 → 非洲。

## 13. Excel Preservation

用户上传的 Excel 是原始数据资产，不能作为临时数据重新生成。

**无修改模式：**

直接返回原始文件字节。

**编辑模式：**

- 保留原 Sheet。
- 保留原始文字。
- 保留字段顺序。
- 保留单元格样式。
- 保留日期格式。
- 保留行高、列宽、合并单元格及元数据。
- 仅更新用户明确修改的单元格。

**新增研究模式：**

使用 `XSTAR_Excel_Master.xlsx` 作为母版，将新新闻写入对应字段，不得自行发明新列或改变原始格式。

研究评分、核验状态和审计信息可以保存在独立内部数据结构中，不能未经授权改变正式 Excel 的列布局。

## 14. Outlook HTML Preservation

HTML 输出必须以用户提供的成品及 Outlook Generator 为标准。

必须保留：

- 邮件整体宽度及表格布局
- 报告标题、日期和期数
- 六大地区标题
- 新闻卡片结构
- 标题、地点、日期和标签
- 摘要段落
- 来源按钮及链接
- Outlook 兼容性结构

用户在编辑器修改新闻后，HTML 预览和下载内容必须同步更新。

不能使用一套独立的简化 HTML 替代原有模板。

## 15. Review & Publication Workflow

研究结果分为：

- **Selected：** 已核验且符合评分门槛。
- **Pending：** 日期、正文、数字或来源仍需核实。
- **Excluded：** 不符合研究要求。
- **Manually Included：** 用户明确选择加入，但必须保留其核验状态。

用户可以编辑标题、摘要、地区、标签、日期、URL、排序及纳入状态。

系统不得在用户修改后自动覆盖其编辑内容。

正式发布前应提供：

- 新闻总数
- 自动选入数量
- 待核验数量
- 排除数量
- 研究覆盖情况
- 未解决的来源或数字风险

## 16. Research Audit & Failure Handling

每次研究应记录：

- 搜索主题及语言
- 查询数量
- 搜索 API 使用量
- AI Token 与费用信息（如果服务返回）
- 原文访问结果
- 来源核验状态
- 评分依据
- 去重原因
- 未完成任务

当 API 超时、额度不足、搜索失败或网页被阻止时：

- 不得生成虚假的新闻填补数量。
- 不得将未访问正文的新闻标为 Verified。
- 不得将未完成的搜索显示为成功。
- 已上传的 Excel 编辑和 HTML 生成功能必须继续可用。

## 17. Acceptance Criteria

Agent 只有满足以下条件，才可以声称该次研究流程完成：

1. 所有用户提供的线索均已处理或明确标记未完成。
2. 必要的主题、地区和本地语言搜索均已执行或明确记录失败。
3. 自动入选新闻满足评分与核验条件。
4. 每条新闻有可追溯的来源和关键事实证据。
5. 不存在已知的重大重复事件。
6. Excel 输出符合原始母版结构。
7. HTML 输出符合原始 Outlook 模板。
8. 预览与下载内容一致。
9. 未完成事项及风险清楚显示。

**不得以“生成了 Excel 和 HTML”作为 Research 成功的唯一标准。**

---

### Implementation Boundary

以上是目标研究规范，并不表示当前 Research V2 已全部实现。

其中事件级语义去重、逐事实数字核验、免费替代来源自动查找、跨期历史存储及真实 API 端到端测试，必须经过实际代码实现和验证后才能标记为完成。

禁止宣传未经测试的研究引擎已经达到 10/10。
