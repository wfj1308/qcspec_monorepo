# DocPeg 全量联调 API 文档（参数 + 返回结构）

- 基准地址: `https://api.docpeg.cn`
- OpenAPI: `https://api.docpeg.cn/openapi.json`
- 生成时间: 2026-04-10T07:20:28.775Z

## 通用请求头
- `content-type: application/json`（POST/PATCH/PUT 时）
- `x-actor-role: designer`（按你的角色替换）
- `x-actor-name: designer-user`（按你的账号替换）
- `authorization: Bearer <token>`（若接入会话鉴权时）

## projectId 获取
1. 调用 `GET /projects`
2. 使用返回的 `items[].id` 作为 `{projectId}`（例如 `PJT-D34A70B8`）

## 全量接口明细

### GET /admin/alert-events
- 概要: List alert events
- Path 参数:
- 无
- Query 参数:
- status (可选, string)
- severity (可选, string)
- rule_id (可选, string)
- from (可选, string)
- to (可选, string)
- limit (可选, integer)
- offset (可选, integer)
- Header 参数:
- 无
- 请求体:
- 无
- 响应:
- 200: OK；返回结构：未声明
- 403: Forbidden；返回结构：未声明

### POST /admin/alert-events/{eventId}/ack
- 概要: Acknowledge alert event
- Path 参数:
- eventId (必填, string)
- Query 参数:
- 无
- Header 参数:
- 无
- 请求体:
- 无
- 响应:
- 200: OK；返回结构：未声明
- 403: Forbidden；返回结构：未声明
- 404: Not found；返回结构：未声明

### GET /admin/alert-events/{eventId}/actions
- 概要: List alert event action trail
- Path 参数:
- eventId (必填, string)
- Query 参数:
- 无
- Header 参数:
- 无
- 请求体:
- 无
- 响应:
- 200: OK；返回结构：未声明
- 403: Forbidden；返回结构：未声明
- 404: Not found；返回结构：未声明

### POST /admin/alert-events/{eventId}/resolve
- 概要: Resolve alert event
- Path 参数:
- eventId (必填, string)
- Query 参数:
- 无
- Header 参数:
- 无
- 请求体:
- 无
- 响应:
- 200: OK；返回结构：未声明
- 403: Forbidden；返回结构：未声明
- 404: Not found；返回结构：未声明

### GET /admin/alerts
- 概要: List alert rules
- Path 参数:
- 无
- Query 参数:
- enabled (可选, boolean)
- severity (可选, string)
- metric_key (可选, string)
- Header 参数:
- 无
- 请求体:
- 无
- 响应:
- 200: OK；返回结构：未声明
- 403: Forbidden；返回结构：未声明

### POST /admin/alerts
- 概要: Upsert alert rule
- Path 参数:
- 无
- Query 参数:
- 无
- Header 参数:
- 无
- 请求体:
- 无
- 响应:
- 200: OK；返回结构：未声明
- 403: Forbidden；返回结构：未声明

### GET /admin/alerts/summary
- 概要: Alert summary counters
- Path 参数:
- 无
- Query 参数:
- 无
- Header 参数:
- 无
- 请求体:
- 无
- 响应:
- 200: OK；返回结构：未声明
- 403: Forbidden；返回结构：未声明

### DELETE /admin/alerts/{ruleId}
- 概要: Delete alert rule
- Path 参数:
- ruleId (必填, string)
- Query 参数:
- 无
- Header 参数:
- 无
- 请求体:
- 无
- 响应:
- 200: OK；返回结构：未声明
- 403: Forbidden；返回结构：未声明
- 404: Not found；返回结构：未声明

### GET /admin/api-coverage
- 概要: API coverage catalog for integrator automation
- Path 参数:
- 无
- Query 参数:
- 无
- Header 参数:
- 无
- 请求体:
- 无
- 响应:
- 200: OK；返回结构：未声明

### GET /admin/audit-logs
- 概要: Global audit logs query
- Path 参数:
- 无
- Query 参数:
- project_id (可选, string)
- actor_name (可选, string)
- actor_role (可选, string)
- action (可选, string)
- from (可选, string)
- to (可选, string)
- limit (可选, integer)
- offset (可选, integer)
- Header 参数:
- 无
- 请求体:
- 无
- 响应:
- 200: OK；返回结构：未声明
- 403: Forbidden；返回结构：未声明

### GET /admin/deployments
- 概要: List deployment records
- Path 参数:
- 无
- Query 参数:
- env (可选, string)
- status (可选, string)
- limit (可选, integer)
- offset (可选, integer)
- Header 参数:
- 无
- 请求体:
- 无
- 响应:
- 200: OK；返回结构：未声明
- 403: Forbidden；返回结构：未声明

### POST /admin/deployments
- 概要: Create deployment record
- Path 参数:
- 无
- Query 参数:
- 无
- Header 参数:
- 无
- 请求体:
- 无
- 响应:
- 200: OK；返回结构：未声明
- 403: Forbidden；返回结构：未声明

### GET /admin/deployments/rollbacks
- 概要: List rollback records globally
- Path 参数:
- 无
- Query 参数:
- env (可选, string)
- operator (可选, string)
- from (可选, string)
- to (可选, string)
- limit (可选, integer)
- offset (可选, integer)
- Header 参数:
- 无
- 请求体:
- 无
- 响应:
- 200: OK；返回结构：未声明
- 403: Forbidden；返回结构：未声明

### PATCH /admin/deployments/{deploymentId}
- 概要: Update deployment status
- Path 参数:
- deploymentId (必填, string)
- Query 参数:
- 无
- Header 参数:
- 无
- 请求体:
- 无
- 响应:
- 200: OK；返回结构：未声明
- 403: Forbidden；返回结构：未声明
- 404: Not found；返回结构：未声明

### POST /admin/deployments/{deploymentId}/rollback
- 概要: Rollback one deployment and register rollback record
- Path 参数:
- deploymentId (必填, string)
- Query 参数:
- 无
- Header 参数:
- 无
- 请求体:
- 无
- 响应:
- 200: OK；返回结构：未声明
- 403: Forbidden；返回结构：未声明
- 404: Not found；返回结构：未声明

### GET /admin/deployments/{deploymentId}/rollbacks
- 概要: List rollback records for one deployment
- Path 参数:
- deploymentId (必填, string)
- Query 参数:
- 无
- Header 参数:
- 无
- 请求体:
- 无
- 响应:
- 200: OK；返回结构：未声明
- 403: Forbidden；返回结构：未声明
- 404: Not found；返回结构：未声明

### GET /admin/idempotency-keys
- 概要: List idempotency key records
- Path 参数:
- 无
- Query 参数:
- 无
- Header 参数:
- 无
- 请求体:
- 无
- 响应:
- 200: OK；返回结构：未声明
- 403: Forbidden；返回结构：未声明

### DELETE /admin/idempotency-keys/{key}
- 概要: Delete one idempotency key record
- Path 参数:
- key (必填, string)
- Query 参数:
- 无
- Header 参数:
- 无
- 请求体:
- 无
- 响应:
- 200: OK；返回结构：未声明
- 403: Forbidden；返回结构：未声明
- 404: Not found；返回结构：未声明

### POST /admin/init
- 概要: Initialize schema and seed
- Path 参数:
- 无
- Query 参数:
- 无
- Header 参数:
- 无
- 请求体:
- 无
- 响应:
- 200: OK；返回结构：未声明

### POST /admin/maintenance/cleanup
- 概要: Cleanup expired sessions and stale idempotency records
- Path 参数:
- 无
- Query 参数:
- 无
- Header 参数:
- 无
- 请求体:
- 无
- 响应:
- 200: OK；返回结构：未声明
- 403: Forbidden；返回结构：未声明

### GET /admin/ops/summary
- 概要: Get operational summary metrics
- Path 参数:
- 无
- Query 参数:
- 无
- Header 参数:
- 无
- 请求体:
- 无
- 响应:
- 200: OK；返回结构：未声明
- 403: Forbidden；返回结构：未声明

### GET /admin/permission-check
- 概要: Evaluate permission with optional actor/project override
- Path 参数:
- 无
- Query 参数:
- permission (必填, string)
- project_id (可选, string)
- actor_role (可选, string)
- actor_name (可选, string)
- Header 参数:
- 无
- 请求体:
- 无
- 响应:
- 200: OK；返回结构：未声明
- 400: Bad request；返回结构：未声明

### GET /admin/policy-rules
- 概要: List D1 policy rules
- Path 参数:
- 无
- Query 参数:
- project_id (可选, string)
- Header 参数:
- 无
- 请求体:
- 无
- 响应:
- 200: OK；返回结构：未声明

### POST /admin/policy-rules
- 概要: Upsert policy rule
- Path 参数:
- 无
- Query 参数:
- 无
- Header 参数:
- 无
- 请求体:
- 无
- 响应:
- 200: OK；返回结构：未声明
- 403: Forbidden；返回结构：未声明

### DELETE /admin/policy-rules/{ruleId}
- 概要: Delete policy rule
- Path 参数:
- ruleId (必填, string)
- Query 参数:
- 无
- Header 参数:
- 无
- 请求体:
- 无
- 响应:
- 200: OK；返回结构：未声明
- 403: Forbidden；返回结构：未声明
- 404: Not found；返回结构：未声明

### GET /admin/rate-limits
- 概要: List API rate-limit policies
- Path 参数:
- 无
- Query 参数:
- scope_type (可选, string)
- scope_value (可选, string)
- method (可选, string)
- path_pattern (可选, string)
- Header 参数:
- 无
- 请求体:
- 无
- 响应:
- 200: OK；返回结构：未声明
- 403: Forbidden；返回结构：未声明

### POST /admin/rate-limits
- 概要: Upsert API rate-limit policy
- Path 参数:
- 无
- Query 参数:
- 无
- Header 参数:
- 无
- 请求体:
- 无
- 响应:
- 200: OK；返回结构：未声明
- 403: Forbidden；返回结构：未声明

### GET /admin/rate-limits/hits
- 概要: List API rate-limit hit buckets
- Path 参数:
- 无
- Query 参数:
- policy_id (可选, string)
- from (可选, string)
- to (可选, string)
- limit (可选, integer)
- offset (可选, integer)
- Header 参数:
- 无
- 请求体:
- 无
- 响应:
- 200: OK；返回结构：未声明
- 403: Forbidden；返回结构：未声明

### DELETE /admin/rate-limits/{ruleId}
- 概要: Delete API rate-limit policy
- Path 参数:
- ruleId (必填, string)
- Query 参数:
- 无
- Header 参数:
- 无
- 请求体:
- 无
- 响应:
- 200: OK；返回结构：未声明
- 403: Forbidden；返回结构：未声明
- 404: Not found；返回结构：未声明

### DELETE /admin/rate-limits/{ruleId}/hits
- 概要: Delete one rate-limit policy hit buckets
- Path 参数:
- ruleId (必填, string)
- Query 参数:
- 无
- Header 参数:
- 无
- 请求体:
- 无
- 响应:
- 200: OK；返回结构：未声明
- 403: Forbidden；返回结构：未声明
- 404: Not found；返回结构：未声明

### GET /admin/role-bindings
- 概要: List role bindings
- Path 参数:
- 无
- Query 参数:
- project_id (可选, string)
- Header 参数:
- 无
- 请求体:
- 无
- 响应:
- 200: OK；返回结构：未声明

