/**
 * QCSpec · 质检录入组件
 * apps/web/src/components/inspection/InspectionForm.tsx
 */

import { useState, useCallback, useEffect, useRef  } from 'react'
import { INSPECTION_TYPES } from '@qcspec/types'
import type { InspectResult } from '@qcspec/types'
import { Button, Input, Select, Card, VPathDisplay } from '../ui'
import { useErpnext } from '../../hooks/api/erpnext'
import { useInspections } from '../../hooks/api/inspections'
import { useQCSpecDocPegApi } from '../../hooks/api'
import { useInspectionStore, useUIStore, useProjectStore, usePhotoStore } from '../../store'
import {
  readDocpegInspectionContext,
  saveDocpegInspectionContext,
} from './docpegContext'

const TYPE_OPTIONS = [
  { value: '', label: '请选择检测类型' },
  // 路面
  { value: 'flatness',   label: '路面平整度' },
  { value: 'crack',      label: '裂缝宽度' },
  { value: 'rut',        label: '车辙深度' },
  { value: 'slope',      label: '横坡坡度' },
  // 结构
  { value: 'settlement', label: '路基沉降' },
  { value: 'compaction', label: '压实度' },
  { value: 'bearing',    label: '路基承载力' },
  // 桥梁
  { value: 'bridge_crack',   label: '桥梁裂缝' },
  { value: 'bridge_deflect', label: '挠度' },
  { value: 'bridge_erosion', label: '混凝土碳化' },
  // 房建
  { value: 'concrete_str',  label: '混凝土强度' },
  { value: 'rebar_spacing', label: '钢筋间距' },
]

// 快捷模板
const TEMPLATES = [
  { key: 'flatness',   icon: '🛣️', label: '路面平整度', std: 'IRI ≤ 2.0' },
  { key: 'crack',      icon: '🔍', label: '裂缝宽度',   std: '≤ 0.2mm' },
  { key: 'compaction', icon: '🏗️', label: '压实度',     std: '≥ 96%' },
  { key: 'settlement', icon: '📏', label: '路基沉降',   std: '≤ 30mm' },
]

interface Props {
  projectId:    string
  enterpriseId: string
  onSuccess?:   () => void
}

const toLocalDateTimeSeconds = (date: Date = new Date()): string => {
  const local = new Date(date.getTime() - date.getTimezoneOffset() * 60000)
  return local.toISOString().slice(0, 19)
}

const normalizeFullWidthDigits = (raw: string): string => {
  return raw.replace(/[０-９]/g, (ch) => String.fromCharCode(ch.charCodeAt(0) - 0xFEE0))
}

const parseNumericList = (raw: string): number[] => {
  const text = normalizeFullWidthDigits(String(raw || ''))
    .replace(/[，、；]/g, ',')
    .replace(/[－–—]/g, '-')
  const matched = text.match(/[-+]?\d+(?:\.\d+)?/g) || []
  return matched
    .map((item) => Number(item))
    .filter((num) => Number.isFinite(num))
}

const parseLimitValue = (raw: string): number | null => {
  const match = String(raw || '').match(/[-+]?\d+(?:\.\d+)?/)
  if (!match) return null
  const val = Number(match[0])
  if (!Number.isFinite(val)) return null
  return Math.abs(val)
}

const asRecord = (value: unknown): Record<string, unknown> =>
  (value && typeof value === 'object' && !Array.isArray(value)) ? (value as Record<string, unknown>) : {}

const pickStringDeep = (value: unknown, keys: string[]): string => {
  const row = asRecord(value)
  for (const key of keys) {
    const val = row[key]
    if (typeof val === 'string' && val.trim()) return val.trim()
  }
  for (const nested of ['data', 'result', 'payload']) {
    const found = pickStringDeep(row[nested], keys)
    if (found) return found
  }
  return ''
}

const pickBooleanDeep = (value: unknown, keys: string[]): boolean | null => {
  const row = asRecord(value)
  for (const key of keys) {
    const val = row[key]
    if (typeof val === 'boolean') return val
  }
  for (const nested of ['data', 'result', 'payload']) {
    const found = pickBooleanDeep(row[nested], keys)
    if (found !== null) return found
  }
  return null
}

const slugify = (input: string): string =>
  String(input || '')
    .trim()
    .toLowerCase()
    .replace(/[^a-z0-9]+/g, '-')
    .replace(/^-+|-+$/g, '')

