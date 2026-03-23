/**
 * QCSpec · Proof 链工具包
 * packages/proof/index.ts
 *
 * 当前：本地 SHA256 模拟
 * 后期：替换为 GitPeg API 调用
 */

// ── Proof 数据结构 ──
export interface ProofPayload {
  uri:       string
  type:      string
  object_id: string
  actor_id?: string
  parent?:   string
  timestamp: number
  data:      Record<string, unknown>
}

export interface ProofResult {
  proof_id:   string   // GP-PROOF-XXXXXXXXXXXXXXXX
  proof_hash: string   // SHA256 hex
  v_uri:      string
  created_at: string
}

// ── SHA256（浏览器 + Node 兼容）──
async function sha256(message: string): Promise<string> {
  if (typeof window !== 'undefined' && window.crypto?.subtle) {
    // 浏览器
    const msgBuffer = new TextEncoder().encode(message)
    const hashBuffer = await crypto.subtle.digest('SHA-256', msgBuffer)
    const hashArray  = Array.from(new Uint8Array(hashBuffer))
    return hashArray.map(b => b.toString(16).padStart(2, '0')).join('')
  } else {
    // Node.js
    const { createHash } = await import('crypto')
    return createHash('sha256').update(message).digest('hex')
  }
}

// ── 生成 Proof ──
export async function generateProof(
  v_uri:     string,
  type:      string,
  object_id: string,
  data:      Record<string, unknown>,
  actor_id?: string,
  parent?:   string,
): Promise<ProofResult> {
  const payload: ProofPayload = {
    uri:       v_uri,
    type,
    object_id,
    actor_id,
    parent:    parent || 'GENESIS',
    timestamp: Date.now(),
    data,
  }

  const payloadStr = JSON.stringify(payload, Object.keys(payload).sort())
  const hash       = await sha256(payloadStr)
  const proof_id   = `GP-PROOF-${hash.substring(0, 16).toUpperCase()}`

  return {
    proof_id,
    proof_hash: hash,
    v_uri,
    created_at: new Date().toISOString(),
  }
}

// ── 验证 Proof ──
export function verifyProofId(proof_id: string, proof_hash: string): boolean {
  const expected = proof_id.replace('GP-PROOF-', '').toLowerCase()
  return proof_hash.startsWith(expected)
}

// ── 生成质检 Proof ──
export async function inspectionProof(
  proj_uri:   string,
  insp_id:    string,
  type:       string,
  value:      number,
  result:     string,
  location:   string,
): Promise<ProofResult> {
  const v_uri = `${proj_uri}inspection/${insp_id}/`
  return generateProof(v_uri, 'inspection', insp_id, {
    type, value, result, location
  })
}

// ── 生成照片 Proof ──
export async function photoProof(
  proj_uri:  string,
  photo_id:  string,
  filename:  string,
  location?: string,
  gps?:      [number, number],
): Promise<ProofResult> {
  const v_uri = `${proj_uri}photo/${photo_id}/`
  return generateProof(v_uri, 'photo', photo_id, {
    filename, location, gps
  })
}

// ── 生成报告 Proof ──
export async function reportProof(
  proj_uri:   string,
  report_no:  string,
  pass_rate:  number,
  total:      number,
): Promise<ProofResult> {
  const v_uri = `${proj_uri}reports/${report_no}/`
  return generateProof(v_uri, 'report', report_no, {
    pass_rate, total, report_no
  })
}

/**
 * 后期替换为 GitPeg API：
 *
 * export async function generateProof(...): Promise<ProofResult> {
 *   const res = await fetch('https://api.gitpeg.dev/v1/proof/commit', {
 *     method: 'POST',
 *     headers: { 'Authorization': `Bearer ${GITPEG_TOKEN}` },
 *     body: JSON.stringify({ uri: v_uri, type, object_id, data })
 *   })
 *   return res.json()
 * }
 */
