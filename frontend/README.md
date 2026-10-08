# 行旅前端

Next.js App Router + JavaScript/JSX + 普通 CSS。当前为旅客视角的界面预览，不执行真实产品匹配、报价或 AI 解析。

从仓库根目录启动：

```bash
cd frontend
npm run dev
```

首次拉取代码后先运行 `npm ci`。开发服务器中修改组件会热更新。

- `/`：首页、城市/天数筛选、产品卡片。
- `/plan`：需求表单与逐日预览。
- `/plan?journey=demo-beijing`：带入一个界面样例；`demo-*` 不是真实产品编号。

## 修改位置

| 位置 | 用途 |
|---|---|
| `app/layout.js` | 共享导航、页脚与页面元信息 |
| `app/globals.css` | 颜色、字体、间距与共享按钮样式 |
| `components/HomePage.jsx` | 首页首屏与区块组织 |
| `components/JourneyCatalog.jsx` | 首页筛选与产品列表 |
| `components/ProductCard.jsx` | 产品卡片 |
| `components/TripForm.jsx` | 需求表单 |
| `components/ItineraryPreview.jsx` | 方案状态与每日时间线 |
| `components/TravelPlanner.jsx` | 查询参数、表单状态与结果快照 |
| `components/ScenicArt.jsx` | 原创占位插画，并非目的地实景 |
| `data/demoJourneys.js` | 界面样例，下一轮替换为经过核对的公开产品内容 |
| `lib/demoPreview.js` | 示意预览构造，后续通过适配层对接业务接口 |

正式产品介绍、照片、亮点和景点安排待下一轮整理，不将原始私人文档复制到 public。不显示成本作为销售报价，真实密钥只留在服务端。

验证：

```bash
npm run lint
npm run build
```

仓库路径包含冒号；npm 脚本直接通过 Node 调用本地 CLI，避免 PATH 拆分导致找不到命令。

当前阶段与下一步统一记录在 [`../docs/roadmap.md`](../docs/roadmap.md)。
