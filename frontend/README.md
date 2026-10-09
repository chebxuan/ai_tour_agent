# 行旅前端

Next.js App Router + JavaScript/JSX + 普通 CSS。对客页面已统一为英文。预览通过服务端适配层调用 FastAPI，按实际产品天数展示英文 Menu 故事、景点亮点和已选体验；已接入销售估算，AI 解析尚未接入。

从仓库根目录启动：

```bash
cd frontend
npm run dev
```

首次拉取代码后先运行 `npm ci`。开发服务器中修改组件会热更新。

- `/`：首页、文化主题筛选、每个目的地一张叙事卡片。
- `/plan`：需求表单与逐日预览。
- `/plan?destination=beijing`：只预填北京，日期与天数由用户选择。
- `/plan?journey=BJ-P-02`：内部产品预选入口，使用真实产品编号；旧 `demo-*` 演示编号已移除。

## 修改位置

| 位置 | 用途 |
|---|---|
| `app/layout.js` | 共享导航、页脚与页面元信息 |
| `app/globals.css` | 颜色、字体、间距与共享按钮样式 |
| `components/HomePage.jsx` | 首页首屏与区块组织 |
| `components/DestinationCatalog.jsx` | 首页文化主题筛选与目的地列表 |
| `components/DestinationCard.jsx` | 目的地叙事卡片，不显示编号/天数 |
| `components/TripForm.jsx` | 需求表单 |
| `components/ItineraryPreview.jsx` | 方案状态与每日时间线 |
| `components/TravelPlanner.jsx` | 查询参数、表单状态与结果快照 |
| `components/ScenicArt.jsx` | 原创占位插画，并非目的地实景 |
| `data/destinations.js` | 基于已审阅资料整理的目的地叙事与文化标签 |
| `data/products.json`、`data/products.js` | 21 个真实产品的公开内容与目的地天数范围 |
| `lib/productPreview.js` | 请求 Next.js 服务端预览接口，保存表单快照 |

真实路线与可选体验已接入，实景照片和更详细的景点介绍另行准备，不将原始私人文档复制到 public。不显示成本作为销售报价，真实密钥只留在服务端。

验证：

```bash
npm run lint
npm run build
```

仓库路径包含冒号；npm 脚本直接通过 Node 调用本地 CLI，避免 PATH 拆分导致找不到命令。

当前阶段与下一步统一记录在 [`../docs/roadmap.md`](../docs/roadmap.md)。

## 真实产品内容

在仓库根目录执行 `python3 scripts/export_frontend_products.py` 可从现有产品库重新导出公开内容。导出会核对规范化数据与 CSV 的城市、天数和原始日程；仅保留产品名称、编号、目的地、每日路线、分支与可选项目，不包含成本、供应商或付款资料。

20 个产品展示逐日路线；重庆 5 日产品因原始日程粒度不完整，只展示概览与待确认说明。图片仍为示意插画，已勾选的体验、人数、明确选择的导游/车辆和分支参与销售估算；最终预订仍需确认。

旅行天数只显示所选城市已有产品的天数；Optional choice 按当前产品显示可选体验与餐饮勾选框。切换城市或天数后清空旧选择，预览保留选择快照。2026-10-09 用户授权按天重做英文 Menu 并开始预览联调：按钮请求 `/api/trips/preview`，由服务端调用 FastAPI 的 `/api/v3/trips/preview`，不调用内部成本接口。

## 服务端预览配置

在 `frontend/.env.local` 配置 `BACKEND_BASE_URL` 和 `BACKEND_API_KEY`，模板见 `.env.example`。密钥必须与后端服务端配置一致，不使用 `NEXT_PUBLIC_*`。已有配置不要覆盖。后端不可用时显示英文错误并保留表单，不悄悄回退到本地数据。

当前本地联调用后端在 `127.0.0.1:8001`，前端仍为 `localhost:3000`；8000 上的旧验证进程未被覆盖。正式运行可按实际配置调整后端地址。

02 按 Day 排列 Menu 标题、完整 Route 介绍与景点描述。仅展示当前产品适用内容；客人选中的体验显示英文描述，原 PDF 价格不作为销售价。重庆 5 日仍以章节概览展示，逐日游轮安排待确认。


## 分支与报价

服务与分支选项通过 `/api/products?city=…` 读取后端公开目录。01 选择具体分支、导游和 Pricing Season；不确定季节或服务时可保留待确认并查看行程。预览随后请求 `/api/trips/quote`，服务端调用 FastAPI `/api/v3/trips/quote`，只转发旅客报价，不请求运营成本接口。

02 显示所选路线、人民币团体估算价及包含/排除范围。修改表单后隐藏旧金额，点击预览重新计算；报价失败仍保留 Menu。浏览器不计算 1.3 倍率，不持有服务端密钥。

2026-10-09 用户端简化：移除 Pricing Season、Guide Service 和导游开关，固定标准英文导游与淡季估算；导游编号读取后端当前目录，缺少标准项则待确认。包车、分支与可选体验保留。02 联系入口及咨询提交随后已实现，具体交付见末尾和路线图最新阶段。

2026-10-09：02 联系入口已实现，点击 Talk to a Travel Expert 展开 Name/Email/Message 表单，自动携带预览与估算。`/api/trips/enquiries` 同源转发后端，保存成功后显示咨询编号；需求变更需更新预览，失败保留输入，同一提交重试去重。咨询待确认也能保存。当前不发送邮件、不提供运营网页登录，运营先用数据库维护命令查看。
