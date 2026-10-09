# PostgreSQL 数据库使用说明

更新：2026-10-09。本机已经初始化、导入并启用数据库，不需要再执行初始化。所有命令从项目根目录执行，保留终端中的 `.venv/bin/python` 前缀。

## 数据库放在哪里，网站如何使用它

数据库服务运行在这台 Mac 上，地址 `127.0.0.1`、端口 `55432`、库名 `travel_copilot`。这是项目专用的本地开发库；它不会随网站代码自动部署到网上。

- 数据文件：`.local/database/pgdata/`。不要手动改里面的文件。
- 服务日志：`.local/database/postgres.log`。
- 连接配置：`.env.database.local`，已被 Git 忽略，权限为仅当前用户可读写。里面有密码，不能提交或发给前端。
- 后端账户 `travel_app` 只有读取权限；维护命令使用 `travel_owner`。

当前链路是：浏览器 → Next.js 服务端 → FastAPI → PostgreSQL。产品目录、Menu 文案、标准产品成本、互斥分支及 1.3 销售倍率已从数据库读取。数据库不可用时接口报服务不可用，不会偷偷使用旧文件的金额。

已导入 **21 个产品、58 条每日记录、261 个服务项目、6 个路线分支**。供应商表及服务关联表已建立，目前为空：现有运行成本表没有足以确认供应商身份和关系的数据。付款仍使用原来的 `data/payments.json`，上海半定制仍读取 `data/custom/`。

## 每次开发时怎么启动

先查看数据库是否运行：

```bash
.venv/bin/python -B scripts/local_database.py status
```

如果未运行，启动一次：

```bash
.venv/bin/python -B scripts/local_database.py start
```

然后照常启动后端和前端，分别放在不同终端。后端端口必须与 `frontend/.env.local` 中的服务地址一致；本次联调使用 8001：

```bash
.venv/bin/python -m uvicorn backend.app.main:app --host 127.0.0.1 --port 8001 --reload
```

前端终端：

```bash
cd frontend
npm run dev
```

数据库已经运行时无需重复 `start`。结束开发后可以先停止前后端，再停止数据库：

```bash
.venv/bin/python -B scripts/local_database.py stop
```

## 查看产品和成本

查看各表记录数、全部产品、上海服务和一个项目的价格历史：

```bash
.venv/bin/python -B scripts/database.py status
.venv/bin/python -B scripts/maintain_database.py products
.venv/bin/python -B scripts/maintain_database.py services --city 上海
.venv/bin/python -B scripts/maintain_database.py services --code SH-TICKET-06
.venv/bin/python -B scripts/maintain_database.py history --code SH-TICKET-06
```

例如本次导入的 `SH-TICKET-06` 是豫园，单位为“人”，平季成本 30 元、旺季成本 40 元，当前 `price_version` 为 42。这是**成本单价**；旅客报价由后端按人数、服务范围和成本 × 1.3 计算。

价格状态分别是：`fixed` 固定成本、`range_estimate` 源表范围价的估算、`confirmed_free` 已确认免费、`missing` 缺失。导入保留了原始价格字符串和文件来源。`CQ-ADD-01` 保留缺价状态，没有编造单价；已有业务复核拦截继续生效。

## 修改成本：新增版本，不覆盖历史

先用上面的 `services --code` 读取最新 `price_version`。确认真实业务价格后，再填写平季、旺季和操作人。

以下只是命令格式示例，**35/45 不是本次确认的新成本**；本轮没有修改实际价格：

```bash
.venv/bin/python -B scripts/maintain_database.py set-price \
  --code SH-TICKET-06 --standard 35 --peak 45 \
  --expected-version 42 --actor gengchenxuan
```

成功后命令输出新版本号，旧版保留并结束有效期，同时写入修改记录。如果有人已先改价，旧 `--expected-version` 会被拒绝；重新查看后再决定是否更新。金额必须非负且最多两位小数。已确认免费项目不能直接改成收费，需先核对产品范围。

维护提交后，新一次预览/报价会使用新成本；已经显示的前端报价需要重新点击预览。已保存的报价快照保持原值。当前价格版本即时生效，尚未提供未来日期定时调价。当前维护单位和计费范围保持既有规则，不能用改金额代替“按人/按车/按天/按次”的规则调整。

