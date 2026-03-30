
import React, { useCallback, useEffect, useMemo, useRef, useState } from 'react'
import { Card } from '../ui'
import { useProof } from '../../hooks/useApi'
import { useUIStore } from '../../store'
import { createQrSvg } from '../../utils/qrcode'
import Papa from 'papaparse'
import { buildHeaderIndex, getBoqHeaderSynonyms, normalizeHeaderValue } from '../../utils/boqHeaderDict'

type NodeStatus = 'Genesis' | 'Spending' | 'Settled'

type TreeNode = {
  code: string
  name: string
  uri: string
  parent: string
  children: string[]
  isLeaf: boolean
  spu: string
  unit: string
  contractQty: number
  consumedQty?: number
  settledQty?: number
  approvedQty?: number
  designQty?: number
  status: NodeStatus
}

type FormRow = { field: string; label: string; operator?: string; default?: string; unit?: string }

type Props = { project: { id?: string; v_uri?: string } | null }

type Evidence = {
  name: string
  url: string
  hash: string
  ntp: string
  gpsLat?: number
  gpsLng?: number
  capturedAt?: string
  exifOk?: boolean
  exifWarning?: string
}
type OfflinePacketType = 'quality.check' | 'variation.apply'

const color: Record<NodeStatus, string> = { Genesis: '#64748B', Spending: '#2563EB', Settled: '#16A34A' }
const statusLabel: Record<NodeStatus, string> = { Genesis: '起源', Spending: '进行中', Settled: '已结算' }
const OFFLINE_KEY = 'qcspec_offline_packets_v1'
const API_BASE = String(import.meta.env.VITE_API_URL || 'http://127.0.0.1:8000')

const fallbackSchema: Record<string, FormRow[]> = {
  SPU_Reinforcement: [
    { field: 'yield_strength', label: '屈服强度', operator: '>=', default: '400', unit: 'MPa' },
    { field: 'spacing_deviation', label: '间距偏差', operator: 'range', default: '-10~10', unit: 'mm' },
  ],
  SPU_Concrete: [
    { field: 'compressive_strength', label: '抗压强度', operator: '>=', default: '30', unit: 'MPa' },
    { field: 'slump', label: '坍落度', operator: 'range', default: '120~220', unit: 'mm' },
  ],
  SPU_Contract: [
    { field: 'voucher_ref', label: '合同凭证编号', operator: 'present', default: '' },
    { field: 'claimed_amount', label: '申报金额', operator: 'present', default: '', unit: 'CNY' },
  ],
  SPU_Generic400: [
    { field: 'voucher_ref', label: '凭证编号', operator: 'present', default: '' },
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
  'Yield Strength': '屈服强度',
  'Spacing Deviation': '间距偏差',
  'Cover Thickness': '保护层厚度',
  'Compressive Strength': '抗压强度',
  Slump: '坍落度',
  'Quality Index': '质量指数',
  'Contract Voucher Ref': '合同凭证编号',
  'Claimed Amount': '申报金额',
  yield_strength: '屈服强度',
  spacing_deviation: '间距偏差',
  cover_thickness: '保护层厚度',
  compressive_strength: '抗压强度',
  slump: '坍落度',
  quality_index: '质量指数',
  voucher_ref: '凭证编号',
  claimed_amount: '申报金额',
}

function _asDict(value: unknown): Record<string, unknown> {
  return value && typeof value === 'object' && !Array.isArray(value) ? (value as Record<string, unknown>) : {}
}

const normalizeMetricKey = (value: string) => String(value || '').trim().toLowerCase().replace(/[\s_-]+/g, '')
const metricLabelMapNormalized: Record<string, string> = Object.fromEntries(
  Object.entries(metricLabelMapRaw).map(([k, v]) => [normalizeMetricKey(k), v]),
)

function toChineseCompType(type: string): string {
  const key = String(type || '').trim()
  return componentTypeNameMap[key] || key || '未配置'
}

function toChineseMetricLabel(label: string, fieldKey: string): string {
  const raw = String(label || '').trim()
  if (/通用|generic/i.test(raw)) return '未绑定指标'
  const byRaw = metricLabelMapRaw[raw]
  if (byRaw) return byRaw
  const byField = metricLabelMapRaw[String(fieldKey || '').trim()]
  if (byField) return byField
  const byNormRaw = metricLabelMapNormalized[normalizeMetricKey(raw)]
  if (byNormRaw) return byNormRaw
  const byNormField = metricLabelMapNormalized[normalizeMetricKey(String(fieldKey || ''))]
  if (byNormField) return byNormField
  return raw || String(fieldKey || '未命名指标')
}

function toChineseRuleText(operator: string, threshold: string, unit: string): string {
  const op = String(operator || '').trim().toLowerCase()
  const raw = String(threshold || '-').trim()
  const normalized = raw.startsWith('range-') ? raw.replace(/^range-/i, '') : raw
  const u = String(unit || '').trim()
  if (op === 'present') return '需填写'
  if (op === 'range' || normalized.includes('~')) return `范围 ${normalized}${u ? ` ${u}` : ''}`
  const displayOp = op === '>=' ? '≥' : op === '<=' ? '≤' : operator || ''
  return `${displayOp} ${normalized}${u ? ` ${u}` : ''}`.trim()
}

function deriveNodeDisplayMeta(
  rawMeta: Record<string, unknown>,
  active: TreeNode | null,
): { unitProject: string; subdivisionProject: string } {
  const unit = String(rawMeta.unit_project || '').trim()
  const subdivision = String(rawMeta.subdivision_project || '').trim()
  if (unit || subdivision) {
    return {
      unitProject: unit || '未命名单位工程',
      subdivisionProject: subdivision || '未命名分部分项',
    }
  }
  const code = String(active?.code || '').trim()
  const name = String(active?.name || '').trim()
  const chapter = code ? code.split('-')[0] : ''
  const unitFallback = chapter ? `${chapter}章` : '单位工程未命名'
  const subdivisionFallback = code ? `${code}${name ? ` ${name}` : ''}`.trim() : (name || '分部分项未命名')
  return {
    unitProject: unitFallback,
    subdivisionProject: subdivisionFallback,
  }
}

function inferSpu(code: string, name: string) {
  const lower = String(name || '').toLowerCase()
  if (['费', '协调', '管理', '监测', '监控', '咨询', '勘察', '保险', '交通', '保通', '征迁', '补偿', '迁改', '拆除', '临时', '安全', '试验', '检验'].some((k) => name.includes(k))) {
    return 'SPU_Contract'
  }
  if (code.startsWith('403') || name.includes('钢筋') || lower.includes('rebar')) return 'SPU_Reinforcement'
  if (name.includes('混凝土') || lower.includes('concrete')) return 'SPU_Concrete'
  return 'SPU_Contract'
}

function asNum(v: unknown): number {
  const n = Number(String(v ?? '').replace(/,/g, '').trim())
  return Number.isFinite(n) ? n : 0
}

function guessChapterFromFileName(name: string): string {
  const text = String(name || '')
  if (/0\s*#|0号|零号/.test(text)) return '000'
  const match = text.match(/([1-7]\d{2})\s*章/)
  if (match) return match[1]
  const plain = text.match(/([1-7]\d{2})/)
  return plain ? plain[1] : ''
}

function detectDelimiter(line: string): string {
  const candidates = [',', '\t', '，', ';', '；']
  let best = ','
  let bestCount = -1
  for (const d of candidates) {
    const count = line.split(d).length - 1
    if (count > bestCount) {
      bestCount = count
      best = d
    }
  }
  return best
}

function splitCsv(line: string, delimiter: string): string[] {
  const out: string[] = []
  let cur = ''
  let q = false
  for (let i = 0; i < line.length; i += 1) {
    const ch = line[i]
    if (ch === '"') {
      if (q && line[i + 1] === '"') {
        cur += '"'
        i += 1
      } else q = !q
      continue
    }
    if (ch === delimiter && !q) {
      out.push(cur)
      cur = ''
      continue
    }
    cur += ch
  }
  out.push(cur)
  return out
}

function defaultGroupName(code: string, depth: number): string {
  if (code === '400') return '400章'
  const label = depth === 1 ? '章' : depth === 2 ? '节' : depth === 3 ? '目' : '分项'
  return `${code}${label}`
}

function codeSortKey(code: string): string {
  return code
    .split('-')
    .map((seg) => {
      const n = Number(seg)
      return Number.isFinite(n) ? n.toString().padStart(6, '0') : seg
    })
    .join('.')
}

function formatNodeSegment(node: TreeNode): string {
  const code = String(node.code || '').trim()
  const name = String(node.name || '').trim()
  if (node.isLeaf) return `${code}${name ? ` ${name}` : ''}`.trim()
  if (name && /章|节|目|分项/.test(name)) return name
  if (name && name !== code) return `${code} ${name}`.trim()
  const depth = code.split('-').filter(Boolean).length
  return defaultGroupName(code, depth)
}

function sanitizeGenericLabel(input: string, fallback: string): string {
  const raw = String(input || '').trim()
  if (!raw) return fallback
  if (/generic|通用/i.test(raw)) return fallback
  return raw
}

function buildTreeFromRealtimeItems(items: Array<Record<string, unknown>>, projectUri: string): TreeNode[] {
  const p = projectUri.replace(/\/$/, '')
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
      status: old.status === 'Settled' ? 'Settled' : node.status === 'Settled' ? 'Settled' : (old.status === 'Spending' || node.status === 'Spending') ? 'Spending' : 'Genesis',
    })
  }

  for (const row of items) {
    const code = String(row.item_no || '').trim()
    if (!/^\d{3}(?:-\d+)*$/.test(code)) continue
    const name = String(row.item_name || '').trim() || code
    const unit = String(row.unit || '').trim()
    const designQty = asNum(row.design_quantity)
    const approvedQty = asNum(row.approved_quantity)
    const contractQty = approvedQty > 0 ? approvedQty : designQty
    const settledQty = asNum(row.settled_quantity)
    const consumedQty = asNum((row as Record<string, unknown>).consumed_quantity)
    const effectiveQty = consumedQty > 0 ? consumedQty : settledQty
    const status: NodeStatus = designQty > 0 && effectiveQty >= designQty ? 'Settled' : effectiveQty > 0 ? 'Spending' : 'Genesis'
    const spu = inferSpu(code, name)
    const segs = code.split('-').filter(Boolean)
    const itemUri = String(row.boq_item_uri || '').trim()
    const rootMatch = itemUri.match(/\/boq\/([^/]+)(?:\/|$)/)
    const rootCode = rootMatch ? rootMatch[1] : '400'
    const rootUri = rootMatch ? itemUri.slice(0, itemUri.indexOf(`/boq/${rootCode}`) + `/boq/${rootCode}`.length) : `${p}/boq/${rootCode}`
    if (!map.has(rootCode)) {
      map.set(rootCode, {
        code: rootCode,
        name: `${rootCode}章`,
        uri: rootUri,
        parent: '',
        children: [],
        isLeaf: false,
        spu: 'SPU_Generic400',
        unit: '',
        contractQty: 0,
        status: 'Genesis',
      })
    }

    for (let d = 1; d <= segs.length; d += 1) {
      const c = segs.slice(0, d).join('-')
      const parent = d === 1 ? (c === rootCode ? '' : rootCode) : segs.slice(0, d - 1).join('-')
      const isLeaf = d === segs.length
      addOrMerge({
        code: c,
        name: isLeaf ? name : (map.get(c)?.name || defaultGroupName(c, d)),
        uri: d === 1 ? `${rootUri}` : `${rootUri}/${c}`,
        parent,
        children: map.get(c)?.children || [],
        isLeaf,
        spu: isLeaf ? spu : (map.get(c)?.spu || 'SPU_Generic400'),
        unit: isLeaf ? unit : '',
        contractQty: isLeaf ? contractQty : (map.get(c)?.contractQty || 0),
        approvedQty: isLeaf ? approvedQty : (map.get(c)?.approvedQty || 0),
        designQty: isLeaf ? designQty : (map.get(c)?.designQty || 0),
        consumedQty: isLeaf ? consumedQty : (map.get(c)?.consumedQty || 0),
        settledQty: isLeaf ? settledQty : (map.get(c)?.settledQty || 0),
        status: isLeaf ? status : (map.get(c)?.status || 'Genesis'),
      })

      if (parent) {
        const parentNode = map.get(parent)
        if (parentNode && !parentNode.children.includes(c)) parentNode.children.push(c)
      }
    }
  }

  const sorted = Array.from(map.values()).sort((a, b) => codeSortKey(a.code).localeCompare(codeSortKey(b.code)))
  for (const node of sorted) {
    node.children = node.children.sort((a, b) => codeSortKey(a).localeCompare(codeSortKey(b)))
  }
  return sorted
}

function getExpandableCodes(nodes: TreeNode[]): string[] {
  return nodes.filter((n) => n.children.length > 0).map((n) => n.code)
}

function getFocusedExpandedCodes(nodes: TreeNode[], focusCode?: string | null): string[] {
  const byCode = new Map(nodes.map((n) => [n.code, n]))
  const expanded = new Set<string>()
  nodes.filter((n) => !n.parent && n.children.length > 0).forEach((n) => expanded.add(n.code))
  const code = String(focusCode || '').trim()
  if (!code) return Array.from(expanded)
  let cur = code
  while (cur) {
    const n = byCode.get(cur)
    if (!n) break
    if (n.children.length > 0) expanded.add(n.code)
    cur = n.parent
  }
  return Array.from(expanded)
}

function normalizeSearch(value: string): string {
  return String(value || '').trim().toLowerCase()
}

function pickFirstLeaf(nodes: TreeNode[]): TreeNode | null {
  const leaf = nodes.filter((n) => n.isLeaf).sort((a, b) => codeSortKey(a.code).localeCompare(codeSortKey(b.code)))[0]
  return leaf || null
}

