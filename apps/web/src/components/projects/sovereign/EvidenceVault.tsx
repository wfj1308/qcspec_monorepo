import { Fragment, useMemo, useState } from 'react'
import SovereignCard from './SovereignCard'
import { useProjectSovereign } from './SovereignContext'
import type { EvidenceFilter, EvidenceGraphNode, EvidenceScope } from './types'
type CardTone = 'certified' | 'pending' | 'conflict'
type FocusKind = 'evidence' | 'document'
type PipelineStage = 'genesis' | 'normref' | 'triprole' | 'finalproof'

type DrawerField = {
  label: string
  value: string
}

type PipelineCard = {
  id: string
  stage: PipelineStage
  title: string
  subtitle?: string
  eyebrow?: string
  tone: CardTone
  fields: DrawerField[]
  focusKind?: FocusKind
  focusId?: string
}

type Props = {
  btnBlueCls: string
  evidenceCenterLoading: boolean
  evidenceCenterError: string
  evidenceQuery: string
  evidenceScope: EvidenceScope
  evidenceSmuId: string
  evidenceFilter: EvidenceFilter
  smuOptions: string[]
  filteredEvidenceItems: Array<Record<string, unknown>>
  filteredDocs: Array<Record<string, unknown>>
  evidenceCompletenessScore: number
  settlementRiskScore: number
  evidenceGraphNodes: EvidenceGraphNode[]
  ledgerSnapshot: Record<string, unknown>
  meshpegItems: Array<Record<string, unknown>>
  formulaItems: Array<Record<string, unknown>>
  gatewayItems: Array<Record<string, unknown>>
  assetOrigin: Record<string, unknown>
  assetOriginStatement: string
  didReputationScore: number
  didReputationGrade: string
  didSamplingMultiplier: number
  didHighRiskList: string[]
  sealingPatternId: string
  sealingScanHint: string
  sealingMicrotext: string[]
  sealingRows: string[]
  scanEntryActiveOnly: Array<Record<string, unknown>>
  evidenceItemsPaged: Array<Record<string, unknown>>
  evidencePageSafe: number
  totalEvidencePages: number
  latestEvidenceNode: Record<string, unknown> | null
  utxoStatusText: string
  consensusConflict: Record<string, unknown> | boolean
  consensusAllowedAbsText: string
  consensusAllowedPctText: string
  disputeConflict: Record<string, unknown>
  disputeDeviation: number
  disputeDeviationPct: number
  disputeAllowedAbs: number | null
  disputeAllowedPct: number | null
  disputeValues: number[]
  disputeProof: string
  disputeOpen: boolean
  disputeProofShort: string
  erpRetrying: boolean
  erpRetryMsg: string
  evidenceZipDownloading: boolean
  erpReceiptDoc: Record<string, unknown> | null
  docpegRisk: Record<string, unknown>
  docpegRiskScore: number
  onEvidenceQueryChange: (value: string) => void
  onEvidenceScopeChange: (value: EvidenceScope) => void
  onEvidenceSmuIdChange: (value: string) => void
  onEvidenceFilterChange: (value: EvidenceFilter) => void
  onEvidencePageChange: (page: number) => void
  onEvidenceFocus: (value: string) => void
  onDocumentFocus: (value: string) => void
  onCopyText: (label: string, value: string) => void
  onRetryErpnextPush: () => void
  onExportEvidenceCenter: () => void
  onExportEvidenceCenterCsv: () => void
  onDownloadEvidenceCenterPackage: () => void
  onLoadEvidenceCenter: () => void
  onOpenDispute: (proofId: string) => void
}

const STAGE_META: Array<{ id: PipelineStage; label: string; caption: string }> = [
  { id: 'genesis', label: '0# 基线', caption: '账本源点与资产根' },
  { id: 'normref', label: '规范绑定', caption: '规范绑定与审计上下文' },
  { id: 'triprole', label: '工序执行', caption: '执行证据与现场链路' },
  { id: 'finalproof', label: '最终存证', caption: '归档哈希与争议闭环' },
]

function asDict(value: unknown): Record<string, unknown> {
  return value && typeof value === 'object' && !Array.isArray(value) ? (value as Record<string, unknown>) : {}
}

function asText(value: unknown, fallback = '-') {
  const text = String(value ?? '').trim()
  return text || fallback
}

function formatNumber(value: unknown, digits = 2) {
  const num = Number(value)
  if (!Number.isFinite(num)) return '-'
  return num.toLocaleString('zh-CN', { maximumFractionDigits: digits })
}

