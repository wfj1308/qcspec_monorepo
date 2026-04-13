import { createContext, useContext  } from 'react'

export type SovereignWorkspaceView = 'trip' | 'audit' | 'genesis'

export type SovereignWorkspaceSnapshot = {
  activePath: string
  lifecycle: string
  activeCode: string
  activeStatus: string
  totalHash: string
  verifyUri: string
  finalProofReady: boolean
  isOnline: boolean
  offlineQueueSize: number
  disputeOpen: boolean
  disputeProof: string
  archiveLocked: boolean
}

type SovereignProjectContextValue = {
  projectId: string
  projectName: string
  projectUri: string
  workspaceView: SovereignWorkspaceView
  navigate: (view: SovereignWorkspaceView) => void
  snapshot: SovereignWorkspaceSnapshot
  setSnapshot: React.Dispatch<React.SetStateAction<SovereignWorkspaceSnapshot>>
}

const SovereignProjectContext = createContext<SovereignProjectContextValue | null>(null)

type Props = {
  value: SovereignProjectContextValue
  children: React.ReactNode
}

export function SovereignProjectProvider({ value, children }: Props) {
  return (
    <SovereignProjectContext.Provider value={value}>
      {children}
    </SovereignProjectContext.Provider>
  )
}

export function useSovereignProjectContext() {
  const ctx = useContext(SovereignProjectContext)
  if (!ctx) {
    throw new Error('useSovereignProjectContext must be used within SovereignProjectProvider')
  }
  return ctx
}