## 修改英文产品介绍

当前维护命令支持英文产品标题与整线介绍。例如：

```bash
.venv/bin/python -B scripts/maintain_database.py product-copy \
  --id SH-P-02 --title "Shanghai: Streets and Waterways" \
  --intro "Explore Shanghai's historic streets and the waterways of Zhujiajiao." \
  --actor gengchenxuan
```

这条命令会真正修改数据库；请用审核后的文案替换示例。修改后刷新页面、重新生成预览即可看到。它不会改变产品编号、天数、项目或价格。逐日亮点、新增/删除产品和路线结构暂未提供通用维护表单，需要后续受控编辑能力。

## 录入供应商并关联服务

只录入你已经确认的真实供应商。下面的名称、邮箱及编号都是格式示例，不应直接作为真实数据执行：

```bash
.venv/bin/python -B scripts/maintain_database.py supplier-add \
  --name "真实供应商名称" --email "contact@example.com" \
  --notes "已确认的服务范围" --actor gengchenxuan
.venv/bin/python -B scripts/maintain_database.py suppliers
.venv/bin/python -B scripts/maintain_database.py supplier-link \
  --supplier 1 --code SH-TICKET-06 --actor gengchenxuan
```

`--supplier` 使用新增命令返回的实际 ID。关联表示该供应商能提供此服务，当前不会自动选择供应商、覆盖成本或创建付款记录。供应商信息留在后端，旅客响应不包含联系方式。

## 保存和查看报价

浏览器的“Preview My Journey”目前只计算报价，不自动保存每次点击。运营可以显式保存审核过的需求和报价快照。

在 `.local/database/quote-request.json` 创建如下需求文件（可以用编辑器创建，先确认目录已存在）：

```json
{
  "city": "上海",
  "days": 3,
  "product_id": "SH-P-02",
  "adults": 2,
  "children": 0,
  "seniors": 0,
  "is_peak": false,
  "need_guide": false,
  "need_private_car": false,
  "selected_optional_items": [],
  "route_choices": []
}
```

保存并查看：

```bash
.venv/bin/python -B scripts/maintain_database.py save-quote \
  --request .local/database/quote-request.json --actor gengchenxuan
.venv/bin/python -B scripts/maintain_database.py quotes
.venv/bin/python -B scripts/maintain_database.py quote --id 返回的报价UUID
.venv/bin/python -B scripts/maintain_database.py audit --limit 20
```

快照包含需求、内部成本、旅客报价、使用的服务价格版本及销售规则版本。待复核/无有效金额的需求不能保存为成功报价。最后两个查看命令是本地运营工具，输出可能含内部成本，不是可发给旅客的公开响应。`--actor` 是本地审计标记，目前还不代表已验证的网页登录身份。

## 备份与恢复

定期备份，选择一个尚不存在的文件名：

```bash
.venv/bin/python -B scripts/local_database.py backup \
  --output .local/database/backups/backup-20261009-01.dump
```

备份包含成本、供应商和已保存报价，不能放进 `frontend/public/`。同机备份能用于操作回退，防止机器损坏还需要把备份安全地复制到另一处。

先恢复到**新库**检查，不覆盖当前业务库：

```bash
.venv/bin/python -B scripts/local_database.py restore \
  --input .local/database/backups/backup-20261009-01.dump \
  --database travel_copilot_recovery_20261009
```

恢复目标必须是未存在的 `travel_copilot_` 前缀库；命令不会修改当前连接配置。本轮已用 `initial-20261009.dump` 恢复到 `travel_copilot_restore_check` 并核对产品和价格，测试库仍保留，可供检查。

另一个 `travel_copilot_restore_atomic_check` 库专门用于实际执行维护命令验证，里面含明确标记的测试文案、供应商和改价记录，不能当作业务库恢复来源。

确需采用恢复库时：先停后端，备份当前库；在 `.env.database.local` 的两条连接地址末尾，将库名改为已检查的恢复库名，保留其他字段；重新启动后端并检查预览和报价。主库与恢复库均保留，便于回退。

