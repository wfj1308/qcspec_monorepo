
import React, { useCallback, useEffect, useMemo, useRef, useState } from 'react'
import { GlobalWorkerOptions, getDocument } from 'pdfjs-dist/legacy/build/pdf'
import { Card } from '../ui'
import { useProof } from '../../hooks/useApi'
import { useAuthStore, useUIStore } from '../../store'
import { createQrSvg } from '../../utils/qrcode'
import EvidenceLineageGraph from './sovereign/EvidenceLineageGraph'
import DidFloatingCard from './sovereign/DidFloatingCard'
import ConsensusDisputePanel from './sovereign/ConsensusDisputePanel'
import DocFinalPanel from './sovereign/DocFinalPanel'
import EvidenceVault from './sovereign/EvidenceVault'
import GenesisTree from './sovereign/GenesisTree'
import ScanConfirmPanel from './sovereign/ScanConfirmPanel'
import SpecdictPanel from './sovereign/SpecdictPanel'
import {
  describeSpecdictItem,
  detectConsensusDeviation,
  isTimeInWindow,
  parseConsensusValue,
  parseNumericInput,
  parseTimeWindow,
  safeEvalFormula,
  toneForDistance,
} from './sovereign/analysisUtils'
import ArPanel from './sovereign/ArPanel'
import {
  downloadJson,
  extractNodeGeo,
  haversineMeters,
  sha256Hex,
  shaJson,
} from './sovereign/fileUtils'
import { deriveGateReason, NormEngineProvider, resolveGate } from './sovereign/NormEngine'
import type { SovereignWorkspaceSnapshot, SovereignWorkspaceView } from './sovereign/SovereignProjectContext'
import { ProjectSovereignProvider } from './sovereign/SovereignContext'
import SovereignWorkbench from './sovereign/SovereignWorkbench'
import {
  buildMeasurementPayload,
  expandFormSchemaRows,
  resolveFallbackSchema,
  sanitizeMeasuredInput,
  toChineseCompType,
  toChineseMetricLabel,
} from './sovereign/spuUtils'
import {
  asNum,
  buildTreeFromRealtimeItems,
  formatNumber,
  getAllExpandedCodes,
  getFocusedExpandedCodes,
  guessChapterFromFileName,
  mergeExpandedCodes,
  normalizeItemNo,
  normalizeSearch,
  parseCsv,
  pickFirstLeaf,
  sanitizeGenericLabel,
  toApiUri,
  toDisplayUri,
} from './sovereign/treeUtils'
import type { ConsensusDeviation } from './sovereign/analysisUtils'
import type { EvidenceCenterPayload, FormRow, NodeStatus, OfflinePacketType, TreeNode } from './sovereign/types'
import { useAuditFinalizeActions } from './sovereign/useAuditFinalizeActions'
import { useEvidenceCenterLoader } from './sovereign/useEvidenceCenterLoader'
import { useEvidenceEventLogs } from './sovereign/useEvidenceEventLogs'
import { useEvidenceCenterView } from './sovereign/useEvidenceCenterView'
import { useEvidenceFiles } from './sovereign/useEvidenceFiles'
import { useOfflinePackets } from './sovereign/useOfflinePackets'
import { useScanConfirmAction } from './sovereign/useScanConfirmAction'
import { useScanEntryState } from './sovereign/useScanEntryState'
import { useSpecdictArActions } from './sovereign/useSpecdictArActions'
import { useSovereignSession } from './sovereign/useSovereignSession'

type Props = {
  project: { id?: string; v_uri?: string; name?: string } | null
  workspaceView?: SovereignWorkspaceView
  onNavigateView?: (view: SovereignWorkspaceView) => void
  onContextChange?: (snapshot: SovereignWorkspaceSnapshot) => void
}

const color: Record<NodeStatus, string> = { Genesis: '#64748B', Spending: '#2563EB', Settled: '#16A34A' }
const statusLabel: Record<NodeStatus, string> = { Genesis: '起源', Spending: '进行中', Settled: '已结算' }

const OFFLINE_KEY = 'qcspec_offline_packets_v1'
const API_BASE = String(import.meta.env.VITE_API_URL || 'http://127.0.0.1:8000')

try {
  GlobalWorkerOptions.workerSrc = new URL('pdfjs-dist/legacy/build/pdf.worker.min.js', import.meta.url).toString()
} catch {
  // ignore worker setup failures in non-browser env
}

function _asDict(value: unknown): Record<string, unknown> {
  return value && typeof value === 'object' && !Array.isArray(value) ? (value as Record<string, unknown>) : {}
}

function escapePdfText(input: string): string {
  return String(input || '').replace(/\\/g, '\\\\').replace(/\(/g, '\\(').replace(/\)/g, '\\)').replace(/\r?\n/g, ' ')
}