### POST /admin/role-bindings
- 概要: Upsert role binding
- Path 参数:
- 无
- Query 参数:
- 无
- Header 参数:
- 无
- 请求体:
- 无
- 响应:
- 200: OK；返回结构：未声明
- 403: Forbidden；返回结构：未声明

### DELETE /admin/role-bindings/{bindingId}
- 概要: Delete role binding
- Path 参数:
- bindingId (必填, string)
- Query 参数:
- 无
- Header 参数:
- 无
- 请求体:
- 无
- 响应:
- 200: OK；返回结构：未声明
- 403: Forbidden；返回结构：未声明
- 404: Not found；返回结构：未声明

### POST /api/ai/plan-trips
- 概要: AI Trip planner (rules engine, model-free)
- Path 参数:
- 无
- Query 参数:
- 无
- Header 参数:
- 无
- 请求体:
- 无
- 响应:
- 200: OK；返回结构：未声明
- 400: Bad request；返回结构：未声明

### POST /api/ai/trip-interpret
- 概要: AI Trip Interpreter (rules engine, model-free)
- Path 参数:
- 无
- Query 参数:
- 无
- Header 参数:
- 无
- 请求体:
- 无
- 响应:
- 200: OK；返回结构：未声明
- 400: Bad request；返回结构：未声明

### GET /api/proofs
- 概要: List proofs
- Path 参数:
- 无
- Query 参数:
- project_id (可选, string)
- document_id (可选, string)
- version_id (可选, string)
- result (可选, string)
- validation_status (可选, string)
- executor_uri (可选, string)
- norm_ref (可选, string)
- search (可选, string)
- from (可选, string)
- to (可选, string)
- limit (可选, integer)
- offset (可选, integer)
- Header 参数:
- 无
- 请求体:
- 无
- 响应:
- 200: OK；返回结构：未声明

### GET /api/proofs/{proofId}
- 概要: Get proof detail
- Path 参数:
- proofId (必填, string)
- Query 参数:
- 无
- Header 参数:
- 无
- 请求体:
- 无
- 响应:
- 200: OK；返回结构：未声明
- 404: Not found；返回结构：未声明

### GET /api/trips
- 概要: List trips
- Path 参数:
- 无
- Query 参数:
- project_id (可选, string)
- action (可选, string)
- status (可选, string)
- document_id (可选, string)
- version_id (可选, string)
- executor_uri (可选, string)
- target_uri (可选, string)
- search (可选, string)
- from (可选, string)
- to (可选, string)
- limit (可选, integer)
- offset (可选, integer)
- Header 参数:
- 无
- 请求体:
- 无
- 响应:
- 200: OK；返回结构：未声明

### POST /api/trips
- 概要: Create trip
- Path 参数:
- 无
- Query 参数:
- 无
- Header 参数:
- x-idempotency-key (可选, string)
- 请求体:
- 无
- 响应:
- 201: Created；返回结构：未声明
- 403: Forbidden；返回结构：未声明

### GET /api/trips/{tripId}
- 概要: Get trip detail
- Path 参数:
- tripId (必填, string)
- Query 参数:
- 无
- Header 参数:
- 无
- 请求体:
- 无
- 响应:
- 200: OK；返回结构：未声明
- 404: Not found；返回结构：未声明

### POST /api/trips/{tripId}/complete
- 概要: Complete trip
- Path 参数:
- tripId (必填, string)
- Query 参数:
- 无
- Header 参数:
- x-idempotency-key (可选, string)
- 请求体:
- 无
- 响应:
- 200: OK；返回结构：未声明
- 403: Forbidden；返回结构：未声明
- 404: Not found；返回结构：未声明

### POST /approvals/batch-resolve
- 概要: Resolve approval nodes in batch
- Path 参数:
- 无
- Query 参数:
- 无
- Header 参数:
- x-idempotency-key (可选, string)
- 请求体:
- 无
- 响应:
- 200: OK；返回结构：未声明
- 207: Partial success；返回结构：未声明
- 400: Bad request；返回结构：未声明

### POST /approvals/{approvalId}/resolve
- 概要: Resolve approval node
- Path 参数:
- approvalId (必填, string)
- Query 参数:
- 无
- Header 参数:
- x-idempotency-key (可选, string)
- 请求体:
- 无
- 响应:
- 200: OK；返回结构：未声明
- 403: Forbidden；返回结构：未声明
- 404: Not found；返回结构：未声明

### GET /auth/api-keys
- 概要: List API keys (owner/system)
- Path 参数:
- 无
- Query 参数:
- subject (可选, string)
- actor_role (可选, string)
- active (可选, boolean)
- include_disabled (可选, boolean)
- limit (可选, integer)
- offset (可选, integer)
- Header 参数:
- 无
- 请求体:
- 无
- 响应:
- 200: OK；返回结构：未声明
- 403: Forbidden；返回结构：未声明

### POST /auth/api-keys
- 概要: Create API key (returns plain token once)
- Path 参数:
- 无
- Query 参数:
- 无
- Header 参数:
- 无
- 请求体:
- 无
- 响应:
- 200: OK；返回结构：未声明
- 400: Bad request；返回结构：未声明
- 403: Forbidden；返回结构：未声明

### DELETE /auth/api-keys/{keyId}
- 概要: Delete one API key
- Path 参数:
- keyId (必填, string)
- Query 参数:
- 无
- Header 参数:
- 无
- 请求体:
- 无
- 响应:
- 200: OK；返回结构：未声明
- 403: Forbidden；返回结构：未声明
- 404: Not found；返回结构：未声明

### PATCH /auth/api-keys/{keyId}
- 概要: Update API key metadata or status
- Path 参数:
- keyId (必填, string)
- Query 参数:
- 无
- Header 参数:
- 无
- 请求体:
- 无
- 响应:
- 200: OK；返回结构：未声明
- 400: Bad request；返回结构：未声明
- 403: Forbidden；返回结构：未声明
- 404: Not found；返回结构：未声明

### POST /auth/api-keys/{keyId}/rotate
- 概要: Rotate API key token (returns new plain token once)
- Path 参数:
- keyId (必填, string)
- Query 参数:
- 无
- Header 参数:
- 无
- 请求体:
- 无
- 响应:
- 200: OK；返回结构：未声明
- 400: Bad request；返回结构：未声明
- 403: Forbidden；返回结构：未声明
- 404: Not found；返回结构：未声明

### POST /auth/introspect
- 概要: Introspect session or API key token (AuthPeg/OIDC seam)
- Path 参数:
- 无
- Query 参数:
- 无
- Header 参数:
- 无
- 请求体:
- 无
- 响应:
- 200: OK；返回结构：未声明
- 401: Unauthorized；返回结构：未声明

### POST /auth/logout
- 概要: Logout current API session
- Path 参数:
- 无
- Query 参数:
- 无
- Header 参数:
- 无
- 请求体:
- 无
- 响应:
- 200: OK；返回结构：未声明
- 401: Unauthorized；返回结构：未声明

### GET /auth/me
- 概要: Resolve current actor by Bearer or API key token
- Path 参数:
- 无
- Query 参数:
- 无
- Header 参数:
- 无
- 请求体:
- 无
- 响应:
- 200: OK；返回结构：未声明
- 401: Unauthorized；返回结构：未声明

### POST /auth/session
- 概要: Issue API session token (OIDC/AuthPeg seam)
- Path 参数:
- 无
- Query 参数:
- 无
- Header 参数:
- 无
- 请求体:
- 无
- 响应:
- 200: OK；返回结构：未声明
- 400: Bad request；返回结构：未声明

### GET /auth/sessions
- 概要: List API sessions for current subject (or system-scoped query)
- Path 参数:
- 无
- Query 参数:
- subject (可选, string)
- active (可选, boolean)
- limit (可选, integer)
- offset (可选, integer)
- include_token (可选, boolean)
- Header 参数:
- 无
- 请求体:
- 无
- 响应:
- 200: OK；返回结构：未声明
- 401: Unauthorized；返回结构：未声明
- 403: Forbidden；返回结构：未声明

### DELETE /auth/sessions/{token}
- 概要: Revoke one API session by token (supports token=current)
- Path 参数:
- token (必填, string)
- Query 参数:
- 无
- Header 参数:
- 无
- 请求体:
- 无
- 响应:
- 200: OK；返回结构：未声明
- 401: Unauthorized；返回结构：未声明
- 403: Forbidden；返回结构：未声明
- 404: Not found；返回结构：未声明

### GET /files
- 概要: List file metadata
- Path 参数:
- 无
- Query 参数:
- project_id (可选, string)
- document_id (可选, string)
- version_id (可选, string)
- proof_id (可选, string)
- uploaded_by (可选, string)
- content_type (可选, string)
- search (可选, string)
- size_min (可选, integer)
- size_max (可选, integer)
- from (可选, string)
- to (可选, string)
- limit (可选, integer)
- offset (可选, integer)
- Header 参数:
- 无
- 请求体:
- 无
- 响应:
- 200: OK；返回结构：未声明

### DELETE /files/{fileId}
- 概要: Delete file metadata and object
- Path 参数:
- fileId (必填, string)
- Query 参数:
- 无
- Header 参数:
- 无
- 请求体:
- 无
- 响应:
- 200: OK；返回结构：未声明
- 403: Forbidden；返回结构：未声明
- 404: Not found；返回结构：未声明

### GET /files/{fileId}
- 概要: Get file metadata by id
- Path 参数:
- fileId (必填, string)
- Query 参数:
- 无
- Header 参数:
- 无
- 请求体:
- 无
- 响应:
- 200: OK；返回结构：未声明
- 404: Not found；返回结构：未声明

### GET /health
- 概要: Health check
- Path 参数:
- 无
- Query 参数:
- 无
- Header 参数:
- 无
- 请求体:
- 无
- 响应:
- 200: OK；返回结构：未声明

### GET /health/ready
- 概要: Readiness check (DB/R2)
- Path 参数:
- 无
- Query 参数:
- 无
- Header 参数:
- 无
- 请求体:
- 无
- 响应:
- 200: Ready；返回结构：未声明
- 503: Not ready；返回结构：未声明

### GET /integrations/bot-events
- 概要: List bot event jobs
- Path 参数:
- 无
- Query 参数:
- 无
- Header 参数:
- 无
- 请求体:
- 无
- 响应:
- 200: OK；返回结构：未声明

### POST /integrations/bot-events
- 概要: Enqueue one bot event job
- Path 参数:
- 无
- Query 参数:
- 无
- Header 参数:
- 无
- 请求体:
- 无
- 响应:
- 200: OK；返回结构：未声明
- 403: Forbidden；返回结构：未声明

### POST /integrations/bot-events/dispatch
- 概要: Dispatch pending bot event jobs
- Path 参数:
- 无
- Query 参数:
- 无
- Header 参数:
- 无
- 请求体:
- 无
- 响应:
- 200: OK；返回结构：未声明
- 403: Forbidden；返回结构：未声明

### GET /integrations/bot-events/stats
- 概要: Get bot event job statistics
- Path 参数:
- 无
- Query 参数:
- 无
- Header 参数:
- 无
- 请求体:
- 无
- 响应:
- 200: OK；返回结构：未声明

