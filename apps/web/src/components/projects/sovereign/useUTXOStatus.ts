import { useMemo } from 'react'
import type { SovereignWorkspaceSnapshot } from './SovereignProjectContext'

export type UTXOStatus = 'Genesis' | 'In_Trip' | 'Pending_Supervisor' | 'Settled'

export function useUTXOStatus(snapshot: SovereignWorkspaceSnapshot): UTXOStatus {
  return useMemo(() => {
    if (snapshot.lifecycle === 'Settled' || snapshot.finalProofReady) return 'Settled'
    if (snapshot.lifecycle === 'Pending_Audit') return 'Pending_Supervisor'
    if (snapshot.lifecycle === 'In_Trip') return 'In_Trip'
    return 'Genesis'
  }, [snapshot.finalProofReady, snapshot.lifecycle])
}