function formatPercent(value: unknown) {
  const num = Number(value)
  if (!Number.isFinite(num)) return '-'
  return `${num.toFixed(1)}%`
}

function formatDate(value: unknown) {
  const text = String(value ?? '').trim()
  if (!text) return '-'
  const stamp = Date.parse(text)
  if (!Number.isFinite(stamp)) return text
  return new Date(stamp).toLocaleString('zh-CN', { hour12: false })
}

function toTone(ok: boolean, hasConflict = false): CardTone {
  if (hasConflict) return 'conflict'
  return ok ? 'certified' : 'pending'
}

function hashStateTone(item: Record<string, unknown>): CardTone {
  if (Boolean(item.conflict) || Boolean(item.is_conflict)) return 'conflict'
  if (Boolean(item.hash_matched) || String(item.chain_status || '').toLowerCase() === 'onchain') return 'certified'
  return 'pending'
}

function buildField(label: string, value: unknown): DrawerField {
  return { label, value: asText(value) }
}

export default function EvidenceVault(props: Props) {
  const { project, identity, asset, audit } = useProjectSovereign()
  const [drawerCardId, setDrawerCardId] = useState<string>('genesis-ledger')

  const pipelineCards = useMemo<PipelineCard[]>(() => {
    const latestProof = asDict(props.latestEvidenceNode || {})
    const latestScan = props.scanEntryActiveOnly.length ? asDict(props.scanEntryActiveOnly[props.scanEntryActiveOnly.length - 1]) : {}
    const origin = asDict(props.assetOrigin)
    const risk = asDict(props.docpegRisk)
    const dispute = asDict(props.disputeConflict)

    const evidenceCards: PipelineCard[] = props.evidenceItemsPaged.slice(0, 2).map((item, index) => {
      const evidenceId = asText(item.id || item.hash || item.file_name || `evidence-${index}`)
      return {
        id: `trip-evidence-${evidenceId}`,
        stage: 'triprole',
        title: asText(item.file_name || item.id, '现场证据'),
        subtitle: asText(item.media_type || item.captured_at || item.created_at, '现场采集'),
        eyebrow: 'SnapPeg',
        tone: hashStateTone(item),
        focusKind: 'evidence',
        focusId: asText(item.id || item.hash || item.file_name, ''),
        fields: [
          buildField('证据ID', item.id || item.hash),
          buildField('媒体类型', item.media_type),
          buildField('GPS', `${asText(item.gps_lat, '-')}, ${asText(item.gps_lng, '-')}`),
          buildField('采集时间', formatDate(item.captured_at || item.created_at)),
          buildField('哈希状态', Boolean(item.hash_matched) ? '已匹配' : '待关联'),
          buildField('签名DID', item.did || identity.executorDid),
        ],
      }
    })

    const docCards: PipelineCard[] = props.filteredDocs.slice(-2).map((item, index) => {
      const docId = asText(item.id || item.file_name || `doc-${index}`)
      return {
        id: `final-doc-${docId}`,
        stage: 'finalproof',
        title: asText(item.file_name || item.doc_type, '归档文档'),
        subtitle: asText(item.doc_type || item.doc_uri || item.url, 'DocPeg 附件'),
        eyebrow: 'DocPeg',
        tone: toTone(Boolean(item.file_name || item.url)),
        focusKind: 'document',
        focusId: asText(item.id || item.file_name, ''),
        fields: [
          buildField('文档类型', item.doc_type),
          buildField('文件名', item.file_name),
          buildField('文档URI', item.doc_uri || item.url),
          buildField('上传时间', formatDate(item.created_at || item.uploaded_at)),
          buildField('哈希', item.hash || item.sha256),
        ],
      }
    })

    return [
      {
        id: 'genesis-ledger',
        stage: 'genesis',
        title: project.active?.name || '基线账本',
        subtitle: project.activePath || project.activeUri || asset.verifyUri || '-',
        eyebrow: '账本',
        tone: toTone(props.utxoStatusText !== '已消费'),
        fields: [
          buildField('项目URI', project.projectUri),
          buildField('当前路径', project.activePath || project.active?.uri),
          buildField('生命周期', project.lifecycle),
          buildField('UTXO状态', props.utxoStatusText),
          buildField('合同量', formatNumber(props.ledgerSnapshot.contract_quantity)),
          buildField('批复量', formatNumber(props.ledgerSnapshot.approved_quantity)),
          buildField('设计量', formatNumber(props.ledgerSnapshot.design_quantity)),
          buildField('结算量', formatNumber(asset.effectiveSpent)),
        ],
      },
      {
        id: 'genesis-origin',
        stage: 'genesis',
        title: asText(origin.material_origin || origin.source || '资产来源'),
        subtitle: asText(props.assetOriginStatement, '待补充来源说明'),
        eyebrow: '来源',
        tone: toTone(Boolean(props.assetOriginStatement)),
        fields: [
          buildField('来源说明', props.assetOriginStatement),
          buildField('来源地点', origin.location || origin.vendor || origin.factory),
          buildField('批次ID', origin.batch_id || origin.batch_no),
          buildField('运输ID', origin.shipment_id || origin.trip_id),
          buildField('节点编码', project.active?.code),
        ],
      },
      {
        id: 'normref-binding',
        stage: 'normref',
        title: audit.normResolution.specBinding || '规范绑定缺失',
        subtitle: audit.normResolution.gateBinding || audit.normResolution.message,
        eyebrow: '规范',
        tone: audit.normResolution.status === 'missing' ? 'conflict' : audit.normResolution.status === 'ready' ? 'certified' : 'pending',
        fields: [
          buildField('规范绑定', audit.normResolution.specBinding || '未绑定'),
          buildField('闸门绑定', audit.normResolution.gateBinding || '未绑定'),
          buildField('解析状态', audit.normResolution.status),
          buildField('规范引用', audit.normResolution.normRefs.join(' / ')),
          buildField('质检门控', audit.gateStats.qcStatus),
          buildField('实验门控', audit.gateStats.labStatus),
        ],
      },
      {
        id: 'normref-did',
        stage: 'normref',
        title: `DID信誉 ${formatNumber(props.didReputationScore)}`,
        subtitle: `等级 ${props.didReputationGrade || '-'} / 抽样系数 ${formatNumber(props.didSamplingMultiplier)}`,
        eyebrow: 'DID',
        tone: props.didHighRiskList.length ? 'conflict' : props.didReputationScore >= 80 ? 'certified' : 'pending',
        fields: [
          buildField('信誉分值', formatNumber(props.didReputationScore)),
          buildField('等级', props.didReputationGrade),
          buildField('抽样系数', formatNumber(props.didSamplingMultiplier)),
          buildField('高风险DID', props.didHighRiskList.join(' / ') || '无'),
          buildField('执行方DID', identity.executorDid),
          buildField('监理DID', identity.supervisorDid),
        ],
      },
      {
        id: 'normref-risk',
        stage: 'normref',
        title: `风险审计 ${formatNumber(props.docpegRiskScore)}`,
        subtitle: asText(risk.summary || risk.level || '打开抽屉查看详情'),
        eyebrow: '风险',
        tone: props.docpegRiskScore >= 60 ? 'conflict' : props.docpegRiskScore > 0 ? 'pending' : 'certified',
        fields: [
          buildField('风险分值', formatNumber(props.docpegRiskScore)),
          buildField('结算风险', formatNumber(props.settlementRiskScore)),
          buildField('完整度', formatPercent(props.evidenceCompletenessScore)),
          buildField('风险标签', JSON.stringify(risk.tags || risk.reasons || [])),
          buildField('风险摘要', risk.summary || risk.level),
        ],
      },
      {
        id: 'triprole-latest',
        stage: 'triprole',
        title: asText(latestProof.proof_id || asset.inputProofId, '工序待提交'),
        subtitle: asText(latestProof.created_at || latestProof.ntp_ts || latestProof.updated_at, '最新现场存证'),
        eyebrow: '工序',
        tone: toTone(audit.gateStats.qcCompliant, props.disputeOpen),
        fields: [
          buildField('存证ID', latestProof.proof_id || asset.inputProofId),
          buildField('双门控', audit.gateStats.dualQualified ? '通过' : '已阻断'),
          buildField('质检状态', audit.gateStats.qcStatus),
          buildField('实验状态', audit.gateStats.labStatus),
          buildField('扫码录入', latestScan.proof_id || latestScan.scan_token),
          buildField('时间戳', formatDate(latestProof.created_at || latestProof.updated_at)),
        ],
      },
      {
        id: 'triprole-gateway',
        stage: 'triprole',
        title: `网关 ${props.gatewayItems.length} / 网状链路 ${props.meshpegItems.length}`,
        subtitle: `公式 ${props.formulaItems.length} / 扫码 ${props.scanEntryActiveOnly.length}`,
        eyebrow: '网关',
        tone: toTone(!audit.geoTemporalBlocked && props.gatewayItems.length > 0, audit.geoTemporalBlocked),
        fields: [
          buildField('网关记录', props.gatewayItems.length),
          buildField('MeshPeg 记录', props.meshpegItems.length),
          buildField('公式记录', props.formulaItems.length),
          buildField('扫码记录', props.scanEntryActiveOnly.length),
          buildField('地理门控', audit.geoTemporalBlocked ? '已阻断' : '通过'),
          buildField('结算风险', formatNumber(props.settlementRiskScore)),
        ],
      },
      ...evidenceCards,
      {
        id: 'finalproof-hash',
        stage: 'finalproof',
        title: props.disputeOpen ? `争议开启 ${props.disputeProofShort || '-'}` : asText(asset.totalHash, '最终哈希待生成'),
        subtitle: `完整度 ${formatPercent(props.evidenceCompletenessScore)} / 风险 ${formatNumber(props.docpegRiskScore)}`,
        eyebrow: '哈希',
        tone: props.disputeOpen ? 'conflict' : toTone(Boolean(asset.totalHash)),
        fields: [
          buildField('最终哈希', asset.totalHash),
          buildField('输出存证', asset.finalProofId),
          buildField('完整度', formatPercent(props.evidenceCompletenessScore)),
          buildField('风险分值', formatNumber(props.docpegRiskScore)),
          buildField('争议状态', props.disputeOpen ? '开启' : '清除'),
          buildField('允许偏差', `${props.consensusAllowedAbsText || '-'} / ${props.consensusAllowedPctText || '-'}`),
        ],
      },
      {
        id: 'finalproof-sealing',
        stage: 'finalproof',
        title: props.sealingPatternId || '封签模式待生成',
        subtitle: props.sealingScanHint || '打开抽屉查看 DID、GPS 与微字',
        eyebrow: '封签',
        tone: toTone(Boolean(props.sealingPatternId)),
        fields: [
          buildField('模式ID', props.sealingPatternId),
          buildField('扫码提示', props.sealingScanHint),
          buildField('ASCII封签', props.sealingRows.join(' | ') || '-'),
          buildField('微字', props.sealingMicrotext.join(' | ') || '-'),
          buildField('ERP回执', props.erpReceiptDoc?.file_name || props.erpReceiptDoc?.doc_uri),
          buildField('ERP状态', props.erpRetryMsg || '就绪'),
        ],
      },
      {
        id: 'finalproof-dispute',
        stage: 'finalproof',
        title: props.disputeOpen ? `已阻断，偏差 ${formatNumber(props.disputeDeviation)}` : '共识清晰',
        subtitle: props.disputeOpen ? `存证 ${props.disputeProofShort || '-'}` : '无开放争议',
        eyebrow: '共识',
        tone: props.disputeOpen || Boolean(props.consensusConflict) ? 'conflict' : 'certified',
        fields: [
          buildField('争议开启', props.disputeOpen ? '是' : '否'),
          buildField('存证', props.disputeProof),
          buildField('偏差', formatNumber(props.disputeDeviation)),
          buildField('偏差比例', formatPercent(props.disputeDeviationPct)),
          buildField('允许绝对偏差', props.disputeAllowedAbs == null ? '-' : formatNumber(props.disputeAllowedAbs)),
          buildField('允许百分比偏差', props.disputeAllowedPct == null ? '-' : formatPercent(props.disputeAllowedPct)),
          buildField('冲突样本', props.disputeValues.length ? props.disputeValues.map((item) => formatNumber(item)).join(' / ') : '-'),
          buildField('冲突载荷', JSON.stringify(dispute)),
        ],
      },
      ...docCards,
      {
        id: 'finalproof-graph',
        stage: 'finalproof',
        title: '因果链路',
        subtitle: props.evidenceGraphNodes.map((item) => item.label).join(' -> '),
        eyebrow: '流程',
        tone: toTone(props.evidenceGraphNodes.some((item) => item.tone === 'ok')),
        fields: props.evidenceGraphNodes.map((item) => ({
          label: item.label,
          value: `${item.subtitle || '-'} / ${item.tone}`,
        })),
      },
      {
        id: 'finalproof-receipt',
        stage: 'finalproof',
        title: props.erpReceiptDoc ? asText(props.erpReceiptDoc.file_name, 'ERP回执') : 'ERP回执待生成',
        subtitle: props.erpRetryMsg || asText(props.erpReceiptDoc?.doc_uri || props.erpReceiptDoc?.url, '等待 ERPnext'),
        eyebrow: 'ERP',
        tone: props.erpRetryMsg ? 'pending' : props.erpReceiptDoc ? 'certified' : 'pending',
        focusKind: props.erpReceiptDoc ? 'document' : undefined,
        focusId: props.erpReceiptDoc ? asText(props.erpReceiptDoc.id || props.erpReceiptDoc.file_name, '') : undefined,
        fields: [
          buildField('回执文件', props.erpReceiptDoc?.file_name),
          buildField('文档URI', props.erpReceiptDoc?.doc_uri || props.erpReceiptDoc?.url),
          buildField('推送状态', props.erpRetryMsg || '完成'),
          buildField('重试中', props.erpRetrying ? '是' : '否'),
        ],
      },
    ]
  }, [asset.effectiveSpent, asset.finalProofId, asset.inputProofId, asset.totalHash, asset.verifyUri, audit.gateStats.dualQualified, audit.gateStats.labStatus, audit.gateStats.qcCompliant, audit.gateStats.qcStatus, audit.geoTemporalBlocked, audit.normResolution.gateBinding, audit.normResolution.message, audit.normResolution.normRefs, audit.normResolution.specBinding, audit.normResolution.status, identity.executorDid, identity.supervisorDid, project.active?.code, project.active?.name, project.active?.uri, project.activePath, project.activeUri, project.lifecycle, project.projectUri, props.assetOrigin, props.assetOriginStatement, props.consensusAllowedAbsText, props.consensusAllowedPctText, props.consensusConflict, props.disputeAllowedAbs, props.disputeAllowedPct, props.disputeConflict, props.disputeDeviation, props.disputeDeviationPct, props.disputeOpen, props.disputeProof, props.disputeProofShort, props.disputeValues, props.didHighRiskList, props.didReputationGrade, props.didReputationScore, props.didSamplingMultiplier, props.docpegRisk, props.docpegRiskScore, props.evidenceCompletenessScore, props.evidenceGraphNodes, props.evidenceItemsPaged, props.erpReceiptDoc, props.erpRetryMsg, props.erpRetrying, props.filteredDocs, props.formulaItems.length, props.gatewayItems.length, props.latestEvidenceNode, props.ledgerSnapshot, props.meshpegItems.length, props.scanEntryActiveOnly, props.sealingMicrotext, props.sealingPatternId, props.sealingRows, props.sealingScanHint, props.settlementRiskScore, props.utxoStatusText])

  const selectedCard = useMemo(
    () => pipelineCards.find((item) => item.id === drawerCardId) || pipelineCards[0] || null,
    [drawerCardId, pipelineCards],
  )

  const stageCounts = useMemo(() => {
    const map = new Map<PipelineStage, number>()
    pipelineCards.forEach((item) => {
      map.set(item.stage, (map.get(item.stage) || 0) + 1)
    })
    return map
  }, [pipelineCards])

  const stageTone = useMemo(() => {
    const toneMap = new Map<PipelineStage, CardTone>()
    STAGE_META.forEach((stage) => {
      const cards = pipelineCards.filter((item) => item.stage === stage.id)
      if (cards.some((item) => item.tone === 'conflict')) {
        toneMap.set(stage.id, 'conflict')
      } else if (cards.some((item) => item.tone === 'certified')) {
        toneMap.set(stage.id, 'certified')
      } else {
        toneMap.set(stage.id, 'pending')
      }
    })
    return toneMap
  }, [pipelineCards])

  const handleCardOpen = (card: PipelineCard) => {
    setDrawerCardId(card.id)
    if (card.focusKind === 'evidence' && card.focusId) props.onEvidenceFocus(card.focusId)
    if (card.focusKind === 'document' && card.focusId) props.onDocumentFocus(card.focusId)
  }

  return (
    <section className="mt-4 rounded-[28px] border border-slate-700/70 bg-[radial-gradient(circle_at_top_left,rgba(59,130,246,0.08),transparent_28%),linear-gradient(180deg,rgba(2,6,23,0.92),rgba(2,6,23,0.86))] p-4 shadow-[0_24px_80px_rgba(2,6,23,0.3)]">
      <div className="flex flex-wrap items-start justify-between gap-3">
        <div>
          <div className="text-[11px] font-semibold uppercase tracking-[0.22em] text-sky-300">证据中心</div>
          <div className="mt-2 text-lg font-semibold text-slate-50">从基线账本到最终存证的因果链路</div>
          <div className="mt-1 text-sm text-slate-400">{project.activePath || project.active?.uri || '-'} / 生命周期 {project.lifecycle}</div>
        </div>
        <div className="flex flex-wrap items-center gap-2 text-[11px]">
          <span className={`rounded-full border px-2.5 py-1 ${audit.gateStats.dualQualified ? 'border-emerald-500/60 bg-emerald-950/30 text-emerald-200' : 'border-amber-500/60 bg-amber-950/30 text-amber-200'}`}>
            双门控 {audit.gateStats.dualQualified ? '通过' : '阻断'}
          </span>
          <span className={`rounded-full border px-2.5 py-1 ${props.disputeOpen ? 'border-rose-500/60 bg-rose-950/30 text-rose-200' : 'border-slate-600/60 bg-slate-900/50 text-slate-300'}`}>
            争议 {props.disputeOpen ? '开启' : '清除'}
          </span>
          <span className="rounded-full border border-sky-500/40 bg-sky-950/20 px-2.5 py-1 text-sky-200">
            证据 {props.filteredEvidenceItems.length} / 文档 {props.filteredDocs.length}
          </span>
        </div>
      </div>

      <div className="mt-4 grid gap-3 rounded-2xl border border-slate-700/60 bg-slate-950/40 p-3 lg:grid-cols-[minmax(0,1fr)_auto]">
        <div className="grid gap-3 md:grid-cols-2 xl:grid-cols-4">
          <input
            value={props.evidenceQuery}
            onChange={(event) => props.onEvidenceQueryChange(event.target.value)}
            placeholder="搜索存证、文档或哈希"
            className="rounded-xl border border-slate-700 bg-slate-950/60 px-3 py-2 text-sm text-slate-100 outline-none transition focus:border-sky-500"
          />
          <select
            value={props.evidenceScope}
            onChange={(event) => props.onEvidenceScopeChange(event.target.value as EvidenceScope)}
            className="rounded-xl border border-slate-700 bg-slate-950/60 px-3 py-2 text-sm text-slate-100 outline-none"
          >
            <option value="item">按节点</option>
            <option value="smu">按SMU</option>
          </select>
          <select
            value={props.evidenceSmuId}
            onChange={(event) => props.onEvidenceSmuIdChange(event.target.value)}
            className="rounded-xl border border-slate-700 bg-slate-950/60 px-3 py-2 text-sm text-slate-100 outline-none"
          >
            {props.smuOptions.map((item) => (
              <option key={item} value={item}>{item}</option>
            ))}
          </select>
          <select
            value={props.evidenceFilter}
            onChange={(event) => props.onEvidenceFilterChange(event.target.value as EvidenceFilter)}
            className="rounded-xl border border-slate-700 bg-slate-950/60 px-3 py-2 text-sm text-slate-100 outline-none"
          >
            <option value="all">全部</option>
            <option value="matched">已匹配</option>
            <option value="unmatched">待关联</option>
            <option value="image">仅图片</option>
          </select>
        </div>
        <div className="flex flex-wrap justify-end gap-2">
          <button type="button" onClick={props.onLoadEvidenceCenter} className={`px-3 py-2 text-sm ${props.btnBlueCls}`}>刷新</button>
          <button type="button" onClick={props.onExportEvidenceCenter} className={`px-3 py-2 text-sm ${props.btnBlueCls}`}>导出报告</button>
          <button type="button" onClick={props.onExportEvidenceCenterCsv} className={`px-3 py-2 text-sm ${props.btnBlueCls}`}>导出CSV</button>
          <button type="button" onClick={props.onDownloadEvidenceCenterPackage} disabled={props.evidenceZipDownloading} className={`px-3 py-2 text-sm disabled:opacity-60 ${props.btnBlueCls}`}>
            {props.evidenceZipDownloading ? '打包中...' : '下载证据包'}
          </button>
          <button type="button" onClick={props.onRetryErpnextPush} disabled={props.erpRetrying} className={`px-3 py-2 text-sm disabled:opacity-60 ${props.btnBlueCls}`}>
            {props.erpRetrying ? '重试中...' : '重试ERP'}
          </button>
        </div>
      </div>

      {(props.evidenceCenterLoading || props.evidenceCenterError) && (
        <div className={`mt-3 rounded-2xl border px-3 py-2 text-sm ${props.evidenceCenterError ? 'border-rose-500/60 bg-rose-950/30 text-rose-200' : 'border-sky-500/50 bg-sky-950/20 text-sky-200'}`}>
          {props.evidenceCenterError || '证据中心加载中...'}
        </div>
      )}

      <div className="mt-4 overflow-x-auto pb-2">
        <div className="flex min-w-max gap-4">
          {STAGE_META.map((stage, index) => {
            const cards = pipelineCards.filter((item) => item.stage === stage.id)
            const tone = stageTone.get(stage.id) || 'pending'
            const frameCls = tone === 'conflict'
              ? 'border-rose-500/50 bg-rose-950/18'
              : tone === 'certified'
                ? 'border-emerald-500/40 bg-emerald-950/12'
                : 'border-amber-500/40 bg-amber-950/12'
            return (
              <Fragment key={stage.id}>
                <div className={`w-[320px] shrink-0 rounded-[26px] border p-3 ${frameCls}`}>
                  <div className="flex items-center justify-between gap-2">
                    <div>
                      <div className="text-[11px] uppercase tracking-[0.18em] text-slate-400">{stage.label}</div>
                      <div className="mt-1 text-sm text-slate-300">{stage.caption}</div>
                    </div>
                    <div className="rounded-full border border-slate-700/70 bg-slate-950/60 px-2 py-1 text-[11px] text-slate-300">
                      {stageCounts.get(stage.id) || 0} 张卡片
                    </div>
                  </div>
                  <div className="mt-3 grid gap-3">
                    {cards.map((card) => (
                      <SovereignCard
                        key={card.id}
                        title={card.title}
                        subtitle={card.subtitle}
                        eyebrow={card.eyebrow}
                        tone={card.tone}
                        onClick={() => handleCardOpen(card)}
                      >
                        <div className="flex items-center justify-between text-[11px] text-slate-300">
                          <span>{card.fields[0]?.label || '详情'}</span>
                          <span className="truncate pl-3 text-slate-400">{card.fields[0]?.value || '-'}</span>
                        </div>
                      </SovereignCard>
                    ))}
                  </div>
                </div>
                {index < STAGE_META.length - 1 && (
                  <div className="flex items-center">
                    <div className="h-[2px] w-14 rounded-full bg-gradient-to-r from-sky-400/70 via-cyan-300/40 to-transparent" />
                  </div>
                )}
              </Fragment>
            )
          })}
        </div>
      </div>

      <div className="mt-4 grid gap-4 xl:grid-cols-[minmax(0,1.2fr)_380px]">
        <div className="rounded-[24px] border border-slate-700/70 bg-slate-950/35 p-4">
          <div className="flex items-center justify-between gap-3">
            <div>
              <div className="text-[11px] uppercase tracking-[0.18em] text-slate-400">流程快照</div>
              <div className="mt-1 text-sm font-semibold text-slate-100">证据页 {props.evidencePageSafe} / {props.totalEvidencePages}</div>
            </div>
            <div className="flex items-center gap-2">
              <button
                type="button"
                onClick={() => props.onEvidencePageChange(Math.max(1, props.evidencePageSafe - 1))}
                disabled={props.evidencePageSafe <= 1}
                className="rounded-lg border border-slate-700 bg-slate-950/60 px-3 py-1.5 text-xs text-slate-200 disabled:opacity-40"
              >
                上一页
              </button>
              <button
                type="button"
                onClick={() => props.onEvidencePageChange(Math.min(props.totalEvidencePages, props.evidencePageSafe + 1))}
                disabled={props.evidencePageSafe >= props.totalEvidencePages}
                className="rounded-lg border border-slate-700 bg-slate-950/60 px-3 py-1.5 text-xs text-slate-200 disabled:opacity-40"
              >
                下一页
              </button>
            </div>
          </div>
          <div className="mt-3 grid gap-3 md:grid-cols-2 xl:grid-cols-3">
            {props.evidenceItemsPaged.length ? props.evidenceItemsPaged.map((item, index) => {
              const evidenceId = asText(item.id || item.hash || item.file_name || `page-${index}`)
              const label = asText(item.file_name || item.id, '现场证据')
              const tone = hashStateTone(item)
              return (
                <button
                  type="button"
                  key={evidenceId}
                  onClick={() => {
                    props.onEvidenceFocus(evidenceId)
                    const matched = pipelineCards.find((card) => card.focusKind === 'evidence' && card.focusId === evidenceId)
                    if (matched) setDrawerCardId(matched.id)
                  }}
                  className="rounded-2xl border border-slate-700/70 bg-slate-950/40 p-3 text-left transition hover:border-sky-500/60 hover:bg-slate-900/60"
                >
                  <div className="flex items-center justify-between gap-2">
                    <div className="text-sm font-semibold text-slate-100">{label}</div>
                    <span className={`rounded-full border px-2 py-0.5 text-[10px] ${tone === 'certified' ? 'border-emerald-500/60 bg-emerald-950/20 text-emerald-200' : tone === 'conflict' ? 'border-rose-500/60 bg-rose-950/20 text-rose-200' : 'border-amber-500/60 bg-amber-950/20 text-amber-200'}`}>
                      {tone === 'certified' ? '已封存' : tone === 'conflict' ? '冲突' : '待处理'}
                    </span>
                  </div>
                  <div className="mt-2 text-xs text-slate-400">哈希: {asText(item.hash || item.id)}</div>
                  <div className="mt-1 text-xs text-slate-500">GPS: {asText(item.gps_lat, '-')}, {asText(item.gps_lng, '-')}</div>
                  <div className="mt-1 text-xs text-slate-500">时间: {formatDate(item.captured_at || item.created_at)}</div>
                </button>
              )
            }) : (
              <div className="col-span-full rounded-2xl border border-dashed border-slate-700 bg-slate-950/20 px-4 py-10 text-center text-sm text-slate-500">
                当前筛选条件下无证据
              </div>
            )}
          </div>
        </div>

        <aside className="rounded-[24px] border border-slate-700/70 bg-slate-950/45 p-4 shadow-[inset_0_1px_0_rgba(148,163,184,0.08)]">
          <div className="flex items-start justify-between gap-3">
            <div>
              <div className="text-[11px] uppercase tracking-[0.18em] text-slate-400">证据抽屉</div>
              <div className="mt-1 text-base font-semibold text-slate-50">{selectedCard?.title || '未选择卡片'}</div>
              <div className="mt-1 text-sm text-slate-400">{selectedCard?.subtitle || '请选择流程中的卡片查看详情'}</div>
            </div>
            {selectedCard && (
              <button
                type="button"
                onClick={() => props.onCopyText('证据卡片', `${selectedCard.title} ${selectedCard.subtitle || ''}`)}
                className="rounded-lg border border-slate-700 bg-slate-950/60 px-3 py-1.5 text-xs text-slate-200"
              >
                复制摘要
              </button>
            )}
          </div>

          <div className="mt-4 grid gap-2">
            {selectedCard?.fields.map((field) => (
              <div key={`${selectedCard.id}-${field.label}`} className="rounded-xl border border-slate-700/70 bg-slate-950/35 px-3 py-2">
                <div className="text-[11px] uppercase tracking-[0.14em] text-slate-500">{field.label}</div>
                <div className="mt-1 break-all text-sm text-slate-100">{field.value}</div>
              </div>
            ))}
          </div>

          <div className="mt-4 grid gap-2 rounded-2xl border border-slate-700/70 bg-slate-950/35 p-3">
            <div className="text-[11px] uppercase tracking-[0.18em] text-slate-400">上下文穿透</div>
            <div className="text-sm text-slate-200">执行方DID: {identity.executorDid || '-'}</div>
            <div className="text-sm text-slate-200">监理DID: {identity.supervisorDid || '-'}</div>
            <div className="text-sm text-slate-200">业主DID: {identity.ownerDid || '-'}</div>
            <div className="text-sm text-slate-200">守门状态: {audit.gateReason || '无阻断项'}</div>
            <div className="text-sm text-slate-200">余额: {audit.exceedBalance ? '余额不足，需补差' : '可用'}</div>
          </div>

          {props.disputeOpen && (
            <button
              type="button"
              onClick={() => props.onOpenDispute(props.disputeProof)}
              className="mt-4 w-full rounded-xl border border-rose-500/60 bg-rose-950/30 px-3 py-2 text-sm font-semibold text-rose-100 transition hover:bg-rose-950/45"
            >
              打开争议存证 {props.disputeProofShort || ''}
            </button>
          )}
        </aside>
      </div>
    </section>
  )
}