### POST /integrations/bot-events/{eventJobId}/replay
- 概要: Replay one bot event job (requeue)
- Path 参数:
- eventJobId (必填, string)
- Query 参数:
- 无
- Header 参数:
- 无
- 请求体:
- 无
- 响应:
- 200: OK；返回结构：未声明
- 403: Forbidden；返回结构：未声明
- 404: Not found；返回结构：未声明

### GET /integrations/bots
- 概要: List integration bots
- Path 参数:
- 无
- Query 参数:
- 无
- Header 参数:
- 无
- 请求体:
- 无
- 响应:
- 200: OK；返回结构：未声明

### POST /integrations/bots
- 概要: Create or update integration bot
- Path 参数:
- 无
- Query 参数:
- 无
- Header 参数:
- 无
- 请求体:
- 无
- 响应:
- 200: OK；返回结构：未声明
- 403: Forbidden；返回结构：未声明

### POST /integrations/bots/dispatch-pending
- 概要: Dispatch enabled bots (manual/scheduler seam)
- Path 参数:
- 无
- Query 参数:
- 无
- Header 参数:
- 无
- 请求体:
- 无
- 响应:
- 200: OK；返回结构：未声明
- 403: Forbidden；返回结构：未声明

### GET /integrations/bots/runs
- 概要: List recent runs across bots
- Path 参数:
- 无
- Query 参数:
- 无
- Header 参数:
- 无
- 请求体:
- 无
- 响应:
- 200: OK；返回结构：未声明

### GET /integrations/bots/runs/export.csv
- 概要: Export recent runs across bots as CSV
- Path 参数:
- 无
- Query 参数:
- 无
- Header 参数:
- 无
- 请求体:
- 无
- 响应:
- 200: OK；返回结构：未声明

### GET /integrations/bots/stats
- 概要: Get integration bots aggregate statistics
- Path 参数:
- 无
- Query 参数:
- 无
- Header 参数:
- 无
- 请求体:
- 无
- 响应:
- 200: OK；返回结构：未声明

### DELETE /integrations/bots/{botId}
- 概要: Delete integration bot
- Path 参数:
- botId (必填, string)
- Query 参数:
- 无
- Header 参数:
- 无
- 请求体:
- 无
- 响应:
- 200: OK；返回结构：未声明
- 404: Not found；返回结构：未声明

### GET /integrations/bots/{botId}
- 概要: Get integration bot detail
- Path 参数:
- botId (必填, string)
- Query 参数:
- 无
- Header 参数:
- 无
- 请求体:
- 无
- 响应:
- 200: OK；返回结构：未声明
- 404: Not found；返回结构：未声明

### PATCH /integrations/bots/{botId}
- 概要: Patch integration bot
- Path 参数:
- botId (必填, string)
- Query 参数:
- 无
- Header 参数:
- 无
- 请求体:
- 无
- 响应:
- 200: OK；返回结构：未声明
- 404: Not found；返回结构：未声明

### POST /integrations/bots/{botId}/run
- 概要: Manually run one bot now
- Path 参数:
- botId (必填, string)
- Query 参数:
- 无
- Header 参数:
- 无
- 请求体:
- 无
- 响应:
- 200: OK；返回结构：未声明
- 404: Not found；返回结构：未声明

### GET /integrations/bots/{botId}/runs
- 概要: List bot run history
- Path 参数:
- botId (必填, string)
- Query 参数:
- 无
- Header 参数:
- 无
- 请求体:
- 无
- 响应:
- 200: OK；返回结构：未声明
- 404: Not found；返回结构：未声明

### GET /integrations/bots/{botId}/runs/{runId}
- 概要: Get one bot run detail
- Path 参数:
- botId (必填, string)
- runId (必填, string)
- Query 参数:
- 无
- Header 参数:
- 无
- 请求体:
- 无
- 响应:
- 200: OK；返回结构：未声明
- 404: Not found；返回结构：未声明

### POST /integrations/bots/{botId}/runs/{runId}/replay
- 概要: Replay one bot run
- Path 参数:
- botId (必填, string)
- runId (必填, string)
- Query 参数:
- 无
- Header 参数:
- 无
- 请求体:
- 无
- 响应:
- 200: OK；返回结构：未声明
- 404: Not found；返回结构：未声明

### GET /integrations/bots/{botId}/stats
- 概要: Get one bot run statistics
- Path 参数:
- botId (必填, string)
- Query 参数:
- 无
- Header 参数:
- 无
- 请求体:
- 无
- 响应:
- 200: OK；返回结构：未声明
- 404: Not found；返回结构：未声明

### GET /integrations/statuses
- 概要: List integration statuses and seams
- Path 参数:
- 无
- Query 参数:
- 无
- Header 参数:
- 无
- 请求体:
- 无
- 响应:
- 200: OK；返回结构：未声明

### GET /integrations/webhooks
- 概要: List webhook subscriptions
- Path 参数:
- 无
- Query 参数:
- 无
- Header 参数:
- 无
- 请求体:
- 无
- 响应:
- 200: OK；返回结构：未声明

### POST /integrations/webhooks
- 概要: Create webhook subscription
- Path 参数:
- 无
- Query 参数:
- 无
- Header 参数:
- 无
- 请求体:
- 无
- 响应:
- 200: OK；返回结构：未声明
- 403: Forbidden；返回结构：未声明

### DELETE /integrations/webhooks/{webhookId}
- 概要: Delete webhook subscription
- Path 参数:
- webhookId (必填, string)
- Query 参数:
- 无
- Header 参数:
- 无
- 请求体:
- 无
- 响应:
- 200: OK；返回结构：未声明
- 404: Not found；返回结构：未声明

### GET /integrations/webhooks/{webhookId}
- 概要: Get webhook subscription detail
- Path 参数:
- webhookId (必填, string)
- Query 参数:
- 无
- Header 参数:
- 无
- 请求体:
- 无
- 响应:
- 200: OK；返回结构：未声明
- 404: Not found；返回结构：未声明

### PATCH /integrations/webhooks/{webhookId}
- 概要: Update webhook subscription
- Path 参数:
- webhookId (必填, string)
- Query 参数:
- 无
- Header 参数:
- 无
- 请求体:
- 无
- 响应:
- 200: OK；返回结构：未声明
- 400: Bad request；返回结构：未声明
- 403: Forbidden；返回结构：未声明
- 404: Not found；返回结构：未声明

### GET /integrations/webhooks/{webhookId}/dead-letter
- 概要: List webhook dead-letter deliveries
- Path 参数:
- webhookId (必填, string)
- Query 参数:
- 无
- Header 参数:
- 无
- 请求体:
- 无
- 响应:
- 200: OK；返回结构：未声明
- 404: Not found；返回结构：未声明

### POST /integrations/webhooks/{webhookId}/dead-letter/replay
- 概要: Batch replay dead-letter deliveries
- Path 参数:
- webhookId (必填, string)
- Query 参数:
- 无
- Header 参数:
- 无
- 请求体:
- 无
- 响应:
- 200: OK；返回结构：未声明
- 403: Forbidden；返回结构：未声明
- 404: Not found；返回结构：未声明

### GET /integrations/webhooks/{webhookId}/deliveries
- 概要: List webhook delivery history
- Path 参数:
- webhookId (必填, string)
- Query 参数:
- status (可选, string)
- search (可选, string)
- from (可选, string)
- to (可选, string)
- limit (可选, integer)
- offset (可选, integer)
- Header 参数:
- 无
- 请求体:
- 无
- 响应:
- 200: OK；返回结构：未声明
- 404: Not found；返回结构：未声明

### GET /integrations/webhooks/{webhookId}/deliveries/{deliveryId}
- 概要: Get webhook delivery detail
- Path 参数:
- webhookId (必填, string)
- deliveryId (必填, string)
- Query 参数:
- 无
- Header 参数:
- 无
- 请求体:
- 无
- 响应:
- 200: OK；返回结构：未声明
- 404: Not found；返回结构：未声明

### POST /integrations/webhooks/{webhookId}/deliveries/{deliveryId}/replay
- 概要: Replay one webhook delivery (optionally bypass retry policy)
- Path 参数:
- webhookId (必填, string)
- deliveryId (必填, string)
- Query 参数:
- 无
- Header 参数:
- 无
- 请求体:
- 无
- 响应:
- 200: OK；返回结构：未声明
- 403: Forbidden；返回结构：未声明
- 404: Not found；返回结构：未声明

### POST /integrations/webhooks/{webhookId}/deliveries/{deliveryId}/retry
- 概要: Retry one webhook delivery
- Path 参数:
- webhookId (必填, string)
- deliveryId (必填, string)
- Query 参数:
- 无
- Header 参数:
- 无
- 请求体:
- 无
- 响应:
- 200: OK；返回结构：未声明
- 403: Forbidden；返回结构：未声明
- 404: Not found；返回结构：未声明

### GET /integrations/webhooks/{webhookId}/delivery-stats
- 概要: Get webhook delivery statistics
- Path 参数:
- webhookId (必填, string)
- Query 参数:
- 无
- Header 参数:
- 无
- 请求体:
- 无
- 响应:
- 200: OK；返回结构：未声明
- 404: Not found；返回结构：未声明

### POST /integrations/webhooks/{webhookId}/dispatch-pending
- 概要: Dispatch pending/failed deliveries in batch
- Path 参数:
- webhookId (必填, string)
- Query 参数:
- 无
- Header 参数:
- 无
- 请求体:
- 无
- 响应:
- 200: OK；返回结构：未声明
- 403: Forbidden；返回结构：未声明
- 404: Not found；返回结构：未声明

### GET /integrations/webhooks/{webhookId}/retry-policy
- 概要: Get webhook retry policy
- Path 参数:
- webhookId (必填, string)
- Query 参数:
- 无
- Header 参数:
- 无
- 请求体:
- 无
- 响应:
- 200: OK；返回结构：未声明
- 404: Not found；返回结构：未声明

### PUT /integrations/webhooks/{webhookId}/retry-policy
- 概要: Upsert webhook retry policy
- Path 参数:
- webhookId (必填, string)
- Query 参数:
- 无
- Header 参数:
- 无
- 请求体:
- 无
- 响应:
- 200: OK；返回结构：未声明
- 403: Forbidden；返回结构：未声明
- 404: Not found；返回结构：未声明

### POST /integrations/webhooks/{webhookId}/rotate-secret
- 概要: Rotate webhook secret
- Path 参数:
- webhookId (必填, string)
- Query 参数:
- 无
- Header 参数:
- 无
- 请求体:
- 无
- 响应:
- 200: OK；返回结构：未声明
- 403: Forbidden；返回结构：未声明
- 404: Not found；返回结构：未声明

### POST /integrations/webhooks/{webhookId}/test
- 概要: Send webhook test delivery record
- Path 参数:
- webhookId (必填, string)
- Query 参数:
- 无
- Header 参数:
- 无
- 请求体:
- 无
- 响应:
- 200: OK；返回结构：未声明
- 404: Not found；返回结构：未声明

### GET /openapi.json
- 概要: OpenAPI spec
- Path 参数:
- 无
- Query 参数:
- 无
- Header 参数:
- 无
- 请求体:
- 无
- 响应:
- 200: OK；返回结构：未声明

### GET /projects
- 概要: List projects
- Path 参数:
- 无
- Query 参数:
- 无
- Header 参数:
- 无
- 请求体:
- 无
- 响应:
- 200: OK；返回结构：未声明

