import { useCallback, useState, type Dispatch, type SetStateAction } from 'react'

type EventLog = Array<Record<string, unknown>>

type ReplayPatch = {
  chain_status: string
  proof_id: string
  proof_hash: string
  action: string
}

type UseEvidenceEventLogsResult = {
  scanEntryLog: EventLog
  meshpegLog: EventLog
  formulaLog: EventLog
  gatewayLog: EventLog
  setScanEntryLog: Dispatch<SetStateAction<EventLog>>
  setMeshpegLog: Dispatch<SetStateAction<EventLog>>
  setFormulaLog: Dispatch<SetStateAction<EventLog>>
  setGatewayLog: Dispatch<SetStateAction<EventLog>>
  appendScanEntryLog: (entry: Record<string, unknown>) => void
  appendMeshpegLog: (entry: Record<string, unknown>) => void
  appendFormulaLog: (entry: Record<string, unknown>) => void
  appendGatewayLog: (entry: Record<string, unknown>) => void
  reconcileReplayResults: (results: Array<Record<string, unknown>>) => boolean
}

function buildReplayPatchMap(results: Array<Record<string, unknown>>) {
  const onchainMap = new Map<string, ReplayPatch>()
  results.forEach((row) => {
    if (!row || row.ok !== true) return
    const packetId = String(row.offline_packet_id || '')
    const result = ((row.result || {}) as Record<string, unknown>)
    const action = String(result.action || row.action || '')
    if (!packetId || !['scan.entry', 'meshpeg.verify', 'formula.price', 'gateway.sync'].includes(action)) return
    onchainMap.set(packetId, {
      chain_status: 'onchain',
      proof_id: String(result.output_proof_id || ''),
      proof_hash: String(result.proof_hash || ''),
      action,
    })
  })
  return onchainMap
}

function patchReplayLog(
  prev: EventLog,
  onchainMap: Map<string, ReplayPatch>,
  action: string,
) {
  return prev.map((item) => {
    const key = String(item.offline_packet_id || '')
    const patch = onchainMap.get(key)
    if (!patch || patch.action !== action) return item
    return { ...item, ...patch }
  })
}

export function useEvidenceEventLogs(): UseEvidenceEventLogsResult {
  const [scanEntryLog, setScanEntryLog] = useState<EventLog>([])
  const [meshpegLog, setMeshpegLog] = useState<EventLog>([])
  const [formulaLog, setFormulaLog] = useState<EventLog>([])
  const [gatewayLog, setGatewayLog] = useState<EventLog>([])

  const appendScanEntryLog = useCallback((entry: Record<string, unknown>) => {
    setScanEntryLog((prev) => [entry, ...prev])
  }, [])

  const appendMeshpegLog = useCallback((entry: Record<string, unknown>) => {
    setMeshpegLog((prev) => [entry, ...prev])
  }, [])

  const appendFormulaLog = useCallback((entry: Record<string, unknown>) => {
    setFormulaLog((prev) => [entry, ...prev])
  }, [])

  const appendGatewayLog = useCallback((entry: Record<string, unknown>) => {
    setGatewayLog((prev) => [entry, ...prev])
  }, [])

  const reconcileReplayResults = useCallback((results: Array<Record<string, unknown>>) => {
    const onchainMap = buildReplayPatchMap(results)
    if (!onchainMap.size) return false
    setScanEntryLog((prev) => patchReplayLog(prev, onchainMap, 'scan.entry'))
    setMeshpegLog((prev) => patchReplayLog(prev, onchainMap, 'meshpeg.verify'))
    setFormulaLog((prev) => patchReplayLog(prev, onchainMap, 'formula.price'))
    setGatewayLog((prev) => patchReplayLog(prev, onchainMap, 'gateway.sync'))
    return true
  }, [])

  return {
    scanEntryLog,
    meshpegLog,
    formulaLog,
    gatewayLog,
    setScanEntryLog,
    setMeshpegLog,
    setFormulaLog,
    setGatewayLog,
    appendScanEntryLog,
    appendMeshpegLog,
    appendFormulaLog,
    appendGatewayLog,
    reconcileReplayResults,
  }
}
