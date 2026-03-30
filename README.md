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
- `docs/normpeg-boq-docpeg-workflow.md`

## NormPeg / DocPeg 扩展

新增脚本与能力：

- `tools/normpeg/boq_to_utxo_init.py`：`400章(1).xlsx` 清单资产化与 BOQ->UTXO 初始化
- `services/api/boq_utxo_service.py::parse_boq_hierarchy(excel_file)`：生成章/节/目/细目树状 UTXO，父节点携带 children Merkle 指纹
- `tools/normpeg/triprole_lifecycle_demo.py`：TripRole 全链路动作模拟（含 FAIL->VARIATION->SETTLEMENT 解锁路径）
- `tools/normpeg/docpeg_chain_report.py`：按 `boq_item_uri` 聚合 Proof 链并渲染 Word/PDF + DSP zip
- `tools/normpeg/docfinal_full_aggregate.py`：执行 400 章全量聚合测试，导出“细目明细 + 章节汇总”主权大账本快照
- `services/api/normpeg_engine.py`：`get_threshold(spec_uri, context)` 动态阈值路由
- `services/api/triprole_engine.py`：`quality.check / measure.record / variation.record / settlement.confirm` + `aggregate_provenance_chain(utxo_id)`
- `services/api/boq_utxo_service.py::resolve_linked_gates / auto_bind_gates`：细目编码自动绑定 `QCGate`，注入 `linked_gate_id` 与规则清单
- `services/api/triprole_engine.py::update_chain_with_result`：质量判定结果链式回写，固化 `qc_gate_result` 与 `qc_gate_result_hash`
- `GET /v1/proof/docfinal/context|download`：支持 `aggregate_anchor_code + aggregate_direction + aggregate_level` 多维聚合渲染过滤
- `POST /v1/proof/triprole/apply-variation`：生成 `Δ UTXO` 并与 Genesis 账本余额合并，输出最新可消费余额
- `POST /v1/proof/triprole/execute`：提交时强制校验 `geo_location + server_timestamp_proof`，每笔 Proof 写入时空锚定指纹
- `POST /v1/proof/triprole/offline/replay`：离线 `OfflineProofPacket` 按 NTP 顺序重放，支持 `offline_packet_id` 幂等去重
- `POST /v1/proof/triprole/scan-confirm`：监理扫码确权，写入扫描签名并更新多方共识状态
- `POST /v1/proof/triprole/hardware/ingest`：BLE/IoT 量具直采入链，固化设备 SN、检定有效期与原始报文 Hash
- `GET /v1/proof/triprole/full-lineage/{utxo_id}`：输出金额→数量→质量→规范全链路血缘
- `GET /v1/proof/unit/merkle-root`：按单位工程生成递归 Merkle Root 与项目级 Global Fingerprint
- `TripRole DID Gate`：403 章关键动作默认要求 `rebar_special_operator` 资质 VC；无有效 DID/VC 将拒绝执行
- `Shadow Ledger Mirroring`：Proof 生成后可通过 `enterprise_configs.custom_fields.shadow_mirror_targets` 加密分发到多镜像节点
- `Sovereign Credit Scoring`：按 DID 聚合 NormPeg 偏差历史，自动输出信用分与快速通道资格（写入 `credit_endorsement`）
- `Biometric DID Binding`：`settlement.confirm` 强制 `signer_metadata` 生物核验（活体/指纹）与时间戳，确保“操作者即签发者”
- `Geo-Fencing Activation`：TripRole 自动校验电子围栏；`measure.record` 场外录入默认降级 `LOW trust` 并在 DocPeg 上红字预警（可 strict_mode 阻断）
- `services/api/docpeg_proof_chain_service.py`：`get_proof_chain(boq_item_uri)` 与报表打包
- `DocPeg Recursive Summary`：`hierarchy_summary_rows` 支持分部分项递归汇总渲染（章级进度 + 细目链路明细）
- `POST /v1/proof/payment/certificate/generate`：按 Settled UTXO（三方签名）自动生成计量支付证书
- `GET /v1/proof/payment/audit-trace/{payment_id}`：支付金额到规范依据的穿透审计图谱
- `POST /v1/proof/docfinal/finalize`：主权竣工包导出后执行 GitPeg 批量锚定收口
- `POST /v1/proof/spatial/bind` + `GET /v1/proof/spatial/dashboard`：空间坐标/BIM 与 UTXO 主权资产映射
- `POST /v1/proof/ai/predictive-quality`：NormPeg 历史偏差趋势预警 + 动态门控注入（专家复核）
- `POST /v1/proof/finance/proof/export`：结算链路导出银行审计加密信用凭证
- `POST /v1/proof/rwa/convert`：将已结算且三方签名资产聚合为 RWA 可融资凭证
- `POST /v1/proof/om/handover/export` + `POST /v1/proof/om/event/register`：施工身份向运维身份移交并持续挂载运维事件
- `POST /v1/proof/norm/evolution/report`：跨项目规范执行偏离度聚合与匿名化反馈建议
