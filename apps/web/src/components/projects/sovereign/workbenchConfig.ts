export type RolePlaybook = {
  role: string
  title: string
  goal: string
  actions: string[]
  constraints: string[]
  chain: string
}

export const OFFLINE_KEY = 'qcspec_offline_packets_v1'

export const ROLE_PLAYBOOK: RolePlaybook[] = [
  {
    role: 'Field Executor',
    title: '现场施工员',
    goal: '扫码即录、即时判定、弱网可用',
    actions: ['扫码进入 v:// 细目', '录入实测值并触发 NormPeg 判定', '拍照生成 SnapPeg 物证 Hash', '弱网封存离线包并自动重放'],
    constraints: ['仅叶子节点可执行', '必须通过 DID Gate 资质校验', '关键动作建议强制 GPS + NTP + 水印'],
    chain: 'zero_ledger -> quality.check -> (fail: remediation) / (pass: measure)',
  },
  {
    role: 'Chief Engineer',
    title: '设计院总工',
    goal: '掌握规则立法权和版本治理权',
    actions: ['导入 400 章并生成层级 UTXO', '维护 SpecDict 和 Context 阈值', '使用 AI 生成 Gate 规则并发布版本', '批量应用到同类细目'],
    constraints: ['规则修改必须版本化存证', 'Gate 必须绑定 SpecDict', '规范升版后需可追溯回滚'],
    chain: 'spec_dicts(versioned) <-> gates(binding) -> linked_gate_id/spec_dict_key',
  },
  {
    role: 'Supervisor',
    title: '监理工程师',
    goal: '在线见证签章，闭合不合格流程',
    actions: ['审核报验链并执行 OrdoSign', '见证取样并联动 LabPeg', 'FAIL 自动整改通知并复检关闭', '监控应检/已检/漏检预警'],
    constraints: ['签章必须上链', '未复检 PASS 不得解锁后续计量', '整改链必须完整可追溯'],
    chain: 'inspection(FAIL) -> remediation.open -> remediation.reinspect -> remediation.close',
  },
  {
    role: 'Owner',
    title: '业主方',
    goal: '数据即结算，结算即审计',
    actions: ['双合格门控后发起计量', '生成支付证书并穿透审计', '推送 ERPNext 同步状态', '生成 RailPact 支付指令'],
    constraints: ['QC/Lab 任一不通过不得结算', '超量计量自动锁死', '支付单必须可回溯到 Proof 链'],
    chain: 'settlement.confirm -> payment.certificate -> railpact.instruction',
  },
  {
    role: 'Lab Tech',
    title: '实验室检测员',
    goal: '保障材料检测原生真实性',
    actions: ['按 JTG E 表单录入试验', '校验仪器检定有效期', '生成报告并回挂到 BOQ 节点'],
    constraints: ['过检定期禁止录入', '样品全流程要可追踪', '检测报告 Hash 必须可追溯'],
    chain: 'lab.record -> lab PASS/FAIL -> dual gate decision',
  },
  {
    role: 'Auditor',
    title: '审计/监管',
    goal: '免登录验真与竣工审计',
    actions: ['扫码进入 verify 页面', '查看金额->数量->质量->规范穿透链', '下载 DocFinal 全量审计包'],
    constraints: ['验真必须展示 proof/hash/签名', '档案需分页/分卷/签章', '异常行为要可机器检出'],
    chain: 'QR verify -> lineage trace -> docfinal audit',
  },
]

