# QCSpec 真实后端联调验收清单

更新时间：2026-03-24

## 1. 联调基础

- 前端地址：`http://localhost:3000`
- 后端地址：`http://localhost:8000`
- API 前缀：`/v1`
- 认证头：`Authorization: Bearer <token>`
- 统一约定：
  - 除 `Auth` 登录/注册接口外，其余业务 API 全部需要 Bearer token
  - 未登录/过期：`401` 或 `403`
  - 前端收到 `401/403` 后会自动清理登录态并回登录页

## 2. 模块接口清单（P0）

### 2.1 Auth

- `POST /v1/auth/login`
- `POST /v1/auth/register-enterprise`
- `GET /v1/auth/me`
- `POST /v1/auth/logout`
- `GET /v1/auth/enterprise/{enterprise_id}`

登录请求示例：

```json
{
  "email": "admin@zhongbei.com",
  "password": "123456"
}
```

验收点：

- `register-enterprise` 返回 `ok=true` 且可用管理员账号登录
- `login` 返回 `access_token/user_id/enterprise_id`
- 带 token 调 `me` 可返回当前用户信息
- 调 `logout` 后再调 `me` 应返回 `401`

### 2.2 Projects

- `GET /v1/projects/?enterprise_id=...&status=...&type=...`
- `POST /v1/projects/`
- `GET /v1/projects/{project_id}`
- `PATCH /v1/projects/{project_id}`
- `DELETE /v1/projects/{project_id}?enterprise_id=...`
- `POST /v1/projects/{project_id}/autoreg-sync`
- `GET /v1/projects/activity?enterprise_id=...&limit=...`
- `GET /v1/projects/export?enterprise_id=...&status=...&type=...`

验收点：

- 新建项目后列表可见
- 编辑后详情与列表一致
- 删除后列表消失
- 导出 CSV 可下载

### 2.3 Inspections

- `GET /v1/inspections/?project_id=...&result=...&type=...&limit=...&offset=...`
- `POST /v1/inspections/`
- `DELETE /v1/inspections/{inspection_id}`
- `GET /v1/inspections/stats/{project_id}`

提交请求示例：

```json
{
  "project_id": "33333333-3333-4333-8333-333333333333",
  "location": "K50+200",
  "type": "flatness",
  "type_name": "路面平整度",
  "value": 1.9,
  "standard": 2.0,
  "unit": "m/km",
  "result": "pass",
  "person": "王质检",
  "remark": "晴天，3点取均值",
  "photo_ids": []
}
```

验收点：

- 返回 `inspection_id/proof_id`
- 若传 `photo_ids`，返回 `linked_photo_count > 0`（有匹配照片时）
- `stats` 数值随新增/删除实时变化

### 2.4 Photos

- `POST /v1/photos/upload`（`multipart/form-data`）
- `GET /v1/photos/?project_id=...&inspection_id=...`
- `DELETE /v1/photos/{photo_id}`

验收点：

- 上传返回 `photo_id/proof_id/storage_url`
- 删除成功后，照片列表不再存在该记录
- 删除照片后对应 `proof_chain` 记录同步清理

### 2.5 Reports

- `POST /v1/reports/generate`
- `GET /v1/reports/?project_id=...`
- `GET /v1/reports/{report_id}`

生成请求示例：

```json
{
  "project_id": "33333333-3333-4333-8333-333333333333",
  "enterprise_id": "11111111-1111-4111-8111-111111111111",
  "location": "K50+200",
  "date_from": "2026-03-01",
  "date_to": "2026-03-31"
}
```

验收点：

- `generate` 返回 `202 accepted`
- 列表中出现新报告
- 报告统计与过滤条件（`location/date_from/date_to`）一致

### 2.6 Proof

- `GET /v1/proof/?project_id=...`
- `GET /v1/proof/verify/{proof_id}`
- `GET /v1/proof/stats/{project_id}`
- `GET /v1/proof/node-tree?root_uri=...`

验收点：

- `verify` 对有效 proof 返回 `valid=true`
- `stats` 和业务数据量一致

### 2.7 Team

- `GET /v1/team/members?enterprise_id=...&include_inactive=false`
- `POST /v1/team/members`
- `PATCH /v1/team/members/{user_id}`
- `DELETE /v1/team/members/{user_id}`

验收点：

- 新增成员后列表可见
- 更新角色后列表即时刷新
- 删除成员后默认列表不可见（软删除）

### 2.8 Settings

- `GET /v1/settings/?enterprise_id=...`
- `PATCH /v1/settings/?enterprise_id=...`
- `POST /v1/settings/erpnext/test`
- `POST /v1/settings/template/upload`（`multipart/form-data`）

验收点：

- 保存后刷新页面配置不丢失
- ERP 测试接口可返回连接结果
- 模板上传后返回最新配置

## 3. 可选模块（P1）

- `POST /v1/autoreg/project`
- `POST /v1/gitpeg/autoreg/project`
- `GET /v1/autoreg/projects?limit=100`

验收点：

- 自动注册后可在项目注册表查询到 `project_uri/site_uri`

## 4. 端到端冒烟流程（建议每次发布执行）

1. 登录获取 token，调用 `me` 验证会话
2. 新建项目
3. 上传 1~2 张现场照片
4. 提交 1 条质检（带 `photo_ids`）
5. 检查质检列表、统计、Proof 列表
6. 触发报告生成并检查报告列表
7. 删除一张照片，确认列表与 Proof 链一致
8. 退出登录后再次访问任意受保护 API，应返回 `401/403`

## 5. 已完成的关键联调修复

- 前端已统一携带 Bearer token
- 前端已统一处理 `401/403` 自动回登录
- 报告生成已支持 `date_from/date_to`
- 质检提交已支持 `photo_ids` 关联
- 照片删除已清理对应 Proof 链记录
