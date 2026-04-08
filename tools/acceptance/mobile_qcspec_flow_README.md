# QCSpec Mobile 验收脚本

## 一键运行

```powershell
powershell -ExecutionPolicy Bypass -File tools/acceptance/run_mobile_qcspec_flow.ps1
```

或直接运行：

```powershell
python tools/acceptance/mobile_qcspec_flow_e2e.py
```

## 覆盖检查项

1. 扫码后 `current-step` 可返回当前工序
1. 主链状态接口 `chain-status` 可返回当前链路状态
2. 二维码接口可返回 PNG
3. SnapPeg 照片锚定可用
4. `submit-mobile` 可提交并返回 `proof_id`
5. 返回 `triprole_sync` 字段
6. 提交后工序自动推进到下一步

## 默认测试样例

- 构件：`K12-340-4C`
- 当前工序：`rebar_install`
- 下一工序：`concrete_pour`
