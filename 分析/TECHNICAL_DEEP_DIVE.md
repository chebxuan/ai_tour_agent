# Hexa Blueprint 技术深度分析

> 用途：帮你理解这个项目背后的技术原理，借项目学技术

---

## 一、技术栈全景

```
┌─────────────────────────────────────────────────────────┐
│                    Streamlit Frontend                     │
│          (streamlit_app.py — Python Web UI)               │
└──────────────────────┬──────────────────────────────────┘
                       │ HTTP (requests)
                       ▼
┌─────────────────────────────────────────────────────────┐
│                    FastAPI Backend                        │
│                  (api_main.py - 1366 lines)               │
│                                                          │
│  ┌──────────┐ ┌──────────┐ ┌──────────┐ ┌──────────┐   │
│  │ Product  │ │ Pricing  │ │   Plan   │ │ Delivery │   │
│  │ Engine   │ │  Engine  │ │  Engine  │ │  Engine  │   │
│  └──────────┘ └──────────┘ └──────────┘ └──────────┘   │
│   engines/     engines/     engines/     engines/        │
│   product_     cost_       plan_       delivery_         │
│   engine.py    engine.py   engine.py   engine.py         │
└──────────────────────┬──────────────────────────────────┘
                       │ Reads
                       ▼
┌─────────────────────────────────────────────────────────┐
│                 Data Layer (CSV + JSON)                   │
│  product_library.csv  →  products.normalized.json        │
│  mashes/10cities.csv  →  per-city pricing data           │
│  attraction_highlights.json → scenic descriptions        │
└─────────────────────────────────────────────────────────┘
```

### 技术栈拆解

| 层次 | 技术 | 版本 | 做什么 | 学习价值 |
|------|------|------|--------|---------|
| Web 框架 | FastAPI | ≥0.104 | API 服务，路由、认证、文档 | ⭐⭐⭐⭐⭐ |
| 数据验证 | Pydantic v2 | ≥2.5 | 用 Python 类型注解定义数据结构 | ⭐⭐⭐⭐⭐ |
| 前端 | Streamlit | ≥1.28 | Python 写的 Web UI，无需 HTML/JS | ⭐⭐⭐⭐ |
| HTTP 请求 | requests | ≥2.31 | 前端调后端 API | ⭐⭐⭐ |
| 容器化 | Docker | — | 打包部署 | ⭐⭐⭐⭐ |
| 运行环境 | Python 3.11+ | — | 全项目语言 | — |

### 这个项目没用的东西（🤷）

很多 AI 项目会用的东西，这里**完全没用**：
- ❌ 没有数据库（SQLite/PostgreSQL/Redis）
- ❌ 没有 ORM（SQLAlchemy）
- ❌ 没有 AI/LLM API（OpenAI/Anthropic）
- ❌ 没有前端框架（React/Vue）
- ❌ 没有消息队列（Celery/RabbitMQ）
- ❌ 没有异步任务

> 这正是学习的好起点——**从最简架构开始理解，再逐步加复杂度**

---

## 二、核心架构模式

### 2.1 Pipeline 模式（管线/管道）

这是整个项目最重要的架构模式。数据像流水线一样，一站一站往前走：

```
LeadJSON → CandidateProductsJSON → PricingResultJSON → PlanObject → DeliveryDraftObject
  输入         匹配产品           计算价格          编排行程      生成交付文档
```

**代码里怎么体现的：**