### POST /projects
- 概要: Create project
- Path 参数:
- 无
- Query 参数:
- 无
- Header 参数:
- x-idempotency-key (可选, string)
- 请求体:
- 无
- 响应:
- 201: Created；返回结构：未声明
- 403: Forbidden；返回结构：未声明
- 409: Conflict；返回结构：未声明

### GET /projects/{projectId}
- 概要: Get project overview
- Path 参数:
- projectId (必填, string)
- Query 参数:
- 无
- Header 参数:
- 无
- 请求体:
- 无
- 响应:
- 200: OK；返回结构：未声明
- 404: Not found；返回结构：未声明

### PATCH /projects/{projectId}
- 概要: Update project metadata
- Path 参数:
- projectId (必填, string)
- Query 参数:
- 无
- Header 参数:
- 无
- 请求体:
- 无
- 响应:
- 200: OK；返回结构：未声明
- 403: Forbidden；返回结构：未声明
- 404: Not found；返回结构：未声明

### GET /projects/{projectId}/approvals
- 概要: List approvals
- Path 参数:
- projectId (必填, string)
- Query 参数:
- status (可选, string)
- role (可选, string)
- document_id (可选, string)
- version_id (可选, string)
- current_only (可选, boolean)
- limit (可选, integer)
- offset (可选, integer)
- Header 参数:
- 无
- 请求体:
- 无
- 响应:
- 200: OK；返回结构：未声明

### GET /projects/{projectId}/audit-hash-chain
- 概要: Build audit hash chain
- Path 参数:
- projectId (必填, string)
- Query 参数:
- 无
- Header 参数:
- 无
- 请求体:
- 无
- 响应:
- 200: OK；返回结构：未声明

### GET /projects/{projectId}/audit-logs
- 概要: List audit logs
- Path 参数:
- projectId (必填, string)
- Query 参数:
- 无
- Header 参数:
- 无
- 请求体:
- 无
- 响应:
- 200: OK；返回结构：未声明

### POST /projects/{projectId}/audit-logs
- 概要: Append audit log
- Path 参数:
- projectId (必填, string)
- Query 参数:
- 无
- Header 参数:
- 无
- 请求体:
- 无
- 响应:
- 201: Created；返回结构：未声明
- 403: Forbidden；返回结构：未声明

### GET /projects/{projectId}/boq/deviation-summary
- 概要: Get BOQ deviation summary
- Path 参数:
- projectId (必填, string)
- Query 参数:
- 无
- Header 参数:
- 无
- 请求体:
- 无
- 响应:
- 200: OK；返回结构：未声明

### POST /projects/{projectId}/boq/execute-trip
- 概要: Execute BOQ trip action (measure.record / quality.check)
- Path 参数:
- projectId (必填, string)
- Query 参数:
- 无
- Header 参数:
- 无
- 请求体:
- 无
- 响应:
- 200: OK；返回结构：未声明
- 400: Bad request；返回结构：未声明

### POST /projects/{projectId}/boq/import
- 概要: Import BOQ rows and generate initial UTXOs
- Path 参数:
- projectId (必填, string)
- Query 参数:
- 无
- Header 参数:
- 无
- 请求体:
- 无
- 响应:
- 200: OK；返回结构：未声明
- 400: Bad request；返回结构：未声明

### GET /projects/{projectId}/boq/items
- 概要: List BOQ items
- Path 参数:
- projectId (必填, string)
- Query 参数:
- 无
- Header 参数:
- 无
- 请求体:
- 无
- 响应:
- 200: OK；返回结构：未声明

### GET /projects/{projectId}/boq/nodes
- 概要: List BOQ nodes
- Path 参数:
- projectId (必填, string)
- Query 参数:
- 无
- Header 参数:
- 无
- 请求体:
- 无
- 响应:
- 200: OK；返回结构：未声明

### GET /projects/{projectId}/boq/utxos
- 概要: List BOQ UTXOs
- Path 参数:
- projectId (必填, string)
- Query 参数:
- is_spent (可选, integer)
- code (可选, string)
- Header 参数:
- 无
- 请求体:
- 无
- 响应:
- 200: OK；返回结构：未声明

### GET /projects/{projectId}/boq/zero-ledger
- 概要: List zero-ledger entries
- Path 参数:
- projectId (必填, string)
- Query 参数:
- 无
- Header 参数:
- 无
- 请求体:
- 无
- 响应:
- 200: OK；返回结构：未声明

### GET /projects/{projectId}/calendar/ai-insights
- 概要: Calendar AI insights (model-first, rule fallback)
- Path 参数:
- projectId (必填, string)
- Query 参数:
- from (可选, string)
- to (可选, string)
- types (可选, string)
- status (可选, string)
- limit (可选, integer)
- Header 参数:
- 无
- 请求体:
- 无
- 响应:
- 200: OK；返回结构：未声明
- 404: Not found；返回结构：未声明

### GET /projects/{projectId}/calendar/events
- 概要: Project calendar event stream
- Path 参数:
- projectId (必填, string)
- Query 参数:
- from (可选, string)
- to (可选, string)
- types (可选, string)
- status (可选, string)
- limit (可选, integer)
- Header 参数:
- 无
- 请求体:
- 无
- 响应:
- 200: OK；返回结构：未声明
- 404: Not found；返回结构：未声明

### GET /projects/{projectId}/calendar/export.csv
- 概要: Export project calendar events as CSV
- Path 参数:
- projectId (必填, string)
- Query 参数:
- from (可选, string)
- to (可选, string)
- types (可选, string)
- status (可选, string)
- limit (可选, integer)
- Header 参数:
- 无
- 请求体:
- 无
- 响应:
- 200: OK；返回结构：未声明
- 404: Not found；返回结构：未声明

### GET /projects/{projectId}/components
- 概要: List component UTXO snapshots
- Path 参数:
- projectId (必填, string)
- Query 参数:
- entity_id (可选, string)
- kind (可选, string)
- status (可选, string)
- all_versions (可选, boolean)
- Header 参数:
- 无
- 请求体:
- 无
- 响应:
- 200: OK；返回结构：未声明

### POST /projects/{projectId}/components
- 概要: Create component UTXO root snapshot
- Path 参数:
- projectId (必填, string)
- Query 参数:
- 无
- Header 参数:
- 无
- 请求体:
- 无
- 响应:
- 201: Created；返回结构：未声明
- 400: Bad request；返回结构：未声明

### GET /projects/{projectId}/components/{componentId}
- 概要: Get current component UTXO snapshot
- Path 参数:
- projectId (必填, string)
- componentId (必填, string)
- Query 参数:
- 无
- Header 参数:
- 无
- 请求体:
- 无
- 响应:
- 200: OK；返回结构：未声明
- 404: Not found；返回结构：未声明

### GET /projects/{projectId}/components/{componentId}/allocations
- 概要: List BOQ allocation records for one component
- Path 参数:
- projectId (必填, string)
- componentId (必填, string)
- Query 参数:
- 无
- Header 参数:
- 无
- 请求体:
- 无
- 响应:
- 200: OK；返回结构：未声明
- 404: Not found；返回结构：未声明

### GET /projects/{projectId}/components/{componentId}/conservation
- 概要: Get component conservation validation result
- Path 参数:
- projectId (必填, string)
- componentId (必填, string)
- Query 参数:
- 无
- Header 参数:
- 无
- 请求体:
- 无
- 响应:
- 200: OK；返回结构：未声明
- 404: Not found；返回结构：未声明

### GET /projects/{projectId}/components/{componentId}/governance
- 概要: Get component BOM/BOQ governance result
- Path 参数:
- projectId (必填, string)
- componentId (必填, string)
- Query 参数:
- 无
- Header 参数:
- 无
- 请求体:
- 无
- 响应:
- 200: OK；返回结构：未声明
- 404: Not found；返回结构：未声明

### POST /projects/{projectId}/components/{componentId}/trips
- 概要: Execute one TripRole action on component and derive next snapshot
- Path 参数:
- projectId (必填, string)
- componentId (必填, string)
- Query 参数:
- 无
- Header 参数:
- 无
- 请求体:
- 无
- 响应:
- 200: OK；返回结构：未声明
- 404: Not found；返回结构：未声明

### GET /projects/{projectId}/documents
- 概要: List documents
- Path 参数:
- projectId (必填, string)
- Query 参数:
- status (可选, string)
- category (可选, string)
- search (可选, string)
- limit (可选, integer)
- offset (可选, integer)
- Header 参数:
- 无
- 请求体:
- 无
- 响应:
- 200: OK；返回结构：未声明

### POST /projects/{projectId}/documents
- 概要: Create document
- Path 参数:
- projectId (必填, string)
- Query 参数:
- 无
- Header 参数:
- x-idempotency-key (可选, string)
- 请求体:
- 无
- 响应:
- 201: Created；返回结构：未声明
- 403: Forbidden；返回结构：未声明
- 409: Conflict；返回结构：未声明

### DELETE /projects/{projectId}/documents/{documentId}
- 概要: Delete one draft document (no versions)
- Path 参数:
- projectId (必填, string)
- documentId (必填, string)
- Query 参数:
- 无
- Header 参数:
- 无
- 请求体:
- 无
- 响应:
- 200: Deleted；返回结构：未声明
- 403: Forbidden；返回结构：未声明
- 404: Not found；返回结构：未声明
- 409: Document has versions or is not draft；返回结构：未声明

### GET /projects/{projectId}/documents/{documentId}
- 概要: Get document summary
- Path 参数:
- projectId (必填, string)
- documentId (必填, string)
- Query 参数:
- 无
- Header 参数:
- 无
- 请求体:
- 无
- 响应:
- 200: OK；返回结构：未声明
- 404: Not found；返回结构：未声明

### PATCH /projects/{projectId}/documents/{documentId}
- 概要: Update document metadata/status
- Path 参数:
- projectId (必填, string)
- documentId (必填, string)
- Query 参数:
- 无
- Header 参数:
- 无
- 请求体:
- 无
- 响应:
- 200: OK；返回结构：未声明
- 403: Forbidden；返回结构：未声明
- 404: Not found；返回结构：未声明

### GET /projects/{projectId}/documents/{documentId}/detail
- 概要: Get document detail with current version and UTXO snapshot
- Path 参数:
- projectId (必填, string)
- documentId (必填, string)
- Query 参数:
- 无
- Header 参数:
- 无
- 请求体:
- 无
- 响应:
- 200: OK；返回结构：未声明
- 404: Not found；返回结构：未声明

### GET /projects/{projectId}/documents/{documentId}/utxo-tree
- 概要: Build document UTXO tree view
- Path 参数:
- projectId (必填, string)
- documentId (必填, string)
- Query 参数:
- 无
- Header 参数:
- 无
- 请求体:
- 无
- 响应:
- 200: OK；返回结构：未声明
- 404: Not found；返回结构：未声明

### GET /projects/{projectId}/documents/{documentId}/versions
- 概要: List versions
- Path 参数:
- projectId (必填, string)
- documentId (必填, string)
- Query 参数:
- status (可选, string)
- author (可选, string)
- proof_id (可选, string)
- limit (可选, integer)
- offset (可选, integer)
- Header 参数:
- 无
- 请求体:
- 无
- 响应:
- 200: OK；返回结构：未声明