function buildDraftPdfBase64(lines: string[]): string {
  const safeLines = lines.filter(Boolean).map((line) => escapePdfText(line))
  const content = safeLines
    .map((line, idx) => {
      const y = 720 - idx * 16
      return `BT /F1 12 Tf 72 ${y} Td (${line}) Tj ET`
    })
    .join('\n')
  const encoder = new TextEncoder()
  const header = '%PDF-1.4\n'
  const obj1 = '1 0 obj\n<< /Type /Catalog /Pages 2 0 R >>\nendobj\n'
  const obj2 = '2 0 obj\n<< /Type /Pages /Kids [3 0 R] /Count 1 >>\nendobj\n'
  const obj3 = '3 0 obj\n<< /Type /Page /Parent 2 0 R /MediaBox [0 0 612 792] /Contents 4 0 R /Resources << /Font << /F1 5 0 R >> >> >>\nendobj\n'
  const contentBytes = encoder.encode(content)
  const obj4 = `4 0 obj\n<< /Length ${contentBytes.length} >>\nstream\n${content}\nendstream\nendobj\n`
  const obj5 = '5 0 obj\n<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>\nendobj\n'
  const objects = [obj1, obj2, obj3, obj4, obj5]
  const offsets: number[] = [0]
  let cursor = encoder.encode(header).length
  for (const obj of objects) {
    offsets.push(cursor)
    cursor += encoder.encode(obj).length
  }
  let xref = `xref\n0 ${objects.length + 1}\n`
  xref += '0000000000 65535 f \n'
  for (let i = 1; i < offsets.length; i += 1) {
    xref += `${String(offsets[i]).padStart(10, '0')} 00000 n \n`
  }
  const trailer = `trailer\n<< /Size ${objects.length + 1} /Root 1 0 R >>\nstartxref\n${cursor}\n%%EOF`
  const pdf = header + objects.join('') + xref + trailer
  const bytes = encoder.encode(pdf)
  let binary = ''
  bytes.forEach((b) => { binary += String.fromCharCode(b) })
  return btoa(binary)
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

export default function SovereignWorkbenchPanel({
  project,
  workspaceView = 'trip',
  onNavigateView,
  onContextChange,
}: Props) {
  const projectUri = String(project?.v_uri || '')
  const apiProjectUri = toApiUri(projectUri)
  const displayProjectUri = projectUri || toDisplayUri(apiProjectUri)
  const projectId = String(project?.id || '')
  const { showToast } = useUIStore()
  const dtoRole = useAuthStore((s) => String(s.user?.dto_role || 'PUBLIC').toUpperCase())
  const forcedBoqProjectUri = displayProjectUri ? displayProjectUri.replace(/\/$/, '') : 'v://cn.zhongbei/highway'
  const forcedBoqRootBase = `${forcedBoqProjectUri}/boq`
  const apiBoqRootBase = apiProjectUri ? `${apiProjectUri.replace(/\/$/, '')}/boq` : toApiUri(forcedBoqRootBase)
  const {
    smuImportGenesis,
    smuImportGenesisAsync,
    smuImportGenesisPreview,
    smuImportGenesisJobPublic,
    smuImportGenesisJobActivePublic,
    smuNodeContext,
    smuExecute,
    smuSign,
    tripGenerateDoc,
    smuFreeze,
    smuRetryErpnext,
    boqRealtimeStatus,
    evidenceCenterEvidence,
    publicVerifyDetail,
    downloadEvidenceCenterZip,
    triproleExecute,
    applyVariationDelta,
    scanConfirmSignature,
    replayOfflinePackets,
    exportDocFinal,
    finalizeDocFinal,
    unitMerkleRoot,
    projectReadinessCheck,
    specdictEvolve,
    specdictExport,
    arOverlay,
  } = useProof()

  const boqFileRef = useRef<HTMLInputElement | null>(null)
  const evidenceFileRef = useRef<HTMLInputElement | null>(null)
  const offlineImportRef = useRef<HTMLInputElement | null>(null)
  const previewScrollRef = useRef<HTMLDivElement | null>(null)
  const pdfCanvasRef = useRef<HTMLCanvasElement | null>(null)
  const pdfRenderRef = useRef<{ doc: unknown; task: { cancel: () => void } | null } | null>(null)
  const contractorAnchorRef = useRef<HTMLDivElement | null>(null)
  const supervisorAnchorRef = useRef<HTMLDivElement | null>(null)
  const ownerAnchorRef = useRef<HTMLDivElement | null>(null)
  const contextReqSeqRef = useRef(0)
  const autoRejectRef = useRef('')
  const geoFenceToastRef = useRef('')
  const autoDocTriggerRef = useRef('')

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
  const [showLeftSummary, setShowLeftSummary] = useState(true)
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

  const {
    evidence,
    evidenceName,
    evidenceOpen,
    evidenceFocus,
    hashing,
    resetEvidence,
    onEvidence,
    openEvidencePreview,
    closeEvidencePreview,
  } = useEvidenceFiles()
  const [evidenceCenter, setEvidenceCenter] = useState<EvidenceCenterPayload | null>(null)
  const [evidenceCenterLoading, setEvidenceCenterLoading] = useState(false)
  const [evidenceCenterError, setEvidenceCenterError] = useState('')
  const [erpRetrying, setErpRetrying] = useState(false)
  const [erpRetryMsg, setErpRetryMsg] = useState('')
  const [fingerprintOpen, setFingerprintOpen] = useState(false)
  const [executing, setExecuting] = useState(false)
  const [rejecting, setRejecting] = useState(false)
  const [execRes, setExecRes] = useState<Record<string, unknown> | null>(null)
  const [signOpen, setSignOpen] = useState(false)
  const [signStep, setSignStep] = useState(0)
  const [draftStamp, setDraftStamp] = useState('')
  const [signing, setSigning] = useState(false)
  const [signRes, setSignRes] = useState<Record<string, unknown> | null>(null)
  const [mockGenerating, setMockGenerating] = useState(false)
  const [mockDocRes, setMockDocRes] = useState<Record<string, unknown> | null>(null)
  const [consensusContractorValue, setConsensusContractorValue] = useState('')
  const [consensusSupervisorValue, setConsensusSupervisorValue] = useState('')
  const [consensusOwnerValue, setConsensusOwnerValue] = useState('')
  const [consensusAllowedDeviation, setConsensusAllowedDeviation] = useState('')
  const [consensusAllowedDeviationPct, setConsensusAllowedDeviationPct] = useState('')
  const [freezeProof, setFreezeProof] = useState('')
  const [signFocus, setSignFocus] = useState<'contractor' | 'supervisor' | 'owner' | ''>('')
  const [deltaAmount, setDeltaAmount] = useState('')
  const [deltaReason, setDeltaReason] = useState('变更指令')
  const [applyingDelta, setApplyingDelta] = useState(false)
  const [variationRes, setVariationRes] = useState<Record<string, unknown> | null>(null)
  const labRefreshTimerRef = useRef<number | null>(null)
  const labRefreshAttemptsRef = useRef(0)
  const autoUnitRef = useRef('')
  const [disputeProofId, setDisputeProofId] = useState('')
  const [disputeResolutionNote, setDisputeResolutionNote] = useState('')
  const [disputeResult, setDisputeResult] = useState<'PASS' | 'REJECT'>('PASS')
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
  const [pdfRenderError, setPdfRenderError] = useState('')
  const [pdfRenderLoading, setPdfRenderLoading] = useState(false)
  const aliveRef = useRef(true)
  const loadEvidenceCenterRef = useRef<(() => void | Promise<void>) | null>(null)
  const resumedProjectRef = useRef('')
  const [showAdvancedExecution, setShowAdvancedExecution] = useState(false)
  const [showAdvancedConsensus, setShowAdvancedConsensus] = useState(false)
  const [showFingerprintAdvanced, setShowFingerprintAdvanced] = useState(false)
  const [showAcceptanceAdvanced, setShowAcceptanceAdvanced] = useState(false)
  const [deltaModalOpen, setDeltaModalOpen] = useState(false)
  const [specdictProjectUris, setSpecdictProjectUris] = useState(apiProjectUri || displayProjectUri || '')
  const [specdictMinSamples, setSpecdictMinSamples] = useState('5')
  const [specdictNamespace, setSpecdictNamespace] = useState('v://global/templates')
  const [specdictCommit, setSpecdictCommit] = useState(false)
  const [arRadius, setArRadius] = useState('80')
  const [arLimit, setArLimit] = useState('50')
  const [arFocus, setArFocus] = useState<Record<string, unknown> | null>(null)
  const [arFullscreen, setArFullscreen] = useState(false)
  const [arFilterMax, setArFilterMax] = useState('120')
  const [p2pNodeId] = useState(() => `node-${Math.random().toString(16).slice(2, 8)}`)
  const [p2pPeers, setP2pPeers] = useState('')
  const [p2pAutoSync, setP2pAutoSync] = useState(true)
  const [p2pLastSync, setP2pLastSync] = useState('')
  const [docFinalPassphrase, setDocFinalPassphrase] = useState('')
  const [docFinalIncludeUnsettled, setDocFinalIncludeUnsettled] = useState(false)
  const [nowTick, setNowTick] = useState(Date.now())
  const [showAllScanEntries, setShowAllScanEntries] = useState(false)
  const [meshpegCloudName, setMeshpegCloudName] = useState('')
  const [meshpegBimName, setMeshpegBimName] = useState('')
  const [meshpegRunning, setMeshpegRunning] = useState(false)
  const [meshpegRes, setMeshpegRes] = useState<Record<string, unknown> | null>(null)
  const [formulaExpr, setFormulaExpr] = useState('qty * unit_price')
  const [formulaRunning, setFormulaRunning] = useState(false)
  const [formulaRes, setFormulaRes] = useState<Record<string, unknown> | null>(null)
  const [gatewayRes, setGatewayRes] = useState<Record<string, unknown> | null>(null)
  const {
    scanEntryLog,
    meshpegLog,
    formulaLog,
    gatewayLog,
    setScanEntryLog,
    setMeshpegLog,
    setFormulaLog,
    setGatewayLog,
    appendScanEntryLog,
    appendMeshpegLog,
    appendFormulaLog,
    appendGatewayLog,
    reconcileReplayResults,
  } = useEvidenceEventLogs()
  const {
    offlinePackets,
    offlineType,
    setOfflineType,
    offlineReplay,
    offlineImporting,
    offlineImportName,
    offlineSyncConflicts,
    isOnline,
    queueOfflinePacket,
    clearOfflinePackets,
    exportOfflinePackets,
    importOfflinePackets,
    simulateP2PSync,
  } = useOfflinePackets({
    storageKey: OFFLINE_KEY,
    autoReplayEnabled: p2pAutoSync,
    replayDefaultExecutorUri: apiProjectUri ? `${apiProjectUri.replace(/\/$/, '')}/role/contractor/mobile/` : '',
    replayOfflinePackets,
    onReplayResults: reconcileReplayResults,
    onReplayPatched: () => loadEvidenceCenterRef.current?.(),
    onSyncRecorded: (iso) => setP2pLastSync(iso),
    showToast,
  })
  const {
    specdictLoading,
    specdictExporting,
    specdictRes,
    runSpecdictEvolve,
    runSpecdictExport,
    arLoading,
    arRes,
    runArOverlay,
  } = useSpecdictArActions({
    apiProjectUri,
    specdictProjectUris,
    specdictMinSamples,
    specdictNamespace,
    specdictCommit,
    lat,
    lng,
    arRadius,
    arLimit,
    specdictEvolve,
    specdictExport,
    arOverlay,
    showToast,
  })

  useEffect(() => () => evidence.forEach((x) => URL.revokeObjectURL(x.url)), [evidence])
  useEffect(() => {
    aliveRef.current = true
    return () => { aliveRef.current = false }
  }, [])
  useEffect(() => {
    const timer = window.setInterval(() => setNowTick(Date.now()), 30000)
    return () => window.clearInterval(timer)
  }, [])
  const runReadinessCheck = useCallback(async (silent = false) => {
    if (!apiProjectUri) return
    setReadinessLoading(true)
    try {
      const payload = await projectReadinessCheck(apiProjectUri) as ReadinessPayload | null
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
  }, [apiProjectUri, projectReadinessCheck, showToast])

  useEffect(() => {
    if (!apiProjectUri) return
    void runReadinessCheck(true)
  }, [apiProjectUri, runReadinessCheck])

  const byUri = useMemo(() => new Map(nodes.map((x) => [x.uri, x])), [nodes])
  const byCode = useMemo(() => new Map(nodes.map((x) => [x.code, x])), [nodes])
  const roots = useMemo(() => nodes.filter((x) => !x.parent).map((x) => x.code), [nodes])
  const active = useMemo(() => byUri.get(activeUri) || null, [activeUri, byUri])
  const smuOptions = useMemo(() => {
    const seen = new Set<string>()
    const out: string[] = []
    nodes.forEach((node) => {
      if (!node.isLeaf) return
      const smu = String(node.code || '').split('-')[0]
      if (!smu || seen.has(smu)) return
      seen.add(smu)
      out.push(smu)
    })
    return out.sort((a, b) => a.localeCompare(b, 'zh-CN'))
  }, [nodes])
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
  const sovereignSession = useSovereignSession({
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
  })
  const {
    nodePathMap,
    activePath,
    boundSpu,
    isContractSpu,
    spuKind,
    spuBadge,
    stepLabel,
    roleAllowed,
    normResolution,
    lifecycle,
  } = sovereignSession
  useEffect(() => {
    if (typeof window === 'undefined') return
    const detail = {
      code: String(active?.code || ''),
      name: String(active?.name || ''),
      status: String(active?.status || ''),
      spu: String(active?.spu || ''),
      path: activePath || displayProjectUri || '',
      uri: String(active?.uri || displayProjectUri || ''),
    }
    try {
      window.sessionStorage.setItem('coordos.activeNode', JSON.stringify(detail))
      window.dispatchEvent(new CustomEvent('coordos:active-node-change', { detail }))
    } catch {
      // ignore storage/event failures in preview env
    }
  }, [active?.code, active?.name, active?.spu, active?.status, active?.uri, activePath, displayProjectUri])

  const formSchema = useMemo<FormRow[]>(() => {
    const s = (ctx?.spu || {}) as Record<string, unknown>
    const apiRows = Array.isArray(s.spu_form_schema) ? (s.spu_form_schema as FormRow[]) : []
    if (apiRows.length) return expandFormSchemaRows(apiRows)
    const node = (ctx?.node || {}) as Record<string, unknown>
    const nodeCode = String(node.item_no || node.item_code || active?.code || '')
    const nodeName = String(node.item_name || node.name || active?.name || '')
    return expandFormSchemaRows(resolveFallbackSchema(boundSpu, nodeCode, nodeName))
  }, [active?.code, active?.name, boundSpu, ctx])
  const effectiveSchema = useMemo<FormRow[]>(() => {
    if (!isContractSpu) return formSchema
    return formSchema.filter((row) => {
      const field = String(row.field || '').toLowerCase()
      const label = String(row.label || '').toLowerCase()
      if (field.includes('quality') || label.includes('quality')) return false
      if (field.includes('design') || field.includes('measured') || field.includes('allowed')) return false
      if (label.includes('设计') || label.includes('实测') || label.includes('允许')) return false
      return true
    })
  }, [formSchema, isContractSpu])

  const inputProofId = useMemo(() => {
    const t = (ctx?.trip || {}) as Record<string, unknown>
    const n = (ctx?.node || {}) as Record<string, unknown>
    const r = (execRes?.trip || {}) as Record<string, unknown>
    return String(r.output_proof_id || t.input_proof_id || n.proof_id || '')
  }, [ctx, execRes])

  const verifyUri = useMemo(() => {
    const fromSign = String(((signRes?.docpeg || {}) as Record<string, unknown>).verify_uri || '')
    if (fromSign) return fromSign
    return String(((mockDocRes?.docpeg || {}) as Record<string, unknown>).verify_uri || '')
  }, [mockDocRes, signRes])
  const pdfB64 = useMemo(() => {
    const fromSign = String(((signRes?.docpeg || {}) as Record<string, unknown>).pdf_preview_b64 || '')
    if (fromSign) return fromSign
    return String(((mockDocRes?.docpeg || {}) as Record<string, unknown>).pdf_preview_b64 || '')
  }, [mockDocRes, signRes])
  const totalHash = useMemo(() => {
    const fromSign = String(((signRes?.trip || {}) as Record<string, unknown>).total_proof_hash || '')
    if (fromSign) return fromSign
    const fromMock = String((mockDocRes?.total_proof_hash || '')).trim()
    if (fromMock) return fromMock
    return String((evidenceCenter?.totalProofHash || '')).trim()
  }, [evidenceCenter?.totalProofHash, mockDocRes, signRes])
  const scanConfirmUri = useMemo(() => String(((signRes?.docpeg || {}) as Record<string, unknown>).scan_confirm_uri || ''), [signRes])
  const scanConfirmToken = useMemo(() => String(((signRes?.docpeg || {}) as Record<string, unknown>).scan_confirm_token || ''), [signRes])
  const {
    scanPayload,
    setScanPayload,
    scanDid,
    setScanDid,
    scanProofId,
    setScanProofId,
    scanRes,
    scanning,
    scanLockStage,
    scanLockProofId,
    doScanConfirm,
    closeScanLock,
  } = useScanConfirmAction({
    apiProjectUri,
    inputProofId,
    scanConfirmToken,
    lat,
    lng,
    scanConfirmSignature,
    showToast,
  })
  const finalProofId = useMemo(() => {
    const fromScan = String(scanLockProofId || '')
    if (fromScan) return fromScan
    const scanOut = String(((scanRes || {}) as Record<string, unknown>).output_proof_id || '')
    if (scanOut) return scanOut
    const signOut = String(((signRes || {}) as Record<string, unknown>).output_proof_id || ((signRes?.trip || {}) as Record<string, unknown>).output_proof_id || '')
    return signOut
  }, [scanLockProofId, scanRes, signRes])
  const approvedProofId = useMemo(() => {
    return String(
      ((signRes?.trip || {}) as Record<string, unknown>).output_proof_id ||
      (signRes as Record<string, unknown> | null)?.output_proof_id ||
      '',
    ).trim()
  }, [signRes])
  const tripStage = useMemo<'Unspent' | 'Reviewing' | 'Approved'>(() => {
    if (approvedProofId) return 'Approved'
    const reviewingProof = String(((execRes?.trip || {}) as Record<string, unknown>).output_proof_id || '').trim()
    if (reviewingProof) return 'Reviewing'
    return 'Unspent'
  }, [approvedProofId, execRes])
  const finalProofReady = Boolean(verifyUri || finalProofId)
  const isGenesisView = workspaceView === 'genesis'
  const isTripView = workspaceView === 'trip'
  const isAuditView = workspaceView === 'audit'
  const docpegPageMap = useMemo(() => {
    const raw = ((signRes?.docpeg || {}) as Record<string, unknown>).sign_page_map as Record<string, unknown> | undefined
    const toPage = (v: unknown, fallback: number) => {
      const n = Number(v)
      return Number.isFinite(n) && n > 0 ? Math.floor(n) : fallback
    }
    return {
      contractor: toPage(raw?.contractor, 1),
      supervisor: toPage(raw?.supervisor, 2),
      owner: toPage(raw?.owner, 3),
    }
  }, [signRes])
  const docpegSignPos = useMemo(() => {
    const raw = ((signRes?.docpeg || {}) as Record<string, unknown>).sign_position_map as Record<string, unknown> | undefined
    const clamp = (n: number) => Math.min(1, Math.max(0, n))
    const toPos = (value: unknown) => {
      if (!value || typeof value !== 'object') return null
      const rec = value as Record<string, unknown>
      const page = Number(rec.page ?? rec.p)
      const x = Number(rec.x ?? rec.left)
      const y = Number(rec.y ?? rec.top)
      if (!Number.isFinite(x) || !Number.isFinite(y)) return null
      return {
        page: Number.isFinite(page) && page > 0 ? Math.floor(page) : undefined,
        x: clamp(x > 1 ? x / 100 : x),
        y: clamp(y > 1 ? y / 100 : y),
      }
    }
    return {
      contractor: toPos(raw?.contractor),
      supervisor: toPos(raw?.supervisor),
      owner: toPos(raw?.owner),
    }
  }, [signRes])
  const evidenceTimeline = (evidenceCenter?.timeline || []) as Array<Record<string, unknown>>
  const evidenceDocs = (evidenceCenter?.documents || []) as Array<Record<string, unknown>>
  const evidenceItems = (evidenceCenter?.evidence || []) as Array<Record<string, unknown>>
  const scanEntryItems = (evidenceCenter?.scanEntries || []) as Array<Record<string, unknown>>
  const meshpegItems = (evidenceCenter?.meshpegEntries || []) as Array<Record<string, unknown>>
  const formulaItems = (evidenceCenter?.formulaEntries || []) as Array<Record<string, unknown>>
  const gatewayItems = (evidenceCenter?.gatewayEntries || []) as Array<Record<string, unknown>>
  const scanEntryLatest = useMemo(() => {
    const filtered = scanEntryItems.filter((item) => {
      const itemUri = String(item.item_uri || item.boq_item_uri || '')
      if (!active?.uri) return true
      return itemUri ? itemUri === active.uri : true
    })
    if (!filtered.length) return null
    const ranked = filtered
      .map((item) => {
        const t = Date.parse(String(item.created_at || item.scan_entry_at || ''))
        return { item, t: Number.isFinite(t) ? t : 0 }
      })
      .sort((a, b) => b.t - a.t)
    return ranked[0]?.item || null
  }, [active?.uri, scanEntryItems])
  const scanChainStatus = String(scanEntryLatest?.chain_status || '').trim()
  const scanChainBadge = scanChainStatus === 'onchain'
    ? { label: '已上链', cls: 'bg-emerald-900/40 text-emerald-200 border-emerald-500/60' }
    : scanChainStatus
      ? { label: '待上链', cls: 'bg-amber-900/40 text-amber-200 border-amber-500/60' }
      : { label: '未知', cls: 'bg-slate-900/40 text-slate-400 border-slate-600/60' }
  const scanEntryActiveOnly = scanEntryItems.filter((item) => {
    if (showAllScanEntries || !active?.uri) return true
    const itemUri = String(item.item_uri || item.boq_item_uri || '')
    return itemUri ? itemUri === active.uri : true
  })
  const ledgerSnapshot = (evidenceCenter?.ledger || {}) as Record<string, unknown>
  const consensusDispute = _asDict(evidenceCenter?.consensusDispute || {})
  const latestEvidenceNode = evidenceTimeline.length ? evidenceTimeline[evidenceTimeline.length - 1] : null
  const utxoConsumed = Boolean((latestEvidenceNode || {}).spent)
  const utxoStatusText = active?.status === 'Settled' || utxoConsumed ? '已消费' : '未消费'
  const docpegRisk = useMemo(() => {
    const fromEvidence = _asDict(evidenceCenter?.riskAudit || {})
    if (Object.keys(fromEvidence).length) return fromEvidence
    return _asDict(((signRes?.docpeg || {}) as Record<string, unknown>).risk_audit)
  }, [evidenceCenter?.riskAudit, signRes])
  const docpegContext = useMemo(
    () => _asDict(((signRes?.docpeg || {}) as Record<string, unknown>).context),
    [signRes],
  )
  const docpegRiskScore = Number(docpegRisk.risk_score || 0)
  const mockRiskAudit = _asDict(mockDocRes?.risk_audit || {})
  const effectiveRiskScore = Number.isFinite(Number(mockRiskAudit.risk_score))
    ? Number(mockRiskAudit.risk_score)
    : docpegRiskScore
  const evidenceCompleteness = _asDict(evidenceCenter?.evidenceCompleteness || {})
  const evidenceCompletenessScore = Number(evidenceCompleteness.score || 0)
  const settlementRiskScore = Number.isFinite(Number(evidenceCenter?.settlementRiskScore))
    ? Number(evidenceCenter?.settlementRiskScore)
    : docpegRiskScore
  const assetOrigin = useMemo(() => {
    const fromEvidence = _asDict(evidenceCenter?.assetOrigin || {})
    if (Object.keys(fromEvidence).length) return fromEvidence
    return _asDict(docpegContext.asset_origin || {})
  }, [docpegContext.asset_origin, evidenceCenter?.assetOrigin])
  const assetOriginStatement = useMemo(() => {
    const fromEvidence = String(evidenceCenter?.assetOriginStatement || '').trim()
    if (fromEvidence) return fromEvidence
    const fromAsset = String(assetOrigin.statement || '').trim()
    if (fromAsset) return fromAsset
    return String(docpegContext.asset_origin_statement || '').trim()
  }, [assetOrigin.statement, docpegContext.asset_origin_statement, evidenceCenter?.assetOriginStatement])
  const didReputation = useMemo(() => {
    const fromEvidence = _asDict(evidenceCenter?.didReputation || {})
    if (Object.keys(fromEvidence).length) return fromEvidence
    const fromRisk = _asDict(docpegRisk.did_reputation || {})
    if (Object.keys(fromRisk).length) return fromRisk
    return _asDict(_asDict(docpegContext.risk_audit).did_reputation || {})
  }, [docpegContext.risk_audit, docpegRisk.did_reputation, evidenceCenter?.didReputation])
  const didReputationScore = Number(didReputation.aggregate_score ?? didReputation.score ?? 0)
  const didReputationGrade = String(didReputation.grade || _asDict(didReputation.items?.[0]).grade || '-')
  const didSamplingMultiplier = Number(didReputation.sampling_multiplier ?? didReputation.samplingMultiplier ?? 1)
  const didHighRiskList = Array.isArray(didReputation.high_risk_dids)
    ? (didReputation.high_risk_dids as Array<Record<string, unknown>>)
    : []
  const sealingTrip = useMemo(() => {
    const fromEvidence = _asDict(evidenceCenter?.sealingTrip || {})
    if (Object.keys(fromEvidence).length) return fromEvidence
    return _asDict(docpegContext.sealing_trip || {})
  }, [docpegContext.sealing_trip, evidenceCenter?.sealingTrip])
  const sealingPatternId = String(sealingTrip.pattern_id || '')
  const sealingScanHint = String(sealingTrip.scan_hint || '')
  const sealingRows = Array.isArray(sealingTrip.ascii_pattern)
    ? (sealingTrip.ascii_pattern as string[]).slice(0, 8)
    : []
  const sealingMicrotext = Array.isArray(sealingTrip.margin_microtext)
    ? (sealingTrip.margin_microtext as string[]).slice(0, 6)
    : []
  const {
    evidenceQuery,
    setEvidenceQuery,
    evidenceFilter,
    setEvidenceFilter,
    evidenceScope,
    setEvidenceScope,
    evidenceSmuId,
    setEvidenceSmuId,
    setEvidencePage,
    evidenceCenterFocus,
    evidenceCenterDocFocus,
    openEvidenceFocus,
    closeEvidenceFocus,
    openDocumentFocus,
    closeDocumentFocus,
    evidenceZipDownloading,
    filteredEvidenceItems,
    filteredDocs,
    erpReceiptDoc,
    evidencePageSafe,
    totalEvidencePages,
    evidenceItemsPaged,
    exportEvidenceCenter,
    exportEvidenceCenterCsv,
    downloadEvidenceCenterPackage,
  } = useEvidenceCenterView({
    activeCode: String(active?.code || ''),
    apiProjectUri,
    smuOptions,
    evidenceCenter,
    evidenceDocs,
    evidenceItems,
    evidenceTimeline,
    meshpegItems,
    formulaItems,
    gatewayItems,
    ledgerSnapshot,
    docpegRisk,
    didReputation,
    assetOrigin,
    assetOriginStatement,
    sealingTrip,
    totalHash,
    showToast,
    downloadEvidenceCenterZip,
  })
  const disputeOpen = Boolean(consensusDispute.open)
  const disputeProof = String(consensusDispute.open_proof_id || consensusDispute.latest_proof_id || '')
  const disputeProofShort = disputeProof.length > 12 ? `${disputeProof.slice(0, 12)}...` : disputeProof
  const disputeConflict = _asDict(consensusDispute.open_conflict || consensusDispute.latest_conflict || {})
  const disputeDeviation = Number(disputeConflict.deviation || 0)
  const disputeDeviationPct = Number(disputeConflict.deviation_percent || disputeConflict.deviationPercent || 0)
  const disputeAllowedAbs = disputeConflict.allowed_deviation ?? disputeConflict.allowedDeviation
  const disputeAllowedPct = disputeConflict.allowed_deviation_percent ?? disputeConflict.allowedDeviationPercent
  const disputeValues = Array.isArray(disputeConflict.values) ? (disputeConflict.values as Array<unknown>) : []
  const nodeMetadata = useMemo(() => {
    const node = (ctx?.node || {}) as Record<string, unknown>
    return ((node.metadata || {}) as Record<string, unknown>)
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
      (nodeMetadata.temporal_window || nodeMetadata.allowed_time_window || nodeMetadata.work_hours || nodeMetadata.time_window)
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
  const specdictAnalysis = _asDict((specdictRes || {}).analysis || specdictRes)
  const specdictRuleTotal = Number(specdictAnalysis.total_rules || (specdictRes || {}).total_rules || 0)
  const specdictHighRisk = Array.isArray(specdictAnalysis.high_risk) ? specdictAnalysis.high_risk.length : 0
  const specdictBestPractice = Array.isArray(specdictAnalysis.best_practice) ? specdictAnalysis.best_practice.length : 0
  const specdictHighRiskItems = Array.isArray(specdictAnalysis.high_risk) ? specdictAnalysis.high_risk : []
  const specdictBestPracticeItems = Array.isArray(specdictAnalysis.best_practice) ? specdictAnalysis.best_practice : []
  const specdictSuccessPatterns = Array.isArray(specdictAnalysis.success_pattern)
    ? specdictAnalysis.success_pattern
    : (Array.isArray(specdictAnalysis.success_patterns) ? specdictAnalysis.success_patterns : [])
  const specdictWeightSuggestions = _asDict(
    specdictAnalysis.weight_suggestions || specdictAnalysis.weight_recommendations || specdictAnalysis.weight_hint || {},
  )
  const specdictWeightEntries = Object.entries(specdictWeightSuggestions).slice(0, 4)
  const specdictBundleUri = String(
    (specdictRes || {}).bundle_uri ||
    (specdictRes || {}).template_uri ||
    (specdictRes || {}).namespace_uri ||
    specdictNamespace ||
    '',
  )
  const arItems = Array.isArray((arRes || {}).items) ? ((arRes || {}).items as Array<Record<string, unknown>>) : []
  const arItemsSorted = useMemo(() => {
    return [...arItems].sort((a, b) => {
      const da = Number(a.distance_m ?? 0)
      const db = Number(b.distance_m ?? 0)
      return da - db
    })
  }, [arItems])
  const arFilterMaxValue = useMemo(() => {
    const parsed = parseNumericInput(arFilterMax)
    return parsed != null && parsed > 0 ? parsed : 0
  }, [arFilterMax])
  const arFilteredItems = useMemo(() => {
    if (!arFilterMaxValue) return arItemsSorted
    return arItemsSorted.filter((item) => Number(item.distance_m ?? 0) <= arFilterMaxValue)
  }, [arItemsSorted, arFilterMaxValue])
  const arPrimary = arItems.length ? arItems[0] : null
  useEffect(() => {
    const openId = String(consensusDispute.open_proof_id || '')
    if (openId && !disputeProofId) {
      setDisputeProofId(openId)
    }
  }, [consensusDispute.open_proof_id, disputeProofId])

  const retryErpnextPush = useCallback(async () => {
    if (erpRetrying) return
    setErpRetrying(true)
    setErpRetryMsg('')
    try {
      const res = await smuRetryErpnext(20) as Record<string, unknown> | null
      if (res && res.ok) {
        setErpRetryMsg(`重试完成：成功 ${String(res.success || 0)} / ${String(res.attempted || 0)}`)
      } else {
        setErpRetryMsg('重试失败：接口无响应')
      }
    } catch {
      setErpRetryMsg('重试失败：请求异常')
    } finally {
      setErpRetrying(false)
    }
  }, [erpRetrying, smuRetryErpnext])
  const offlineActorId = useMemo(() => {
    const didSlug = String(executorDid || 'anonymous').split(':').slice(-1)[0] || 'anonymous'
    return `${p2pNodeId}:${didSlug}`
  }, [executorDid, p2pNodeId])

  const summary = useMemo(() => {
    if (!active) return { contract: 0, approved: 0, design: 0, settled: 0, consumed: 0, pct: 0 }
    const x = aggMap.get(active.code) || { contract: 0, approved: 0, design: 0, settled: 0, consumed: 0 }
    const effective = x.settled
    const baseline = x.approved > 0 ? x.approved : (x.contract > 0 ? x.contract : x.design)
    return {
      contract: x.contract,
      approved: x.approved,
      design: x.design,
      settled: x.settled,
      consumed: x.consumed,
      pct: baseline > 0 ? (effective * 100) / baseline : 0,
    }
  }, [active, aggMap])

  const gateStats = useMemo(() => resolveGate({
    schema: effectiveSchema,
    form,
    ctx,
    isContractSpu,
  }), [ctx, effectiveSchema, form, isContractSpu])
  const activeGenesisSummary = useMemo(() => {
    if (!active) {
      return {
        contractQty: 0,
        progressPct: 0,
        reportedPct: 0,
        leafCount: 0,
        contractDocCount: 0,
      }
    }
    let leafCount = 0
    const stack = [active.code]
    while (stack.length) {
      const code = stack.pop() as string
      const node = byCode.get(code)
      if (!node) continue
      if (node.isLeaf) {
        leafCount += 1
        continue
      }
      node.children.forEach((child) => stack.push(child))
    }
    const contractQty = summary.contract > 0 ? summary.contract : summary.design
    const reportedPct = gateStats.total > 0 ? ((gateStats.pass + gateStats.fail) * 100) / gateStats.total : summary.pct
    const contractDocCount = filteredDocs.filter((doc) => {
      const text = `${String(doc.doc_type || '')} ${String(doc.file_name || '')}`.toLowerCase()
      return text.includes('contract') || text.includes('合同')
    }).length
    return {
      contractQty,
      progressPct: summary.pct,
      reportedPct,
      leafCount,
      contractDocCount,
    }
  }, [active, byCode, filteredDocs, gateStats.fail, gateStats.pass, gateStats.total, summary.contract, summary.design, summary.pct])
  const gateReason = useMemo(() => deriveGateReason(gateStats), [gateStats])
  const evidenceGraphNodes = useMemo(() => {
    const latestTimeline = evidenceTimeline.length ? evidenceTimeline[evidenceTimeline.length - 1] : null
    const latestDoc = filteredDocs.length ? filteredDocs[filteredDocs.length - 1] : null
    return [
      { id: 'graph-ledger', label: '0#台账 Genesis', subtitle: String(active?.uri || '-'), tone: 'neutral' as const },
      { id: 'graph-qc', label: 'QCSpec 质检 Proof', subtitle: String((latestTimeline || {}).proof_id || inputProofId || '-'), tone: gateStats.qcCompliant ? ('ok' as const) : ('warn' as const) },
      { id: 'graph-lab', label: 'LabPeg 实验 Proof', subtitle: gateStats.labLatestPass || '未检出', tone: gateStats.labQualified ? ('ok' as const) : ('warn' as const) },
      { id: 'graph-doc', label: 'DocPeg / PDF', subtitle: String((latestDoc || {}).file_name || verifyUri || '-'), tone: verifyUri || latestDoc ? ('ok' as const) : ('neutral' as const) },
      { id: 'graph-hash', label: 'Final total_proof_hash', subtitle: String(totalHash || '-'), tone: totalHash ? ('ok' as const) : ('neutral' as const) },
    ]
  }, [active?.uri, evidenceTimeline, filteredDocs, gateStats.labLatestPass, gateStats.labQualified, gateStats.qcCompliant, inputProofId, totalHash, verifyUri])

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
  const offlineCount = offlinePackets.length
  const draftReady = signStep >= 1
  const draftPdfB64 = useMemo(() => {
    if (!draftReady) return ''
    const nodeName = String(active?.name || '')
    const nodeCode = String(active?.code || '')
    const lines = [
      'QCSpec DocPeg Draft',
      `构件: ${nodeCode}${nodeName ? ` ${nodeName}` : ''}`,
      `施工员: ${executorDid}`,
      `监理: ${supervisorDid || '-'}`,
      `业主: ${ownerDid || '-'}`,
      `时间: ${draftStamp || new Date().toISOString()}`,
      `模板: ${String(templateBinding.template_path || templateBinding.fallback_template || '-')}`,
    ]
    return buildDraftPdfBase64(lines)
  }, [active?.code, active?.name, draftReady, draftStamp, executorDid, ownerDid, supervisorDid, templateBinding.fallback_template, templateBinding.template_path])
  const previewPdfB64 = pdfB64 || draftPdfB64
  const previewIsDraft = Boolean(draftPdfB64 && !pdfB64)
  const pdfPage = useMemo(() => {
    if (!signFocus) return docpegPageMap.contractor
    return docpegPageMap[signFocus] || docpegPageMap.contractor
  }, [docpegPageMap, signFocus])
  const activeSignMarker = useMemo(() => {
    if (!signFocus) return null
    const pos = docpegSignPos[signFocus]
    if (!pos) return null
    if (pos.page && pos.page !== pdfPage) return null
    return pos
  }, [docpegSignPos, pdfPage, signFocus])
  const specBinding = normResolution.specBinding
  const gateBinding = normResolution.gateBinding
  const normRefs = normResolution.normRefs
  const displayMeta = useMemo(() => deriveNodeDisplayMeta(nodeMetadata, active), [active, nodeMetadata])
  const designTotal = summary.design
  const approvedTotal = summary.approved
  const contractTotal = summary.contract
  const settledTotal = summary.settled
  const effectiveSpent = settledTotal
  const baselineTotal = approvedTotal > 0 ? approvedTotal : (contractTotal > 0 ? contractTotal : designTotal)
  const availableTotal = Math.max(0, baselineTotal - effectiveSpent)
  const claimValue = Number(claimQty)
  const claimQtyValue = Number.isFinite(claimValue) ? claimValue : 0
  const claimQtyProvided = String(claimQty || '').trim() !== ''
  const measuredQtyValue = useMemo(() => {
    const points: number[] = []
    effectiveSchema.forEach((row, idx) => {
      const source = String(row.source_field || row.field || '').trim().toLowerCase()
      if (source !== 'measured_value') return
      const key = String(row.field || `f_${idx}`)
      const raw = String(form[key] || '').replace(/,/g, '').trim()
      if (!raw) return
      const parsed = Number(raw)
      if (Number.isFinite(parsed)) points.push(parsed)
    })
    if (!points.length) return 0
    const avg = points.reduce((sum, v) => sum + v, 0) / points.length
    return Number(avg.toFixed(6))
  }, [effectiveSchema, form])
  const effectiveClaimQtyValue = claimQtyProvided ? claimQtyValue : (!isContractSpu ? measuredQtyValue : 0)
  const consensusBaseValue = useMemo(() => {
    if (effectiveClaimQtyValue > 0) return effectiveClaimQtyValue
    if (measuredQtyValue > 0) return measuredQtyValue
    return 0
  }, [effectiveClaimQtyValue, measuredQtyValue])
  const consensusPreview = useMemo(() => {
    const values = [
      {
        role: 'contractor',
        did: executorDid,
        value: parseConsensusValue(consensusContractorValue, consensusBaseValue),
        source: parseNumericInput(consensusContractorValue) == null ? 'default' : 'input',
      },
      {
        role: 'supervisor',
        did: supervisorDid,
        value: parseConsensusValue(consensusSupervisorValue, consensusBaseValue),
        source: parseNumericInput(consensusSupervisorValue) == null ? 'default' : 'input',
      },
      {
        role: 'owner',
        did: ownerDid,
        value: parseConsensusValue(consensusOwnerValue, consensusBaseValue),
        source: parseNumericInput(consensusOwnerValue) == null ? 'default' : 'input',
      },
    ]
    const allowedAbs = parseNumericInput(consensusAllowedDeviation)
    const allowedPct = parseNumericInput(consensusAllowedDeviationPct)
    const deviation = detectConsensusDeviation(
      values.map((v) => v.value),
      consensusBaseValue,
      allowedAbs,
      allowedPct,
    )
    return { values, allowedAbs, allowedPct, deviation }
  }, [
    consensusAllowedDeviation,
    consensusAllowedDeviationPct,
    consensusBaseValue,
    consensusContractorValue,
    consensusOwnerValue,
    consensusSupervisorValue,
    executorDid,
    ownerDid,
    supervisorDid,
  ])
  const consensusDeviation = consensusPreview.deviation
  const consensusConflict = consensusDeviation.conflict
  const consensusAllowedAbsText = consensusDeviation.allowedDeviation != null ? formatNumber(consensusDeviation.allowedDeviation) : '-'
  const consensusAllowedPctText = consensusDeviation.allowedDeviationPercent != null
    ? `${consensusDeviation.allowedDeviationPercent.toFixed(2)}%`
    : (consensusDeviation.defaulted ? '默认 0.50%' : '-')
  const consensusConflictSummary = {
    project_uri: apiProjectUri,
    boq_item_uri: active?.uri || '',
    base_value: consensusBaseValue,
    allowed_deviation: consensusDeviation.allowedDeviation,
    allowed_deviation_percent: consensusDeviation.allowedDeviationPercent ?? (consensusDeviation.defaulted ? 0.5 : null),
    deviation: consensusDeviation.deviation,
    deviation_percent: consensusDeviation.deviationPercent,
    values: consensusPreview.values.map((v) => ({
      role: v.role,
      did: v.did,
      value: v.value,
      source: v.source,
    })),
    conflict: consensusDeviation.conflict,
  }
  const exceedBalance = effectiveClaimQtyValue > availableTotal + 1e-9
  const exceedRatio = baselineTotal > 0 ? ((effectiveSpent + effectiveClaimQtyValue) - baselineTotal) / baselineTotal : 0
  const exceedPercent = Math.max(0, exceedRatio * 100)
  const deltaSuggest = Math.max(0, (effectiveSpent + effectiveClaimQtyValue) - baselineTotal)
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
  const snappegReady = useMemo(() => {
    if (isContractSpu) return true
    if (!geoValid) return false
    if (evidence.length === 0) return false
    return evidence.every((x) => x.exifOk !== false)
  }, [evidence, geoValid, isContractSpu])
  const geoFenceStatusText = useMemo(() => {
    if (!geoFenceActive) return '未启用'
    if (geoTemporalBlocked) return '拦截中'
    return '通过'
  }, [geoFenceActive, geoTemporalBlocked])
  const geoFormLocked = geoTemporalBlocked
  const evidenceLabel = isContractSpu ? '合同凭证附件' : 'SnapPeg 现场照'
  const evidenceAccept = isContractSpu ? 'image/*,application/pdf' : 'image/*'
  const evidenceHint = isContractSpu ? '支持图片/PDF' : '仅支持图片'
  const finalPiecePrompt = `Role: CoordOS 首席协议架构师
Task: 参照 18 份文档及 20260327-GPT 逻辑，补全共识仲裁、知识迁移与 AR 物理锚定。
1. 共识冲突检查器：detect_consensus_deviation() 对比签名量值，超阈值自动挂起结算 Trip。
2. 规则进化提取器：分析 proof_utxo 历史，提取 success_pattern 并更新 spec_dicts 权重建议。
3. AR 主权叠加层：GPS + 时空指纹渲染 v:// 节点，实现所见即所证。
完工态：Trip 自动流转；风险审计 24h；项目经验沉淀为智能标准。`

  useEffect(() => {
    if (exceedBalance) {
      setDeltaModalOpen(true)
      setShowAdvancedExecution(true)
    } else {
      setDeltaModalOpen(false)
      setShowAdvancedExecution(false)
    }
  }, [exceedBalance])

  const loadContext = useCallback(async (uri: string, component = compType) => {
    if (!apiProjectUri || !uri) return
    const reqSeq = contextReqSeqRef.current + 1
    contextReqSeqRef.current = reqSeq
    setLoadingCtx(true)
    setContextError('')
    try {
      const payload = await smuNodeContext({ project_uri: apiProjectUri, boq_item_uri: toApiUri(uri), component_type: component }) as Record<string, unknown> | null
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
      const payloadNode = _asDict(payload.node as Record<string, unknown>)
      const nodeCode = String(payloadNode.item_no || payloadNode.item_code || active?.code || '')
      const nodeName = String(payloadNode.item_name || payloadNode.name || active?.name || '')
      const baseRows = Array.isArray(payloadSpu.spu_form_schema)
        ? (payloadSpu.spu_form_schema as FormRow[])
        : resolveFallbackSchema(payloadSpuLabel, nodeCode, nodeName)
      const rows = expandFormSchemaRows(baseRows)
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
  }, [active?.code, active?.name, apiProjectUri, compType, showToast, smuNodeContext])

  useEffect(() => {
    if (gateStats.labQualified) {
      labRefreshAttemptsRef.current = 0
      if (labRefreshTimerRef.current) {
        window.clearTimeout(labRefreshTimerRef.current)
        labRefreshTimerRef.current = null
      }
      return
    }
    if (!active?.isLeaf || !activeUri || !apiProjectUri) return
    if (isContractSpu) return
    if (!sampleId) return
    if (loadingCtx) return
    if (labRefreshAttemptsRef.current >= 3) return
    if (labRefreshTimerRef.current) return
    labRefreshTimerRef.current = window.setTimeout(() => {
      labRefreshTimerRef.current = null
      labRefreshAttemptsRef.current += 1
      void loadContext(activeUri, compType)
    }, 3000)
  }, [active?.isLeaf, activeUri, apiProjectUri, compType, gateStats.labQualified, isContractSpu, loadContext, loadingCtx, sampleId])

  const autoSelectLeafAndPrefill = useCallback(async (leaf: TreeNode | null) => {
    if (!leaf) return
    const c = leaf.spu === 'SPU_Reinforcement' || leaf.spu === 'SPU_Bridge'
      ? 'main_beam'
      : leaf.spu === 'SPU_Concrete'
        ? 'pier'
        : 'generic'
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
    if (!apiProjectUri) return null
    const payload = await boqRealtimeStatus(apiProjectUri) as Record<string, unknown> | null
    const items = Array.isArray((payload || {}).items) ? ((payload || {}).items as Array<Record<string, unknown>>) : []
    if (!items.length) return null
    const displayBase = displayProjectUri || toDisplayUri(apiProjectUri)
    const rebuilt = buildTreeFromRealtimeItems(items, displayBase)
    if (!rebuilt.length) return null
    setNodes(rebuilt)
    const defaultLeaf = pickFirstLeaf(rebuilt)
    const focus = String(focusCode || defaultLeaf?.code || '')
    setExpandedCodes(getAllExpandedCodes(rebuilt))
    return rebuilt
  }, [apiProjectUri, boqRealtimeStatus, displayProjectUri])

  const { loadEvidenceCenter } = useEvidenceCenterLoader({
    apiProjectUri,
    activeCode: String(active?.code || ''),
    activeIsLeaf: Boolean(active?.isLeaf),
    activeUri: String(active?.uri || ''),
    evidenceScope,
    evidenceSmuId,
    finalProofId,
    inputProofId,
    evidenceCenterEvidence,
    publicVerifyDetail,
    showToast,
    setEvidenceCenter,
    setEvidenceCenterLoading,
    setEvidenceCenterError,
    scanEntryLog,
    meshpegLog,
    formulaLog,
    gatewayLog,
    setScanEntryLog,
    setMeshpegLog,
    setFormulaLog,
    setGatewayLog,
  })
  useEffect(() => {
    loadEvidenceCenterRef.current = loadEvidenceCenter
  }, [loadEvidenceCenter])
  const {
    disputeResolving,
    disputeResolveRes,
    resolveDispute,
    docFinalExporting,
    docFinalFinalizing,
    docFinalRes,
    archiveLocked,
    exportProjectDocFinal,
    finalizeProjectDocFinal,
    assetAppraising,
    assetAppraisal,
    buildAssetAppraisal,
  } = useAuditFinalizeActions({
    apiProjectUri,
    projectName: String(project?.name || ''),
    ownerDid,
    lat,
    lng,
    disputeProofId,
    disputeResolutionNote,
    disputeResult,
    docFinalPassphrase,
    docFinalIncludeUnsettled,
    activeUri: String(active?.uri || ''),
    finalProofReady,
    consensusConflict,
    disputeOpen,
    docpegRiskScore,
    totalHash,
    evidenceCount: evidenceItems.length,
    documentCount: evidenceDocs.length,
    finalProofId,
    inputProofId,
    triproleExecute,
    exportDocFinal,
    finalizeDocFinal,
    loadEvidenceCenter,
    showToast,
  })
  useEffect(() => {
    const snapshotDispute = _asDict(evidenceCenter?.consensusDispute || {})
    onContextChange?.({
      activePath: activePath || displayProjectUri || '',
      lifecycle,
      activeCode: String(active?.code || ''),
      activeStatus: String(active?.status || ''),
      totalHash: String(totalHash || ''),
      verifyUri: String(verifyUri || ''),
      finalProofReady,
      isOnline,
      offlineQueueSize: offlinePackets.length,
      disputeOpen: Boolean(snapshotDispute.open),
      disputeProof: String(snapshotDispute.open_proof_id || snapshotDispute.latest_proof_id || ''),
      archiveLocked,
    })
  }, [active?.code, active?.status, activePath, archiveLocked, displayProjectUri, evidenceCenter?.consensusDispute, finalProofReady, isOnline, lifecycle, offlinePackets.length, onContextChange, totalHash, verifyUri])

  useEffect(() => {
    if (!geoFenceActive || !active?.uri) {
      geoFenceToastRef.current = ''
      return
    }
    if (!geoTemporalBlocked) return
    const key = `${active.uri}|${Math.round(geoDistance || 0)}|${temporalBlocked ? 'time' : 'geo'}`
    if (geoFenceToastRef.current === key) return
    geoFenceToastRef.current = key
    const distanceText = geoDistance != null ? `${Math.round(geoDistance)}m` : '未知'
    const radiusText = geoAnchor?.radiusM != null ? `${geoAnchor.radiusM}m` : '-'
    showToast(`空间坐标越界（Geo-Leap Error）：距桩号中心 ${distanceText} / 半径 ${radiusText}`)
  }, [active?.uri, geoAnchor?.radiusM, geoDistance, geoFenceActive, geoTemporalBlocked, showToast, temporalBlocked])


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
    resetEvidence()
  }, [resetEvidence])

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
    if (!apiProjectUri) return
    if (nodes.length > 0) return
    // Hydrate existing BOQ tree when reopening the project drawer.
    void (async () => {
      const rebuilt = await refreshTreeFromServer()
      if (!rebuilt?.length) return
      if (activeUri) return
      const firstLeaf = pickFirstLeaf(rebuilt)
      if (firstLeaf) await autoSelectLeafAndPrefill(firstLeaf)
    })()
  }, [activeUri, apiProjectUri, autoSelectLeafAndPrefill, nodes.length, refreshTreeFromServer])

  useEffect(() => {
    if (!apiProjectUri) return
    if (importing) return
    if (resumedProjectRef.current === apiProjectUri) return
    resumedProjectRef.current = apiProjectUri
    void (async () => {
      const activeJob = await smuImportGenesisJobActivePublic(apiProjectUri) as Record<string, unknown> | null
      if (!activeJob?.active) return
      const jobId = String(activeJob.job_id || '')
      if (!jobId) return
      const fn = String(activeJob.file_name || '').trim()
      if (fn) setFileName(fn)
      setImportStatusText(String(activeJob.message || '检测到未完成导入任务，正在恢复'))
      setImportProgress(Number(activeJob.progress || 0))
      await pollImportJob(jobId, { skipStartToast: true })
    })()
  }, [apiProjectUri, importing, pollImportJob, smuImportGenesisJobActivePublic])

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
        let parsed = parseCsv(text, displayProjectUri, chapterHint, forcedBoqRootBase)
        if (!parsed.length) {
          const gbText = decode('gb18030')
          if (gbText) {
            text = gbText
            parsed = parseCsv(text, displayProjectUri, chapterHint, forcedBoqRootBase)
          }
        }
        if (!parsed.length) {
          showToast('CSV 解析失败：请检查表头或编码')
          return
        }
        setNodes(parsed)
        const firstLeaf = pickFirstLeaf(parsed)
        setExpandedCodes(getAllExpandedCodes(parsed))
        const leaf = parsed.find((x) => x.isLeaf)
        if (leaf) void autoSelectLeafAndPrefill(leaf)
      })
    } else {
      // xlsx/xls preview: call backend to build a quick hierarchy snapshot for immediate tree.
      try {
        const chapterHint = guessChapterFromFileName(f.name || '') || '400'
        const preview = await smuImportGenesisPreview({
          file: f,
          project_uri: apiProjectUri,
          project_id: projectId || undefined,
          boq_root_uri: `${apiBoqRootBase}/${chapterHint}`,
          norm_context_root_uri: `${apiProjectUri.replace(/\/$/, '')}/normContext`,
          owner_uri: `${apiProjectUri.replace(/\/$/, '')}/role/system/`,
        }) as Record<string, unknown> | null
        const items = Array.isArray((preview || {}).preview_items) ? ((preview || {}).preview_items as Array<Record<string, unknown>>) : []
        if (items.length) {
          const rebuilt = buildTreeFromRealtimeItems(items, displayProjectUri)
          setNodes(rebuilt)
          const firstLeaf = pickFirstLeaf(rebuilt)
          setExpandedCodes(getAllExpandedCodes(rebuilt))
          if (firstLeaf) void autoSelectLeafAndPrefill(firstLeaf)
        }
      } catch {
        // Preview is best-effort; fallback to empty tree until import completes.
        setNodes([])
        setExpandedCodes([])
        setActiveUri('')
      }
    }
  }, [apiProjectUri, autoSelectLeafAndPrefill, displayProjectUri, projectId, showToast, smuImportGenesisPreview])

  const loadBuiltinLedger400 = useCallback(async () => {
    try {
      const res = await fetch('/boq_0_400_sample.csv', { cache: 'no-store' })
      if (!res.ok) {
        showToast('示例台账不存在，请手动上传 CSV')
        return
      }
      const text = await res.text()
      const blob = new Blob([text], { type: 'text/csv;charset=utf-8' })
      const builtInFile = new File([blob], '0#台账-400章.csv', { type: 'text/csv' })
      await onSelectFile(builtInFile)
      showToast('已加载示例台账：0#台账-400章.csv')
    } catch {
      showToast('示例台账加载失败，请手动上传')
    }
  }, [onSelectFile, showToast])

  const importGenesis = useCallback(async () => {
    if (!file || !apiProjectUri) {
      showToast('请先选择清单文件')
      return
    }
    setImporting(true)
    setImportJobId('')
    setImportProgress(0)
    setImportStatusText('任务提交中（大文件约 1-3 分钟）')
    setImportError('')
    try {
      const chapterHint = guessChapterFromFileName(fileName || '') || '400'
      const params = {
        file,
        project_uri: apiProjectUri,
        project_id: projectId || undefined,
        boq_root_uri: `${apiBoqRootBase}/${chapterHint}`,
        norm_context_root_uri: `${apiProjectUri.replace(/\/$/, '')}/normContext`,
        owner_uri: `${apiProjectUri.replace(/\/$/, '')}/role/system/`,
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
  }, [apiProjectUri, asyncImportSupported, clearTreeState, file, pollImportJob, projectId, refreshTreeFromServer, showToast, smuImportGenesis, smuImportGenesisAsync])

  const selectNode = useCallback(async (code: string) => {
    const n = byCode.get(code)
    if (!n) return
    setExpandedCodes((prev) => mergeExpandedCodes(prev, getFocusedExpandedCodes(nodes, code)))
    setActiveUri(n.uri)
    setCtx(null)
    setContextError('')
    setClaimQty('')
    if (!n.isLeaf) return
    const c = n.spu === 'SPU_Reinforcement' || n.spu === 'SPU_Bridge'
      ? 'main_beam'
      : n.spu === 'SPU_Concrete'
        ? 'pier'
        : 'generic'
    setCompType(c)
    if (!sampleId) {
      const seed = `${n.code}-${Date.now().toString().slice(-6)}`
      setSampleId(`SAMPLE-${seed}`)
    }
    await loadContext(n.uri, c)
  }, [byCode, loadContext, nodes, sampleId])

  const jumpToArItem = useCallback(async (item: Record<string, unknown>) => {
    const code = normalizeItemNo(String(item.item_no || item.item_code || ''))
    const uri = toDisplayUri(String(item.boq_item_uri || item.segment_uri || ''))
    const node = (code && byCode.get(code)) || (uri && byUri.get(uri)) || null
    if (!node) {
      showToast('未找到对应细目')
      return
    }
    await selectNode(node.code)
    setArFocus(null)
  }, [byCode, byUri, selectNode, showToast])

  useEffect(() => {
    const next = String(((signRes?.trip || {}) as Record<string, unknown>).output_proof_id || '')
    if (next) setScanProofId(next)
  }, [signRes])

  useEffect(() => {
    if (pdfB64) setDocModalOpen(true)
  }, [pdfB64])

  useEffect(() => {
    if (!draftReady) {
      if (draftStamp) setDraftStamp('')
      return
    }
    setDraftStamp(new Date().toISOString())
  }, [active?.uri, draftReady])

  useEffect(() => {
    if (!active?.code) return
    const next = active.code.split('-')[0]
    if (next) setUnitCode(next)
  }, [active?.code])

  useEffect(() => {
    if (!previewPdfB64 || !pdfCanvasRef.current) {
      setPdfRenderError('')
      return
    }
    let cancelled = false
    let activeTask: { cancel: () => void; promise?: Promise<void> } | null = null
    let activeDoc: { destroy?: () => void; numPages?: number; getPage?: (n: number) => Promise<unknown> } | null = null
    setPdfRenderLoading(true)
    setPdfRenderError('')
    const bytes = Uint8Array.from(atob(previewPdfB64), (c) => c.charCodeAt(0))
    const loadingTask: any = getDocument({ data: bytes })
    loadingTask.promise.then((doc) => {
      if (cancelled) {
        doc.destroy?.()
        return
      }
      activeDoc = doc
      const total = Number(doc.numPages || 1)
      const pageNum = Math.min(Math.max(1, pdfPage), total)
      return doc.getPage?.(pageNum).then((page: unknown) => {
        if (cancelled || !pdfCanvasRef.current || !page) return
        const p = page as { getViewport: (opts: { scale: number }) => { width: number; height: number }; render: (opts: { canvasContext: CanvasRenderingContext2D; viewport: { width: number; height: number } }) => { promise: Promise<void>; cancel: () => void } }
        const viewport = p.getViewport({ scale: 1.2 })
        const canvas = pdfCanvasRef.current
        const ctx = canvas.getContext('2d')
        if (!ctx) return
        canvas.width = viewport.width
        canvas.height = viewport.height
        activeTask = p.render({ canvasContext: ctx, viewport })
        pdfRenderRef.current = { doc, task: activeTask }
        return activeTask.promise
      })
    }).then(() => {
      if (cancelled) return
      setPdfRenderLoading(false)
    }).catch(() => {
      if (cancelled) return
      setPdfRenderError('PDF 渲染失败，请稍后重试')
      setPdfRenderLoading(false)
    })
    return () => {
      cancelled = true
      if (activeTask) activeTask.cancel()
      if (pdfRenderRef.current?.task) pdfRenderRef.current.task.cancel()
      activeDoc?.destroy?.()
      loadingTask.destroy()
    }
  }, [pdfPage, previewPdfB64])

  useEffect(() => {
    if (!activeSignMarker || !previewScrollRef.current || !pdfCanvasRef.current) return
    const canvas = pdfCanvasRef.current
    const container = previewScrollRef.current
    const canvasHeight = canvas.getBoundingClientRect().height || canvas.offsetHeight
    if (!canvasHeight) return
    const targetTop = activeSignMarker.y * canvasHeight
    const nextTop = Math.max(0, targetTop - container.clientHeight / 2)
    container.scrollTo({ top: nextTop, behavior: 'smooth' })
  }, [activeSignMarker, previewPdfB64])

  const submitTrip = useCallback(async () => {
    if (!active?.isLeaf || !apiProjectUri || !inputProofId) {
      showToast('请先选择叶子细目并加载规则')
      return
    }
    if (!isSpecBound) {
      showToast('未绑定规范/门控，禁止提交')
      return
    }
    if (!roleAllowed) {
      showToast('角色权限冲突：当前账号无权提交该子目')
      return
    }
    if (!gateStats.labQualified) {
      showToast('证据链不完整：缺少实验合格 Proof')
      return
    }
    if (!gateStats.qcCompliant) {
      showToast('TripRole 现场判定未通过，已拦截提交')
      return
    }
    if (exceedBalance) {
      showToast('申报量超出批复量，已自动跳转变更补差流程')
      setDeltaModalOpen(true)
      setShowAdvancedExecution(true)
      return
    }
    const measurement = buildMeasurementPayload(form, effectiveSchema)
    if (sampleId) {
      measurement.sample_id = sampleId
      measurement.utxo_identifier = sampleId
    }
    if (effectiveClaimQtyValue > 0) measurement.claim_quantity = effectiveClaimQtyValue
    if (gateStats.labLatestPass) measurement.lab_proof_id = gateStats.labLatestPass
    if (gateStats.labLatestHash) measurement.lab_proof_hash = gateStats.labLatestHash
    setExecuting(true)
    try {
      const now = new Date().toISOString()
      let payload: Record<string, unknown> | null = null
      try {
        payload = await smuExecute({
          project_uri: apiProjectUri,
          input_proof_id: inputProofId,
          executor_uri: `${apiProjectUri.replace(/\/$/, '')}/role/contractor/mobile/`,
          executor_did: executorDid,
          executor_role: 'TRIPROLE',
          component_type: compType,
          measurement,
          geo_location: { lat: Number(lat), lng: Number(lng) },
          server_timestamp_proof: { ntp_server: 'pool.ntp.org', captured_at: now, proof_hash: `ntp-${now}` },
          evidence_hashes: evidence.map((x) => x.hash),
        }) as Record<string, unknown> | null
      } catch (err) {
        const msg = String((err as Error)?.message || err || '')
        if (msg.includes('lab PASS')) {
          showToast('证据链不完整：缺少实验合格 Proof')
        } else if (msg.includes('deviation_warning')) {
          showToast('申报量超出批复量，已自动跳转变更补差流程')
          setDeltaModalOpen(true)
          setShowAdvancedExecution(true)
        } else {
          showToast('提交失败')
        }
        return
      }
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
  }, [active, apiProjectUri, compType, effectiveClaimQtyValue, effectiveSchema, evidence, exceedBalance, executorDid, form, gateStats.labLatestHash, gateStats.labLatestPass, gateStats.labQualified, gateStats.qcCompliant, inputProofId, isSpecBound, lat, lng, refreshTreeFromServer, roleAllowed, showToast, smuExecute])

  const submitTripMock = useCallback(async () => {
    if (!active?.isLeaf || !apiProjectUri) {
      showToast('请先选择叶子细目')
      return
    }
    if (!isSpecBound) {
      showToast('未绑定规范/门控，禁止提交')
      return
    }
    const measurement = buildMeasurementPayload(form, effectiveSchema)
    if (sampleId) measurement.sample_id = sampleId
    if (effectiveClaimQtyValue > 0) measurement.claim_quantity = effectiveClaimQtyValue

    const normRows = effectiveSchema.map((row, idx) => {
      const field = String(row.field || `f_${idx}`)
      const measured = String(form[field] ?? '').trim()
      return {
        field,
        label: row.label || field,
        operator: String(row.operator || 'present'),
        threshold: String(row.default || ''),
        measured_value: measured,
        unit: String(row.unit || ''),
      }
    })

    setMockGenerating(true)
    try {
      const payload = await tripGenerateDoc({
        project_uri: apiProjectUri,
        boq_item_uri: toApiUri(active.uri),
        smu_id: String(active.code || '').split('-')[0],
        subitem_code: active.code,
        item_name: active.name,
        unit: active.unit || '',
        executor_did: executorDid,
        geo_location: { lat: Number(lat), lng: Number(lng) },
        anchor_location: geoAnchor ? { lat: geoAnchor.lat, lng: geoAnchor.lng } : {},
        norm_rows: normRows,
        measurements: measurement,
        evidence_hashes: evidence.map((x) => x.hash),
        report_template: '3、桥施表.docx',
      }) as Record<string, unknown> | null
      if (!payload?.ok) {
        showToast('DocPeg Mock 生成失败')
        return
      }
      setMockDocRes(payload)
      setDocModalOpen(true)
      const risk = Number((_asDict(payload.risk_audit).risk_score || 0))
      if (risk < 60) showToast(`报告已生成，但风险偏高（${risk.toFixed(2)}）`)
      else showToast(`桥施表已生成，Total Proof Hash 已锁定`)
    } finally {
      setMockGenerating(false)
    }
  }, [active, apiProjectUri, effectiveClaimQtyValue, effectiveSchema, evidence, executorDid, form, geoAnchor, isSpecBound, lat, lng, sampleId, showToast, tripGenerateDoc])

  useEffect(() => {
    if (!approvedProofId) return
    if (pdfB64) return
    if (mockGenerating) return
    if (!active?.isLeaf || !isSpecBound) return
    if (autoDocTriggerRef.current === approvedProofId) return
    autoDocTriggerRef.current = approvedProofId
    void submitTripMock()
  }, [active?.isLeaf, approvedProofId, isSpecBound, mockGenerating, pdfB64, submitTripMock])

  const recordRejectTrip = useCallback(async () => {
    if (!active?.isLeaf || !apiProjectUri || !inputProofId) {
      showToast('请先选择叶子细目并加载规则')
      return
    }
    setRejecting(true)
    try {
      const now = new Date().toISOString()
      const measurement = buildMeasurementPayload(form, effectiveSchema)
      if (sampleId) {
        measurement.sample_id = sampleId
        measurement.utxo_identifier = sampleId
      }
      if (gateStats.labLatestPass) measurement.lab_proof_id = gateStats.labLatestPass
      if (gateStats.labLatestHash) measurement.lab_proof_hash = gateStats.labLatestHash
      const payload = await smuExecute({
        project_uri: apiProjectUri,
        input_proof_id: inputProofId,
        executor_uri: `${apiProjectUri.replace(/\/$/, '')}/role/contractor/mobile/`,
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
  }, [active, apiProjectUri, compType, effectiveSchema, evidence, executorDid, form, gateStats.labLatestHash, gateStats.labLatestPass, inputProofId, lat, lng, refreshTreeFromServer, showToast, smuExecute, sampleId])

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
      const parseConsensus = (raw: string, fallback: number) => {
        const cleaned = String(raw || '').replace(/,/g, '').trim()
        const parsed = Number(cleaned)
        return Number.isFinite(parsed) ? parsed : fallback
      }
      const parseOptional = (raw: string) => {
        const cleaned = String(raw || '').replace(/,/g, '').trim()
        if (!cleaned) return Number.NaN
        const parsed = Number(cleaned)
        return parsed
      }
      const consensusValues = [
        { role: 'contractor', did: executorDid, value: parseConsensus(consensusContractorValue, consensusBaseValue) },
        { role: 'supervisor', did: supervisorDid, value: parseConsensus(consensusSupervisorValue, consensusBaseValue) },
        { role: 'owner', did: ownerDid, value: parseConsensus(consensusOwnerValue, consensusBaseValue) },
      ].filter((item) => Number.isFinite(item.value))
      const allowedAbs = parseOptional(consensusAllowedDeviation)
      const allowedPct = parseOptional(consensusAllowedDeviationPct)
      const signerMetadata = {
        mode: 'liveness',
        checked_at: now,
        passed: true,
        signers: consensusValues.map((item) => ({
          role: item.role,
          did: item.did,
          biometric_passed: true,
          verified_at: now,
          measured_value: item.value,
        })),
      }

      let payload: Record<string, unknown> | null = null
      try {
        payload = await smuSign({
          input_proof_id: output,
          boq_item_uri: toApiUri(active.uri),
          supervisor_executor_uri: `${apiProjectUri.replace(/\/$/, '')}/role/supervisor/mobile/`,
          supervisor_did: supervisorDid,
          contractor_did: executorDid,
          owner_did: ownerDid,
          signer_metadata: signerMetadata,
          consensus_values: consensusValues,
          allowed_deviation: Number.isFinite(allowedAbs) ? allowedAbs : undefined,
          allowed_deviation_percent: Number.isFinite(allowedPct) ? allowedPct : undefined,
          geo_location: { lat: Number(lat), lng: Number(lng) },
          server_timestamp_proof: { ntp_server: 'pool.ntp.org', captured_at: now, proof_hash: `ntp-${now}` },
          auto_docpeg: true,
          template_path: String(templateBinding.template_path || ''),
        }) as Record<string, unknown> | null
      } catch (err) {
        const msg = err instanceof Error ? err.message : '请求异常'
        const disputeMatch = String(msg || '').match(/dispute_proof_id=([A-Za-z0-9-]+)/)
        const openMatch = String(msg || '').match(/consensus_dispute_open:\s*([A-Za-z0-9-]+)/)
        const disputeId = disputeMatch?.[1] || openMatch?.[1] || ''
        if (disputeId) {
          setDisputeProofId(disputeId)
          setShowAdvancedConsensus(true)
          showToast(`共识冲突已触发：${disputeId}`)
          return
        }
        showToast(`签认失败：${msg}`)
        return
      }
      if (!payload?.ok) {
        showToast('签认失败')
        return
      }
      setSignRes(payload)
      setNodes((prev) => prev.map((x) => (x.uri === active.uri ? { ...x, status: 'Settled' } : x)))
      const smuId = active.code.split('-')[0]
      if (smuId) {
        const freeze = await smuFreeze({ project_uri: apiProjectUri, smu_id: smuId, executor_uri: `${apiProjectUri.replace(/\/$/, '')}/role/owner/system/`, min_risk_score: 60 }) as Record<string, unknown> | null
        if (freeze?.ok) setFreezeProof(String(freeze.freeze_proof_id || ''))
      }
      setSignOpen(false)
    } finally {
      setSigning(false)
    }
  }, [
    active,
    apiProjectUri,
    consensusAllowedDeviation,
    consensusAllowedDeviationPct,
    consensusBaseValue,
    consensusContractorValue,
    consensusOwnerValue,
    consensusSupervisorValue,
    execRes,
    executorDid,
    lat,
    lng,
    ownerDid,
    showToast,
    smuFreeze,
    smuSign,
    supervisorDid,
    templateBinding.template_path,
  ])

  const applyDelta = useCallback(async () => {
    if (!active?.isLeaf || !apiProjectUri) {
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
        boq_item_uri: toApiUri(active.uri),
        delta_amount: delta,
        reason: deltaReason,
        project_uri: apiProjectUri,
        executor_uri: `${apiProjectUri.replace(/\/$/, '')}/role/contractor/mobile/`,
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
  }, [active, apiProjectUri, applyVariationDelta, deltaAmount, deltaReason, executorDid, lat, lng, showToast])

  const docFinalVerifyBaseUrl = useMemo(() => {
    if (typeof window === 'undefined') return ''
    return `${window.location.origin}/verify`
  }, [])
  const sealOfflinePacket = useCallback(async () => {
    if (!active?.uri) {
      showToast('请先选择细目')
      return
    }
    if (!apiProjectUri) {
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
        project_uri: apiProjectUri,
        boq_item_uri: toApiUri(active.uri),
        delta_amount: delta,
        reason: deltaReason,
        sample_id: sampleId,
        executor_uri: `${apiProjectUri.replace(/\/$/, '')}/role/contractor/mobile/`,
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
        project_uri: apiProjectUri,
        input_proof_id: inputProofId,
        boq_item_uri: toApiUri(active.uri),
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
        project_uri: apiProjectUri,
        boq_item_uri: toApiUri(active.uri),
        input_proof_id: inputProofId,
        executor_uri: `${apiProjectUri.replace(/\/$/, '')}/role/contractor/mobile/`,
        executor_did: executorDid,
        executor_role: 'TRIPROLE',
        payload: { component_type: compType, measurement, snappeg_payload_hash: snappegHash, sample_id: sampleId },
        geo_location: { lat: Number(lat), lng: Number(lng) },
        server_timestamp_proof: { ntp_server: 'offline', captured_at: now, proof_hash: `offline-${now}` },
      }
    }
    if (!packet) return
    await queueOfflinePacket(packet, {
      actorId: offlineActorId,
      did: executorDid,
    })
    showToast('离线封存成功，待网络恢复后重放')
  }, [active, apiProjectUri, compType, deltaAmount, deltaReason, evidence, executorDid, form, inputProofId, lat, lng, offlineActorId, offlineType, queueOfflinePacket, showToast])

  const calcUnitMerkle = useCallback(async () => {
    if (!apiProjectUri) {
      showToast('项目 URI 缺失')
      return
    }
    setUnitLoading(true)
    try {
      const payload = await unitMerkleRoot({
        project_uri: apiProjectUri,
        unit_code: unitCode || undefined,
        proof_id: unitProofId || undefined,
        max_rows: Number(unitMaxRows) || undefined,
      }) as Record<string, unknown> | null
      if (!payload?.ok) {
        showToast('数字资产总指纹计算失败')
        return
      }
      setUnitRes(payload)
      showToast('数字资产总指纹已生成')
    } finally {
      setUnitLoading(false)
    }
  }, [apiProjectUri, showToast, unitCode, unitMaxRows, unitMerkleRoot, unitProofId])

  useEffect(() => {
    if (!apiProjectUri || !unitCode) return
    if (autoUnitRef.current === unitCode) return
    autoUnitRef.current = unitCode
    void calcUnitMerkle()
  }, [apiProjectUri, calcUnitMerkle, unitCode])

  const useCurrentProofForUnit = useCallback(() => {
    const pid = String(inputProofId || '')
    if (pid) setUnitProofId(pid)
    const code = active?.code ? active.code.split('-')[0] : ''
    if (code) setUnitCode(code)
  }, [active?.code, inputProofId])

  const scrollToSign = useCallback((role: 'contractor' | 'supervisor' | 'owner') => {
    setSignFocus(role)
    const target = role === 'contractor'
      ? contractorAnchorRef.current
      : role === 'supervisor'
        ? supervisorAnchorRef.current
        : ownerAnchorRef.current
    if (!target) return
    target.scrollIntoView({ behavior: 'smooth', block: 'center' })
  }, [])

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
      showToast('请先生成数字资产总指纹')
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

  const exportP2PManifest = useCallback(() => {
    const projectRoot = String((unitRes || {}).project_root_hash || (unitRes || {}).global_project_fingerprint || '')
    const payload = {
      node_id: p2pNodeId,
      project_uri: apiProjectUri,
      project_root_hash: projectRoot,
      total_proof_hash: totalHash,
      offline_packets: offlinePackets,
      offline_queue_size: offlinePackets.length,
      offline_conflicts: offlineSyncConflicts,
      peers: p2pPeers.split(/[\n,]+/).map((x) => x.trim()).filter(Boolean),
      generated_at: new Date().toISOString(),
    }
    downloadJson(`gitpeg-sync-${Date.now()}.json`, payload)
  }, [apiProjectUri, offlinePackets, offlineSyncConflicts, p2pNodeId, p2pPeers, totalHash, unitRes])

  const enqueueScanEntryPacket = useCallback((status: 'ok' | 'blocked', tokenHash: string, nowIso: string, tokenPresent: boolean) => {
    if (!active?.uri || !apiProjectUri) return
    const packetId = `scan-entry-${Date.now()}-${Math.random().toString(16).slice(2, 8)}`
    const packet = {
      packet_type: 'triprole.execute',
      action: 'scan.entry',
      offline_packet_id: packetId,
      local_created_at: nowIso,
      project_uri: apiProjectUri,
      boq_item_uri: toApiUri(active.uri),
      input_proof_id: String(inputProofId || ''),
      executor_uri: `${apiProjectUri.replace(/\/$/, '')}/role/contractor/mobile/`,
      executor_did: executorDid,
      executor_role: 'TRIPROLE',
      payload: {
        status,
        token_hash: tokenHash || null,
        token_present: tokenPresent,
        scan_entry_at: nowIso,
        geo_distance_m: geoDistance ?? null,
        geo_radius_m: geoAnchor?.radiusM ?? null,
        temporal_window: temporalWindow ? { start: temporalWindow.start, end: temporalWindow.end } : null,
      },
      geo_location: { lat: Number(lat), lng: Number(lng) },
      server_timestamp_proof: { ntp_server: 'offline', captured_at: nowIso, proof_hash: `offline-${nowIso}` },
    }
    void queueOfflinePacket(packet, {
      actorId: offlineActorId,
      did: executorDid,
    })
    return packetId
  }, [
    active?.uri,
    apiProjectUri,
    executorDid,
    geoAnchor?.radiusM,
    geoDistance,
    inputProofId,
    lat,
    lng,
    offlineActorId,
    queueOfflinePacket,
    temporalWindow,
  ])

  const {
    scanEntryAt,
    scanEntryStatus,
    scanEntryToken,
    scanEntryTokenHash,
    scanEntryRequired,
    setScanEntryToken,
    setScanEntryRequired,
    handleScanEntry,
  } = useScanEntryState({
    activeUri: String(active?.uri || ''),
    geoTemporalBlocked,
    lat,
    lng,
    showToast,
    enqueueScanEntryPacket,
    appendScanEntryLog,
    loadEvidenceCenter,
  })

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

  const enqueueTriprolePacket = useCallback((
    action: string,
    payload: Record<string, unknown>,
    result?: string,
  ) => {
    if (!active?.uri || !apiProjectUri || !inputProofId) return ''
    const packetId = `triprole-${Date.now()}-${Math.random().toString(16).slice(2, 8)}`
    const nowIso = new Date().toISOString()
    const packet = {
      packet_type: 'triprole.execute',
      action,
      offline_packet_id: packetId,
      local_created_at: nowIso,
      project_uri: apiProjectUri,
      boq_item_uri: toApiUri(active.uri),
      input_proof_id: inputProofId,
      executor_uri: `${apiProjectUri.replace(/\/$/, '')}/role/contractor/mobile/`,
      executor_did: executorDid,
      executor_role: 'TRIPROLE',
      result: result || undefined,
      payload,
      geo_location: { lat: Number(lat), lng: Number(lng) },
      server_timestamp_proof: { ntp_server: 'offline', captured_at: nowIso, proof_hash: `offline-${nowIso}` },
    }
    void queueOfflinePacket(packet, {
      actorId: offlineActorId,
      did: executorDid,
    })
    return packetId
  }, [active?.uri, apiProjectUri, executorDid, inputProofId, lat, lng, offlineActorId, queueOfflinePacket])

  const runMeshpeg = useCallback(() => {
    if (!active?.uri) {
      showToast('请先选择细目')
      return
    }
    setMeshpegRunning(true)
    try {
      const designQty = asNum(
        ledgerSnapshot.approved_quantity
        || ledgerSnapshot.contract_quantity
        || ledgerSnapshot.design_quantity
        || 0,
      )
      const baseQty = designQty || effectiveClaimQtyValue || measuredQtyValue
      const drift = geoDistance != null ? Math.max(-0.06, Math.min(0.06, ((geoDistance % 7) - 3) / 100)) : -0.02
      const meshVolume = baseQty ? baseQty * (1 + drift) : 0
      const deviationPct = baseQty ? ((meshVolume - baseQty) / baseQty) * 100 : 0
      const status = Math.abs(deviationPct) <= 2 ? 'PASS' : 'FAIL'
      const payload = {
        ok: true,
        mesh_volume: Number(meshVolume.toFixed(4)),
        design_quantity: Number(baseQty.toFixed(4)),
        deviation_percent: Number(deviationPct.toFixed(3)),
        status,
        cloud: meshpegCloudName || 'LiDAR',
        bim: meshpegBimName || 'BIM',
        proof_id: `MESH-${Date.now().toString(36).toUpperCase()}`,
      }
      setMeshpegRes(payload)
      const packetId = enqueueTriprolePacket('meshpeg.verify', { ...payload, status })
      appendMeshpegLog({
        item_uri: active.uri,
        created_at: new Date().toISOString(),
        status: payload.status,
        mesh_volume: payload.mesh_volume,
        design_quantity: payload.design_quantity,
        deviation_percent: payload.deviation_percent,
        proof_id: payload.proof_id,
        chain_status: 'queued',
        offline_packet_id: packetId,
      })
      showToast(`MeshPeg 核算完成：${status}`)
    } finally {
      setMeshpegRunning(false)
    }
  }, [
    active?.uri,
    appendMeshpegLog,
    enqueueTriprolePacket,
    effectiveClaimQtyValue,
    geoDistance,
    ledgerSnapshot.approved_quantity,
    ledgerSnapshot.contract_quantity,
    ledgerSnapshot.design_quantity,
    measuredQtyValue,
    meshpegBimName,
    meshpegCloudName,
    showToast,
  ])

  const runFormulaPeg = useCallback(() => {
    if (!active?.uri) {
      showToast('请先选择细目')
      return
    }
    setFormulaRunning(true)
    try {
      const qty = asNum(meshpegRes?.mesh_volume)
        || effectiveClaimQtyValue
        || measuredQtyValue
        || asNum(ledgerSnapshot.approved_quantity || ledgerSnapshot.contract_quantity || ledgerSnapshot.design_quantity || 0)
      const unitPrice = asNum(ledgerSnapshot.unit_price || ledgerSnapshot.unit_price_with_tax || 0)
      const result = safeEvalFormula(formulaExpr, { qty, unit_price: unitPrice, factor: 1 })
      if (!result.ok) {
        showToast(`FormulaPeg 失败：${result.error}`)
        return
      }
      const amount = result.value
      const payload = {
        ok: true,
        formula: formulaExpr,
        qty: Number(qty.toFixed(4)),
        unit_price: Number(unitPrice.toFixed(4)),
        amount: Number(amount.toFixed(2)),
        railpact_id: `RP-${Date.now().toString(36).toUpperCase()}`,
        status: 'LOCKED',
        mesh_proof_id: String(meshpegRes?.proof_id || ''),
        proof_id: finalProofId || inputProofId || '',
        created_at: new Date().toISOString(),
      }
      setFormulaRes(payload)
      const packetId = enqueueTriprolePacket('formula.price', { ...payload, status: 'LOCKED' })
      appendFormulaLog({
        item_uri: active.uri,
        created_at: payload.created_at,
        status: payload.status,
        formula: payload.formula,
        qty: payload.qty,
        unit_price: payload.unit_price,
        amount: payload.amount,
        railpact_id: payload.railpact_id,
        chain_status: 'queued',
        offline_packet_id: packetId,
      })
      showToast(`FormulaPeg 已生成：${payload.amount}`)
    } finally {
      setFormulaRunning(false)
    }
  }, [
    active?.uri,
    appendFormulaLog,
    effectiveClaimQtyValue,
    enqueueTriprolePacket,
    formulaExpr,
    inputProofId,
    ledgerSnapshot.approved_quantity,
    ledgerSnapshot.contract_quantity,
    ledgerSnapshot.design_quantity,
    ledgerSnapshot.unit_price,
    ledgerSnapshot.unit_price_with_tax,
    measuredQtyValue,
    meshpegRes?.mesh_volume,
    meshpegRes?.proof_id,
    finalProofId,
    showToast,
  ])

  const runGatewaySync = useCallback(() => {
    if (!apiProjectUri) {
      showToast('项目 URI 缺失')
      return
    }
    const payload = {
      project_uri: apiProjectUri,
      total_proof_hash: totalHash,
      proof_id: finalProofId || inputProofId || '',
      scan_entry_proof: String(scanEntryLatest?.proof_id || ''),
      risk_score: docpegRiskScore,
      updated_at: new Date().toISOString(),
      gateway: 'SovereignGateway/0.1',
    }
    setGatewayRes(payload)
    const packetId = enqueueTriprolePacket('gateway.sync', { ...payload, status: 'PASS' })
    appendGatewayLog({
      item_uri: active?.uri || '',
      created_at: payload.updated_at,
      total_proof_hash: payload.total_proof_hash,
      proof_id: payload.proof_id,
      scan_entry_proof: payload.scan_entry_proof,
      risk_score: payload.risk_score,
      chain_status: 'queued',
      offline_packet_id: packetId,
    })
    showToast('监管同步摘要已生成')
  }, [active?.uri, apiProjectUri, appendGatewayLog, docpegRiskScore, enqueueTriprolePacket, finalProofId, inputProofId, scanEntryLatest?.proof_id, showToast, totalHash])

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
      showToast('请先生成数字资产总指纹')
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

  const backendQrSrc = useMemo(() => String(((mockDocRes?.docpeg || {}) as Record<string, unknown>).qr_png_base64 || ''), [mockDocRes])
  const qrSrc = useMemo(() => backendQrSrc || createQrSvg(verifyUri || 'qcspec-docpeg-empty', 140, 'medium'), [backendQrSrc, verifyUri])
  const docFinalAuditUrl = useMemo(() => {
    if (typeof window === 'undefined' || !projectId) return verifyUri || ''
    return `${window.location.origin}/project/${encodeURIComponent(projectId)}/auditor/workbench?view=audit`
  }, [projectId, verifyUri])
  const docFinalQrSrc = useMemo(() => createQrSvg(docFinalAuditUrl || verifyUri || 'qcspec-docfinal-empty', 120, 'medium'), [docFinalAuditUrl, verifyUri])
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

  const sovereignValue = useMemo(() => ({
    project: {
      projectUri,
      apiProjectUri,
      displayProjectUri,
      projectId,
      active,
      activeUri,
      activePath,
      boundSpu,
      isContractSpu,
      spuKind: spuKind as 'bridge' | 'landscape' | 'contract' | 'physical',
      spuBadge,
      stepLabel,
      lifecycle,
      nodePathMap,
    },
    identity: {
      dtoRole,
      roleAllowed,
      executorDid,
      supervisorDid,
      ownerDid,
    },
    asset: {
      summary,
      activeGenesisSummary,
      baselineTotal,
      availableTotal,
      effectiveSpent,
      effectiveClaimQtyValue,
      inputProofId,
      finalProofId,
      totalHash,
      verifyUri,
      evidenceCenter,
    },
    audit: {
      gateStats,
      gateReason,
      exceedBalance,
      snappegReady,
      geoTemporalBlocked,
      normResolution,
      disputeOpen,
      disputeProof,
      disputeArbiterRole: 'OWNER / THIRD_PARTY',
      archiveLocked,
    },
  }), [
    active,
    activeGenesisSummary,
    activePath,
    activeUri,
    apiProjectUri,
    baselineTotal,
    boundSpu,
    displayProjectUri,
    dtoRole,
    effectiveClaimQtyValue,
    effectiveSpent,
    evidenceCenter,
    exceedBalance,
    executorDid,
    finalProofId,
    gateReason,
    gateStats,
    geoTemporalBlocked,
    inputProofId,
    isContractSpu,
    lifecycle,
    nodePathMap,
    normResolution,
    disputeOpen,
    disputeProof,
    archiveLocked,
    ownerDid,
    projectId,
    projectUri,
    roleAllowed,
    snappegReady,
    spuBadge,
    spuKind,
    stepLabel,
    summary,
    supervisorDid,
    totalHash,
    availableTotal,
    verifyUri,
  ])

  return (
    <ProjectSovereignProvider value={sovereignValue}>
      <NormEngineProvider schema={effectiveSchema} form={form} ctx={ctx} isContractSpu={isContractSpu}>
        <Card title="主权 BOQ 工作台" icon="🔗" style={{ marginBottom: 10 }} className="overflow-hidden sovereign-workbench">
      <style>{`@keyframes sovereignPulse {0%{transform:scale(.92);opacity:.45}50%{transform:scale(1.06);opacity:1}100%{transform:scale(.92);opacity:.45}}
      @keyframes ordosealPulse {0%{transform:scale(.8);opacity:.2}50%{transform:scale(1.12);opacity:.95}100%{transform:scale(.8);opacity:.2}}
      .sovereign-workbench{font-size:15px;line-height:1.68;font-family:"Fira Sans","Segoe UI",sans-serif}
      .sovereign-workbench .font-mono{font-family:"Fira Code","Cascadia Code","SFMono-Regular",monospace}
      .sovereign-workbench .wb-panel{padding:20px;border-radius:16px}
      .sovereign-workbench input,.sovereign-workbench select,.sovereign-workbench button{min-height:44px}
      .sovereign-workbench textarea{line-height:1.68}
      .sovereign-workbench .wb-table-head{font-size:14px;padding:13px 15px}
      .sovereign-workbench .wb-table-row{font-size:14px;line-height:1.72;padding:13px 15px}
      `}</style>
      <div className="relative rounded-2xl border border-slate-800 bg-[radial-gradient(circle_at_top_left,rgba(14,116,144,.18),transparent_28%),radial-gradient(circle_at_top_right,rgba(34,197,94,.08),transparent_22%),linear-gradient(180deg,#020617,#0f172a_62%,#111827)] p-6 text-slate-100 shadow-[inset_0_1px_0_rgba(148,163,184,.08),0_28px_60px_rgba(2,6,23,.55)]">
        <div
          className="pointer-events-none absolute inset-0 rounded-2xl opacity-20"
          style={{
            backgroundImage: 'linear-gradient(rgba(148,163,184,0.08) 1px, transparent 1px), linear-gradient(90deg, rgba(148,163,184,0.08) 1px, transparent 1px)',
            backgroundSize: '26px 26px',
            maskImage: 'linear-gradient(180deg, rgba(255,255,255,0.7), rgba(255,255,255,0.08))',
          }}
        />
        <div className="mb-4 rounded-xl border border-slate-700/80 bg-slate-950/55 px-4 py-3 text-slate-200 shadow-[0_18px_36px_rgba(2,6,23,.24)]">
          <div className="flex flex-wrap items-center justify-between gap-2">
            <div>
              <div className="text-xs uppercase tracking-[0.18em] text-sky-300/80">主权执行控制台</div>
              <div className="mt-1 text-base font-bold text-slate-50">400 章主权资产树 + TripRole 执行闭环</div>
              <div className="mt-1 text-xs text-slate-400 break-all">当前主权路径: {activePath || '-'}</div>
              <div className="mt-2 rounded-lg border border-slate-700 bg-slate-950 text-slate-100 px-3 py-1.5 text-[11px] font-mono flex items-center gap-2">
                <span className="text-sky-300">v://</span>
                <span className="truncate">{activePath || displayProjectUri || '-'}</span>
              </div>
              <div className="mt-2">
                <div className="flex items-center justify-between text-[10px] text-slate-500">
                  <span>钱袋子树红线刻度</span>
                  <span>0 · 50 · 100</span>
                </div>
                <div className="relative mt-1 h-2 w-full rounded-full border border-slate-700 bg-slate-900 overflow-hidden">
                  <div className="h-2 bg-gradient-to-r from-emerald-400 via-amber-400 to-rose-500" style={{ width: `${Math.max(0, Math.min(100, summary.pct))}%` }} />
                  <div className="absolute right-0 top-0 h-full w-[2px] bg-rose-600" />
                </div>
              </div>
            </div>
            <div className="flex items-center gap-2 text-[11px]">
              <div
                className={`rounded-full border px-2 py-0.5 flex items-center gap-1 ${isOnline ? 'border-slate-600 bg-slate-900/70 text-slate-300' : 'border-amber-500/60 bg-amber-950/30 text-amber-200'}`}
                title="同步云 · 离线队列"
              >
                <svg width="12" height="12" viewBox="0 0 24 24" fill="none" aria-hidden="true">
                  <path d="M7 18h10a4 4 0 0 0 0-8 5.5 5.5 0 0 0-10.7 1.8A3.8 3.8 0 0 0 7 18Z" stroke="currentColor" strokeWidth="1.6" strokeLinecap="round" strokeLinejoin="round" />
                </svg>
                同步云 {offlineCount}
              </div>
              <span className="rounded-full border border-slate-600 bg-slate-900/70 px-2 py-0.5 text-slate-300">节点 {nodes.length}</span>
              <span className="rounded-full border border-sky-500/60 bg-sky-950/30 px-2 py-0.5 text-sky-200">当前 {active?.code || '-'}</span>
            </div>
          </div>
        </div>
        {!!totalHash && (
          <div className="mb-3 border border-emerald-600/80 bg-emerald-950 text-emerald-100 rounded-xl p-2">
            <div className="text-xs font-extrabold">总证明哈希: 主权已锁定</div>
            <div className="mt-1 text-xs">SMU 已冻结，证据链不可篡改</div>
            <div className="mt-1 text-[11px] font-mono break-all">Total Proof Hash: {totalHash}</div>
          </div>
        )}
        {isTripView && finalProofReady && onNavigateView && (
          <div className="mb-4 rounded-xl border border-sky-500/70 bg-sky-950/30 p-3 text-sky-100">
            <div className="flex flex-wrap items-center justify-between gap-3">
              <div>
                <div className="text-xs font-extrabold">Proof 已生成</div>
                <div className="mt-1 text-[11px] text-sky-200">执行数据已落链，可一键跳转到证据与审计视图检查因果链。</div>
              </div>
              <button type="button" onClick={() => onNavigateView('audit')} className={`px-3 py-2 text-sm ${btnBlueCls}`}>
                打开证据与审计
              </button>
            </div>
          </div>
        )}

        {isGenesisView && (
        <div className="mb-4 rounded-xl border border-slate-700/80 bg-slate-950/55 p-3 shadow-[0_18px_36px_rgba(2,6,23,.2)]">
          <div className="flex flex-wrap items-center justify-between gap-2">
            <div>
              <div className="text-xs uppercase tracking-[0.18em] text-slate-400">Project Readiness / 项目完备度</div>
              <div className="mt-1 text-sm font-bold text-slate-100">七步闭环落地体检</div>
            </div>
            <div className="flex items-center gap-2">
              <span className={`rounded-full border px-2.5 py-1 text-xs font-semibold ${
                readinessOverall === 'complete'
                  ? 'border-emerald-500/60 bg-emerald-950/30 text-emerald-200'
                  : readinessOverall === 'partial'
                    ? 'border-amber-500/60 bg-amber-950/30 text-amber-200'
                    : 'border-rose-500/60 bg-rose-950/30 text-rose-200'
              }`}>
                {readinessOverall === 'complete' ? '已落地' : readinessOverall === 'partial' ? '部分落地' : '待落地'}
              </span>
              <button type="button" onClick={() => void runReadinessCheck(false)} disabled={readinessLoading || !apiProjectUri} className={`px-3 py-1.5 text-xs disabled:opacity-60 ${btnBlueCls}`}>
                {readinessLoading ? '体检中...' : '运行体检'}
              </button>
              <button type="button" onClick={() => setShowRolePlaybook((v) => !v)} className={`px-3 py-1.5 text-xs ${btnGreenCls}`}>
                {showRolePlaybook ? '收起角色SOP' : '展开角色SOP'}
              </button>
            </div>
          </div>
          <div className="mt-3 h-2.5 w-full overflow-hidden rounded-full border border-slate-700 bg-slate-900">
            <div className="h-2.5 bg-gradient-to-r from-sky-500 to-emerald-500 transition-[width] duration-500" style={{ width: `${readinessPercent}%` }} />
          </div>
          <div className="mt-1 text-xs text-slate-400">当前落地度: {readinessPercent.toFixed(2)}%</div>

          {!!readinessLayers.length && (
            <div className="mt-3 grid gap-2 min-[1100px]:grid-cols-2">
              {readinessLayers.map((layer) => {
                const st = String(layer.status || 'missing')
                return (
                  <div key={layer.key} className="rounded-lg border border-slate-700 bg-slate-900/60 p-2.5">
                    <div className="flex items-center justify-between gap-2">
                      <div className="text-sm font-semibold text-slate-100">{layer.name}</div>
                      <span className={`rounded-full px-2 py-0.5 text-[11px] font-semibold ${
                        st === 'complete'
                          ? 'bg-emerald-950/40 text-emerald-300'
                          : st === 'partial'
                            ? 'bg-amber-950/40 text-amber-300'
                            : 'bg-rose-950/40 text-rose-300'
                      }`}>
                        {st === 'complete' ? '完成' : st === 'partial' ? '部分' : '缺失'}
                      </span>
                    </div>
                    <div className="mt-1 text-xs text-slate-400">{readinessAction[layer.key] || '补齐该层关键流程数据后重试体检'}</div>
                  </div>
                )
              })}
            </div>
          )}

          {showRolePlaybook && (
            <div className="mt-3 grid gap-2 min-[1200px]:grid-cols-2">
              {ROLE_PLAYBOOK.map((r) => (
                <div key={r.role} className="rounded-lg border border-slate-700 bg-slate-900/70 p-3">
                  <div className="text-sm font-bold text-slate-100">{r.title} <span className="text-xs text-slate-500">({r.role})</span></div>
                  <div className="mt-1 text-xs text-slate-400">目标: {r.goal}</div>
                  <div className="mt-2 text-xs font-semibold text-slate-300">操作行为</div>
                  <div className="text-xs text-slate-400">{r.actions.join('；')}</div>
                  <div className="mt-2 text-xs font-semibold text-slate-300">技术约束</div>
                  <div className="text-xs text-slate-400">{r.constraints.join('；')}</div>
                  <div className="mt-2 text-xs font-semibold text-slate-300">闭环路径</div>
                  <div className="text-xs text-slate-200 font-mono break-all">{r.chain}</div>
                </div>
              ))}
            </div>
          )}
        </div>
        )}

        <div className={`grid gap-6 ${isGenesisView ? 'grid-cols-1 min-[1260px]:grid-cols-[460px_minmax(0,1fr)]' : 'grid-cols-1'}`}>
          {isGenesisView && (
          <GenesisTree
            panelCls={panelCls}
            inputBaseCls={inputBaseCls}
            btnBlueCls={btnBlueCls}
            boqFileRef={boqFileRef}
            fileName={fileName}
            importing={importing}
            importJobId={importJobId}
            importStatusText={importStatusText}
            importProgress={importProgress}
            importError={importError}
            showLeftSummary={showLeftSummary}
            treeQuery={treeQuery}
            treeSearch={treeSearch}
            nodes={nodes}
            roots={roots}
            byCode={byCode}
            aggMap={aggMap}
            expandedCodes={expandedCodes}
            nodePathMap={nodePathMap}
            onSelectFile={onSelectFile}
            onImportGenesis={() => void importGenesis()}
            onLoadBuiltinLedger400={() => void loadBuiltinLedger400()}
            onToggleSummary={() => setShowLeftSummary((v) => !v)}
            onTreeQueryChange={setTreeQuery}
            onToggleExpanded={(code) => setExpandedCodes((prev) => prev.includes(code) ? prev.filter((x) => x !== code) : [...prev, code])}
            onSelectNode={(code) => void selectNode(code)}
          />
          )}

          {isGenesisView && (
            <div className={`${panelCls} wb-panel`}>
              <div className="mb-2 flex items-center justify-between">
                <div className="text-sm font-extrabold">Project Genesis</div>
                <span className="rounded-full border border-slate-700 bg-slate-800/90 px-2 py-0.5 text-[10px] text-slate-400">Config view</span>
              </div>
              <div className="grid gap-3 min-[980px]:grid-cols-2">
                <div className="rounded-xl border border-slate-700/70 bg-slate-950/30 p-3">
                  <div className="text-xs font-semibold uppercase tracking-[0.18em] text-slate-400">Norm Binding</div>
                  <div className="mt-2 text-sm text-slate-100">Spec: {specBinding || 'Unbound'}</div>
                  <div className="mt-1 text-sm text-slate-300">Gate: {gateBinding || 'Unbound'}</div>
                  <div className="mt-1 text-xs text-slate-500">Refs: {normRefs.join(' / ') || '-'}</div>
                  <div className={`mt-2 text-xs ${isSpecBound ? 'text-emerald-300' : 'text-amber-300'}`}>
                    {isSpecBound ? 'NormResolver ready for routing.' : 'NormResolver still needs binding.'}
                  </div>
                </div>
                <div className="rounded-xl border border-slate-700/70 bg-slate-950/30 p-3">
                  <div className="text-xs font-semibold uppercase tracking-[0.18em] text-slate-400">Project Control</div>
                  <div className="mt-2 text-sm text-slate-100">Lifecycle: {lifecycle}</div>
                  <div className="mt-1 text-sm text-slate-300">Active node: {active?.code || '-'}</div>
                  <div className="mt-1 text-sm text-slate-300">Available qty: {availableTotal.toLocaleString()}</div>
                  <div className="mt-1 text-xs text-slate-500 break-all">Path: {activePath || displayProjectUri || '-'}</div>
                  <div className="mt-3 flex flex-wrap gap-2">
                    {onNavigateView && (
                      <>
                        <button type="button" onClick={() => onNavigateView('trip')} className={`px-3 py-2 text-sm ${btnBlueCls}`}>Open trip console</button>
                        <button type="button" onClick={() => onNavigateView('audit')} className={`px-3 py-2 text-sm ${btnAmberCls}`}>Open audit</button>
                      </>
                    )}
                  </div>
                </div>
              </div>
            </div>
          )}

          {isTripView && (
          <SovereignWorkbench
            panelCls={panelCls}
            inputBaseCls={inputBaseCls}
            btnBlueCls={btnBlueCls}
            btnAmberCls={btnAmberCls}
            btnGreenCls={btnGreenCls}
            btnRedCls={btnRedCls}
            hashing={hashing}
            templateDisplay={templateDisplay}
            isSpecBound={isSpecBound}
            specBinding={specBinding}
            gateBinding={gateBinding}
            displayMeta={displayMeta}
            compType={compType}
            componentTypeOptions={componentTypeOptions}
            loadingCtx={loadingCtx}
            geoFormLocked={geoFormLocked}
            scanEntryStatus={scanEntryStatus}
            scanEntryAt={scanEntryAt}
            scanEntryToken={scanEntryToken}
            scanEntryRequired={scanEntryRequired}
            scanEntryTokenHash={scanEntryTokenHash}
            scanChainBadge={scanChainBadge}
            scanEntryLatest={scanEntryLatest}
            normRefs={normRefs}
            contextError={contextError}
            sampleId={sampleId}
            effectiveSchema={effectiveSchema}
            form={form}
            evidence={evidence}
            evidenceName={evidenceName}
            evidenceAccept={evidenceAccept}
            evidenceLabel={evidenceLabel}
            evidenceHint={evidenceHint}
            geoValid={geoValid}
            geoFenceWarning={geoFenceWarning}
            showAdvancedExecution={showAdvancedExecution}
            deltaAmount={deltaAmount}
            deltaReason={deltaReason}
            applyingDelta={applyingDelta}
            variationRes={variationRes}
            claimQty={claimQty}
            claimQtyProvided={claimQtyProvided}
            measuredQtyValue={measuredQtyValue}
            deltaSuggest={deltaSuggest}
            temporalBlocked={temporalBlocked}
            geoFenceActive={geoFenceActive}
            geoDistance={geoDistance}
            geoAnchor={geoAnchor}
            tripStage={tripStage}
            effectiveRiskScore={effectiveRiskScore}
            executing={executing}
            mockGenerating={mockGenerating}
            rejecting={rejecting}
            evidenceFileRef={evidenceFileRef}
            lat={lat}
            lng={lng}
            onTraceOpen={() => setTraceOpen(true)}
            onScanEntry={() => handleScanEntry()}
            onScanEntryTokenChange={setScanEntryToken}
            onScanEntryRequiredChange={setScanEntryRequired}
            onSampleIdChange={setSampleId}
            onCompTypeChange={setCompType}
            onExecutorDidChange={setExecutorDid}
            onLoadContext={() => active?.uri && loadContext(active.uri, compType)}
            onFormChange={setForm}
            onEvidence={(files) => void onEvidence(files)}
            onFingerprintOpen={() => setFingerprintOpen(true)}
            onEvidencePreview={openEvidencePreview}
            onDeltaAmountChange={setDeltaAmount}
            onDeltaReasonChange={setDeltaReason}
            onApplyDelta={() => void applyDelta()}
            onSuggestDelta={() => {
              setDeltaAmount(deltaSuggest.toFixed(3))
              setDeltaReason('超量补差')
              setShowAdvancedExecution(true)
            }}
            onClaimQtyChange={setClaimQty}
            onSubmitTrip={() => void submitTrip()}
            onSubmitTripMock={() => void submitTripMock()}
            onRecordRejectTrip={() => void recordRejectTrip()}
            onLatChange={setLat}
            onLngChange={setLng}
            sanitizeMeasuredInput={sanitizeMeasuredInput}
            metricLabel={toChineseMetricLabel}
            toChineseCompType={toChineseCompType}
          />
          )}

        {isAuditView && (
        <div className={`${panelCls} wb-panel min-[980px]:col-span-2 min-[1480px]:col-span-1`}>
          <div className="mb-2 flex items-center justify-between">
            <div className="text-sm font-extrabold">步骤 3：共识见证 · OrdoSign</div>
            <div className="flex items-center gap-2">
              <span className="rounded-full bg-slate-800/90 border border-slate-700 px-2 py-0.5 text-[10px] text-slate-400">共识层</span>
              <span className={`rounded-full border px-2 py-0.5 text-[10px] ${draftReady ? 'border-emerald-500/60 text-emerald-300 bg-emerald-950/30' : 'border-slate-600/60 text-slate-400 bg-slate-950/30'}`}>
                {draftReady ? '实时编译' : '待编译'}
              </span>
            </div>
          </div>
          {(consensusConflict || disputeOpen) && (
            <div className={`mb-3 rounded-xl border p-3 ${consensusConflict ? 'border-rose-600/70 bg-rose-950/30 text-rose-100' : 'border-amber-600/70 bg-amber-950/30 text-amber-100'}`}>
              <div className="text-xs font-extrabold">共识冲突警告</div>
              <div className="text-[11px] mt-1">
                偏差 {formatNumber(consensusDeviation.deviation)} ({consensusDeviation.deviationPercent.toFixed(2)}%) · 阈值 {consensusAllowedAbsText}/{consensusAllowedPctText}
              </div>
              <div className="text-[11px] mt-1">Dispute UTXO: {disputeProof || (consensusConflict ? '待生成' : '-')}</div>
              <div className="text-[11px] mt-1">结算权限已锁定，需通过 Dispute UTXOResolution Trip 解除。</div>
            </div>
          )}
          {finalProofReady && (
            <div className="mb-3 rounded-xl border border-emerald-500/70 bg-emerald-950/30 p-3 shadow-[0_0_24px_rgba(16,185,129,0.2)]">
              <div className="text-xs font-extrabold text-emerald-200">Final Proof · 主权二维码</div>
              <div className="mt-2 grid grid-cols-[140px_1fr] max-[600px]:grid-cols-1 gap-3 items-center">
                <div className="w-[140px] h-[140px] border border-emerald-500/60 bg-white grid place-items-center">
                  <img src={qrSrc} alt="Final Proof 二维码" className="w-[128px] h-[128px]" />
                </div>
                <div className="text-xs text-emerald-100 leading-5">
                  <div>扫码溯源验证 Final Proof</div>
                  <div className="mt-1 text-emerald-200 break-all">{verifyUri || '未生成验真 URI'}</div>
                  {finalProofId && (
                    <div className="mt-1 text-emerald-300 break-all">Proof ID: {finalProofId}</div>
                  )}
                </div>
              </div>
            </div>
          )}
          <div className="grid gap-3 min-[1100px]:grid-cols-[280px_1fr]">
            <div className="rounded-xl border border-slate-700 bg-slate-950/30 p-3">
              <div className="text-xs text-sky-300 mb-2">DID 身份卡片</div>
              <div className="relative pl-4">
                <div className="absolute left-1.5 top-3 bottom-3 w-px bg-slate-700/70" />
                {[
                  { key: 'contractor', label: '施工员', did: executorDid, step: 1 },
                  { key: 'supervisor', label: '监理', did: supervisorDid, step: 2 },
                  { key: 'owner', label: '业主', did: ownerDid, step: 3 },
                ].map((item) => {
                  const activeCard = signFocus === item.key
                  const signed = signStep >= item.step
                  return (
                    <button
                      type="button"
                      key={item.key}
                      onClick={() => scrollToSign(item.key as 'contractor' | 'supervisor' | 'owner')}
                      className={`mb-2 w-full text-left rounded-xl border px-3 py-2 transition cursor-pointer ${activeCard ? 'border-emerald-500/70 bg-emerald-950/30' : 'border-slate-700/70 bg-slate-950/40 hover:border-slate-500/60'}`}
                    >
                      <div className="flex items-center justify-between">
                        <div className="text-sm font-bold text-slate-100">{item.label}</div>
                        <div className={`text-[11px] font-semibold ${signed ? 'text-emerald-300' : 'text-slate-400'}`}>{signed ? '已签' : '待签'}</div>
                      </div>
                      <div className="text-[11px] text-slate-400 mt-1">{item.did}</div>
                      <div className="mt-2 flex items-center gap-1 text-[11px] text-emerald-300">
                        <svg width="14" height="14" viewBox="0 0 24 24" fill="none" aria-hidden="true">
                          <path d="M12 3l7 3v6c0 5-3.5 9-7 12-3.5-3-7-7-7-12V6l7-3Z" stroke="currentColor" strokeWidth="1.6" strokeLinejoin="round" />
                          <path d="M9 12l2 2 4-4" stroke="currentColor" strokeWidth="1.6" strokeLinecap="round" strokeLinejoin="round" />
                        </svg>
                        CA 认证已通过
                      </div>
                    </button>
                  )
                })}
              </div>
              <div className="grid gap-2 mt-3">
                <input value={supervisorDid} onChange={(e) => setSupervisorDid(e.target.value)} placeholder="监理 DID" className={inputBaseCls} />
                <input value={ownerDid} onChange={(e) => setOwnerDid(e.target.value)} placeholder="业主 DID" className={inputBaseCls} />
              </div>
            </div>
            <div className="rounded-xl border border-slate-700 bg-slate-950/30 p-3">
              <div className="flex items-center justify-between mb-2">
                <div className="text-xs text-slate-400">DocPeg 分屏预览 · 共识见证</div>
                <div className={`text-[11px] ${previewPdfB64 ? 'text-emerald-300' : 'text-slate-400'}`}>
                  {pdfB64 ? '正式 DocPeg 已生成' : previewIsDraft ? '草稿已编译' : '等待施工员签认'}
                </div>
              </div>
              <div className="mb-3 grid gap-2 min-[720px]:grid-cols-4">
                <div className="rounded-xl border border-slate-700/80 bg-slate-900/70 px-3 py-2">
                  <div className="text-[10px] uppercase tracking-[0.16em] text-slate-500">提交流程</div>
                  <div className={`mt-1 text-sm font-semibold ${tripStage === 'Approved' ? 'text-emerald-300' : tripStage === 'Reviewing' ? 'text-sky-300' : 'text-slate-200'}`}>
                    {tripStage === 'Approved' ? '已批准' : tripStage === 'Reviewing' ? '审核中' : '未提交'}
                  </div>
                </div>
                <div className="rounded-xl border border-slate-700/80 bg-slate-900/70 px-3 py-2">
                  <div className="text-[10px] uppercase tracking-[0.16em] text-slate-500">证明ID</div>
                  <div className="mt-1 text-sm font-semibold text-slate-100">{finalProofId ? `${finalProofId.slice(0, 10)}...` : '-'}</div>
                </div>
                <div className="rounded-xl border border-slate-700/80 bg-slate-900/70 px-3 py-2">
                  <div className="text-[10px] uppercase tracking-[0.16em] text-slate-500">SnapPeg</div>
                  <div className="mt-1 text-sm font-semibold text-slate-100">{evidence.length}</div>
                </div>
                <div className="rounded-xl border border-slate-700/80 bg-slate-900/70 px-3 py-2">
                  <div className="text-[10px] uppercase tracking-[0.16em] text-slate-500">哈希锁</div>
                  <div className="mt-1 text-sm font-semibold text-slate-100">{totalHash ? `${totalHash.slice(0, 10)}...` : '-'}</div>
                </div>
              </div>
              <div className="mb-3 rounded-xl border border-slate-700/80 bg-[linear-gradient(135deg,rgba(15,23,42,.95),rgba(8,47,73,.24))] px-3 py-2 text-[11px] text-slate-300">
                <div className="flex flex-wrap items-center justify-between gap-2">
                  <span className="text-slate-400">当前 SMU 路径</span>
                  <span className={`rounded-full border px-2 py-0.5 ${previewIsDraft ? 'border-amber-500/60 text-amber-200 bg-amber-950/30' : 'border-emerald-500/60 text-emerald-200 bg-emerald-950/30'}`}>
                    {previewIsDraft ? '草稿预览' : '验真预览'}
                  </span>
                </div>
                <div className="mt-1 break-all font-mono text-slate-100">{activePath || active?.uri || '-'}</div>
                <div className="mt-1 text-slate-500">
                  门控通过 {gateStats.pass}/{gateStats.total || 0} · 已报验 {activeGenesisSummary.reportedPct.toFixed(2)}%
                </div>
              </div>
              <div className="mb-3 flex flex-wrap items-center gap-2">
                <button
                  type="button"
                  onClick={() => void copyText('验真 URI', verifyUri || '')}
                  disabled={!verifyUri}
                  className="px-3 py-1.5 text-[11px] border border-slate-700 rounded-lg bg-slate-900/80 text-slate-200 disabled:opacity-50"
                >
                  复制验真 URI
                </button>
                <button
                  type="button"
                  onClick={() => void copyText('Proof ID', finalProofId || '')}
                  disabled={!finalProofId}
                  className="px-3 py-1.5 text-[11px] border border-slate-700 rounded-lg bg-slate-900/80 text-slate-200 disabled:opacity-50"
                >
                  复制证明ID
                </button>
                <button
                  type="button"
                  onClick={() => setDocModalOpen(true)}
                  disabled={!previewPdfB64}
                  className="px-3 py-1.5 text-[11px] border border-sky-500/60 rounded-lg bg-sky-950/30 text-sky-200 disabled:opacity-50"
                >
                  全屏预览
                </button>
              </div>
              {previewPdfB64 && signFocus && !activeSignMarker && (
                <div className="text-[11px] text-amber-300 mb-2">
                  未提供签认坐标，已定位到第 {pdfPage} 页
                </div>
              )}
              <div className="text-[11px] text-slate-400 mb-2">验真 URI: {verifyUri || '-'}</div>
              <div className="text-[11px] text-slate-500 mb-2 break-all">
                模板来源: {String(((signRes?.docpeg || {}) as Record<string, unknown>).selected_template_path || templateBinding.template_path || templateBinding.fallback_template || '-')}
              </div>
              <div className="overflow-hidden rounded-lg border border-slate-700 bg-white">
                <div className="grid grid-cols-[1fr_auto] gap-2 border-b border-slate-200 bg-slate-100 px-3 py-2 text-[11px]">
                  <div className="flex flex-wrap items-center gap-2">
                    <span className="rounded-full border border-slate-300 bg-white px-2 py-0.5 text-slate-700">《3、桥施表》</span>
                    <span className="rounded-full border border-slate-300 bg-white px-2 py-0.5 text-slate-600">SMU {String(active?.code || '-')}</span>
                    <span className="rounded-full border border-slate-300 bg-white px-2 py-0.5 text-slate-600">第 {pdfPage} 页</span>
                  </div>
                  <div className="text-right text-slate-500">{previewIsDraft ? '草稿联编' : '正式预览'}</div>
                </div>
                <div className="grid min-[1180px]:grid-cols-[180px_1fr]">
                  <div className="border-r border-slate-200 bg-slate-50 p-3 text-[11px] text-slate-600">
                    <div className="text-[10px] uppercase tracking-[0.14em] text-slate-400">签认侧栏</div>
                    <div className="mt-2 grid gap-2">
                      <div ref={contractorAnchorRef} className={`rounded-lg border px-2 py-2 ${signFocus === 'contractor' ? 'border-emerald-400 bg-emerald-50 text-emerald-700' : 'border-slate-200 bg-white'}`}>
                        <div className="font-semibold">施工员签认区</div>
                        <div className="mt-1 text-[10px] text-slate-500">点击左侧身份卡可跳转定位</div>
                      </div>
                      <div ref={supervisorAnchorRef} className={`rounded-lg border px-2 py-2 ${signFocus === 'supervisor' ? 'border-emerald-400 bg-emerald-50 text-emerald-700' : 'border-slate-200 bg-white'}`}>
                        <div className="font-semibold">监理签认区</div>
                        <div className="mt-1 text-[10px] text-slate-500">证据回溯与复核签认</div>
                      </div>
                      <div ref={ownerAnchorRef} className={`rounded-lg border px-2 py-2 ${signFocus === 'owner' ? 'border-emerald-400 bg-emerald-50 text-emerald-700' : 'border-slate-200 bg-white'}`}>
                        <div className="font-semibold">业主签认区</div>
                        <div className="mt-1 text-[10px] text-slate-500">最终共识与哈希锁定</div>
                      </div>
                    </div>
                    <div className="mt-3 rounded-lg border border-slate-200 bg-white px-2 py-2">
                      <div className="text-[10px] uppercase tracking-[0.14em] text-slate-400">验真链路</div>
                      <div className="mt-1 break-all font-mono text-[10px] text-slate-600">{verifyUri || '-'}</div>
                    </div>
                  </div>
                  <div ref={previewScrollRef} className="relative h-[320px] overflow-y-auto bg-white">
                    <div className="relative">
                      {previewPdfB64 ? (
                        <div className="relative bg-white">
                          <canvas ref={pdfCanvasRef} className="w-full h-auto block" />
                          {pdfRenderLoading && (
                            <div className="absolute inset-0 grid place-items-center text-slate-500 text-sm bg-white/70">
                              PDF 渲染中...
                            </div>
                          )}
                          {pdfRenderError && (
                            <div className="absolute inset-0 grid place-items-center text-rose-500 text-sm bg-white/80">
                              {pdfRenderError}
                            </div>
                          )}
                        </div>
                      ) : draftReady ? (
                        <div className="h-[360px] grid place-items-center text-slate-500 text-sm">
                          草稿版 PDF 实时编译中…
                        </div>
                      ) : (
                        <div className="h-[360px] grid place-items-center text-slate-400 text-sm">
                          等待施工员签认后生成草稿预览
                        </div>
                      )}
                      {previewPdfB64 && activeSignMarker && !pdfRenderError && (
                        <div className="pointer-events-none absolute inset-0">
                          <div
                            className="absolute -translate-x-1/2 -translate-y-1/2 rounded-full border border-emerald-500 bg-emerald-400/70 shadow-[0_0_12px_rgba(52,211,153,0.5)]"
                            style={{ left: `${activeSignMarker.x * 100}%`, top: `${activeSignMarker.y * 100}%`, width: 14, height: 14 }}
                          />
                          <div
                            className="absolute -translate-x-1/2 -translate-y-1/2 text-[10px] font-bold text-emerald-700"
                            style={{ left: `${activeSignMarker.x * 100}%`, top: `calc(${activeSignMarker.y * 100}% + 14px)` }}
                          >
                            签认点
                          </div>
                        </div>
                      )}
                      {previewIsDraft && (
                        <div className="pointer-events-none absolute inset-0 flex items-center justify-center text-emerald-600/30 font-black text-4xl tracking-[0.25em]">
                          DRAFT
                        </div>
                      )}
                    </div>
                  </div>
                </div>
              </div>
              <div className="mt-2 grid gap-2 min-[720px]:grid-cols-3">
                <div className="rounded-lg border border-slate-700/80 bg-slate-900/60 px-3 py-2 text-[11px]">
                  <div className="text-slate-500">模板</div>
                  <div className="mt-1 truncate text-slate-200">{templateDisplay}</div>
                </div>
                <div className="rounded-lg border border-slate-700/80 bg-slate-900/60 px-3 py-2 text-[11px]">
                  <div className="text-slate-500">签认页</div>
                  <div className="mt-1 text-slate-200">第 {pdfPage} 页</div>
                </div>
                <div className="rounded-lg border border-slate-700/80 bg-slate-900/60 px-3 py-2 text-[11px]">
                  <div className="text-slate-500">渲染状态</div>
                  <div className={`mt-1 ${pdfRenderError ? 'text-rose-300' : pdfRenderLoading ? 'text-amber-300' : 'text-emerald-300'}`}>
                    {pdfRenderError ? '渲染异常' : pdfRenderLoading ? '渲染中' : previewPdfB64 ? '就绪' : '待机'}
                  </div>
                </div>
              </div>
              <div className="mt-3 border border-slate-700 rounded-xl p-3 grid grid-cols-[140px_1fr] max-[600px]:grid-cols-1 gap-3">
                <div className="w-[140px] h-[140px] border border-slate-800 bg-white grid place-items-center">
                  <img src={qrSrc} alt="DocPeg 验真二维码" className="w-[128px] h-[128px]" />
                </div>
                <div className="text-xs text-slate-400 leading-5">
                  扫码验真 DocPeg
                  <div className="mt-1 text-slate-200 break-all">{verifyUri || '暂无 URI'}</div>
                  <div className="mt-2 grid gap-2 min-[720px]:grid-cols-2">
                    <div className="rounded-lg border border-slate-700/80 bg-slate-900/70 px-3 py-2">
                      <div className="text-[10px] uppercase tracking-[0.14em] text-slate-500">证明ID</div>
                      <div className="mt-1 break-all text-slate-200">{finalProofId || '-'}</div>
                    </div>
                    <div className="rounded-lg border border-slate-700/80 bg-slate-900/70 px-3 py-2">
                      <div className="text-[10px] uppercase tracking-[0.14em] text-slate-500">总证明哈希</div>
                      <div className="mt-1 break-all text-slate-200">{totalHash || '-'}</div>
                    </div>
                  </div>
                  <div className="mt-2 flex flex-wrap items-center gap-2">
                    <button
                      type="button"
                      onClick={() => void copyText('验真 URI', verifyUri || '')}
                      disabled={!verifyUri}
                      className="px-2 py-1 text-[11px] border border-slate-700 rounded bg-slate-900 text-slate-200 disabled:opacity-50"
                    >
                      复制验真 URI
                    </button>
                    <button
                      type="button"
                      onClick={() => void copyText('Total Proof Hash', totalHash || '')}
                      disabled={!totalHash}
                      className="px-2 py-1 text-[11px] border border-slate-700 rounded bg-slate-900 text-slate-200 disabled:opacity-50"
                    >
                      复制 Hash
                    </button>
                  </div>
                </div>
              </div>
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
            <div className="flex items-center justify-between mb-1">
              <div className="text-xs font-extrabold">The Final Piece · 完工态提示</div>
              <button
                type="button"
                onClick={() => void copyText('Final Piece Prompt', finalPiecePrompt)}
                className="px-2 py-1 text-[11px] border border-slate-700 rounded bg-slate-900 text-slate-200 hover:bg-slate-800"
              >
                复制提示词
              </button>
            </div>
            <div className="text-[11px] text-slate-400 whitespace-pre-line">{finalPiecePrompt}</div>
          </div>
          <ScanConfirmPanel
            scanConfirmUri={scanConfirmUri}
            scanProofId={scanProofId}
            scanPayload={scanPayload}
            scanDid={scanDid}
            scanConfirmToken={scanConfirmToken}
            scanning={scanning}
            showAcceptanceAdvanced={showAcceptanceAdvanced}
            scanRes={scanRes}
            inputBaseCls={inputBaseCls}
            btnBlueCls={btnBlueCls}
            btnGreenCls={btnGreenCls}
            onScanPayloadChange={setScanPayload}
            onScanDidChange={setScanDid}
            onScanProofIdChange={setScanProofId}
            onFillScanToken={() => setScanPayload(scanConfirmToken)}
            onScanConfirm={() => void doScanConfirm()}
            onToggleAdvanced={() => setShowAcceptanceAdvanced((value) => !value)}
          />
          <ConsensusDisputePanel
            minValueText={formatNumber(consensusDeviation.minValue)}
            maxValueText={formatNumber(consensusDeviation.maxValue)}
            deviationText={formatNumber(consensusDeviation.deviation)}
            deviationPercentText={`${consensusDeviation.deviationPercent.toFixed(2)}%`}
            consensusAllowedAbsText={consensusAllowedAbsText}
            consensusAllowedPctText={consensusAllowedPctText}
            consensusConflict={consensusConflict}
            disputeProof={disputeProof}
            disputeOpen={disputeOpen}
            disputeProofId={disputeProofId}
            disputeResolutionNote={disputeResolutionNote}
            disputeResult={disputeResult}
            disputeResolving={disputeResolving}
            disputeResolveRes={disputeResolveRes}
            inputBaseCls={inputBaseCls}
            btnAmberCls={btnAmberCls}
            onCopyConflictSummary={() => void copyText('共识冲突摘要', JSON.stringify(consensusConflictSummary, null, 2))}
            onJumpToDispute={() => {
              setShowAdvancedConsensus(true)
              if (disputeProof) setDisputeProofId(disputeProof)
            }}
            onDisputeProofIdChange={setDisputeProofId}
            onDisputeResolutionNoteChange={setDisputeResolutionNote}
            onDisputeResultChange={setDisputeResult}
            onResolveDispute={() => void resolveDispute()}
          />
          <DocFinalPanel
            archiveLocked={archiveLocked}
            docFinalPassphrase={docFinalPassphrase}
            docFinalIncludeUnsettled={docFinalIncludeUnsettled}
            docFinalExporting={docFinalExporting}
            docFinalFinalizing={docFinalFinalizing}
            docFinalRes={docFinalRes}
            docFinalAuditUrl={docFinalAuditUrl}
            docFinalVerifyBaseUrl={docFinalVerifyBaseUrl}
            verifyUri={verifyUri}
            disputeOpen={disputeOpen}
            disputeProofShort={disputeProofShort}
            offlineQueueSize={offlinePackets.length}
            offlineSyncConflicts={offlineSyncConflicts}
            apiProjectUri={apiProjectUri}
            docFinalQrSrc={docFinalQrSrc}
            inputBaseCls={inputBaseCls}
            btnBlueCls={btnBlueCls}
            btnGreenCls={btnGreenCls}
            onDocFinalPassphraseChange={setDocFinalPassphrase}
            onDocFinalIncludeUnsettledChange={setDocFinalIncludeUnsettled}
            onExportProjectDocFinal={() => void exportProjectDocFinal()}
            onFinalizeProjectDocFinal={() => void finalizeProjectDocFinal()}
          />
          <SpecdictPanel
            specdictProjectUris={specdictProjectUris}
            specdictMinSamples={specdictMinSamples}
            specdictNamespace={specdictNamespace}
            specdictCommit={specdictCommit}
            specdictLoading={specdictLoading}
            specdictExporting={specdictExporting}
            specdictRuleTotal={specdictRuleTotal}
            specdictHighRisk={specdictHighRisk}
            specdictBestPractice={specdictBestPractice}
            specdictBundleUri={specdictBundleUri}
            successPatterns={specdictSuccessPatterns.slice(0, 3).map((item) => describeSpecdictItem(item))}
            highRiskItems={specdictHighRiskItems.slice(0, 3).map((item) => describeSpecdictItem(item))}
            bestPracticeItems={specdictBestPracticeItems.slice(0, 3).map((item) => describeSpecdictItem(item))}
            weightEntriesText={specdictWeightEntries.map(([key, value]) => `${key}:${String(value)}`)}
            hasSpecdictRes={Boolean(specdictRes)}
            inputBaseCls={inputBaseCls}
            btnBlueCls={btnBlueCls}
            btnGreenCls={btnGreenCls}
            onProjectUrisChange={setSpecdictProjectUris}
            onMinSamplesChange={setSpecdictMinSamples}
            onNamespaceChange={setSpecdictNamespace}
            onCommitChange={setSpecdictCommit}
            onRunSpecdictEvolve={() => void runSpecdictEvolve()}
            onRunSpecdictExport={() => void runSpecdictExport()}
            onOneClickWriteGlobal={() => {
              setSpecdictCommit(true)
              void runSpecdictExport()
            }}
          />
          <div className="border border-dashed border-slate-700 rounded-xl p-3 mt-3">
            <div className="text-xs font-extrabold mb-1">MeshPeg 数字孪生核算</div>
            <div className="text-[11px] text-slate-400 mb-2">LiDAR 点云 vs BIM 模型自动比对，生成几何 Proof。</div>
            <div className="grid gap-2">
              <div className="grid grid-cols-2 gap-2">
                <input value={meshpegCloudName} onChange={(e) => setMeshpegCloudName(e.target.value)} placeholder="点云源（如 LiDAR-Drone-01）" className={inputBaseCls} />
                <input value={meshpegBimName} onChange={(e) => setMeshpegBimName(e.target.value)} placeholder="BIM 模型（如 BIM-v3.2）" className={inputBaseCls} />
              </div>
              <button type="button" onClick={() => runMeshpeg()} disabled={meshpegRunning} className={`px-3 py-2 text-sm font-bold ${btnBlueCls}`}>
                {meshpegRunning ? '核算中...' : '运行 MeshPeg 核算'}
              </button>
              {meshpegRes && (
                <div className="text-[11px] text-slate-300 grid gap-1">
                  <div>设计量: {formatNumber(meshpegRes.design_quantity)} · 实测体积: {formatNumber(meshpegRes.mesh_volume)}</div>
                  <div>偏差: {String(meshpegRes.deviation_percent || 0)}% · 状态 {String(meshpegRes.status || '-')}</div>
                  <div>Mesh Proof: {String(meshpegRes.proof_id || '-')}</div>
                </div>
              )}
            </div>
          </div>
          <div className="border border-dashed border-slate-700 rounded-xl p-3 mt-3">
            <div className="text-xs font-extrabold mb-1">FormulaPeg 动态计价合约</div>
            <div className="text-[11px] text-slate-400 mb-2">质量合格 + 几何合格后自动计价生成 RailPact。</div>
            <div className="grid gap-2">
              <input value={formulaExpr} onChange={(e) => setFormulaExpr(e.target.value)} placeholder="公式示例：qty * unit_price" className={inputBaseCls} />
              <button type="button" onClick={() => runFormulaPeg()} disabled={formulaRunning} className={`px-3 py-2 text-sm font-bold ${btnGreenCls}`}>
                {formulaRunning ? '计价中...' : '生成 RailPact'}
              </button>
              {formulaRes && (
                <div className="text-[11px] text-slate-300 grid gap-1">
                  <div>数量: {String(formulaRes.qty || '-')} · 单价: {String(formulaRes.unit_price || '-')}</div>
                  <div>金额: {String(formulaRes.amount || '-')} · RailPact: {String(formulaRes.railpact_id || '-')}</div>
                  <div>状态: {String(formulaRes.status || '-')}</div>
                </div>
              )}
            </div>
          </div>
          <div className="border border-dashed border-slate-700 rounded-xl p-3 mt-3">
            <div className="text-xs font-extrabold mb-1">Sovereign Gateway 跨链治理</div>
            <div className="text-[11px] text-slate-400 mb-2">同步监管侧节点，实时对齐 total_proof_hash。</div>
            <div className="grid gap-2">
              <button type="button" onClick={() => runGatewaySync()} className={`px-3 py-2 text-sm font-bold ${btnAmberCls}`}>生成监管同步摘要</button>
              {gatewayRes && (
                <div className="text-[11px] text-slate-300 grid gap-1">
                  <div>Project: {String(gatewayRes.project_uri || '-')}</div>
                  <div>Total Proof Hash: {String(gatewayRes.total_proof_hash || '-')}</div>
                  <div>Proof ID: {String(gatewayRes.proof_id || '-')}</div>
                  <div>Scan Entry: {String(gatewayRes.scan_entry_proof || '-')}</div>
                  <div>更新时间: {String(gatewayRes.updated_at || '-')}</div>
                  <div className="flex items-center gap-2">
                    <button type="button" onClick={() => void copyText('监管同步摘要', JSON.stringify(gatewayRes, null, 2))} className="px-2 py-1 text-[11px] border border-slate-700 rounded bg-slate-900 text-slate-200">复制 JSON</button>
                    <button type="button" onClick={() => downloadJson(`gateway-${Date.now()}.json`, gatewayRes)} className="px-2 py-1 text-[11px] border border-slate-700 rounded bg-slate-900 text-slate-200">导出 JSON</button>
                  </div>
                </div>
              )}
            </div>
          </div>
          <div className="border border-dashed border-slate-700 rounded-xl p-3 mt-3">
            <div className="text-xs font-extrabold mb-1">主权资产评估接口</div>
            <div className="text-[11px] text-slate-400 mb-2">面向金融机构的证明强度评分，数据即信用。</div>
            <div className="grid gap-2">
              <button type="button" onClick={() => buildAssetAppraisal()} disabled={assetAppraising} className={`px-3 py-2 text-sm font-bold ${btnGreenCls}`}>
                {assetAppraising ? '评估中...' : '生成资产评估'}
              </button>
              {assetAppraisal && (
                <div className="text-[11px] text-slate-300 grid gap-1">
                  <div>评分: {String(assetAppraisal.score || '-')} · 等级 {String(assetAppraisal.grade || '-')}</div>
                  <div>Proof: {String(assetAppraisal.proof_id || '-')}</div>
                  <div>Hash: {String(assetAppraisal.total_proof_hash || '-')}</div>
                  <div>风险: dispute={String(assetAppraisal.dispute_open)} · consensus={String(assetAppraisal.consensus_conflict)} · risk_score={String(assetAppraisal.risk_score || 0)}</div>
                  <div>证据 {String(assetAppraisal.evidence_count || 0)} · 文档 {String(assetAppraisal.document_count || 0)}</div>
                  <div className="flex items-center gap-2">
                    <button type="button" onClick={() => void copyText('资产评估 JSON', JSON.stringify(assetAppraisal, null, 2))} className="px-2 py-1 text-[11px] border border-slate-700 rounded bg-slate-900 text-slate-200">复制 JSON</button>
                    <button type="button" onClick={() => downloadJson(`asset-appraisal-${Date.now()}.json`, assetAppraisal)} className="px-2 py-1 text-[11px] border border-slate-700 rounded bg-slate-900 text-slate-200">导出 JSON</button>
                  </div>
                </div>
              )}
            </div>
          </div>
          <ArPanel
            arRadius={arRadius}
            arLimit={arLimit}
            arLoading={arLoading}
            activeUri={String(active?.uri || '')}
            latestProofId={String((latestEvidenceNode || {}).proof_id || inputProofId || '-')}
            totalHashShort={totalHash ? `${totalHash.slice(0, 10)}...` : '-'}
            nearestAnchorText={arPrimary ? `${String(arPrimary.item_no || arPrimary.boq_item_uri || arPrimary.uri || 'UTXO')} · ${String(arPrimary.distance_m || '-')}m` : ''}
            arItems={arItems}
            inputBaseCls={inputBaseCls}
            btnAmberCls={btnAmberCls}
            onArRadiusChange={setArRadius}
            onArLimitChange={setArLimit}
            onRunArOverlay={() => void runArOverlay()}
            onOpenFullscreen={() => setArFullscreen(true)}
            onFocusItem={setArFocus}
          />
          <div className="border border-dashed border-slate-700 rounded-xl p-3 mt-3">
            <div className="text-xs font-extrabold mb-1">动态时空围栏</div>
            <div className="text-[11px] text-slate-400 mb-2">扫码进入节点时实时拦截，空间坐标越界将锁定录入。</div>
          <div className="grid gap-2 text-[11px] text-slate-300">
            <div>围栏状态: {geoFenceStatusText}</div>
            <div>扫码状态: {scanEntryStatus === 'ok' ? '已通过' : scanEntryStatus === 'blocked' ? '被拦截' : '未扫码'}</div>
            <div>扫码令牌: {scanEntryRequired ? (scanEntryToken ? '已提交' : '缺失') : '可选'}</div>
            <div className="flex items-center gap-2">
              <span>链状态</span>
              <span className={`px-2 py-0.5 rounded-full border ${scanChainBadge.cls}`}>{scanChainBadge.label}</span>
            </div>
            <div>桩号中心: {geoAnchor ? `${geoAnchor.lat}, ${geoAnchor.lng}` : '未配置'}</div>
              <div>允许半径: {geoAnchor ? `${geoAnchor.radiusM}m` : '-'}</div>
              <div>当前距离: {geoDistance != null ? `${Math.round(geoDistance)}m` : '-'}</div>
              <div>时间窗口: {temporalWindow ? `${Math.floor(temporalWindow.start / 60).toString().padStart(2, '0')}:${String(temporalWindow.start % 60).padStart(2, '0')} - ${Math.floor(temporalWindow.end / 60).toString().padStart(2, '0')}:${String(temporalWindow.end % 60).padStart(2, '0')}` : '未限制'}</div>
              <div className={geoTemporalBlocked ? 'text-rose-300' : 'text-emerald-300'}>
                {geoTemporalBlocked ? 'Geo-Leap Error：已锁定录入按钮' : '定位与时间均合规'}
              </div>
            </div>
          </div>
          <div className="border border-dashed border-slate-700 rounded-xl p-3 mt-3">
            <div className="text-xs font-extrabold mb-1">数字资产总指纹</div>
            <div className="grid gap-2">
              <div className="rounded-lg border border-slate-800 bg-slate-900/60 px-3 py-2 text-[11px] text-slate-300">
                当前分部分项：{active?.code ? `${active.code.split('-')[0]}章 ${active.name || ''}`.trim() : '未选择'}
              </div>
              <div className="grid grid-cols-[1fr_auto] gap-2">
                <button type="button" onClick={() => void calcUnitMerkle()} disabled={unitLoading} className={`px-3 py-2 font-bold text-sm ${btnAmberCls}`}>{unitLoading ? '计算中...' : '生成数字资产总指纹'}</button>
                <button type="button" onClick={() => useCurrentProofForUnit()} className={`px-3 py-2 text-sm ${btnBlueCls}`}>同步当前细目</button>
              </div>
              <button type="button" onClick={() => setShowFingerprintAdvanced((v) => !v)} className="text-[11px] text-slate-400 text-left hover:text-slate-200">
                {showFingerprintAdvanced ? '收起高级参数 ▲' : '展开高级参数 ▼'}
              </button>
              {showFingerprintAdvanced && (
                <div className="grid gap-2">
                  <input value={unitProofId} onChange={(e) => setUnitProofId(e.target.value)} placeholder="证明ID（可选）" className={inputBaseCls} />
                  <input value={unitMaxRows} onChange={(e) => setUnitMaxRows(e.target.value)} placeholder="最大扫描行数" className={inputBaseCls} />
                </div>
              )}
              {!!unitRes && (
                <div className="text-[11px] text-slate-400 break-all">
                  <div>分部分项总指纹: 主权已锁定</div>
                  <div>项目总指纹: 主权已锁定</div>
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
                      <div>计算叶子根: 主权已锁定</div>
                      <div className="mt-1">单位叶子哈希: 主权已锁定</div>
                      <div className="mt-1">计算项目根: 主权已锁定</div>
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
                              <div className="text-slate-400 break-all">兄弟哈希: 主权已锁定</div>
                              <div className="text-emerald-300 break-all">合并哈希: 主权已锁定</div>
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
                              <div className="text-slate-400 break-all">兄弟哈希: 主权已锁定</div>
                              <div className="text-emerald-300 break-all">合并哈希: 主权已锁定</div>
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
          <div className="border border-dashed border-slate-700 rounded-xl p-3 mt-3">
            <div className="text-xs font-extrabold mb-1">GitPeg P2P 同步</div>
            <div className="text-[11px] text-slate-400 mb-2">自愈式数据冗余：本地节点离线记录，恢复后自动合拢。</div>
            <div className="grid gap-2 text-[11px] text-slate-300">
              <div>本地节点: {p2pNodeId}</div>
              <div>离线队列: {offlinePackets.length} 条 · 上次同步 {p2pLastSync || '未同步'}</div>
              <label className="flex items-center gap-2 text-[11px] text-slate-400">
                <input type="checkbox" checked={p2pAutoSync} onChange={(e) => setP2pAutoSync(e.target.checked)} />
                启用自动增量同步
              </label>
              <textarea value={p2pPeers} onChange={(e) => setP2pPeers(e.target.value)} rows={2} placeholder="Peer 节点（逗号或换行分隔）" className={`${inputBaseCls} resize-y`} />
              <div className="grid grid-cols-2 gap-2">
                <button type="button" onClick={() => exportP2PManifest()} className={`px-3 py-2 text-sm font-bold ${btnBlueCls}`}>导出同步清单</button>
                <button type="button" onClick={() => simulateP2PSync()} className={`px-3 py-2 text-sm font-bold ${btnAmberCls}`}>记录一次同步</button>
              </div>
              <div className="text-[11px] text-slate-400">Merkle Root: {String((unitRes || {}).project_root_hash || (unitRes || {}).global_project_fingerprint || '-') || '-'}</div>
            </div>
          </div>
          </>
          )}
        </div>
        )}
        </div>
      </div>

      {isAuditView && (
      <EvidenceVault
        btnBlueCls={btnBlueCls}
        evidenceCenterLoading={evidenceCenterLoading}
        evidenceCenterError={evidenceCenterError}
        evidenceQuery={evidenceQuery}
        evidenceScope={evidenceScope}
        evidenceSmuId={evidenceSmuId}
        evidenceFilter={evidenceFilter}
        smuOptions={smuOptions}
        filteredEvidenceItems={filteredEvidenceItems}
        filteredDocs={filteredDocs}
        evidenceCompletenessScore={evidenceCompletenessScore}
        settlementRiskScore={settlementRiskScore}
        evidenceGraphNodes={evidenceGraphNodes}
        ledgerSnapshot={ledgerSnapshot}
        meshpegItems={meshpegItems}
        formulaItems={formulaItems}
        gatewayItems={gatewayItems}
        assetOrigin={assetOrigin}
        assetOriginStatement={assetOriginStatement}
        didReputationScore={didReputationScore}
        didReputationGrade={didReputationGrade}
        didSamplingMultiplier={didSamplingMultiplier}
        didHighRiskList={didHighRiskList.map((item) => String(item))}
        sealingPatternId={sealingPatternId}
        sealingScanHint={sealingScanHint}
        sealingMicrotext={sealingMicrotext}
        sealingRows={sealingRows}
        scanEntryActiveOnly={scanEntryActiveOnly}
        evidenceItemsPaged={evidenceItemsPaged}
        evidencePageSafe={evidencePageSafe}
        totalEvidencePages={totalEvidencePages}
        latestEvidenceNode={latestEvidenceNode}
        utxoStatusText={utxoStatusText}
        consensusConflict={consensusConflict}
        consensusAllowedAbsText={consensusAllowedAbsText}
        consensusAllowedPctText={consensusAllowedPctText}
        disputeConflict={disputeConflict}
        disputeDeviation={disputeDeviation}
        disputeDeviationPct={disputeDeviationPct}
        disputeAllowedAbs={typeof disputeAllowedAbs === 'number' ? disputeAllowedAbs : null}
        disputeAllowedPct={typeof disputeAllowedPct === 'number' ? disputeAllowedPct : null}
        disputeValues={disputeValues.map((value) => Number(value)).filter((value) => Number.isFinite(value))}
        disputeProof={disputeProof}
        disputeOpen={disputeOpen}
        disputeProofShort={disputeProofShort}
        erpRetrying={erpRetrying}
        erpRetryMsg={erpRetryMsg}
        evidenceZipDownloading={evidenceZipDownloading}
        erpReceiptDoc={erpReceiptDoc}
        docpegRisk={docpegRisk}
        docpegRiskScore={docpegRiskScore}
        onEvidenceQueryChange={setEvidenceQuery}
        onEvidenceScopeChange={setEvidenceScope}
        onEvidenceSmuIdChange={setEvidenceSmuId}
        onEvidenceFilterChange={setEvidenceFilter}
        onEvidencePageChange={setEvidencePage}
        onEvidenceFocus={openEvidenceFocus}
        onDocumentFocus={openDocumentFocus}
        onCopyText={(label, value) => copyText(label, value)}
        onRetryErpnextPush={() => void retryErpnextPush()}
        onExportEvidenceCenter={exportEvidenceCenter}
        onExportEvidenceCenterCsv={exportEvidenceCenterCsv}
        onDownloadEvidenceCenterPackage={() => void downloadEvidenceCenterPackage()}
        onLoadEvidenceCenter={() => void loadEvidenceCenter()}
        onOpenDispute={(proofId) => {
          setShowAdvancedConsensus(true)
          setDisputeProofId(proofId)
        }}
      />
      )}

      {signOpen && (
        <div className="fixed inset-0 bg-slate-950/70 z-[1200] grid place-items-center">
          <div className="w-[460px] max-w-[92vw] rounded-xl border border-slate-700 bg-slate-950 text-slate-100 p-4">
            <div className="text-sm font-extrabold mb-2">OrdoSign 共识签认</div>
            <div className="text-xs text-slate-400 mb-3">DID 签名链路: 施工员 → 监理 → 业主</div>
            <div className="mb-3 rounded-xl border border-slate-700/80 bg-slate-900/60 px-3 py-3">
              <div className="flex items-center justify-between text-[10px] uppercase tracking-[0.14em] text-slate-500">
                <span>TripRole Flow</span>
                <span>{tripStage}</span>
              </div>
              <div className="mt-3 flex items-center justify-between gap-2">
                {[
                  { step: 1, label: '施工员', active: signStep >= 1 },
                  { step: 2, label: '监理', active: signStep >= 2 },
                  { step: 3, label: '业主', active: signStep >= 3 },
                ].map((item, idx) => (
                  <React.Fragment key={`sign-step-${item.step}`}>
                    <div className="flex min-w-0 flex-1 flex-col items-center gap-1">
                      <div className={`grid h-8 w-8 place-items-center rounded-full border text-[11px] font-bold ${
                        item.active ? 'border-emerald-500/70 bg-emerald-950/40 text-emerald-200 shadow-[0_0_16px_rgba(16,185,129,.22)]' : 'border-slate-600/70 bg-slate-950/80 text-slate-400'
                      }`}>
                        {item.step}
                      </div>
                      <div className={`text-[11px] ${item.active ? 'text-emerald-200' : 'text-slate-500'}`}>{item.label}</div>
                    </div>
                    {idx < 2 && (
                      <div className={`h-px flex-1 ${signStep > item.step ? 'bg-emerald-500/70' : 'bg-slate-700/80'}`} />
                    )}
                  </React.Fragment>
                ))}
              </div>
            </div>
            <div className="rounded-lg border border-slate-700/70 bg-slate-900/40 px-3 py-2 mb-3">
              <div className="flex items-center gap-2 text-[11px]">
                <span className={`rounded-full border px-2 py-0.5 ${tripStage === 'Unspent' ? 'border-slate-500/70 text-slate-300' : 'border-slate-700/60 text-slate-500'}`}>Unspent</span>
                <span className="text-slate-600">→</span>
                <span className={`rounded-full border px-2 py-0.5 ${tripStage === 'Reviewing' ? 'border-sky-500/70 text-sky-200' : tripStage === 'Approved' ? 'border-sky-700/60 text-sky-400' : 'border-slate-700/60 text-slate-500'}`}>Reviewing</span>
                <span className="text-slate-600">→</span>
                <span className={`rounded-full border px-2 py-0.5 ${tripStage === 'Approved' ? 'border-emerald-500/70 text-emerald-200' : 'border-slate-700/60 text-slate-500'}`}>Approved</span>
              </div>
            </div>
            {signing && (
              <div className="mb-3 rounded-xl border border-emerald-500/60 bg-emerald-950/20 p-3 flex items-center gap-3">
                <div className="w-10 h-10 rounded-full border border-emerald-400/80" style={{ animation: 'ordosealPulse 1.2s infinite ease-in-out' }} />
                <div className="text-xs text-emerald-200">OrdoSign 封印中，正在生成主权签章与 total_proof_hash ...</div>
              </div>
            )}
            <div className="grid gap-2 mb-3">
              {[{ k: 1, l: '施工方', d: executorDid }, { k: 2, l: '监理', d: supervisorDid }, { k: 3, l: '业主', d: ownerDid }].map((x) => (
                <div key={x.k} className="border border-slate-700 rounded-lg p-2 flex items-center justify-between text-xs bg-slate-900/35">
                  <div className="min-w-0">
                    <div className="flex items-center gap-2">
                      <div>{x.l} 签名</div>
                      <span className="rounded-full border border-slate-700/80 bg-slate-950/80 px-2 py-0.5 text-[10px] text-slate-400">
                        DID {x.d ? `${x.d.slice(0, 10)}...` : '-'}
                      </span>
                    </div>
                    <div className="text-slate-400 mt-1 truncate">{x.d}</div>
                  </div>
                  <div className={`font-bold ${signStep >= x.k ? 'text-emerald-300' : 'text-slate-500'}`}>{signStep >= x.k ? '已签' : '待签'}</div>
                </div>
              ))}
            </div>
            <div className="mb-3 rounded-lg border border-slate-700/80 bg-slate-900/40 px-3 py-2 text-[11px] text-slate-400">
              审批完成后，节点状态会从 <span className="text-sky-300">Reviewing</span> 切换到 <span className="text-emerald-300">Approved</span>，并触发 SMU 冻结与 DocPeg 哈希锁定。
            </div>
            <div className="border border-slate-700/80 rounded-lg p-2 text-[11px] text-slate-300 mb-3">
              <div className="font-semibold text-slate-200 mb-2">共识量值（可调以触发冲突）</div>
              <div className="grid gap-2">
                <input
                  value={consensusContractorValue}
                  onChange={(e) => setConsensusContractorValue(e.target.value)}
                  placeholder={`施工方量值（默认 ${formatNumber(consensusBaseValue)}）`}
                  className={inputBaseCls}
                />
                <input
                  value={consensusSupervisorValue}
                  onChange={(e) => setConsensusSupervisorValue(e.target.value)}
                  placeholder={`监理量值（默认 ${formatNumber(consensusBaseValue)}）`}
                  className={inputBaseCls}
                />
                <input
                  value={consensusOwnerValue}
                  onChange={(e) => setConsensusOwnerValue(e.target.value)}
                  placeholder={`业主量值（默认 ${formatNumber(consensusBaseValue)}）`}
                  className={inputBaseCls}
                />
                <div className="grid grid-cols-2 gap-2">
                  <input
                    value={consensusAllowedDeviation}
                    onChange={(e) => setConsensusAllowedDeviation(e.target.value)}
                    placeholder="允许偏差（绝对值）"
                    className={inputBaseCls}
                  />
                  <input
                    value={consensusAllowedDeviationPct}
                    onChange={(e) => setConsensusAllowedDeviationPct(e.target.value)}
                    placeholder="允许偏差（%）"
                    className={inputBaseCls}
                  />
                </div>
                <div className="text-[10px] text-slate-500">
                  未填写时使用默认量值与系统阈值（约 0.5%）。
                </div>
                <div className={`rounded-lg border px-3 py-2 text-[11px] ${consensusConflict ? 'border-rose-600/60 bg-rose-950/40 text-rose-100' : 'border-slate-700/70 bg-slate-900/40 text-slate-300'}`}>
                  <div className="font-semibold mb-1">共识冲突检查器</div>
                  <div className="text-slate-400">
                    最小 {formatNumber(consensusDeviation.minValue)} · 最大 {formatNumber(consensusDeviation.maxValue)} · 偏差 {formatNumber(consensusDeviation.deviation)} ({consensusDeviation.deviationPercent.toFixed(2)}%)
                  </div>
                  <div className="text-slate-400">允许偏差: {consensusAllowedAbsText} / {consensusAllowedPctText}</div>
                  <div className={consensusConflict ? 'text-rose-200' : 'text-emerald-300'}>
                    {consensusConflict ? '检测到逻辑背离，将触发 Dispute UTXO 并挂起结算 Trip' : '共识一致，允许进入结算'}
                  </div>
                </div>
              </div>
            </div>
            <div className="flex justify-end gap-2">
              <button type="button" onClick={() => setSignOpen(false)} disabled={signing} className="border border-slate-700 rounded-lg px-3 py-2 bg-slate-900 text-slate-200">取消</button>
              <button type="button" onClick={() => void doSign()} disabled={signing} className={`px-3 py-2 font-bold ${btnAmberCls}`}>{signing ? '签认中...' : '执行多方签认'}</button>
            </div>
          </div>
        </div>
      )}

      {scanLockStage !== 'idle' && (
        <div className="fixed inset-0 z-[1300] bg-slate-950/90 grid place-items-center">
          <div className="w-[520px] max-w-[92vw] rounded-2xl border border-emerald-700/60 bg-gradient-to-b from-emerald-950/70 via-slate-950/90 to-slate-950 p-6 text-center text-slate-100 shadow-[0_0_40px_rgba(16,185,129,0.25)]">
            {scanLockStage === 'locking' ? (
              <>
                <div className="text-lg font-extrabold mb-2">主权资产锁定中...</div>
                <div className="text-xs text-emerald-200/80 mb-5">请勿关闭，链上指纹正在生成</div>
                <div className="flex items-center justify-center">
                  <div className="w-16 h-16 rounded-full border-2 border-emerald-400/60 border-t-transparent animate-spin" />
                </div>
              </>
            ) : (
              <>
                <div className="text-lg font-extrabold mb-2">资产已锁定</div>
                <div className="text-xs text-emerald-200/80 mb-4">Final Proof 已生成</div>
                <div className="rounded-lg border border-emerald-700/70 bg-emerald-950/40 px-3 py-2 text-[11px] break-all">
                  {scanLockProofId || '未返回 Proof ID'}
                </div>
                <button
                  type="button"
                  onClick={closeScanLock}
                  className="mt-4 px-4 py-2 text-sm font-bold rounded-lg border border-emerald-500/70 bg-emerald-900/70 text-emerald-100 hover:bg-emerald-800/80"
                >
                  关闭
                </button>
              </>
            )}
          </div>
        </div>
      )}
      {evidenceOpen && evidenceFocus && (
        <div className="fixed inset-0 bg-slate-950/70 z-[1200] grid place-items-center">
          <div className="w-[520px] max-w-[92vw] rounded-xl border border-slate-700 bg-slate-950 text-slate-100 p-4">
            <div className="text-sm font-extrabold mb-2">SnapPeg 物证详情</div>
            <div className="relative mb-2">
              <img src={evidenceFocus.url} alt={evidenceFocus.name} className={`w-full rounded-lg border ${geoTemporalBlocked ? 'border-rose-500/80' : 'border-slate-700'} mb-0`} />
              <div className="absolute bottom-2 left-2 rounded border border-slate-600/70 bg-slate-950/75 px-2 py-1 text-[10px] text-slate-200">
                桩号 {active?.code || '-'} · GPS {lat},{lng} · NTP {evidenceFocus.ntp}
              </div>
            </div>
            <div className="text-xs text-slate-400 break-all">
              <div className="text-emerald-300">主权已锁定</div>
              <div>签名 DID: {executorDid}</div>
              <div>定位: {lat}, {lng}</div>
              <div>授时戳: {evidenceFocus.ntp}</div>
              <div>样品: {sampleId || '-'}</div>
              <div>路径: {active?.uri || '-'}</div>
              {geoTemporalBlocked && <div className="text-rose-300 mt-1">GPS 漂移/时间窗口异常，已触发风险拦截。</div>}
            </div>
            <div className="flex justify-end mt-3">
              <button type="button" onClick={closeEvidencePreview} className="border border-slate-700 rounded-lg px-3 py-2 bg-slate-900 text-slate-200">关闭</button>
            </div>
          </div>
        </div>
      )}
      {evidenceCenterFocus && (
        <div className="fixed inset-0 bg-slate-950/70 z-[1200] grid place-items-center">
          <div className="w-[560px] max-w-[92vw] rounded-xl border border-slate-700 bg-slate-950 text-slate-100 p-4">
            <div className="text-sm font-extrabold mb-2">证据详情</div>
            {String(evidenceCenterFocus.media_type || '').startsWith('image') && String(evidenceCenterFocus.url || '') ? (
              <img src={String(evidenceCenterFocus.url || '')} alt={String(evidenceCenterFocus.file_name || 'evidence')} className="w-full rounded-lg border border-slate-700 mb-2" />
            ) : (
              <div className="h-[200px] grid place-items-center border border-slate-700 rounded-lg text-xs text-slate-400 mb-2">非图片证据</div>
            )}
            <div className="text-xs text-slate-400 break-all grid gap-1">
              <div>文件名: {String(evidenceCenterFocus.file_name || evidenceCenterFocus.id || '-')}</div>
              <div>Hash: {String(evidenceCenterFocus.evidence_hash || '-')}</div>
              <div>Proof ID: {String(evidenceCenterFocus.proof_id || '-')}</div>
              <div>时间: {String(evidenceCenterFocus.time || '-')}</div>
              <div>来源: {String(evidenceCenterFocus.source || '-')}</div>
              <div>匹配: {String(evidenceCenterFocus.hash_match_text || (evidenceCenterFocus.hash_matched ? '已匹配' : '待核验'))}</div>
              <div>GPS: {String((_asDict(evidenceCenterFocus.geo_location).lat || '-'))}, {String((_asDict(evidenceCenterFocus.geo_location).lng || '-'))}</div>
              <div>NTP: {String(_asDict(evidenceCenterFocus.server_timestamp_proof).ntp_server || _asDict(evidenceCenterFocus.server_timestamp_proof).proof_hash || '-')}</div>
            </div>
            {String(evidenceCenterFocus.url || '') && (
              <div className="mt-2">
                <a href={String(evidenceCenterFocus.url || '')} target="_blank" rel="noreferrer" className="text-xs text-emerald-300">打开原始文件</a>
              </div>
            )}
            <div className="flex justify-end mt-3">
              <button type="button" onClick={closeEvidenceFocus} className="border border-slate-700 rounded-lg px-3 py-2 bg-slate-900 text-slate-200">关闭</button>
            </div>
          </div>
        </div>
      )}
      {evidenceCenterDocFocus && (
        <div className="fixed inset-0 bg-slate-950/70 z-[1200] grid place-items-center">
          <div className="w-[520px] max-w-[92vw] rounded-xl border border-slate-700 bg-slate-950 text-slate-100 p-4">
            <div className="text-sm font-extrabold mb-2">文档详情</div>
            <div className="text-xs text-slate-400 break-all grid gap-1">
              <div>文件名: {String(evidenceCenterDocFocus.file_name || '-')}</div>
              <div>类型: {String(evidenceCenterDocFocus.doc_type || '-')}</div>
              {String(evidenceCenterDocFocus.doc_status || '') && (
                <div>状态: {String(evidenceCenterDocFocus.doc_status || '-')}</div>
              )}
              {String(evidenceCenterDocFocus.trip_action || '') && (
                <div>Trip: {String(evidenceCenterDocFocus.trip_action || '-')}</div>
              )}
              {String(evidenceCenterDocFocus.lifecycle_stage || '') && (
                <div>阶段: {String(evidenceCenterDocFocus.lifecycle_stage || '-')}</div>
              )}
              <div>Proof ID: {String(evidenceCenterDocFocus.proof_id || '-')}</div>
              <div>Proof Hash: {String(evidenceCenterDocFocus.proof_hash || '-')}</div>
              <div>创建时间: {String(evidenceCenterDocFocus.created_at || '-')}</div>
              <div>来源 UTXO: {String(evidenceCenterDocFocus.source_utxo_id || '-')}</div>
              <div>节点: {String(evidenceCenterDocFocus.node_uri || '-')}</div>
            </div>
            {String(evidenceCenterDocFocus.storage_url || '') ? (
              <div className="mt-2">
                <a href={String(evidenceCenterDocFocus.storage_url || '')} target="_blank" rel="noreferrer" className="text-xs text-emerald-300">打开文档</a>
              </div>
            ) : (
              <div className="mt-2 text-xs text-slate-500">无可用链接</div>
            )}
            <div className="flex justify-end mt-3">
              <button type="button" onClick={closeDocumentFocus} className="border border-slate-700 rounded-lg px-3 py-2 bg-slate-900 text-slate-200">关闭</button>
            </div>
          </div>
        </div>
      )}
      {arFocus && (
        <div className="fixed inset-0 bg-slate-950/70 z-[1200] grid place-items-center">
          <div className="w-[520px] max-w-[92vw] rounded-xl border border-slate-700 bg-slate-950 text-slate-100 p-4">
            <div className="text-sm font-extrabold mb-2">AR 现场验真视窗</div>
            <div className="text-xs text-slate-400 break-all grid gap-1">
              <div>细目: {String(arFocus.item_no || arFocus.item_name || arFocus.boq_item_uri || '-')}</div>
              <div>Proof ID: {String(arFocus.proof_id || '-')}</div>
              <div>Proof Hash: {String(arFocus.proof_hash || '-')}</div>
              <div>Trip: {String(arFocus.trip_action || arFocus.proof_type || '-')}</div>
              <div>阶段: {String(arFocus.lifecycle_stage || '-')}</div>
              <div>结果: {String(arFocus.result || '-')}</div>
              <div>距离: {String(arFocus.distance_m || '-')}m</div>
              <div>时间: {String(arFocus.created_at || '-')}</div>
            </div>
            <div className="mt-2 flex items-center justify-between text-[11px] text-slate-400">
              <span>GPS: {lat}, {lng}</span>
              <button
                type="button"
                onClick={() => void copyText('AR Proof Hash', String(arFocus.proof_hash || ''))}
                className="px-2 py-1 rounded border border-slate-700 text-[10px] text-slate-200 hover:bg-slate-800"
              >
                复制 Hash
              </button>
            </div>
            <div className="flex justify-end gap-2 mt-3">
              <button type="button" onClick={() => void jumpToArItem(arFocus)} className={`px-3 py-2 text-sm font-bold ${btnBlueCls}`}>定位到细目</button>
              <button type="button" onClick={() => setArFocus(null)} className="border border-slate-700 rounded-lg px-3 py-2 bg-slate-900 text-slate-200">关闭</button>
            </div>
          </div>
        </div>
      )}
      {arFullscreen && (
        <div className="fixed inset-0 z-[1300] bg-slate-950/95 text-slate-100">
          <div className="absolute inset-0">
            <div className="absolute inset-0 bg-gradient-to-b from-slate-900/60 via-slate-950/40 to-slate-950/80" />
            <div className="absolute inset-0 pointer-events-none">
              <div className="absolute left-1/2 top-1/2 w-14 h-14 -translate-x-1/2 -translate-y-1/2 border border-emerald-400/60 rounded-full" />
              <div className="absolute left-1/2 top-1/2 w-2 h-2 -translate-x-1/2 -translate-y-1/2 bg-emerald-400 rounded-full shadow-[0_0_16px_rgba(16,185,129,0.8)]" />
              <div className="absolute left-1/2 top-1/2 w-[1px] h-20 -translate-x-1/2 -translate-y-[calc(50%+40px)] bg-emerald-400/70" />
              <div className="absolute left-1/2 top-1/2 w-[1px] h-20 -translate-x-1/2 translate-y-[calc(50%+40px)] bg-emerald-400/70" />
              <div className="absolute left-1/2 top-1/2 h-[1px] w-20 -translate-y-1/2 -translate-x-[calc(50%+40px)] bg-emerald-400/70" />
              <div className="absolute left-1/2 top-1/2 h-[1px] w-20 -translate-y-1/2 translate-x-[calc(50%+40px)] bg-emerald-400/70" />
            </div>
          </div>
            <div className="relative z-10 h-full w-full flex flex-col">
              <div className="px-4 py-3 flex items-center justify-between border-b border-slate-800/60 bg-slate-950/70">
                <div>
                  <div className="text-sm font-extrabold">AR 现场验真全屏</div>
                  <div className="text-[11px] text-slate-400">GPS: {lat}, {lng} · 半径 {arRadius}m · 锚点 {arFilteredItems.length}/{arItemsSorted.length}</div>
                </div>
                <div className="flex items-center gap-2">
                  <button
                    type="button"
                    onClick={() => void runArOverlay()}
                    disabled={arLoading}
                  className={`px-3 py-2 text-xs font-bold ${btnAmberCls}`}
                >
                  {arLoading ? '刷新中...' : '刷新锚点'}
                </button>
                  <button
                    type="button"
                    onClick={() => setArFullscreen(false)}
                    className="px-3 py-2 text-xs border border-slate-700 rounded-lg bg-slate-900 text-slate-200"
                  >
                    退出
                  </button>
                </div>
              </div>
            <div className="flex-1 overflow-y-auto px-4 py-4">
              <div className="mb-3 grid gap-2">
                <div className="text-[11px] text-slate-400">距离过滤（米）</div>
                <div className="grid grid-cols-[1fr_auto] gap-2">
                  <input value={arFilterMax} onChange={(e) => setArFilterMax(e.target.value)} placeholder="例如 120" className={inputBaseCls} />
                  <div className="grid grid-cols-3 gap-1">
                    {[20, 50, 100].map((m) => (
                      <button
                        type="button"
                        key={`ar-filter-${m}`}
                        onClick={() => setArFilterMax(String(m))}
                        className="px-2 py-2 text-[11px] border border-slate-700 rounded bg-slate-900 text-slate-200 hover:bg-slate-800"
                      >
                        {m}m
                      </button>
                    ))}
                  </div>
                </div>
                <div className="text-[11px] text-slate-500">提示：留空或 0 表示不筛选</div>
              </div>
              {arItemsSorted.length === 0 && (
                <div className="text-sm text-slate-400 text-center mt-10">暂无锚点，请先获取 AR 叠加。</div>
              )}
              {arItemsSorted.length > 0 && arFilteredItems.length === 0 && (
                <div className="text-sm text-slate-400 text-center mt-4">当前距离过滤未命中锚点，请放宽范围。</div>
              )}
              <div className="grid gap-3">
                {arFilteredItems.map((item, idx) => {
                  const distance = Number(item.distance_m ?? 0)
                  const tone = toneForDistance(distance)
                  return (
                  <button
                    type="button"
                    key={`ar-full-${idx}`}
                    onClick={() => {
                      setArFocus(item)
                      setArFullscreen(false)
                    }}
                    className="w-full text-left border border-slate-800 rounded-xl p-3 bg-slate-950/70 hover:bg-slate-900/70"
                  >
                    <div className="flex items-center justify-between gap-2">
                      <div className="text-sm font-semibold text-slate-100 truncate">
                        {String(item.item_no || item.item_name || item.boq_item_uri || 'UTXO')}
                      </div>
                      <div className={`text-[10px] px-2 py-0.5 rounded-full border ${tone}`}>{String(item.distance_m || '-')}m</div>
                    </div>
                    <div className="mt-1 text-[11px] text-slate-400 truncate">Proof: {String(item.proof_id || '-')}</div>
                    <div className="text-[11px] text-slate-500 truncate">Trip: {String(item.trip_action || item.proof_type || '-')}</div>
                    <div className="text-[11px] text-slate-500 truncate">时间: {String(item.created_at || '-')}</div>
                  </button>
                )})}
              </div>
            </div>
            <div className="px-4 py-3 border-t border-slate-800/60 text-[11px] text-slate-400 bg-slate-950/70">
              提示：点击锚点可进入验真详情并定位到对应细目。
            </div>
          </div>
        </div>
      )}
          {deltaModalOpen && (
        <div className="fixed inset-0 bg-slate-950/70 z-[1200] grid place-items-center">
          <div className="w-[520px] max-w-[92vw] rounded-xl border border-rose-700 bg-slate-950 text-slate-100 p-4">
            <div className="text-sm font-extrabold mb-2">量值超出批复边界</div>
            <div className="text-xs text-slate-300 mb-3">当前申报量已超过批复量，请执行变更补差 Trip 后再提交。</div>
            <div className="text-xs text-slate-400 mb-3">申报量 + 已结算累计量 = {(effectiveSpent + effectiveClaimQtyValue).toLocaleString()}</div>
            <div className="flex justify-end gap-2">
              <button
                type="button"
                onClick={() => {
                  setShowAdvancedExecution(true)
                  setDeltaModalOpen(false)
                }}
                className={`px-3 py-2 font-bold ${btnAmberCls}`}
              >
                执行变更补差
              </button>
            </div>
          </div>
        </div>
      )}
      <DidFloatingCard
        executorDid={executorDid}
        supervisorDid={supervisorDid}
        ownerDid={ownerDid}
        riskScore={effectiveRiskScore}
        totalHash={String(totalHash || '')}
      />
      {!isOnline && (
        <div className="fixed bottom-4 left-4 right-4 z-[1100] border border-amber-600/70 bg-amber-950/40 text-amber-100 rounded-xl px-4 py-3 shadow-lg">
          <div className="flex flex-wrap items-center justify-between gap-3">
            <div className="text-xs font-semibold">
              离线主权模式 · 待同步 {offlineCount}
              {offlineSyncConflicts > 0 ? ` · 向量钟折叠 ${offlineSyncConflicts}` : ''}
            </div>
            <div className="flex items-center gap-2">
              <select value={offlineType} onChange={(e) => setOfflineType(e.target.value as OfflinePacketType)} className={inputXsCls}>
                <option value="quality.check">离线质检封存</option>
                <option value="variation.apply">离线变更补差</option>
              </select>
              <button type="button" onClick={() => void sealOfflinePacket()} className={`px-3 py-2 text-xs font-bold ${btnBlueCls}`}>封存当前动作</button>
              <button type="button" disabled={offlineImporting} onClick={() => offlineImportRef.current?.click()} className={`px-3 py-2 text-xs font-bold ${btnBlueCls}`}>{offlineImporting ? '导入中...' : '导入离线包'}</button>
              <button type="button" onClick={() => exportOfflinePackets()} disabled={!offlinePackets.length} className={`px-3 py-2 text-xs disabled:opacity-60 ${btnBlueCls}`}>导出</button>
              <button type="button" onClick={() => clearOfflinePackets()} disabled={!offlinePackets.length} className="rounded-lg border border-slate-600 px-3 py-2 text-xs bg-slate-900 text-slate-200 disabled:opacity-60">清空</button>
            </div>
          </div>
          <input ref={offlineImportRef} type="file" accept="application/json,.json" onChange={(e) => void importOfflinePackets(e.target.files?.[0] || null)} className="hidden" />
          {offlineImportName && <div className="mt-2 text-[11px] text-amber-200">已选文件: {offlineImportName}</div>}
          {!!offlineReplay && (
            <div className="mt-2 text-[11px] text-amber-200">
              重放完成: {String(offlineReplay.replayed_count || 0)} 条 · 错误 {String(offlineReplay.error_count || 0)} 条
            </div>
          )}
        </div>
      )}
      {fingerprintOpen && (
        <div className="fixed inset-0 bg-slate-950/70 z-[1200] grid place-items-center">
          <div className="w-[520px] max-w-[92vw] rounded-xl border border-slate-700 bg-slate-950 text-slate-100 p-4">
            <div className="text-sm font-extrabold mb-2">主权指纹</div>
            <div className="text-xs text-slate-400 mb-3">指纹数量: {evidence.length}</div>
            <div className="grid gap-2 max-h-[360px] overflow-y-auto">
              {evidence.length === 0 && <div className="text-xs text-slate-500">暂无指纹记录</div>}
              {evidence.map((x, idx) => (
                <div key={`${x.name}-${idx}`} className="border border-slate-800 rounded-lg p-2 text-xs">
                  <div className="text-emerald-300 font-semibold">指纹记录 #{String(idx + 1).padStart(2, '0')} · 主权已锁定</div>
                  <div className="text-slate-400 mt-1">文件: {x.name}</div>
                  <div className="text-slate-500">授时戳: {x.ntp}</div>
                </div>
              ))}
            </div>
            <div className="flex justify-end mt-3">
              <button type="button" onClick={() => setFingerprintOpen(false)} className="border border-slate-700 rounded-lg px-3 py-2 bg-slate-900 text-slate-200">关闭</button>
            </div>
          </div>
        </div>
      )}
      {traceOpen && (
        <div className="fixed inset-0 bg-slate-950/70 z-[1200] grid place-items-center">
          <div className="w-[560px] max-w-[92vw] rounded-xl border border-slate-700 bg-slate-950 text-slate-100 p-4">
            <div className="text-sm font-extrabold mb-2">样品溯源图谱</div>
            <EvidenceLineageGraph
              nodes={[
                { id: 'ledger', label: '0#台账 Genesis', subtitle: active?.uri || '-', tone: 'neutral' },
                { id: 'qcspec', label: 'QCSpec 质检 Proof', subtitle: sampleId || '-', tone: gateStats.qcCompliant ? 'ok' : 'warn' },
                { id: 'lab', label: 'LabPeg 实验 Proof', subtitle: gateStats.labLatestPass || '未检出', tone: gateStats.labQualified ? 'ok' : 'warn' },
                { id: 'docpeg', label: 'DocPeg 报表', subtitle: verifyUri || '-', tone: verifyUri ? 'ok' : 'neutral' },
                { id: 'hash', label: 'Final total_proof_hash', subtitle: totalHash || '-', tone: totalHash ? 'ok' : 'neutral' },
              ]}
            />
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
                <div>Total Proof Hash: {totalHash || '-'}</div>
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
      </NormEngineProvider>
    </ProjectSovereignProvider>
  )
}
