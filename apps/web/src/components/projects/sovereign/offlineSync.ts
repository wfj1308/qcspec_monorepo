export type PeerVectorClock = Record<string, number>
export type OfflinePacketRecord = Record<string, unknown>

const DB_NAME = 'qcspec-sovereign-offline'
const STORE_NAME = 'packets'

function isRecord(value: unknown): value is Record<string, unknown> {
  return Boolean(value) && typeof value === 'object' && !Array.isArray(value)
}

function stableValue(value: unknown): unknown {
  if (Array.isArray(value)) return value.map((item) => stableValue(item))
  if (!isRecord(value)) return value
  return Object.keys(value)
    .sort()
    .reduce<Record<string, unknown>>((acc, key) => {
      acc[key] = stableValue(value[key])
      return acc
    }, {})
}

async function sha256Hex(input: string) {
  const buf = new TextEncoder().encode(input)
  const digest = await crypto.subtle.digest('SHA-256', buf)
  return Array.from(new Uint8Array(digest)).map((b) => b.toString(16).padStart(2, '0')).join('')
}

function openOfflineDb(): Promise<IDBDatabase | null> {
  if (typeof window === 'undefined' || !('indexedDB' in window)) {
    return Promise.resolve(null)
  }
  return new Promise((resolve) => {
    try {
      const request = window.indexedDB.open(DB_NAME, 1)
      request.onupgradeneeded = () => {
        const db = request.result
        if (!db.objectStoreNames.contains(STORE_NAME)) {
          db.createObjectStore(STORE_NAME)
        }
      }
      request.onsuccess = () => resolve(request.result)
      request.onerror = () => resolve(null)
    } catch {
      resolve(null)
    }
  })
}

export async function loadOfflinePacketsFromIndexedDb(): Promise<OfflinePacketRecord[]> {
  const db = await openOfflineDb()
  if (!db) return []
  return new Promise((resolve) => {
    try {
      const tx = db.transaction(STORE_NAME, 'readonly')
      const store = tx.objectStore(STORE_NAME)
      const request = store.get('queue')
      request.onsuccess = () => {
        const value = request.result
        resolve(Array.isArray(value) ? value.filter((item) => isRecord(item)) as OfflinePacketRecord[] : [])
      }
      request.onerror = () => resolve([])
      tx.oncomplete = () => db.close()
      tx.onerror = () => db.close()
      tx.onabort = () => db.close()
    } catch {
      db.close()
      resolve([])
    }
  })
}

export async function saveOfflinePacketsToIndexedDb(packets: OfflinePacketRecord[]): Promise<void> {
  const db = await openOfflineDb()
  if (!db) return
  await new Promise<void>((resolve) => {
    try {
      const tx = db.transaction(STORE_NAME, 'readwrite')
      tx.objectStore(STORE_NAME).put(packets, 'queue')
      tx.oncomplete = () => {
        db.close()
        resolve()
      }
      tx.onerror = () => {
        db.close()
        resolve()
      }
      tx.onabort = () => {
        db.close()
        resolve()
      }
    } catch {
      db.close()
      resolve()
    }
  })
}

function normalizeVectorClock(value: unknown, actorId: string): PeerVectorClock {
  const record = isRecord(value) ? value : {}
  const next: PeerVectorClock = {}
  Object.entries(record).forEach(([key, raw]) => {
    const count = Number(raw)
    if (key && Number.isFinite(count) && count > 0) {
      next[key] = Math.floor(count)
    }
  })
  if (!next[actorId]) next[actorId] = 0
  return next
}

function compareVectorClocks(a: PeerVectorClock, b: PeerVectorClock) {
  const keys = new Set([...Object.keys(a), ...Object.keys(b)])
  let aAhead = false
  let bAhead = false
  keys.forEach((key) => {
    const av = Number(a[key] || 0)
    const bv = Number(b[key] || 0)
    if (av > bv) aAhead = true
    if (bv > av) bAhead = true
  })
  if (aAhead && !bAhead) return 1
  if (bAhead && !aAhead) return -1
  return 0
}

