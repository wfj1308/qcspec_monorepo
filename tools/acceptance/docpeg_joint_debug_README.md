# DocPeg 联调 Smoke 工具

## 1. 文件说明

1. 脚本：`tools/acceptance/docpeg_joint_debug_smoke.ps1`
2. Payload 模板目录：`tools/acceptance/docpeg_joint_debug_payloads`
3. 结果输出：`tmp/docpeg_joint_debug_last_run.json`

## 2. 快速开始（只读模式，推荐先跑）

```powershell
powershell -ExecutionPolicy Bypass -File tools/acceptance/docpeg_joint_debug_smoke.ps1 `
  -ProjectId "<projectId>" `
  -ChainId "<chainId>" `
  -EntityUri "<entity_uri>" `
  -ComponentUri "<component_uri>" `
  -FormCode "<formCode>" `
  -DocId "<docId>" `
  -Authorization "Bearer <token>"
```

也可用环境变量传鉴权：

```powershell
$env:DOCPEG_AUTHORIZATION = "Bearer <token>"
$env:DOCPEG_X_API_KEY = "<apiKey>"
```

## 3. 开启写接口联调

写接口默认关闭。确认测试数据可写后，再加 `-RunWriteOps`：

```powershell
powershell -ExecutionPolicy Bypass -File tools/acceptance/docpeg_joint_debug_smoke.ps1 `
  -ProjectId "<projectId>" `
  -ChainId "<chainId>" `
  -EntityUri "<entity_uri>" `
  -ComponentUri "<component_uri>" `
  -FormCode "<formCode>" `
  -DocId "<docId>" `
  -Authorization "Bearer <token>" `
  -RunWriteOps
```

## 4. 注意事项

1. 模板里包含 `__TODO_*__` 占位符时，脚本会自动跳过对应写接口并提示告警。
2. `trips` 接口自动兼容：
   - 先尝试 `/api/v1/trips/preview` 与 `/api/v1/trips/submit`
   - 若 404，再回退 `/trips/preview` 与 `/trips/submit`
3. `FormCode` 为空时，会跳过 NormRef 细项接口。
4. 脚本不会修改仓库业务代码，只做联调请求与结果汇总。
5. `-Simulate` 可用于测试阶段：不发真实请求，返回模拟成功结果并输出完整汇总。

## 5. 完整写链路所需参数

当你要跑 `-RunWriteOps` 的完整写链路（含 trips/sign/verify）时，建议额外传入：

1. `-TripAction "<action>"`
2. `-BodyHash "<body_hash>"`
3. `-ExecutorUri "<executor_uri>"`
4. `-SigData "<sig_data>"`

示例：

```powershell
powershell -ExecutionPolicy Bypass -File tools/acceptance/docpeg_joint_debug_smoke.ps1 `
  -ProjectId "<projectId>" `
  -ChainId "<chainId>" `
  -EntityUri "<entity_uri>" `
  -ComponentUri "<component_uri>" `
  -FormCode "<formCode>" `
  -DocId "<docId>" `
  -TripAction "qc_submit" `
  -BodyHash "<body_hash>" `
  -ExecutorUri "<executor_uri>" `
  -SigData "<sig_data>" `
  -Authorization "Bearer <token>" `
  -RunWriteOps
```

测试阶段纯模拟：

```powershell
powershell -ExecutionPolicy Bypass -File tools/acceptance/docpeg_joint_debug_smoke.ps1 `
  -ProjectId "sim-project" `
  -ChainId "sim-chain" `
  -EntityUri "entity://sim" `
  -ComponentUri "v://sim/component/001" `
  -FormCode "qc-form-001" `
  -DocId "doc-sim-001" `
  -RunWriteOps `
  -Simulate
```
