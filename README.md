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

