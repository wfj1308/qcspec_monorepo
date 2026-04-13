# QCSpec DocPeg 联调验收清单（文档唯一源）

更新时间：2026-04-11

## 1. 单一事实来源

- API 规范唯一来源：`docs/qcspec-full-api-pack.md`
- Base URL：`https://api.docpeg.cn`
- 前端默认开启 DocPeg 严格模式：
  - 仅允许清单中定义的 `\`/projects\``、`\`/api/v1/*\`` 等路径
  - 非清单路径（例如旧 `\`/v1/auth\``、`\`/v1/inspections\``）默认拦截
- 如需临时回退旧接口（不建议）：
  - `VITE_ALLOW_LEGACY_QCSPEC_API=true`

## 2. 必测端点（P0）

- `POST /projects`
- `GET /projects`
- `GET /projects/{projectId}`
- `POST /api/v1/execpeg/execute`
- `GET /api/v1/execpeg/status/{execId}`
- `GET /api/v1/execpeg/status/{execId}/callbacks`
- `POST /api/v1/dtorole/role-bindings`
- `GET /api/v1/dtorole/permission-check`
- `GET /projects/{projectId}/entities`
- `GET /projects/{projectId}/process-chains`
- `GET /projects/{projectId}/process-chains/{chainId}/status`
- `GET /api/v1/normref/projects/{projectId}/forms/{formCode}`
- `POST /api/v1/normref/projects/{projectId}/forms/{formCode}/interpret-preview`
- `POST /api/v1/normref/projects/{projectId}/forms/{formCode}/draft-instances`
- `POST /api/v1/triprole/submit`
- `GET /api/v1/proof/{proofId}`
- `POST /api/v1/proof/{proofId}/verify`
- `POST /api/v1/boqitem/projects/{projectId}/consume`
- `POST /api/v1/boqitem/projects/{projectId}/settle`
- `POST /api/v1/files/upload`

## 3. 端到端最小闭环

1. `POST /projects` 创建项目，拿到 `projectId`
2. `POST /api/v1/execpeg/execute` 依次执行：
   - `highway_spu_creation@v1.0`
   - `register_project_participants@v1.0`
   - `create_section@v1.0`
3. `GET /projects/{projectId}/entities` 获取工程树
4. `GET /projects/{projectId}/process-chains` 获取工序链
5. `POST /api/v1/normref/.../interpret-preview`
6. `POST /api/v1/normref/.../draft-instances`
7. `POST /api/v1/normref/.../submit`
8. `POST /api/v1/triprole/submit` 完成工序动作
9. `GET /api/v1/proof/{proofId}` + `POST /api/v1/proof/{proofId}/verify`
10. `POST /api/v1/boqitem/.../consume` / `settle`

## 4. 前端验收标准

- 前端调用 URL 必须命中 `qcspec-full-api-pack` 清单
- 发现非清单路径时，前端应立即报错并停止请求
- 不得以“兼容 fallback / legacy 接口”作为默认行为

## 5. 变更规则

- 同事 API 变更后，先更新 `docs/qcspec-full-api-pack.md`
- 前端仅按更新后的清单调整，不接受口头临时路径
- 每次发版前执行一次“P0 端点 + 最小闭环”回归

## 6. 当前接入状态（2026-04-13）

### 6.1 P0 接口覆盖率

- 已接入：20 / 20
- 未接入：0 / 20
- 说明：`execpeg` 与 `boq consume/settle` 通过工序页、结算页的联调按钮触发；若上游未返回业务数据，页面仍按空数据兜底。

已接入（20）：
- `POST /projects`
- `GET /projects`
- `GET /projects/{projectId}`
- `POST /api/v1/dtorole/role-bindings`
- `GET /api/v1/dtorole/permission-check`
- `GET /projects/{projectId}/entities`
- `GET /projects/{projectId}/process-chains`
- `GET /projects/{projectId}/process-chains/{chainId}/status`
- `GET /api/v1/normref/projects/{projectId}/forms/{formCode}`
- `POST /api/v1/normref/projects/{projectId}/forms/{formCode}/interpret-preview`
- `POST /api/v1/normref/projects/{projectId}/forms/{formCode}/draft-instances`
- `POST /api/v1/triprole/submit`
- `GET /api/v1/proof/{proofId}`
- `POST /api/v1/proof/{proofId}/verify`
- `POST /api/v1/execpeg/execute`
- `GET /api/v1/execpeg/status/{execId}`
- `GET /api/v1/execpeg/status/{execId}/callbacks`
- `POST /api/v1/boqitem/projects/{projectId}/consume`
- `POST /api/v1/boqitem/projects/{projectId}/settle`
- `POST /api/v1/files/upload`

### 6.2 非 P0 状态

- 已接入 API Hook（工序页联调工具已挂载）：
- `POST /api/v1/execpeg/manual-input`
- `POST /api/v1/execpeg/register`
- `GET /api/v1/execpeg/highway-spus`
- `GET /api/v1/execpeg/highway-spus/{spuRef}`
- `POST /projects/{projectId}/documents`
- `POST /projects/{projectId}/documents/{documentId}/versions`
- `POST /projects/{projectId}/entities`
- `PATCH /projects/{projectId}/entities/{entityId}`
- `POST /api/v1/proof/{proofId}/attachments`

### 6.3 已清理项

- 已删除未使用且包含旧路径的前端服务：`apps/web/src/services/docpeg/coreApi.ts`
- `apps/web/src/services/docpeg/index.ts` 已改为仅导出 `httpClient` 相关能力
