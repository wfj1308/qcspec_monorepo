import { useMemo } from 'react'

import {
  isTimeInWindow,
  parseTimeWindow,
} from './analysisUtils'
import {
  extractNodeGeo,
  haversineMeters,
} from './fileUtils'
import { deriveGateReason } from './NormEngine'
import type {
  Evidence,
  GateStats,
  TreeNode,
} from './types'

function asDict(value: unknown): Record<string, unknown> {
  return value && typeof value === 'object' && !Array.isArray(value) ? (value as Record<string, unknown>) : {}
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

const FINAL_PIECE_PROMPT = `Role: CoordOS 首席协议架构师
Task: 参照 18 份文档及 20260327-GPT 逻辑，补全共识仲裁、知识迁移与 AR 物理锚定。
1. 共识冲突检查器：detect_consensus_deviation() 对比签名量值，超阈值自动挂起结算 Trip。
2. 规则进化提取器：分析 proof_utxo 历史，提取 success_pattern 并更新 spec_dicts 权重建议。
3. AR 主权叠加层：GPS + 时空指纹渲染 v:// 节点，实现所见即所证。
完工态：Trip 自动流转；风险审计 24h；项目经验沉淀为智能标准。`

type Args = {
  active: TreeNode | null
  ctx: Record<string, unknown> | null
  lat: string
  lng: string
  nowTick: number
  specdictRes: Record<string, unknown> | null
  specdictNamespace: string
  arRes: Record<string, unknown> | null
  gateStats: GateStats
  execRes: Record<string, unknown> | null
  isContractSpu: boolean
  evidence: Evidence[]
  specBinding: string
  gateBinding: string
}

export function useSovereignGeoSpecdictState({
  active,
  ctx,
  lat,
  lng,
  nowTick,
  specdictRes,
  specdictNamespace,
  arRes,
  gateStats,
  execRes,
  isContractSpu,
  evidence,
  specBinding,
  gateBinding,
}: Args) {
  const nodeMetadata = useMemo(() => {
    const node = (ctx?.node || {}) as Record<string, unknown>
    return (node.metadata || {}) as Record<string, unknown>
  }, [ctx])

  const geoAnchor = useMemo(() => extractNodeGeo(nodeMetadata), [nodeMetadata])
  const geoDistance = useMemo(() => {
    if (!geoAnchor) return null
    const la = Number(lat)
    const ln = Number(lng)
    if (!Number.isFinite(la) || !Number.isFinite(ln)) return null
    return haversineMeters(la, ln, geoAnchor.lat, geoAnchor.lng)
  }, [geoAnchor, lat, lng])

  const temporalWindow = useMemo(() => {
    const raw =
      nodeMetadata.temporal_window || nodeMetadata.allowed_time_window || nodeMetadata.work_hours || nodeMetadata.time_window
    return parseTimeWindow(raw)
  }, [nodeMetadata])

  const temporalAllowed = useMemo(() => {
    if (!temporalWindow) return true
    const d = new Date(nowTick)
    const minutes = d.getHours() * 60 + d.getMinutes()
    return isTimeInWindow(minutes, temporalWindow)
  }, [nowTick, temporalWindow])

  const geoFenceActive = Boolean(geoAnchor)
  const geoFenceBlocked = geoFenceActive && (!geoDistance || geoDistance > (geoAnchor?.radiusM || 0))
  const temporalBlocked = geoFenceActive && !temporalAllowed
  const geoTemporalBlocked = geoFenceBlocked || temporalBlocked

  const specdictAnalysis = asDict((specdictRes || {}).analysis || specdictRes)
  const specdictRuleTotal = Number(specdictAnalysis.total_rules || (specdictRes || {}).total_rules || 0)
  const specdictHighRiskItems = Array.isArray(specdictAnalysis.high_risk) ? specdictAnalysis.high_risk : []
  const specdictBestPracticeItems = Array.isArray(specdictAnalysis.best_practice) ? specdictAnalysis.best_practice : []
  const specdictSuccessPatterns = Array.isArray(specdictAnalysis.success_pattern)
    ? specdictAnalysis.success_pattern
    : (Array.isArray(specdictAnalysis.success_patterns) ? specdictAnalysis.success_patterns : [])
  const specdictWeightEntries = Object.entries(asDict(
    specdictAnalysis.weight_suggestions || specdictAnalysis.weight_recommendations || specdictAnalysis.weight_hint || {},
  )).slice(0, 4)
  const specdictBundleUri = String(
    (specdictRes || {}).bundle_uri ||
    (specdictRes || {}).template_uri ||
    (specdictRes || {}).namespace_uri ||
    specdictNamespace ||
    '',
  )

  const gateReason = useMemo(() => deriveGateReason(gateStats), [gateStats])
  const displayMeta = useMemo(() => deriveNodeDisplayMeta(nodeMetadata, active), [active, nodeMetadata])
  const geoValid = useMemo(() => {
    const la = Number(lat)
    const ln = Number(lng)
    return Number.isFinite(la) && Number.isFinite(ln)
  }, [lat, lng])
  const geoFenceWarning = useMemo(() => {
    const raw = asDict((execRes || {}) as Record<string, unknown>)
    const stateData = asDict(raw.state_data || raw.state || {})
    return String(stateData.geo_fence_warning || '').trim()
  }, [execRes])
  const snappegReady = useMemo(() => {
    if (isContractSpu) return true
    if (!geoValid) return false
    if (evidence.length === 0) return false
    return evidence.every((item) => item.exifOk !== false)
  }, [evidence, geoValid, isContractSpu])

  const geoFenceStatusText = useMemo(() => {
    if (!geoFenceActive) return '未启用'
    if (geoTemporalBlocked) return '拦截中'
    return '通过'
  }, [geoFenceActive, geoTemporalBlocked])

  const isSpecBound = Boolean(specBinding || gateBinding || isContractSpu)
  const geoFormLocked = geoTemporalBlocked
  const evidenceLabel = isContractSpu ? '合同凭证附件' : 'SnapPeg 现场照'
  const evidenceAccept = isContractSpu ? 'image/*,application/pdf' : 'image/*'
  const evidenceHint = isContractSpu ? '支持图片/PDF' : '仅支持图片'
  const arItems = Array.isArray((arRes || {}).items) ? ((arRes || {}).items as Array<Record<string, unknown>>) : []

  return {
    geoAnchor,
    geoDistance,
    temporalWindow,
    temporalAllowed,
    geoFenceActive,
    geoFenceBlocked,
    temporalBlocked,
    geoTemporalBlocked,
    specdictAnalysis,
    specdictRuleTotal,
    specdictHighRisk: specdictHighRiskItems.length,
    specdictBestPractice: specdictBestPracticeItems.length,
    specdictHighRiskItems,
    specdictBestPracticeItems,
    specdictSuccessPatterns,
    specdictWeightEntries,
    specdictBundleUri,
    gateReason,
    displayMeta,
    geoValid,
    geoFenceWarning,
    snappegReady,
    geoFenceStatusText,
    geoFormLocked,
    evidenceLabel,
    evidenceAccept,
    evidenceHint,
    finalPiecePrompt: FINAL_PIECE_PROMPT,
    arItems,
    isSpecBound,
  }
}
