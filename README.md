# QCSpec 工程质检平台 Monorepo

QCSpec 是面向工程质检业务的多端项目，当前主干由 `apps/web` + `services/api` 驱动，使用 Supabase 作为后端数据与存储基础设施。

## 当前架构状态

- 生产主路径：`apps/web`（React + Vite）+ `services/api`（FastAPI）
- 共享层：`packages/types`、`packages/sdk`、`packages/proof`、`packages/db`
- 基础设施：`infra/supabase`（SQL 迁移）、`infra/docker`（容器配置）
- 预留目录（尚未形成稳定产线）：`apps/report`、`services/gate`

## Monorepo 结构

```text
qcspec_monorepo_v4/
  apps/
    web/            # Web 管理端（当前主应用）
    mobile/         # 移动端原型/页面
    report/         # 报告端预留目录
  packages/
    types/          # 共享类型定义
    sdk/            # 前端 API SDK 封装
    proof/          # Proof 相关逻辑
    db/             # 数据层工具
  services/
    api/            # FastAPI 后端（当前主服务）
    worker/         # 报告/任务处理脚本
    gate/           # 预留服务目录
  infra/
    supabase/       # Supabase SQL 迁移
    docker/         # Dockerfile / compose
```

## 本地开发

### 1) 安装依赖

```bash
npm install
```

### 2) 配置环境变量

项目根目录使用 `.env`，可从 `.env.example` 拷贝后填充。

```bash
cp .env.example .env
```

说明：本项目支持连接远程 Supabase（团队共享环境），并不要求本地自建 Supabase。

### 3) 启动 Web

```bash
npm --workspace @qcspec/web run dev
```

### 4) 启动 API

```bash
cd services/api
pip install -r requirements.txt
uvicorn main:app --reload --port 8000
```

API 文档地址：`http://localhost:8000/docs`

## 常用命令

```bash
npm run lint
npm run build
npm run test
```

> 说明：部分 workspace 目前为 `skip` 脚本（占位护栏），后续会逐步替换为真实测试与静态检查。

## 核心接口前缀

- `/v1/auth`
- `/v1/projects`
- `/v1/inspections`
- `/v1/photos`
- `/v1/reports`
- `/v1/verify`
- `/v1/proof`
- `/v1/team`
- `/v1/settings`
- `/v1/erpnext`

## 近期架构优化重点

1. 安全与鉴权收敛（公开接口、token 吊销一致性、凭据安全）
2. 后端 router 继续瘦身（service/repository 分层）
3. 前端继续拆分 `App.tsx`（按 domain + controller hook）
4. 把 `skip` 护栏逐步升级为真实 CI 校验

架构分层与扩展规范见：

- `docs/architecture-blueprint.md`
