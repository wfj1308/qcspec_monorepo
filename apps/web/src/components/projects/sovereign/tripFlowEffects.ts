import { useEffect, useRef } from 'react'
import type { Dispatch, SetStateAction } from 'react'

type UseTripExceedBalanceEffectArgs = {
  exceedBalance: boolean
  setDeltaModalOpen: Dispatch<SetStateAction<boolean>>
  setShowAdvancedExecution: Dispatch<SetStateAction<boolean>>
}

export function useTripExceedBalanceEffect({
  exceedBalance,
  setDeltaModalOpen,
  setShowAdvancedExecution,
}: UseTripExceedBalanceEffectArgs): void {
  useEffect(() => {
    if (exceedBalance) {
      setDeltaModalOpen(true)
      setShowAdvancedExecution(true)
      return
    }
    setDeltaModalOpen(false)
    setShowAdvancedExecution(false)
  }, [exceedBalance, setDeltaModalOpen, setShowAdvancedExecution])
}

type UseTripAutoDocEffectArgs = {
  approvedProofId: string
  hasPreviewPdf: boolean
  mockGenerating: boolean
  activeIsLeaf: boolean
  isSpecBound: boolean
  submitTripMock: () => Promise<void>
}

export function useTripAutoDocEffect({
  approvedProofId,
  hasPreviewPdf,
  mockGenerating,
  activeIsLeaf,
  isSpecBound,
  submitTripMock,
}: UseTripAutoDocEffectArgs): void {
  const autoDocTriggerRef = useRef('')

  useEffect(() => {
    if (!approvedProofId) return
    if (hasPreviewPdf) return
    if (mockGenerating) return
    if (!activeIsLeaf || !isSpecBound) return
    if (autoDocTriggerRef.current === approvedProofId) return
    autoDocTriggerRef.current = approvedProofId
    void submitTripMock()
  }, [activeIsLeaf, approvedProofId, hasPreviewPdf, isSpecBound, mockGenerating, submitTripMock])
}
