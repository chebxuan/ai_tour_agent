# Docker Compose 部署与维护

更新：2026-10-09。用户网站已进入部署准备阶段，运营接单网页暂缓。目标服务器为 `120.27.240.194`，域名待申请。SSH 已连通；用户要求后续服务器命令由其亲自执行。旧 Nginx 已停止并禁用开机启动，配置备份为服务器 `/root/travel-deploy-backups/nginx-before-compose.tar.gz`；旧前后端进程仍仅监听本机。Docker 安装与新版发布尚未完成。

## 部署结构

浏览器 → Caddy → Next.js → FastAPI → PostgreSQL 16。只有 Caddy 发布 80/443；后端、数据库和维护工具不发布主机端口。前端仅转发既有公开产品、预览、销售报价和咨询接口，密钥只在服务端。

数据库使用命名卷；网站读取、咨询写入和数据库维护分别使用独立账户。API 容器没有数据库管理员密码。初始化任务先等待数据库健康，再应用不可修改的版本迁移，并且只给空产品库导入 21 个产品与现行成本 × 1.3 销售规则。已经维护过的服务器产品库不会被源码种子覆盖。

此部署不包含旧 Streamlit、付款 JSON、私人 PDF、个人材料、本机数据库或测试询单。不自动发送邮件。运营暂用服务器维护命令查看并人工回复。

## 第一次上线

以下项目命令在**服务器的项目根目录**执行。

