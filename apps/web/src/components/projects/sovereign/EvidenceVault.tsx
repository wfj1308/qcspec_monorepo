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
  { id: 'genesis', label: '0# Genesis', caption: 'Ledger origin and asset root' },
  { id: 'normref', label: 'NormRef', caption: 'Norm binding and audit context' },
  { id: 'triprole', label: 'TripRole', caption: 'Execution evidence and field chain' },
  { id: 'finalproof', label: 'Final Proof', caption: 'Archive hash and dispute exit' },
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
        title: asText(item.file_name || item.id, 'SnapPeg evidence'),
        subtitle: asText(item.media_type || item.captured_at || item.created_at, 'Field capture'),
        eyebrow: 'SnapPeg',
        tone: hashStateTone(item),
        focusKind: 'evidence',
        focusId: asText(item.id || item.hash || item.file_name, ''),
        fields: [
          buildField('Evidence ID', item.id || item.hash),
          buildField('Media type', item.media_type),
          buildField('GPS', `${asText(item.gps_lat, '-')}, ${asText(item.gps_lng, '-')}`),
          buildField('Captured at', formatDate(item.captured_at || item.created_at)),
          buildField('Hash state', Boolean(item.hash_matched) ? 'Matched' : 'Pending link'),
          buildField('Signer DID', item.did || identity.executorDid),
        ],
      }
    })

    const docCards: PipelineCard[] = props.filteredDocs.slice(-2).map((item, index) => {
      const docId = asText(item.id || item.file_name || `doc-${index}`)
      return {
        id: `final-doc-${docId}`,
        stage: 'finalproof',
        title: asText(item.file_name || item.doc_type, 'Archive document'),
        subtitle: asText(item.doc_type || item.doc_uri || item.url, 'DocPeg attachment'),
        eyebrow: 'DocPeg',
        tone: toTone(Boolean(item.file_name || item.url)),
        focusKind: 'document',
        focusId: asText(item.id || item.file_name, ''),
        fields: [
          buildField('Doc type', item.doc_type),
          buildField('File name', item.file_name),
          buildField('Doc URI', item.doc_uri || item.url),
          buildField('Uploaded at', formatDate(item.created_at || item.uploaded_at)),
          buildField('Hash', item.hash || item.sha256),
        ],
      }
    })

    return [
      {
        id: 'genesis-ledger',
        stage: 'genesis',
        title: project.active?.name || 'Genesis ledger',
        subtitle: project.activePath || project.activeUri || asset.verifyUri || '-',
        eyebrow: 'Ledger',
        tone: toTone(props.utxoStatusText !== '已消费'),
        fields: [
          buildField('Project URI', project.projectUri),
          buildField('Active path', project.activePath || project.active?.uri),
          buildField('Lifecycle', project.lifecycle),
          buildField('UTXO state', props.utxoStatusText),
          buildField('Contract qty', formatNumber(props.ledgerSnapshot.contract_quantity)),
          buildField('Approved qty', formatNumber(props.ledgerSnapshot.approved_quantity)),
          buildField('Design qty', formatNumber(props.ledgerSnapshot.design_quantity)),
          buildField('Settled qty', formatNumber(asset.effectiveSpent)),
        ],
      },
      {
        id: 'genesis-origin',
        stage: 'genesis',
        title: asText(origin.material_origin || origin.source || 'Asset origin'),
        subtitle: asText(props.assetOriginStatement, 'Waiting for source statement'),
        eyebrow: 'Origin',
        tone: toTone(Boolean(props.assetOriginStatement)),
        fields: [
          buildField('Origin statement', props.assetOriginStatement),
          buildField('Origin place', origin.location || origin.vendor || origin.factory),
          buildField('Batch ID', origin.batch_id || origin.batch_no),
          buildField('Shipment ID', origin.shipment_id || origin.trip_id),
          buildField('Node code', project.active?.code),
        ],
      },
      {
        id: 'normref-binding',
        stage: 'normref',
        title: audit.normResolution.specBinding || 'NormRef missing',
        subtitle: audit.normResolution.gateBinding || audit.normResolution.message,
        eyebrow: 'NormRef',
        tone: audit.normResolution.status === 'missing' ? 'conflict' : audit.normResolution.status === 'ready' ? 'certified' : 'pending',
        fields: [
          buildField('Spec binding', audit.normResolution.specBinding || 'Unbound'),
          buildField('Gate binding', audit.normResolution.gateBinding || 'Unbound'),
          buildField('Resolver state', audit.normResolution.status),
          buildField('Norm refs', audit.normResolution.normRefs.join(' / ')),
          buildField('QC gate', audit.gateStats.qcStatus),
          buildField('Lab gate', audit.gateStats.labStatus),
        ],
      },
      {
        id: 'normref-did',
        stage: 'normref',
        title: `DID reputation ${formatNumber(props.didReputationScore)}`,
        subtitle: `Grade ${props.didReputationGrade || '-'} / Multiplier ${formatNumber(props.didSamplingMultiplier)}`,
        eyebrow: 'DID',
        tone: props.didHighRiskList.length ? 'conflict' : props.didReputationScore >= 80 ? 'certified' : 'pending',
        fields: [
          buildField('Reputation score', formatNumber(props.didReputationScore)),
          buildField('Grade', props.didReputationGrade),
          buildField('Sampling multiplier', formatNumber(props.didSamplingMultiplier)),
          buildField('High risk DID', props.didHighRiskList.join(' / ') || 'None'),
          buildField('Executor DID', identity.executorDid),
          buildField('Supervisor DID', identity.supervisorDid),
        ],
      },
      {
        id: 'normref-risk',
        stage: 'normref',
        title: `Risk audit ${formatNumber(props.docpegRiskScore)}`,
        subtitle: asText(risk.summary || risk.level || 'Open drawer for details'),
        eyebrow: 'Risk',
        tone: props.docpegRiskScore >= 60 ? 'conflict' : props.docpegRiskScore > 0 ? 'pending' : 'certified',
        fields: [
          buildField('Risk score', formatNumber(props.docpegRiskScore)),
          buildField('Settlement risk', formatNumber(props.settlementRiskScore)),
          buildField('Completeness', formatPercent(props.evidenceCompletenessScore)),
          buildField('Risk tags', JSON.stringify(risk.tags || risk.reasons || [])),
          buildField('Risk summary', risk.summary || risk.level),
        ],
      },
      {
        id: 'triprole-latest',
        stage: 'triprole',
        title: asText(latestProof.proof_id || asset.inputProofId, 'TripRole pending'),
        subtitle: asText(latestProof.created_at || latestProof.ntp_ts || latestProof.updated_at, 'Latest field proof'),
        eyebrow: 'TripRole',
        tone: toTone(audit.gateStats.qcCompliant, props.disputeOpen),
        fields: [
          buildField('Proof ID', latestProof.proof_id || asset.inputProofId),
          buildField('Dual gate', audit.gateStats.dualQualified ? 'Pass' : 'Blocked'),
          buildField('QC state', audit.gateStats.qcStatus),
          buildField('Lab state', audit.gateStats.labStatus),
          buildField('Scan entry', latestScan.proof_id || latestScan.scan_token),
          buildField('Timestamp', formatDate(latestProof.created_at || latestProof.updated_at)),
        ],
      },
      {
        id: 'triprole-gateway',
        stage: 'triprole',
        title: `Gateway ${props.gatewayItems.length} / Mesh ${props.meshpegItems.length}`,
        subtitle: `Formula ${props.formulaItems.length} / Scan ${props.scanEntryActiveOnly.length}`,
        eyebrow: 'Gateway',
        tone: toTone(!audit.geoTemporalBlocked && props.gatewayItems.length > 0, audit.geoTemporalBlocked),
        fields: [
          buildField('Gateway records', props.gatewayItems.length),
          buildField('MeshPeg records', props.meshpegItems.length),
          buildField('Formula records', props.formulaItems.length),
          buildField('Scan entries', props.scanEntryActiveOnly.length),
          buildField('Geo gate', audit.geoTemporalBlocked ? 'Blocked' : 'Pass'),
          buildField('Settlement risk', formatNumber(props.settlementRiskScore)),
        ],
      },
      ...evidenceCards,
      {
        id: 'finalproof-hash',
        stage: 'finalproof',
        title: props.disputeOpen ? `Dispute open ${props.disputeProofShort || '-'}` : asText(asset.totalHash, 'Final hash pending'),
        subtitle: `Completeness ${formatPercent(props.evidenceCompletenessScore)} / Risk ${formatNumber(props.docpegRiskScore)}`,
        eyebrow: 'Hash',
        tone: props.disputeOpen ? 'conflict' : toTone(Boolean(asset.totalHash)),
        fields: [
          buildField('Final hash', asset.totalHash),
          buildField('Output proof', asset.finalProofId),
          buildField('Completeness', formatPercent(props.evidenceCompletenessScore)),
          buildField('Risk score', formatNumber(props.docpegRiskScore)),
          buildField('Dispute state', props.disputeOpen ? 'Open' : 'Clear'),
          buildField('Allowed drift', `${props.consensusAllowedAbsText || '-'} / ${props.consensusAllowedPctText || '-'}`),
        ],
      },
      {
        id: 'finalproof-sealing',
        stage: 'finalproof',
        title: props.sealingPatternId || 'Seal pattern pending',
        subtitle: props.sealingScanHint || 'Open drawer for DID, GPS, and microtext',
        eyebrow: 'Seal',
        tone: toTone(Boolean(props.sealingPatternId)),
        fields: [
          buildField('Pattern ID', props.sealingPatternId),
          buildField('Scan hint', props.sealingScanHint),
          buildField('ASCII seal', props.sealingRows.join(' | ') || '-'),
          buildField('Microtext', props.sealingMicrotext.join(' | ') || '-'),
          buildField('ERP receipt', props.erpReceiptDoc?.file_name || props.erpReceiptDoc?.doc_uri),
          buildField('ERP state', props.erpRetryMsg || 'Ready'),
        ],
      },
      {
        id: 'finalproof-dispute',
        stage: 'finalproof',
        title: props.disputeOpen ? `Blocked by ${formatNumber(props.disputeDeviation)}` : 'Consensus clear',
        subtitle: props.disputeOpen ? `Proof ${props.disputeProofShort || '-'}` : 'No open dispute',
        eyebrow: 'Consensus',
        tone: props.disputeOpen || Boolean(props.consensusConflict) ? 'conflict' : 'certified',
        fields: [
          buildField('Dispute open', props.disputeOpen ? 'Yes' : 'No'),
          buildField('Proof', props.disputeProof),
          buildField('Deviation', formatNumber(props.disputeDeviation)),
          buildField('Deviation pct', formatPercent(props.disputeDeviationPct)),
          buildField('Allowed abs', props.disputeAllowedAbs == null ? '-' : formatNumber(props.disputeAllowedAbs)),
          buildField('Allowed pct', props.disputeAllowedPct == null ? '-' : formatPercent(props.disputeAllowedPct)),
          buildField('Conflict samples', props.disputeValues.length ? props.disputeValues.map((item) => formatNumber(item)).join(' / ') : '-'),
          buildField('Conflict payload', JSON.stringify(dispute)),
        ],
      },
      ...docCards,
      {
        id: 'finalproof-graph',
        stage: 'finalproof',
        title: 'Causal track',
        subtitle: props.evidenceGraphNodes.map((item) => item.label).join(' -> '),
        eyebrow: 'Flow',
        tone: toTone(props.evidenceGraphNodes.some((item) => item.tone === 'ok')),
        fields: props.evidenceGraphNodes.map((item) => ({
          label: item.label,
          value: `${item.subtitle || '-'} / ${item.tone}`,
        })),
      },
      {
        id: 'finalproof-receipt',
        stage: 'finalproof',
        title: props.erpReceiptDoc ? asText(props.erpReceiptDoc.file_name, 'ERP receipt') : 'ERP receipt pending',
        subtitle: props.erpRetryMsg || asText(props.erpReceiptDoc?.doc_uri || props.erpReceiptDoc?.url, 'Waiting for ERPnext'),
        eyebrow: 'ERP',
        tone: props.erpRetryMsg ? 'pending' : props.erpReceiptDoc ? 'certified' : 'pending',
        focusKind: props.erpReceiptDoc ? 'document' : undefined,
        focusId: props.erpReceiptDoc ? asText(props.erpReceiptDoc.id || props.erpReceiptDoc.file_name, '') : undefined,
        fields: [
          buildField('Receipt file', props.erpReceiptDoc?.file_name),
          buildField('Doc URI', props.erpReceiptDoc?.doc_uri || props.erpReceiptDoc?.url),
          buildField('Push state', props.erpRetryMsg || 'Done'),
          buildField('Retrying', props.erpRetrying ? 'Yes' : 'No'),
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
          <div className="text-[11px] font-semibold uppercase tracking-[0.22em] text-sky-300">Evidence Center</div>
          <div className="mt-2 text-lg font-semibold text-slate-50">Causal pipeline from genesis ledger to final proof</div>
          <div className="mt-1 text-sm text-slate-400">{project.activePath || project.active?.uri || '-'} / lifecycle {project.lifecycle}</div>
        </div>
        <div className="flex flex-wrap items-center gap-2 text-[11px]">
          <span className={`rounded-full border px-2.5 py-1 ${audit.gateStats.dualQualified ? 'border-emerald-500/60 bg-emerald-950/30 text-emerald-200' : 'border-amber-500/60 bg-amber-950/30 text-amber-200'}`}>
            Dual gate {audit.gateStats.dualQualified ? 'pass' : 'blocked'}
          </span>
          <span className={`rounded-full border px-2.5 py-1 ${props.disputeOpen ? 'border-rose-500/60 bg-rose-950/30 text-rose-200' : 'border-slate-600/60 bg-slate-900/50 text-slate-300'}`}>
            Dispute {props.disputeOpen ? 'open' : 'clear'}
          </span>
          <span className="rounded-full border border-sky-500/40 bg-sky-950/20 px-2.5 py-1 text-sky-200">
            Evidence {props.filteredEvidenceItems.length} / Docs {props.filteredDocs.length}
          </span>
        </div>
      </div>

      <div className="mt-4 grid gap-3 rounded-2xl border border-slate-700/60 bg-slate-950/40 p-3 lg:grid-cols-[minmax(0,1fr)_auto]">
        <div className="grid gap-3 md:grid-cols-2 xl:grid-cols-4">
          <input
            value={props.evidenceQuery}
            onChange={(event) => props.onEvidenceQueryChange(event.target.value)}
            placeholder="Search proof, doc, or hash"
            className="rounded-xl border border-slate-700 bg-slate-950/60 px-3 py-2 text-sm text-slate-100 outline-none transition focus:border-sky-500"
          />
          <select
            value={props.evidenceScope}
            onChange={(event) => props.onEvidenceScopeChange(event.target.value as EvidenceScope)}
            className="rounded-xl border border-slate-700 bg-slate-950/60 px-3 py-2 text-sm text-slate-100 outline-none"
          >
            <option value="item">By node</option>
            <option value="smu">By SMU</option>
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
            <option value="all">All</option>
            <option value="matched">Matched</option>
            <option value="unmatched">Pending link</option>
            <option value="image">Images only</option>
          </select>
        </div>
        <div className="flex flex-wrap justify-end gap-2">
          <button type="button" onClick={props.onLoadEvidenceCenter} className={`px-3 py-2 text-sm ${props.btnBlueCls}`}>Refresh</button>
          <button type="button" onClick={props.onExportEvidenceCenter} className={`px-3 py-2 text-sm ${props.btnBlueCls}`}>Export report</button>
          <button type="button" onClick={props.onExportEvidenceCenterCsv} className={`px-3 py-2 text-sm ${props.btnBlueCls}`}>Export CSV</button>
          <button type="button" onClick={props.onDownloadEvidenceCenterPackage} disabled={props.evidenceZipDownloading} className={`px-3 py-2 text-sm disabled:opacity-60 ${props.btnBlueCls}`}>
            {props.evidenceZipDownloading ? 'Packing...' : 'Download package'}
          </button>
          <button type="button" onClick={props.onRetryErpnextPush} disabled={props.erpRetrying} className={`px-3 py-2 text-sm disabled:opacity-60 ${props.btnBlueCls}`}>
            {props.erpRetrying ? 'Retrying...' : 'Retry ERP'}
          </button>
        </div>
      </div>

      {(props.evidenceCenterLoading || props.evidenceCenterError) && (
        <div className={`mt-3 rounded-2xl border px-3 py-2 text-sm ${props.evidenceCenterError ? 'border-rose-500/60 bg-rose-950/30 text-rose-200' : 'border-sky-500/50 bg-sky-950/20 text-sky-200'}`}>
          {props.evidenceCenterError || 'Evidence center loading...'}
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
                      {stageCounts.get(stage.id) || 0} cards
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
                          <span>{card.fields[0]?.label || 'Detail'}</span>
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
              <div className="text-[11px] uppercase tracking-[0.18em] text-slate-400">Flow Snapshot</div>
              <div className="mt-1 text-sm font-semibold text-slate-100">Evidence page {props.evidencePageSafe} / {props.totalEvidencePages}</div>
            </div>
            <div className="flex items-center gap-2">
              <button
                type="button"
                onClick={() => props.onEvidencePageChange(Math.max(1, props.evidencePageSafe - 1))}
                disabled={props.evidencePageSafe <= 1}
                className="rounded-lg border border-slate-700 bg-slate-950/60 px-3 py-1.5 text-xs text-slate-200 disabled:opacity-40"
              >
                Prev
              </button>
              <button
                type="button"
                onClick={() => props.onEvidencePageChange(Math.min(props.totalEvidencePages, props.evidencePageSafe + 1))}
                disabled={props.evidencePageSafe >= props.totalEvidencePages}
                className="rounded-lg border border-slate-700 bg-slate-950/60 px-3 py-1.5 text-xs text-slate-200 disabled:opacity-40"
              >
                Next
              </button>
            </div>
          </div>
          <div className="mt-3 grid gap-3 md:grid-cols-2 xl:grid-cols-3">
            {props.evidenceItemsPaged.length ? props.evidenceItemsPaged.map((item, index) => {
              const evidenceId = asText(item.id || item.hash || item.file_name || `page-${index}`)
              const label = asText(item.file_name || item.id, 'Field evidence')
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
                      {tone === 'certified' ? 'Sealed' : tone === 'conflict' ? 'Conflict' : 'Pending'}
                    </span>
                  </div>
                  <div className="mt-2 text-xs text-slate-400">Hash: {asText(item.hash || item.id)}</div>
                  <div className="mt-1 text-xs text-slate-500">GPS: {asText(item.gps_lat, '-')}, {asText(item.gps_lng, '-')}</div>
                  <div className="mt-1 text-xs text-slate-500">Time: {formatDate(item.captured_at || item.created_at)}</div>
                </button>
              )
            }) : (
              <div className="col-span-full rounded-2xl border border-dashed border-slate-700 bg-slate-950/20 px-4 py-10 text-center text-sm text-slate-500">
                No evidence matches the current filter
              </div>
            )}
          </div>
        </div>

        <aside className="rounded-[24px] border border-slate-700/70 bg-slate-950/45 p-4 shadow-[inset_0_1px_0_rgba(148,163,184,0.08)]">
          <div className="flex items-start justify-between gap-3">
            <div>
              <div className="text-[11px] uppercase tracking-[0.18em] text-slate-400">Evidence Drawer</div>
              <div className="mt-1 text-base font-semibold text-slate-50">{selectedCard?.title || 'No card selected'}</div>
              <div className="mt-1 text-sm text-slate-400">{selectedCard?.subtitle || 'Select a card from the pipeline to inspect details'}</div>
            </div>
            {selectedCard && (
              <button
                type="button"
                onClick={() => props.onCopyText('evidence-card', `${selectedCard.title} ${selectedCard.subtitle || ''}`)}
                className="rounded-lg border border-slate-700 bg-slate-950/60 px-3 py-1.5 text-xs text-slate-200"
              >
                Copy summary
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
            <div className="text-[11px] uppercase tracking-[0.18em] text-slate-400">Context Penetration</div>
            <div className="text-sm text-slate-200">Executor DID: {identity.executorDid || '-'}</div>
            <div className="text-sm text-slate-200">Supervisor DID: {identity.supervisorDid || '-'}</div>
            <div className="text-sm text-slate-200">Owner DID: {identity.ownerDid || '-'}</div>
            <div className="text-sm text-slate-200">Gatekeeper: {audit.gateReason || 'No blocker'}</div>
            <div className="text-sm text-slate-200">Balance: {audit.exceedBalance ? 'Insufficient, offset required' : 'Available'}</div>
          </div>

          {props.disputeOpen && (
            <button
              type="button"
              onClick={() => props.onOpenDispute(props.disputeProof)}
              className="mt-4 w-full rounded-xl border border-rose-500/60 bg-rose-950/30 px-3 py-2 text-sm font-semibold text-rose-100 transition hover:bg-rose-950/45"
            >
              Open dispute proof {props.disputeProofShort || ''}
            </button>
          )}
        </aside>
      </div>
    </section>
  )
}