### POST /projects/{projectId}/documents/{documentId}/versions
- 概要: Create version
- Path 参数:
- projectId (必填, string)
- documentId (必填, string)
- Query 参数:
- 无
- Header 参数:
- x-idempotency-key (可选, string)
- 请求体:
- 无
- 响应:
- 201: Created；返回结构：未声明
- 403: Forbidden；返回结构：未声明
- 409: Conflict；返回结构：未声明

### GET /projects/{projectId}/documents/{documentId}/versions/{versionId}
- 概要: Get version summary with proof/validation aggregates
- Path 参数:
- projectId (必填, string)
- documentId (必填, string)
- versionId (必填, string)
- Query 参数:
- 无
- Header 参数:
- 无
- 请求体:
- 无
- 响应:
- 200: OK；返回结构：未声明
- 404: Not found；返回结构：未声明

### PATCH /projects/{projectId}/documents/{documentId}/versions/{versionId}
- 概要: Update version status/metadata
- Path 参数:
- projectId (必填, string)
- documentId (必填, string)
- versionId (必填, string)
- Query 参数:
- 无
- Header 参数:
- 无
- 请求体:
- 无
- 响应:
- 200: OK；返回结构：未声明
- 403: Forbidden；返回结构：未声明
- 404: Not found；返回结构：未声明

### POST /projects/{projectId}/documents/{documentId}/versions/{versionId}/activate
- 概要: Activate one version as current effective
- Path 参数:
- projectId (必填, string)
- documentId (必填, string)
- versionId (必填, string)
- Query 参数:
- 无
- Header 参数:
- 无
- 请求体:
- 无
- 响应:
- 200: OK；返回结构：未声明
- 403: Forbidden；返回结构：未声明
- 404: Not found；返回结构：未声明

### GET /projects/{projectId}/documents/{documentId}/versions/{versionId}/evidence-package
- 概要: Get version evidence package aggregate
- Path 参数:
- projectId (必填, string)
- documentId (必填, string)
- versionId (必填, string)
- Query 参数:
- 无
- Header 参数:
- 无
- 请求体:
- 无
- 响应:
- 200: OK；返回结构：未声明
- 404: Not found；返回结构：未声明

### GET /projects/{projectId}/entities
- 概要: List engineering entities
- Path 参数:
- projectId (必填, string)
- Query 参数:
- status (可选, string)
- entity_type (可选, string)
- search (可选, string)
- Header 参数:
- 无
- 请求体:
- 无
- 响应:
- 200: OK；返回结构：未声明

### POST /projects/{projectId}/entities
- 概要: Create engineering entity
- Path 参数:
- projectId (必填, string)
- Query 参数:
- 无
- Header 参数:
- 无
- 请求体:
- 无
- 响应:
- 201: Created；返回结构：未声明
- 400: Bad request；返回结构：未声明

### DELETE /projects/{projectId}/entities/{entityId}
- 概要: Delete engineering entity
- Path 参数:
- projectId (必填, string)
- entityId (必填, string)
- Query 参数:
- force (可选, boolean)
- Header 参数:
- 无
- 请求体:
- 无
- 响应:
- 200: OK；返回结构：未声明
- 404: Not found；返回结构：未声明
- 409: Conflict；返回结构：未声明

### PATCH /projects/{projectId}/entities/{entityId}
- 概要: Update engineering entity
- Path 参数:
- projectId (必填, string)
- entityId (必填, string)
- Query 参数:
- 无
- Header 参数:
- 无
- 请求体:
- 无
- 响应:
- 200: OK；返回结构：未声明
- 404: Not found；返回结构：未声明

### GET /projects/{projectId}/entities/{entityId}/components
- 概要: List components under one engineering entity
- Path 参数:
- projectId (必填, string)
- entityId (必填, string)
- Query 参数:
- all_versions (可选, boolean)
- Header 参数:
- 无
- 请求体:
- 无
- 响应:
- 200: OK；返回结构：未声明
- 404: Not found；返回结构：未声明

### GET /projects/{projectId}/evidence-summary
- 概要: Project evidence summary
- Path 参数:
- projectId (必填, string)
- Query 参数:
- 无
- Header 参数:
- 无
- 请求体:
- 无
- 响应:
- 200: OK；返回结构：未声明
- 404: Not found；返回结构：未声明

### POST /projects/{projectId}/final-proof
- 概要: Generate project-level final proof from current component snapshots
- Path 参数:
- projectId (必填, string)
- Query 参数:
- 无
- Header 参数:
- 无
- 请求体:
- 无
- 响应:
- 200: OK；返回结构：未声明
- 404: Not found；返回结构：未声明

### GET /projects/{projectId}/final-proof/precheck
- 概要: Get final-proof precheck status from current snapshots
- Path 参数:
- projectId (必填, string)
- Query 参数:
- 无
- Header 参数:
- 无
- 请求体:
- 无
- 响应:
- 200: OK；返回结构：未声明
- 404: Not found；返回结构：未声明

### GET /projects/{projectId}/final-proof/summary
- 概要: Final proof risk snapshot and aggregates
- Path 参数:
- projectId (必填, string)
- Query 参数:
- 无
- Header 参数:
- 无
- 请求体:
- 无
- 响应:
- 200: OK；返回结构：未声明
- 404: Not found；返回结构：未声明

### GET /projects/{projectId}/members
- 概要: List project members
- Path 参数:
- projectId (必填, string)
- Query 参数:
- 无
- Header 参数:
- 无
- 请求体:
- 无
- 响应:
- 200: OK；返回结构：未声明

### POST /projects/{projectId}/members
- 概要: Upsert project member
- Path 参数:
- projectId (必填, string)
- Query 参数:
- 无
- Header 参数:
- 无
- 请求体:
- 无
- 响应:
- 200: OK；返回结构：未声明
- 403: Forbidden；返回结构：未声明

### DELETE /projects/{projectId}/members/{memberId}
- 概要: Delete project member
- Path 参数:
- projectId (必填, string)
- memberId (必填, string)
- Query 参数:
- 无
- Header 参数:
- 无
- 请求体:
- 无
- 响应:
- 200: OK；返回结构：未声明
- 403: Forbidden；返回结构：未声明
- 404: Not found；返回结构：未声明

### PATCH /projects/{projectId}/members/{memberId}
- 概要: Update project member
- Path 参数:
- projectId (必填, string)
- memberId (必填, string)
- Query 参数:
- 无
- Header 参数:
- 无
- 请求体:
- 无
- 响应:
- 200: OK；返回结构：未声明
- 400: Bad request；返回结构：未声明
- 403: Forbidden；返回结构：未声明
- 404: Not found；返回结构：未声明

### GET /projects/{projectId}/milestones
- 概要: List project milestones
- Path 参数:
- projectId (必填, string)
- Query 参数:
- status (可选, string)
- limit (可选, integer)
- Header 参数:
- 无
- 请求体:
- 无
- 响应:
- 200: OK；返回结构：未声明
- 404: Not found；返回结构：未声明

### POST /projects/{projectId}/milestones
- 概要: Create project milestone
- Path 参数:
- projectId (必填, string)
- Query 参数:
- 无
- Header 参数:
- 无
- 请求体:
- 无
- 响应:
- 201: Created；返回结构：未声明
- 403: Forbidden；返回结构：未声明
- 404: Not found；返回结构：未声明

### DELETE /projects/{projectId}/milestones/{milestoneId}
- 概要: Delete project milestone
- Path 参数:
- projectId (必填, string)
- milestoneId (必填, string)
- Query 参数:
- 无
- Header 参数:
- 无
- 请求体:
- 无
- 响应:
- 200: OK；返回结构：未声明
- 403: Forbidden；返回结构：未声明
- 404: Not found；返回结构：未声明

### PATCH /projects/{projectId}/milestones/{milestoneId}
- 概要: Update project milestone
- Path 参数:
- projectId (必填, string)
- milestoneId (必填, string)
- Query 参数:
- 无
- Header 参数:
- 无
- 请求体:
- 无
- 响应:
- 200: OK；返回结构：未声明
- 403: Forbidden；返回结构：未声明
- 404: Not found；返回结构：未声明

### GET /projects/{projectId}/normref/families
- 概要: List bridge NormRef families
- Path 参数:
- projectId (必填, string)
- Query 参数:
- 无
- Header 参数:
- 无
- 请求体:
- 无
- 响应:
- 200: OK；返回结构：未声明
- 404: Not found；返回结构：未声明

### GET /projects/{projectId}/normref/forms
- 概要: List bridge NormRef form catalog
- Path 参数:
- projectId (必填, string)
- Query 参数:
- family_code (可选, string)
- q (可选, string)
- Header 参数:
- 无
- 请求体:
- 无
- 响应:
- 200: OK；返回结构：未声明
- 404: Not found；返回结构：未声明

### GET /projects/{projectId}/normref/forms/{formCode}
- 概要: Get one bridge NormRef form template and protocol stub
- Path 参数:
- projectId (必填, string)
- formCode (必填, string)
- Query 参数:
- 无
- Header 参数:
- 无
- 请求体:
- 无
- 响应:
- 200: OK；返回结构：未声明
- 404: Not found；返回结构：未声明

### POST /projects/{projectId}/normref/forms/{formCode}/draft-instances
- 概要: Save one NormRef draft instance from preview payload
- Path 参数:
- projectId (必填, string)
- formCode (必填, string)
- Query 参数:
- 无
- Header 参数:
- 无
- 请求体:
- 无
- 响应:
- 200: OK；返回结构：未声明
- 400: Bad request；返回结构：未声明
- 404: Not found；返回结构：未声明

### GET /projects/{projectId}/normref/forms/{formCode}/draft-instances/latest
- 概要: Get latest NormRef draft instance
- Path 参数:
- projectId (必填, string)
- formCode (必填, string)
- Query 参数:
- 无
- Header 参数:
- 无
- 请求体:
- 无
- 响应:
- 200: OK；返回结构：未声明
- 400: Bad request；返回结构：未声明
- 404: Not found；返回结构：未声明

### POST /projects/{projectId}/normref/forms/{formCode}/draft-instances/{instanceId}/submit
- 概要: Submit one NormRef draft instance
- Path 参数:
- projectId (必填, string)
- formCode (必填, string)
- instanceId (必填, string)
- Query 参数:
- 无
- Header 参数:
- 无
- 请求体:
- 无
- 响应:
- 200: OK；返回结构：未声明
- 400: Bad request；返回结构：未声明
- 404: Not found；返回结构：未声明
- 409: Invalid status transition；返回结构：未声明

### POST /projects/{projectId}/normref/forms/{formCode}/interpret-preview
- 概要: Interpret NormRef form input and return five-layer preview
- Path 参数:
- projectId (必填, string)
- formCode (必填, string)
- Query 参数:
- 无
- Header 参数:
- 无
- 请求体:
- 无
- 响应:
- 200: OK；返回结构：未声明
- 400: Bad request；返回结构：未声明
- 404: Not found；返回结构：未声明

### GET /projects/{projectId}/normref/forms/{formCode}/latest-submitted
- 概要: Get latest submitted NormRef instance
- Path 参数:
- projectId (必填, string)
- formCode (必填, string)
- Query 参数:
- 无
- Header 参数:
- 无
- 请求体:
- 无
- 响应:
- 200: OK；返回结构：未声明
- 400: Bad request；返回结构：未声明
- 404: Not found；返回结构：未声明

