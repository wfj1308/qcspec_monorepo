import type { FormRow, GateStats, NormResolutionState } from './types'

export type NormStatus = 'pending' | 'success' | 'fail'

export type ThresholdResolution =
  | { kind: 'present'; raw: string }
  | { kind: 'plusminus'; raw: string; min: number; max: number }
  | { kind: 'range'; raw: string; min: number; max: number }
  | { kind: 'scalar'; raw: string; value: number }
  | { kind: 'unknown'; raw: string }

export type ResolveGateArgs = {
  schema: FormRow[]
  form: Record<string, string>
  ctx: Record<string, unknown> | null
  isContractSpu: boolean
}

function asDict(value: unknown): Record<string, unknown> {
  return value && typeof value === 'object' && !Array.isArray(value) ? (value as Record<string, unknown>) : {}
}

export function resolveNormThreshold(op: string, threshold: string): ThresholdResolution {
  const operator = String(op || '').trim().toLowerCase()
  const raw = String(threshold || '').trim()
  if (operator === 'present') return { kind: 'present', raw }
  if (!raw) return { kind: 'unknown', raw }

  if (raw.includes('±')) {
    const part = raw.split('±')[1] || ''
    const value = Number(part.trim())
    if (Number.isFinite(value)) {
      const span = Math.abs(value)
      return { kind: 'plusminus', raw, min: -span, max: span }
    }
  }

  const normalizedRange = raw.startsWith('range-') ? raw.replace(/^range-/i, '') : raw
  if (normalizedRange.includes('~')) {
    const [left, right] = normalizedRange.split('~').map((item) => Number(item.trim()))
    if (Number.isFinite(left) && Number.isFinite(right)) {
      return { kind: 'range', raw, min: Math.min(left, right), max: Math.max(left, right) }
    }
  }

  const value = Number(normalizedRange)
  if (Number.isFinite(value)) return { kind: 'scalar', raw, value }
  return { kind: 'unknown', raw }
}

export function evaluateNormValue(op: string, threshold: string, value: string): NormStatus {
  const operator = String(op || '').trim().toLowerCase()
  if (operator === 'present') {
    return String(value || '').trim() ? 'success' : 'pending'
  }

  const numeric = Number(value)
  if (!Number.isFinite(numeric)) return 'pending'

  const resolved = resolveNormThreshold(operator, threshold)
  if (resolved.kind === 'plusminus' || resolved.kind === 'range') {
    return numeric >= resolved.min && numeric <= resolved.max ? 'success' : 'fail'
  }
  if (resolved.kind === 'scalar') {
    if (operator === '>=') return numeric >= resolved.value ? 'success' : 'fail'
    if (operator === '<=') return numeric <= resolved.value ? 'success' : 'fail'
    return numeric === resolved.value ? 'success' : 'fail'
  }
  return 'pending'
}

export function describeNormRule(operator: string, threshold: string, unit: string): string {
  const op = String(operator || '').trim().toLowerCase()
  const resolved = resolveNormThreshold(op, threshold)
  const suffix = String(unit || '').trim()
  if (resolved.kind === 'present') return '需填写'
  if (resolved.kind === 'plusminus') return `允许偏差 ±${Math.abs(resolved.max)}${suffix}`
  if (resolved.kind === 'range') return `应在 ${resolved.min}~${resolved.max}${suffix} 范围内`
  if (resolved.kind === 'scalar') {
    if (op === '>=') return `需 >= ${resolved.value}${suffix}`
    if (op === '<=') return `需 <= ${resolved.value}${suffix}`
    return `需 = ${resolved.value}${suffix}`
  }
  return `${String(threshold || '-').trim()}${suffix}`.trim()
}

export function resolveNormRefs(ctx: Record<string, unknown> | null, isContractSpu: boolean): NormResolutionState {
  const node = asDict(ctx?.node)
  const specBinding = String(node.linked_spec_uri || '').trim()
  const gateBinding = String(node.linked_gate_id || '').trim()
  const normRefs = Array.isArray(node.norm_refs)
    ? node.norm_refs.map((item) => String(item || '').trim()).filter(Boolean)
    : []
  const isBound = isContractSpu || Boolean(specBinding || gateBinding || normRefs.length)
  const status = isContractSpu
    ? 'ready'
    : specBinding && gateBinding
      ? 'ready'
      : specBinding || gateBinding || normRefs.length
        ? 'partial'
        : 'missing'
  const message = isContractSpu
    ? '合同凭证模式不依赖 NormRef 门控。'
    : status === 'ready'
      ? `NormRef 已联通：${normRefs.length || 1} 条规则在线。`
      : status === 'partial'
        ? 'NormRef 部分联通，建议补齐 Spec / Gate 绑定。'
        : 'NormRef 缺失，提交应被 Gatekeeper 拦截。'

  return {
    specBinding,
    gateBinding,
    normRefs,
    isBound,
    status,
    message,
  }
}

export function resolveGateState({ schema, form, ctx, isContractSpu }: ResolveGateArgs): GateStats {
  const total = schema.length
  let pass = 0
  let fail = 0
  let pending = 0

  for (let i = 0; i < schema.length; i += 1) {
    const row = schema[i]
    const key = String(row.field || `f_${i}`)
    const status = evaluateNormValue(String(row.operator || ''), String(row.default || ''), form[key] || '')
    if (status === 'success') pass += 1
    else if (status === 'fail') fail += 1
    else pending += 1
  }

  const qcStatus: string = total === 0 ? '未配置' : fail > 0 ? '不合格' : pending > 0 ? '待检' : '合格'
  const node = asDict(ctx?.node)
  const gatekeeper = asDict(ctx?.gatekeeper)
  const labNode = asDict(node.lab_status)
  const labTotal = Number(labNode.total || 0)
  const labPass = Number(labNode.pass || 0)
  const labLatest = String(labNode.latest_proof_id || '')
  const labLatestPass = String(labNode.latest_pass_proof_id || '')
  const labLatestHash = String(labNode.latest_pass_proof_hash || labNode.latest_proof_hash || '')
  const labStatus = isContractSpu
    ? '不适用'
    : labTotal > 0
      ? (labPass > 0 ? '已取证' : '未通过')
      : '未取证'
  const labQualified = isContractSpu || Boolean(gatekeeper.lab_ok) || Boolean(labLatestPass) || labPass > 0
  const qcCompliant = Boolean(gatekeeper.is_compliant) || qcStatus === '合格'
  const qcStatusDisplay = qcCompliant ? '合格' : (qcStatus === '合格' ? '待检' : qcStatus)

  return {
    total,
    pass,
    fail,
    pending,
    qcStatus: qcStatusDisplay,
    qcCompliant,
    labStatus,
    labQualified,
    dualQualified: qcCompliant && labQualified,
    labPass,
    labTotal,
    labLatest,
    labLatestPass,
    labLatestHash,
  }
}

export function deriveGateReason(gateStats: GateStats) {
  if (!gateStats.labQualified) return '缺少实验合格 Proof'
  if (!gateStats.qcCompliant) return 'TripRole 现场判定未通过'
  return ''
}
