import type { MutableRefObject } from 'react'
import { useCallback } from 'react'

import { shaJson } from '../../fileUtils'
import { toApiUri } from '../../treeUtils'
import type { OfflinePacketType } from '../../types'

type SignRole = 'contractor' | 'supervisor' | 'owner'

type UseWorkbenchActionsArgs = {
  sign: {
    setSignFocus: (role: SignRole) => void
    contractorAnchorRef: MutableRefObject<HTMLDivElement | null>
    supervisorAnchorRef: MutableRefObject<HTMLDivElement | null>
    ownerAnchorRef: MutableRefObject<HTMLDivElement | null>
  }
  clipboard: {
    setCopiedMsg: (value: string) => void
    showToast: (message: string) => void
  }
  offline: {
    activeUri: string
    apiProjectUri: string
    compType: string
    deltaAmount: string
    deltaReason: string
    evidence: Array<{ hash: string }>
    executorDid: string
    form: Record<string, string>
    inputProofId: string
    lat: string
    lng: string
    offlineActorId: string
    offlineType: OfflinePacketType
    queueOfflinePacket: (packet: Record<string, unknown>, meta: { actorId: string; did: string }) => Promise<unknown>
    sampleId: string
  }
  scanEntry: {
    activeUri: string
    apiProjectUri: string
    inputProofId: string
    executorDid: string
    lat: string
    lng: string
    offlineActorId: string
    queueOfflinePacket: (packet: Record<string, unknown>, meta: { actorId: string; did: string }) => Promise<unknown> | void
    geoDistance: number | null
    geoRadiusM: number | null | undefined
    temporalWindow: { start: number; end: number } | null
  }
  triprole: {
    activeUri: string
    apiProjectUri: string
    inputProofId: string
    executorDid: string
    lat: string
    lng: string
    offlineActorId: string
    queueOfflinePacket: (packet: Record<string, unknown>, meta: { actorId: string; did: string }) => Promise<unknown> | void
  }
}

