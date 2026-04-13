import type { Dispatch, SetStateAction } from 'react'

import type { Evidence, FormRow, TreeNode } from './types'
import type { SovereignTripFlowState } from './useSovereignTripFlowState'

export type GateStatsLike = {
  labQualified: boolean
  qcCompliant: boolean
  labLatestPass: string
  labLatestHash: string
}

export type TripFlowState = Pick<
  SovereignTripFlowState,
  | 'setExecuting'
  | 'setRejecting'
  | 'execRes'
  | 'setExecRes'
  | 'setSignOpen'
  | 'setSignStep'
  | 'setSigning'
  | 'signRes'
  | 'setSignRes'
  | 'mockGenerating'
  | 'setMockGenerating'
  | 'mockDocRes'
  | 'setMockDocRes'
  | 'setFreezeProof'
  | 'deltaAmount'
  | 'deltaReason'
  | 'setApplyingDelta'
  | 'setVariationRes'
  | 'setShowAdvancedExecution'
  | 'setDeltaModalOpen'
>

export type UseSovereignTripFlowArgs = {
  active: TreeNode | null
  apiProjectUri: string
  inputProofId: string
  isSpecBound: boolean
  roleAllowed: boolean
  compType: string
  form: Record<string, string>
  effectiveSchema: FormRow[]
  sampleId: string
  effectiveClaimQtyValue: number
  measuredQtyValue: number
  exceedBalance: boolean
  executorDid: string
  supervisorDid: string
  ownerDid: string
  lat: string
  lng: string
  evidence: Evidence[]
  gateStats: GateStatsLike
  geoAnchor: { lat: number; lng: number } | null
  templatePath: string
  refreshTreeFromServer: (focusCode?: string | null) => Promise<unknown>
  setNodes: Dispatch<SetStateAction<TreeNode[]>>
  setDisputeProofId: Dispatch<SetStateAction<string>>
  setShowAdvancedConsensus: Dispatch<SetStateAction<boolean>>
  consensusContractorValue: string
  consensusSupervisorValue: string
  consensusOwnerValue: string
  consensusAllowedDeviation: string
  consensusAllowedDeviationPct: string
  showToast: (message: string) => void
  smuExecute: (payload: Record<string, unknown>) => Promise<unknown>
  tripGenerateDoc: (payload: Record<string, unknown>) => Promise<unknown>
  smuSign: (payload: Record<string, unknown>) => Promise<unknown>
  smuFreeze: (payload: Record<string, unknown>) => Promise<unknown>
  applyVariationDelta: (payload: Record<string, unknown>) => Promise<unknown>
  tripState: TripFlowState
  onMockDocReady?: () => void
}

