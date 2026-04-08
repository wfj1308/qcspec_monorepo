import type { FieldValidation, MobileFormField, MobileFormSpec, ThresholdValue } from '../types/mobile'

function toNumber(value: unknown): number | null {
  if (typeof value === 'number' && Number.isFinite(value)) return value
  if (typeof value === 'string') {
    const parsed = Number(value.trim())
    return Number.isFinite(parsed) ? parsed : null
  }
  return null
}

function normalizeRange(value: ThresholdValue): [number, number] | null {
  if (!Array.isArray(value) || value.length < 2) return null
  const min = toNumber(value[0])
  const max = toNumber(value[1])
  if (min === null || max === null) return null
  return [min, max]
}

export function buildHint(operator: string, value: ThresholdValue, unit: string): string {
  if (operator === 'gte') return `设计>=${value}${unit}`
  if (operator === 'lte') return `规范<=${value}${unit}`
  if (operator === 'range' && Array.isArray(value)) return `允许范围 ${value[0]}-${value[1]}${unit}`
  return `目标=${value}${unit}`
}

export function validateField(field: MobileFormField, rawValue: string): FieldValidation {
  const text = String(rawValue || '').trim()
  if (!text) return { ok: false, message: '请填写此项' }

  const value = toNumber(text)
  if (value === null) {
    return {
      ok: false,
      message: '请输入有效数字',
      tip: '请确认测量数据',
    }
  }

  const operator = field.threshold.operator
  const threshold = field.threshold.value
  const unit = field.unit || ''

  if (operator === 'gte') {
    const target = toNumber(threshold) ?? 0
    if (value >= target) return { ok: true, message: '满足要求' }
    const deltaPercent = target === 0 ? 0 : ((value - target) / target) * 100
    return {
      ok: false,
      message: `低于设计值 ${target}${unit}`,
      detail: `偏差 ${deltaPercent.toFixed(1)}% 超过允许范围`,
      tip: '请确认测量数据',
    }
  }

  if (operator === 'lte') {
    const target = toNumber(threshold) ?? 0
    if (value <= target) return { ok: true, message: '满足要求' }
    const deltaPercent = target === 0 ? 0 : ((value - target) / target) * 100
    return {
      ok: false,
      message: `高于允许值 ${target}${unit}`,
      detail: `偏差 +${deltaPercent.toFixed(1)}% 超过允许范围`,
      tip: '请确认测量数据',
    }
  }

  if (operator === 'range') {
    const range = normalizeRange(threshold)
    if (!range) return { ok: false, message: '阈值配置错误' }
    const [min, max] = range
    if (value >= min && value <= max) return { ok: true, message: '满足要求' }
    return {
      ok: false,
      message: `应在 ${min}-${max}${unit} 范围内`,
      detail: `当前值 ${value}${unit}`,
      tip: '请确认测量数据',
    }
  }

  if (String(value) === String(threshold)) return { ok: true, message: '满足要求' }

  return {
    ok: false,
    message: `应为 ${threshold}${unit}`,
    tip: '请确认测量数据',
  }
}

export function buildActualData(spec: MobileFormSpec, values: Record<string, string>) {
  return spec.fields.reduce<Record<string, number | null>>((acc, field) => {
    const value = String(values[field.key] || '').trim()
    acc[field.key] = value ? Number(value) : null
    return acc
  }, {})
}


