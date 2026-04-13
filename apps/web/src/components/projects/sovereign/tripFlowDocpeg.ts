import type { Dispatch, SetStateAction } from 'react'

import { buildMeasurementPayload } from './spuUtils'
import { toApiUri } from './treeUtils'
import type { Evidence, FormRow, TreeNode } from './types'
import { asDict } from './tripFlowUtils'

type RunTripGenerateDocArgs = {
  active: TreeNode | null
  apiProjectUri: string
  isSpecBound: boolean
  form: Record<string, string>
  effectiveSchema: FormRow[]
  sampleId: string
  effectiveClaimQtyValue: number
  executorDid: string
  lat: string
  lng: string
  geoAnchor: { lat: number; lng: number } | null
  evidence: Evidence[]
  showToast: (message: string) => void
  tripGenerateDoc: (payload: Record<string, unknown>) => Promise<unknown>
  setMockGenerating: Dispatch<SetStateAction<boolean>>
  setMockDocRes: Dispatch<SetStateAction<Record<string, unknown> | null>>
  onMockDocReady?: () => void
}

export async function runTripGenerateDoc({
  active,
  apiProjectUri,
  isSpecBound,
  form,
  effectiveSchema,
  sampleId,
  effectiveClaimQtyValue,
  executorDid,
  lat,
  lng,
  geoAnchor,
  evidence,
  showToast,
  tripGenerateDoc,
  setMockGenerating,
  setMockDocRes,
  onMockDocReady,
}: RunTripGenerateDocArgs): Promise<void> {
  if (!active?.isLeaf || !apiProjectUri) {
    showToast('请先选择叶子细目')
    return
  }
  if (!isSpecBound) {
    showToast('未绑定规范门控，禁止提交')
    return
  }

  const measurement = buildMeasurementPayload(form, effectiveSchema)
  if (sampleId) measurement.sample_id = sampleId
  if (effectiveClaimQtyValue > 0) measurement.claim_quantity = effectiveClaimQtyValue

  const normRows = effectiveSchema.map((row, idx) => {
    const field = String(row.field || `f_${idx}`)
    const measured = String(form[field] ?? '').trim()
    return {
      field,
      label: row.label || field,
      operator: String(row.operator || 'present'),
      threshold: String(row.default || ''),
      measured_value: measured,
      unit: String(row.unit || ''),
    }
  })

  setMockGenerating(true)
  try {
    const payload = await tripGenerateDoc({
      project_uri: apiProjectUri,
      boq_item_uri: toApiUri(active.uri),
      smu_id: String(active.code || '').split('-')[0],
      subitem_code: active.code,
      item_name: active.name,
      unit: active.unit || '',
      executor_did: executorDid,
      geo_location: { lat: Number(lat), lng: Number(lng) },
      anchor_location: geoAnchor ? { lat: geoAnchor.lat, lng: geoAnchor.lng } : {},
      norm_rows: normRows,
      measurements: measurement,
      evidence_hashes: evidence.map((item) => item.hash),
      report_template: '3、桥施表.docx',
    }) as Record<string, unknown> | null

    if (!payload?.ok) {
      showToast('DocPeg 生成失败')
      return
    }

    setMockDocRes(payload)
    onMockDocReady?.()
    const risk = Number((asDict(payload.risk_audit).risk_score || 0))
    if (risk < 60) showToast(`报告已生成，但风险偏高（${risk.toFixed(2)}）`)
    else showToast('桥施表已生成，总存证哈希 已锁定')
  } finally {
    setMockGenerating(false)
  }
}

// Backward-compatible alias during refactor rollout.
export const runTripSubmitMock = runTripGenerateDoc