function getPacketKey(packet: OfflinePacketRecord, index: number) {
  const explicit = String(packet.offline_packet_id || packet.hash_chain_self || '').trim()
  return explicit || `packet-${index}`
}

function comparePackets(a: OfflinePacketRecord, b: OfflinePacketRecord) {
  const clockCompare = compareVectorClocks(
    normalizeVectorClock(a.vector_clock, String(a.peer_node_id || a.executor_did || 'local')),
    normalizeVectorClock(b.vector_clock, String(b.peer_node_id || b.executor_did || 'local')),
  )
  if (clockCompare !== 0) return clockCompare
  const aStamp = Date.parse(String(a.did_timestamp || a.local_created_at || ''))
  const bStamp = Date.parse(String(b.did_timestamp || b.local_created_at || ''))
  if (Number.isFinite(aStamp) && Number.isFinite(bStamp) && aStamp !== bStamp) {
    return aStamp > bStamp ? 1 : -1
  }
  const aHash = String(a.hash_chain_self || '')
  const bHash = String(b.hash_chain_self || '')
  if (aHash && bHash && aHash !== bHash) {
    return aHash > bHash ? 1 : -1
  }
  return 0
}

export function mergeOfflinePacketSets(
  localPackets: OfflinePacketRecord[],
  peerPackets: OfflinePacketRecord[],
): OfflinePacketRecord[] {
  const merged = new Map<string, OfflinePacketRecord>()
  ;[...localPackets, ...peerPackets].forEach((packet, index) => {
    if (!isRecord(packet)) return
    const key = getPacketKey(packet, index)
    const current = merged.get(key)
    if (!current || comparePackets(packet, current) >= 0) {
      merged.set(key, packet)
    }
  })
  return Array.from(merged.values()).sort((left, right) => {
    const leftStamp = Date.parse(String(left.did_timestamp || left.local_created_at || ''))
    const rightStamp = Date.parse(String(right.did_timestamp || right.local_created_at || ''))
    if (Number.isFinite(leftStamp) && Number.isFinite(rightStamp) && leftStamp !== rightStamp) {
      return leftStamp - rightStamp
    }
    return String(left.offline_packet_id || '').localeCompare(String(right.offline_packet_id || ''))
  })
}

export async function stampOfflinePacket(packet: OfflinePacketRecord, options: {
  actorId: string
  did: string
  previousPackets: OfflinePacketRecord[]
}) {
  const actorId = String(options.actorId || 'local').trim() || 'local'
  const did = String(options.did || '').trim()
  const previousPacket = options.previousPackets.length ? options.previousPackets[options.previousPackets.length - 1] : null
  const previousClock = previousPacket ? normalizeVectorClock(previousPacket.vector_clock, actorId) : { [actorId]: 0 }
  const vectorClock: PeerVectorClock = {
    ...previousClock,
    [actorId]: Number(previousClock[actorId] || 0) + 1,
  }
  const didTimestamp = String(packet.did_timestamp || packet.local_created_at || new Date().toISOString())
  const canonical = stableValue({
    ...packet,
    did_timestamp: didTimestamp,
    peer_node_id: actorId,
    vector_clock: vectorClock,
    hash_chain_prev: String(previousPacket?.hash_chain_self || previousPacket?.offline_packet_id || ''),
  })
  const envelopeDigest = await sha256Hex(JSON.stringify(canonical))
  return {
    ...packet,
    did_timestamp: didTimestamp,
    peer_node_id: actorId,
    vector_clock: vectorClock,
    hash_chain_prev: String(previousPacket?.hash_chain_self || previousPacket?.offline_packet_id || ''),
    hash_chain_self: envelopeDigest,
    signature_envelope: {
      did,
      scheme: 'SM2-offline-envelope',
      signed_at: didTimestamp,
      digest: envelopeDigest,
    },
  }
}