export default function InspectionForm({ projectId, enterpriseId, onSuccess }: Props) {
  const { submit, loading } = useInspections()
  const {
    getProcessChainStatus,
    getProcessChainSummary,
    getProcessChainRecommend,
    getBindingByEntity,
    previewTrip,
    submitTrip,
    listTripRoleTrips,
    checkDtoPermission,
    createLayerpegAnchor,
    loading: docpegLoading,
    error: docpegError,
  } = useQCSpecDocPegApi()
  const { gateCheck } = useErpnext()
  const { addInspection, setInspectionPhotoLinks } = useInspectionStore()
  const { showToast, setActiveTab } = useUIStore()
  const { currentProject }  = useProjectStore()
  const { photos, pendingLinkPhotoIds, clearPendingLinkPhotoIds } = usePhotoStore()

  const [type,     setType]     = useState('')
  const [location, setLocation] = useState('')
  const [value,    setValue]    = useState('')
  const [person,   setPerson]   = useState('')
  const [remark,   setRemark]   = useState('')
  const [result,   setResult]   = useState<InspectResult | ''>('')
  const [lastProof, setLastProof] = useState('')
  const [gateStatus, setGateStatus] = useState('')
  const [inspectedAt, setInspectedAt] = useState(
    () => toLocalDateTimeSeconds()
  )
  const [rebarDesign, setRebarDesign] = useState('')
  const [rebarLimit, setRebarLimit] = useState('±10')
  const [rebarValues, setRebarValues] = useState('')
  const rebarValuesRef = useRef<HTMLTextAreaElement | null>(null)
  const [judgeHint, setJudgeHint] = useState<{ text: string; color: string } | null>(null)
  const [docpegEnabled, setDocpegEnabled] = useState(true)
  const [docpegProjectId, setDocpegProjectId] = useState(projectId)
  const [docpegChainId, setDocpegChainId] = useState('')
  const [docpegComponentUri, setDocpegComponentUri] = useState('')
  const [docpegPileId, setDocpegPileId] = useState('')
  const [docpegAction, setDocpegAction] = useState('qcspec_inspection_submit')
  const [docpegFormCode, setDocpegFormCode] = useState('桥施2表')
  const [docpegSyncStatus, setDocpegSyncStatus] = useState('')
  const [docpegLastTripProof, setDocpegLastTripProof] = useState('')
  const docpegHydratedRef = useRef(false)

  // 选类型时自动填标准值和自动判定
  const typeConfig = type ? INSPECTION_TYPES[type] : null
  const isRebarType = type === 'rebar_spacing'
  const linkedPhotos = photos.filter((p) => pendingLinkPhotoIds.includes(p.id))

  useEffect(() => {
    docpegHydratedRef.current = false
    const saved = readDocpegInspectionContext(projectId)
    setDocpegEnabled(saved.docpegEnabled)
    setDocpegProjectId(saved.docpegProjectId || projectId)
    setDocpegChainId(saved.docpegChainId)
    setDocpegComponentUri(saved.docpegComponentUri)
    setDocpegPileId(saved.docpegPileId)
    setDocpegAction(saved.docpegAction || 'qcspec_inspection_submit')
    setDocpegFormCode(saved.docpegFormCode || '桥施2表')
    docpegHydratedRef.current = true
  }, [projectId])

  useEffect(() => {
    if (!docpegHydratedRef.current) return
    saveDocpegInspectionContext(projectId, {
      docpegEnabled,
      docpegProjectId,
      docpegChainId,
      docpegComponentUri,
      docpegPileId,
      docpegAction,
      docpegFormCode,
    })
  }, [docpegEnabled, docpegProjectId, docpegChainId, docpegComponentUri, docpegPileId, docpegAction, docpegFormCode, projectId])

  useEffect(() => {
    if (docpegPileId || !location.trim()) return
    setDocpegPileId(location.trim())
  }, [docpegPileId, location])

  useEffect(() => {
    if (docpegComponentUri || !location.trim() || !type.trim()) return
    const locationSlug = slugify(location)
    const typeSlug = slugify(type)
    if (!locationSlug || !typeSlug) return
    setDocpegComponentUri(`v://qcspec/component/${locationSlug}/${typeSlug}`)
  }, [docpegComponentUri, location, type])

  const autoJudge = useCallback((val: string) => {
    if (!typeConfig || !val) return
    const v = parseFloat(val)
    if (isNaN(v)) return
    const std = typeConfig.standard
    let r: InspectResult = 'pass'
    if (typeConfig.better === 'less') {
      if (v > std * 1.2) r = 'fail'
      else if (v > std)  r = 'warn'
    } else if (typeConfig.better === 'more') {
      if (v < std * 0.95) r = 'fail'
      else if (v < std)   r = 'warn'
    }
    setResult(r)
    setJudgeHint(null)
  }, [typeConfig])

  const autoJudgeRebar = useCallback(() => {
    if (!isRebarType) return
    const values = parseNumericList(rebarValues)
    const design = Number(rebarDesign || typeConfig?.standard)
    const limit = parseLimitValue(rebarLimit)
    if (!values.length || !Number.isFinite(design) || limit == null) {
      return
    }
    const lower = design - limit
    const upper = design + limit
    const outOfRange = values.some((num) => num < lower || num > upper)
    const avg = values.reduce((sum, n) => sum + n, 0) / values.length
    setValue(avg.toFixed(2))
    setResult(outOfRange ? 'fail' : 'pass')
    setJudgeHint({
      text: outOfRange
        ? `自动判定：不合格（允许区间 ${lower} ~ ${upper}）`
        : `自动判定：合格（允许区间 ${lower} ~ ${upper}）`,
      color: outOfRange ? '#DC2626' : '#059669',
    })
  }, [isRebarType, rebarValues, rebarDesign, rebarLimit, typeConfig?.standard])

  useEffect(() => {
    if (!isRebarType) {
      setJudgeHint(null)
      return
    }
    if (!rebarDesign && typeConfig?.standard != null) {
      setRebarDesign(String(typeConfig.standard))
    }
    if (!rebarLimit) {
      setRebarLimit('±10')
    }
  }, [isRebarType, rebarDesign, rebarLimit, typeConfig?.standard])

  const loadTemplate = (key: string) => {
    setType(key)
    setInspectedAt(toLocalDateTimeSeconds())
    if (key !== 'rebar_spacing') {
      autoJudge(value)
    }
  }

  const buildDocpegTripPayload = (inspectionId?: string, proofId?: string) =>
    ({
      request_id: `qcspec-${Date.now()}`,
      project_id: docpegProjectId.trim(),
      chain_id: docpegChainId.trim(),
      component_uri: docpegComponentUri.trim() || undefined,
      pile_id: ((docpegPileId || location).trim()) || undefined,
      inspection_location: (location.trim() || (docpegPileId || location).trim()) || undefined,
      action: docpegAction.trim() || 'qcspec_inspection_submit',
      payload: {
        inspection_id: inspectionId || undefined,
        inspection_proof_id: proofId || undefined,
        inspection_type: type,
        inspection_result: result,
        inspection_value: value,
      },
    })

  const resolveDocpegChainId = useCallback(async () => {
    const existing = docpegChainId.trim()
    if (existing) return existing
    const pid = docpegProjectId.trim()
    const entity = docpegComponentUri.trim()
    if (!pid || !entity) return ''
    const bindingRes = await getBindingByEntity(pid, entity)
    const autoChainId = pickStringDeep(bindingRes, ['chain_id', 'chainId'])
    if (autoChainId) {
      setDocpegChainId(autoChainId)
      setDocpegSyncStatus(`DocPeg chain auto-bound: ${autoChainId}`)
    }
    return autoChainId
  }, [docpegChainId, docpegProjectId, docpegComponentUri, getBindingByEntity])

  const queryDocpegStatus = async () => {
    const projectIdReady = docpegProjectId.trim()
    const componentUriReady = docpegComponentUri.trim()
    const pileIdReady = (docpegPileId || location).trim()
    if (!projectIdReady || (!componentUriReady && !pileIdReady)) {
      showToast('⚠️ DocPeg 参数不完整：projectId 必填，component_uri / pile_id 至少填一个')
      return
    }
    const chainIdReady = await resolveDocpegChainId()
    if (!chainIdReady) {
      showToast('⚠️ DocPeg chainId 为空且无法自动从 bindings 补全')
      return
    }
    const statusRes = await getProcessChainStatus(projectIdReady, {
      chain_id: chainIdReady,
      component_uri: componentUriReady || undefined,
      pile_id: pileIdReady || undefined,
      inspection_location: location.trim() || undefined,
      source_mode: componentUriReady ? 'component' : 'pile',
    })
    if (statusRes) {
      const currentStep = pickStringDeep(statusRes, ['current_step', 'step_id', 'step'])
      setDocpegSyncStatus(currentStep ? `DocPeg current step: ${currentStep}` : 'DocPeg status synced')
      showToast('✅ 已读取 DocPeg 工序链状态')
    }
  }

  const handleSubmit = async () => {
    if (!type || !location || !value || (!result && !isRebarType)) {
      showToast('⚠️ 请填写检测类型、桩号、实测值并选择结果')
      return
    }
    const parsedValue = parseFloat(value)
    if (Number.isNaN(parsedValue)) {
      showToast('⚠️ 实测值格式不正确')
      return
    }
    let submitValue = parsedValue
    let submitResult: InspectResult = (result || 'warn') as InspectResult
    const rebarValuesRaw = String(rebarValues || rebarValuesRef.current?.value || '')
    if (!rebarValues && rebarValuesRaw) {
      setRebarValues(rebarValuesRaw)
    }
    const parsedRebarValuesList = parseNumericList(rebarValuesRaw)
    const rebarValuesList = parsedRebarValuesList.length > 0
      ? parsedRebarValuesList
      : (Number.isFinite(parsedValue) ? [parsedValue] : [])
    const rebarDesignNumber = Number(rebarDesign || typeConfig?.standard)
    if (isRebarType) {
      if (!rebarValuesList.length) {
        showToast('⚠️ 钢筋间距请至少录入一个实测值')
        return
      }
      if (!parsedRebarValuesList.length && Number.isFinite(parsedValue)) {
        const normalized = String(parsedValue)
        setRebarValues(normalized)
        if (rebarValuesRef.current) rebarValuesRef.current.value = normalized
      }
      if (rebarValuesList.length === 1 && rebarValuesList[0] === 0) {
        showToast('⚠️ 实测值解析异常（当前仅识别到 0），请检查分隔符或重新粘贴数据')
        return
      }
      if (!Number.isFinite(rebarDesignNumber)) {
        showToast('⚠️ 请输入有效设计值')
        return
      }
      if (parseLimitValue(rebarLimit) == null) {
        showToast('⚠️ 请输入有效允许偏差，例如 ±10')
        return
      }
      const limit = parseLimitValue(rebarLimit) as number
      const lower = rebarDesignNumber - limit
      const upper = rebarDesignNumber + limit
      const outOfRange = rebarValuesList.some((num) => num < lower || num > upper)
      const avg = rebarValuesList.reduce((sum, n) => sum + n, 0) / rebarValuesList.length
      submitValue = Number(avg.toFixed(4))
      submitResult = outOfRange ? 'fail' : 'pass'
      setValue(avg.toFixed(2))
      setResult(submitResult)
      setJudgeHint({
        text: outOfRange
          ? `自动判定：不合格（允许区间 ${lower} ~ ${upper}）`
          : `自动判定：合格（允许区间 ${lower} ~ ${upper}）`,
        color: outOfRange ? '#DC2626' : '#059669',
      })
    } else if (!result) {
      showToast('⚠️ 请先选择合格判定')
      return
    }
    const subitemLabel = typeConfig?.label || type
    if (enterpriseId) {
      const gateRes = await gateCheck({
        enterprise_id: enterpriseId,
        project_id: projectId,
        stake: location.trim(),
        subitem: subitemLabel,
        result: submitResult as 'pass' | 'warn' | 'fail',
      }) as {
        gate?: {
          enabled?: boolean
          allow_submit?: boolean
          can_release?: boolean
          action?: string
          reason?: string
        }
        metering_lookup?: {
          success?: boolean
          count?: number
        }
      } | null

      const gate = gateRes?.gate
      const count = Number(gateRes?.metering_lookup?.count || 0)
      if (submitResult === 'pass' && !gateRes) {
        showToast('⛔ ERP 门禁检查失败，暂不允许以“合格”结果提交')
        return
      }
      if (gate?.enabled) {
        if (!gate.allow_submit) {
          if (gate.reason === 'metering_lookup_failed') {
            showToast('⚠️ ERP 计量查询失败，已按“先保存后通知”策略继续保存质检记录')
            setGateStatus(`门禁降级：${gate.reason}（匹配计量 ${count} 条，保存后异步通知 ERP）`)
          } else if (gate.reason === 'no_pending_metering_request') {
            showToast('⛔ 未匹配到待审批计量申请，当前“合格”结果不可提交放行')
            setGateStatus(`门禁拦截：${gate.reason || 'unknown'}（匹配计量 ${count} 条）`)
            return
          } else if (gate.reason === 'missing_erp_project_code_binding') {
            showToast('⛔ 当前项目未绑定 ERP 项目编码，请到项目详情补齐 ERP 项目编码')
            setGateStatus(`门禁拦截：${gate.reason || 'unknown'}（匹配计量 ${count} 条）`)
            return
          } else {
            showToast(`⛔ ERP 门禁未通过：${gate.reason || 'unknown'}`)
            setGateStatus(`门禁拦截：${gate.reason || 'unknown'}（匹配计量 ${count} 条）`)
            return
          }
        }
        if (gate.reason === 'metering_lookup_failed') {
          // Keep degradation hint above; do not override by generic action message.
        } else if (gate.action === 'release') {
          setGateStatus(`门禁通过：匹配 ${count} 条待审批计量申请，提交后将通知 ERP 放行`)
        } else if (gate.action === 'block') {
          setGateStatus(`门禁判定：提交后将通知 ERP 拦截（原因：${gate.reason || 'inspection_not_passed'}）`)
        }
      } else {
        setGateStatus('')
      }
    } else {
      setGateStatus('')
    }

    const body = {
      project_id:  projectId,
      location,
      type,
      type_name:   typeConfig?.label || type,
      value:       submitValue,
      standard:    isRebarType ? rebarDesignNumber : typeConfig?.standard,
      unit:        typeConfig?.unit || '',
      result:      submitResult,
      person:      person || undefined,
      remark:      remark || undefined,
      inspected_at: inspectedAt ? new Date(inspectedAt).toISOString() : new Date().toISOString(),
      photo_ids: pendingLinkPhotoIds.length ? pendingLinkPhotoIds : undefined,
      design: isRebarType ? rebarDesignNumber : undefined,
      limit: isRebarType ? rebarLimit : undefined,
      values: isRebarType ? rebarValuesList : undefined,
      spec_uri: typeConfig?.normRef || undefined,
      norm_uri: typeConfig?.normRef || undefined,
      component_type: isRebarType ? 'main_beam' : undefined,
    }
    const res = await submit(body) as {
      inspection_id?: string
      proof_id?: string
      result?: string
      erpnext_notify?: {
        success?: boolean
        gate?: {
          action?: string
          reason?: string
          can_release?: boolean
        }
      }
    } | null
    if (res?.inspection_id) {
      addInspection({
        id:           res.inspection_id,
        project_id:   projectId,
        v_uri:        `${currentProject?.v_uri || ''}inspection/${res.inspection_id}/`,
        location, type,
        type_name:    typeConfig?.label || type,
        value:        submitValue,
        standard:     isRebarType ? rebarDesignNumber : typeConfig?.standard,
        unit:         typeConfig?.unit || '',
        result:       (res.result as InspectResult) || submitResult,
        person, remark,
        proof_id:     res.proof_id,
        proof_status: 'confirmed',
        seal_status:  'unsigned',
        inspected_at: inspectedAt ? new Date(inspectedAt).toISOString() : new Date().toISOString(),
      })
      if (pendingLinkPhotoIds.length) {
        setInspectionPhotoLinks(res.inspection_id, pendingLinkPhotoIds)
        clearPendingLinkPhotoIds()
      }
      setLastProof(res.proof_id || '')
      // 重置表单
      setValue('')
      setRemark('')
      setResult('')
      setGateStatus('')
      setJudgeHint(null)
      if (isRebarType) {
        setRebarValues('')
        if (typeConfig?.standard != null) {
          setRebarDesign(String(typeConfig.standard))
        }
      }
      setInspectedAt(toLocalDateTimeSeconds())
      const gateAction = res.erpnext_notify?.gate?.action
      if (gateAction === 'release') {
        showToast('✅ 质检已保存，并已通知 ERPNext 放行计量')
      } else if (gateAction === 'block') {
        showToast('✅ 质检已保存，并已通知 ERPNext 拦截计量')
      } else {
        showToast('✅ 质检记录已保存')
      }

      if (docpegEnabled) {
        const componentUriReady = docpegComponentUri.trim()
        const pileIdReady = (docpegPileId || location).trim()
        const missing: string[] = []
        if (!docpegProjectId.trim()) missing.push('projectId')
        if (!componentUriReady && !pileIdReady) missing.push('component_uri / pile_id')
        if (missing.length) {
          setDocpegSyncStatus(`DocPeg skipped: missing ${missing.join(', ')}`)
          showToast(`⚠️ 质检已保存，DocPeg 联动跳过（缺少 ${missing.join(', ')}）`)
        } else {
          try {
            setDocpegSyncStatus('DocPeg syncing: preview...')
            const autoChainId = await resolveDocpegChainId()
            const chainToUse = autoChainId || docpegChainId.trim()
            if (!chainToUse) {
              setDocpegSyncStatus('DocPeg skipped: chainId missing and auto-bind failed')
              showToast('⚠️ 质检已保存，DocPeg 联动跳过（chainId 缺失）')
              onSuccess?.()
              return
            }

            const permissionRes = await checkDtoPermission({
              permission: 'trip.execute',
              project_id: docpegProjectId.trim(),
            })
            const allowed = pickBooleanDeep(permissionRes, ['allowed', 'granted', 'permit'])
            if (allowed === false) {
              setDocpegSyncStatus('DocPeg blocked: DTORole permission denied for trip.execute')
              showToast('⚠️ DocPeg 判权不通过，已阻断工序提交')
              onSuccess?.()
              return
            }

            const tripPayload = {
              ...buildDocpegTripPayload(res.inspection_id, res.proof_id),
              chain_id: chainToUse,
            }
            const previewRes = await previewTrip(tripPayload)
            if (!previewRes) {
              setDocpegSyncStatus('DocPeg preview failed')
            } else {
              setDocpegSyncStatus('DocPeg syncing: submit...')
              const submitRes = await submitTrip(tripPayload)
              const tripProofId = pickStringDeep(submitRes, ['proof_id', 'proofId', 'trip_proof_id'])
              if (tripProofId) setDocpegLastTripProof(tripProofId)

              await getProcessChainSummary(docpegProjectId.trim(), chainToUse, {
                component_uri: componentUriReady || undefined,
                pile_id: pileIdReady || undefined,
              })

              await listTripRoleTrips(docpegProjectId.trim(), {
                chain_id: chainToUse,
                component_uri: componentUriReady || undefined,
                pile_id: pileIdReady || undefined,
              })

              const recommendRes = await getProcessChainRecommend(docpegProjectId.trim(), {
                chain_id: chainToUse,
                component_uri: componentUriReady || undefined,
                pile_id: pileIdReady || undefined,
              })
              const nextAction = pickStringDeep(recommendRes, ['next_action', 'action', 'label'])

              const anchorHash = String(tripProofId || res.proof_id || '').trim()
              if (anchorHash && componentUriReady) {
                await createLayerpegAnchor({
                  project_id: docpegProjectId.trim(),
                  entity_uri: componentUriReady,
                  hash: anchorHash,
                })
              }

              setDocpegSyncStatus(
                nextAction
                  ? `DocPeg synced (permission + trip + anchor). Next action: ${nextAction}`
                  : 'DocPeg synced: trip preview + submit completed'
              )
              showToast('✅ 已同步 DocPeg 工序链')
            }
          } catch (e) {
            const msg = e instanceof Error ? e.message : 'unknown error'
            setDocpegSyncStatus(`DocPeg sync error: ${msg}`)
            showToast(`⚠️ 质检已保存，DocPeg 联动失败：${msg}`)
          }
        }
      }
      onSuccess?.()
    }
  }

  const resultBtns: { key: InspectResult; label: string; color: string; bg: string }[] = [
    { key: 'pass', label: '✓ 合格', color: '#059669', bg: '#ECFDF5' },
    { key: 'warn', label: '⚠ 观察', color: '#D97706', bg: '#FFFBEB' },
    { key: 'fail', label: '✗ 不合格', color: '#DC2626', bg: '#FEF2F2' },
  ]

  return (
    <Card title="质检录入" icon="📋">
      {/* 快捷模板 */}
      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(4,1fr)', gap: 8, marginBottom: 16 }}>
        {TEMPLATES.map(t => (
          <button
            key={t.key}
            onClick={() => loadTemplate(t.key)}
            style={{
              padding: '10px 8px',
              background: type === t.key ? '#EFF6FF' : '#F0F4F8',
              border: `1px solid ${type === t.key ? '#1A56DB' : '#E2E8F0'}`,
              borderRadius: 8, cursor: 'pointer',
              fontSize: 12, textAlign: 'left',
              fontFamily: 'var(--sans)',
            }}
          >
            <div style={{ fontSize: 18, marginBottom: 4 }}>{t.icon}</div>
            <div style={{ fontWeight: 700, color: '#0F172A' }}>{t.label}</div>
            <div style={{ fontSize: 12, color: '#9CA3AF', marginTop: 2 }}>{t.std}</div>
          </button>
        ))}
      </div>

      {/* 表单 */}
      <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 12, marginBottom: 12 }}>
        <Select
          label="检测类型" required
          value={type} onChange={setType}
          options={TYPE_OPTIONS}
        />
        <Input
          label="检测桩号" required
          value={location} onChange={setLocation}
          placeholder="K50+200"
        />
        <div>
          <Input
            label="实测值" required
            value={value} type="number"
            onChange={v => {
              setValue(v)
              if (!isRebarType) autoJudge(v)
            }}
            placeholder="0.00"
          />
          {typeConfig && (
            <div style={{ fontSize: 12, color: '#1A56DB', marginTop: 4 }}>
              规范标准：{isRebarType ? (rebarDesign || typeConfig.standard) : typeConfig.standard} {typeConfig.unit}
              {typeConfig.normRef && (
                <span style={{ color: '#9CA3AF', marginLeft: 6 }}>{typeConfig.normRef}</span>
              )}
            </div>
          )}
          {judgeHint && (
            <div style={{ fontSize: 12, color: judgeHint.color, marginTop: 4, fontWeight: 700 }}>
              {judgeHint.text}
            </div>
          )}
        </div>
        <Input
          label="检测人员"
          value={person} onChange={setPerson}
          placeholder="姓名"
        />
        <div>
          <div style={{ fontSize: 12, fontWeight: 700, color: '#6B7280', marginBottom: 5, letterSpacing: '0.5px', textTransform: 'uppercase' }}>
            检测时间
          </div>
          <input
            type="datetime-local"
            step={1}
            value={inspectedAt}
            onChange={(e) => setInspectedAt(e.target.value)}
            style={{
              width: '100%',
              background: '#F0F4F8',
              border: '1px solid #E2E8F0',
              borderRadius: 8,
              padding: '9px 12px',
              fontSize: 13,
              fontFamily: 'var(--sans)',
              color: '#0F172A',
              outline: 'none',
            }}
          />
        </div>
      </div>

      {isRebarType && (
        <div style={{
          marginBottom: 12,
          padding: 10,
          borderRadius: 8,
          border: '1px solid #DBEAFE',
          background: '#F8FBFF',
        }}>
          <div style={{ fontSize: 12, fontWeight: 700, color: '#1E40AF', marginBottom: 8 }}>
            钢筋间距活表参数（失焦自动判定）
          </div>
          <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 10 }}>
            <Input
              label="设计值"
              value={rebarDesign}
              type="number"
              onChange={setRebarDesign}
              onBlur={autoJudgeRebar}
              placeholder="200"
            />
            <Input
              label="允许偏差"
              value={rebarLimit}
              onChange={setRebarLimit}
              onBlur={autoJudgeRebar}
              placeholder="±10"
            />
          </div>
          <div style={{ marginTop: 8 }}>
            <div style={{ fontSize: 12, fontWeight: 700, color: '#6B7280', marginBottom: 5, letterSpacing: '0.5px', textTransform: 'uppercase' }}>
              实测值列表（逗号/空格/换行分隔，Blur 自动判定）
            </div>
            <textarea
              ref={rebarValuesRef}
              value={rebarValues}
              onChange={(e) => setRebarValues(e.target.value)}
              onBlur={autoJudgeRebar}
              placeholder="198, 203, 201, 196, 207, 202, 199, 204, 198, 200, 201"
              rows={3}
              style={{
                width: '100%',
                background: '#F0F4F8',
                border: '1px solid #E2E8F0',
                borderRadius: 8,
                padding: '9px 12px',
                fontSize: 13,
                fontFamily: 'var(--sans)',
                resize: 'vertical',
                outline: 'none',
              }}
            />
          </div>
        </div>
      )}

      {/* 合格判定 */}
      <div style={{ marginBottom: 12 }}>
        <div style={{ fontSize: 12, fontWeight: 700, color: '#6B7280', marginBottom: 8, letterSpacing: '0.5px', textTransform: 'uppercase' }}>
          合格判定 <span style={{ color: '#DC2626' }}>*</span>
        </div>
        {isRebarType && (
          <div style={{ fontSize: 12, color: '#1E40AF', marginBottom: 8 }}>
            钢筋间距类型由活表参数自动判定，结果按钮只读。
          </div>
        )}
        <div style={{ display: 'flex', gap: 8 }}>
          {resultBtns.map(b => (
            <button
              key={b.key}
              onClick={() => {
                if (!isRebarType) setResult(b.key)
              }}
              disabled={isRebarType}
              style={{
                flex: 1, padding: '10px 0', borderRadius: 8,
                border: `1.5px solid ${result === b.key ? b.color : '#E2E8F0'}`,
                background: result === b.key ? b.bg : '#F0F4F8',
                color: result === b.key ? b.color : '#6B7280',
                fontSize: 13, fontWeight: 700, cursor: isRebarType ? 'not-allowed' : 'pointer',
                opacity: isRebarType ? 0.75 : 1,
                fontFamily: 'var(--sans)',
              }}
            >
              {b.label}
            </button>
          ))}
        </div>
      </div>

      {/* 备注 */}
      <div style={{ marginBottom: 14 }}>
        <div style={{ fontSize: 12, fontWeight: 700, color: '#6B7280', marginBottom: 5, letterSpacing: '0.5px', textTransform: 'uppercase' }}>备注</div>
        <textarea
          value={remark}
          onChange={e => setRemark(e.target.value)}
          placeholder="检测情况描述、异常说明..."
          rows={2}
          style={{
            width: '100%', background: '#F0F4F8',
            border: '1px solid #E2E8F0', borderRadius: 8,
            padding: '9px 12px', fontSize: 13,
            fontFamily: 'var(--sans)', resize: 'vertical', outline: 'none',
          }}
        />
      </div>

      {/* 提交 */}
      <div
        style={{
          marginBottom: 12,
          padding: 10,
          borderRadius: 8,
          border: '1px solid #DBEAFE',
          background: '#F8FBFF',
        }}
      >
        <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', gap: 8, marginBottom: 8 }}>
          <div style={{ fontSize: 12, fontWeight: 700, color: '#1E40AF' }}>
            DocPeg 工序链联动（落业务流程）
          </div>
          <Button
            variant="secondary"
            size="sm"
            onClick={() => setActiveTab('process')}
          >
            去工序页配置
          </Button>
        </div>
        <div
          style={{
            display: 'grid',
            gridTemplateColumns: '1fr 1fr',
            gap: 8,
            padding: 10,
            borderRadius: 8,
            border: '1px solid #DBEAFE',
            background: '#EFF6FF',
            marginBottom: 8,
            fontSize: 12,
            color: '#1E3A8A',
          }}
        >
          <div>projectId: <strong>{docpegProjectId || '-'}</strong></div>
          <div>chainId: <strong>{docpegChainId || '自动绑定'}</strong></div>
          <div style={{ gridColumn: '1 / -1' }}>component_uri: <strong>{docpegComponentUri || '-'}</strong></div>
          <div>pile_id: <strong>{docpegPileId || location || '-'}</strong></div>
          <div>formCode: <strong>{docpegFormCode || '-'}</strong></div>
          <div>action: <strong>{docpegAction || 'qcspec_inspection_submit'}</strong></div>
          <div style={{ gridColumn: '1 / -1', color: '#334155' }}>
            上下文参数在“工序上下文（项目/构件）”面板配置，质检页仅执行录入与提交流程。
          </div>
          <div style={{ display: 'flex', alignItems: 'end' }}>
            <Button
              onClick={() => { void queryDocpegStatus() }}
              disabled={docpegLoading}
              icon="🔄"
            >
              {docpegLoading ? '查询中...' : '查询链状态'}
            </Button>
          </div>
        </div>
        {(docpegSyncStatus || docpegError || docpegLastTripProof) && (
          <div style={{ marginTop: 8, fontSize: 12, color: '#0F766E', lineHeight: 1.6 }}>
            {docpegSyncStatus && <div>状态：{docpegSyncStatus}</div>}
            {docpegLastTripProof && <div>Trip Proof：{docpegLastTripProof}</div>}
            {docpegError && <div style={{ color: '#DC2626' }}>错误：{docpegError}</div>}
          </div>
        )}
      </div>

      <div style={{ marginBottom: 14 }}>
        <div style={{ fontSize: 12, fontWeight: 700, color: '#6B7280', marginBottom: 5, letterSpacing: '0.5px', textTransform: 'uppercase' }}>
          关联照片
        </div>
        {linkedPhotos.length ? (
          <div style={{ display: 'flex', gap: 6, flexWrap: 'wrap' }}>
            {linkedPhotos.map((p) => (
              <img
                key={p.id}
                src={p.storage_url}
                alt={p.file_name}
                title={p.file_name}
                style={{ width: 56, height: 56, borderRadius: 6, objectFit: 'cover', border: '1px solid #E2E8F0' }}
              />
            ))}
            <button
              onClick={clearPendingLinkPhotoIds}
              style={{
                padding: '0 10px',
                borderRadius: 6,
                border: '1px solid #FECACA',
                background: '#FEF2F2',
                color: '#DC2626',
                fontSize: 12,
                cursor: 'pointer',
                fontFamily: 'var(--sans)',
              }}
            >
              清空关联
            </button>
          </div>
        ) : (
          <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', gap: 8 }}>
            <div style={{ fontSize: 12, color: '#94A3B8' }}>可在“现场照片”页多选后点击“关联到质检录入”。</div>
            <button
              onClick={() => setActiveTab('records')}
              style={{
                border: '1px solid #BFDBFE',
                background: '#EFF6FF',
                color: '#1A56DB',
                borderRadius: 6,
                padding: '4px 8px',
                fontSize: 12,
                cursor: 'pointer',
                fontFamily: 'var(--sans)',
                whiteSpace: 'nowrap',
              }}
            >
              去现场照片
            </button>
          </div>
        )}
      </div>

      <Button
        fullWidth onClick={handleSubmit}
        disabled={loading || !type || !location || !value || (!result && !isRebarType)}
        icon="✅"
      >
        {loading ? '保存中...' : '保存质检记录'}
      </Button>
      {gateStatus && (
        <div style={{ marginTop: 8, fontSize: 12, color: '#0F766E' }}>
          {gateStatus}
        </div>
      )}

      {/* 最新 Proof */}
      {lastProof && (
        <div style={{ marginTop: 10 }}>
          <VPathDisplay
            uri={`${currentProject?.v_uri || ''}inspection/latest/`}
            proofId={lastProof}
          />
        </div>
      )}
    </Card>
  )
}

