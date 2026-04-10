import Papa from 'papaparse'

import { buildHeaderIndex, getBoqHeaderSynonyms, normalizeHeaderValue } from '../../../utils/boqHeaderDict'
import { inferSpu } from './spuUtils'
import type { TreeNode } from './types'

const ITEM_NO_PATTERN = /^\d{3}(?:-[0-9A-Za-z]+)*$/

export function normalizeItemNo(value: string): string {
  let text = String(value || '').trim()
  if (!text) return ''
  text = text.replace(/[（]/g, '(').replace(/[）]/g, ')')
  text = text.replace(/\s+/g, '')
  text = text.replace(/[./]/g, '-')
  text = text.replace(/[()]+/g, '-')
  text = text.replace(/-+/g, '-').replace(/^-+/, '').replace(/-+$/, '')
  return text
}

export function toApiUri(input: string): string {
  const raw = String(input || '').trim()
  if (!raw) return ''
  return raw
}

export function toDisplayUri(input: string): string {
  const raw = String(input || '').trim()
  if (!raw) return ''
  return raw
}

export function asNum(value: unknown): number {
  const parsed = Number(String(value ?? '').replace(/,/g, '').trim())
  return Number.isFinite(parsed) ? parsed : 0
}

export function formatNumber(value: unknown, digits = 4): string {
  const numeric = asNum(value)
  if (!Number.isFinite(numeric)) return '-'
  return numeric.toLocaleString(undefined, { maximumFractionDigits: digits })
}

