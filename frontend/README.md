# 行旅前端

Next.js App Router + JavaScript/JSX + 普通 CSS。当前为旅客视角的界面预览，不执行真实产品匹配、报价或 AI 解析。

从仓库根目录启动：

```bash
cd frontend
npm run dev
```

首次拉取代码后先运行 `npm ci`。开发服务器中修改组件会热更新。

- `/`：首页、文化主题筛选、每个目的地一张叙事卡片。
- `/plan`：需求表单与逐日预览。
- `/plan?destination=beijing`：只预填北京，日期与天数由用户选择。
- 旧演示入口 `/plan?journey=demo-beijing` 仍可使用；`demo-*` 不是真实产品编号。

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
| `data/demoJourneys.js` | 定制页行程样例，后续替换真实产品日程 |
| `lib/demoPreview.js` | 示意预览构造，后续通过适配层对接业务接口 |

正式产品介绍、照片、亮点和景点安排待下一轮整理，不将原始私人文档复制到 public。不显示成本作为销售报价，真实密钥只留在服务端。

验证：

```bash
npm run lint
npm run build
```

仓库路径包含冒号；npm 脚本直接通过 Node 调用本地 CLI，避免 PATH 拆分导致找不到命令。

当前阶段与下一步统一记录在 [`../docs/roadmap.md`](../docs/roadmap.md)。