1. 先确认服务器系统、磁盘和 80/443 是否被现有网站使用；按实际系统安装 Docker Engine 与 Compose 插件。安装入口：[Docker 官方安装说明](https://docs.docker.com/engine/install/)。不要在未知系统上直接执行一键脚本，也不要替换现有网站。
当前 Ubuntu 22.04 的已配置 Ubuntu 软件源提供 Docker 29.1.3 和 Compose 2.40.3；Docker 官方下载站连接被重置，可改用 Ubuntu 发行版维护的软件包。此方式使用现有的发行版签名软件源：

```bash
apt-get update
DEBIAN_FRONTEND=noninteractive NEEDRESTART_MODE=l apt-get install -y docker.io docker-compose-v2
systemctl enable --now docker
docker --version
docker compose version
```

这是服务器安装命令，由用户执行。不要混装发行版 Docker 与 Docker CE。`deploy/install-docker-ubuntu.sh` 保留官方仓库安装方式，在网络可达时才使用。

服务器约 1.6GB 内存、当前无 swap。构建前可执行 `sh deploy/prepare-swap.sh`，只在没有现行 swap 时创建专用 2GB swap，并保留 `/etc/fstab.before-travel-copilot`；不改现有 swap。前端镜像构建将 Node 堆上限设为 768MB。资源充足的其他服务器无需这一步。

2. 在本机仓库根目录执行 `python3 deploy/package.py`，生成忽略目录 `.local/deploy/` 下的发布包；上传指定包到服务器独立目录（例如 `/opt/travel-copilot`）并解压。发布包基于允许列表生成，会包含尚未提交的当前代码，不依赖 Git archive。
3. 在服务器生成一次专用配置：

```bash
python3 deploy/configure.py --site http://120.27.240.194
sh deploy/compose.sh config --quiet
sh deploy/compose.sh up -d --build
sh deploy/compose.sh ps -a
```

`configure.py` 生成四个独立随机密钥，保存到 Git 忽略的 `deploy/.env.production`（权限 600），不显示密钥且不覆盖已有配置。这个文件是服务器长期配置，备份时单独加密保管；不要上传本机开发配置。不要执行不带 `--quiet` 的 `config`，它会输出解析后的密钥。

数据库管理密码仅给 db、migrate 和按需 maintenance；两个受限密码仅给 API 与初始化任务；网站只获得后端 API 密钥。Docker 管理权限仍能读取容器环境，服务器账户和 Docker 权限应仅给维护人员。

Compose 的 migrate 为一次性任务，正常应显示 Exited (0)；db、api、frontend 应健康，caddy 应运行。若 migrate 失败，后端不会绕过数据库读旧 CSV。

已有 80/443 服务需保留时，可用 `--http-port 8080 --https-port 8443` 生成配置，访问 IP 的 8080 端口；脚本会同步填写受信任的 `SITE_ORIGIN`，Caddy 在容器内仍监听标准端口。

IP 的 HTTP 页面用于自己验收。正式收集客户姓名、邮箱和咨询前，切换到域名 HTTPS。服务器安全组只开放网站 80/443 和必要 SSH；不开放 3000、8000、5432。

## 网站验收

- 首页、照片、手机布局及目的地页面正常。
- 上海 3 日预览、销售估算、住宿提示、其他城市及分支正常，旅客响应中没有运营成本。
- 咨询成功后返回 TC 编号，并能在运营维护命令中找到对应记录。自测使用明确标注的测试联系信息。
- 数据库重启后记录仍存在；数据库故障时页面提示服务不可用，不展示旧成本总额。
- Caddy 反向代理后的同源咨询检查正常；无浏览器运行错误。

本机没有 Docker，容器镜像构建、Compose 启动和线上验收须在服务器实际执行。不要把本地 lint/build 的通过当成镜像部署成功。

## 域名与 HTTPS

确定域名后，将 A 记录指向服务器公网 IP。仅在服务器具备 IPv6 时设置 AAAA。80 和 443 需可达。编辑服务器 `deploy/.env.production` 中的 `SITE_ADDRESS=travel.example.com` 和 `SITE_ORIGIN=https://travel.example.com`（替换成实际域名），保留所有已有密码和 API_KEY。`SITE_ORIGIN` 是联系接口使用的受信任地址，不能只更改代理的域名。

```bash
sh deploy/compose.sh up -d --force-recreate frontend caddy
```

Caddy 自动申请、续期证书并将 HTTP 重定向到 HTTPS；证书存放在持久卷。切换后再次验收咨询提交，不要只看首页。[Caddy HTTPS 条件说明](https://caddyserver.com/docs/automatic-https)

若服务器位于中国大陆，正式域名接入还需按云服务商的实际要求办理备案等上线流程；先确认服务器地域，再使用对应服务商指南。[阿里云备案适用条件](https://www.alibabacloud.com/help/en/icp-filing/basic-icp-service/product-overview/icp-filing-requirements-for-a-regular-website)

## 查看咨询与维护数据库

```bash
sh deploy/compose.sh run --rm maintenance maintain enquiries
sh deploy/compose.sh run --rm maintenance maintain enquiry --reference TC实际编号
sh deploy/compose.sh run --rm maintenance maintain products
sh deploy/compose.sh run --rm maintenance maintain services --city 上海
```

这是既有维护 CLI，输出可能包含客户个人信息，只在授权服务器终端查看。详细改价、供应商和文案操作见 [数据库使用说明](database-guide.md)，用上述维护容器替代本机 Python 启动方式。此维护容器按需启动，不作为网站服务对外提供。

首次部署默认只导入经版本管理的产品/成本种子。如果此前已经在本机数据库维护了新价格、文案或供应商，需先核对并设计单独的目录数据迁移，不能直接复制包含测试询单的本机全库。之后的生产维护留在服务器数据库，更新代码不会重新导入覆盖。

## 更新与备份

先备份，再更新代码，保留服务器的 `.env.production`：

```bash
sh deploy/backup.sh
sh deploy/compose.sh build api frontend
sh deploy/compose.sh run --rm migrate
sh deploy/compose.sh up -d
sh deploy/compose.sh ps -a
```

备份为 `.local/backups/` 下权限 600 的 PostgreSQL 自定义格式文件，包含客户咨询。失败不留下伪装成成功备份的文件。按业务频率手动备份，并加密复制到服务器之外；本方案未创建定时任务。

排错：`sh deploy/compose.sh logs --tail=80 api`；避免将日志与咨询数据直接公开。

暂停网站可执行 `sh deploy/compose.sh stop`，不会删除数据库。**不要执行 `down -v`**，这会删除数据库和证书卷。

## 恢复与回退

恢复先在新数据库验证，不直接覆盖现行库：

```bash
sh deploy/compose.sh exec -T db createdb -U travel_owner travel_copilot_restore
sh deploy/compose.sh exec -T db pg_restore -U travel_owner -d travel_copilot_restore --single-transaction --exit-on-error < .local/backups/实际备份.dump
```

核对产品、成本、咨询与报价关联后，再安排停站和切换。恢复已有目标库会失败，应选择未使用的新名称。密码配置另行保管，数据库备份不包含角色密码。

发布前记录当前代码版本；可用 `APP_VERSION` 为镜像标记不同版本，保留上一版镜像。回退应用前先确认新迁移与旧代码兼容。schema 迁移文件不可改写；不自动执行降级或覆盖生产库。

根目录旧 `Dockerfile` / `render.yaml` 继续保留供原后端流程参考；本次全站部署使用 `deploy/compose.yaml`，两套入口不要混用。

## 本轮已验证与未验证

- 前端 lint、生产构建及独立生产启动通过；两个联系接口在代理场景接受配置域名来源、拒绝外站来源。无效表单返回 422，不创建咨询。
- 新增同源回归检查覆盖开发地址、IP/非标准端口、HTTPS、伪造转发头、缺少来源及无效配置。
- 独立临时 PostgreSQL 实测首次初始化、三次迁移、21 个产品、1.3 规则、读写权限和重复初始化保留维护数据；测试库没有咨询/报价种子，验证后已停止。
- 开发库与文件种子核对 192 个分支/季节/服务/家庭场景通过，公开产品与销售报价一致；约束验证回滚。
- 已创建并检查源码发布包排除配置、客户数据、付款、私人资料和密钥。尚未实际构建 Docker 镜像、启动服务器 Compose 或配置公网 HTTPS。
- 旧 Nginx 如需恢复，先停止新版 Caddy，再执行 `systemctl enable --now nginx`；不会删除原配置。
