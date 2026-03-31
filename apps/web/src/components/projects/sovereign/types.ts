export type NodeStatus = 'Genesis' | 'Spending' | 'Settled'

export type TreeNode = {
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

export type FormRow = {
  field: string
  label: string
  operator?: string
  default?: string
  unit?: string
  point_count?: number
  point_labels?: string[]
  source_field?: string
}

export type Evidence = {
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

export type EvidenceCenterPayload = {
  ledger?: Record<string, unknown>
  timeline?: Array<Record<string, unknown>>
  documents?: Array<Record<string, unknown>>
  evidence?: Array<Record<string, unknown>>
  proofId?: string
  riskAudit?: Record<string, unknown>
  totalProofHash?: string
  evidenceSource?: string
  consensusDispute?: Record<string, unknown>
  scanEntries?: Array<Record<string, unknown>>
  meshpegEntries?: Array<Record<string, unknown>>
  formulaEntries?: Array<Record<string, unknown>>
  gatewayEntries?: Array<Record<string, unknown>>
  scope?: string
  smuId?: string
  evidenceCompleteness?: Record<string, unknown>
  settlementRiskScore?: number
  assetOrigin?: Record<string, unknown>
  assetOriginStatement?: string
  didReputation?: Record<string, unknown>
  sealingTrip?: Record<string, unknown>
}

export type EvidenceFilter = 'all' | 'matched' | 'unmatched' | 'image'

export type EvidenceScope = 'item' | 'smu'

export type OfflinePacketType = 'quality.check' | 'variation.apply'

export type SummaryMetrics = {
  contract: number
  approved: number
  design: number
  settled: number
  consumed: number
  pct: number
}

export type ActiveGenesisSummary = {
  contractQty: number
  progressPct: number
  reportedPct: number
  leafCount: number
  contractDocCount: number
}

export type TreeSearchState = {
  active: boolean
  visible: Set<string>
  expanded: string[]
  matched: TreeNode[]
}

export type GateStats = {
  total: number
  pass: number
  fail: number
  pending: number
  qcStatus: string
  qcCompliant: boolean
  labStatus: string
  labQualified: boolean
  dualQualified: boolean
  labPass: number
  labTotal: number
  labLatest: string
  labLatestPass: string
  labLatestHash: string
}

export type SpuKind = 'bridge' | 'landscape' | 'contract' | 'physical'

export type SpuBadge = {
  label: string
  cls: string
}

export type EvidenceGraphNode = {
  id: string
  label: string
  subtitle: string
  tone: 'neutral' | 'ok' | 'warn'
}

export type SovereignLifecycleStatus = 'Genesis' | 'In_Trip' | 'Pending_Audit' | 'Settled'

export type NormResolutionState = {
  specBinding: string
  gateBinding: string
  normRefs: string[]
  isBound: boolean
  status: 'ready' | 'partial' | 'missing'
  message: string
}
