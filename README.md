# 量化平台

这是基于 `量化平台标准需求文档.md` 和 `量化平台技术架构文档.md` 启动的第一版工程骨架。

## 技术栈

- 前端：Vue 3、TypeScript、Element Plus、ECharts
- 后端：FastAPI、SQLAlchemy、Alembic
- 任务：Celery、Redis
- 数据库：PostgreSQL
- 回测：Backtrader
- 部署：Docker Compose

## 本阶段已实现

- FastAPI 服务骨架与 REST API 路由
- SQLAlchemy 模型和 Alembic 初始迁移
- Celery Worker/Beat 任务入口
- 策略、标的、组合、行情缓存、信号洞察、设置等 API 骨架
- Vue3 前端工程、路由、布局和核心页面
- Docker Compose 编排
- 策略沙箱镜像基础文件
- 本地演示回测闭环：组合创建后如果缺少行情，会生成 deterministic 演示日线数据，并写入净值、回撤、交易、持仓、资金流水和信号统计

## 启动

```bash
cp .env.example .env
docker compose up --build
```

初始化数据库：

```bash
docker compose exec api alembic upgrade head
```

访问：

- 前端：http://localhost:5173
- API：http://localhost:8000
- OpenAPI：http://localhost:8000/docs

## 后续实现重点

- TickFlow 行情接口真实适配
- Backtrader 回测结果落库
- 交易规则和指标计算完整实现
- 策略 Docker 沙箱真实运行链路
- 邮件发送配置持久化和通知重试
- 前端图表数据接入和页面细节完善

## 当前可验证流程

1. 打开 http://localhost:5173
2. 在“策略管理”新增一个 Backtrader 策略。
3. 在“组合管理”创建组合；创建页可直接新增 ETF/股票标的。
4. 组合创建后等待任务完成，进入组合详情查看净值曲线、回撤曲线、交易、持仓和资金流水。
5. 进入“信号洞察”查看价格走势、持仓占比、交易频率和波动率。

当前回测是演示实现，用于验证系统链路和页面展示；真实策略执行、TickFlow 行情和 Backtrader 完整成交逻辑仍在后续阶段接入。