### GET /projects/{projectId}/normref/instances
- 概要: List bridge NormRef instances
- Path 参数:
- projectId (必填, string)
- Query 参数:
- form_code (可选, string)
- status (可选, string)
- Header 参数:
- 无
- 请求体:
- 无
- 响应:
- 200: OK；返回结构：未声明
- 404: Not found；返回结构：未声明

### POST /projects/{projectId}/pipeline/run
- 概要: Run unified DocPeg pipeline (component create/trip/check/final-proof)
- Path 参数:
- projectId (必填, string)
- Query 参数:
- 无
- Header 参数:
- 无
- 请求体:
- 无
- 响应:
- 200: OK；返回结构：未声明
- 400: Bad request；返回结构：未声明
- 404: Not found；返回结构：未声明

### GET /projects/{projectId}/quality-gate-executions
- 概要: List quality gate executions
- Path 参数:
- projectId (必填, string)
- Query 参数:
- subitem_code (可选, string)
- Header 参数:
- 无
- 请求体:
- 无
- 响应:
- 200: OK；返回结构：未声明

### GET /projects/{projectId}/quality-gates
- 概要: List quality gates
- Path 参数:
- projectId (必填, string)
- Query 参数:
- subitem_code (可选, string)
- Header 参数:
- 无
- 请求体:
- 无
- 响应:
- 200: OK；返回结构：未声明

### POST /projects/{projectId}/quality-gates
- 概要: Upsert quality gate
- Path 参数:
- projectId (必填, string)
- Query 参数:
- 无
- Header 参数:
- 无
- 请求体:
- 无
- 响应:
- 200: OK；返回结构：未声明
- 400: Bad request；返回结构：未声明

### POST /projects/{projectId}/quality-gates/{gateId}/execute
- 概要: Execute one quality gate
- Path 参数:
- projectId (必填, string)
- gateId (必填, string)
- Query 参数:
- 无
- Header 参数:
- 无
- 请求体:
- 无
- 响应:
- 200: OK；返回结构：未声明
- 400: Bad request；返回结构：未声明
- 404: Not found；返回结构：未声明

### POST /projects/{projectId}/quality-gates/{gateId}/execute-with-trip
- 概要: Execute one quality gate and atomically create completed trip with proof
- Path 参数:
- projectId (必填, string)
- gateId (必填, string)
- Query 参数:
- 无
- Header 参数:
- 无
- 请求体:
- 无
- 响应:
- 200: OK；返回结构：未声明
- 400: Bad request；返回结构：未声明
- 404: Not found；返回结构：未声明

### GET /projects/{projectId}/state-events
- 概要: Project state-event ledger snapshot
- Path 参数:
- projectId (必填, string)
- Query 参数:
- 无
- Header 参数:
- 无
- 请求体:
- 无
- 响应:
- 200: OK；返回结构：未声明
- 404: Not found；返回结构：未声明

### GET /projects/{projectId}/utxo-conflicts
- 概要: List project UTXO conflicts
- Path 参数:
- projectId (必填, string)
- Query 参数:
- 无
- Header 参数:
- 无
- 请求体:
- 无
- 响应:
- 200: OK；返回结构：未声明
- 404: Not found；返回结构：未声明

### GET /projects/{projectId}/utxo-tree
- 概要: Build project document-level UTXO tree view
- Path 参数:
- projectId (必填, string)
- Query 参数:
- 无
- Header 参数:
- 无
- 请求体:
- 无
- 响应:
- 200: OK；返回结构：未声明
- 404: Not found；返回结构：未声明

### GET /projects/{projectId}/utxos
- 概要: List project UTXOs (optionally filtered by document/version/status)
- Path 参数:
- projectId (必填, string)
- Query 参数:
- document_id (可选, string)
- version_id (可选, string)
- status (可选, string)
- is_spent (可选, integer)
- Header 参数:
- 无
- 请求体:
- 无
- 响应:
- 200: OK；返回结构：未声明
- 404: Not found；返回结构：未声明

### POST /projects/{projectId}/utxos/{utxoId}/resolve-conflict
- 概要: Resolve one UTXO conflict
- Path 参数:
- projectId (必填, string)
- utxoId (必填, string)
- Query 参数:
- 无
- Header 参数:
- 无
- 请求体:
- 无
- 响应:
- 200: OK；返回结构：未声明
- 400: Bad request；返回结构：未声明
- 404: Not found；返回结构：未声明

### DELETE /repo/snapshot
- 概要: Delete repository snapshot
- Path 参数:
- 无
- Query 参数:
- 无
- Header 参数:
- 无
- 请求体:
- 无
- 响应:
- 200: OK；返回结构：未声明

### GET /repo/snapshot
- 概要: Get repository snapshot
- Path 参数:
- 无
- Query 参数:
- 无
- Header 参数:
- 无
- 请求体:
- 无
- 响应:
- 200: OK；返回结构：未声明

### PUT /repo/snapshot
- 概要: Save repository snapshot
- Path 参数:
- 无
- Query 参数:
- 无
- Header 参数:
- 无
- 请求体:
- 无
- 响应:
- 200: OK；返回结构：未声明

### GET /spec-dicts
- 概要: List quality spec dictionaries
- Path 参数:
- 无
- Query 参数:
- 无
- Header 参数:
- 无
- 请求体:
- 无
- 响应:
- 200: OK；返回结构：未声明

### POST /upload
- 概要: Upload file to R2 and write metadata to D1
- Path 参数:
- 无
- Query 参数:
- 无
- Header 参数:
- x-upload-token (可选, string)
- x-upload-session-token (可选, string)
- 请求体:
- 无
- 响应:
- 200: OK；返回结构：未声明
- 401: Unauthorized；返回结构：未声明
- 403: Forbidden；返回结构：未声明

### GET /uploads/sessions
- 概要: List upload sessions
- Path 参数:
- 无
- Query 参数:
- 无
- Header 参数:
- 无
- 请求体:
- 无
- 响应:
- 200: OK；返回结构：未声明

### POST /uploads/sessions
- 概要: Create one-time upload session token
- Path 参数:
- 无
- Query 参数:
- 无
- Header 参数:
- 无
- 请求体:
- 无
- 响应:
- 200: OK；返回结构：未声明
- 403: Forbidden；返回结构：未声明

### DELETE /uploads/sessions/{sessionId}
- 概要: Revoke upload session
- Path 参数:
- sessionId (必填, string)
- Query 参数:
- 无
- Header 参数:
- 无
- 请求体:
- 无
- 响应:
- 200: OK；返回结构：未声明
- 403: Forbidden；返回结构：未声明
- 404: Not found；返回结构：未声明

### GET /uploads/sessions/{sessionId}
- 概要: Get upload session
- Path 参数:
- sessionId (必填, string)
- Query 参数:
- 无
- Header 参数:
- 无
- 请求体:
- 无
- 响应:
- 200: OK；返回结构：未声明
- 404: Not found；返回结构：未声明

### GET /verify/final/{finalProofId}
- 概要: Public verify endpoint for project-level final proof
- Path 参数:
- finalProofId (必填, string)
- Query 参数:
- 无
- Header 参数:
- 无
- 请求体:
- 无
- 响应:
- 200: OK；返回结构：未声明
- 404: Not found；返回结构：未声明

### GET /verify/proof/{proofId}
- 概要: Public verify endpoint
- Path 参数:
- proofId (必填, string)
- Query 参数:
- 无
- Header 参数:
- 无
- 请求体:
- 无
- 响应:
- 200: OK；返回结构：未声明
- 404: Not found；返回结构：未声明

## /api/v1 兼容域接口（当前后端已开放，部分未写入 openapi）

### GET /api/v1/docpeg/summary
- Query 参数: 无
- 返回结构（示例）: `{ ok:boolean, domain:"docpeg", summary:{ projects:number, documents:number, versions:number, trips:number, proofs:number } }`

### GET /api/v1/dtorole/role-bindings
- Query 参数: `project_id?`
- 返回结构: 与 `/admin/role-bindings` 一致

### POST /api/v1/dtorole/role-bindings
- 请求体: 与 `/admin/role-bindings` upsert 一致
- 返回结构: upsert 结果

### DELETE /api/v1/dtorole/role-bindings/{bindingId}
- Path 参数: `bindingId`
- 返回结构: 删除结果

### GET /api/v1/dtorole/permission-check
- Query 参数: `permission`(必填), `project_id?`, `actor_role?`, `actor_name?`
- 返回结构: 权限评估结果（allow/deny + reason）

### GET /api/v1/triprole/trips
- Query 参数: `project_id?`, `component_uri?`, `pile_id?`, `limit?`, `offset?`
- 返回结构: trip 列表（与 `/api/trips` 兼容）

### POST /api/v1/triprole/trips
- 请求体: trip 创建参数（与 `/api/trips` 一致）
- 返回结构: trip 创建结果

### POST /api/v1/triprole/preview
- 请求体: Trip 提交预演参数
- 返回结构: `{ ok, guard, projection }`

### POST /api/v1/triprole/submit
- 请求体: Trip 提交参数
- 返回结构: `{ ok, result }`

### GET /api/v1/layerpeg/chain-status
- Query 参数: `project_id?`
- 返回结构（示例）: `{ ok, mode, reason, checks }`

### POST /api/v1/layerpeg/anchor
- 请求体: `{ project_id:string, entity_uri:string, hash:string, payload?:object }`
- 返回结构: `{ ok, anchor_id, hash, created_at }`

### GET /api/v1/layerpeg/anchor
- Query 参数: `project_id`(必填), `entity_uri`(必填)
- 返回结构: `{ ok, items:[{ id, project_id, entity_uri, hash, payload, created_by, created_at }] }`

### NormRef /api/v1 路径
- GET `/api/v1/normref/projects/{projectId}/forms`
- GET `/api/v1/normref/projects/{projectId}/forms/{formCode}`
- POST `/api/v1/normref/projects/{projectId}/forms/{formCode}/interpret-preview`
- POST `/api/v1/normref/projects/{projectId}/forms/{formCode}/draft-instances`
- GET `/api/v1/normref/projects/{projectId}/forms/{formCode}/draft-instances/latest`
- POST `/api/v1/normref/projects/{projectId}/forms/{formCode}/draft-instances/{instanceId}/submit`
- GET `/api/v1/normref/projects/{projectId}/forms/{formCode}/latest-submitted`
- 参数与返回结构: 与 `/projects/{projectId}/normref/...` 同口径

### BOQItem /api/v1 路径
- GET `/api/v1/boqitem/projects/{projectId}/nodes`
- GET `/api/v1/boqitem/projects/{projectId}/items`
- GET `/api/v1/boqitem/projects/{projectId}/utxos`
- 参数与返回结构: 与 `/projects/{projectId}/boq/nodes|items|utxos` 同口径

## 目标口径 P0/P1 复核
- 已在上一个版本复核：部分为“目标接口”，当前需使用替代口径（如 `/api/proofs/{proofId}`, `/upload`, `/api/trips/{tripId}` 等）。
## 核心业务接口（已补充明确字段结构，给 QCSpec 直接联调）

### 1) 工程树与实体

#### GET /projects/{projectId}/entities
- Path 参数:
  - `projectId`(必填,string)
- Query 参数:
  - `status?` `entity_type?` `search?`