export function guessChapterFromFileName(name: string): string {
  const text = String(name || '')
  if (/0\s*#|0号|零号/.test(text)) return '000'
  const match = text.match(/([1-7]\d{2})\s*章/)
  if (match) return match[1]
  const plain = text.match(/([1-7]\d{2})/)
  return plain ? plain[1] : ''
}

export function defaultGroupName(code: string, depth: number): string {
  if (code === '400') return '400章'
  const label = depth === 1 ? '章' : depth === 2 ? '节' : depth === 3 ? '目' : '分项'
  return `${code}${label}`
}

export function codeSortKey(code: string): string {
  return code
    .split('-')
    .map((seg) => {
      const parsed = Number(seg)
      return Number.isFinite(parsed) ? parsed.toString().padStart(6, '0') : seg
    })
    .join('.')
}

export function formatNodeSegment(node: TreeNode): string {
  const code = String(node.code || '').trim()
  const name = String(node.name || '').trim()
  if (node.isLeaf) return `${code}${name ? ` ${name}` : ''}`.trim()
  if (name && /章|节|目|分项/.test(name)) return name
  if (name && name !== code) return `${code} ${name}`.trim()
  const depth = code.split('-').filter(Boolean).length
  return defaultGroupName(code, depth)
}

export function sanitizeGenericLabel(input: string, fallback: string): string {
  const raw = String(input || '').trim()
  if (!raw) return fallback
  if (/generic|通用/i.test(raw)) return fallback
  return raw
}

export function buildTreeFromRealtimeItems(items: Array<Record<string, unknown>>, projectUri: string): TreeNode[] {
  const normalizedProjectUri = projectUri.replace(/\/$/, '')
  const map = new Map<string, TreeNode>()

  const addOrMerge = (node: TreeNode) => {
    const old = map.get(node.code)
    if (!old) {
      map.set(node.code, node)
      return
    }
    map.set(node.code, {
      ...old,
      ...node,
      children: old.children,
      status:
        old.status === 'Settled'
          ? 'Settled'
          : node.status === 'Settled'
            ? 'Settled'
            : old.status === 'Spending' || node.status === 'Spending'
              ? 'Spending'
              : 'Genesis',
    })
  }

  for (const row of items) {
    const rawCode = String(row.item_no || '').trim()
    const code = normalizeItemNo(rawCode)
    if (!code || !ITEM_NO_PATTERN.test(code)) continue
    const name = String(row.item_name || '').trim() || rawCode || code
    const unit = String(row.unit || '').trim()
    const designQty = asNum(row.design_quantity)
    const approvedQty = asNum(row.approved_quantity)
    const contractQty = asNum((row as Record<string, unknown>).contract_quantity) || (approvedQty > 0 ? approvedQty : designQty)
    const settledQty = asNum(row.settled_quantity)
    const consumedQty = asNum((row as Record<string, unknown>).consumed_quantity)
    const effectiveQty = settledQty
    const baselineQty = approvedQty > 0 ? approvedQty : (contractQty > 0 ? contractQty : designQty)
    const status = baselineQty > 0 && effectiveQty >= baselineQty ? 'Settled' : effectiveQty > 0 ? 'Spending' : 'Genesis'
    const spu = inferSpu(code, name)
    const codeParts = code.split('-').filter(Boolean)
    const codePath = codeParts.map((_, idx) => codeParts.slice(0, idx + 1).join('-'))
    const itemUri = String(row.boq_item_uri || '').trim()
    const rootMatch = itemUri.match(/\/boq\/([^/]+)(?:\/|$)/)
    const rootCode = rootMatch ? rootMatch[1] : '400'
    const rootUri = rootMatch
      ? itemUri.slice(0, itemUri.indexOf(`/boq/${rootCode}`) + `/boq/${rootCode}`.length)
      : `${normalizedProjectUri}/boq/${rootCode}`
    const displayRootUri = toDisplayUri(rootUri)
    const uriSuffix = itemUri.startsWith(`${rootUri}/`) ? itemUri.slice(rootUri.length + 1) : ''
    const uriSegs = uriSuffix ? uriSuffix.split('/').filter(Boolean) : []
    const useUriHierarchy = uriSegs.length > 1
    const pathSegs = useUriHierarchy ? uriSegs : codePath
    if (!map.has(rootCode)) {
      map.set(rootCode, {
        code: rootCode,
        name: `${rootCode}章`,
        uri: displayRootUri,
        parent: '',
        children: [],
        isLeaf: false,
        spu: 'SPU_Group',
        unit: '',
        contractQty: 0,
        status: 'Genesis',
      })
    }

    for (let depth = 1; depth <= pathSegs.length; depth += 1) {
      const currentCode = pathSegs[depth - 1]
      const parent = depth === 1 ? (currentCode === rootCode ? '' : rootCode) : pathSegs[depth - 2]
      const isLeaf = depth === pathSegs.length
      const uri = useUriHierarchy
        ? `${displayRootUri}/${pathSegs.slice(0, depth).join('/')}`
        : depth === 1
          ? currentCode === rootCode
            ? displayRootUri
            : `${displayRootUri}/${currentCode}`
          : `${displayRootUri}/${currentCode}`
      addOrMerge({
        code: currentCode,
        name: isLeaf ? name : (map.get(currentCode)?.name || defaultGroupName(currentCode, depth)),
        uri,
        parent,
        children: map.get(currentCode)?.children || [],
        isLeaf,
        spu: isLeaf ? spu : (map.get(currentCode)?.spu || 'SPU_Group'),
        unit: isLeaf ? unit : '',
        contractQty: isLeaf ? contractQty : (map.get(currentCode)?.contractQty || 0),
        approvedQty: isLeaf ? approvedQty : (map.get(currentCode)?.approvedQty || 0),
        designQty: isLeaf ? designQty : (map.get(currentCode)?.designQty || 0),
        consumedQty: isLeaf ? consumedQty : (map.get(currentCode)?.consumedQty || 0),
        settledQty: isLeaf ? settledQty : (map.get(currentCode)?.settledQty || 0),
        status: isLeaf ? status : (map.get(currentCode)?.status || 'Genesis'),
      })

      if (parent) {
        const parentNode = map.get(parent)
        if (parentNode && !parentNode.children.includes(currentCode)) parentNode.children.push(currentCode)
      }
    }
  }

  const sorted = Array.from(map.values()).sort((a, b) => codeSortKey(a.code).localeCompare(codeSortKey(b.code)))
  for (const node of sorted) {
    node.children = node.children.sort((a, b) => codeSortKey(a).localeCompare(codeSortKey(b)))
  }
  return sorted
}

export function getFocusedExpandedCodes(nodes: TreeNode[], focusCode?: string | null): string[] {
  const byCode = new Map(nodes.map((node) => [node.code, node]))
  const expanded = new Set<string>()
  nodes.filter((node) => !node.parent && node.children.length > 0).forEach((node) => expanded.add(node.code))
  const code = String(focusCode || '').trim()
  if (!code) return Array.from(expanded)
  let current = code
  while (current) {
    const node = byCode.get(current)
    if (!node) break
    if (node.children.length > 0) expanded.add(node.code)
    current = node.parent
  }
  return Array.from(expanded)
}

export function getAllExpandedCodes(nodes: TreeNode[]): string[] {
  const expanded = new Set<string>()
  nodes.forEach((node) => {
    if (node.children.length > 0) expanded.add(node.code)
  })
  return Array.from(expanded)
}

export function mergeExpandedCodes(prev: string[], next: string[]): string[] {
  const merged = new Set<string>(prev)
  next.forEach((code) => merged.add(code))
  return Array.from(merged)
}

export function normalizeSearch(value: string): string {
  return String(value || '').trim().toLowerCase()
}

export function pickFirstLeaf(nodes: TreeNode[]): TreeNode | null {
  const leaf = nodes
    .filter((node) => node.isLeaf)
    .sort((a, b) => codeSortKey(a.code).localeCompare(codeSortKey(b.code)))[0]
  return leaf || null
}

export function parseCsv(text: string, projectUri: string, rootCode = '400', boqRootBase = ''): TreeNode[] {
  const parsed = Papa.parse<string[]>(text || '', { skipEmptyLines: true })
  const rows = Array.isArray(parsed.data) ? (parsed.data as string[][]) : []
  if (!rows.length) return []
  const dict = getBoqHeaderSynonyms()
  const header = rows.findIndex((row) => {
    const normalizedHeader = row.map((cell) => normalizeHeaderValue(cell))
    const aliases = dict.item_code || []
    return normalizedHeader.some((cell) => aliases.some((alias) => normalizeHeaderValue(alias) === cell))
  })
  if (header < 0) return []
  const idx = buildHeaderIndex(rows[header], dict)
  const idxCode = idx.item_code ?? -1
  const idxName = idx.item_name ?? -1
  const idxUnit = idx.unit ?? -1
  const idxDesign = idx.design_qty ?? -1
  const idxApproved = idx.approved_qty ?? -1
  if (idxCode < 0) return []

  const map = new Map<string, TreeNode>()
  map.set(rootCode, {
    code: rootCode,
    name: `${rootCode}章`,
    uri: `${projectUri.replace(/\/$/, '')}/boq/${rootCode}`,
    parent: '',
    children: [],
    isLeaf: false,
    spu: 'SPU_Group',
    unit: '',
    contractQty: 0,
    status: 'Genesis',
  })

  const add = (node: TreeNode) => {
    const old = map.get(node.code)
    map.set(node.code, old ? { ...old, ...node, children: old.children } : node)
  }

  for (let rowIndex = header + 1; rowIndex < rows.length; rowIndex += 1) {
    const row = rows[rowIndex]
    const rawCode = String(row[idxCode] || '').trim()
    const code = normalizeItemNo(rawCode)
    if (!code || !ITEM_NO_PATTERN.test(code)) continue
    const name = String(row[idxName] || '').trim() || rawCode || code
    const unit = idxUnit >= 0 ? String(row[idxUnit] || '').trim() : ''
    const design = idxDesign >= 0 ? asNum(row[idxDesign]) : 0
    const approved = idxApproved >= 0 ? asNum(row[idxApproved]) : 0
    const contractQty = approved > 0 ? approved : design
    const spu = inferSpu(code, name)
    const segments = code.split('-').filter(Boolean)
    for (let depth = 1; depth <= segments.length; depth += 1) {
      const currentCode = segments.slice(0, depth).join('-')
      const parent = depth === 1 ? (currentCode === rootCode ? '' : rootCode) : segments.slice(0, depth - 1).join('-')
      const basePrefix = boqRootBase ? boqRootBase.replace(/\/$/, '') : `${projectUri.replace(/\/$/, '')}/boq`
      const baseRoot = `${basePrefix}/${rootCode}`
      const uri = depth === 1 ? (currentCode === rootCode ? baseRoot : `${baseRoot}/${currentCode}`) : `${baseRoot}/${currentCode}`
      add({
        code: currentCode,
        name: depth === segments.length ? name : (map.get(currentCode)?.name || defaultGroupName(currentCode, depth)),
        uri,
        parent,
        children: map.get(currentCode)?.children || [],
        isLeaf: depth === segments.length,
        spu: depth === segments.length ? spu : (map.get(currentCode)?.spu || 'SPU_Group'),
        unit: depth === segments.length ? unit : '',
        contractQty: depth === segments.length ? contractQty : (map.get(currentCode)?.contractQty || 0),
        approvedQty: depth === segments.length ? approved : (map.get(currentCode)?.approvedQty || 0),
        designQty: depth === segments.length ? design : (map.get(currentCode)?.designQty || 0),
        settledQty: depth === segments.length ? 0 : (map.get(currentCode)?.settledQty || 0),
        status: map.get(currentCode)?.status || 'Genesis',
      })
      const parentNode = map.get(parent)
      if (parentNode && !parentNode.children.includes(currentCode)) parentNode.children.push(currentCode)
    }
  }

  const byCode = Array.from(map.values())
  const sortCode = (left: string, right: string) =>
    left.split('-').map(Number).join('.').localeCompare(right.split('-').map(Number).join('.'), undefined, { numeric: true })
  byCode.forEach((node) => {
    node.children = node.children.sort(sortCode)
  })
  return byCode.sort((a, b) => sortCode(a.code, b.code))
}
