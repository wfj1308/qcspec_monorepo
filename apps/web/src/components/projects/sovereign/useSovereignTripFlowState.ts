import { useState } from 'react'
import type { Dispatch, SetStateAction } from 'react'

export type SovereignTripFlowState = {
  executing: boolean
  setExecuting: Dispatch<SetStateAction<boolean>>
  rejecting: boolean
  setRejecting: Dispatch<SetStateAction<boolean>>
  execRes: Record<string, unknown> | null
  setExecRes: Dispatch<SetStateAction<Record<string, unknown> | null>>
  signOpen: boolean
  setSignOpen: Dispatch<SetStateAction<boolean>>
  signStep: number
  setSignStep: Dispatch<SetStateAction<number>>
  signing: boolean
  setSigning: Dispatch<SetStateAction<boolean>>
  signRes: Record<string, unknown> | null
  setSignRes: Dispatch<SetStateAction<Record<string, unknown> | null>>
  mockGenerating: boolean
  setMockGenerating: Dispatch<SetStateAction<boolean>>
  mockDocRes: Record<string, unknown> | null
  setMockDocRes: Dispatch<SetStateAction<Record<string, unknown> | null>>
  consensusContractorValue: string
  setConsensusContractorValue: Dispatch<SetStateAction<string>>
  consensusSupervisorValue: string
  setConsensusSupervisorValue: Dispatch<SetStateAction<string>>
  consensusOwnerValue: string
  setConsensusOwnerValue: Dispatch<SetStateAction<string>>
  consensusAllowedDeviation: string
  setConsensusAllowedDeviation: Dispatch<SetStateAction<string>>
  consensusAllowedDeviationPct: string
  setConsensusAllowedDeviationPct: Dispatch<SetStateAction<string>>
  freezeProof: string
  setFreezeProof: Dispatch<SetStateAction<string>>
  signFocus: 'contractor' | 'supervisor' | 'owner' | ''
  setSignFocus: Dispatch<SetStateAction<'contractor' | 'supervisor' | 'owner' | ''>>
  deltaAmount: string
  setDeltaAmount: Dispatch<SetStateAction<string>>
  deltaReason: string
  setDeltaReason: Dispatch<SetStateAction<string>>
  applyingDelta: boolean
  setApplyingDelta: Dispatch<SetStateAction<boolean>>
  setVariationRes: Dispatch<SetStateAction<Record<string, unknown> | null>>
  variationRes: Record<string, unknown> | null
  showAdvancedExecution: boolean
  setShowAdvancedExecution: Dispatch<SetStateAction<boolean>>
  deltaModalOpen: boolean
  setDeltaModalOpen: Dispatch<SetStateAction<boolean>>
}

export function useSovereignTripFlowState(): SovereignTripFlowState {
  const [executing, setExecuting] = useState(false)
  const [rejecting, setRejecting] = useState(false)
  const [execRes, setExecRes] = useState<Record<string, unknown> | null>(null)
  const [signOpen, setSignOpen] = useState(false)
  const [signStep, setSignStep] = useState(0)
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
  const [showAdvancedExecution, setShowAdvancedExecution] = useState(false)
  const [deltaModalOpen, setDeltaModalOpen] = useState(false)

  return {
    executing,
    setExecuting,
    rejecting,
    setRejecting,
    execRes,
    setExecRes,
    signOpen,
    setSignOpen,
    signStep,
    setSignStep,
    signing,
    setSigning,
    signRes,
    setSignRes,
    mockGenerating,
    setMockGenerating,
    mockDocRes,
    setMockDocRes,
    consensusContractorValue,
    setConsensusContractorValue,
    consensusSupervisorValue,
    setConsensusSupervisorValue,
    consensusOwnerValue,
    setConsensusOwnerValue,
    consensusAllowedDeviation,
    setConsensusAllowedDeviation,
    consensusAllowedDeviationPct,
    setConsensusAllowedDeviationPct,
    freezeProof,
    setFreezeProof,
    signFocus,
    setSignFocus,
    deltaAmount,
    setDeltaAmount,
    deltaReason,
    setDeltaReason,
    applyingDelta,
    setApplyingDelta,
    variationRes,
    setVariationRes,
    showAdvancedExecution,
    setShowAdvancedExecution,
    deltaModalOpen,
    setDeltaModalOpen,
  }
}
