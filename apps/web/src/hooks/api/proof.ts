import { useRequest } from './base'
import { useProofCore } from './proof/core'
import { useProofExecution } from './proof/execution'
import { useProofGovernance } from './proof/governance'
import { useProofSmu } from './proof/smu'

export function useProof() {
  const { request, loading } = useRequest()
  const core = useProofCore(request)
  const smu = useProofSmu(request)
  const governance = useProofGovernance(request)
  const execution = useProofExecution(request)

  return {
    ...core,
    ...smu,
    ...governance,
    ...execution,
    loading,
  }
}
