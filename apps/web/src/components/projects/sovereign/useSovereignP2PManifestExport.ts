import { useCallback } from 'react'

import { downloadJson } from './fileUtils'

type UseSovereignP2PManifestExportArgs = {
  apiProjectUri: string
  p2pNodeId: string
  p2pPeers: string
  totalHash: string
  unitRes: Record<string, unknown> | null
  offlinePackets: Record<string, unknown>[]
  offlineSyncConflicts: number
}

export function useSovereignP2PManifestExport({
  apiProjectUri,
  p2pNodeId,
  p2pPeers,
  totalHash,
  unitRes,
  offlinePackets,
  offlineSyncConflicts,
}: UseSovereignP2PManifestExportArgs) {
  return useCallback(() => {
    const projectRoot = String((unitRes || {}).project_root_hash || (unitRes || {}).global_project_fingerprint || '')
    const payload = {
      node_id: p2pNodeId,
      project_uri: apiProjectUri,
      project_root_hash: projectRoot,
      total_proof_hash: totalHash,
      offline_packets: offlinePackets,
      offline_queue_size: offlinePackets.length,
      offline_conflicts: offlineSyncConflicts,
      peers: p2pPeers.split(/[\n,]+/).map((x) => x.trim()).filter(Boolean),
      generated_at: new Date().toISOString(),
    }
    downloadJson(`gitpeg-sync-${Date.now()}.json`, payload)
  }, [apiProjectUri, offlinePackets, offlineSyncConflicts, p2pNodeId, p2pPeers, totalHash, unitRes])
}