## 用 SQL 查看表

学习数据库时可以进入命令行：

```bash
.venv/bin/python -B scripts/local_database.py console
```

在出现的数据库提示符中执行：

```sql
\dt
SELECT id, city, name, days FROM products ORDER BY id;
SELECT code, name, price, price_peak, price_version FROM current_service_costs WHERE city = '上海';
\q
```

维护优先使用上述专用命令，避免直接更新表而绕过价格历史和审计。需要图形数据库工具时，连接地址仍是 `127.0.0.1:55432`，用户名/密码从本地配置手动填写，不要复制到公开文档。

| 数据 | 表 |
|---|---|
| 产品、每天路线、项目名称及服务引用 | `products`、`product_days`、`product_item_names`、`product_code_refs` |
| 互斥分支与计费范围 | `route_branches`、`branch_items`、`cost_scopes` |
| 服务和历史成本 | `service_items`、`service_prices`；`current_service_costs` 是当前价视图 |
| 供应商及服务关联 | `suppliers`、`supplier_services` |
| Menu 文案 | `content_documents`，复杂叙事保留 JSONB |
| 销售规则及保存的报价 | `pricing_policies`、`quote_snapshots` |
| 导入、变更记录、结构版本 | `import_batches`、`audit_events`、`schema_migrations` |

## 文件、导入和验证的关系

数据库启用后，标准产品文件是初始来源、文件模式基线及离线导出输入。修改 CSV/JSON **不会更新当前数据库**；日常改价和文案用维护命令，不长期双写两套数据。当前 `export_frontend_products.py` 仍从文件生成静态备用数据，数据库文案修改不会自动反向导出到文件。

本机已完成首次导入。新机器先安装 PostgreSQL 工具与项目依赖，再按顺序运行：

```bash
.venv/bin/python -B scripts/local_database.py init
.venv/bin/python -B scripts/database.py audit
.venv/bin/python -B scripts/database.py migrate
.venv/bin/python -B scripts/database.py import
.venv/bin/python -B scripts/verify_database.py
.venv/bin/python -B scripts/database.py activate
```

`init` 拒绝覆盖已有数据目录/配置；导入是原子事务，同一批次重复执行不重复创建记录，已有数据不接受新文件强制覆盖。已应用的 SQL 迁移文件不能改写，结构变化新增迁移文件后执行 `migrate`。

首次迁移核对 `verify_database.py` 要求数据库与文件完全一致，**正常维护之后产生差异是预期的**，不应为了让它通过而覆盖数据库。`activate` 会检查首次核对之后数据未变；正常日常使用无需反复激活。

默认项目验证独立使用文件模式，不要求数据库在线、不调用付费模型：

```bash
.venv/bin/python -B scripts/verify_project.py
```

专门的数据库维护测试需明确启用，所有测试写操作都回滚：

```bash
RUN_DATABASE_TESTS=1 .venv/bin/python -B -m unittest tests.test_database_integration
```

测试使用初始数据基线；修改真实成本后应在独立测试库执行，并通过环境变量给测试设置两条连接地址，避免使用已维护的业务库。

应急时可显式选择文件模式并重启后端：

```bash
.venv/bin/python -B scripts/database.py use-files
```

文件模式不会带上数据库里的后续维护结果或供应商信息。恢复正常前需要核对数据差异；不要把它作为数据库故障时的自动报价替代。

## 本阶段边界

已完成本地 PostgreSQL、导入审计、后端读取切换、价格历史、维护命令、显式报价快照和备份恢复。尚未提供运营登录、网页维护界面、旅客询单提交或生产数据库部署；对外发布前仍需落实内部接口身份权限和生产配置。当前共享 API Key 保留，不能把它当作完整运营账户系统。

