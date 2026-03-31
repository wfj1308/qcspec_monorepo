import { useMemo } from 'react'
import type {
  NormResolutionState,
  SovereignLifecycleStatus,
  SpuBadge,
  SpuKind,
  TreeNode,
} from './types'
import { resolveNormRefs } from './NormResolver'
import { formatNodeSegment } from './treeUtils'

type SessionInput = {
  projectUri: string
  apiProjectUri: string
  displayProjectUri: string
  projectId: string
  nodes: TreeNode[]
  byCode: Map<string, TreeNode>
  active: TreeNode | null
  ctx: Record<string, unknown> | null
  execRes: Record<string, unknown> | null
  signRes: Record<string, unknown> | null
  dtoRole: string
}

type SessionOutput = {
  nodePathMap: Map<string, string>
  activePath: string
  boundSpu: string
  isContractSpu: boolean
  spuKind: SpuKind
  spuBadge: SpuBadge
  stepLabel: string
  allowedRoles: string[]
  roleAllowed: boolean
  normResolution: NormResolutionState
  lifecycle: SovereignLifecycleStatus
}

function asDict(value: unknown): Record<string, unknown> {
  return value && typeof value === 'object' && !Array.isArray(value) ? (value as Record<string, unknown>) : {}
}

function deriveSpuKind(boundSpu: string, isContractSpu: boolean): SpuKind {
  const value = String(boundSpu || '').toUpperCase()
  if (value.includes('BRIDGE')) return 'bridge'
  if (value.includes('LANDSCAPE')) return 'landscape'
  if (isContractSpu) return 'contract'
  return 'physical'
}

function deriveSpuBadge(boundSpu: string, isContractSpu: boolean): SpuBadge {
  const value = String(boundSpu || '').toUpperCase()
  if (value.includes('BRIDGE')) return { label: '桥梁质检', cls: 'border-emerald-500/60 text-emerald-300 bg-emerald-950/30' }
  if (value.includes('LANDSCAPE')) return { label: '绿化验收', cls: 'border-lime-500/60 text-lime-300 bg-lime-950/30' }
  if (value.includes('REINFORCEMENT')) return { label: '钢筋质检', cls: 'border-sky-500/60 text-sky-300 bg-sky-950/30' }
  if (value.includes('CONCRETE')) return { label: '混凝土质检', cls: 'border-indigo-500/60 text-indigo-300 bg-indigo-950/30' }
  if (isContractSpu) return { label: '合同凭证', cls: 'border-amber-500/60 text-amber-300 bg-amber-950/30' }
  return { label: '实体工程', cls: 'border-slate-500/60 text-slate-300 bg-slate-950/30' }
}

function deriveLifecycle(active: TreeNode | null, execRes: Record<string, unknown> | null, signRes: Record<string, unknown> | null): SovereignLifecycleStatus {
  const signed = String(((signRes?.trip || {}) as Record<string, unknown>).output_proof_id || (signRes || {}).output_proof_id || '').trim()
  if (signed || active?.status === 'Settled') return 'Settled'
  const reviewing = String(((execRes?.trip || {}) as Record<string, unknown>).output_proof_id || '').trim()
  if (reviewing) return 'Pending_Audit'
  if (active?.status === 'Spending') return 'In_Trip'
  return 'Genesis'
}

export function useSovereignSession({
  projectUri,
  apiProjectUri,
  displayProjectUri,
  projectId,
  nodes,
  byCode,
  active,
  ctx,
  execRes,
  signRes,
  dtoRole,
}: SessionInput): SessionOutput {
  const nodePathMap = useMemo(() => {
    const map = new Map<string, string>()
    const base = String(displayProjectUri || '').replace(/\/$/, '')
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
    nodes.forEach((node) => build(node.code))
    return map
  }, [byCode, displayProjectUri, nodes])

  const activePath = useMemo(() => {
    if (!active) return ''
    return nodePathMap.get(active.code) || active.uri
  }, [active, nodePathMap])

  const boundSpu = useMemo(() => {
    const spuNode = asDict(ctx?.node)
    const spuMeta = asDict(ctx?.spu)
    return String(spuMeta.spu_code || spuMeta.spu_type || spuNode.spu || active?.spu || '').trim()
  }, [active?.spu, ctx])

  const isContractSpu = useMemo(() => {
    const value = String(boundSpu || '').toLowerCase()
    return value === 'spu_contract' || value.includes('contract') || value.includes('voucher')
  }, [boundSpu])

  const spuKind = useMemo(() => deriveSpuKind(boundSpu, isContractSpu), [boundSpu, isContractSpu])
  const spuBadge = useMemo(() => deriveSpuBadge(boundSpu, isContractSpu), [boundSpu, isContractSpu])
  const stepLabel = isContractSpu ? '步骤 2：合同凭证表单' : '步骤 2：SPU 动态表单 + SnapPeg'
  const lifecycle = useMemo(() => deriveLifecycle(active, execRes, signRes), [active, execRes, signRes])
  const normResolution = useMemo(() => resolveNormRefs(ctx, isContractSpu), [ctx, isContractSpu])

  const allowedRoles = useMemo(() => {
    const ctxRole = asDict(ctx?.role)
    const fromCtx = Array.isArray(ctxRole.allowed_dto_roles) ? ctxRole.allowed_dto_roles : []
    const normalized = fromCtx.map((item) => String(item || '').toUpperCase()).filter(Boolean)
    if (normalized.length) return normalized
    const code = String(active?.code || '')
    if (code.startsWith('403') || code.startsWith('405')) return ['AI', 'SUPERVISOR', 'OWNER']
    if (code.startsWith('401') || code.startsWith('101') || code.startsWith('102') || code.startsWith('600')) return ['SUPERVISOR', 'OWNER']
    if (isContractSpu) return ['OWNER', 'SUPERVISOR']
    return ['AI', 'SUPERVISOR', 'OWNER']
  }, [active?.code, ctx?.role, isContractSpu])

  const roleAllowed = useMemo(() => allowedRoles.includes(dtoRole), [allowedRoles, dtoRole])

  void projectUri
  void apiProjectUri
  void projectId

  return {
    nodePathMap,
    activePath,
    boundSpu,
    isContractSpu,
    spuKind,
    spuBadge,
    stepLabel,
    allowedRoles,
    roleAllowed,
    normResolution,
    lifecycle,
  }
}