- 返回结构（示例）:
```json
{
  "ok": true,
  "items": [
    {
      "id": "ENT-...",
      "project_id": "PJT-D34A70B8",
      "entity_uri": "v://cn.docpeg/project/PJT-D34A70B8/entity/桥-400-1-1",
      "entity_code": "桥-400-1-1",
      "entity_name": "钻孔灌注桩",
      "entity_type": "subitem",
      "parent_id": "ENT-...",
      "status": "active",
      "created_at": "2026-04-10 06:12:51",
      "updated_at": "2026-04-10 06:12:51"
    }
  ]
}
```

## DTO Role Canonical Permission Model (Proof Lifecycle, 2026-04-10)

This section is the recommended integration contract for QCSPEC frontend/backend when using `/api/v1/dtorole/*`.

### 1) Canonical definition

- `Exec`: execution subject (person/team/device), e.g. `EXEC-ZHANG-SAN-001`.
- `DTO Role`: permission set on Proof lifecycle for an Exec in one project scope.
- `TripRole`: concrete executable action in process chain, e.g. `trip.execute`.

DTO Role is not only a generic user role. It is the explicit permission layer that controls who can create/fill/review/approve/reject/view Proof, and whether a caller can execute a TripRole.

### 2) Core relation

- One `Exec` can have multiple `DTO Role` bindings in a project.
- One `TripRole` execution must pass a DTO Role permission check.
- Every Proof mutation should be auditable with actor and role context.

Recommended chain: `Exec -> DTO Role binding -> permission-check -> TripRole execution -> Proof write`.

### 3) Recommended permission vocabulary

- `proof.create.<proof_type>`
- `proof.fill.<proof_type>` or `proof.fill.<field_group>`
- `proof.approve.<proof_type>`
- `proof.reject.<proof_type>`
- `proof.view.<proof_type>`
- `trip.execute` (current frontend usage)
- `trip.execute.<trip_role>` (recommended next step for finer granularity)

### 4) DTO Role object (recommended stable schema)

```json
{
  "dtorole_id": "DTOROLE-ZHANG-SAN-001",
  "exec_id": "EXEC-ZHANG-SAN-001",
  "project_id": "PJT-D34A70B8",
  "permissions": {
    "create_proof": ["lab_report", "construction_record"],
    "fill_proof": ["temperature", "slump_mm", "actual_volume"],
    "approve_proof": ["iqc_report", "pqc_report"],
    "reject_proof": ["all"],
    "view_proof": ["all"],
    "trip_execute": ["trip.execute", "trip.execute.pile.concrete"]
  },
  "constraints": {
    "max_concurrent_approvals": 5,
    "require_second_approval_for": ["fqc_report"]
  },
  "valid_until": "2026-12-31",
  "updated_at": "2026-04-10T09:00:00Z"
}
```

### 5) Permission-check decision rule

Input: `project_id`, `permission`, optional `actor_role`, optional `actor_name`.

Decision:
1. Resolve actor context from query or request headers/session.
2. Load active role bindings in `project_id`.
3. Merge all granted permissions for matched bindings.
4. Evaluate permission and constraints.
5. Return `allowed` and machine-readable `reason`.

Recommended deny reasons:
- `binding_not_found`
- `permission_not_granted`
- `constraint_exceeded`
- `role_expired`

### 6) `/api/v1/dtorole/*` integration contract

#### GET /api/v1/dtorole/role-bindings

- Query: `project_id?`, `exec_id?`, `actor_name?`
- Recommended response:

```json
{
  "ok": true,
  "items": [
    {
      "binding_id": "RB-001",
      "project_id": "PJT-D34A70B8",
      "exec_id": "EXEC-ZHANG-SAN-001",
      "actor_name": "zhangsan",
      "actor_role": "quality_inspector",
      "dtorole_id": "DTOROLE-ZHANG-SAN-001",
      "permissions": {
        "trip_execute": ["trip.execute"]
      },
      "valid_until": "2026-12-31"
    }
  ],
  "total": 1
}
```

#### POST /api/v1/dtorole/role-bindings

- Request:

```json
{
  "project_id": "PJT-D34A70B8",
  "exec_id": "EXEC-ZHANG-SAN-001",
  "actor_name": "zhangsan",
  "actor_role": "quality_inspector",
  "dtorole_id": "DTOROLE-ZHANG-SAN-001",
  "permissions": {
    "trip_execute": ["trip.execute"],
    "approve_proof": ["iqc_report"]
  },
  "valid_until": "2026-12-31"
}
```

- Response:

```json
{
  "ok": true,
  "upserted": true,
  "binding_id": "RB-001"
}
```

#### GET /api/v1/dtorole/permission-check

- Query: `permission` (required), `project_id?`, `actor_role?`, `actor_name?`
- Recommended response:

```json
{
  "ok": true,
  "allowed": true,
  "reason": "granted_by_binding",
  "permission": "trip.execute",
  "matched_binding_ids": ["RB-001"],
  "trace_id": "perm-20260410-001"
}
```

Denied example:

```json
{
  "ok": true,
  "allowed": false,
  "reason": "permission_not_granted",
  "permission": "trip.execute.pile.concrete",
  "matched_binding_ids": ["RB-001"],
  "trace_id": "perm-20260410-002"
}
```

### 7) Frontend integration guideline

- Before `triprole/preview` and `triprole/submit`, always call `dtorole/permission-check`.
- Continue using current `permission=trip.execute` first; then extend to `trip.execute.<trip_role>` per action.
- On deny:
  - disable submit button;
  - show reason text from API;
  - keep `trace_id` visible/copyable for troubleshooting.
- On allow:
  - continue preview/submit flow;
  - store `permission`, `reason`, `trace_id` in operation log.
- For write APIs, send `x-actor-role` and `x-actor-name` consistently.

### 8) UI display recommendation (Role & Permission)

- Role card: show `actor_name`, `actor_role`, `dtorole_id`, `valid_until`.
- Permission matrix:
  - rows: proof/trip actions;
  - columns: create, fill, approve, reject, view, execute;
  - cell states: allow/deny/inherited/expired.
- Action area:
  - if deny, button disabled and inline reason;
  - if allow, show a small "authorized" status line with last `trace_id`.

This keeps DTO Role visible, explainable, and auditable during Proof and Trip workflows.

### 9) Common DTO Role templates

The templates below are baseline presets. You can narrow permissions by `project_id`, `component_uri`, `trip_role`, and validity constraints.

#### Template A: quality_inspector (质检员)

```json
{
  "dtorole_code": "quality_inspector",
  "permissions": {
    "create_proof": ["iqc_report", "pqc_report", "lab_report"],
    "fill_proof": ["test_value", "sampling_info", "attachment", "remark"],
    "approve_proof": [],
    "reject_proof": [],
    "view_proof": ["all"],
    "trip_execute": ["trip.execute.quality.sample", "trip.execute.quality.submit"]
  },
  "constraints": {
    "can_approve_own_proof": false,
    "require_attachment_for_submit": true
  }
}
```

#### Template B: site_operator (施工员)

```json
{
  "dtorole_code": "site_operator",
  "permissions": {
    "create_proof": ["construction_record", "material_receipt", "daily_log"],
    "fill_proof": ["actual_volume", "location", "crew", "equipment"],
    "approve_proof": [],
    "reject_proof": [],
    "view_proof": ["construction_record", "daily_log", "iqc_report", "pqc_report"],
    "trip_execute": ["trip.execute.construction.start", "trip.execute.construction.finish"]
  },
  "constraints": {
    "can_approve_own_proof": false,
    "cross_section_write": false
  }
}
```

#### Template C: supervisor (监理)

```json
{
  "dtorole_code": "supervisor",
  "permissions": {
    "create_proof": ["supervision_note", "inspection_order"],
    "fill_proof": ["issue", "rectification_deadline", "review_comment"],
    "approve_proof": ["iqc_report", "pqc_report", "construction_record"],
    "reject_proof": ["iqc_report", "pqc_report", "construction_record"],
    "view_proof": ["all"],
    "trip_execute": ["trip.execute.supervision.approve", "trip.execute.supervision.reject"]
  },
  "constraints": {
    "max_concurrent_approvals": 20,
    "can_approve_own_proof": false
  }
}
```

#### Template D: project_manager (项目经理)

```json
{
  "dtorole_code": "project_manager",
  "permissions": {
    "create_proof": ["management_instruction", "final_acceptance_note"],
    "fill_proof": ["risk_comment", "milestone_comment", "decision"],
    "approve_proof": ["all"],
    "reject_proof": ["all"],
    "view_proof": ["all"],
    "trip_execute": ["trip.execute.project.milestone_approve", "trip.execute.project.close"]
  },
  "constraints": {
    "require_second_approval_for": ["fqc_report", "final_acceptance_note"],
    "max_concurrent_approvals": 100
  }
}
```

#### Template E: lab_technician (试验员, optional)

```json
{
  "dtorole_code": "lab_technician",
  "permissions": {
    "create_proof": ["lab_report"],
    "fill_proof": ["temperature", "strength", "sample_id", "mix_ratio"],
    "approve_proof": [],
    "reject_proof": [],
    "view_proof": ["lab_report", "iqc_report", "pqc_report"],
    "trip_execute": ["trip.execute.lab.test", "trip.execute.lab.upload"]
  },
  "constraints": {
    "can_approve_own_proof": false
  }
}
```

#### Template F: data_clerk (资料员, optional)

```json
{
  "dtorole_code": "data_clerk",
  "permissions": {
    "create_proof": ["document_index", "archive_record"],
    "fill_proof": ["metadata", "file_tag", "archive_location"],
    "approve_proof": [],
    "reject_proof": [],
    "view_proof": ["all"],
    "trip_execute": ["trip.execute.docs.archive", "trip.execute.docs.sync"]
  },
  "constraints": {
    "proof_content_editable": false
  }
}
```

#### Suggested rollout order

1. Start with `quality_inspector`, `site_operator`, `supervisor`, `project_manager`.
2. Bind each template to real `exec_id` by project.
3. Verify with `/api/v1/dtorole/permission-check` before each Trip submit.
4. Add `lab_technician` and `data_clerk` only when related Proof workflows are enabled.

#### GET /projects/{projectId}/entities/{entityId}/components
- Path 参数: `projectId`,`entityId`
- 返回结构（示例）:
```json
{
  "ok": true,
  "items": [
    {
      "id": "COMP-...",
      "component_uri": "v://cn.docpeg/DJGS/pile/桥-400-1-1",
      "pile_id": "桥-400-1-1",
      "status": "current",
      "proof_id": null,
      "trip_id": null,
      "updated_at": "2026-04-10 06:12:51"
    }
  ]
}
```

### 2) 分项绑定与工序链

#### POST /projects/{projectId}/process-chains/bindings
- 请求体:
```json
{
  "entity_uri": "v://.../entity/桥-400-1-1",
  "entity_code": "桥-400-1-1",
  "entity_name": "钻孔灌注桩",
  "chain_id": "drilled-pile",
  "component_uri": "v://cn.docpeg/DJGS/pile/桥-400-1-1",
  "pile_id": "桥-400-1-1",
  "inspection_location": "桥 400 1 1",
  "source_mode": "hybrid"
}
```
- 返回结构:
```json
{
  "ok": true,
  "binding": {
    "id": "PCB-...",
    "project_id": "PJT-D34A70B8",
    "entity_uri": "v://...",
    "chain_id": "drilled-pile",
    "component_uri": "v://...",
    "pile_id": "桥-400-1-1",
    "inspection_location": "桥 400 1 1",
    "is_active": 1,
    "updated_at": "2026-04-10 06:12:51"
  }
}
```

