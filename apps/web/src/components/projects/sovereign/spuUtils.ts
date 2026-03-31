import type { FormRow } from './types'

const fallbackSchema: Record<string, FormRow[]> = {
  SPU_Physical: [
    { field: 'design_value', label: '设计值', operator: 'present', default: '' },
    { field: 'measured_value', label: '实测值', operator: 'present', default: '' },
    { field: 'allowed_deviation', label: '允许偏差', operator: 'present', default: '' },
  ],
  SPU_Bridge: [
    { field: 'design_value', label: '设计值', operator: 'present', default: '' },
    { field: 'measured_value', label: '实测值', operator: 'present', default: '' },
    { field: 'allowed_deviation', label: '允许偏差', operator: 'present', default: '' },
    { field: 'cover_thickness', label: '保护层厚度', operator: 'range', default: '20~60', unit: 'mm' },
  ],
  SPU_Landscape: [
    { field: 'survival_rate', label: '成活率', operator: '>=', default: '95', unit: '%' },
    { field: 'coverage_rate', label: '覆盖率', operator: '>=', default: '90', unit: '%' },
    { field: 'height_range', label: '高度偏差', operator: 'range', default: '-5~5', unit: 'cm' },
  ],
  SPU_Reinforcement: [
    { field: 'design_value', label: '设计值', operator: 'present', default: '' },
    { field: 'measured_value', label: '实测值', operator: 'present', default: '' },
    { field: 'allowed_deviation', label: '允许偏差', operator: 'present', default: '' },
    { field: 'yield_strength', label: '屈服强度', operator: '>=', default: '400', unit: 'MPa' },
    { field: 'spacing_deviation', label: '间距偏差', operator: 'range', default: '-10~10', unit: 'mm' },
  ],
  SPU_Concrete: [
    { field: 'design_value', label: '设计值', operator: 'present', default: '' },
    { field: 'measured_value', label: '实测值', operator: 'present', default: '' },
    { field: 'allowed_deviation', label: '允许偏差', operator: 'present', default: '' },
    { field: 'compressive_strength', label: '抗压强度', operator: '>=', default: '30', unit: 'MPa' },
    { field: 'slump', label: '坍落度', operator: 'range', default: '120~220', unit: 'mm' },
  ],
  SPU_Contract: [
    { field: 'voucher_ref', label: '合同凭证编号', operator: 'present', default: '' },
    { field: 'claimed_amount', label: '申报金额', operator: 'present', default: '', unit: 'CNY' },
    { field: 'payment_cycle', label: '支付周期', operator: 'present', default: '' },
  ],
}

const componentTypeNameMap: Record<string, string> = {
  main_beam: '主梁',
  pier: '桥墩',
  guardrail: '护栏',
  slab: '桥面板',
  generic: '未配置',
}

const metricLabelMapRaw: Record<string, string> = {
  'Design Value': '设计值',
  'Measured Value': '实测值',
  'Allowed Deviation': '允许偏差',
  'Survival Rate': '成活率',
  'Coverage Rate': '覆盖率',
  'Height Deviation': '高度偏差',
  'Yield Strength': '屈服强度',
  'Spacing Deviation': '间距偏差',
  'Cover Thickness': '保护层厚度',
  'Compressive Strength': '抗压强度',
  Slump: '坍落度',
  'Quality Index': '质量指数',
  'Contract Voucher Ref': '合同凭证编号',
  'Claimed Amount': '申报金额',
  'Payment Cycle': '支付周期',
  yield_strength: '屈服强度',
  spacing_deviation: '间距偏差',
  cover_thickness: '保护层厚度',
  compressive_strength: '抗压强度',
  slump: '坍落度',
  quality_index: '质量指数',
  design_value: '设计值',
  measured_value: '实测值',
  allowed_deviation: '允许偏差',
  survival_rate: '成活率',
  coverage_rate: '覆盖率',
  height_range: '高度偏差',
  voucher_ref: '凭证编号',
  claimed_amount: '申报金额',
  payment_cycle: '支付周期',
}

function normalizeMetricKey(value: string): string {
  return String(value || '').trim().toLowerCase().replace(/[\s_-]+/g, '')
}

const metricLabelMapNormalized: Record<string, string> = Object.fromEntries(
  Object.entries(metricLabelMapRaw).map(([key, value]) => [normalizeMetricKey(key), value]),
)

export function spuTreeGeneLabel(spu: string): string {
  const value = String(spu || '').toUpperCase()
  if (value.includes('REINFORCEMENT')) return 'SPU 钢筋'
  if (value.includes('CONCRETE')) return 'SPU 混凝土'
  if (value.includes('BRIDGE')) return 'SPU 桥梁'
  if (value.includes('LANDSCAPE')) return 'SPU 绿化'
  if (value.includes('CONTRACT')) return 'SPU 合同'
  if (value.includes('PHYSICAL')) return 'SPU 实体'
  return 'SPU 组'
}

export function toChineseCompType(type: string): string {
  const key = String(type || '').trim()
  return componentTypeNameMap[key] || key || '未配置'
}