export const WORKBENCH_STYLES = {
  inputBaseCls: 'border border-slate-700/90 rounded-lg px-3 py-2 bg-slate-950/90 text-slate-100 text-sm leading-5 placeholder:text-slate-500 focus:outline-none focus:ring-2 focus:ring-sky-500/40 focus:border-sky-500 transition',
  inputXsCls: 'border border-slate-700/90 rounded-lg px-3 py-2 bg-slate-950/90 text-slate-100 text-sm leading-5 placeholder:text-slate-500 focus:outline-none focus:ring-2 focus:ring-sky-500/40 focus:border-sky-500 transition',
  btnBlueCls: 'rounded-lg border border-sky-500/70 bg-gradient-to-r from-slate-800 to-slate-700 text-sky-100 hover:from-slate-700 hover:to-slate-600 transition-colors duration-200 shadow-[0_0_0_1px_rgba(56,189,248,.15)]',
  btnGreenCls: 'rounded-lg border border-emerald-500/70 bg-gradient-to-r from-slate-800 to-slate-700 text-emerald-100 hover:from-slate-700 hover:to-slate-600 transition-colors duration-200 shadow-[0_0_0_1px_rgba(16,185,129,.15)]',
  btnAmberCls: 'rounded-lg border border-amber-500/70 bg-gradient-to-r from-slate-800 to-slate-700 text-amber-100 hover:from-slate-700 hover:to-slate-600 transition-colors duration-200 shadow-[0_0_0_1px_rgba(245,158,11,.15)]',
  btnRedCls: 'rounded-lg border border-rose-500/70 bg-gradient-to-r from-rose-900 to-rose-800 text-rose-100 hover:from-rose-800 hover:to-rose-700 transition-colors duration-200 shadow-[0_0_0_1px_rgba(244,63,94,.15)]',
  panelCls: 'h-full rounded-2xl border border-slate-700/80 bg-gradient-to-b from-slate-900 to-slate-900/75 p-4 text-slate-100 shadow-[0_14px_28px_rgba(2,6,23,.35)]',
} as const

export const WORKBENCH_FRAME_STYLE_TEXT = `@keyframes sovereignPulse {0%{transform:scale(.92);opacity:.45}50%{transform:scale(1.06);opacity:1}100%{transform:scale(.92);opacity:.45}}
@keyframes ordosealPulse {0%{transform:scale(.8);opacity:.2}50%{transform:scale(1.12);opacity:.95}100%{transform:scale(.8);opacity:.2}}
.sovereign-workbench{font-size:15px;line-height:1.68;font-family:"Fira Sans","Segoe UI",sans-serif}
.sovereign-workbench .font-mono{font-family:"Fira Code","Cascadia Code","SFMono-Regular",monospace}
.sovereign-workbench .wb-panel{padding:20px;border-radius:16px}
.sovereign-workbench input,.sovereign-workbench select,.sovereign-workbench button{min-height:44px}
.sovereign-workbench textarea{line-height:1.68}
.sovereign-workbench .wb-table-head{font-size:14px;padding:13px 15px}
.sovereign-workbench .wb-table-row{font-size:14px;line-height:1.72;padding:13px 15px}`

export const WORKBENCH_GRID_OVERLAY_STYLE = {
  backgroundImage:
    'linear-gradient(rgba(148,163,184,0.08) 1px, transparent 1px), linear-gradient(90deg, rgba(148,163,184,0.08) 1px, transparent 1px)',
  backgroundSize: '26px 26px',
  maskImage: 'linear-gradient(180deg, rgba(255,255,255,0.7), rgba(255,255,255,0.08))',
} as const

type WorkbenchDisplayTextArgs = {
  latestEvidenceNode: Record<string, unknown> | null
  inputProofId: string
  totalHash: string
  arPrimary: Record<string, unknown> | null
  active: { code?: string; name?: string } | null
  unitRes: Record<string, unknown> | null
}

export function buildWorkbenchDisplayTexts({
  latestEvidenceNode,
  inputProofId,
  totalHash,
  arPrimary,
  active,
  unitRes,
}: WorkbenchDisplayTextArgs) {
  const latestProofIdText = String((latestEvidenceNode || {}).proof_id || inputProofId || '-')
  const totalHashShort = totalHash ? `${totalHash.slice(0, 10)}...` : '-'
  const nearestAnchorText = arPrimary
    ? `${String(arPrimary.item_no || arPrimary.boq_item_uri || arPrimary.uri || 'UTXO')} · ${String(arPrimary.distance_m || '-')}m`
    : ''
  const currentSubdivisionText = active?.code ? `${active.code.split('-')[0]}章 ${active.name || ''}`.trim() : '未选择'
  const merkleRootText = String((unitRes || {}).project_root_hash || (unitRes || {}).global_project_fingerprint || '-') || '-'

  return {
    latestProofIdText,
    totalHashShort,
    nearestAnchorText,
    currentSubdivisionText,
    merkleRootText,
  }
}

