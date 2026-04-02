import { useState } from 'react'
import type { Dispatch, SetStateAction } from 'react'

import type { EvidenceCenterPayload } from './types'

type DisputeResult = 'PASS' | 'REJECT'

type UseSovereignWorkbenchLocalStateArgs = {
  apiProjectUri: string
  displayProjectUri: string
}

export type SovereignWorkbenchLocalState = {
  ctx: Record<string, unknown> | null
  setCtx: Dispatch<SetStateAction<Record<string, unknown> | null>>
  loadingCtx: boolean
  setLoadingCtx: Dispatch<SetStateAction<boolean>>
  contextError: string
  setContextError: Dispatch<SetStateAction<string>>
  form: Record<string, string>
  setForm: Dispatch<SetStateAction<Record<string, string>>>
  compType: string
  setCompType: Dispatch<SetStateAction<string>>
  sampleId: string
  setSampleId: Dispatch<SetStateAction<string>>
  claimQty: string
  setClaimQty: Dispatch<SetStateAction<string>>
  executorDid: string
  setExecutorDid: Dispatch<SetStateAction<string>>
  supervisorDid: string
  setSupervisorDid: Dispatch<SetStateAction<string>>
  ownerDid: string
  setOwnerDid: Dispatch<SetStateAction<string>>
  lat: string
  setLat: Dispatch<SetStateAction<string>>
  lng: string
  setLng: Dispatch<SetStateAction<string>>
  evidenceCenter: EvidenceCenterPayload | null
  setEvidenceCenter: Dispatch<SetStateAction<EvidenceCenterPayload | null>>
  evidenceCenterLoading: boolean
  setEvidenceCenterLoading: Dispatch<SetStateAction<boolean>>
  evidenceCenterError: string
  setEvidenceCenterError: Dispatch<SetStateAction<string>>
  erpRetrying: boolean
  setErpRetrying: Dispatch<SetStateAction<boolean>>
  erpRetryMsg: string
  setErpRetryMsg: Dispatch<SetStateAction<string>>
  fingerprintOpen: boolean
  setFingerprintOpen: Dispatch<SetStateAction<boolean>>
  draftStamp: string
  setDraftStamp: Dispatch<SetStateAction<string>>
  disputeProofId: string
  setDisputeProofId: Dispatch<SetStateAction<string>>
  disputeResolutionNote: string
  setDisputeResolutionNote: Dispatch<SetStateAction<string>>
  disputeResult: DisputeResult
  setDisputeResult: Dispatch<SetStateAction<DisputeResult>>
  copiedMsg: string
  setCopiedMsg: Dispatch<SetStateAction<string>>
  traceOpen: boolean
  setTraceOpen: Dispatch<SetStateAction<boolean>>
  docModalOpen: boolean
  setDocModalOpen: Dispatch<SetStateAction<boolean>>
  pdfRenderError: string
  setPdfRenderError: Dispatch<SetStateAction<string>>
  pdfRenderLoading: boolean
  setPdfRenderLoading: Dispatch<SetStateAction<boolean>>
  showAdvancedConsensus: boolean
  setShowAdvancedConsensus: Dispatch<SetStateAction<boolean>>
  showAcceptanceAdvanced: boolean
  setShowAcceptanceAdvanced: Dispatch<SetStateAction<boolean>>
  specdictProjectUris: string
  setSpecdictProjectUris: Dispatch<SetStateAction<string>>
  specdictMinSamples: string
  setSpecdictMinSamples: Dispatch<SetStateAction<string>>
  specdictNamespace: string
  setSpecdictNamespace: Dispatch<SetStateAction<string>>
  specdictCommit: boolean
  setSpecdictCommit: Dispatch<SetStateAction<boolean>>
  arRadius: string
  setArRadius: Dispatch<SetStateAction<string>>
  arLimit: string
  setArLimit: Dispatch<SetStateAction<string>>
  p2pNodeId: string
  p2pPeers: string
  setP2pPeers: Dispatch<SetStateAction<string>>
  p2pAutoSync: boolean
  setP2pAutoSync: Dispatch<SetStateAction<boolean>>
  p2pLastSync: string
  setP2pLastSync: Dispatch<SetStateAction<string>>
  docFinalPassphrase: string
  setDocFinalPassphrase: Dispatch<SetStateAction<string>>
  docFinalIncludeUnsettled: boolean
  setDocFinalIncludeUnsettled: Dispatch<SetStateAction<boolean>>
  nowTick: number
  setNowTick: Dispatch<SetStateAction<number>>
}

