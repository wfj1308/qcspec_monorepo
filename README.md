# QCSpec · 工程质检平台

> 工程建设全生命周期数字化 · GitPeg v:// 生态

## 产品线

```
SnapPeg   现场快照存证    → 入口·最低门槛·免费
LogPeg    施工日志管理    → 每日必填
QCSpec    质检数据录入    → 核心数据·按产值0.5%收费
DocFinal  竣工档案生成    → 最终交付
```

## Monorepo 结构

```
qcspec/
├── apps/
│   ├── web/          管理端（React + Supabase）
│   ├── mobile/       微信小程序（现场端）
│   └── report/       报告预览
│
├── packages/
│   ├── sdk/          TypeScript SDK（Supabase封装）
│   ├── db/           数据库工具函数
│   ├── proof/        Proof链生成
│   └── types/        共享类型定义 ← 从这里开始
│
├── services/
│   ├── api/          FastAPI后端（Python）
│   ├── gate/         Evidence Gate（AI质检识别）
│   └── worker/       报告生成引擎（docxtpl）
│
└── infra/
    ├── supabase/     SQL迁移文件
    └── docker/       容器配置
```

## 快速启动

### 1. 数据库初始化

```bash
# 在 Supabase Dashboard → SQL Editor 执行
infra/supabase/001_init.sql
infra/supabase/002_storage_bootstrap.sql
infra/supabase/003_coord_gitpeg_autoreg.sql
infra/supabase/004_coord_runtime_core.sql
```

### 2. 后端 API

```bash
cd services/api
pip install -r requirements.txt
cp ../../.env.example .env   # 填入 Supabase 配置
uvicorn main:app --reload --port 8000
# 访问 http://localhost:8000/docs
```

### 3. 前端（现阶段直接用 HTML）

```bash
# 直接打开
apps/web/index.html      # 管理端
apps/mobile/index.html   # 现场端
```

## API 接口

### 项目管理
```
GET  /v1/projects/              列表
POST /v1/projects/              创建（自动生成v://节点）
GET  /v1/projects/{id}          详情
```

### 质检记录
```
GET  /v1/inspections/?project_id=  列表
POST /v1/inspections/              提交（自动生成Proof）
GET  /v1/inspections/stats/{id}    统计
```

### 报告生成
```
POST /v1/reports/export        DocPeg同步导出（按type路由模板）
POST /v1/reports/generate      触发生成（异步）
GET  /v1/reports/?project_id=  列表
GET  /v1/reports/{id}          详情
```

## v:// 节点结构

```
v://cn.中北/
└── highway/京沪高速大修/          项目节点
    ├── inspection/uuid/           质检记录节点（自动生成）
    ├── reports/QC-20260322/       报告节点
    └── photos/uuid/               照片节点
```

## 技术栈

| 层级 | 技术 |
|------|------|
| 前端 | HTML/CSS/JS → React（迁移中）|
| 后端 | Python FastAPI |
| 数据库 | Supabase（PostgreSQL + RLS）|
| 存储 | Supabase Storage |
| 报告 | python-docx + docxtpl |
| 类型 | TypeScript（共享types包）|
| Monorepo | Turborepo |

## IR-8 映射

| IR层 | QCSpec对应 |
|------|-----------|
| IR1 主权 | v://项目节点·DTORole权限 |
| IR2 定义 | JTG F80规范SpecIR |
| IR5 运行 | 质检Trip执行调度 |
| IR6 验证 | 每条记录自动Proof存证 |

---

**QCSpec · qcspec.com · GitPeg生态 · 2026**
