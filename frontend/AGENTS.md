<!-- BEGIN:nextjs-agent-rules -->

## This is NOT the Next.js you know

This version has breaking changes — APIs, conventions, and file structure may all differ from your training data. Read the relevant guide in `node_modules/next/dist/docs/` (resolved from this file's directory; in monorepos the `next` package may not be visible from the repo root) before writing any code. Heed deprecation notices.

This block is written and re-added by `next dev` — verify at `node_modules/next/dist/server/lib/generate-agent-files.js`. Removing it from a diff only re-creates the uncommitted change; committing it with your work keeps the tree clean.

<!-- END:nextjs-agent-rules -->

## 本项目前端约定

- 遵循根目录 AGENTS.md；使用 JavaScript/JSX、App Router、普通 CSS。
- 新页面采用旅客视角：产品首页 `/`、联系页 `/plan`；目的地卡片通过 `/plan?destination=…` 进入行程预览。实施计划见 `../docs/roadmap.md`，未实现页面不能报告为完成。
- 正文与输入 16–18px、说明约 14px，按钮触控高度至少 44px；保持移动端和键盘可用。
- 演示产品/行程明确标注。内部成本不直接展示为销售报价；私有资料、供应商付款与 API Key 不进入客户端。
- 产品展示数据保留稳定编号，不复制整个后端数据目录到 public。
- 仓库路径含冒号，npm 脚本保留通过 Node 直接调用本地 CLI 的写法。
- 页面改动完成后运行 lint 和生产构建，并检查开发页面，明确报告未完成的验证。