export function useSovereignWorkbenchLocalState({
  apiProjectUri,
  displayProjectUri,
}: UseSovereignWorkbenchLocalStateArgs): SovereignWorkbenchLocalState {
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
  const [evidenceCenter, setEvidenceCenter] = useState<EvidenceCenterPayload | null>(null)
  const [evidenceCenterLoading, setEvidenceCenterLoading] = useState(false)
  const [evidenceCenterError, setEvidenceCenterError] = useState('')
  const [erpRetrying, setErpRetrying] = useState(false)
  const [erpRetryMsg, setErpRetryMsg] = useState('')
  const [fingerprintOpen, setFingerprintOpen] = useState(false)
  const [draftStamp, setDraftStamp] = useState('')
  const [disputeProofId, setDisputeProofId] = useState('')
  const [disputeResolutionNote, setDisputeResolutionNote] = useState('')
  const [disputeResult, setDisputeResult] = useState<DisputeResult>('PASS')
  const [copiedMsg, setCopiedMsg] = useState('')
  const [traceOpen, setTraceOpen] = useState(false)
  const [docModalOpen, setDocModalOpen] = useState(false)
  const [pdfRenderError, setPdfRenderError] = useState('')
  const [pdfRenderLoading, setPdfRenderLoading] = useState(false)
  const [showAdvancedConsensus, setShowAdvancedConsensus] = useState(false)
  const [showAcceptanceAdvanced, setShowAcceptanceAdvanced] = useState(false)
  const [specdictProjectUris, setSpecdictProjectUris] = useState(apiProjectUri || displayProjectUri || '')
  const [specdictMinSamples, setSpecdictMinSamples] = useState('5')
  const [specdictNamespace, setSpecdictNamespace] = useState('v://global/templates')
  const [specdictCommit, setSpecdictCommit] = useState(false)
  const [arRadius, setArRadius] = useState('80')
  const [arLimit, setArLimit] = useState('50')
  const [p2pNodeId] = useState(() => `node-${Math.random().toString(16).slice(2, 8)}`)
  const [p2pPeers, setP2pPeers] = useState('')
  const [p2pAutoSync, setP2pAutoSync] = useState(true)
  const [p2pLastSync, setP2pLastSync] = useState('')
  const [docFinalPassphrase, setDocFinalPassphrase] = useState('')
  const [docFinalIncludeUnsettled, setDocFinalIncludeUnsettled] = useState(false)
  const [nowTick, setNowTick] = useState(Date.now())

  return {
    ctx,
    setCtx,
    loadingCtx,
    setLoadingCtx,
    contextError,
    setContextError,
    form,
    setForm,
    compType,
    setCompType,
    sampleId,
    setSampleId,
    claimQty,
    setClaimQty,
    executorDid,
    setExecutorDid,
    supervisorDid,
    setSupervisorDid,
    ownerDid,
    setOwnerDid,
    lat,
    setLat,
    lng,
    setLng,
    evidenceCenter,
    setEvidenceCenter,
    evidenceCenterLoading,
    setEvidenceCenterLoading,
    evidenceCenterError,
    setEvidenceCenterError,
    erpRetrying,
    setErpRetrying,
    erpRetryMsg,
    setErpRetryMsg,
    fingerprintOpen,
    setFingerprintOpen,
    draftStamp,
    setDraftStamp,
    disputeProofId,
    setDisputeProofId,
    disputeResolutionNote,
    setDisputeResolutionNote,
    disputeResult,
    setDisputeResult,
    copiedMsg,
    setCopiedMsg,
    traceOpen,
    setTraceOpen,
    docModalOpen,
    setDocModalOpen,
    pdfRenderError,
    setPdfRenderError,
    pdfRenderLoading,
    setPdfRenderLoading,
    showAdvancedConsensus,
    setShowAdvancedConsensus,
    showAcceptanceAdvanced,
    setShowAcceptanceAdvanced,
    specdictProjectUris,
    setSpecdictProjectUris,
    specdictMinSamples,
    setSpecdictMinSamples,
    specdictNamespace,
    setSpecdictNamespace,
    specdictCommit,
    setSpecdictCommit,
    arRadius,
    setArRadius,
    arLimit,
    setArLimit,
    p2pNodeId,
    p2pPeers,
    setP2pPeers,
    p2pAutoSync,
    setP2pAutoSync,
    p2pLastSync,
    setP2pLastSync,
    docFinalPassphrase,
    setDocFinalPassphrase,
    docFinalIncludeUnsettled,
    setDocFinalIncludeUnsettled,
    nowTick,
    setNowTick,
  }
}
