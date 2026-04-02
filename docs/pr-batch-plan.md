# 重构提交拆批计划（执行版）
更新时间：2026-04-02

## 目标
把当前大工作区拆成可审阅、可回滚、可验证的多批 PR，避免一次性提交过大。

## 建议批次
1. 后端架构边界批（优先）
   - 范围：`services/api/domain/**`、`services/api/dependencies.py`、`services/api/domain/__init__.py`
   - 目标：完成 domain 边界收口与 integrations 统一接入
   - 验证：`python -m pytest -q services/api/tests --maxfail=1` + OpenAPI 路由数稳定

2. 后端兼容层与 worker 稳定性批
   - 范围：`services/api/*_service.py` 中兼容 shim、`services/api/workers/**`、边界/冒烟测试
   - 目标：消除循环导入风险，固化 smoke + boundary guard
   - 验证：后端全量测试

3. 前端 Sovereign Workbench 收口批
   - 范围：`apps/web/src/components/projects/**`、`apps/web/src/app/**`（仅本次重构相关）
   - 目标：模块化拆分、TripFlow 语义与乱码修复、构建稳定
   - 验证：`pnpm -C apps/web exec tsc --noEmit` + `pnpm -C apps/web run -s build`

4. 文档与规范批
   - 范围：`docs/**`、`.gitignore`
   - 目标：进度看板、流程文档、上线验收规范同步
   - 验证：文档抽检 + 链接可用性检查

## 不提交项（保持忽略/删除）
- 本地烟测产物：`tmp/docpeg_smoke/**`
- 缓存/日志：`.pytest_cache/`、`.runtime-logs/`、`.npm-temp-cache/`、`*.log`

## 每批统一执行清单
1. 仅 `git add` 当前批次文件
2. 运行对应验证命令（前端或后端）
3. 生成提交信息（`feat/refactor/test/docs` 前缀）
4. 记录 PR 说明：目标、范围、回归、风险、回滚
