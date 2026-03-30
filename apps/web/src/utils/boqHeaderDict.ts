export const DEFAULT_BOQ_HEADER_SYNONYMS: Record<string, string[]> = {
  item_code: ['子目号', '细目号', '子目编号', '细目编号', '清单编码', '清单编号', 'itemno', 'item_no', 'itemcode'],
  item_name: ['子目名称', '细目名称', '清单名称', '名称', 'name'],
  unit: ['单位', 'unit'],
  design_qty: ['设计数量', '设计工程量', '设计量', '工程量', 'designqty', 'designquantity'],
  approved_qty: ['批复数量', '批准数量', '合同数量', '合同工程量', 'approvedqty', 'approvedquantity'],
}

export function getBoqHeaderSynonyms(): Record<string, string[]> {
  if (typeof window === 'undefined') return DEFAULT_BOQ_HEADER_SYNONYMS
  const raw = window.localStorage.getItem('boq_header_synonyms')
  if (!raw) return DEFAULT_BOQ_HEADER_SYNONYMS
  try {
    const parsed = JSON.parse(raw)
    if (!parsed || typeof parsed !== 'object') return DEFAULT_BOQ_HEADER_SYNONYMS
    const out: Record<string, string[]> = {}
    for (const [key, val] of Object.entries(parsed as Record<string, unknown>)) {
      if (Array.isArray(val)) {
        out[key] = val.map((x) => String(x))
      }
    }
    return Object.keys(out).length ? out : DEFAULT_BOQ_HEADER_SYNONYMS
  } catch {
    return DEFAULT_BOQ_HEADER_SYNONYMS
  }
}

export function normalizeHeaderValue(value: string): string {
  return String(value || '')
    .replace(/^\uFEFF/, '')
    .trim()
    .toLowerCase()
    .replace(/\s+/g, '')
}

export function buildHeaderIndex(headerRow: string[], dict?: Record<string, string[]>) {
  const index: Record<string, number> = {}
  const normalized = headerRow.map((cell) => normalizeHeaderValue(cell))
  const entries = Object.entries(dict || DEFAULT_BOQ_HEADER_SYNONYMS)

  for (let i = 0; i < normalized.length; i += 1) {
    const cell = normalized[i]
    if (!cell) continue
    for (const [key, aliases] of entries) {
      if (index[key] !== undefined) continue
      if (aliases.some((alias) => normalizeHeaderValue(alias) === cell)) {
        index[key] = i
      }
    }
  }

  return index
}
