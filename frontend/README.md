# 行旅前端

Next.js App Router + JavaScript/JSX + 普通 CSS。对客页面已统一为英文。预览通过服务端适配层调用 FastAPI，按实际产品天数展示英文 Menu 故事、景点亮点和已选体验；已接入销售估算，AI 解析尚未接入。

从仓库根目录启动：

```bash
cd frontend
npm run dev
```

首次拉取代码后先运行 `npm ci`。开发服务器中修改组件会热更新。

- `/`：首页、文化主题筛选、每个目的地一张叙事卡片。
- `/plan`：独立联系与旅行偏好表单，可不选定产品直接咨询。
- `/plan?destination=beijing`：预填北京，显示 01 选择与 02 英文行程预览。
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
| `components/DestinationPhoto.jsx` | 开放授权实景摄影、响应式图片和署名 |
| `components/ContactPage.jsx` | 独立联系页与偏好提交 |
| `data/photography.json` | 图片来源、摄影师与授权信息 |
| `data/destinations.js` | 基于已审阅资料整理的目的地叙事与文化标签 |
| `data/products.json`、`data/products.js` | 21 个真实产品的公开内容与目的地天数范围 |
| `lib/productPreview.js` | 请求 Next.js 服务端预览接口，保存表单快照 |

真实路线、可选体验与开放授权实景照片已接入，不将原始私人文档复制到 public。不显示成本作为销售报价，真实密钥只留在服务端。

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

服务与分支选项通过 `/api/products?city=…` 读取后端公开目录。01 选择具体分支、包车与住宿偏好；淡季与标准英文导游默认使用，不向旅客提供切换控件。预览随后请求 `/api/trips/quote`，服务端调用 FastAPI `/api/v3/trips/quote`，只转发旅客报价，不请求运营成本接口。

02 显示所选路线、人民币团体估算价及包含/排除范围。修改表单后隐藏旧金额，点击预览重新计算；报价失败仍保留 Menu。浏览器不计算 1.3 倍率，不持有服务端密钥。

2026-10-09 用户端简化：移除 Pricing Season、Guide Service 和导游开关，固定标准英文导游与淡季估算；导游编号读取后端当前目录，缺少标准项则待确认。包车、分支与可选体验保留。02 联系入口及咨询提交随后已实现，具体交付见末尾和路线图最新阶段。

2026-10-09：02 联系入口已实现，点击 Talk to a Travel Expert 展开 Name/Email/Message 表单，自动携带预览与估算。`/api/trips/enquiries` 同源转发后端，保存成功后显示咨询编号；需求变更需更新预览，失败保留输入，同一提交重试去重。咨询待确认也能保存。当前不发送邮件、不提供运营网页登录，运营先用数据库维护命令查看。


## 联系页与住宿偏好（2026-10-09）

- 直接打开 `/plan` 是独立联系页：姓名、邮箱、目的地意向、日期、停留时间、人数、住宿需求、兴趣与留言。旅行偏好可暂不确定，默认 2 人。
- 从目的地卡片进入 `/plan?destination=shanghai` 等链接，仍显示 01 选择 / 02 英文 Menu 预览；`?journey=SH-P-02` 等已有产品链接也保留。
- 01 的 Accommodation 收集安排酒店／自行预订／希望获得建议。02 和提交询单包含相同选择，现有估算继续明确排除酒店，住宿由运营另外报价。
- 联系页经 `/api/trips/custom-enquiries` → FastAPI `/api/v3/trips/custom-enquiries` 保存到 PostgreSQL，同样返回 TC 编号；无产品时不会生成费用快照或假价格。受限写入、重试去重、同源检查与输入大小限制继续生效。
- 实景图片在 `public/images/destinations/`，来源、作者、授权、展示裁切说明在 `data/photography.json` 及网站页脚。使用 Wikimedia 开放授权照片，未复制 WildChina 图片、商标、文案或资质。
- animejs 用于滚动进入时的文字与卡片动画，照片有轻微悬停缩放；系统开启减少动态效果时停用动画。

## 在桌面查看手机页面

Mac Chrome 打开 `http://localhost:3000`，按 **⌘⌥I** 打开开发者工具，再按 **⌘⇧M** 切换设备模式。在顶部设备菜单选择 iPhone 或 Responsive，使用 390 / 360px 宽度；可以切换横竖屏。它模拟屏幕与触摸行为，发布前仍需在真实手机检查。

官方说明：https://developer.chrome.com/docs/devtools/device-mode/


## 用户自选照片与全屏首图

当前照片入口为 `data/sitePhotography.js`：`destinationPhotos` 对应城市图片，`heroPhoto` 固定使用首页石桥图 `ABUIABACGAAgyZbglQYorqaD2gIwkxY4ngk(1).jpg`。北京改用 `主要景点-故宫-11.jpg`。原始图片不被修改，`position` 控制裁切位置；旧 Wikimedia 记录仅保留备查。

首页首屏高度覆盖完整视口，透明导航叠在照片上。`HeroScene` 使用持续慢速缩放和平移，每段 32 秒、往返循环，不因悬停／聚焦而停止；提供 Pause motion / Resume motion 按钮，系统减少动态效果模式下自动停用动画。取消多图轮播及切换控件。桌面最大内容宽度 1440px 和三列目的地卡片保留。

## Docker 部署

生产镜像使用 Next.js standalone，配置和命令见 [全站部署说明](../docs/deployment-guide.md)。Compose 注入服务端后端密钥和网站可信来源（SITE_ORIGIN）；域名切换要同步更新网站来源并重建运行容器。`npm run test:origin` 验证联系表单同源限制。
