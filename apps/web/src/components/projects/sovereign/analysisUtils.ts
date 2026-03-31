export type ConsensusDeviation = {
  ok: boolean
  conflict: boolean
  minValue: number
  maxValue: number
  deviation: number
  deviationPercent: number
  allowedDeviation: number | null
  allowedDeviationPercent: number | null
  values: number[]
  defaulted: boolean
}

export function parseNumericInput(raw: string): number | null {
  const cleaned = String(raw || '').replace(/,/g, '').trim()
  if (!cleaned) return null
  const parsed = Number(cleaned)
  return Number.isFinite(parsed) ? parsed : null
}

export function parseConsensusValue(raw: string, fallback: number): number {
  const parsed = parseNumericInput(raw)
  return parsed == null ? fallback : parsed
}

export function detectConsensusDeviation(
  values: number[],
  baseValue: number,
  allowedAbs?: number | null,
  allowedPct?: number | null,
): ConsensusDeviation {
  const clean = values.filter((value) => Number.isFinite(value))
  if (clean.length < 2) {
    return {
      ok: false,
      conflict: false,
      minValue: clean[0] ?? 0,
      maxValue: clean[0] ?? 0,
      deviation: 0,
      deviationPercent: 0,
      allowedDeviation: allowedAbs ?? null,
      allowedDeviationPercent: allowedPct ?? null,
      values: clean,
      defaulted: allowedAbs == null && allowedPct == null,
    }
  }
  const minValue = Math.min(...clean)
  const maxValue = Math.max(...clean)
  const deviation = maxValue - minValue
  const avg = (minValue + maxValue) / 2
  const baseline = avg || Math.abs(baseValue) || 0
  const deviationPercent = baseline ? (deviation / baseline) * 100 : 0
  const defaulted = allowedAbs == null && allowedPct == null
  let conflict = false
  if (allowedAbs != null && deviation > allowedAbs) conflict = true
  if (allowedPct != null && deviationPercent > allowedPct) conflict = true
  if (defaulted) {
    conflict = avg ? deviationPercent > 0.5 : deviation > 0
  }
  return {
    ok: true,
    conflict,
    minValue,
    maxValue,
    deviation,
    deviationPercent,
    allowedDeviation: allowedAbs ?? null,
    allowedDeviationPercent: allowedPct ?? null,
    values: clean,
    defaulted,
  }
}

export function describeSpecdictItem(item: unknown): string {
  if (item == null) return '-'
  if (typeof item === 'string' || typeof item === 'number') return String(item)
  if (typeof item === 'object') {
    const obj = item as Record<string, unknown>
    const pick =
      obj.name ||
      obj.rule ||
      obj.key ||
      obj.metric ||
      obj.context ||
      obj.pattern ||
      obj.spu ||
      obj.item_no ||
      obj.code ||
      obj.uri ||
      obj.spec ||
      obj.id
    if (pick) return String(pick)
    try {
      return JSON.stringify(obj)
    } catch {
      return String(obj)
    }
  }
  return String(item)
}

export function toneForDistance(distance: number): string {
  if (distance <= 20) return 'border-emerald-500/60 bg-emerald-950/30 text-emerald-200'
  if (distance <= 50) return 'border-sky-500/60 bg-sky-950/30 text-sky-200'
  if (distance <= 100) return 'border-amber-500/60 bg-amber-950/30 text-amber-200'
  return 'border-slate-600/60 bg-slate-900/50 text-slate-300'
}

export function safeEvalFormula(
  expression: string,
  vars: { qty: number; unit_price: number; factor?: number },
): { ok: boolean; value: number; error?: string } {
  const raw = String(expression || '').trim()
  if (!raw) return { ok: false, value: 0, error: '公式为空' }
  const replaced = raw
    .replace(/\bqty\b/g, String(vars.qty))
    .replace(/\bunit_price\b/g, String(vars.unit_price))
    .replace(/\bfactor\b/g, String(vars.factor ?? 1))
  if (!/^[0-9+\-*/().\s]+$/.test(replaced)) {
    return { ok: false, value: 0, error: '公式含非法字符' }
  }
  try {
    const value = Function(`"use strict"; return (${replaced});`)()
    if (!Number.isFinite(value)) return { ok: false, value: 0, error: '计算结果无效' }
    return { ok: true, value }
  } catch {
    return { ok: false, value: 0, error: '公式解析失败' }
  }
}

export function parseTimeWindow(input: unknown): { start: number; end: number } | null {
  if (!input) return null
  if (typeof input === 'string') {
    const match = input.trim().match(/(\d{1,2}:\d{2})\s*-\s*(\d{1,2}:\d{2})/)
    if (!match) return null
    const toMinutes = (text: string) => {
      const [hours, minutes] = text.split(':').map((value) => Number(value))
      if (!Number.isFinite(hours) || !Number.isFinite(minutes)) return null
      return Math.min(24 * 60 - 1, Math.max(0, hours * 60 + minutes))
    }
    const start = toMinutes(match[1])
    const end = toMinutes(match[2])
    if (start == null || end == null) return null
    return { start, end }
  }
  if (typeof input === 'object') {
    const record = input as Record<string, unknown>
    const start = String(record.start || record.begin || record.from || '').trim()
    const end = String(record.end || record.finish || record.to || '').trim()
    if (start && end) return parseTimeWindow(`${start}-${end}`)
  }
  return null
}

export function isTimeInWindow(minutes: number, window: { start: number; end: number }): boolean {
  if (window.start === window.end) return true
  if (window.start < window.end) return minutes >= window.start && minutes <= window.end
  return minutes >= window.start || minutes <= window.end
}
