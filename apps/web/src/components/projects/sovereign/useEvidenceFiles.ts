import { useCallback, useEffect, useState } from 'react'

import { sha } from './fileUtils'
import type { Evidence } from './types'

type UseEvidenceFilesResult = {
  evidence: Evidence[]
  evidenceName: string
  evidenceOpen: boolean
  evidenceFocus: Evidence | null
  hashing: boolean
  setEvidence: React.Dispatch<React.SetStateAction<Evidence[]>>
  setEvidenceName: React.Dispatch<React.SetStateAction<string>>
  resetEvidence: () => void
  onEvidence: (list: FileList | null) => Promise<void>
  openEvidencePreview: (item: Evidence) => void
  closeEvidencePreview: () => void
}

export function useEvidenceFiles(): UseEvidenceFilesResult {
  const [evidence, setEvidence] = useState<Evidence[]>([])
  const [evidenceName, setEvidenceName] = useState('')
  const [evidenceOpen, setEvidenceOpen] = useState(false)
  const [evidenceFocus, setEvidenceFocus] = useState<Evidence | null>(null)
  const [hashing, setHashing] = useState(false)

  useEffect(() => () => {
    evidence.forEach((item) => URL.revokeObjectURL(item.url))
  }, [evidence])

  const resetEvidence = useCallback(() => {
    setEvidence([])
    setEvidenceName('')
    setEvidenceOpen(false)
    setEvidenceFocus(null)
    setHashing(false)
  }, [])

  const onEvidence = useCallback(async (list: FileList | null) => {
    evidence.forEach((item) => URL.revokeObjectURL(item.url))
    const files = list ? Array.from(list) : []
    setEvidenceName(files.length ? files.map((file) => file.name).join('、') : '')
    if (!files.length) {
      setEvidence([])
      return
    }
    setHashing(true)
    try {
      const rows = await Promise.all(files.map(async (file) => ({
        name: file.name,
        url: URL.createObjectURL(file),
        hash: await sha(file),
        ntp: new Date().toISOString(),
      })))
      setEvidence(rows)
    } finally {
      setHashing(false)
    }
  }, [evidence])

  const openEvidencePreview = useCallback((item: Evidence) => {
    setEvidenceFocus(item)
    setEvidenceOpen(true)
  }, [])

  const closeEvidencePreview = useCallback(() => {
    setEvidenceOpen(false)
  }, [])

  return {
    evidence,
    evidenceName,
    evidenceOpen,
    evidenceFocus,
    hashing,
    setEvidence,
    setEvidenceName,
    resetEvidence,
    onEvidence,
    openEvidencePreview,
    closeEvidencePreview,
  }
}