数据库连接与事务实现使用 [Psycopg 官方文档](https://www.psycopg.org/psycopg3/docs/basic/transactions.html)，关系约束与精确金额依据 [PostgreSQL 约束](https://www.postgresql.org/docs/16/ddl-constraints.html) 和 [数值类型](https://www.postgresql.org/docs/16/datatype-numeric.html)。

## 查看网站收到的咨询（2026-10-09 已接入）

旅客在 02 点击 `Talk to a Travel Expert`，填写姓名、邮箱和可选留言后，咨询保存到 `journey_enquiries`。提交成功显示 `TC-…` 咨询编号；不自动发送邮件，也不创建订单。

在项目根目录查看最新 50 份咨询，以及指定咨询的详情：

```bash
.venv/bin/python -B scripts/maintain_database.py enquiries
.venv/bin/python -B scripts/maintain_database.py enquiry --reference TC-实际咨询编号
```

列表显示创建时间、姓名/邮箱、产品、状态与报价变化标记。详情包含客人当时的 Menu/需求、留言、所展示销售估算、提交时复核的报价，以及成功报价快照关联。`quote_changed=true` 表示展示估算与提交时复核结果不同，需要先与客人确认；`review_reason` 保存待复核原因。没有展示过成功报价的咨询，`shown_quote` 可以为空；仍允许咨询。成功报价的内部成本和价格版本在关联的 `quote_snapshots` 中，不能将这些运营输出整体发给客人。

当前入口是本地命令，没有 `/ops` 网页或邮件通知，需要运营主动查看新咨询并使用团队邮箱联系客人。正式发布前再配置通知与运营接单入口；不要把“已保存咨询”当作邮件已发送。

本机已新增并配置 `travel_intake` 账户，连接配置为忽略文件中的 `TRAVEL_INTAKE_DATABASE_URL`。它只能读取报价所需目录、查询/新增咨询和新增报价快照，不能改成本、产品、供应商或已保存咨询；`travel_app` 不能读取客户咨询表。后端请求不使用维护账户密码写咨询。

新环境在数据库迁移后增加这一步：

```bash
.venv/bin/python -B scripts/database.py migrate
.venv/bin/python -B scripts/database.py intake
```

`intake` 使用本地维护权限配置受限账户及私有连接字段；不要把生成的连接地址复制到浏览器或 `NEXT_PUBLIC_*`。已存在且配置好的账户不会反复重置密码。迁移历史文件仍不改写。

咨询使用服务器签名的公开行程/报价快照（有效 2 小时），签名不含成本或数据库密码；预览过期需重新生成。接口重试使用同一请求编号，已经提交成功但响应丢失时，重试返回原咨询编号而不重复落库。价格再次核对与咨询/报价快照处于同一事务，提交失败不显示成功；数据库不可用或文件模式不能保存咨询。

本次实际网页提交在独立库 `travel_copilot_enquiry_validation` 中验证，含 `example.invalid` 测试邮箱和测试记录，不是业务咨询。业务主库没有留下测试咨询或报价。恢复到另一台机器时，除了数据库备份，还需先准备 `travel_owner`、`travel_app` 和 `travel_intake` 角色，重新配置该机器的连接密码；数据库备份不包含角色密码。

数据库咨询测试（所有写入回滚）：

```bash
RUN_DATABASE_TESTS=1 .venv/bin/python -B -m unittest tests.test_enquiry_database
```


## 新增联系页与酒店需求

本轮新增迁移 `003_custom_enquiries.sql`，已有数据保留。本地已应用；其他环境升级前备份，然后从根目录执行 `.venv/bin/python -B scripts/database.py migrate`。沿用现有 intake 权限，未增加维护权限。

旅客直接通过 `/plan` 提交后，同样使用以下命令接单：

```bash
.venv/bin/python -B scripts/maintain_database.py enquiries
.venv/bin/python -B scripts/maintain_database.py enquiry --reference TC-实际编号
```

列表新增 `enquiry_kind` 和 `preferences`：`product` 为带产品与预览快照的咨询，`custom` 为尚未选定产品的咨询。自定义咨询 `product_id`、展示报价、报价快照均为空，不应当作金额为零的订单。

`preferences.hotel_preference` 可为 `discuss`（希望听取建议）、`arrange`（请安排酒店）、`self_booked`（自行安排）；`hotel_quote_status=not_included` 明确当前金额不含住宿。自定义咨询还保存目的地意向、日期、时长、人数与兴趣。运营先联系旅客确认，再单独报价住宿。

当前没有自动业务邮件或运营网页登录，成功保存并不等于团队已收到外部通知。
