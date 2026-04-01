import { useCallback, useEffect, useRef, useState } from 'react'

import { safeEvalFormula } from './analysisUtils'
import { downloadJson, sha256Hex } from './fileUtils'
import { asNum } from './treeUtils'

type MerkleStep = {
  depth: number
  position: string
  sibling_hash: string
  combined_hash: string
}

type UseSovereignAdvancedOpsArgs = {
  apiProjectUri: string
  activeCode: string
  activeUri: string
  inputProofId: string
  finalProofId: string
  totalHash: string
  docpegRiskScore: number
  scanEntryLatestProofId: string
  geoDistance: number
  effectiveClaimQtyValue: number
  measuredQtyValue: number
  ledgerSnapshot: Record<string, unknown>
  unitMerkleRoot: (query: {
    project_uri: string
    unit_code?: string
    proof_id?: string
    max_rows?: number
  }) => Promise<unknown>
  enqueueTriprolePacket: (action: string, payload: Record<string, unknown>, result?: string) => string
  appendMeshpegLog: (entry: Record<string, unknown>) => void
  appendFormulaLog: (entry: Record<string, unknown>) => void
  appendGatewayLog: (entry: Record<string, unknown>) => void
  showToast: (message: string) => void
}

export function useSovereignAdvancedOps({
  apiProjectUri,
  activeCode,
  activeUri,
  inputProofId,
  finalProofId,
  totalHash,
  docpegRiskScore,
  scanEntryLatestProofId,
  geoDistance,
  effectiveClaimQtyValue,
  measuredQtyValue,
  ledgerSnapshot,
  unitMerkleRoot,
  enqueueTriprolePacket,
  appendMeshpegLog,
  appendFormulaLog,
  appendGatewayLog,
  showToast,
}: UseSovereignAdvancedOpsArgs) {
  const autoUnitRef = useRef('')
  const [showFingerprintAdvanced, setShowFingerprintAdvanced] = useState(false)
  const [unitCode, setUnitCode] = useState('')
  const [unitProofId, setUnitProofId] = useState('')
  const [unitMaxRows, setUnitMaxRows] = useState('20000')
  const [unitRes, setUnitRes] = useState<Record<string, unknown> | null>(null)
  const [unitLoading, setUnitLoading] = useState(false)
  const [unitVerifying, setUnitVerifying] = useState(false)
  const [itemRootComputed, setItemRootComputed] = useState('')
  const [unitLeafComputed, setUnitLeafComputed] = useState('')
  const [projectRootComputed, setProjectRootComputed] = useState('')
  const [unitVerifyMsg, setUnitVerifyMsg] = useState('')
  const [itemPathSteps, setItemPathSteps] = useState<MerkleStep[]>([])
  const [unitPathSteps, setUnitPathSteps] = useState<MerkleStep[]>([])
  const [meshpegCloudName, setMeshpegCloudName] = useState('')
  const [meshpegBimName, setMeshpegBimName] = useState('')
  const [meshpegRunning, setMeshpegRunning] = useState(false)
  const [meshpegRes, setMeshpegRes] = useState<Record<string, unknown> | null>(null)
  const [formulaExpr, setFormulaExpr] = useState('qty * unit_price')
  const [formulaRunning, setFormulaRunning] = useState(false)
  const [formulaRes, setFormulaRes] = useState<Record<string, unknown> | null>(null)
  const [gatewayRes, setGatewayRes] = useState<Record<string, unknown> | null>(null)

  useEffect(() => {
    if (!activeCode) return
    const next = activeCode.split('-')[0]
    if (next) setUnitCode(next)
  }, [activeCode])

  const calcUnitMerkle = useCallback(async () => {
    if (!apiProjectUri) {
      showToast('项目 URI 缺失')
      return
    }
    setUnitLoading(true)
    try {
      const payload = await unitMerkleRoot({
        project_uri: apiProjectUri,
        unit_code: unitCode || undefined,
        proof_id: unitProofId || undefined,
        max_rows: Number(unitMaxRows) || undefined,
      }) as Record<string, unknown> | null
      if (!payload?.ok) {
        showToast('数字资产总指纹计算失败')
        return
      }
      setUnitRes(payload)
      showToast('数字资产总指纹已生成')
    } finally {
      setUnitLoading(false)
    }
  }, [apiProjectUri, showToast, unitCode, unitMaxRows, unitMerkleRoot, unitProofId])

  useEffect(() => {
    if (!apiProjectUri || !unitCode) return
    if (autoUnitRef.current === unitCode) return
    autoUnitRef.current = unitCode
    void calcUnitMerkle()
  }, [apiProjectUri, calcUnitMerkle, unitCode])

  const useCurrentProofForUnit = useCallback(() => {
    const pid = String(inputProofId || '')
    if (pid) setUnitProofId(pid)
    const code = activeCode ? activeCode.split('-')[0] : ''
    if (code) setUnitCode(code)
  }, [activeCode, inputProofId])

  const exportMerkleJson = useCallback(() => {
    if (!unitRes) {
      showToast('请先生成数字资产总指纹')
      return
    }
    downloadJson(`merkle-snapshot-${Date.now()}.json`, {
      unit: unitRes,
      computed: {
        item_root: itemRootComputed,
        unit_leaf: unitLeafComputed,
        project_root: projectRootComputed,
        item_path_steps: itemPathSteps,
        unit_path_steps: unitPathSteps,
      },
    })
  }, [itemPathSteps, itemRootComputed, projectRootComputed, showToast, unitLeafComputed, unitRes, unitPathSteps])

  const runMeshpeg = useCallback(() => {
    if (!activeUri) {
      showToast('请先选择细目')
      return
    }
    setMeshpegRunning(true)
    try {
      const designQty = asNum(
        ledgerSnapshot.approved_quantity
        || ledgerSnapshot.contract_quantity
        || ledgerSnapshot.design_quantity
        || 0,
      )
      const baseQty = designQty || effectiveClaimQtyValue || measuredQtyValue
      const drift = geoDistance != null ? Math.max(-0.06, Math.min(0.06, ((geoDistance % 7) - 3) / 100)) : -0.02
      const meshVolume = baseQty ? baseQty * (1 + drift) : 0
      const deviationPct = baseQty ? ((meshVolume - baseQty) / baseQty) * 100 : 0
      const status = Math.abs(deviationPct) <= 2 ? 'PASS' : 'FAIL'
      const payload = {
        ok: true,
        mesh_volume: Number(meshVolume.toFixed(4)),
        design_quantity: Number(baseQty.toFixed(4)),
        deviation_percent: Number(deviationPct.toFixed(3)),
        status,
        cloud: meshpegCloudName || 'LiDAR',
        bim: meshpegBimName || 'BIM',
        proof_id: `MESH-${Date.now().toString(36).toUpperCase()}`,
      }
      setMeshpegRes(payload)
      const packetId = enqueueTriprolePacket('meshpeg.verify', { ...payload, status })
      appendMeshpegLog({
        item_uri: activeUri,
        created_at: new Date().toISOString(),
        status: payload.status,
        mesh_volume: payload.mesh_volume,
        design_quantity: payload.design_quantity,
        deviation_percent: payload.deviation_percent,
        proof_id: payload.proof_id,
        chain_status: 'queued',
        offline_packet_id: packetId,
      })
      showToast(`MeshPeg 核算完成：${status}`)
    } finally {
      setMeshpegRunning(false)
    }
  }, [
    activeUri,
    appendMeshpegLog,
    effectiveClaimQtyValue,
    enqueueTriprolePacket,
    geoDistance,
    ledgerSnapshot,
    measuredQtyValue,
    meshpegBimName,
    meshpegCloudName,
    showToast,
  ])

  const runFormulaPeg = useCallback(() => {
    if (!activeUri) {
      showToast('请先选择细目')
      return
    }
    setFormulaRunning(true)
    try {
      const qty = asNum(meshpegRes?.mesh_volume)
        || effectiveClaimQtyValue
        || measuredQtyValue
        || asNum(ledgerSnapshot.approved_quantity || ledgerSnapshot.contract_quantity || ledgerSnapshot.design_quantity || 0)
      const unitPrice = asNum(ledgerSnapshot.unit_price || ledgerSnapshot.unit_price_with_tax || 0)
      const result = safeEvalFormula(formulaExpr, { qty, unit_price: unitPrice, factor: 1 })
      if (!result.ok) {
        showToast(`FormulaPeg 失败：${result.error}`)
        return
      }
      const payload = {
        ok: true,
        formula: formulaExpr,
        qty: Number(qty.toFixed(4)),
        unit_price: Number(unitPrice.toFixed(4)),
        amount: Number(result.value.toFixed(2)),
        railpact_id: `RP-${Date.now().toString(36).toUpperCase()}`,
        status: 'LOCKED',
        mesh_proof_id: String(meshpegRes?.proof_id || ''),
        proof_id: finalProofId || inputProofId || '',
        created_at: new Date().toISOString(),
      }
      setFormulaRes(payload)
      const packetId = enqueueTriprolePacket('formula.price', { ...payload, status: 'LOCKED' })
      appendFormulaLog({
        item_uri: activeUri,
        created_at: payload.created_at,
        status: payload.status,
        formula: payload.formula,
        qty: payload.qty,
        unit_price: payload.unit_price,
        amount: payload.amount,
        railpact_id: payload.railpact_id,
        chain_status: 'queued',
        offline_packet_id: packetId,
      })
      showToast(`FormulaPeg 已生成：${payload.amount}`)
    } finally {
      setFormulaRunning(false)
    }
  }, [
    activeUri,
    appendFormulaLog,
    effectiveClaimQtyValue,
    enqueueTriprolePacket,
    finalProofId,
    formulaExpr,
    inputProofId,
    ledgerSnapshot,
    measuredQtyValue,
    meshpegRes?.mesh_volume,
    meshpegRes?.proof_id,
    showToast,
  ])

  const runGatewaySync = useCallback(() => {
    if (!apiProjectUri) {
      showToast('项目 URI 缺失')
      return
    }
    const payload = {
      project_uri: apiProjectUri,
      total_proof_hash: totalHash,
      proof_id: finalProofId || inputProofId || '',
      scan_entry_proof: scanEntryLatestProofId,
      risk_score: docpegRiskScore,
      updated_at: new Date().toISOString(),
      gateway: 'SovereignGateway/0.1',
    }
    setGatewayRes(payload)
    const packetId = enqueueTriprolePacket('gateway.sync', { ...payload, status: 'PASS' })
    appendGatewayLog({
      item_uri: activeUri,
      created_at: payload.updated_at,
      total_proof_hash: payload.total_proof_hash,
      proof_id: payload.proof_id,
      scan_entry_proof: payload.scan_entry_proof,
      risk_score: payload.risk_score,
      chain_status: 'queued',
      offline_packet_id: packetId,
    })
    showToast('监管同步摘要已生成')
  }, [
    activeUri,
    apiProjectUri,
    appendGatewayLog,
    docpegRiskScore,
    enqueueTriprolePacket,
    finalProofId,
    inputProofId,
    scanEntryLatestProofId,
    showToast,
    totalHash,
  ])

  const computeMerkleSteps = useCallback(async (leaf: string, path: Array<Record<string, unknown>>) => {
    if (!leaf || !Array.isArray(path) || !path.length) return { root: '', steps: [] as MerkleStep[] }
    let current = leaf
    const steps: MerkleStep[] = []
    for (const step of path) {
      const sibling = String(step.sibling_hash || '')
      const position = String(step.position || '')
      if (!sibling) continue
      current = position === 'left'
        ? await sha256Hex(`${sibling}|${current}`)
        : await sha256Hex(`${current}|${sibling}`)
      steps.push({
        depth: Number(step.depth || steps.length),
        position,
        sibling_hash: sibling,
        combined_hash: current,
      })
    }
    return { root: current, steps }
  }, [])

  const verifyUnitMerkle = useCallback(async () => {
    if (!unitRes) {
      showToast('请先生成数字资产总指纹')
      return
    }
    setUnitVerifying(true)
    setUnitVerifyMsg('')
    try {
      const requestedLeaf = (unitRes.requested_leaf || {}) as Record<string, unknown>
      const leafHash = String(requestedLeaf.leaf_hash || '')
      const itemPath = Array.isArray(unitRes.item_merkle_path) ? (unitRes.item_merkle_path as Array<Record<string, unknown>>) : []
      const unitRootExpected = String(unitRes.unit_root_hash || '')
      const itemCalc = leafHash && itemPath.length ? await computeMerkleSteps(leafHash, itemPath) : { root: '', steps: [] as MerkleStep[] }

      const resolvedUnit = String(unitRes.resolved_unit_code || '')
      const units = Array.isArray(unitRes.units) ? (unitRes.units as Array<Record<string, unknown>>) : []
      let unitLeaf = ''
      for (const u of units) {
        if (String(u.unit_code || '') === resolvedUnit) {
          unitLeaf = String(u.unit_leaf_hash || '')
          break
        }
      }
      if (!unitLeaf && resolvedUnit && unitRootExpected) {
        unitLeaf = await sha256Hex(`unit:${resolvedUnit}|${unitRootExpected}`)
      }

      const unitPath = Array.isArray(unitRes.unit_merkle_path) ? (unitRes.unit_merkle_path as Array<Record<string, unknown>>) : []
      const projectRootExpected = String(unitRes.project_root_hash || unitRes.global_project_fingerprint || '')
      const unitCalc = unitLeaf && unitPath.length ? await computeMerkleSteps(unitLeaf, unitPath) : { root: '', steps: [] as MerkleStep[] }

      setItemRootComputed(itemCalc.root)
      setUnitLeafComputed(unitLeaf)
      setProjectRootComputed(unitCalc.root)
      setItemPathSteps(itemCalc.steps)
      setUnitPathSteps(unitCalc.steps)

      const itemOk = !!itemCalc.root && !!unitRootExpected && itemCalc.root === unitRootExpected
      const projectOk = !!unitCalc.root && !!projectRootExpected && unitCalc.root === projectRootExpected
      setUnitVerifyMsg(itemOk && projectOk ? '校验通过：叶子 -> 单位 -> 项目链路一致' : '校验失败：请检查路径或 leaf hash')
    } finally {
      setUnitVerifying(false)
    }
  }, [computeMerkleSteps, showToast, unitRes])

  return {
    showFingerprintAdvanced,
    setShowFingerprintAdvanced,
    unitProofId,
    setUnitProofId,
    unitMaxRows,
    setUnitMaxRows,
    unitRes,
    unitLoading,
    unitVerifying,
    unitVerifyMsg,
    itemPathSteps,
    unitPathSteps,
    meshpegCloudName,
    setMeshpegCloudName,
    meshpegBimName,
    setMeshpegBimName,
    meshpegRunning,
    meshpegRes,
    formulaExpr,
    setFormulaExpr,
    formulaRunning,
    formulaRes,
    gatewayRes,
    calcUnitMerkle,
    useCurrentProofForUnit,
    exportMerkleJson,
    runMeshpeg,
    runFormulaPeg,
    runGatewaySync,
    verifyUnitMerkle,
  }
}