#### GET /projects/{projectId}/process-chains/bindings
- Query: `chain_id?`, `chain_state?`, `q?`
- 返回结构:
```json
{
  "ok": true,
  "total": 1,
  "items": [
    {
      "id": "PCB-...",
      "entity_code": "桥-400-1-1",
      "entity_name": "钻孔灌注桩",
      "entity_uri": "v://...",
      "chain_id": "drilled-pile",
      "component_uri": "v://...",
      "pile_id": "桥-400-1-1",
      "chain_state": "process_complete",
      "current_step_name": "护筒埋设",
      "complete": false,
      "acceptance": "pending",
      "latest_instance_at": "2026-04-10 06:12:51"
    }
  ]
}
```

#### GET /projects/{projectId}/process-chains/status
- Query: `chain_id`(必填), `component_uri?`, `pile_id?`, `source_mode?`
- 返回结构:
```json
{
  "ok": true,
  "chain_id": "drilled-pile",
  "chain_name": "钻孔灌注桩工序链",
  "chain_state": "processing",
  "component_uri": "v://...",
  "pile_id": "桥-400-1-1",
  "current_step": "bridge11",
  "current_step_name": "钢筋安装",
  "complete": false,
  "steps": [
    {
      "step_id": "bridge2",
      "name": "护筒埋设",
      "table": "桥施2表",
      "status": "done",
      "latest_instance": {
        "instance_id": "NINST-...",
        "status": "submitted",
        "updated_at": "2026-04-10 06:12:51",
        "created_by": "designer-user"
      }
    }
  ]
}
```

### 3) NormRef（/api/v1）

#### GET /api/v1/normref/projects/{projectId}/forms
- 返回:
```json
{ "ok": true, "items": [ { "form_code": "桥施2表", "form_name": "...", "family_code": "bridge" } ] }
```

#### GET /api/v1/normref/projects/{projectId}/forms/{formCode}
- 返回:
```json
{
  "ok": true,
  "item": {
    "form_code": "桥施2表",
    "form_name": "...",
    "fields": [ { "field_key": "inspection_location", "field_type": "text", "required": true } ],
    "protocol_stub": {},
    "mapping_config": {}
  }
}
```

#### POST /api/v1/normref/projects/{projectId}/forms/{formCode}/interpret-preview
- 请求体:
```json
{ "input": { "inspection_location": "桥 400 1 1", "inspection_date": "2026-04-10", "result": "合格" } }
```
- 返回:
```json
{ "ok": true, "project_id": "PJT-D34A70B8", "form_code": "桥施2表", "raw": {}, "normalized": {}, "derived": {}, "validation": {}, "five_layer": {} }
```

#### POST /api/v1/normref/projects/{projectId}/forms/{formCode}/draft-instances
- 请求体:
```json
{ "input": { "...": "..." }, "preview": { "...": "..." } }
```
- 返回:
```json
{ "ok": true, "instance_id": "NINST-...", "status": "draft" }
```

#### GET /api/v1/normref/projects/{projectId}/forms/{formCode}/draft-instances/latest
- 返回:
```json
{ "ok": true, "instance_id": "NINST-...", "status": "draft", "input_json": {}, "preview_json": {} }
```

#### POST /api/v1/normref/projects/{projectId}/forms/{formCode}/draft-instances/{instanceId}/submit
- 返回:
```json
{ "ok": true, "instance_id": "NINST-...", "status": "submitted" }
```

#### GET /api/v1/normref/projects/{projectId}/forms/{formCode}/latest-submitted
- 返回:
```json
{ "ok": true, "instance_id": "NINST-...", "status": "submitted", "input_json": {}, "preview_json": {} }
```

### 4) TripRole（/api/v1）

#### GET /api/v1/triprole/trips
- Query: `project_id?`, `component_uri?`, `pile_id?`, `limit?`, `offset?`
- 返回:
```json
{ "ok": true, "items": [ { "trip_id": "TRIP-...", "project_id": "...", "action": "...", "status": "...", "created_at": "..." } ], "total": 1 }
```

#### POST /api/v1/triprole/trips
- 请求体: Trip 创建参数
- 返回:
```json
{ "ok": true, "trip": { "trip_id": "TRIP-...", "status": "pending" } }
```

#### POST /api/v1/triprole/preview
- 返回:
```json
{ "ok": true, "guard": {}, "projection": {} }
```

#### POST /api/v1/triprole/submit
- 返回:
```json
{ "ok": true, "result": { "trip_id": "TRIP-...", "status": "submitted", "proof_id": "PROOF-..." } }
```

### 5) LayerPeg（/api/v1）

#### GET /api/v1/layerpeg/chain-status
- Query: `project_id?`
- 返回:
```json
{ "ok": true, "mode": "ready", "reason": "all_checks_passed", "checks": { "docpeg_api": { "ok": true, "count": 1 } } }
```

#### POST /api/v1/layerpeg/anchor
- 请求体:
```json
{ "project_id": "PJT-D34A70B8", "entity_uri": "v://.../entity/桥-400-1-1", "hash": "hash-test-001", "payload": {} }
```
- 返回:
```json
{ "ok": true, "anchor_id": "ANCHOR-...", "hash": "hash-test-001", "created_at": "2026-04-10 06:06:20" }
```

#### GET /api/v1/layerpeg/anchor
- Query: `project_id`(必填), `entity_uri`(必填)
- 返回:
```json
{ "ok": true, "items": [ { "id": "ANCHOR-...", "project_id": "...", "entity_uri": "v://...", "hash": "...", "payload": null, "created_by": "designer-user", "created_at": "..." } ] }
```

### 6) BOQItem（/api/v1）

#### GET /api/v1/boqitem/projects/{projectId}/nodes
```json
{ "ok": true, "items": [ { "id": "...", "parent_id": null, "code": "...", "name": "..." } ] }
```

#### GET /api/v1/boqitem/projects/{projectId}/items
```json
{ "ok": true, "items": [ { "id": "...", "item_code": "...", "material_name": "...", "design_qty": 0, "allocated": 0, "remaining": 0 } ] }
```

#### GET /api/v1/boqitem/projects/{projectId}/utxos
```json
{ "ok": true, "items": [ { "id": "...", "code": "...", "qty": 0, "status": "unspent", "linked_v": "v://..." } ] }
```

### 7) 文件上传与附件

#### POST /uploads/sessions
- 返回:
```json
{ "ok": true, "session_id": "US-...", "token": "...", "expires_at": "..." }
```

#### POST /upload
- Header: `x-upload-session-token` 或 `x-upload-token`
- Body: `multipart/form-data` (`file` + 可选关联字段)
- 返回:
```json
{ "ok": true, "file_id": "FILE-...", "object_key": "...", "url": "...", "hash": "..." }
```

#### GET /files
```json
{ "ok": true, "items": [ { "file_id": "FILE-...", "filename": "...", "uploaded_by": "...", "created_at": "..." } ], "total": 1 }
```

---

## 错误码与分页统一口径（建议同事前端按此处理）
- 错误码: `400/401/403/404/409/422/500`
- 分页字段: `page`, `page_size`, `total`（部分历史接口使用 `limit/offset/total`）
- 时间字段: ISO8601 或 `yyyy-MM-dd HH:mm:ss`（前端需统一格式化）
- 统一保底错误解析: `error` / `message` / `detail`

### 8) 工程树生成与返回结构（新增）

#### POST /projects/{projectId}/entities/tree-import
- 用途: 批量导入工程树节点（单位/分部/分项），后端自动 upsert，并返回完整树结构。
- Path 参数:
  - `projectId`(必填)
- 前端模板导入口径（当前 DocPeg 页面）:
  - 用户先下载“标准工程划分模板（Excel）”
  - 固定 4 列中文表头：`实体编码` / `实体名称` / `实体类型` / `位置链`
  - 不再使用 `chain_id` 列
  - 前端解析后转换为下方 `items[]` 请求体提交
- 请求体（两种输入都支持，至少传一种）:
```json
{
  "upsert": true,
  "items": [
    { "entity_code": "100", "entity_name": "路基工程", "entity_type": "unit", "location_chain": "" },
    { "entity_code": "100-1", "entity_name": "土石方工程", "entity_type": "division", "location_chain": "" },
    { "entity_code": "100-1-1", "entity_name": "挖方路基", "entity_type": "subitem", "location_chain": "K0+000-K1+000" },
    { "entity_code": "400", "entity_name": "桥梁工程", "entity_type": "unit", "location_chain": "" },
    { "entity_code": "400-1", "entity_name": "基础与下部构造", "entity_type": "division", "location_chain": "" },
    { "entity_code": "400-1-1", "entity_name": "钻孔灌注桩", "entity_type": "subitem", "location_chain": "桥400 1 1" },
    { "entity_code": "900", "entity_name": "附属工程", "entity_type": "unit", "location_chain": "" }
  ]
}
```
或
```json
{
  "upsert": true,
  "tree": [
    {
      "entity_code": "桥",
      "entity_name": "单位工程桥",
      "children": [
        {
          "entity_code": "桥-400",
          "entity_name": "桥梁工程",
          "children": [
            { "entity_code": "桥-400-1-1", "entity_name": "钻孔灌注桩" }
          ]
        }
      ]
    }
  ]
}
```
- 返回结构:
```json
{
  "ok": true,
  "project_id": "PJT-D34A70B8",
  "summary": {
    "imported_count": 7,
    "created_count": 7,
    "updated_count": 0,
    "skipped_count": 0
  },
  "created": [ { "entity_id": "ENT-...", "entity_code": "400-1-1", "entity_name": "钻孔灌注桩", "entity_type": "subitem" } ],
  "updated": [],
  "skipped": [],
  "total": 7,
  "flat_items": [ { "id": "ENT-...", "entity_uri": "v://...", "entity_code": "400-1-1", "entity_name": "钻孔灌注桩", "entity_type": "subitem", "status": "active" } ],
  "tree": [ { "entity_code": "400", "children": [ { "entity_code": "400-1", "children": [ { "entity_code": "400-1-1", "children": [] } ] } ] } ]
}
```

#### GET /projects/{projectId}/entities/tree
- 用途: 获取项目当前工程树（后端按 `entity_code` 层级规则自动组装）。
- 返回结构:
```json
{
  "ok": true,
  "project_id": "PJT-D34A70B8",
  "total": 3,
  "flat_items": [
    { "id": "ENT-...", "entity_code": "桥", "entity_name": "单位工程桥", "entity_type": "unit" },
    { "id": "ENT-...", "entity_code": "桥-400", "entity_name": "桥梁工程", "entity_type": "division" },
    { "id": "ENT-...", "entity_code": "桥-400-1-1", "entity_name": "钻孔灌注桩", "entity_type": "subitem" }
  ],
  "tree": [
    {
      "id": "ENT-...",
      "entity_code": "桥",
      "entity_name": "单位工程桥",
      "parent_code": null,
      "level": 1,
      "children": [
        {
          "entity_code": "桥-400",
          "level": 2,
          "children": [
            { "entity_code": "桥-400-1-1", "level": 3, "children": [] }
          ]
        }
      ]
    }
  ]
}
```