function parseCsv(text: string, projectUri: string, rootCode = '400'): TreeNode[] {
  const parsed = Papa.parse<string[]>(text || '', { skipEmptyLines: true })
  const rows = Array.isArray(parsed.data) ? (parsed.data as string[][]) : []
  if (!rows.length) return []
  const dict = getBoqHeaderSynonyms()
  const header = rows.findIndex((r) => {
    const h = r.map((cell) => normalizeHeaderValue(cell))
    const aliases = dict.item_code || []
    return h.some((cell) => aliases.some((alias) => normalizeHeaderValue(alias) === cell))
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
  map.set(rootCode, { code: rootCode, name: `${rootCode}章`, uri: `${projectUri.replace(/\/$/, '')}/boq/${rootCode}`, parent: '', children: [], isLeaf: false, spu: 'SPU_Generic400', unit: '', contractQty: 0, status: 'Genesis' })

  const add = (node: TreeNode) => {
    const old = map.get(node.code)
    map.set(node.code, old ? { ...old, ...node, children: old.children } : node)
  }

  for (let i = header + 1; i < rows.length; i += 1) {
    const r = rows[i]
    const code = String(r[idxCode] || '').trim()
    if (!/^\d{3}(?:-\d+)*$/.test(code)) continue
    const name = String(r[idxName] || '').trim() || code
    const unit = idxUnit >= 0 ? String(r[idxUnit] || '').trim() : ''
    const design = idxDesign >= 0 ? asNum(r[idxDesign]) : 0
    const approved = idxApproved >= 0 ? asNum(r[idxApproved]) : 0
    const contractQty = approved > 0 ? approved : design
    const spu = inferSpu(code, name)
    const segs = code.split('-').filter(Boolean)
    for (let d = 1; d <= segs.length; d += 1) {
      const c = segs.slice(0, d).join('-')
      const p = d === 1 ? (c === rootCode ? '' : rootCode) : segs.slice(0, d - 1).join('-')
      add({ code: c, name: d === segs.length ? name : (map.get(c)?.name || defaultGroupName(c, d)), uri: d === 1 ? `${projectUri.replace(/\/$/, '')}/boq/${rootCode}` : `${projectUri.replace(/\/$/, '')}/boq/${rootCode}/${c}`, parent: p, children: map.get(c)?.children || [], isLeaf: d === segs.length, spu: d === segs.length ? spu : (map.get(c)?.spu || 'SPU_Generic400'), unit: d === segs.length ? unit : '', contractQty: d === segs.length ? contractQty : (map.get(c)?.contractQty || 0), approvedQty: d === segs.length ? approved : (map.get(c)?.approvedQty || 0), designQty: d === segs.length ? design : (map.get(c)?.designQty || 0), settledQty: d === segs.length ? 0 : (map.get(c)?.settledQty || 0), status: map.get(c)?.status || 'Genesis' })
      const parent = map.get(p)
      if (parent && !parent.children.includes(c)) parent.children.push(c)
    }
  }

  const byCode = Array.from(map.values())
  const sortCode = (a: string, b: string) => a.split('-').map(Number).join('.').localeCompare(b.split('-').map(Number).join('.'), undefined, { numeric: true })
  byCode.forEach((x) => (x.children = x.children.sort(sortCode)))
  return byCode.sort((a, b) => sortCode(a.code, b.code))
}

function evalNorm(op: string, threshold: string, value: string): 'pending' | 'success' | 'fail' {
  const n = Number(value)
  if (String(op || '').trim().toLowerCase() === 'present') {
    return String(value || '').trim() ? 'success' : 'pending'
  }
  if (!Number.isFinite(n)) return 'pending'
  const t = String(threshold || '').trim()
  if (t.includes('~')) {
    const [a, b] = t.split('~').map((x) => Number(x.trim()))
    if (Number.isFinite(a) && Number.isFinite(b)) return n >= Math.min(a, b) && n <= Math.max(a, b) ? 'success' : 'fail'
    return 'pending'
  }
  const x = Number(t)
  if (!Number.isFinite(x)) return 'pending'
  if (op === '>=') return n >= x ? 'success' : 'fail'
  if (op === '<=') return n <= x ? 'success' : 'fail'
  return n === x ? 'success' : 'fail'
}

function sanitizeMeasuredInput(raw: string): string {
  const text = String(raw || '').replace(/,/g, '').trim()
  if (!text) return ''
  const match = text.match(/[-+]?\d*\.?\d+/)
  return match ? match[0] : ''
}

async function shaBuffer(buf: ArrayBuffer) {
  const digest = await crypto.subtle.digest('SHA-256', buf)
  return Array.from(new Uint8Array(digest)).map((b) => b.toString(16).padStart(2, '0')).join('')
}

async function sha(file: File) {
  const buf = await file.arrayBuffer()
  return shaBuffer(buf)
}

async function shaJson(payload: Record<string, unknown>) {
  const raw = JSON.stringify(payload)
  const buf = new TextEncoder().encode(raw)
  const digest = await crypto.subtle.digest('SHA-256', buf)
  return Array.from(new Uint8Array(digest)).map((b) => b.toString(16).padStart(2, '0')).join('')
}

async function sha256Hex(input: string) {
  const buf = new TextEncoder().encode(input)
  const digest = await crypto.subtle.digest('SHA-256', buf)
  return Array.from(new Uint8Array(digest)).map((b) => b.toString(16).padStart(2, '0')).join('')
}

function formatExifDate(raw: string): string {
  const text = String(raw || '').trim()
  if (!text) return ''
  const normalized = text.replace(/^(\d{4}):(\d{2}):(\d{2})/, '$1-$2-$3')
  const dt = new Date(normalized)
  if (!Number.isFinite(dt.getTime())) return text
  return dt.toISOString()
}

function readExifValue(
  view: DataView,
  entryOffset: number,
  little: boolean,
): { tag: number; type: number; count: number; valueOffset: number } {
  const tag = view.getUint16(entryOffset, little)
  const type = view.getUint16(entryOffset + 2, little)
  const count = view.getUint32(entryOffset + 4, little)
  const valueOffset = view.getUint32(entryOffset + 8, little)
  return { tag, type, count, valueOffset }
}

function exifTypeSize(type: number): number {
  if (type === 1 || type === 2 || type === 7) return 1
  if (type === 3) return 2
  if (type === 4 || type === 9) return 4
  if (type === 5 || type === 10) return 8
  return 0
}

function readExifAscii(view: DataView, offset: number, count: number): string {
  let out = ''
  for (let i = 0; i < count; i += 1) {
    const c = view.getUint8(offset + i)
    if (c === 0) break
    out += String.fromCharCode(c)
  }
  return out
}

function readExifRational(view: DataView, offset: number, little: boolean, signed = false): number {
  const num = signed ? view.getInt32(offset, little) : view.getUint32(offset, little)
  const den = signed ? view.getInt32(offset + 4, little) : view.getUint32(offset + 4, little)
  if (!den) return 0
  return num / den
}

function readExifTagValue(
  view: DataView,
  tiffStart: number,
  entryOffset: number,
  type: number,
  count: number,
  valueOffset: number,
  little: boolean,
): string | number | number[] {
  const size = exifTypeSize(type) * count
  const offset = size <= 4 ? entryOffset + 8 : tiffStart + valueOffset
  const valueInline = size <= 4 ? view.getUint32(entryOffset + 8, little) : 0

  if (type === 2) {
    if (size <= 4) {
      const bytes = new Uint8Array([
        valueInline & 0xff,
        (valueInline >> 8) & 0xff,
        (valueInline >> 16) & 0xff,
        (valueInline >> 24) & 0xff,
      ])
      return String.fromCharCode(...bytes).replace(/\0+$/, '')
    }
    return readExifAscii(view, offset, count)
  }
  if (type === 3) {
    if (count === 1) {
      return size <= 4 ? (little ? (valueInline & 0xffff) : (valueInline >> 16)) : view.getUint16(offset, little)
    }
    const arr: number[] = []
    for (let i = 0; i < count; i += 1) arr.push(view.getUint16(offset + i * 2, little))
    return arr
  }
  if (type === 4) {
    if (count === 1) return size <= 4 ? valueInline : view.getUint32(offset, little)
    const arr: number[] = []
    for (let i = 0; i < count; i += 1) arr.push(view.getUint32(offset + i * 4, little))
    return arr
  }
  if (type === 5) {
    const arr: number[] = []
    for (let i = 0; i < count; i += 1) arr.push(readExifRational(view, offset + i * 8, little))
    return count === 1 ? arr[0] : arr
  }
  if (type === 9) {
    if (count === 1) return size <= 4 ? (valueInline | 0) : view.getInt32(offset, little)
  }
  if (type === 10) {
    const arr: number[] = []
    for (let i = 0; i < count; i += 1) arr.push(readExifRational(view, offset + i * 8, little, true))
    return count === 1 ? arr[0] : arr
  }
  if (type === 1 || type === 7) {
    if (count === 1) return size <= 4 ? (valueInline & 0xff) : view.getUint8(offset)
  }
  return ''
}

function parseExifFromJpeg(buffer: ArrayBuffer): { lat?: number; lng?: number; capturedAt?: string; warning?: string; ok: boolean } {
  const view = new DataView(buffer)
  if (view.byteLength < 4 || view.getUint16(0, false) !== 0xffd8) {
    return { ok: false, warning: '非 JPEG，无法解析 EXIF' }
  }
  let offset = 2
  while (offset + 4 < view.byteLength) {
    if (view.getUint8(offset) !== 0xff) break
    const marker = view.getUint8(offset + 1)
    const size = view.getUint16(offset + 2, false)
    if (marker === 0xe1) {
      const header = String.fromCharCode(
        view.getUint8(offset + 4),
        view.getUint8(offset + 5),
        view.getUint8(offset + 6),
        view.getUint8(offset + 7),
        view.getUint8(offset + 8),
        view.getUint8(offset + 9),
      )
      if (header === 'Exif\u0000\u0000') {
        const tiffStart = offset + 10
        const endian = view.getUint16(tiffStart, false)
        const little = endian === 0x4949
        const firstIfdOffset = view.getUint32(tiffStart + 4, little)
        let exifIfdOffset = 0
        let gpsIfdOffset = 0
        let dateTime = ''

        const ifd0Offset = tiffStart + firstIfdOffset
        const ifd0Entries = view.getUint16(ifd0Offset, little)
        for (let i = 0; i < ifd0Entries; i += 1) {
          const entryOffset = ifd0Offset + 2 + i * 12
          const { tag, type, count, valueOffset } = readExifValue(view, entryOffset, little)
          if (tag === 0x8769) exifIfdOffset = valueOffset
          if (tag === 0x8825) gpsIfdOffset = valueOffset
          if (tag === 0x0132) {
            const val = readExifTagValue(view, tiffStart, entryOffset, type, count, valueOffset, little)
            if (typeof val === 'string') dateTime = val
          }
        }

        let dateTimeOriginal = ''
        if (exifIfdOffset) {
          const exifOffset = tiffStart + exifIfdOffset
          const exifEntries = view.getUint16(exifOffset, little)
          for (let i = 0; i < exifEntries; i += 1) {
            const entryOffset = exifOffset + 2 + i * 12
            const { tag, type, count, valueOffset } = readExifValue(view, entryOffset, little)
            if (tag === 0x9003 || tag === 0x9004) {
              const val = readExifTagValue(view, tiffStart, entryOffset, type, count, valueOffset, little)
              if (typeof val === 'string') dateTimeOriginal = val
            }
          }
        }

        let lat: number | undefined
        let lng: number | undefined
        let gpsDate = ''
        let gpsTime: number[] | null = null
        let latRef = ''
        let lngRef = ''
        if (gpsIfdOffset) {
          const gpsOffset = tiffStart + gpsIfdOffset
          const gpsEntries = view.getUint16(gpsOffset, little)
          for (let i = 0; i < gpsEntries; i += 1) {
            const entryOffset = gpsOffset + 2 + i * 12
            const { tag, type, count, valueOffset } = readExifValue(view, entryOffset, little)
            const val = readExifTagValue(view, tiffStart, entryOffset, type, count, valueOffset, little)
            if (tag === 0x0001 && typeof val === 'string') latRef = val.trim()
            if (tag === 0x0003 && typeof val === 'string') lngRef = val.trim()
            if (tag === 0x0002 && Array.isArray(val)) {
              const [d, m, s] = val as number[]
              lat = d + m / 60 + s / 3600
            }
            if (tag === 0x0004 && Array.isArray(val)) {
              const [d, m, s] = val as number[]
              lng = d + m / 60 + s / 3600
            }
            if (tag === 0x001d && typeof val === 'string') gpsDate = val.trim()
            if (tag === 0x0007 && Array.isArray(val)) gpsTime = val as number[]
          }
        }

        if (lat != null && /S/i.test(latRef)) lat = -Math.abs(lat)
        if (lng != null && /W/i.test(lngRef)) lng = -Math.abs(lng)

        let capturedAt = ''
        if (dateTimeOriginal) capturedAt = formatExifDate(dateTimeOriginal)
        else if (dateTime) capturedAt = formatExifDate(dateTime)
        if (!capturedAt && gpsDate && gpsTime && gpsTime.length >= 2) {
          const [h, m, s = 0] = gpsTime
          const iso = `${gpsDate.replace(/:/g, '-') || gpsDate} ${String(h).padStart(2, '0')}:${String(m).padStart(2, '0')}:${String(Math.floor(s)).padStart(2, '0')}`
          capturedAt = formatExifDate(iso)
        }

        const ok = !!(lat != null && lng != null && capturedAt)
        const warning = ok ? '' : 'EXIF 信息不完整'
        return { lat, lng, capturedAt, ok, warning }
      }
    }
    offset += 2 + size
  }
  return { ok: false, warning: '未检测到 EXIF' }
}

function haversineMeters(lat1: number, lng1: number, lat2: number, lng2: number): number {
  const toRad = (x: number) => (x * Math.PI) / 180
  const dLat = toRad(lat2 - lat1)
  const dLng = toRad(lng2 - lng1)
  const a =
    Math.sin(dLat / 2) ** 2 +
    Math.cos(toRad(lat1)) * Math.cos(toRad(lat2)) * Math.sin(dLng / 2) ** 2
  return 2 * 6371000 * Math.asin(Math.sqrt(a))
}

function extractNodeGeo(meta: Record<string, unknown>): { lat: number; lng: number; radiusM: number } | null {
  const pickNum = (v: unknown) => (Number.isFinite(Number(v)) ? Number(v) : null)
  const lat = pickNum(meta.gps_lat) ?? pickNum(meta.lat) ?? pickNum((meta.geo_location as Record<string, unknown> | undefined)?.lat) ?? pickNum((meta.coordinate as Record<string, unknown> | undefined)?.lat)
  const lng = pickNum(meta.gps_lng) ?? pickNum(meta.lng) ?? pickNum((meta.geo_location as Record<string, unknown> | undefined)?.lng) ?? pickNum((meta.coordinate as Record<string, unknown> | undefined)?.lng)
  if (lat == null || lng == null) return null
  const radiusM = pickNum(meta.geo_radius_m) ?? pickNum(meta.radius_m) ?? 150
  return { lat, lng, radiusM }
}

function downloadJson(filename: string, data: unknown) {
  const payload = JSON.stringify(data, null, 2)
  const blob = new Blob([payload], { type: 'application/json' })
  const url = URL.createObjectURL(blob)
  const a = document.createElement('a')
  a.href = url
  a.download = filename
  document.body.appendChild(a)
  a.click()
  a.remove()
  URL.revokeObjectURL(url)
}

type MerkleStep = {
  depth: number
  position: string
  sibling_hash: string
  combined_hash: string
}

type ReadinessLayer = {
  key: string
  name: string
  status: 'complete' | 'partial' | 'missing' | string
  metrics?: Record<string, unknown>
}

type ReadinessPayload = {
  ok?: boolean
  overall_status?: 'complete' | 'partial' | 'missing' | string
  readiness_percent?: number
  layers?: ReadinessLayer[]
}

type RolePlaybook = {
  role: string
  title: string
  goal: string
  actions: string[]
  constraints: string[]
  chain: string
}

const ROLE_PLAYBOOK: RolePlaybook[] = [
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

export default function SovereignWorkbenchPanel({ project }: Props) {
  const projectUri = String(project?.v_uri || '')
  const projectId = String(project?.id || '')
  const { showToast } = useUIStore()
  const {
    smuImportGenesis,
    smuImportGenesisAsync,
    smuImportGenesisPreview,
    smuImportGenesisJobPublic,
    smuImportGenesisJobActivePublic,
    smuNodeContext,
    smuExecute,
    smuSign,
    smuFreeze,
    boqRealtimeStatus,
    applyVariationDelta,
    scanConfirmSignature,
    replayOfflinePackets,
    unitMerkleRoot,
    projectReadinessCheck,
  } = useProof()

  const boqFileRef = useRef<HTMLInputElement | null>(null)
  const evidenceFileRef = useRef<HTMLInputElement | null>(null)
  const offlineImportRef = useRef<HTMLInputElement | null>(null)
  const contextReqSeqRef = useRef(0)
  const autoRejectRef = useRef('')

  const [file, setFile] = useState<File | null>(null)
  const [fileName, setFileName] = useState('')
  const [importing, setImporting] = useState(false)
  const [importJobId, setImportJobId] = useState('')
  const [importProgress, setImportProgress] = useState(0)
  const [importStatusText, setImportStatusText] = useState('')
  const [importError, setImportError] = useState('')
  const [asyncImportSupported, setAsyncImportSupported] = useState<boolean | null>(null)
  const [readinessLoading, setReadinessLoading] = useState(false)
  const [readiness, setReadiness] = useState<ReadinessPayload | null>(null)
  const [showRolePlaybook, setShowRolePlaybook] = useState(false)
  const [showLeftSummary, setShowLeftSummary] = useState(false)
  const [nodes, setNodes] = useState<TreeNode[]>([])
  const [expandedCodes, setExpandedCodes] = useState<string[]>([])
  const [activeUri, setActiveUri] = useState('')
  const [treeQuery, setTreeQuery] = useState('')
  const [ctx, setCtx] = useState<Record<string, unknown> | null>(null)
  const [loadingCtx, setLoadingCtx] = useState(false)
  const [contextError, setContextError] = useState('')
  const [form, setForm] = useState<Record<string, string>>({})
  const [compType, setCompType] = useState('generic')
  const [sampleId, setSampleId] = useState('')
  const [claimQty, setClaimQty] = useState('')

  const [executorDid, setExecutorDid] = useState('did:qcspec:contractor:demo')
  const [supervisorDid, setSupervisorDid] = useState('did:qcspec:supervisor:demo')
  const [ownerDid, setOwnerDid] = useState('did:qcspec:owner:demo')
  const [lat, setLat] = useState('30.657')
  const [lng, setLng] = useState('104.065')

  const [evidence, setEvidence] = useState<Evidence[]>([])
  const [evidenceName, setEvidenceName] = useState('')
  const [evidenceOpen, setEvidenceOpen] = useState(false)
  const [evidenceFocus, setEvidenceFocus] = useState<Evidence | null>(null)
  const [hashing, setHashing] = useState(false)
  const [executing, setExecuting] = useState(false)
  const [rejecting, setRejecting] = useState(false)
  const [execRes, setExecRes] = useState<Record<string, unknown> | null>(null)
  const [signOpen, setSignOpen] = useState(false)
  const [signStep, setSignStep] = useState(0)
  const [signing, setSigning] = useState(false)
  const [signRes, setSignRes] = useState<Record<string, unknown> | null>(null)
  const [freezeProof, setFreezeProof] = useState('')
  const [deltaAmount, setDeltaAmount] = useState('')
  const [deltaReason, setDeltaReason] = useState('变更指令')
  const [applyingDelta, setApplyingDelta] = useState(false)
  const [variationRes, setVariationRes] = useState<Record<string, unknown> | null>(null)
  const [scanPayload, setScanPayload] = useState('')
  const [scanDid, setScanDid] = useState('did:qcspec:supervisor:demo')
  const [scanProofId, setScanProofId] = useState('')
  const [scanRes, setScanRes] = useState<Record<string, unknown> | null>(null)
  const [scanning, setScanning] = useState(false)
  const [offlinePackets, setOfflinePackets] = useState<Record<string, unknown>[]>([])
  const [offlineType, setOfflineType] = useState<OfflinePacketType>('quality.check')
  const [offlineReplay, setOfflineReplay] = useState<Record<string, unknown> | null>(null)
  const [offlineStopOnError, setOfflineStopOnError] = useState(true)
  const [offlineReplaying, setOfflineReplaying] = useState(false)
  const [offlineImporting, setOfflineImporting] = useState(false)
  const [offlineImportName, setOfflineImportName] = useState('')
  const [unitCode, setUnitCode] = useState('')
  const [unitProofId, setUnitProofId] = useState('')
  const [unitMaxRows, setUnitMaxRows] = useState('20000')
  const [unitRes, setUnitRes] = useState<Record<string, unknown> | null>(null)
  const [unitLoading, setUnitLoading] = useState(false)
  const [unitVerifying, setUnitVerifying] = useState(false)
  const [itemRootComputed, setItemRootComputed] = useState('')
  const [unitLeafComputed, setUnitLeafComputed] = useState('')
  const [projectRootComputed, setProjectRootComputed] = useState('')
  const [unitVerifyMsg, setUnitVerifyMsg] = useState('')
  const [itemPathSteps, setItemPathSteps] = useState<MerkleStep[]>([])
  const [unitPathSteps, setUnitPathSteps] = useState<MerkleStep[]>([])
  const [copiedMsg, setCopiedMsg] = useState('')
  const [traceOpen, setTraceOpen] = useState(false)
  const [docModalOpen, setDocModalOpen] = useState(false)
  const aliveRef = useRef(true)
  const resumedProjectRef = useRef('')
  const [showAdvancedExecution, setShowAdvancedExecution] = useState(false)
  const [showAdvancedConsensus, setShowAdvancedConsensus] = useState(false)

  useEffect(() => () => evidence.forEach((x) => URL.revokeObjectURL(x.url)), [evidence])
  useEffect(() => {
    aliveRef.current = true
    return () => { aliveRef.current = false }
  }, [])
  useEffect(() => {
    if (typeof window === 'undefined') return
    try {
      const raw = window.localStorage.getItem(OFFLINE_KEY)
      if (!raw) return
      const parsed = JSON.parse(raw)
      if (Array.isArray(parsed)) setOfflinePackets(parsed)
    } catch {
      setOfflinePackets([])
    }
  }, [])

  const runReadinessCheck = useCallback(async (silent = false) => {
    if (!projectUri) return
    setReadinessLoading(true)
    try {
      const payload = await projectReadinessCheck(projectUri) as ReadinessPayload | null
      if (!payload) {
        if (!silent) showToast('体检接口无响应')
        return
      }
      setReadiness(payload)
      if (!silent) {
        const percent = Number(payload.readiness_percent || 0)
        showToast(`闭环体检完成：${percent.toFixed(2)}%`)
      }
    } finally {
      setReadinessLoading(false)
    }
  }, [projectReadinessCheck, projectUri, showToast])

  useEffect(() => {
    if (!projectUri) return
    void runReadinessCheck(true)
  }, [projectUri, runReadinessCheck])

  const byUri = useMemo(() => new Map(nodes.map((x) => [x.uri, x])), [nodes])
  const byCode = useMemo(() => new Map(nodes.map((x) => [x.code, x])), [nodes])
  const roots = useMemo(() => nodes.filter((x) => !x.parent).map((x) => x.code), [nodes])
  const active = useMemo(() => byUri.get(activeUri) || null, [activeUri, byUri])
  const aggMap = useMemo(() => {
    const memo = new Map<string, { contract: number; approved: number; design: number; settled: number; consumed: number }>()
    const walk = (code: string): { contract: number; approved: number; design: number; settled: number; consumed: number } => {
      if (memo.has(code)) return memo.get(code) as { contract: number; approved: number; design: number; settled: number; consumed: number }
      const n = byCode.get(code)
      if (!n) return { contract: 0, approved: 0, design: 0, settled: 0, consumed: 0 }
      if (n.isLeaf) {
        const settled = Number.isFinite(n.settledQty as number) ? (n.settledQty as number) : 0
        const consumed = Number.isFinite(n.consumedQty as number) ? (n.consumedQty as number) : 0
        const contract = Number.isFinite(n.contractQty) ? n.contractQty : 0
        const approved = Number.isFinite(n.approvedQty as number) ? (n.approvedQty as number) : 0
        const design = Number.isFinite(n.designQty as number) ? (n.designQty as number) : 0
        const agg = { contract, approved, design, settled, consumed }
        memo.set(code, agg)
        return agg
      }
      const agg = n.children.reduce(
        (acc, child) => {
          const p = walk(child)
          return {
            contract: acc.contract + p.contract,
            approved: acc.approved + p.approved,
            design: acc.design + p.design,
            settled: acc.settled + p.settled,
            consumed: acc.consumed + p.consumed,
          }
        },
        { contract: 0, approved: 0, design: 0, settled: 0, consumed: 0 },
      )
      memo.set(code, agg)
      return agg
    }
    nodes.forEach((n) => walk(n.code))
    return memo
  }, [byCode, nodes])
  const treeSearch = useMemo(() => {
    const q = normalizeSearch(treeQuery)
    if (!q) {
      return { active: false, visible: new Set<string>(), expanded: [] as string[], matched: [] as TreeNode[] }
    }
    const matched = nodes.filter((n) => {
      const code = normalizeSearch(n.code)
      const name = normalizeSearch(n.name)
      return code.includes(q) || name.includes(q)
    })
    const visible = new Set<string>()
    matched.forEach((n) => {
      visible.add(n.code)
      let parent = n.parent
      while (parent) {
        visible.add(parent)
        parent = byCode.get(parent)?.parent || ''
      }
    })
    if (byCode.get('400')) visible.add('400')
    const expanded = Array.from(visible).filter((code) => {
      const node = byCode.get(code)
      if (!node) return false
      return node.children.some((child) => visible.has(child))
    })
    return { active: true, visible, expanded, matched }
  }, [byCode, nodes, treeQuery])
  const visibleRoots = useMemo(() => {
    if (!treeSearch.active) return roots
    return roots.filter((r) => treeSearch.visible.has(r))
  }, [roots, treeSearch.active, treeSearch.visible])
  const boundSpu = useMemo(() => {
    const spuNode = _asDict(ctx?.node as Record<string, unknown>)
    const spuMeta = _asDict(ctx?.spu as Record<string, unknown>)
    return String(spuMeta.spu_code || spuMeta.spu_type || spuNode.spu || active?.spu || '').trim()
  }, [active?.spu, ctx])
  const isContractSpu = useMemo(() => {
    const s = String(boundSpu || '').toLowerCase()
    return s === 'spu_contract' || s.includes('contract') || s.includes('voucher')
  }, [boundSpu])
  const nodePathMap = useMemo(() => {
    const map = new Map<string, string>()
    const base = String(projectUri || '').replace(/\/$/, '')
    const build = (code: string): string => {
      if (map.has(code)) return map.get(code) as string
      const node = byCode.get(code)
      if (!node) return ''
      const seg = formatNodeSegment(node)
      const parentPath = node.parent ? build(node.parent) : base
      const path = parentPath ? `${parentPath}/${seg}` : seg
      map.set(code, path)
      return path
    }
    nodes.forEach((n) => build(n.code))
    return map
  }, [byCode, nodes, projectUri])
  const activePath = useMemo(() => {
    if (!active) return ''
    return nodePathMap.get(active.code) || active.uri
  }, [active, nodePathMap])

  const formSchema = useMemo<FormRow[]>(() => {
    const s = (ctx?.spu || {}) as Record<string, unknown>
    const apiRows = Array.isArray(s.spu_form_schema) ? (s.spu_form_schema as FormRow[]) : []
    if (apiRows.length) return apiRows
    if (isContractSpu) return fallbackSchema.SPU_Contract
    return []
  }, [ctx, isContractSpu])

  const inputProofId = useMemo(() => {
    const t = (ctx?.trip || {}) as Record<string, unknown>
    const n = (ctx?.node || {}) as Record<string, unknown>
    const r = (execRes?.trip || {}) as Record<string, unknown>
    return String(r.output_proof_id || t.input_proof_id || n.proof_id || '')
  }, [ctx, execRes])

  const verifyUri = useMemo(() => String(((signRes?.docpeg || {}) as Record<string, unknown>).verify_uri || ''), [signRes])
  const pdfB64 = useMemo(() => String(((signRes?.docpeg || {}) as Record<string, unknown>).pdf_preview_b64 || ''), [signRes])
  const totalHash = useMemo(() => String(((signRes?.trip || {}) as Record<string, unknown>).total_proof_hash || ''), [signRes])
  const scanConfirmUri = useMemo(() => String(((signRes?.docpeg || {}) as Record<string, unknown>).scan_confirm_uri || ''), [signRes])
  const scanConfirmToken = useMemo(() => String(((signRes?.docpeg || {}) as Record<string, unknown>).scan_confirm_token || ''), [signRes])
  const persistOfflinePackets = useCallback((next: Record<string, unknown>[]) => {
    setOfflinePackets(next)
    if (typeof window === 'undefined') return
    window.localStorage.setItem(OFFLINE_KEY, JSON.stringify(next))
  }, [])

  const summary = useMemo(() => {
    if (!active) return { contract: 0, approved: 0, design: 0, settled: 0, consumed: 0, pct: 0 }
    const x = aggMap.get(active.code) || { contract: 0, approved: 0, design: 0, settled: 0, consumed: 0 }
    const effective = x.consumed > 0 ? x.consumed : x.settled
    const baseline = x.design > 0 ? x.design : x.contract
    return {
      contract: x.contract,
      approved: x.approved,
      design: x.design,
      settled: x.settled,
      consumed: x.consumed,
      pct: baseline > 0 ? (effective * 100) / baseline : 0,
    }
  }, [active, aggMap])

  const gateStats = useMemo(() => {
    const total = formSchema.length
    let pass = 0
    let fail = 0
    let pending = 0
    for (let i = 0; i < formSchema.length; i += 1) {
      const row = formSchema[i]
      const k = String(row.field || `f_${i}`)
      const st = evalNorm(String(row.operator || ''), String(row.default || ''), form[k] || '')
      if (st === 'success') pass += 1
      else if (st === 'fail') fail += 1
      else pending += 1
    }
    const qcStatus = total === 0 ? '未配置' : (fail > 0 ? '不合格' : pending > 0 ? '待检' : '合格')
    const labNode = _asDict((ctx?.node || {}) as Record<string, unknown>).lab_status as Record<string, unknown> | undefined
    const labTotal = Number(labNode?.total || 0)
    const labPass = Number(labNode?.pass || 0)
    const labLatest = String(labNode?.latest_proof_id || '')
    const labLatestPass = String(labNode?.latest_pass_proof_id || '')
    const labLatestHash = String(labNode?.latest_pass_proof_hash || labNode?.latest_proof_hash || '')
    const labStatus = isContractSpu
      ? '不适用'
      : labTotal > 0
        ? (labPass > 0 ? '已取证' : '未通过')
        : '未取证'
    const labQualified = isContractSpu || Boolean(labLatestPass) || labPass > 0
    const dualQualified = qcStatus === '合格' && labQualified
    return { total, pass, fail, pending, qcStatus, labStatus, dualQualified, labPass, labTotal, labLatest, labLatestPass, labLatestHash }
  }, [ctx, form, formSchema, isContractSpu])
  const templateBinding = useMemo(() => {
    const node = (ctx?.node || {}) as Record<string, unknown>
    return ((node.docpeg_template || {}) as Record<string, unknown>)
  }, [ctx])
  const templateDisplay = useMemo(() => {
    const code = String(templateBinding.template_code || '').trim()
    const name = String(templateBinding.template_name || '').trim()
    const spuLabel = String(((ctx?.spu || {}) as Record<string, unknown>).spu_template_label || '').trim()
    const cleanCode = sanitizeGenericLabel(code, '')
    const cleanName = sanitizeGenericLabel(name, '')
    const cleanSpu = sanitizeGenericLabel(spuLabel, '')
    if (cleanCode) return cleanName ? `${cleanCode} · ${cleanName}` : cleanCode
    if (cleanName) return cleanName
    if (cleanSpu) return cleanSpu
    return '未绑定模板'
  }, [ctx, templateBinding.template_code, templateBinding.template_name])
  const specBinding = useMemo(() => {
    const node = (ctx?.node || {}) as Record<string, unknown>
    return String(node.linked_spec_uri || '').trim()
  }, [ctx])
  const gateBinding = useMemo(() => {
    const node = (ctx?.node || {}) as Record<string, unknown>
    return String(node.linked_gate_id || '').trim()
  }, [ctx])
  const nodeMetadata = useMemo(() => {
    const node = (ctx?.node || {}) as Record<string, unknown>
    return ((node.metadata || {}) as Record<string, unknown>)
  }, [ctx])
  const displayMeta = useMemo(() => deriveNodeDisplayMeta(nodeMetadata, active), [active, nodeMetadata])
  const designTotal = summary.design
  const contractTotal = summary.contract
  const settledTotal = summary.settled
  const consumedTotal = summary.consumed
  const effectiveSpent = consumedTotal > 0 ? consumedTotal : settledTotal
  const baselineTotal = designTotal > 0 ? designTotal : contractTotal
  const availableTotal = Math.max(0, baselineTotal - effectiveSpent)
  const claimValue = Number(claimQty)
  const claimQtyValue = Number.isFinite(claimValue) ? claimValue : 0
  const exceedBalance = claimQtyValue > availableTotal + 1e-9
  const isSpecBound = Boolean(specBinding || gateBinding || isContractSpu)
  const hasFormInput = useMemo(() => Object.values(form).some((v) => String(v || '').trim()), [form])
  const geoValid = useMemo(() => {
    const la = Number(lat)
    const ln = Number(lng)
    return Number.isFinite(la) && Number.isFinite(ln)
  }, [lat, lng])
  const geoFenceWarning = useMemo(() => {
    const raw = _asDict((execRes || {}) as Record<string, unknown>)
    const sd = _asDict(raw.state_data || raw.state || {})
    return String(sd.geo_fence_warning || '').trim()
  }, [execRes])

  const loadContext = useCallback(async (uri: string, component = compType) => {
    if (!projectUri || !uri) return
    const reqSeq = contextReqSeqRef.current + 1
    contextReqSeqRef.current = reqSeq
    setLoadingCtx(true)
    setContextError('')
    try {
      const payload = await smuNodeContext({ project_uri: projectUri, boq_item_uri: uri, component_type: component }) as Record<string, unknown> | null
      if (contextReqSeqRef.current !== reqSeq) return
      if (!payload?.ok || !payload?.node) {
        setCtx(null)
        setForm({})
        setContextError('该细目未加载到可用门控，请检查导入数据或重新导入后重试。')
        showToast('加载门控失败')
        return
      }
      setCtx(payload)
      const payloadSpu = _asDict(payload.spu as Record<string, unknown>)
      const payloadSpuLabel = String(payloadSpu.spu_code || payloadSpu.spu_type || '')
      const payloadIsContract = /contract|voucher/i.test(payloadSpuLabel)
      const rows = Array.isArray(payloadSpu.spu_form_schema)
        ? (payloadSpu.spu_form_schema as FormRow[])
        : (payloadIsContract ? fallbackSchema.SPU_Contract : [])
      const next: Record<string, string> = {}
      rows.forEach((r) => (next[String(r.field || '')] = ''))
      setForm(next)
    } catch {
      if (contextReqSeqRef.current !== reqSeq) return
      setCtx(null)
      setForm({})
      setContextError('加载门控请求失败，请稍后重试。')
      showToast('加载门控失败')
    } finally {
      if (contextReqSeqRef.current === reqSeq) setLoadingCtx(false)
    }
  }, [compType, projectUri, showToast, smuNodeContext])

  const autoSelectLeafAndPrefill = useCallback(async (leaf: TreeNode | null) => {
    if (!leaf) return
    const c = leaf.spu === 'SPU_Reinforcement' ? 'main_beam' : leaf.spu === 'SPU_Concrete' ? 'pier' : 'generic'
    setActiveUri(leaf.uri)
    setCtx(null)
    setContextError('')
    setCompType(c)
    setClaimQty('')
    if (!sampleId) {
      const seed = `${leaf.code}-${Date.now().toString().slice(-6)}`
      setSampleId(`SAMPLE-${seed}`)
    }
    await loadContext(leaf.uri, c)
  }, [loadContext, sampleId])

  const refreshTreeFromServer = useCallback(async (focusCode?: string | null) => {
    if (!projectUri) return null
    const payload = await boqRealtimeStatus(projectUri) as Record<string, unknown> | null
    const items = Array.isArray((payload || {}).items) ? ((payload || {}).items as Array<Record<string, unknown>>) : []
    if (!items.length) return null
    const rebuilt = buildTreeFromRealtimeItems(items, projectUri)
    if (!rebuilt.length) return null
    setNodes(rebuilt)
    const defaultLeaf = pickFirstLeaf(rebuilt)
    const focus = String(focusCode || defaultLeaf?.code || '')
    setExpandedCodes(getFocusedExpandedCodes(rebuilt, focus))
    return rebuilt
  }, [boqRealtimeStatus, projectUri])

  const clearTreeState = useCallback(() => {
    setNodes([])
    setExpandedCodes([])
    setActiveUri('')
    setCtx(null)
    setContextError('')
    setForm({})
    setCompType('generic')
    setSampleId('')
    setClaimQty('')
    setEvidence([])
    setEvidenceName('')
    setHashing(false)
  }, [])

  const pollImportJob = useCallback(async (
    jobId: string,
    opts: { skipStartToast?: boolean } = {},
  ) => {
    const id = String(jobId || '').trim()
    if (!id) return
    setImporting(true)
    setImportJobId(id)
    if (!opts.skipStartToast) {
      showToast('已连接到导入任务，正在后台处理中')
    }
    const startedAt = Date.now()
    const maxWaitMs = 10 * 60 * 1000
    let pollFailure = 0
    let pollRound = 0
    while (aliveRef.current) {
      // Poll public status endpoint only to avoid auth revoke checks during long imports.
      // eslint-disable-next-line no-await-in-loop
      const job = await smuImportGenesisJobPublic(id) as Record<string, unknown> | null
      if (!job) {
        pollFailure += 1
        if (pollFailure >= 8) {
          setImportStatusText('导入状态查询失败（后台任务可能仍在执行）')
          showToast('Genesis 导入状态查询失败，请稍后重试')
          break
        }
        // eslint-disable-next-line no-await-in-loop
        await new Promise((resolve) => window.setTimeout(resolve, 1500))
        continue
      }
      pollFailure = 0
      const state = String(job.state || '')
      const stage = String(job.stage || '')
      const progress = Number(job.progress || 0)
      const msg = String(job.message || '')
      const phaseLabel = stage ? `[${stage}] ` : ''
      if (aliveRef.current) {
        setImportProgress(Number.isFinite(progress) ? progress : 0)
        const fallback = state === 'running' ? '后台处理中（大文件约 1-3 分钟）' : '执行中'
        setImportStatusText(`${phaseLabel}${msg || fallback}`)
      }

      if (state === 'success') {
        setImportError('')
        const result = (job.result || {}) as Record<string, unknown>
        const n = Number(result.total_nodes || 0)
        const leaf = Number(result.leaf_nodes || 0)
        const rebuilt = await refreshTreeFromServer()
        const firstLeaf = pickFirstLeaf(rebuilt || [])
        if (firstLeaf) {
          await autoSelectLeafAndPrefill(firstLeaf)
          showToast(`Genesis 已锚定：节点 ${n}，叶子 ${leaf}，已定位 ${firstLeaf.code}`)
        } else {
          showToast(`Genesis 已锚定：节点 ${n}，叶子 ${leaf}`)
        }
        break
      }
      if (state === 'failed') {
        const err = (job.error || {}) as Record<string, unknown>
        const detail = String(err.detail || job.message || 'unknown error')
        setImportStatusText('导入失败')
        setImportError(detail || '导入失败')
        clearTreeState()
        showToast(`Genesis 导入失败: ${detail}`)
        break
      }
      if (Date.now() - startedAt > maxWaitMs) {
        setImportStatusText('后台继续执行中，可稍后重试')
        showToast('导入任务仍在后台执行，请稍后重试查询状态')
        break
      }
      pollRound += 1
      const waitMs = pollRound < 10 ? 1200 : pollRound < 30 ? 2200 : 3500
      // eslint-disable-next-line no-await-in-loop
      await new Promise((resolve) => window.setTimeout(resolve, waitMs))
    }
    if (aliveRef.current) setImporting(false)
  }, [autoSelectLeafAndPrefill, clearTreeState, refreshTreeFromServer, showToast, smuImportGenesisJobPublic])

  useEffect(() => {
    if (!projectUri) return
    if (nodes.length > 0) return
    // Hydrate existing BOQ tree when reopening the project drawer.
    void (async () => {
      const rebuilt = await refreshTreeFromServer()
      if (!rebuilt?.length) return
      if (activeUri) return
      const firstLeaf = pickFirstLeaf(rebuilt)
      if (firstLeaf) await autoSelectLeafAndPrefill(firstLeaf)
    })()
  }, [activeUri, autoSelectLeafAndPrefill, nodes.length, projectUri, refreshTreeFromServer])

  useEffect(() => {
    if (!projectUri) return
    if (importing) return
    if (resumedProjectRef.current === projectUri) return
    resumedProjectRef.current = projectUri
    void (async () => {
      const activeJob = await smuImportGenesisJobActivePublic(projectUri) as Record<string, unknown> | null
      if (!activeJob?.active) return
      const jobId = String(activeJob.job_id || '')
      if (!jobId) return
      const fn = String(activeJob.file_name || '').trim()
      if (fn) setFileName(fn)
      setImportStatusText(String(activeJob.message || '检测到未完成导入任务，正在恢复'))
      setImportProgress(Number(activeJob.progress || 0))
      await pollImportJob(jobId, { skipStartToast: true })
    })()
  }, [importing, pollImportJob, projectUri, smuImportGenesisJobActivePublic])

  const onSelectFile = useCallback(async (f: File | null) => {
    setFile(f)
    setFileName(f?.name || '')
    setImportError('')
    if (!f) return
    if (/\.xlsx$/i.test(f.name)) {
      // Backend handles legacy or mislabeled Excel files.
    }
    if (/\.csv$/i.test(f.name)) {
      f.arrayBuffer().then((buf) => {
        const decode = (enc: string) => {
          try {
            return new TextDecoder(enc).decode(buf)
          } catch {
            return ''
          }
        }
        let text = decode('utf-8')
        const chapterHint = guessChapterFromFileName(f.name || '') || '400'
        let parsed = parseCsv(text, projectUri, chapterHint)
        if (!parsed.length) {
          const gbText = decode('gb18030')
          if (gbText) {
            text = gbText
            parsed = parseCsv(text, projectUri, chapterHint)
          }
        }
        if (!parsed.length) {
          showToast('CSV 解析失败：请检查表头或编码')
          return
        }
        setNodes(parsed)
        const firstLeaf = pickFirstLeaf(parsed)
        setExpandedCodes(getFocusedExpandedCodes(parsed, firstLeaf?.code))
        const leaf = parsed.find((x) => x.isLeaf)
        if (leaf) void autoSelectLeafAndPrefill(leaf)
      })
    } else {
      // xlsx/xls preview: call backend to build a quick hierarchy snapshot for immediate tree.
      try {
        const chapterHint = guessChapterFromFileName(f.name || '') || '400'
        const preview = await smuImportGenesisPreview({
          file: f,
          project_uri: projectUri,
          project_id: projectId || undefined,
          boq_root_uri: `${projectUri.replace(/\/$/, '')}/boq/${chapterHint}`,
          norm_context_root_uri: `${projectUri.replace(/\/$/, '')}/normContext`,
          owner_uri: `${projectUri.replace(/\/$/, '')}/role/system/`,
        }) as Record<string, unknown> | null
        const items = Array.isArray((preview || {}).preview_items) ? ((preview || {}).preview_items as Array<Record<string, unknown>>) : []
        if (items.length) {
          const rebuilt = buildTreeFromRealtimeItems(items, projectUri)
          setNodes(rebuilt)
          const firstLeaf = pickFirstLeaf(rebuilt)
          setExpandedCodes(getFocusedExpandedCodes(rebuilt, firstLeaf?.code))
          if (firstLeaf) void autoSelectLeafAndPrefill(firstLeaf)
        }
      } catch {
        // Preview is best-effort; fallback to empty tree until import completes.
        setNodes([])
        setExpandedCodes([])
        setActiveUri('')
      }
    }
  }, [autoSelectLeafAndPrefill, projectId, projectUri, showToast, smuImportGenesisPreview])

  const importGenesis = useCallback(async () => {
    if (!file || !projectUri) {
      showToast('请先选择清单文件')
      return
    }
    setImporting(true)
    setImportJobId('')
    setImportProgress(0)
    setImportStatusText('任务提交中（大文件约 1-3 分钟）')
    setImportError('')
    setImportWarning('')
    try {
      const chapterHint = guessChapterFromFileName(fileName || '') || '400'
      const params = {
        file,
        project_uri: projectUri,
        project_id: projectId || undefined,
        boq_root_uri: `${projectUri.replace(/\/$/, '')}/boq/${chapterHint}`,
        norm_context_root_uri: `${projectUri.replace(/\/$/, '')}/normContext`,
        owner_uri: `${projectUri.replace(/\/$/, '')}/role/system/`,
        commit: true,
      }
      let canUseAsync = asyncImportSupported
      if (canUseAsync === null) {
        try {
          const res = await fetch(`${API_BASE}/openapi.json`)
          const json = await res.json() as { paths?: Record<string, unknown> }
          canUseAsync = !!json?.paths?.['/v1/proof/smu/genesis/import-async']
          setAsyncImportSupported(canUseAsync)
        } catch {
          // If capability check fails (network/temporary error), fallback to sync path.
          canUseAsync = false
          setAsyncImportSupported(false)
        }
      }

      let payload: Record<string, unknown> | null = null
      if (canUseAsync) {
        payload = await smuImportGenesisAsync(params) as Record<string, unknown> | null
      }

      // Fallback for environments that expose only sync import endpoint.
      const hasJobId = canUseAsync && String(payload?.job_id || '').trim().length > 0
      if (!hasJobId) {
        if (canUseAsync) {
          setImportStatusText('异步任务创建失败，已回退同步导入')
          setImportProgress(15)
        } else {
          setImportStatusText('异步接口不可用，回退同步导入（可能耗时较久）')
          setImportProgress(10)
        }
        const syncPayload = await smuImportGenesis(params) as Record<string, unknown> | null
        if (!syncPayload?.ok) {
          const detail = String((syncPayload as Record<string, unknown>)?.detail || (payload as Record<string, unknown>)?.detail || '')
          setImportProgress(0)
          setImportStatusText('导入失败')
          setImportError(detail || '导入失败')
          clearTreeState()
          showToast(detail ? `Genesis 导入失败: ${detail}` : 'Genesis 导入失败')
          return
        }
        setImportProgress(100)
        setImportStatusText('导入完成')
        setImportError('')
        const rebuilt = await refreshTreeFromServer()
        const firstLeaf = pickFirstLeaf(rebuilt || [])
        if (firstLeaf) {
          await autoSelectLeafAndPrefill(firstLeaf)
          showToast(`Genesis 已锚定并定位到首个细目：${firstLeaf.code}`)
        } else {
          showToast('Genesis 已锚定')
        }
        return
      }
      if (!payload?.ok) {
        const detail = String((payload as Record<string, unknown>)?.detail || '')
        setImportProgress(0)
        setImportStatusText('导入失败')
        setImportError(detail || '导入失败')
        clearTreeState()
        showToast(detail ? `Genesis 导入失败: ${detail}` : 'Genesis 导入失败')
        return
      }
      const jobId = String(payload.job_id || '')
      if (!jobId) {
        showToast('Genesis 导入任务创建失败')
        return
      }
      setImportStatusText(String(payload.message || '任务已创建'))
      setImportProgress(Number(payload.progress || 0))
      await pollImportJob(jobId, { skipStartToast: true })
    } finally {
      if (aliveRef.current) setImporting(false)
    }
  }, [asyncImportSupported, clearTreeState, file, pollImportJob, projectId, projectUri, refreshTreeFromServer, showToast, smuImportGenesis, smuImportGenesisAsync])

  const selectNode = useCallback(async (code: string) => {
    const n = byCode.get(code)
    if (!n) return
    setExpandedCodes(getFocusedExpandedCodes(nodes, code))
    setActiveUri(n.uri)
    setCtx(null)
    setContextError('')
    setClaimQty('')
    if (!n.isLeaf) return
    const c = n.spu === 'SPU_Reinforcement' ? 'main_beam' : n.spu === 'SPU_Concrete' ? 'pier' : 'generic'
    setCompType(c)
    if (!sampleId) {
      const seed = `${n.code}-${Date.now().toString().slice(-6)}`
      setSampleId(`SAMPLE-${seed}`)
    }
    await loadContext(n.uri, c)
  }, [byCode, loadContext, nodes, sampleId])

  const onEvidence = useCallback(async (list: FileList | null) => {
    evidence.forEach((x) => URL.revokeObjectURL(x.url))
    const files = list ? Array.from(list) : []
    setEvidenceName(files.length ? files.map((f) => f.name).join('、') : '')
    if (!files.length) {
      setEvidence([])
      return
    }
    setHashing(true)
    try {
      const rows = await Promise.all(files.map(async (f) => ({ name: f.name, url: URL.createObjectURL(f), hash: await sha(f), ntp: new Date().toISOString() })))
      setEvidence(rows)
    } finally {
      setHashing(false)
    }
  }, [evidence])

  useEffect(() => {
    const next = String(((signRes?.trip || {}) as Record<string, unknown>).output_proof_id || '')
    if (next) setScanProofId(next)
  }, [signRes])

  useEffect(() => {
    if (pdfB64) setDocModalOpen(true)
  }, [pdfB64])

  const submitTrip = useCallback(async () => {
    if (!active?.isLeaf || !projectUri || !inputProofId) {
      showToast('请先选择叶子细目并加载规则')
      return
    }
    if (!isSpecBound) {
      showToast('未绑定规范/门控，禁止提交')
      return
    }
    if (!gateStats.dualQualified) {
      showToast('双合格门控未通过，已拦截提交')
      return
    }
    if (exceedBalance) {
      showToast('申报量超出合同余额，已拦截提交')
      return
    }
    const measurement: Record<string, number | string> = {}
    Object.entries(form).forEach(([k, v]) => {
      const n = Number(v)
      measurement[k] = Number.isFinite(n) ? n : v
    })
    if (sampleId) measurement.sample_id = sampleId
    if (claimQtyValue > 0) measurement.claim_quantity = claimQtyValue
    if (gateStats.labLatestPass) measurement.lab_proof_id = gateStats.labLatestPass
    if (gateStats.labLatestHash) measurement.lab_proof_hash = gateStats.labLatestHash
    setExecuting(true)
    try {
      const now = new Date().toISOString()
      const payload = await smuExecute({
        project_uri: projectUri,
        input_proof_id: inputProofId,
        executor_uri: `${projectUri.replace(/\/$/, '')}/role/contractor/mobile/`,
        executor_did: executorDid,
        executor_role: 'TRIPROLE',
        component_type: compType,
        measurement,
        geo_location: { lat: Number(lat), lng: Number(lng) },
        server_timestamp_proof: { ntp_server: 'pool.ntp.org', captured_at: now, proof_hash: `ntp-${now}` },
        evidence_hashes: evidence.map((x) => x.hash),
      }) as Record<string, unknown> | null
      if (!payload?.ok) {
        showToast('提交失败')
        return
      }
      setExecRes(payload)
      setNodes((prev) => prev.map((x) => (x.uri === active.uri ? { ...x, status: 'Spending' } : x)))
      setSignOpen(true)
      setSignStep(0)
      void refreshTreeFromServer(active.code)
    } finally {
      setExecuting(false)
    }
  }, [active, claimQtyValue, compType, evidence, exceedBalance, executorDid, form, gateStats.dualQualified, gateStats.labLatestHash, gateStats.labLatestPass, inputProofId, isSpecBound, lat, lng, projectUri, refreshTreeFromServer, showToast, smuExecute])

  const recordRejectTrip = useCallback(async () => {
    if (!active?.isLeaf || !projectUri || !inputProofId) {
      showToast('请先选择叶子细目并加载规则')
      return
    }
    setRejecting(true)
    try {
      const now = new Date().toISOString()
      const measurement: Record<string, number | string> = {}
      Object.entries(form).forEach(([k, v]) => {
        const n = Number(v)
        measurement[k] = Number.isFinite(n) ? n : v
      })
      if (sampleId) measurement.sample_id = sampleId
      if (gateStats.labLatestPass) measurement.lab_proof_id = gateStats.labLatestPass
      if (gateStats.labLatestHash) measurement.lab_proof_hash = gateStats.labLatestHash
      const payload = await smuExecute({
        project_uri: projectUri,
        input_proof_id: inputProofId,
        executor_uri: `${projectUri.replace(/\/$/, '')}/role/contractor/mobile/`,
        executor_did: executorDid,
        executor_role: 'TRIPROLE',
        component_type: compType,
        measurement,
        geo_location: { lat: Number(lat), lng: Number(lng) },
        server_timestamp_proof: { ntp_server: 'pool.ntp.org', captured_at: now, proof_hash: `ntp-${now}` },
        evidence_hashes: evidence.map((x) => x.hash),
        force_reject: true,
      }) as Record<string, unknown> | null
      if (!payload?.ok) {
        showToast('记录拒绝失败')
        return
      }
      setExecRes(payload)
      showToast('已记录不合格 Proof')
      void refreshTreeFromServer(active.code)
    } finally {
      setRejecting(false)
    }
  }, [active, compType, evidence, executorDid, form, gateStats.labLatestHash, gateStats.labLatestPass, inputProofId, lat, lng, projectUri, refreshTreeFromServer, showToast, smuExecute, sampleId])

  const doSign = useCallback(async () => {
    const output = String(((execRes?.trip || {}) as Record<string, unknown>).output_proof_id || '')
    if (!active?.uri || !output) return
    setSigning(true)
    try {
      for (const s of [1, 2, 3]) {
        setSignStep(s)
        // eslint-disable-next-line no-await-in-loop
        await new Promise((r) => window.setTimeout(r, 350))
      }
      const now = new Date().toISOString()
      const payload = await smuSign({
        input_proof_id: output,
        boq_item_uri: active.uri,
        supervisor_executor_uri: `${projectUri.replace(/\/$/, '')}/role/supervisor/mobile/`,
        supervisor_did: supervisorDid,
        contractor_did: executorDid,
        owner_did: ownerDid,
        signer_metadata: { mode: 'liveness', checked_at: now, passed: true },
        geo_location: { lat: Number(lat), lng: Number(lng) },
        server_timestamp_proof: { ntp_server: 'pool.ntp.org', captured_at: now, proof_hash: `ntp-${now}` },
        auto_docpeg: true,
        template_path: String(templateBinding.template_path || ''),
      }) as Record<string, unknown> | null
      if (!payload?.ok) {
        showToast('签认失败')
        return
      }
      setSignRes(payload)
      setNodes((prev) => prev.map((x) => (x.uri === active.uri ? { ...x, status: 'Settled' } : x)))
      const smuId = active.code.split('-')[0]
      if (smuId) {
        const freeze = await smuFreeze({ project_uri: projectUri, smu_id: smuId, executor_uri: `${projectUri.replace(/\/$/, '')}/role/owner/system/`, min_risk_score: 60 }) as Record<string, unknown> | null
        if (freeze?.ok) setFreezeProof(String(freeze.freeze_proof_id || ''))
      }
      setSignOpen(false)
    } finally {
      setSigning(false)
    }
  }, [active, execRes, executorDid, lat, lng, ownerDid, projectUri, showToast, smuFreeze, smuSign, supervisorDid, templateBinding.template_path])

  const applyDelta = useCallback(async () => {
    if (!active?.isLeaf || !projectUri) {
      showToast('请先选择叶子细目')
      return
    }
    const delta = Number(String(deltaAmount || '').replace(/,/g, '').trim())
    if (!Number.isFinite(delta) || Math.abs(delta) < 1e-9) {
      showToast('请输入有效的变更数量')
      return
    }
    setApplyingDelta(true)
    try {
      const now = new Date().toISOString()
      const payload = await applyVariationDelta({
        boq_item_uri: active.uri,
        delta_amount: delta,
        reason: deltaReason,
        project_uri: projectUri,
        executor_uri: `${projectUri.replace(/\/$/, '')}/role/contractor/mobile/`,
        executor_did: executorDid,
        executor_role: 'TRIPROLE',
        geo_location: { lat: Number(lat), lng: Number(lng) },
        server_timestamp_proof: { ntp_server: 'pool.ntp.org', captured_at: now, proof_hash: `ntp-${now}` },
      }) as Record<string, unknown> | null
      if (!payload?.ok) {
        showToast('变更补差失败')
        return
      }
      setVariationRes(payload)
      setNodes((prev) => prev.map((x) => {
        if (x.uri !== active.uri) return x
        const next = Math.max(0, (x.contractQty || 0) + delta)
        return { ...x, contractQty: next }
      }))
      showToast('变更补差已写回链')
    } finally {
      setApplyingDelta(false)
    }
  }, [active, applyVariationDelta, deltaAmount, deltaReason, executorDid, lat, lng, projectUri, showToast])

  const doScanConfirm = useCallback(async () => {
    const proofId = String(scanProofId || inputProofId || '')
    if (!proofId) {
      showToast('请输入待确权 Proof ID')
      return
    }
    if (!scanPayload) {
      showToast('请提供扫码凭据')
      return
    }
    if (!scanDid) {
      showToast('请输入扫码人 DID')
      return
    }
    setScanning(true)
    try {
      const now = new Date().toISOString()
      const payload = await scanConfirmSignature({
        input_proof_id: proofId,
        scan_payload: scanPayload,
        scanner_did: scanDid,
        scanner_role: 'SUPERVISOR',
        executor_uri: `${projectUri.replace(/\/$/, '')}/role/supervisor/mobile/`,
        executor_role: 'SUPERVISOR',
        geo_location: { lat: Number(lat), lng: Number(lng) },
        server_timestamp_proof: { ntp_server: 'pool.ntp.org', captured_at: now, proof_hash: `ntp-${now}` },
      }) as Record<string, unknown> | null
      if (!payload?.ok) {
        showToast('扫码确权失败')
        return
      }
      setScanRes(payload)
      showToast('扫码确权成功')
    } finally {
      setScanning(false)
    }
  }, [inputProofId, lat, lng, projectUri, scanConfirmSignature, scanDid, scanPayload, scanProofId, showToast])

  const sealOfflinePacket = useCallback(async () => {
    if (!active?.uri) {
      showToast('请先选择细目')
      return
    }
    if (!projectUri) {
      showToast('项目 URI 缺失')
      return
    }
    const now = new Date().toISOString()
    const packetId = `offline-${Date.now()}-${Math.random().toString(16).slice(2, 8)}`
    let packet: Record<string, unknown> | null = null
    if (offlineType === 'variation.apply') {
      const delta = Number(String(deltaAmount || '').replace(/,/g, '').trim())
      if (!Number.isFinite(delta) || Math.abs(delta) < 1e-9) {
        showToast('请输入有效的变更数量')
        return
      }
      packet = {
        packet_type: 'variation.apply',
        offline_packet_id: packetId,
        local_created_at: now,
        project_uri: projectUri,
        boq_item_uri: active.uri,
        delta_amount: delta,
        reason: deltaReason,
        sample_id: sampleId,
        executor_uri: `${projectUri.replace(/\/$/, '')}/role/contractor/mobile/`,
        executor_did: executorDid,
        executor_role: 'TRIPROLE',
        geo_location: { lat: Number(lat), lng: Number(lng) },
        server_timestamp_proof: { ntp_server: 'offline', captured_at: now, proof_hash: `offline-${now}` },
      }
    } else {
      if (!inputProofId) {
        showToast('当前细目缺少可消费 UTXO')
        return
      }
      const measurement: Record<string, number | string> = {}
      Object.entries(form).forEach(([k, v]) => {
        const n = Number(v)
        measurement[k] = Number.isFinite(n) ? n : v
      })
      const snappegPayload = {
        project_uri: projectUri,
        input_proof_id: inputProofId,
        boq_item_uri: active.uri,
        measurement,
        sample_id: sampleId,
        geo_location: { lat: Number(lat), lng: Number(lng) },
        server_timestamp_proof: { ntp_server: 'offline', captured_at: now },
        executor_did: executorDid,
        evidence_hashes: evidence.map((x) => x.hash),
      }
      const snappegHash = await shaJson(snappegPayload)
      packet = {
        packet_type: 'triprole.execute',
        action: 'quality.check',
        offline_packet_id: packetId,
        local_created_at: now,
        project_uri: projectUri,
        boq_item_uri: active.uri,
        input_proof_id: inputProofId,
        executor_uri: `${projectUri.replace(/\/$/, '')}/role/contractor/mobile/`,
        executor_did: executorDid,
        executor_role: 'TRIPROLE',
        payload: { component_type: compType, measurement, snappeg_payload_hash: snappegHash, sample_id: sampleId },
        geo_location: { lat: Number(lat), lng: Number(lng) },
        server_timestamp_proof: { ntp_server: 'offline', captured_at: now, proof_hash: `offline-${now}` },
      }
    }
    if (!packet) return
    const next = [...offlinePackets, packet]
    persistOfflinePackets(next)
    showToast('离线封存成功，待网络恢复后重放')
  }, [active, compType, deltaAmount, deltaReason, evidence, executorDid, form, inputProofId, lat, lng, offlinePackets, offlineType, persistOfflinePackets, projectUri, showToast])

  const replayOffline = useCallback(async () => {
    if (!offlinePackets.length) {
      showToast('离线队列为空')
      return
    }
    setOfflineReplaying(true)
    try {
      const payload = await replayOfflinePackets({
        packets: offlinePackets,
        stop_on_error: offlineStopOnError,
        default_executor_uri: `${projectUri.replace(/\/$/, '')}/role/contractor/mobile/`,
        default_executor_role: 'TRIPROLE',
      }) as Record<string, unknown> | null
      if (!payload) {
        showToast('离线重放失败')
        return
      }
      setOfflineReplay(payload)
      const errCount = Number(payload.error_count || 0)
      if (errCount === 0) {
        persistOfflinePackets([])
      }
    } finally {
      setOfflineReplaying(false)
    }
  }, [offlinePackets, offlineStopOnError, persistOfflinePackets, projectUri, replayOfflinePackets, showToast])

  const removeOfflinePacket = useCallback((packetId: string) => {
    const next = offlinePackets.filter((p) => String(p.offline_packet_id || '') !== packetId)
    persistOfflinePackets(next)
  }, [offlinePackets, persistOfflinePackets])

  const clearOfflinePackets = useCallback(() => {
    persistOfflinePackets([])
  }, [persistOfflinePackets])

  const exportOfflinePackets = useCallback(() => {
    if (!offlinePackets.length) {
      showToast('离线队列为空')
      return
    }
    const payload = JSON.stringify(offlinePackets, null, 2)
    const blob = new Blob([payload], { type: 'application/json' })
    const url = URL.createObjectURL(blob)
    const a = document.createElement('a')
    a.href = url
    a.download = `offline-packets-${Date.now()}.json`
    document.body.appendChild(a)
    a.click()
    a.remove()
    URL.revokeObjectURL(url)
  }, [offlinePackets, showToast])

  const importOfflinePackets = useCallback(async (file: File | null) => {
    if (!file) return
    setOfflineImporting(true)
    setOfflineImportName(file.name || '')
    try {
      const text = await file.text()
      const parsed = JSON.parse(text)
      if (!Array.isArray(parsed)) {
        showToast('离线包格式错误')
        return
      }
      const next = [...offlinePackets, ...parsed.filter((x) => typeof x === 'object' && x)]
      persistOfflinePackets(next)
      showToast(`已导入 ${parsed.length} 条离线包`)
    } catch {
      showToast('离线包解析失败')
    } finally {
      setOfflineImporting(false)
    }
  }, [offlinePackets, persistOfflinePackets, showToast])

  const calcUnitMerkle = useCallback(async () => {
    if (!projectUri) {
      showToast('项目 URI 缺失')
      return
    }
    setUnitLoading(true)
    try {
      const payload = await unitMerkleRoot({
        project_uri: projectUri,
        unit_code: unitCode || undefined,
        proof_id: unitProofId || undefined,
        max_rows: Number(unitMaxRows) || undefined,
      }) as Record<string, unknown> | null
      if (!payload?.ok) {
        showToast('单位工程 Merkle 计算失败')
        return
      }
      setUnitRes(payload)
      showToast('单位工程 Merkle 根已生成')
    } finally {
      setUnitLoading(false)
    }
  }, [projectUri, showToast, unitCode, unitMaxRows, unitMerkleRoot, unitProofId])

  const useCurrentProofForUnit = useCallback(() => {
    const pid = String(inputProofId || '')
    if (pid) setUnitProofId(pid)
    const code = active?.code ? active.code.split('-')[0] : ''
    if (code) setUnitCode(code)
  }, [active?.code, inputProofId])

  const copyText = useCallback(async (label: string, value: string) => {
    if (!value) return
    try {
      await navigator.clipboard.writeText(value)
      setCopiedMsg(`${label} 已复制`)
      window.setTimeout(() => setCopiedMsg(''), 1500)
    } catch {
      showToast('复制失败')
    }
  }, [showToast])

  const exportMerkleJson = useCallback(() => {
    if (!unitRes) {
      showToast('请先生成单位工程根哈希')
      return
    }
    const payload = {
      unit: unitRes,
      computed: {
        item_root: itemRootComputed,
        unit_leaf: unitLeafComputed,
        project_root: projectRootComputed,
        item_path_steps: itemPathSteps,
        unit_path_steps: unitPathSteps,
      },
    }
    downloadJson(`merkle-snapshot-${Date.now()}.json`, payload)
  }, [itemPathSteps, itemRootComputed, projectRootComputed, showToast, unitLeafComputed, unitRes, unitPathSteps])

  const computeMerkleRootFromPath = useCallback(async (leaf: string, path: Array<Record<string, unknown>>) => {
    if (!leaf || !Array.isArray(path) || !path.length) return ''
    let current = leaf
    for (const step of path) {
      const sibling = String(step.sibling_hash || '')
      const position = String(step.position || '')
      if (!sibling) continue
      if (position === 'left') {
        current = await sha256Hex(`${sibling}|${current}`)
      } else {
        current = await sha256Hex(`${current}|${sibling}`)
      }
    }
    return current
  }, [])

  const computeMerkleSteps = useCallback(async (leaf: string, path: Array<Record<string, unknown>>) => {
    if (!leaf || !Array.isArray(path) || !path.length) return { root: '', steps: [] as MerkleStep[] }
    let current = leaf
    const steps: MerkleStep[] = []
    for (const step of path) {
      const sibling = String(step.sibling_hash || '')
      const position = String(step.position || '')
      if (!sibling) continue
      if (position === 'left') {
        current = await sha256Hex(`${sibling}|${current}`)
      } else {
        current = await sha256Hex(`${current}|${sibling}`)
      }
      steps.push({
        depth: Number(step.depth || steps.length),
        position,
        sibling_hash: sibling,
        combined_hash: current,
      })
    }
    return { root: current, steps }
  }, [])

  const verifyUnitMerkle = useCallback(async () => {
    if (!unitRes) {
      showToast('请先生成单位工程根哈希')
      return
    }
    setUnitVerifying(true)
    setUnitVerifyMsg('')
    try {
      const requestedLeaf = (unitRes.requested_leaf || {}) as Record<string, unknown>
      const leafHash = String(requestedLeaf.leaf_hash || '')
      const itemPath = Array.isArray(unitRes.item_merkle_path) ? (unitRes.item_merkle_path as Array<Record<string, unknown>>) : []
      const unitRootExpected = String(unitRes.unit_root_hash || '')
      const itemCalc = leafHash && itemPath.length ? await computeMerkleSteps(leafHash, itemPath) : { root: '', steps: [] as MerkleStep[] }
      const computedItemRoot = itemCalc.root

      const resolvedUnit = String(unitRes.resolved_unit_code || '')
      const units = Array.isArray(unitRes.units) ? (unitRes.units as Array<Record<string, unknown>>) : []
      let unitLeaf = ''
      for (const u of units) {
        if (String(u.unit_code || '') === resolvedUnit) {
          unitLeaf = String(u.unit_leaf_hash || '')
          break
        }
      }
      if (!unitLeaf && resolvedUnit && unitRootExpected) {
        unitLeaf = await sha256Hex(`unit:${resolvedUnit}|${unitRootExpected}`)
      }

      const unitPath = Array.isArray(unitRes.unit_merkle_path) ? (unitRes.unit_merkle_path as Array<Record<string, unknown>>) : []
      const projectRootExpected = String(unitRes.project_root_hash || unitRes.global_project_fingerprint || '')
      const unitCalc = unitLeaf && unitPath.length ? await computeMerkleSteps(unitLeaf, unitPath) : { root: '', steps: [] as MerkleStep[] }
      const computedProjectRoot = unitCalc.root

      setItemRootComputed(computedItemRoot)
      setUnitLeafComputed(unitLeaf)
      setProjectRootComputed(computedProjectRoot)
      setItemPathSteps(itemCalc.steps)
      setUnitPathSteps(unitCalc.steps)

      const itemOk = !!computedItemRoot && !!unitRootExpected && computedItemRoot === unitRootExpected
      const projectOk = !!computedProjectRoot && !!projectRootExpected && computedProjectRoot === projectRootExpected
      setUnitVerifyMsg(itemOk && projectOk ? '校验通过：叶子 -> 单位 -> 项目链路一致' : '校验失败：请检查路径或 leaf hash')
    } finally {
      setUnitVerifying(false)
    }
  }, [computeMerkleSteps, showToast, unitRes])

  const qrSrc = useMemo(() => createQrSvg(verifyUri || 'qcspec-docpeg-empty', 140, 'medium'), [verifyUri])
  const readinessPercent = useMemo(() => {
    const v = Number(readiness?.readiness_percent || 0)
    return Number.isFinite(v) ? Math.max(0, Math.min(100, v)) : 0
  }, [readiness])
  const readinessOverall = useMemo(() => String(readiness?.overall_status || 'missing'), [readiness])
  const readinessLayers = useMemo<ReadinessLayer[]>(() => {
    return Array.isArray(readiness?.layers) ? readiness.layers : []
  }, [readiness])
  const readinessAction: Record<string, string> = {
    live_boq: '先导入 400 章并完成 Genesis 锚定',
    specdict_qcgate: '到 Gate 编辑器完成规则绑定与版本发布',
    docpeg_documents: '执行签认并生成 DocPeg/文档上传挂链',
    field_execution_qcspec: '做至少 1 笔现场质检并提交物证',
    labpeg_dual_gate: '补录 LabPeg 试验并清零漏检',
    finance_erp_railpact: '生成支付证书并下发 RailPact 指令',
    audit_reconciliation: '运行主权对账，确认非法尝试为 0',
  }

  const inputBaseCls = 'border border-slate-700/90 rounded-lg px-3 py-2 bg-slate-950/90 text-slate-100 text-sm leading-5 placeholder:text-slate-500 focus:outline-none focus:ring-2 focus:ring-sky-500/40 focus:border-sky-500 transition'
  const inputXsCls = 'border border-slate-700/90 rounded-lg px-3 py-2 bg-slate-950/90 text-slate-100 text-sm leading-5 placeholder:text-slate-500 focus:outline-none focus:ring-2 focus:ring-sky-500/40 focus:border-sky-500 transition'
  const btnBlueCls = 'rounded-lg border border-sky-500/70 bg-gradient-to-r from-slate-800 to-slate-700 text-sky-100 hover:from-slate-700 hover:to-slate-600 transition-colors duration-200 shadow-[0_0_0_1px_rgba(56,189,248,.15)]'
  const btnGreenCls = 'rounded-lg border border-emerald-500/70 bg-gradient-to-r from-slate-800 to-slate-700 text-emerald-100 hover:from-slate-700 hover:to-slate-600 transition-colors duration-200 shadow-[0_0_0_1px_rgba(16,185,129,.15)]'
  const btnAmberCls = 'rounded-lg border border-amber-500/70 bg-gradient-to-r from-slate-800 to-slate-700 text-amber-100 hover:from-slate-700 hover:to-slate-600 transition-colors duration-200 shadow-[0_0_0_1px_rgba(245,158,11,.15)]'
  const btnRedCls = 'rounded-lg border border-rose-500/70 bg-gradient-to-r from-rose-900 to-rose-800 text-rose-100 hover:from-rose-800 hover:to-rose-700 transition-colors duration-200 shadow-[0_0_0_1px_rgba(244,63,94,.15)]'
  const panelCls = 'h-full rounded-2xl border border-slate-700/80 bg-gradient-to-b from-slate-900 to-slate-900/75 p-4 text-slate-100 shadow-[0_14px_28px_rgba(2,6,23,.35)]'
  const componentTypeOptions = useMemo<Array<{ value: string; label: string }>>(() => {
    const base = [
      { value: 'main_beam', label: '主梁' },
      { value: 'pier', label: '桥墩' },
      { value: 'guardrail', label: '护栏' },
      { value: 'slab', label: '桥面板' },
    ]
    if (!base.some((x) => x.value === compType) && compType) {
      base.unshift({ value: compType, label: compType === 'generic' ? '未配置构件' : `其他（${compType}）` })
    }
    return base
  }, [compType])

  const renderTree = (code: string, depth: number): React.ReactNode => {
    const node = byCode.get(code)
    if (!node) return null
    if (treeSearch.active && !treeSearch.visible.has(code)) return null
    const childList = treeSearch.active ? node.children.filter((child) => treeSearch.visible.has(child)) : node.children
    const hasChildren = childList.length > 0
    const agg = aggMap.get(code) || { contract: 0, approved: 0, design: 0, settled: 0, consumed: 0 }
    const baseQty = agg.design > 0 ? agg.design : agg.contract
    const expanded = hasChildren
      ? (treeSearch.active ? treeSearch.expanded.includes(code) : expandedCodes.includes(code))
      : false
    const activeCls = activeUri === node.uri
      ? 'border-blue-500 bg-blue-500/20 shadow-[inset_0_0_0_1px_rgba(59,130,246,.35)]'
      : 'border-slate-500/30 bg-slate-900/60 hover:bg-slate-900/90 hover:border-slate-400/40'
    return (
      <React.Fragment key={code}>
        <button
          type="button"
          onClick={() => void selectNode(code)}
          title={`${nodePathMap.get(code) || node.uri} · ${statusLabel[node.status]}`}
          className={`w-full grid grid-cols-[14px_14px_1fr_auto] gap-3 items-center text-left text-[15px] leading-7 text-slate-200 rounded-lg px-3.5 py-3 transition ${activeCls}`}
          style={{ paddingLeft: `${8 + depth * 14}px` }}
        >
          <span style={{ width: 10, height: 10, borderRadius: 999, background: color[node.status], boxShadow: `0 0 8px ${color[node.status]}`, animation: 'sovereignPulse 1.8s infinite ease-in-out' }} />
          <span
            role="button"
            tabIndex={0}
            onClick={(e) => {
              e.preventDefault()
              e.stopPropagation()
              if (!hasChildren) return
              setExpandedCodes((prev) => prev.includes(code) ? prev.filter((x) => x !== code) : [...prev, code])
            }}
            onKeyDown={(e) => {
              if (e.key !== 'Enter' && e.key !== ' ') return
              e.preventDefault()
              e.stopPropagation()
              if (!hasChildren) return
              setExpandedCodes((prev) => prev.includes(code) ? prev.filter((x) => x !== code) : [...prev, code])
            }}
            className={`text-[11px] ${hasChildren ? 'text-slate-400 hover:text-sky-300 cursor-pointer' : 'text-slate-700'}`}
            aria-label={hasChildren ? (expanded ? '折叠节点' : '展开节点') : '叶子节点'}
          >
            {hasChildren ? (expanded ? '▼' : '▶') : '•'}
          </span>
          <span className="truncate">
            <span className="font-mono text-slate-300">{node.code}</span> - {node.name}
            <span className="block text-[11px] text-slate-400 truncate mt-1">{nodePathMap.get(code) || node.uri}</span>
          </span>
          <span className="rounded-full border border-slate-500/60 bg-slate-950/60 px-2 py-0.5 text-[11px] text-slate-300">
            {baseQty.toLocaleString()}
          </span>
        </button>
        {expanded && childList.map((child) => renderTree(child, depth + 1))}
      </React.Fragment>
    )
  }

  return (
    <Card title="主权 BOQ 工作台" icon="🔗" style={{ marginBottom: 10 }} className="overflow-hidden sovereign-workbench">
      <style>{`@keyframes sovereignPulse {0%{transform:scale(.92);opacity:.45}50%{transform:scale(1.06);opacity:1}100%{transform:scale(.92);opacity:.45}}
      .sovereign-workbench{font-size:15px;line-height:1.68}
      .sovereign-workbench .wb-panel{padding:20px;border-radius:16px}
      .sovereign-workbench input,.sovereign-workbench select,.sovereign-workbench button{min-height:44px}
      .sovereign-workbench textarea{line-height:1.68}
      .sovereign-workbench .wb-table-head{font-size:14px;padding:13px 15px}
      .sovereign-workbench .wb-table-row{font-size:14px;line-height:1.72;padding:13px 15px}
      `}</style>
      <div className="rounded-2xl border border-slate-200 bg-gradient-to-br from-slate-100 via-white to-slate-100 p-6 shadow-[inset_0_1px_0_rgba(255,255,255,.9)]">
        <div className="mb-4 rounded-xl border border-slate-300 bg-white/80 px-4 py-3 text-slate-700 shadow-sm">
          <div className="flex flex-wrap items-center justify-between gap-2">
            <div>
              <div className="text-xs uppercase tracking-[0.12em] text-slate-500">主权执行控制台</div>
              <div className="mt-1 text-base font-bold">400 章主权资产树 + TripRole 执行闭环</div>
              <div className="mt-1 text-xs text-slate-500 break-all">当前主权路径: {activePath || '-'}</div>
            </div>
            <div className="flex items-center gap-2 text-[11px]">
              <span className="rounded-full border border-slate-300 bg-slate-50 px-2 py-0.5 text-slate-600">节点 {nodes.length}</span>
              <span className="rounded-full border border-sky-300 bg-sky-50 px-2 py-0.5 text-sky-700">当前 {active?.code || '-'}</span>
            </div>
          </div>
        </div>
        {!!totalHash && (
          <div className="mb-3 border border-emerald-600/80 bg-emerald-950 text-emerald-100 rounded-xl p-2">
            <div className="text-xs font-extrabold">总证明哈希: {totalHash}</div>
            <div className="mt-1 text-xs">SMU 已冻结，证据链不可篡改{freezeProof ? ` · 冻结证明: ${freezeProof}` : ''}</div>
          </div>
        )}

        <div className="mb-4 rounded-xl border border-slate-300 bg-white/80 p-3 shadow-sm">
          <div className="flex flex-wrap items-center justify-between gap-2">
            <div>
              <div className="text-xs uppercase tracking-[0.12em] text-slate-500">Project Readiness / 项目完备度</div>
              <div className="mt-1 text-sm font-bold text-slate-700">七步闭环落地体检</div>
            </div>
            <div className="flex items-center gap-2">
              <span className={`rounded-full border px-2.5 py-1 text-xs font-semibold ${
                readinessOverall === 'complete'
                  ? 'border-emerald-300 bg-emerald-50 text-emerald-700'
                  : readinessOverall === 'partial'
                    ? 'border-amber-300 bg-amber-50 text-amber-700'
                    : 'border-rose-300 bg-rose-50 text-rose-700'
              }`}>
                {readinessOverall === 'complete' ? '已落地' : readinessOverall === 'partial' ? '部分落地' : '待落地'}
              </span>
              <button type="button" onClick={() => void runReadinessCheck(false)} disabled={readinessLoading || !projectUri} className={`px-3 py-1.5 text-xs disabled:opacity-60 ${btnBlueCls}`}>
                {readinessLoading ? '体检中...' : '运行体检'}
              </button>
              <button type="button" onClick={() => setShowRolePlaybook((v) => !v)} className={`px-3 py-1.5 text-xs ${btnGreenCls}`}>
                {showRolePlaybook ? '收起角色SOP' : '展开角色SOP'}
              </button>
            </div>
          </div>
          <div className="mt-3 h-2.5 w-full overflow-hidden rounded-full border border-slate-300 bg-slate-200">
            <div className="h-2.5 bg-gradient-to-r from-sky-500 to-emerald-500 transition-[width] duration-500" style={{ width: `${readinessPercent}%` }} />
          </div>
          <div className="mt-1 text-xs text-slate-600">当前落地度: {readinessPercent.toFixed(2)}%</div>

          {!!readinessLayers.length && (
            <div className="mt-3 grid gap-2 min-[1100px]:grid-cols-2">
              {readinessLayers.map((layer) => {
                const st = String(layer.status || 'missing')
                return (
                  <div key={layer.key} className="rounded-lg border border-slate-300 bg-white p-2.5">
                    <div className="flex items-center justify-between gap-2">
                      <div className="text-sm font-semibold text-slate-700">{layer.name}</div>
                      <span className={`rounded-full px-2 py-0.5 text-[11px] font-semibold ${
                        st === 'complete'
                          ? 'bg-emerald-100 text-emerald-700'
                          : st === 'partial'
                            ? 'bg-amber-100 text-amber-700'
                            : 'bg-rose-100 text-rose-700'
                      }`}>
                        {st === 'complete' ? '完成' : st === 'partial' ? '部分' : '缺失'}
                      </span>
                    </div>
                    <div className="mt-1 text-xs text-slate-500">{readinessAction[layer.key] || '补齐该层关键流程数据后重试体检'}</div>
                  </div>
                )
              })}
            </div>
          )}

          {showRolePlaybook && (
            <div className="mt-3 grid gap-2 min-[1200px]:grid-cols-2">
              {ROLE_PLAYBOOK.map((r) => (
                <div key={r.role} className="rounded-lg border border-slate-300 bg-white p-3">
                  <div className="text-sm font-bold text-slate-700">{r.title} <span className="text-xs text-slate-500">({r.role})</span></div>
                  <div className="mt-1 text-xs text-slate-500">目标: {r.goal}</div>
                  <div className="mt-2 text-xs font-semibold text-slate-600">操作行为</div>
                  <div className="text-xs text-slate-600">{r.actions.join('；')}</div>
                  <div className="mt-2 text-xs font-semibold text-slate-600">技术约束</div>
                  <div className="text-xs text-slate-600">{r.constraints.join('；')}</div>
                  <div className="mt-2 text-xs font-semibold text-slate-600">闭环路径</div>
                  <div className="text-xs text-slate-700 font-mono break-all">{r.chain}</div>
                </div>
              ))}
            </div>
          )}
        </div>

        <div className="grid gap-6 grid-cols-1 min-[1120px]:grid-cols-[460px_minmax(560px,1fr)] min-[1780px]:grid-cols-[460px_minmax(620px,1fr)_440px]">
        <div className={`${panelCls} wb-panel`}>
          <div className="mb-2 flex items-center justify-between">
            <div className="text-sm font-extrabold">步骤 1：Genesis 主权树</div>
            <span className="rounded-full bg-slate-800/90 border border-slate-700 px-2 py-0.5 text-[10px] text-slate-400">资产初始化</span>
          </div>
          <div className="grid grid-cols-[auto_1fr] gap-2 items-center">
            <button type="button" onClick={() => boqFileRef.current?.click()} className="border border-slate-700 rounded-lg px-3 py-2 bg-slate-950/80 text-slate-200 text-sm leading-5">选择清单文件</button>
            <div className={`text-sm leading-5 truncate ${fileName ? 'text-slate-200' : 'text-slate-500'}`}>{fileName || '未选择任何文件'}</div>
            <input ref={boqFileRef} type="file" accept=".csv,.xlsx,.xls" onChange={(e) => onSelectFile(e.target.files?.[0] || null)} className="hidden" />
          </div>
          <div className="mt-1 text-[11px] text-slate-400">支持 .csv / .xlsx / .xls；建议优先使用 .xlsx 或 CSV</div>
          <button type="button" onClick={() => void importGenesis()} disabled={importing || !file} className={`mt-2 w-full px-3 py-2 disabled:opacity-60 font-bold ${btnBlueCls}`}>{importing ? '锚定中...' : '导入并锚定清单'}</button>
          {(importing || importJobId) && (
            <div className="mt-2 rounded-lg border border-slate-700/70 bg-slate-950/60 p-2">
              <div className="flex items-center justify-between text-xs text-slate-300">
                <span>{importStatusText || '执行中'}</span>
                <span>{Math.max(0, Math.min(100, importProgress))}%</span>
              </div>
              <div className="mt-1 h-2 w-full overflow-hidden rounded-full border border-slate-700/80 bg-slate-900">
                <div
                  className="h-2 bg-sky-500 transition-[width] duration-500"
                  style={{ width: `${Math.max(0, Math.min(100, importProgress))}%` }}
                />
              </div>
            </div>
          )}
          {!!importError && (
            <div className="mt-2 rounded-lg border border-rose-500/70 bg-rose-950/40 p-2 text-xs text-rose-200">
              导入失败原因：{importError}
            </div>
          )}
          <div className="mt-3 flex items-center justify-between">
            <div className="text-xs text-slate-400">核心信息优先展示</div>
            <button
              type="button"
              onClick={() => setShowLeftSummary((v) => !v)}
              className={`px-3 py-1.5 text-xs ${btnBlueCls}`}
            >
              {showLeftSummary ? '收起资产摘要' : '展开资产摘要'}
            </button>
          </div>
          {showLeftSummary && (
            <div className="border border-slate-700/70 rounded-xl p-3 mt-2 mb-3 bg-slate-900/50 text-sm leading-6">
              <div>设计总量(BOM): {(summary.design > 0 ? summary.design : summary.contract).toLocaleString()}</div>
              <div className="text-xs text-slate-400">批复总量: {summary.contract.toLocaleString()}</div>
              <div>已消耗量: {consumedTotal.toLocaleString()}</div>
              <div>已结算量: {summary.settled.toLocaleString()}</div>
              <div>剩余额度: {availableTotal.toLocaleString()}</div>
              <div className="w-full h-2.5 bg-slate-950 rounded-full overflow-hidden border border-slate-700/70 mt-1">
                <div style={{ width: `${Math.max(0, Math.min(100, summary.pct))}%` }} className="h-2 bg-green-600" />
              </div>
              <div className="text-xs text-emerald-300 mt-1">当前进度: {summary.pct.toFixed(2)}%</div>
            </div>
          )}
          <div className="grid grid-cols-[1fr_auto] gap-2 mb-3">
            <input
              value={treeQuery}
              onChange={(e) => setTreeQuery(e.target.value)}
              placeholder="搜索细目号 / 名称"
              className={inputBaseCls}
            />
            <button
              type="button"
              onClick={() => setTreeQuery('')}
              className={`px-3 py-2 text-sm ${btnBlueCls}`}
              disabled={!treeQuery.trim()}
            >
              清除
            </button>
          </div>
          {treeSearch.active && (
            <div className="text-xs text-slate-400 mb-2">
              命中 {treeSearch.matched.length} 项 · 展示 {treeSearch.visible.size} 节点
            </div>
          )}
          <div className="max-h-[560px] overflow-y-auto grid gap-2.5 pr-1">
            {!nodes.length && <div className="text-sm text-slate-500">上传 CSV 以生成 v:// 主权树</div>}
            {visibleRoots.map((r) => renderTree(r, 0))}
          </div>
        </div>

        <div className={`${panelCls} wb-panel`}>
          {/* header moved below with trace button */}
          <div className="flex items-center justify-between mb-2">
            <div className="flex items-center gap-2">
              <div className="text-sm font-extrabold">步骤 2：SPU 动态表单 + SnapPeg</div>
              <span className="rounded-full bg-slate-800/90 border border-slate-700 px-2 py-0.5 text-[10px] text-slate-400">执行层</span>
              <span className={`rounded-full border px-2 py-0.5 text-[10px] ${hashing ? 'border-amber-500/60 text-amber-300' : 'border-emerald-500/60 text-emerald-300'}`}>
                SnapPeg 数量 {hashing ? '计算中...' : evidence.length}
              </span>
            </div>
            <button type="button" onClick={() => setTraceOpen(true)} className={`px-3 py-1.5 text-xs ${btnBlueCls}`}>溯源图谱</button>
          </div>
          <div className="border border-slate-700/70 rounded-xl p-3 mb-3 text-sm">
            <div className="text-xs text-sky-300 mb-1">当前节点</div>
            <div className="break-all">{activePath || active?.uri || '-'}</div>
            <div className="mt-2 text-xs text-slate-400">
              模板绑定: {templateDisplay}
            </div>
            <div className={`text-xs ${isSpecBound ? 'text-emerald-300' : 'text-amber-300'}`}>
              规范绑定: {specBinding || (isContractSpu ? '合同凭证类' : '未绑定')} {gateBinding ? `· 门控 ${gateBinding}` : ''}
            </div>
            <div className="text-xs text-slate-500">
              自动预填: {displayMeta.unitProject} / {displayMeta.subdivisionProject}
            </div>
            <div className="text-xs text-slate-500">
              构件类型: {toChineseCompType(compType)}
            </div>
            {!!contextError && (
              <div className="mt-2 text-xs text-amber-300 border border-amber-700/70 bg-amber-950/30 rounded-lg px-2 py-1.5">
                {contextError}
              </div>
            )}
            {!isSpecBound && (
              <div className="mt-2 text-xs text-rose-300 border border-rose-700/70 bg-rose-950/30 rounded-lg px-2 py-1.5">
                未绑定规范/门控，已锁定提交
              </div>
            )}
          </div>
          <div className="grid grid-cols-2 max-[1180px]:grid-cols-1 gap-3 mb-3">
            <input value={sampleId} onChange={(e) => setSampleId(e.target.value)} placeholder="样品编号" className={inputBaseCls} />
            <div className="border border-dashed border-slate-700 rounded-lg px-3 py-2 text-sm leading-5 text-slate-400">样品编号将写入 UTXO 识别码</div>
          </div>
          <div className="grid grid-cols-[1fr_1fr_auto] max-[1180px]:grid-cols-1 gap-3 mb-3">
            <select value={compType} onChange={(e) => setCompType(e.target.value)} className={inputBaseCls}>
              {componentTypeOptions.map((opt) => (
                <option key={opt.value} value={opt.value}>{opt.label}</option>
              ))}
            </select>
            <input value={executorDid} onChange={(e) => setExecutorDid(e.target.value)} placeholder="执行人 DID" className={inputBaseCls} />
            <button type="button" disabled={!active?.isLeaf || loadingCtx} onClick={() => active?.uri && void loadContext(active.uri, compType)} className={`px-3 py-2 text-sm disabled:opacity-60 ${btnBlueCls}`}>{loadingCtx ? '加载中...' : '加载门控'}</button>
          </div>
          <div className="border border-slate-700 rounded-xl overflow-hidden mb-3">
            <div className="wb-table-head sticky top-0 z-10 grid grid-cols-[1.3fr_1fr_1fr_.55fr] bg-slate-950 font-bold text-slate-200 border-b border-slate-700">
              <span>{isContractSpu ? '凭证字段' : '检验项目'}</span>
              <span>{isContractSpu ? '要求' : '设计/标准值'}</span>
              <span>{isContractSpu ? '填报值' : '实测值'}</span>
              <span>{isContractSpu ? '状态' : '判定'}</span>
            </div>
            <div className="max-h-[250px] overflow-y-auto">
              {!formSchema.length && (
                <div className="p-4 text-xs text-rose-300">
                  未绑定规范/门控或未解析到 SPU 条款，已锁定执行。
                </div>
              )}
              {formSchema.map((row, idx) => {
                const k = String(row.field || `f_${idx}`)
                const val = form[k] || ''
                const st = evalNorm(String(row.operator || ''), String(row.default || ''), val)
                const c = st === 'success' ? '#22C55E' : st === 'fail' ? '#EF4444' : '#64748B'
                const bg = st === 'success' ? 'rgba(34,197,94,0.12)' : st === 'fail' ? 'rgba(239,68,68,0.12)' : 'transparent'
                return (
                  <div key={`${k}-${idx}`} className="wb-table-row grid grid-cols-[1.3fr_1fr_1fr_.55fr] border-t border-slate-800 items-center" style={{ background: bg }}>
                    <div>{toChineseMetricLabel(String(row.label || ''), k)}</div>
                    <div className="text-slate-400">{toChineseRuleText(String(row.operator || ''), String(row.default || '-'), String(row.unit || ''))}</div>
                    <div className="grid grid-cols-[1fr_auto] items-center gap-2">
                      <input
                        value={val}
                        inputMode={String(row.operator || '').toLowerCase() === 'present' ? 'text' : 'decimal'}
                        onChange={(e) => {
                          const raw = e.target.value
                          const nextVal = String(row.operator || '').toLowerCase() === 'present' ? raw : sanitizeMeasuredInput(raw)
                          setForm((p) => ({ ...p, [k]: nextVal }))
                        }}
                        className="rounded-md px-2.5 py-1.5 bg-slate-950 text-slate-100 text-sm"
                        style={{ border: `1px solid ${c}` }}
                        placeholder={isContractSpu ? '请输入' : '请输入数值'}
                      />
                      <span className="text-xs text-slate-400">{row.unit || ''}</span>
                    </div>
                    <div style={{ color: c, fontWeight: 700 }}>{st === 'success' ? '合格' : st === 'fail' ? '不合格' : '待判定'}</div>
                  </div>
                )
              })}
            </div>
          </div>
          <div className="grid grid-cols-2 max-[1180px]:grid-cols-1 gap-3 mb-3">
            <div className="rounded-xl border border-emerald-700/60 bg-emerald-950/25 p-3">
              <div className="text-xs text-emerald-300 mb-1">双合格门控</div>
              <div className="text-sm font-semibold text-slate-100">现场质检: {gateStats.qcStatus}</div>
              <div className="text-sm font-semibold text-slate-100 mt-1">实验佐证: {gateStats.labStatus}</div>
              {!isContractSpu && gateStats.labTotal > 0 && (
                <div className="text-xs text-slate-300 mt-1">
                  实验室证明: {gateStats.labPass}/{gateStats.labTotal}
                  {gateStats.labLatestPass && <span className="ml-2">最新 PASS: {gateStats.labLatestPass}</span>}
                  {gateStats.labLatestHash && <div className="mt-1 text-[11px] text-slate-400 break-all">Proof Hash: {gateStats.labLatestHash}</div>}
                </div>
              )}
              {!isContractSpu && !gateStats.labTotal && (
                <div className="text-xs text-amber-200 mt-1">未检测到实验室 Proof Hash，请先录入 LabPeg</div>
              )}
              <div className={`mt-2 text-xs font-bold ${gateStats.dualQualified ? 'text-emerald-300' : 'text-amber-300'}`}>
                双合格门控: {gateStats.dualQualified ? '通过' : '未通过'}
              </div>
              {!gateStats.dualQualified && active?.isLeaf && (
                <button
                  type="button"
                  onClick={() => void recordRejectTrip()}
                  disabled={rejecting || !inputProofId}
                  className={`mt-2 w-full px-3 py-2 text-xs font-bold rounded-lg border border-rose-500/70 bg-rose-950/40 text-rose-200 hover:bg-rose-900/40 disabled:opacity-60`}
                >
                  {rejecting ? '记录中...' : '记录不合格（Reject Trip）'}
                </button>
              )}
            </div>
            <div className="rounded-xl border border-sky-700/60 bg-sky-950/20 p-3">
            <div className="text-xs text-sky-300 mb-1">规范判定概览（NormPeg）</div>
              <div className="text-sm text-slate-100">总项: {gateStats.total}</div>
              <div className="text-sm text-emerald-300">合格: {gateStats.pass}</div>
              <div className="text-sm text-red-300">不合格: {gateStats.fail}</div>
              <div className="text-sm text-amber-200">待检: {gateStats.pending}</div>
            </div>
          </div>
          <div className="grid grid-cols-2 max-[1180px]:grid-cols-1 gap-3 mb-3">
            <input value={lat} onChange={(e) => setLat(e.target.value)} placeholder="GPS 纬度" className={inputBaseCls} />
            <input value={lng} onChange={(e) => setLng(e.target.value)} placeholder="GPS 经度" className={inputBaseCls} />
          </div>
          <div className="grid grid-cols-[auto_1fr] gap-2 items-center">
            <button type="button" onClick={() => evidenceFileRef.current?.click()} className="border border-slate-700 rounded-lg px-3 py-2 bg-slate-950/80 text-slate-200 text-sm leading-5">选择物证照片</button>
            <div className={`text-sm leading-5 truncate ${evidenceName ? 'text-slate-200' : 'text-slate-500'}`}>{evidenceName || '未选择任何文件'}</div>
            <input ref={evidenceFileRef} type="file" multiple accept="image/*" onChange={(e) => void onEvidence(e.target.files)} className="hidden" />
          </div>
          <div className="mt-2 flex items-center justify-between text-xs text-slate-400">
            <span>物证哈希（SnapPeg）</span>
            <span className={`rounded-full px-2 py-0.5 border ${hashing ? 'border-amber-500/60 text-amber-300' : 'border-emerald-500/60 text-emerald-300'}`}>
              {hashing ? '计算中...' : `数量 ${evidence.length}`}
            </span>
          </div>
          <div className={`mt-1 text-xs ${geoValid ? 'text-emerald-300' : 'text-amber-300'}`}>
            位置校验: {geoValid ? '坐标已采集' : '疑似虚假影像（坐标缺失）'}
          </div>
          {!!geoFenceWarning && (
            <div className="mt-1 text-xs text-rose-300">
              位置警告: {geoFenceWarning}
            </div>
          )}
          <div className="grid grid-cols-2 gap-2 max-h-[190px] overflow-y-auto mt-3 mb-3">
            {evidence.map((x) => (
              <button type="button" key={x.hash} onClick={() => { setEvidenceFocus(x); setEvidenceOpen(true) }} className="relative rounded-lg overflow-hidden border border-slate-700 p-0 bg-transparent">
                <img src={x.url} alt={x.name} className="w-full h-[108px] object-cover block" />
                <div className="absolute inset-0 bg-gradient-to-t from-slate-950/80 to-slate-950/20 text-slate-200 text-[11px] leading-4 p-2 flex flex-col justify-end gap-0.5">
                  <div>v:// {active?.uri || '-'}</div>
                  <div>GPS: {lat}, {lng}</div>
                  <div>NTP: {x.ntp}</div>
                  <div>DID: {executorDid}</div>
                  <div>样品: {sampleId || '-'}</div>
                </div>
              </button>
            ))}
          </div>
          <div className="mb-3 rounded-xl border border-slate-700/70 bg-slate-950/30 p-2">
            <button
              type="button"
              onClick={() => setShowAdvancedExecution((v) => !v)}
              className="w-full text-left text-sm font-semibold text-slate-200 px-2 py-1.5 hover:text-white"
            >
              高级执行面板 {showAdvancedExecution ? '▲' : '▼'}
            </button>
          </div>
          {showAdvancedExecution && (
          <>
          <div className="border border-dashed border-slate-700 rounded-xl p-3 mb-3">
            <div className="text-xs font-extrabold mb-1">变更补差 (Delta UTXO)</div>
            <div className="grid grid-cols-2 max-[1180px]:grid-cols-1 gap-3 mb-3">
              <input value={deltaAmount} onChange={(e) => setDeltaAmount(e.target.value)} placeholder="变更数量 (+/-)" className={inputBaseCls} />
              <input value={deltaReason} onChange={(e) => setDeltaReason(e.target.value)} placeholder="变更原因" className={inputBaseCls} />
            </div>
            <button type="button" onClick={() => void applyDelta()} disabled={applyingDelta || !active?.isLeaf} className={`w-full px-3 py-2 disabled:opacity-60 font-bold text-sm ${btnAmberCls}`}>{applyingDelta ? '提交中...' : '提交变更补差'}</button>
            {!!variationRes && <div className="text-[11px] text-amber-200 mt-1">变更 Proof: {String(variationRes.output_proof_id || '')}</div>}
          </div>
          <div className="border border-dashed border-slate-700 rounded-xl p-3 mb-3">
            <div className="text-xs font-extrabold mb-1">离线封存 / 重放</div>
            <div className="grid grid-cols-2 gap-2 mb-3">
              <select value={offlineType} onChange={(e) => setOfflineType(e.target.value as OfflinePacketType)} className={inputXsCls}>
                <option value="quality.check">离线质检封存</option>
                <option value="variation.apply">离线变更补差</option>
              </select>
              <button type="button" onClick={() => void sealOfflinePacket()} className={`px-3 py-2 text-sm font-bold ${btnBlueCls}`}>封存当前动作</button>
            </div>
            <div className="flex items-center gap-2 mb-3">
              <input type="checkbox" checked={offlineStopOnError} onChange={(e) => setOfflineStopOnError(e.target.checked)} />
              <span className="text-xs text-slate-400">遇错即停</span>
            </div>
            <div className="grid grid-cols-[1fr_auto_auto] gap-2 mb-3">
              <button type="button" onClick={() => void replayOffline()} disabled={offlineReplaying} className={`px-3 py-2 text-sm font-bold ${btnGreenCls}`}>{offlineReplaying ? '重放中...' : `重放队列 (${offlinePackets.length})`}</button>
              <button type="button" onClick={() => exportOfflinePackets()} disabled={!offlinePackets.length} className={`px-3 py-2 text-sm disabled:opacity-60 ${btnBlueCls}`}>导出</button>
              <button type="button" onClick={() => clearOfflinePackets()} disabled={!offlinePackets.length} className="rounded-lg border border-slate-600 px-3 py-2 text-sm bg-slate-900 text-slate-200 disabled:opacity-60">清空</button>
            </div>
            <div className="grid grid-cols-[1fr_auto] gap-2 mb-3">
              <div className="grid grid-cols-[auto_1fr] gap-2 items-center">
                <button type="button" disabled={offlineImporting} onClick={() => offlineImportRef.current?.click()} className={`px-3 py-2 text-sm font-bold ${btnBlueCls}`}>{offlineImporting ? '导入中...' : '导入离线包'}</button>
                <div className={`text-sm truncate ${offlineImportName ? 'text-slate-200' : 'text-slate-500'}`}>{offlineImportName || '未选择任何文件'}</div>
                <input ref={offlineImportRef} type="file" accept="application/json,.json" onChange={(e) => void importOfflinePackets(e.target.files?.[0] || null)} className="hidden" />
              </div>
            </div>
            {!!offlineReplay && (
              <div className="text-[11px] text-slate-400">
                重放完成: {String(offlineReplay.replayed_count || 0)} 条 · 错误 {String(offlineReplay.error_count || 0)} 条
              </div>
            )}
            <div className="max-h-[160px] overflow-y-auto mt-2 grid gap-2">
              {!offlinePackets.length && <div className="text-xs text-slate-500">暂无离线封存包</div>}
              {offlinePackets.map((p) => {
                const pid = String(p.offline_packet_id || '')
                const label = String(p.packet_type || p.action || 'offline')
                const uri = String(p.boq_item_uri || '')
                return (
                  <div key={pid} className="border border-slate-800 rounded-lg p-2 grid grid-cols-[1fr_auto] gap-2 items-center">
                    <div className="text-[11px] text-slate-200 break-all">
                      <div>{label}</div>
                      <div className="text-slate-400">{uri}</div>
                      <div className="text-slate-500">{pid}</div>
                    </div>
                    <button type="button" onClick={() => removeOfflinePacket(pid)} className="border border-slate-700 rounded px-2 py-0.5 bg-slate-950 text-slate-200 text-[11px]">移除</button>
                  </div>
                )
              })}
            </div>
          </div>
          </>
          )}
          <div className="mt-3 rounded-xl border border-slate-700/70 bg-slate-950/30 p-3">
            <div className="text-xs font-semibold text-slate-300 mb-2">BOM 守恒校验</div>
            <div className="grid grid-cols-3 gap-2 text-xs text-slate-300 mb-2">
              <div>设计总量: {baselineTotal.toLocaleString()}</div>
              <div>已消耗量: {effectiveSpent.toLocaleString()}</div>
              <div>剩余额度: {availableTotal.toLocaleString()}</div>
            </div>
            <div className="grid grid-cols-[1fr_auto] gap-2 items-center">
              <input
                value={claimQty}
                onChange={(e) => setClaimQty(e.target.value)}
                placeholder="本次申报量"
                className={inputBaseCls}
              />
              <span className={`text-xs ${exceedBalance ? 'text-rose-300' : 'text-emerald-300'}`}>
                {exceedBalance ? '超出余额' : '余额充足'}
              </span>
            </div>
            <div className="mt-2 h-2.5 w-full overflow-hidden rounded-full border border-slate-700/70 bg-slate-900">
              <div
                className={`h-2.5 ${exceedBalance ? 'bg-rose-500' : 'bg-emerald-500'}`}
                style={{ width: `${Math.max(0, Math.min(100, baselineTotal > 0 ? ((effectiveSpent + claimQtyValue) * 100) / baselineTotal : 0))}%` }}
              />
            </div>
            <div className="mt-1 text-[11px] text-slate-400">
              公式：申报量 + 已消耗量 ≤ 设计总量(BOM)
            </div>
          </div>
          <button
            type="button"
            onClick={() => void submitTrip()}
            disabled={executing || !active?.isLeaf || !inputProofId || !isSpecBound || !gateStats.dualQualified || exceedBalance}
            className={`mt-3 w-full px-3 py-2 disabled:opacity-60 font-bold ${exceedBalance ? btnRedCls : btnGreenCls}`}
          >
            {executing ? '提交中...' : '确认提交'}
          </button>
        </div>

        <div className={`${panelCls} wb-panel min-[980px]:col-span-2 min-[1480px]:col-span-1`}>
          <div className="mb-2 flex items-center justify-between">
            <div className="text-sm font-extrabold">步骤 3：OrdoSign + DocPeg 预览</div>
            <span className="rounded-full bg-slate-800/90 border border-slate-700 px-2 py-0.5 text-[10px] text-slate-400">共识层</span>
          </div>
          <div className="border border-slate-700 rounded-xl p-3 mb-3 text-sm leading-6">
            <div className="text-sky-300 mb-1">DID 链路</div>
            <div>施工方: {executorDid}</div>
            <div>监理: {supervisorDid}</div>
            <div>业主: {ownerDid}</div>
          </div>
          <div className="grid gap-3 mb-3">
            <input value={supervisorDid} onChange={(e) => setSupervisorDid(e.target.value)} placeholder="监理 DID" className={inputBaseCls} />
            <input value={ownerDid} onChange={(e) => setOwnerDid(e.target.value)} placeholder="业主 DID" className={inputBaseCls} />
          </div>
          <div className="mb-3 border border-dashed border-slate-700 rounded-xl p-3 text-xs text-slate-400 break-all">验真 URI: {verifyUri || '-'}</div>
          <div className="mb-3 border border-dashed border-slate-700 rounded-xl p-3 text-xs text-slate-500 break-all">
            模板来源: {String(((signRes?.docpeg || {}) as Record<string, unknown>).selected_template_path || templateBinding.template_path || templateBinding.fallback_template || '-')}
          </div>
          {pdfB64 ? (
            <iframe title="docpeg-preview" src={`data:application/pdf;base64,${pdfB64}`} className="w-full h-[292px] border border-slate-700 rounded-lg bg-white" />
          ) : (
            <div className="border border-slate-700 rounded-lg h-[292px] grid place-items-center text-slate-500 text-sm">签认完成后生成 DocPeg 预览</div>
          )}
          <div className="mt-3 border border-slate-700 rounded-xl p-3 grid grid-cols-[140px_1fr] max-[600px]:grid-cols-1 gap-3">
            <div className="w-[140px] h-[140px] border border-slate-800 bg-white grid place-items-center">
              <img src={qrSrc} alt="DocPeg 验真二维码" className="w-[128px] h-[128px]" />
            </div>
            <div className="text-xs text-slate-400 leading-5">
              扫码验真 DocPeg
              <div className="mt-1 text-slate-200 break-all">{verifyUri || '暂无 URI'}</div>
            </div>
          </div>
          <div className="mt-3 rounded-xl border border-slate-700/70 bg-slate-950/30 p-2">
            <button
              type="button"
              onClick={() => setShowAdvancedConsensus((v) => !v)}
              className="w-full text-left text-sm font-semibold text-slate-200 px-2 py-1.5 hover:text-white"
            >
              高级共识与审计面板 {showAdvancedConsensus ? '▲' : '▼'}
            </button>
          </div>
          {showAdvancedConsensus && (
          <>
          <div className="border border-dashed border-slate-700 rounded-xl p-3 mt-3">
            <div className="text-xs font-extrabold mb-1">扫码即确权</div>
            <div className="text-[11px] text-slate-400 mb-2">扫码 URI: {scanConfirmUri || '未生成'}</div>
            <div className="grid gap-2">
              <input value={scanProofId} onChange={(e) => setScanProofId(e.target.value)} placeholder="待确权证明ID" className={inputBaseCls} />
              <textarea value={scanPayload} onChange={(e) => setScanPayload(e.target.value)} placeholder="扫码凭据（scan_confirm_token）" rows={3} className={`${inputBaseCls} resize-y`} />
              <input value={scanDid} onChange={(e) => setScanDid(e.target.value)} placeholder="扫码人 DID" className={inputBaseCls} />
              <div className="grid grid-cols-2 gap-2">
                <button type="button" onClick={() => setScanPayload(scanConfirmToken)} disabled={!scanConfirmToken} className={`px-3 py-2 text-sm disabled:opacity-60 ${btnBlueCls}`}>填充扫码凭据</button>
                <button type="button" onClick={() => void doScanConfirm()} disabled={scanning} className={`px-3 py-2 text-sm font-bold ${btnGreenCls}`}>{scanning ? '确权中...' : '执行扫码确权'}</button>
              </div>
              {!!scanRes && <div className="text-[11px] text-emerald-300">确权完成: {String((scanRes as Record<string, unknown>).output_proof_id || '')}</div>}
            </div>
          </div>
          <div className="border border-dashed border-slate-700 rounded-xl p-3 mt-3">
            <div className="text-xs font-extrabold mb-1">单位工程默克尔根</div>
            <div className="grid gap-2">
              <input value={unitCode} onChange={(e) => setUnitCode(e.target.value)} placeholder="单位工程号 (如 403)" className={inputBaseCls} />
              <input value={unitProofId} onChange={(e) => setUnitProofId(e.target.value)} placeholder="证明ID（可选）" className={inputBaseCls} />
              <input value={unitMaxRows} onChange={(e) => setUnitMaxRows(e.target.value)} placeholder="最大扫描行数" className={inputBaseCls} />
              <div className="grid grid-cols-[1fr_auto] gap-2">
                <button type="button" onClick={() => void calcUnitMerkle()} disabled={unitLoading} className={`px-3 py-2 font-bold text-sm ${btnAmberCls}`}>{unitLoading ? '计算中...' : '生成单位工程根哈希'}</button>
                <button type="button" onClick={() => useCurrentProofForUnit()} className={`px-3 py-2 text-sm ${btnBlueCls}`}>使用当前细目</button>
              </div>
              {!!unitRes && (
                <div className="text-[11px] text-slate-400 break-all">
                  <div>单位工程根: {String(unitRes.unit_root_hash || '')}</div>
                  <div>项目总指纹: {String(unitRes.global_project_fingerprint || '')}</div>
                  <div>叶子数量: {String(unitRes.leaf_count || 0)}</div>
                  <div>请求叶子: {String(((unitRes.requested_leaf || {}) as Record<string, unknown>).item_uri || '')}</div>
                </div>
              )}
              {!!unitRes && (
                <div className="border border-slate-800 rounded-lg p-2 mt-1">
                  <div className="text-xs font-extrabold mb-2">本地校验器</div>
                  <div className="grid grid-cols-[1fr_auto] gap-2 mb-2">
                    <button type="button" onClick={() => void verifyUnitMerkle()} disabled={unitVerifying} className="border border-emerald-500/80 rounded-lg px-3 py-2 bg-emerald-900/80 text-emerald-100 font-bold text-sm">{unitVerifying ? '校验中...' : '校验链路一致性'}</button>
                    <div className={`text-[11px] ${unitVerifyMsg.includes('通过') ? 'text-emerald-300' : 'text-red-300'} grid items-center`}>{unitVerifyMsg || '未校验'}</div>
                  </div>
                  {!!itemRootComputed && (
                    <div className="text-[11px] text-slate-400 break-all">
                      <div className="grid grid-cols-[1fr_auto] gap-2">
                        <div>计算叶子根: {itemRootComputed}</div>
                        <button type="button" onClick={() => void copyText('叶子根', itemRootComputed)} className="border border-slate-700 rounded px-1.5 py-0.5 text-[11px] text-slate-200">复制</button>
                      </div>
                      <div className="grid grid-cols-[1fr_auto] gap-2 mt-1">
                        <div>单位叶子哈希: {unitLeafComputed}</div>
                        <button type="button" onClick={() => void copyText('单位叶子哈希', unitLeafComputed)} className="border border-slate-700 rounded px-1.5 py-0.5 text-[11px] text-slate-200">复制</button>
                      </div>
                      <div className="grid grid-cols-[1fr_auto] gap-2 mt-1">
                        <div>计算项目根: {projectRootComputed}</div>
                        <button type="button" onClick={() => void copyText('项目根', projectRootComputed)} className="border border-slate-700 rounded px-1.5 py-0.5 text-[11px] text-slate-200">复制</button>
                      </div>
                      {!!copiedMsg && <div className="mt-1 text-emerald-300">{copiedMsg}</div>}
                    </div>
                  )}
                  {(itemPathSteps.length > 0 || unitPathSteps.length > 0) && (
                    <div className="mt-2 grid gap-2">
                      <div className="flex justify-end">
                        <button type="button" onClick={() => exportMerkleJson()} className="border border-blue-700 rounded px-2 py-1 text-[11px] bg-blue-900 text-blue-100">导出默克尔 JSON</button>
                      </div>
                      <div>
                        <div className="text-[11px] text-slate-200 mb-1">叶子路径演算</div>
                        <div className="grid gap-2">
                          {itemPathSteps.length === 0 && <div className="text-[11px] text-slate-500">无路径</div>}
                          {itemPathSteps.map((step, idx) => (
                            <div key={`item-step-${idx}`} className="border border-slate-800 rounded p-2 text-[11px]">
                              <div>深度 {step.depth} · 方向 {step.position}</div>
                              <div className="text-slate-400 break-all">兄弟哈希: {step.sibling_hash}</div>
                              <div className="text-emerald-300 break-all">合并哈希: {step.combined_hash}</div>
                            </div>
                          ))}
                        </div>
                      </div>
                      <div>
                        <div className="text-[11px] text-slate-200 mb-1">单位路径演算</div>
                        <div className="grid gap-2">
                          {unitPathSteps.length === 0 && <div className="text-[11px] text-slate-500">无路径</div>}
                          {unitPathSteps.map((step, idx) => (
                            <div key={`unit-step-${idx}`} className="border border-slate-800 rounded p-2 text-[11px]">
                              <div>深度 {step.depth} · 方向 {step.position}</div>
                              <div className="text-slate-400 break-all">兄弟哈希: {step.sibling_hash}</div>
                              <div className="text-emerald-300 break-all">合并哈希: {step.combined_hash}</div>
                            </div>
                          ))}
                        </div>
                      </div>
                    </div>
                  )}
                </div>
              )}
            </div>
          </div>
          </>
          )}
        </div>
        </div>
      </div>

      {signOpen && (
        <div className="fixed inset-0 bg-slate-950/70 z-[1200] grid place-items-center">
          <div className="w-[460px] max-w-[92vw] rounded-xl border border-slate-700 bg-slate-950 text-slate-100 p-4">
            <div className="text-sm font-extrabold mb-2">OrdoSign 共识签认</div>
            <div className="text-xs text-slate-400 mb-3">审核中 → 已批准</div>
            <div className="grid gap-2 mb-3">
              {[{ k: 1, l: '施工方', d: executorDid }, { k: 2, l: '监理', d: supervisorDid }, { k: 3, l: '业主', d: ownerDid }].map((x) => (
                <div key={x.k} className="border border-slate-700 rounded-lg p-2 flex items-center justify-between text-xs">
                  <div>
                    <div>{x.l} 签名</div>
                    <div className="text-slate-400 mt-1">{x.d}</div>
                  </div>
                  <div className={`font-bold ${signStep >= x.k ? 'text-emerald-300' : 'text-slate-500'}`}>{signStep >= x.k ? '已签' : '待签'}</div>
                </div>
              ))}
            </div>
            <div className="flex justify-end gap-2">
              <button type="button" onClick={() => setSignOpen(false)} disabled={signing} className="border border-slate-700 rounded-lg px-3 py-2 bg-slate-900 text-slate-200">取消</button>
              <button type="button" onClick={() => void doSign()} disabled={signing} className={`px-3 py-2 font-bold ${btnAmberCls}`}>{signing ? '签认中...' : '执行多方签认'}</button>
            </div>
          </div>
        </div>
      )}
      {evidenceOpen && evidenceFocus && (
        <div className="fixed inset-0 bg-slate-950/70 z-[1200] grid place-items-center">
          <div className="w-[520px] max-w-[92vw] rounded-xl border border-slate-700 bg-slate-950 text-slate-100 p-4">
            <div className="text-sm font-extrabold mb-2">SnapPeg 物证详情</div>
            <img src={evidenceFocus.url} alt={evidenceFocus.name} className="w-full rounded-lg border border-slate-700 mb-2" />
            <div className="text-xs text-slate-400 break-all">
              <div>哈希: {evidenceFocus.hash}</div>
              <div>签名 DID: {executorDid}</div>
              <div>定位: {lat}, {lng}</div>
              <div>授时戳: {evidenceFocus.ntp}</div>
              <div>样品: {sampleId || '-'}</div>
              <div>路径: {active?.uri || '-'}</div>
            </div>
            <div className="flex justify-end mt-3">
              <button type="button" onClick={() => setEvidenceOpen(false)} className="border border-slate-700 rounded-lg px-3 py-2 bg-slate-900 text-slate-200">关闭</button>
            </div>
          </div>
        </div>
      )}
      {traceOpen && (
        <div className="fixed inset-0 bg-slate-950/70 z-[1200] grid place-items-center">
          <div className="w-[560px] max-w-[92vw] rounded-xl border border-slate-700 bg-slate-950 text-slate-100 p-4">
            <div className="text-sm font-extrabold mb-2">样品溯源图谱</div>
            <div className="grid gap-2 text-xs">
              {[
                { title: '0# 台账清单', value: active?.uri || '-' },
                { title: '现场样品', value: sampleId || '-' },
                { title: '实验结果', value: String(((execRes?.trip || {}) as Record<string, unknown>).output_proof_id || '') || inputProofId || '-' },
                { title: 'DocPeg 报告', value: verifyUri || '-' },
                { title: '总证明哈希', value: totalHash || '-' },
              ].map((node, idx) => (
                <div key={`${node.title}-${idx}`} className="border border-slate-700 rounded-lg p-2">
                  <div className="text-sky-300 mb-1">{node.title}</div>
                  <div className="break-all text-slate-100">{node.value}</div>
                </div>
              ))}
            </div>
            <div className="flex justify-end mt-3">
              <button type="button" onClick={() => setTraceOpen(false)} className="border border-slate-700 rounded-lg px-3 py-2 bg-slate-900 text-slate-200">关闭</button>
            </div>
          </div>
        </div>
      )}
      {docModalOpen && pdfB64 && (
        <div className="fixed inset-0 bg-slate-950/70 z-[1200] grid place-items-center">
          <div className="w-[640px] max-w-[96vw] rounded-xl border border-slate-700 bg-slate-950 text-slate-100 p-4">
            <div className="text-sm font-extrabold mb-2">DocPeg 正式报告</div>
            <iframe title="docpeg-modal" src={`data:application/pdf;base64,${pdfB64}`} className="w-full h-[420px] border border-slate-700 rounded-lg bg-white" />
            <div className="mt-2 grid grid-cols-[140px_1fr] gap-2">
              <div className="w-[140px] h-[140px] border border-slate-800 bg-white grid place-items-center">
                <img src={qrSrc} alt="DocPeg 验真二维码" className="w-[128px] h-[128px]" />
              </div>
              <div className="text-[11px] text-slate-400 break-all">
                <div>验真 URI: {verifyUri || '-'}</div>
                <div>样品编号: {sampleId || '-'}</div>
                <div>路径: {active?.uri || '-'}</div>
              </div>
            </div>
            <div className="flex justify-end mt-3">
              <button type="button" onClick={() => setDocModalOpen(false)} className="border border-slate-700 rounded-lg px-3 py-2 bg-slate-900 text-slate-200">关闭</button>
            </div>
          </div>
        </div>
      )}
    </Card>
  )
}