[api_main.py:1156](api_main.py#L1156) `full_chain_v2()` 函数：

```python
# 1. 构建 Lead
lead = build_lead_from_full_chain_request(request)

# 2. 产品匹配
product_match = build_candidates_from_lead(lead)

# 3. 报价
pricing = 调 pricing 接口

# 4. 行程编排
plan = 调 plan 接口

# 5. 交付文档
delivery = 调 delivery 接口

# 6. 格式化成 Markdown
markdown = format_itinerary_markdown(lead, product_match, pricing, plan, delivery)
```

**学习要点：**
- 每个阶段输入是前一个阶段的输出
- 每个阶段可以独立修改、测试、替换
- 这是软件工程中最常用的模式之一

### 2.2 分层架构

```
api_main.py ──── 接口层（路由 + 认证 + 请求/响应）
     │
     ▼
engines/ ─────── 业务逻辑层（匹配/报价/行程/交付）
     │
     ▼
data/ ────────── 数据层（CSV/JSON 文件）
```

**学习要点：**
- 层与层之间通过函数调用通信，不直接依赖内部实现
- 替换数据层（CSV→数据库）不影响业务逻辑层
- 这是后端开发的标准分层

### 2.3 Schema-Driven 开发（Schema-Driven Development）

先定义数据结构，再写业务逻辑。项目有 **30+ Pydantic 模型**。

[schemas.py](schemas.py) 里的每个模型就是一个"数据合约"：

```python
class LeadJSON(BaseModel):
    lead_id: str
    contact: ContactInfo
    passenger_mix: PassengerMix
    intent: LeadIntent
    # 自动验证：类型不对 → 报错
    # 自动文档：OpenAPI 自动生成
    # 自动序列化：JSON 互转
```

**学习要点：**
- 先定义数据结构，再写逻辑——这是生产级开发的常规做法
- Pydantic 帮你免费拿到：类型检查、JSON 序列化、文档生成
- 对比"不用 Schema"的方式，你就知道为什么这能省大量调试时间

---

## 三、关键函数拆解（值得你仔细读的）

### 3.1 产品评分函数—最核心的算法逻辑

[api_main.py:356](api_main.py#L356) `score_product_for_lead()`

```python
def score_product_for_lead(product, lead) -> ProductCandidate:
```

这个函数把一个产品和一个客户需求做匹配，返回匹配分数（0-1）。

**学到的概念：**
- **评分算法**：按城市匹配、天数匹配、兴趣标签匹配、人数约束逐项打分
- **归一化**：多个维度的分数如何合并成一个 0-1 的分数
- **候选排序**：对所有产品打分后取最高分

**这就是一个简化版的推荐系统**——没有用 ML，但逻辑是一样的。

---

### 3.2 报价计算函数—最复杂的业务逻辑

[cost_engine.py:513](cost_engine.py#L513) `calculate_total_cost()`

```python
def calculate_total_cost(product, user_intent):
    # 1. 读成本库 CSV
    # 2. 查门票价格 → 成人价/儿童价/老人价（折扣）
    # 3. 查车辆价格 → 包车费/接送机费
    # 4. 查导游价格 → 日薪 × 天数
    # 5. 查酒店价格 → 房费 × 房间数 × 晚数
    # 6. 汇总 → 总价 + 人均价 + 分类小计
    # 7. 返回 PricingResultJSON
```

**学到的概念：**
- **面向对象 vs 面向过程**：这里用了大量小函数组合（calc_ticket / calc_hotel / calc_transport / calc_guide）
- **防御性编程**：`safe_float()`、`parse_int()` 处理 CSV 脏数据
- **缺失处理**：`missing_codes` 收集找不到价格的项，不直接崩
- **价格逻辑**：淡旺季不同价、儿童半价、老人折扣

---

### 3.3 行程编排函数—数据转换的典型例子

[plan_engine.py:125](plan_engine.py#L125) `build_plan_object()`

```python
def build_plan_object(lead, selected_products) -> PlanObject:
```

**学到了什么：**
- **扁平数据 → 结构化数据**：把 CSV 里扁平的 activity_names 列表，转成带 time_slot、activity_type、included 标记的结构化 PlanDay
- **时间槽推理**：`infer_time_slot()` 根据活动在一天中的位置，自动分配 morning/afternoon/evening
- **活动分类**：`infer_activity_type()` 根据标题关键词判断是 hotel/transport/meal/sightseeing

---

### 3.4 Markdown 生成—AI 最擅长但你自己写也行的

[api_main.py:559](api_main.py#L559) `format_itinerary_markdown()`

**学到的概念：**
- **模板模式**：用字符串数组拼接 Markdown，一行一行构造
- **条件渲染**：不同数据状态（有/无行程、有/无报价）显示不同内容
- **双语实现**：字段名同时输出中文和英文

### 3.5 一键全链路—API 组合模式

[api_main.py:1156](api_main.py#L1156) `full_chain_v2()`

这是最值得学习的"工程模式"——**把多个独立接口组合成一个高价值接口**。

```python
async def full_chain_v2(request: FullChainRequest):
    # 1. 转请求格式
    lead = build_lead_from_full_chain_request(request)
    
    # 2. 产品匹配
    candidates = build_candidates_from_lead(lead)
    top = candidates.candidates[0] if candidates.candidates else None
    
    # 3. 自动算参数（人数、车辆、导游）
    # ...
    
    # 4. 调报价
    pricing = calculate_pricing_v2(...)
    
    # 5. 调行程编排
    plan = build_plan_v2(...)
    
    # 6. 调交付生成
    delivery = build_delivery_v2(...)
    
    # 7. 格式化成可读文本
    md = format_itinerary_markdown(lead, candidates, pricing, plan, delivery)
    
    # 8. 返回
    return {"success": True, "itinerary_markdown": md, ...}
```

---

## 四、值得学习的 Python 技术点

### 4.1 类型注解（Type Hints）

全项目都用了 Python 类型注解，这是现代 Python 开发的标准：

```python
def build_plan_object(
    lead: Any,
    selected_products: List[SelectedProduct],
    normalized_products: Optional[List[Dict[str, Any]]] = None,
) -> PlanObject:
```

好处：
- IDE 自动补全
- 提前发现类型错误
- 自文档化（不用看实现就知道输入输出）

### 4.2 FastAPI 依赖注入

```python
async def get_cities(api_key: str = Depends(verify_api_key)):
```

FastAPI 自动调用 `verify_api_key()`，把返回值注入到 `api_key` 参数。这是**依赖注入模式**的入门级实现。

### 4.3 Pydantic 模型嵌套

```python
class LeadJSON(BaseModel):
    contact: ContactInfo       # 另一个模型
    passenger_mix: PassengerMix  # 另一个模型
    intent: LeadIntent           # 另一个模型
```

模型嵌套模型，JSON 转 Python 对象自动完成。

### 4.4 Pathlib 文件操作

```python
ROOT = Path(__file__).resolve().parent
NORMALIZED_PRODUCTS_JSON = ROOT / "data" / "products" / "products.normalized.json"
```

用 `/` 拼接路径（跨平台），比 `os.path.join()` 优雅得多。

### 4.5 CSV 读取与脏数据处理

```python
def safe_float(value, default=0.0):
    try:
        return float(value)
    except (ValueError, TypeError):
        return default
```

CSV 数据经常有空值、格式错误，防御性函数保证不崩。

---

## 五、可以怎么通过这个项目学技术

### 方式一：读代码，逐行理解

最佳阅读顺序：

```
1. schemas.py（先理解所有数据结构）
2. api_main.py:559 format_itinerary_markdown（看输出长什么样）
3. api_main.py:1156 full_chain_v2（看怎么串联）
4. engines/product_engine.py（看匹配逻辑）
5. engines/cost_engine.py（看价格计算）
6. engines/plan_engine.py（看行程编排）
7. engines/delivery_engine.py（看交付生成）
```

### 方式二：改代码，动手实验

| 实验 | 难度 | 学什么 |
|------|------|--------|
| 加一个新的可选项目到产品库 | ⭐ | CSV 数据格式、normalize 流程 |
| 改一下行程 Markdown 的格式 | ⭐⭐ | 模板渲染流程 |
| 加一个新的城市 | ⭐⭐ | 完整的数据配置流程 |
| 把 CSV 存储换成 SQLite | ⭐⭐⭐⭐ | 数据库基本操作、数据迁移 |
| 加一个新的 API 接口 | ⭐⭐⭐ | FastAPI 路由、Pydantic 响应模型 |
| 把报价解释（QuoteExplanation）补上 | ⭐⭐⭐ | 理解完整的数据流 |

### 方式三：从零复刻

挑一个更简单的业务场景（比如「餐厅推荐系统」或「学习笔记管理」），用同样的架构自己搭一遍。

---

## 六、这个项目技术上的局限

诚实地说，这个项目在生产级标准上还有这些差距：

| 局限 | 为什么 | 生产级怎么做 |
|------|--------|------------|
| 无数据库 | CSV 不适合并发读写 | PostgreSQL / MySQL |
| 无单元测试 | 没法自动验证修改后是否崩 | pytest + 测试覆盖率 |
| 无日志系统 | 出问题很难排查 | loguru / structlog |
| 无错误监控 | 不知道用户遇到了什么错 | Sentry |
| 无缓存 | 每次请求都读 CSV/JSON | Redis / 内存缓存 |
| 无异步处理 | CSV 读取是同步的，阻塞线程 | asyncio / 异步 DB 驱动 |
| 无 CI/CD | 只能手动部署 | GitHub Actions |

这些不是缺点——对于项目阶段来说完全合理。只是要知道"如果这是生产系统，还需要什么"。

---

## 七、关于下一个项目的建议

### 鸿蒙开发 vs GitHub 借鉴

**鸿蒙开发（ArkTS + DevEco Studio）：**

| 维度 | 评价 |
|------|------|
| 学习曲线 | ⚠️ 陡峭——ArkTS 是 TypeScript 变体，DevEco 工具链还不够成熟 |
| Vibe Coding 可行性 | ⚠️ 低——AI 对 ArkTS 和鸿蒙 API 的训练数据极少 |
| 求职价值 | 🤷 看方向——如果想去鸿蒙生态的公司（某为系）有价值 |
| 时间成本 | ⚠️ 高——学工具链、学语言、学生态都要时间 |

**GitHub 上 fork/借鉴项目：**

| 维度 | 评价 |
|------|------|
| 学习曲线 | ✅ 可控——选 Python/JS 你熟悉的栈 |
| Vibe Coding 可行性 | ✅ 高——主流语言 AI 训练充分 |
| 求职价值 | ✅ 高——可以选和 AI + 出海方向一致的项目 |
| 时间成本 | ✅ 低——直接上手改 |

### 我的建议

**不要做鸿蒙开发**，除非你已经想好要去鸿蒙生态的公司。原因：

1. **AI 帮不了你** — Vibe Coding 的核心理念是"AI 替你写大部分代码"，但主流 AI 模型对 ArkTS / 鸿蒙 API 的训练数据极少，遇到报错 AI 也无法准确修复。你会从"指挥 AI 干活"退回"自己查文档、自己调试"。
2. **和你的方向不一致** — 你想走的是 AI + 出海，鸿蒙是一个纯国内生态，两者没有交集。
3. **学习成本太高** — 你得学：ArkTS 语言、DevEco Studio IDE、鸿蒙 API、新的 UI 框架。这些学完如果不去鸿蒙公司，几乎没有迁移价值。

**更好的选择：**

**方案 A：深挖当前项目（推荐）**

这个项目已经跑通了，你在这个阶段最应该做的是：
- 加单元测试（学 pytest）
- 加 SQLite 存储（学数据库）
- 加 CI/CD（学 GitHub Actions）
- 加日志（学 loguru）

每一次"加"都是实际可用的技能提升，而且 AI 能全程帮你。

**方案 B：做一个新项目，但选 AI 熟悉的栈**

如果你想换场景但保留技术栈：
- Python + FastAPI + 某个前端（Streamlit / Gradio / 简单 React）
- 可以是任何工具型产品：笔记工具、书签管理器、个人记账
- AI 能帮你写 80% 的代码

**方案 C：GitHub 上找一个开源项目做贡献**

- 找 Python 相关的、活跃的、有 good first issue 的项目
- 先读文档和代码，修一个小 bug，提交 PR
- 这是最接近"真实工作"的体验

核心逻辑只有一个：**选择 AI 能帮你加速的方向，不要选择 AI 帮不了你的方向。**