export function toChineseMetricLabel(label: string, fieldKey: string): string {
  const raw = String(label || '').trim()
  const cleanedRaw = raw.replace(/[\s_-]*测点\d+$/i, '').replace(/[#\s]*\d+$/i, '').trim()
  const cleanedField = String(fieldKey || '').replace(/__p\d+$/i, '').trim()
  if (/通用|generic/i.test(raw)) return '未绑定指标'
  const byRaw = metricLabelMapRaw[raw] || metricLabelMapRaw[cleanedRaw]
  if (byRaw) return byRaw
  const byField = metricLabelMapRaw[String(fieldKey || '').trim()] || metricLabelMapRaw[cleanedField]
  if (byField) return byField
  const byNormRaw = metricLabelMapNormalized[normalizeMetricKey(raw)] || metricLabelMapNormalized[normalizeMetricKey(cleanedRaw)]
  if (byNormRaw) return byNormRaw
  const byNormField = metricLabelMapNormalized[normalizeMetricKey(String(fieldKey || ''))] || metricLabelMapNormalized[normalizeMetricKey(cleanedField)]
  if (byNormField) return byNormField
  return raw || String(fieldKey || '未命名指标')
}

export function expandFormSchemaRows(rows: FormRow[]): FormRow[] {
  const out: FormRow[] = []
  rows.forEach((row, idx) => {
    const baseField = String(row.field || `f_${idx}`).trim() || `f_${idx}`
    const label = String(row.label || baseField).trim()
    const rawCount = Number(row.point_count || 1)
    const count = Number.isFinite(rawCount) ? Math.max(1, Math.min(12, Math.floor(rawCount))) : 1
    if (count <= 1) {
      out.push({
        ...row,
        field: baseField,
        label,
        source_field: String(row.source_field || baseField),
      })
      return
    }
    const labels = Array.isArray(row.point_labels) ? row.point_labels.map((x) => String(x || '').trim()).filter(Boolean) : []
    for (let i = 0; i < count; i += 1) {
      out.push({
        ...row,
        field: `${baseField}__p${i + 1}`,
        label: labels[i] || `${label} 测点${i + 1}`,
        source_field: baseField,
        point_count: 1,
      })
    }
  })
  return out
}

export function buildMeasurementPayload(
  form: Record<string, string>,
  schema: FormRow[],
): Record<string, number | string | number[]> {
  const payload: Record<string, number | string | number[]> = {}
  const grouped: Record<string, number[]> = {}
  schema.forEach((row, idx) => {
    const key = String(row.field || `f_${idx}`)
    const source = String(row.source_field || key)
    const raw = String(form[key] ?? '').trim()
    if (!raw) return
    const parsed = Number(raw)
    const value: number | string = Number.isFinite(parsed) ? parsed : raw
    payload[key] = value
    if (Number.isFinite(parsed)) {
      if (!grouped[source]) grouped[source] = []
      grouped[source].push(parsed)
    }
  })
  Object.entries(grouped).forEach(([source, values]) => {
    if (!values.length) return
    payload[`${source}_points`] = values
    const avg = values.reduce((sum, value) => sum + value, 0) / values.length
    payload[source] = Number(avg.toFixed(6))
  })
  return payload
}

export function inferSpu(code: string, name: string): string {
  const lower = String(name || '').toLowerCase()
  if (code.startsWith('101') || code.startsWith('102')) return 'SPU_Contract'
  if (['费', '协调', '管理', '监测', '监控', '咨询', '勘察', '保险', '交通', '保通', '征迁', '补偿', '迁改', '拆除', '临时', '安全', '试验', '检验'].some((keyword) => name.includes(keyword))) {
    return 'SPU_Contract'
  }
  if (code.startsWith('401') || name.includes('桥')) return 'SPU_Bridge'
  if (code.startsWith('600') || code.startsWith('702') || name.includes('绿化') || name.includes('种植') || lower.includes('landscape')) return 'SPU_Landscape'
  if (code.startsWith('403') || code.startsWith('405') || name.includes('钢筋') || lower.includes('rebar')) return 'SPU_Reinforcement'
  if (name.includes('混凝土') || lower.includes('concrete')) return 'SPU_Concrete'
  return 'SPU_Physical'
}

export function resolveFallbackSchema(spuLabel: string, code: string, name: string): FormRow[] {
  const label = String(spuLabel || '').toUpperCase()
  if (label.includes('BRIDGE')) return fallbackSchema.SPU_Bridge
  if (label.includes('LANDSCAPE')) return fallbackSchema.SPU_Landscape
  if (label.includes('REINFORCEMENT')) return fallbackSchema.SPU_Reinforcement
  if (label.includes('CONCRETE')) return fallbackSchema.SPU_Concrete
  if (label.includes('PHYSICAL')) return fallbackSchema.SPU_Physical
  if (label.includes('CONTRACT')) return fallbackSchema.SPU_Contract
  const inferred = inferSpu(code, name)
  return fallbackSchema[inferred] || []
}

export function sanitizeMeasuredInput(raw: string): string {
  const normalized = String(raw || '').replace(/,/g, '.').replace(/[^\d.+-]/g, '')
  const sign = normalized.startsWith('-') ? '-' : ''
  const body = sign ? normalized.slice(1) : normalized
  const plusRemoved = body.replace(/\+/g, '')
  const parts = plusRemoved.split('.')
  if (parts.length <= 1) return `${sign}${plusRemoved}`
  return `${sign}${parts.shift()}.${parts.join('')}`
}
