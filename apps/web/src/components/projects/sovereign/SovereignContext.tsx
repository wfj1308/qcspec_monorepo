import { createContext, useContext  } from 'react'
import type {
  ActiveGenesisSummary,
  EvidenceCenterPayload,
  GateStats,
  NormResolutionState,
  SpuBadge,
  SpuKind,
  SovereignLifecycleStatus,
  SummaryMetrics,
  TreeNode,
} from './types'

export type SovereignProjectState = {
  projectUri: string
  apiProjectUri: string
  displayProjectUri: string
  projectId: string
  active: TreeNode | null
  activeUri: string
  activePath: string
  boundSpu: string
  isContractSpu: boolean
  spuKind: SpuKind
  spuBadge: SpuBadge
  stepLabel: string
  lifecycle: SovereignLifecycleStatus
  nodePathMap: Map<string, string>
}

export type SovereignIdentityState = {
  dtoRole: string
  roleAllowed: boolean
  executorDid: string
  supervisorDid: string
  ownerDid: string
}

export type SovereignAssetState = {
  summary: SummaryMetrics
  activeGenesisSummary: ActiveGenesisSummary
  baselineTotal: number
  availableTotal: number
  effectiveSpent: number
  effectiveClaimQtyValue: number
  inputProofId: string
  finalProofId: string
  totalHash: string
  verifyUri: string
  evidenceCenter: EvidenceCenterPayload | null
}

export type SovereignAuditState = {
  gateStats: GateStats
  gateReason: string
  exceedBalance: boolean
  snappegReady: boolean
  geoTemporalBlocked: boolean
  normResolution: NormResolutionState
  disputeOpen: boolean
  disputeProof: string
  disputeArbiterRole: string
  archiveLocked: boolean
}

export type ProjectSovereignContextValue = {
  project: SovereignProjectState
  identity: SovereignIdentityState
  asset: SovereignAssetState
  audit: SovereignAuditState
}

const ProjectSovereignContext = createContext<ProjectSovereignContextValue | null>(null)

type ProviderProps = {
  value: ProjectSovereignContextValue
  children: React.ReactNode
}

export function ProjectSovereignProvider({ value, children }: ProviderProps) {
  return (
    <ProjectSovereignContext.Provider value={value}>
      {children}
    </ProjectSovereignContext.Provider>
  )
}

export function useProjectSovereign() {
  const ctx = useContext(ProjectSovereignContext)
  if (!ctx) {
    throw new Error('useProjectSovereign must be used within ProjectSovereignProvider')
  }
  return ctx
}