export function useSovereignWorkbenchActions({
  sign,
  clipboard,
  offline,
  scanEntry,
  triprole,
}: UseWorkbenchActionsArgs) {
  const scrollToSign = useCallback((role: SignRole) => {
    sign.setSignFocus(role)
    const target = role === 'contractor'
      ? sign.contractorAnchorRef.current
      : role === 'supervisor'
        ? sign.supervisorAnchorRef.current
        : sign.ownerAnchorRef.current
    if (!target) return
    target.scrollIntoView({ behavior: 'smooth', block: 'center' })
  }, [sign])

  const copyText = useCallback(async (label: string, value: string) => {
    if (!value) return
    try {
      await navigator.clipboard.writeText(value)
      clipboard.setCopiedMsg(`${label}已复制`)
      window.setTimeout(() => clipboard.setCopiedMsg(''), 1500)
    } catch {
      clipboard.showToast('复制失败')
    }
  }, [clipboard])

  const sealOfflinePacket = useCallback(async () => {
    if (!offline.activeUri) {
      clipboard.showToast('请先选择一个细目')
      return
    }
    if (!offline.apiProjectUri) {
      clipboard.showToast('项目 URI 缺失')
      return
    }
    const now = new Date().toISOString()
    const packetId = `offline-${Date.now()}-${Math.random().toString(16).slice(2, 8)}`
    let packet: Record<string, unknown> | null = null
    if (offline.offlineType === 'variation.apply') {
      const delta = Number(String(offline.deltaAmount || '').replace(/,/g, '').trim())
      if (!Number.isFinite(delta) || Math.abs(delta) < 1e-9) {
        clipboard.showToast('请输入有效的变更数量')
        return
      }
      packet = {
        packet_type: 'variation.apply',
        offline_packet_id: packetId,
        local_created_at: now,
        project_uri: offline.apiProjectUri,
        boq_item_uri: toApiUri(offline.activeUri),
        delta_amount: delta,
        reason: offline.deltaReason,
        sample_id: offline.sampleId,
        executor_uri: `${offline.apiProjectUri.replace(/\/$/, '')}/role/contractor/mobile/`,
        executor_did: offline.executorDid,
        executor_role: 'TRIPROLE',
        geo_location: { lat: Number(offline.lat), lng: Number(offline.lng) },
        server_timestamp_proof: { ntp_server: 'offline', captured_at: now, proof_hash: `offline-${now}` },
      }
    } else {
      if (!offline.inputProofId) {
        clipboard.showToast('当前细目缺少可消费 UTXO')
        return
      }
      const measurement: Record<string, number | string> = {}
      Object.entries(offline.form).forEach(([key, value]) => {
        const numeric = Number(value)
        measurement[key] = Number.isFinite(numeric) ? numeric : value
      })
      const snappegPayload = {
        project_uri: offline.apiProjectUri,
        input_proof_id: offline.inputProofId,
        boq_item_uri: toApiUri(offline.activeUri),
        measurement,
        sample_id: offline.sampleId,
        geo_location: { lat: Number(offline.lat), lng: Number(offline.lng) },
        server_timestamp_proof: { ntp_server: 'offline', captured_at: now },
        executor_did: offline.executorDid,
        evidence_hashes: offline.evidence.map((item) => item.hash),
      }
      const snappegHash = await shaJson(snappegPayload)
      packet = {
        packet_type: 'triprole.execute',
        action: 'quality.check',
        offline_packet_id: packetId,
        local_created_at: now,
        project_uri: offline.apiProjectUri,
        boq_item_uri: toApiUri(offline.activeUri),
        input_proof_id: offline.inputProofId,
        executor_uri: `${offline.apiProjectUri.replace(/\/$/, '')}/role/contractor/mobile/`,
        executor_did: offline.executorDid,
        executor_role: 'TRIPROLE',
        payload: {
          component_type: offline.compType,
          measurement,
          snappeg_payload_hash: snappegHash,
          sample_id: offline.sampleId,
        },
        geo_location: { lat: Number(offline.lat), lng: Number(offline.lng) },
        server_timestamp_proof: { ntp_server: 'offline', captured_at: now, proof_hash: `offline-${now}` },
      }
    }
    if (!packet) return
    await offline.queueOfflinePacket(packet, {
      actorId: offline.offlineActorId,
      did: offline.executorDid,
    })
    clipboard.showToast('离线包已封存并加入重放队列')
  }, [clipboard, offline])

  const enqueueScanEntryPacket = useCallback((status: 'ok' | 'blocked', tokenHash: string, nowIso: string, tokenPresent: boolean) => {
    if (!scanEntry.activeUri || !scanEntry.apiProjectUri) return
    const packetId = `scan-entry-${Date.now()}-${Math.random().toString(16).slice(2, 8)}`
    const packet = {
      packet_type: 'triprole.execute',
      action: 'scan.entry',
      offline_packet_id: packetId,
      local_created_at: nowIso,
      project_uri: scanEntry.apiProjectUri,
      boq_item_uri: toApiUri(scanEntry.activeUri),
      input_proof_id: String(scanEntry.inputProofId || ''),
      executor_uri: `${scanEntry.apiProjectUri.replace(/\/$/, '')}/role/contractor/mobile/`,
      executor_did: scanEntry.executorDid,
      executor_role: 'TRIPROLE',
      payload: {
        status,
        token_hash: tokenHash || null,
        token_present: tokenPresent,
        scan_entry_at: nowIso,
        geo_distance_m: scanEntry.geoDistance ?? null,
        geo_radius_m: scanEntry.geoRadiusM ?? null,
        temporal_window: scanEntry.temporalWindow
          ? { start: scanEntry.temporalWindow.start, end: scanEntry.temporalWindow.end }
          : null,
      },
      geo_location: { lat: Number(scanEntry.lat), lng: Number(scanEntry.lng) },
      server_timestamp_proof: { ntp_server: 'offline', captured_at: nowIso, proof_hash: `offline-${nowIso}` },
    }
    void scanEntry.queueOfflinePacket(packet, {
      actorId: scanEntry.offlineActorId,
      did: scanEntry.executorDid,
    })
    return packetId
  }, [scanEntry])

  const enqueueTriprolePacket = useCallback((action: string, payload: Record<string, unknown>, result?: string) => {
    if (!triprole.activeUri || !triprole.apiProjectUri || !triprole.inputProofId) return ''
    const packetId = `triprole-${Date.now()}-${Math.random().toString(16).slice(2, 8)}`
    const nowIso = new Date().toISOString()
    const packet = {
      packet_type: 'triprole.execute',
      action,
      offline_packet_id: packetId,
      local_created_at: nowIso,
      project_uri: triprole.apiProjectUri,
      boq_item_uri: toApiUri(triprole.activeUri),
      input_proof_id: triprole.inputProofId,
      executor_uri: `${triprole.apiProjectUri.replace(/\/$/, '')}/role/contractor/mobile/`,
      executor_did: triprole.executorDid,
      executor_role: 'TRIPROLE',
      result: result || undefined,
      payload,
      geo_location: { lat: Number(triprole.lat), lng: Number(triprole.lng) },
      server_timestamp_proof: { ntp_server: 'offline', captured_at: nowIso, proof_hash: `offline-${nowIso}` },
    }
    void triprole.queueOfflinePacket(packet, {
      actorId: triprole.offlineActorId,
      did: triprole.executorDid,
    })
    return packetId
  }, [triprole])

  return {
    scrollToSign,
    copyText,
    sealOfflinePacket,
    enqueueScanEntryPacket,
    enqueueTriprolePacket,
  }
}

