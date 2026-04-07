# NormRef 总览（官方定义）

## 1. NormRef 是什么
NormRef = 规范参考协议网关（Norm Reference Protocol Gateway）。

它是 DocPeg / CoordOS 体系中专门负责把“规范、标准、规则”结构化、可执行、可验证的核心引擎与协议层。

一句话：把人类文字规则，翻译成机器可读、可自动校验、可 Proof 的主权协议。

## 2. 核心作用
- 统一入口：所有规则通过 `v://normref.com/...` 引用。
- 自动校验：Gate 层自动判断数据是否符合规范。
- 协议化：普通质检表/处方/检查单转为五层结构协议块。
- 可追溯：每次校验和执行都产出 Proof。
- 可复用：同一规范在多项目、多表族复用。

## 3. 五层结构（必须）
1. Header（身份层）
- 作用：定义“这是什么协议、属于谁、依据什么规范”。
- 典型字段：`doc_type`、`v_uri`、`version`、`jurisdiction`、`created_at`。

2. Gate（门槛层）
- 作用：定义“什么条件才允许通过”。
- 典型字段：`pre_conditions`、`entry_rules(gte/lte/range)`、`required_trip_roles`。

3. Body（内容层）
- 作用：定义“需要填什么、怎么算”。
- 典型字段：`basic`、`test_data`、`relations`、计算公式。

4. Proof（证明层）
- 作用：保证不可篡改、可验证。
- 典型字段：`data_hash`、`proof_hash`、`signatures`、`timestamps`、`witness_logs`。

5. State（状态层）
- 作用：描述生命周期与当前进度。
- 典型字段：`lifecycle_stage`、`state_matrix`、`next_action`、`valid_until`。

## 4. 在体系中的位置
- SpecIR：NormRef 是规范定义层的重要实现形式。
- Tab-to-Peg：把原始表格/处方/Excel 自动转换为 NormRef 协议。
- Gate：执行校验的核心。
- ProofIR：每次 NormRef 调用产出 Proof。
- DocPeg Core API：表单提交先过 NormRef，再进入执行链。

## 5. 应用示例
- 工程：桥施 7 表 -> 自动校验孔径、倾斜度是否符合 JTG F80。
- 中医：处方 -> 自动校验配伍禁忌、剂量范围、妊娠禁忌。
- 通用：任何“按标准执行”的业务表单都可协议化。

## 6. 一句话总结
NormRef 是把“人类规范”翻译成“机器可执行、可验证主权协议”的标准层与引擎。

有了 NormRef：
- 表格不再是死数据，而是可自动判定的活协议。
- 每次填写和执行都有可追溯 Proof。
- 系统具备“按规范自动执行”的能力。
