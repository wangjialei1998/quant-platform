# Quant Platform

个人单用户量化平台 MVP。当前版本使用 Vue 3 + TypeScript + Element Plus + ECharts 前端，FastAPI 后端，PostgreSQL 主库，Redis + Celery 任务队列，Backtrader 策略在 Docker 沙箱镜像中隔离执行。

## 服务组成

Docker Compose 当前包含以下服务：

- `postgres`：PostgreSQL，宿主机端口 `15432`
- `redis`：Redis，宿主机端口 `16379`
- `api`：FastAPI，宿主机端口 `18000`
- `worker`：Celery Worker，执行策略测试、回测、监控、邮件、图表快照等任务
- `beat`：Celery Beat，负责每日定时任务
- `frontend`：Vue/Vite 开发服务，宿主机端口 `15173`
- `strategy-sandbox`：只用于构建策略沙箱镜像，不是常驻业务容器

策略实际运行依赖镜像 `quant-platform-strategy-sandbox:latest`。删除 `strategy-sandbox` 容器不会影响系统；删除该镜像后需要重新构建。

## 首次启动

在项目根目录执行：

```bash
cp .env.example .env
docker compose -p quant-platform build strategy-sandbox
docker compose -p quant-platform up -d --build postgres redis api worker beat frontend
docker compose -p quant-platform exec -T api sh -lc "cd /app && alembic -c alembic.ini upgrade head"
```

访问地址：

- 前端：http://localhost:15173
- API：http://localhost:18000
- OpenAPI：http://localhost:18000/docs

## 日常启动

如果镜像和依赖已经构建过，直接启动主服务：

```bash
docker compose -p quant-platform up -d postgres redis api worker beat frontend
```

查看服务状态：

```bash
docker compose -p quant-platform ps
```

查看后端日志：

```bash
docker compose -p quant-platform logs --tail=120 api
docker compose -p quant-platform logs --tail=120 worker
docker compose -p quant-platform logs --tail=120 beat
```

## 策略沙箱恢复

如果误删了 `strategy-sandbox` 容器，一般不需要处理。该容器只是构建镜像时使用，回测任务会临时创建并删除真正的沙箱容器。

如果误删了镜像 `quant-platform-strategy-sandbox:latest`，重新构建：

```bash
docker compose -p quant-platform build strategy-sandbox
```

验证镜像是否存在：

```bash
docker image ls quant-platform-strategy-sandbox
```

构建完成后不需要单独启动 `strategy-sandbox` 服务。继续使用页面的策略测试、组合创建、手动更新即可。

## 重新构建主服务

后端或前端依赖变更后：

```bash
docker compose -p quant-platform up -d --build api worker beat frontend
```

只修改 Python 或 Vue 源码时，当前 Compose 使用代码挂载，通常不需要重新构建；重启对应服务即可：

```bash
docker compose -p quant-platform restart api worker beat frontend
```

## 数据库迁移

执行迁移：

```bash
docker compose -p quant-platform exec -T api sh -lc "cd /app && alembic -c alembic.ini upgrade head"
```

保留数据重启不会清空数据库。PostgreSQL 数据保存在 Docker volume `quant-platform_postgres_data`。

## 定时任务

当前 Celery Beat 配置：

- 每天 `18:00` 运行组合监控，拉取最新日线并回测运行中的组合。
- 每个交易日 `08:30` 发送上一交易日组合日报。

注意：当前交易日判断仍按工作日处理，暂未接入完整 A 股节假日日历。

## 常见问题

### `No such image: quant-platform-strategy-sandbox:latest`

说明策略沙箱镜像不存在，执行：

```bash
docker compose -p quant-platform build strategy-sandbox
```

### `failed to connect to the docker API`

说明 Docker Desktop 没有启动，或当前终端无法访问 Docker。先确认 Docker Desktop 正常运行，再执行：

```bash
docker compose -p quant-platform ps
```

### 页面打不开

确认 `frontend` 服务已启动，并访问当前端口：

```bash
docker compose -p quant-platform ps frontend
```

浏览器打开：

```text
http://localhost:15173
```

### API 打不开

确认 `api` 服务已启动：

```bash
docker compose -p quant-platform ps api
docker compose -p quant-platform logs --tail=120 api
```

浏览器打开：

```text
http://localhost:18000/docs
```

## 当前功能范围

- 策略管理：上传、查看、测试 Backtrader 策略代码
- 标的管理：按股票/ETF 代码创建标的
- 组合管理：创建、编辑、删除、手动更新组合
- 回测监控：使用 TickFlow 日线数据和 Docker 沙箱中的 Backtrader 执行策略
- 组合详情：净值、回撤、持仓、交易、资金流水、指标卡片
- 信号洞察：价格走势、买卖点显示切换、标准化价格、信号分布、有效性、频率、波动率
- 邮件通知：SMTP 配置测试、每日组合 HTML 日报
