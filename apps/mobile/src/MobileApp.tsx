import React, { useCallback, useEffect, useMemo, useRef, useState } from 'react'
import './styles/mobile.css'
import { mobileApi } from './services/mobileApi'
import { buildActualData, buildHint, validateField } from './utils/gate'
import { cloneMockWorkorder, fallbackFormSpecsByStepKey } from './data/mock'
import DonePage from './pages/DonePage'
import FormPage from './pages/FormPage'
import HistoryPage from './pages/HistoryPage'
import ScanPage from './pages/ScanPage'
import SignPage from './pages/SignPage'
import WorkorderPage from './pages/WorkorderPage'
import { MOBILE_ROUTES, MOBILE_ROLES } from './types/mobile'
import type {
  ChainSyncState,
  FieldValidation,
  HistoryRecord,
  MobileFormField,
  MobileFormSpec,
  MobileRole,
  MobileRoute,
  MobileWorkStep,
  MobileWorkorder,
  PendingAnchor,
  PendingSubmission,
  PhotoEvidence,
  SignatureMethod,
} from './types/mobile'

type StorageSnapshot = {
  role: MobileRole
  history: HistoryRecord[]
  recent: Array<{ code: string; step: string; time: string }>
  pending: PendingSubmission[]
  pendingAnchors: PendingAnchor[]
}

const STORAGE_KEY = 'qcspec_mobile_react_v1'

function asRecord(value: unknown): Record<string, unknown> {
  if (value && typeof value === 'object' && !Array.isArray(value)) return value as Record<string, unknown>
  return {}
}

function asString(value: unknown, fallback = ''): string {
  return typeof value === 'string' ? value : fallback
}

function formatChainSyncError(raw: string): string {
  const token = String(raw || '').trim()
  if (!token) return ''
  if (token.includes('supabase_not_configured_or_unreachable')) return '主链服务未配置或不可达'
  if (token.includes('triprole_execution_failed')) return 'TripRole执行失败'
  if (token.includes('proof_utxo')) return 'Proof链表不可用'
  return token
}

function pickGates(value: unknown): Array<Record<string, unknown>> {
  if (!value || typeof value !== 'object' || Array.isArray(value)) return []
  const root = value as Record<string, unknown>
  if (Array.isArray(root.gates)) return root.gates as Array<Record<string, unknown>>
  const protocol = root.protocol
  if (protocol && typeof protocol === 'object' && !Array.isArray(protocol)) {
    const protocolGates = (protocol as Record<string, unknown>).gates
    if (Array.isArray(protocolGates)) return protocolGates as Array<Record<string, unknown>>
  }
  return []
}

function pickSignatureToken(value: unknown): string {
  if (!value || typeof value !== 'object' || Array.isArray(value)) return ''
  const row = value as Record<string, unknown>
  const keys = ['signature', 'token', 'signedToken', 'data', 'dataUrl']
  for (const key of keys) {
    const text = row[key]
    if (typeof text === 'string' && text.trim()) return text
  }
  return ''
}

function parseRouteFromHash(hash: string): MobileRoute {
  const route = hash.replace(/^#/, '')
  return MOBILE_ROUTES.includes(route as MobileRoute) ? (route as MobileRoute) : 'scan'
}

function nowText() {
  const date = new Date()
  const month = String(date.getMonth() + 1).padStart(2, '0')
  const day = String(date.getDate()).padStart(2, '0')
  const hour = String(date.getHours()).padStart(2, '0')
  const minute = String(date.getMinutes()).padStart(2, '0')
  return `${month}-${day} ${hour}:${minute}`
}

function todayDate() {
  return new Date().toISOString().slice(0, 10)
}

function randomProofId() {
  const seed = `${Date.now()}${Math.random().toString(16).slice(2, 10)}`
  return `NINST-${seed.slice(-8).toUpperCase()}`
}

function isRole(value: string): value is MobileRole {
  return MOBILE_ROLES.includes(value as MobileRole)
}

function parseScanInput(raw: string) {
  const text = String(raw || '').trim()
  if (!text) return null
  if (text.startsWith('v://')) {
    const code = text.split('/').filter(Boolean).pop() || text
    return { code, vUri: text }
  }
  return { code: text, vUri: `v://cn.dajing/djgs/bridge/${text}` }
}

function pickCurrentStep(order: MobileWorkorder | null): MobileWorkStep | null {
  if (!order?.steps?.length) return null
  return (
    order.steps.find((step) => step.status === 'current') ||
    order.steps.find((step) => step.status === 'todo') ||
    order.steps[order.steps.length - 1]
  )
}

function fallbackFormSpec(step: MobileWorkStep, workorderCode: string): MobileFormSpec {
  const candidate = fallbackFormSpecsByStepKey[step.key] || {
    subtitle: step.formName || '现场检查表',
    fields: [
      {
        key: 'main_value',
        label: '检查值',
        hint: '按设计值填写',
        unit: '',
        required: true,
        threshold: { operator: 'eq' as const, value: 1 },
      },
    ],
  }

  return {
    subtitle: candidate.subtitle,
    normrefUri: step.normrefUri || '',
    baseFields: [
      { key: 'component_code', label: '检查部位', type: 'text', readonly: true, defaultValue: workorderCode },
      { key: 'inspect_date', label: '检查日期', type: 'date', defaultValue: todayDate() },
    ],
    fields: candidate.fields,
  }
}

function mapRemoteWorkorder(payload: unknown, fallbackVUri: string): MobileWorkorder | null {
  const root = asRecord(payload)
  const code = asString(root.component_code || root.componentCode)
  if (!code) return null

  const rows = Array.isArray(root.steps) ? root.steps : []
  const steps: MobileWorkStep[] = rows.map((item, index) => {
    const row = asRecord(item)
    const requiredRoleRaw = asString(row.required_role || row.requiredRole, '检查')
    return {
      key: asString(row.key || row.step_key, `step-${index + 1}`),
      name: asString(row.name || row.step_name, '工序'),
      status: (asString(row.status, 'todo') as 'done' | 'current' | 'todo'),
      requiredRole: isRole(requiredRoleRaw) ? requiredRoleRaw : '检查',
      formName: asString(row.form_name || row.formName, '检查表'),
      normrefUri: asString(row.normref_uri || row.normrefUri, ''),
      doneAt: asString(row.done_at || row.doneAt, ''),
      doneBy: asString(row.executor_name || row.executorName, ''),
      proofId: asString(row.proof_id || row.proofId, ''),
    }
  })

  return {
    code,
    name: asString(root.component_name || root.componentName, `${code} 构件`),
    vUri: asString(root.v_uri || root.vUri, fallbackVUri),
    steps,
  }
}

function toNormrefField(gate: Record<string, unknown>, index: number): MobileFormField | null {
  const thresholdRaw = asRecord(gate.threshold || gate.rule)
  const operatorRaw = asString(thresholdRaw.operator || thresholdRaw.op, 'eq').toLowerCase()
  const operator = (['gte', 'lte', 'range', 'eq'].includes(operatorRaw) ? operatorRaw : 'eq') as
    | 'gte'
    | 'lte'
    | 'range'
    | 'eq'

  const unit = asString(thresholdRaw.unit || gate.unit, '')
  const thresholdValue =
    thresholdRaw.value !== undefined
      ? thresholdRaw.value
      : Array.isArray(thresholdRaw.range)
      ? [Number(thresholdRaw.range[0]), Number(thresholdRaw.range[1])]
      : gate.design_value

  const key = asString(gate.check_id || gate.code, `field_${index + 1}`)
  const label = asString(gate.label || gate.name, `检查项${index + 1}`)
  const required = gate.required !== false

  if (!required) return null

  return {
    key,
    label,
    unit,
    required: true,
    threshold: { operator, value: thresholdValue as number | string | [number, number] },
    hint: buildHint(operator, thresholdValue as number | string | [number, number], unit),
  }
}

async function readFileAsDataUrl(file: File) {
  return new Promise<string>((resolve, reject) => {
    const reader = new FileReader()
    reader.onload = () => resolve(String(reader.result || ''))
    reader.onerror = reject
    reader.readAsDataURL(file)
  })
}

async function sha256FromBase64(base64: string) {
  const bytes = Uint8Array.from(atob(base64), (char) => char.charCodeAt(0))
  const hashBuffer = await crypto.subtle.digest('SHA-256', bytes)
  return Array.from(new Uint8Array(hashBuffer))
    .map((byte) => byte.toString(16).padStart(2, '0'))
    .join('')
}

async function getGps() {
  return new Promise<{ lat: number | null; lng: number | null }>((resolve) => {
    if (!navigator.geolocation) {
      resolve({ lat: null, lng: null })
      return
    }
    navigator.geolocation.getCurrentPosition(
      (position) => resolve({ lat: position.coords.latitude, lng: position.coords.longitude }),
      () => resolve({ lat: null, lng: null }),
      { timeout: 5000 },
    )
  })
}

export default function MobileApp() {
  const [route, setRoute] = useState<MobileRoute>(() => parseRouteFromHash(window.location.hash))
  const [online, setOnline] = useState(navigator.onLine)
  const [role, setRole] = useState<MobileRole>('检查')
  const [workorder, setWorkorder] = useState<MobileWorkorder | null>(null)
  const [formSpec, setFormSpec] = useState<MobileFormSpec | null>(null)
  const [formValues, setFormValues] = useState<Record<string, string>>({})
  const [checks, setChecks] = useState<Record<string, FieldValidation>>({})
  const [result, setResult] = useState<'合格' | '不合格'>('合格')
  const [remoteGateHint, setRemoteGateHint] = useState('')
  const [photos, setPhotos] = useState<PhotoEvidence[]>([])
  const [signatureData, setSignatureData] = useState('')
  const [signatureMethod, setSignatureMethod] = useState<SignatureMethod>('handwrite')
  const [password, setPassword] = useState('')
  const [done, setDone] = useState<HistoryRecord | null>(null)
  const [history, setHistory] = useState<HistoryRecord[]>([])
  const [recent, setRecent] = useState<Array<{ code: string; step: string; time: string }>>([])
  const [pending, setPending] = useState<PendingSubmission[]>([])
  const [pendingAnchors, setPendingAnchors] = useState<PendingAnchor[]>([])
  const [qrCodeImage, setQrCodeImage] = useState('')
  const [qrCodeLoading, setQrCodeLoading] = useState(false)
  const verifyTimerRef = useRef<number | null>(null)

  const currentStep = useMemo(() => pickCurrentStep(workorder), [workorder])

  const canSignCurrent = !!currentStep && currentStep.requiredRole === role

  const navigate = useCallback((next: MobileRoute) => {
    setRoute(next)
    window.location.hash = next
  }, [])

  useEffect(() => {
    const onHashChange = () => setRoute(parseRouteFromHash(window.location.hash))
    window.addEventListener('hashchange', onHashChange)
    return () => window.removeEventListener('hashchange', onHashChange)
  }, [])

  useEffect(() => {
    const onOnline = () => setOnline(true)
    const onOffline = () => setOnline(false)
    window.addEventListener('online', onOnline)
    window.addEventListener('offline', onOffline)
    return () => {
      window.removeEventListener('online', onOnline)
      window.removeEventListener('offline', onOffline)
    }
  }, [])

  useEffect(() => {
    try {
      const raw = localStorage.getItem(STORAGE_KEY)
      if (!raw) return
      const snapshot = JSON.parse(raw) as Partial<StorageSnapshot>
      if (snapshot.role && isRole(snapshot.role)) setRole(snapshot.role)
      if (Array.isArray(snapshot.history)) setHistory(snapshot.history)
      if (Array.isArray(snapshot.recent)) setRecent(snapshot.recent)
      if (Array.isArray(snapshot.pending)) setPending(snapshot.pending)
      if (Array.isArray(snapshot.pendingAnchors)) setPendingAnchors(snapshot.pendingAnchors)
    } catch {
      // ignore corrupted local cache
    }
  }, [])

  useEffect(() => {
    let alive = true
    void mobileApi
      .getMyRole()
      .then((payload) => {
        if (!alive) return
        const source = asString(asRecord(payload).source, '')
        const roleText = asString(asRecord(payload).role, '')
        if (source === 'auth' && isRole(roleText)) {
          setRole(roleText)
        }
      })
      .catch(() => null)
    return () => {
      alive = false
    }
  }, [])

  useEffect(() => {
    const snapshot: StorageSnapshot = {
      role,
      history,
      recent,
      pending,
      pendingAnchors,
    }
    localStorage.setItem(STORAGE_KEY, JSON.stringify(snapshot))
  }, [history, pending, pendingAnchors, recent, role])

  const syncAll = useCallback(async () => {
    if (!online) return

    const pendingLeft: PendingSubmission[] = []
    for (const item of pending) {
      try {
        await mobileApi.submitMobile(item.payload)
      } catch {
        pendingLeft.push({ ...item, retry: item.retry + 1 })
      }
    }
    if (pendingLeft.length !== pending.length) setPending(pendingLeft)

    const anchorLeft: PendingAnchor[] = []
    for (const item of pendingAnchors) {
      try {
        await mobileApi.anchorPhoto(item.payload)
      } catch {
        anchorLeft.push({ ...item, retry: item.retry + 1 })
      }
    }
    if (anchorLeft.length !== pendingAnchors.length) setPendingAnchors(anchorLeft)
  }, [online, pending, pendingAnchors])

  useEffect(() => {
    if (online) void syncAll()
  }, [online, syncAll])

  useEffect(() => {
    void mobileApi.getExecutorWorkorders(role).catch(() => null)
  }, [role])

  const resolveFormSpecFor = useCallback(async (targetWorkorder: MobileWorkorder, targetStep: MobileWorkStep) => {
    const fallback = fallbackFormSpec(targetStep, targetWorkorder.code)
    if (!targetStep.normrefUri) return fallback

    try {
      const resolved = await mobileApi.resolveNormref(targetStep.normrefUri)
      const gates = pickGates(resolved)
      const fields = gates
        .map((gate, index) => toNormrefField(asRecord(gate), index))
        .filter((item): item is MobileFormField => !!item)
      if (!fields.length) return fallback
      return {
        subtitle: targetStep.formName || fallback.subtitle,
        normrefUri: targetStep.normrefUri,
        baseFields: fallback.baseFields,
        fields,
      }
    } catch {
      return fallback
    }
  }, [])

  const applyFormSpec = useCallback((loaded: MobileFormSpec) => {
    if (!loaded) return

    const nextValues: Record<string, string> = {}
    loaded.baseFields.forEach((field) => {
      nextValues[field.key] = field.defaultValue || ''
    })
    const nextChecks: Record<string, FieldValidation> = {}
    loaded.fields.forEach((field) => {
      nextValues[field.key] = ''
      nextChecks[field.key] = { ok: false, message: '请填写此项' }
    })

    setFormSpec(loaded)
    setFormValues(nextValues)
    setChecks(nextChecks)
    setResult('合格')
    setRemoteGateHint('')
    setPhotos([])
    setSignatureData('')
    setSignatureMethod('handwrite')
    setPassword('')
    navigate('form')
  }, [navigate])

  const prepareForm = useCallback(async (targetWorkorder?: MobileWorkorder) => {
    const sourceWorkorder = targetWorkorder || workorder
    if (!sourceWorkorder) return
    const step = pickCurrentStep(sourceWorkorder)
    if (!step) return
    const loaded = await resolveFormSpecFor(sourceWorkorder, step)
    applyFormSpec(loaded)
  }, [applyFormSpec, resolveFormSpecFor, workorder])

  const openWorkorderFromInput = useCallback(
    async (raw: string) => {
      const parsed = parseScanInput(raw)
      if (!parsed) {
        window.alert('请输入桩号或二维码地址')
        return
      }

      let nextWorkorder: MobileWorkorder | null = null
      try {
        const remotePayload = await mobileApi.getCurrentStep(parsed.vUri)
        nextWorkorder = mapRemoteWorkorder(remotePayload, parsed.vUri)
      } catch {
        nextWorkorder = null
      }

      if (!nextWorkorder) {
        nextWorkorder =
          cloneMockWorkorder(parsed.code) || {
            code: parsed.code,
            name: `${parsed.code} 钻孔灌注桩`,
            vUri: parsed.vUri,
            steps: [
              {
                key: 'general_check',
                name: '现场检查',
                status: 'current',
                requiredRole: '检查',
                formName: '现场检查表',
                normrefUri: 'v://normref.com/qc/template/general-quality-inspection@v1',
              },
            ],
          }
      }

      setWorkorder(nextWorkorder)
      setDone(null)
      setQrCodeImage('')

      const nextStep = pickCurrentStep(nextWorkorder)
      if (nextStep && nextStep.requiredRole === role) {
        await prepareForm(nextWorkorder)
        return
      }

      navigate('workorder')
    },
    [navigate, prepareForm, role],
  )

  const loadQrCode = useCallback(async () => {
    if (!workorder?.vUri || qrCodeLoading) return
    setQrCodeLoading(true)
    try {
      const image = await mobileApi.getQrCode(workorder.vUri)
      if (image) {
        setQrCodeImage(image)
      } else {
        window.alert('二维码接口未返回可展示图片')
      }
    } catch {
      window.alert('二维码加载失败，请稍后重试')
    } finally {
      setQrCodeLoading(false)
    }
  }, [qrCodeLoading, workorder?.vUri])

  const onFieldChange = useCallback(
    (key: string, value: string) => {
      if (!formSpec) return
      const field = formSpec.fields.find((item) => item.key === key)
      if (!field) return
      setFormValues((prev) => ({ ...prev, [key]: value }))
      setChecks((prev) => ({ ...prev, [key]: validateField(field, value) }))
    },
    [formSpec],
  )

  useEffect(() => {
    if (route !== 'form' || !formSpec?.normrefUri || !online || !workorder) return
    if (verifyTimerRef.current) window.clearTimeout(verifyTimerRef.current)

    const hasInput = formSpec.fields.some((field) => String(formValues[field.key] || '').trim())
    if (!hasInput) {
      setRemoteGateHint('')
      return
    }

    verifyTimerRef.current = window.setTimeout(async () => {
      try {
        const verify = await mobileApi.verifyNormref({
          protocolUri: formSpec.normrefUri || '',
          actualData: buildActualData(formSpec, formValues),
          designData: {},
          context: { component_code: workorder.code, step_name: currentStep?.name || '' },
        })
        setRemoteGateHint(verify.result === 'FAIL' ? verify.explain || '存在不满足要求的检查项，请核对数据' : '')
      } catch {
        setRemoteGateHint('')
      }
    }, 420)

    return () => {
      if (verifyTimerRef.current) window.clearTimeout(verifyTimerRef.current)
    }
  }, [currentStep?.name, formSpec, formValues, online, route, workorder])

  const takePhoto = useCallback(async () => {
    const input = document.createElement('input')
    input.type = 'file'
    input.accept = 'image/*'
    input.capture = 'environment'

    input.onchange = async () => {
      const file = input.files?.[0]
      if (!file) return

      const dataUrl = await readFileAsDataUrl(file)
      const base64 = dataUrl.split(',')[1] || ''
      const hash = await sha256FromBase64(base64)
      const gps = await getGps()
      const timestamp = new Date().toISOString()

      const photo: PhotoEvidence = {
        preview: dataUrl,
        base64,
        hash,
        gps,
        timestamp,
      }

      setPhotos((prev) => [...prev, photo])

      const anchorPayload = {
        photo: base64,
        hash,
        trip_id: workorder?.code || '',
        location: gps,
        timestamp,
      }

      try {
        if (!online) throw new Error('offline')
        await mobileApi.anchorPhoto(anchorPayload)
      } catch {
        setPendingAnchors((prev) => [...prev, { id: `anchor-${Date.now()}`, payload: anchorPayload, retry: 0 }])
      }
    }

    input.click()
  }, [online, workorder?.code])

  const goSign = useCallback(() => {
    if (!formSpec) return
    const allFilled = formSpec.fields.every((field) => String(formValues[field.key] || '').trim())
    if (!allFilled) {
      window.alert('请先完成所有必填项')
      return
    }
    navigate('sign')
  }, [formSpec, formValues, navigate])

  const useExternalSignature = useCallback(
    async (provider: 'signpeg' | 'ca') => {
      const providerLabel = provider === 'signpeg' ? 'SignPeg' : '法大大 CA'
      const sdkHolder = window as unknown as {
        SignPeg?: { sign?: (payload: Record<string, unknown>) => Promise<unknown> }
        FaDaDa?: { sign?: (payload: Record<string, unknown>) => Promise<unknown> }
      }

      const sdk = provider === 'signpeg' ? sdkHolder.SignPeg : sdkHolder.FaDaDa
      const payload = {
        component_code: workorder?.code || '',
        step_name: currentStep?.name || '',
        role,
        timestamp: new Date().toISOString(),
      }

      if (sdk?.sign) {
        try {
          const signed = await sdk.sign(payload)
          const token = pickSignatureToken(signed)
          if (token) {
            setSignatureMethod(provider === 'signpeg' ? 'signpeg' : 'ca')
            setSignatureData(token)
            window.alert(`已通过 ${providerLabel} 完成签名`)
            return
          }
        } catch {
          // fallback below
        }
      }

      try {
        const remote = await mobileApi.confirmSignature({
          provider,
          componentCode: workorder?.code || '',
          stepName: currentStep?.name || '',
          role,
          payload,
        })
        const remoteToken = pickSignatureToken(remote)
        if (remoteToken) {
          setSignatureMethod(provider === 'signpeg' ? 'signpeg' : 'ca')
          setSignatureData(remoteToken)
          window.alert(`已通过服务端 ${providerLabel} 确认签名`)
          return
        }
      } catch {
        // continue below
      }

      const confirmFallback = window.confirm(
        `未检测到 ${providerLabel} SDK 且服务端确认失败，是否改用密码确认提交？`,
      )
      if (confirmFallback) {
        setSignatureMethod(provider === 'signpeg' ? 'signpeg' : 'ca')
        setSignatureData('')
        window.alert('已切换为密码确认模式，请输入密码后提交')
      }
    },
    [currentStep?.name, role, workorder?.code],
  )

  const submit = useCallback(async () => {
    if (!workorder || !formSpec || !currentStep) return
    if (!canSignCurrent) {
      window.alert('当前角色不可签名提交')
      return
    }

    const allFilled = formSpec.fields.every((field) => String(formValues[field.key] || '').trim())
    if (!allFilled) {
      window.alert('请先完成所有必填项')
      return
    }
    if (!signatureData && !password.trim()) {
      window.alert('请手写签名，或输入密码确认')
      return
    }

    const payload = {
      v_uri: workorder.vUri,
      component_code: workorder.code,
      step_key: currentStep.key,
      step_name: currentStep.name,
      result,
      form_data: { ...formValues, checked_at: new Date().toISOString() },
      evidence: photos.map((photo) => ({ hash: photo.hash, timestamp: photo.timestamp, location: photo.gps })),
      signature: signatureData
        ? { type: signatureMethod, data: signatureData }
        : { type: 'password', data: 'password-confirmed' },
      executor_uri: `v://mobile/executor/${encodeURIComponent(role)}`,
      timestamp: new Date().toISOString(),
      device_id: navigator.userAgent,
    }

    let proofId = randomProofId()
    let chainSyncState: ChainSyncState = online ? 'fallback' : 'pending'
    let chainSyncMessage = online ? '已提交，主链同步稍后自动补偿' : '离线已保存，联网后自动同步'
    let chainSyncAction = ''
    let chainSyncError = ''
    try {
      if (!online) throw new Error('offline')
      const response = await mobileApi.submitMobile(payload)
      const raw = asRecord(response)
      proofId = asString(raw.proof_id || raw.proofId, proofId)
      const sync = asRecord(raw.triprole_sync || raw.triproleSync)
      const syncOk = sync.ok === true
      const outputProof = asString(sync.output_proof_id || sync.outputProofId, '')
      chainSyncAction = asString(sync.action, '')
      chainSyncError = asString(sync.error, '')
      if (syncOk && outputProof) {
        chainSyncState = 'chained'
        chainSyncMessage = chainSyncAction ? `已通过 ${chainSyncAction} 写入Proof链` : '已写入Proof链'
      } else {
        chainSyncState = 'fallback'
        const reasonText = formatChainSyncError(chainSyncError)
        chainSyncMessage = reasonText ? `已提交，主链未写入：${reasonText}` : '已提交，主链同步稍后自动补偿'
      }
    } catch {
      setPending((prev) => [...prev, { id: `submit-${Date.now()}`, payload, retry: 0 }])
      chainSyncState = 'pending'
      chainSyncMessage = '离线已保存，联网后自动同步'
      chainSyncAction = ''
      chainSyncError = ''
    }

    const currentIndex = workorder.steps.findIndex((step) => step.key === currentStep.key)
    const updatedSteps = workorder.steps.map((step) => ({ ...step }))
    if (currentIndex >= 0) {
      updatedSteps[currentIndex] = {
        ...updatedSteps[currentIndex],
        status: 'done',
        doneAt: nowText(),
        doneBy: role,
        proofId,
      }
      const nextIndex = updatedSteps.slice(currentIndex + 1).findIndex((step) => step.status === 'todo')
      if (nextIndex >= 0) {
        updatedSteps[currentIndex + 1 + nextIndex] = {
          ...updatedSteps[currentIndex + 1 + nextIndex],
          status: 'current',
        }
      }
    }

    const nextStepName =
      updatedSteps.slice(currentIndex + 1).find((step) => step.status === 'current')?.name || '等待施工员操作'

    const record: HistoryRecord = {
      code: workorder.code,
      step: currentStep.name,
      result,
      role,
      time: nowText(),
      proofId,
      nextStep: nextStepName,
      chainSyncState,
      chainSyncMessage,
      chainSyncAction,
      chainSyncError,
    }

    setWorkorder({ ...workorder, steps: updatedSteps })
    setHistory((prev) => [...prev, record])
    setRecent((prev) => [{ code: record.code, step: record.step, time: record.time }, ...prev].slice(0, 20))
    setDone(record)
    navigate('done')
  }, [
    canSignCurrent,
    currentStep,
    formSpec,
    formValues,
    navigate,
    online,
    password,
    photos,
    result,
    role,
    signatureData,
    signatureMethod,
    workorder,
  ])

  const safeRoute: MobileRoute =
    route === 'workorder' && !workorder
      ? 'scan'
      : route === 'form' && (!workorder || !formSpec)
      ? 'scan'
      : route === 'sign' && (!workorder || !formSpec || !currentStep)
      ? 'scan'
      : route === 'done' && !done
      ? 'scan'
      : route

  return (
    <div className="mobile-app">
      {!online ? <div className="mobile-offline-banner">离线模式 - 数据将在联网后同步</div> : null}

      {safeRoute === 'scan' ? (
        <ScanPage
          role={role}
          recent={recent}
          onRoleChange={setRole}
          onResolveInput={openWorkorderFromInput}
          onOpenHistory={() => navigate('history')}
        />
      ) : null}

      {safeRoute === 'workorder' && workorder ? (
        <WorkorderPage
          role={role}
          workorder={workorder}
          qrCodeImage={qrCodeImage}
          qrCodeLoading={qrCodeLoading}
          onBack={() => navigate('scan')}
          onStartForm={() => void prepareForm()}
          onLoadQrCode={loadQrCode}
          onQuickSwitchRole={(nextRole) => {
            setRole(nextRole)
            window.alert(`已切换为${nextRole}，可继续处理当前工序`)
          }}
        />
      ) : null}

      {safeRoute === 'form' && workorder && formSpec ? (
        <FormPage
          title={currentStep?.name || '填表'}
          stepIndex={2}
          stepTotal={3}
          componentCode={workorder.code}
          componentName={workorder.name}
          requiredRole={currentStep?.requiredRole || role}
          role={role}
          spec={formSpec}
          values={formValues}
          checks={checks}
          result={result}
          remoteGateHint={remoteGateHint}
          photos={photos}
          onBack={() => navigate('workorder')}
          onBaseChange={(key, value) => setFormValues((prev) => ({ ...prev, [key]: value }))}
          onFieldChange={onFieldChange}
          onResultChange={setResult}
          onRemarkChange={(value) => setFormValues((prev) => ({ ...prev, remark: value }))}
          onTakePhoto={takePhoto}
          onNextSign={goSign}
        />
      ) : null}

      {safeRoute === 'sign' && workorder && formSpec && currentStep ? (
        <SignPage
          role={role}
          requiredRole={currentStep.requiredRole}
          canSign={canSignCurrent}
          code={workorder.code}
          stepName={currentStep.name}
          result={result}
          spec={formSpec}
          values={formValues}
          password={password}
          signatureMethod={signatureMethod}
          onBack={() => navigate('form')}
          onSetPassword={setPassword}
          onSetHandwriteSignature={(value) => {
            setSignatureMethod('handwrite')
            setSignatureData(value)
          }}
          onUseSignPeg={() => void useExternalSignature('signpeg')}
          onUseCaSign={() => void useExternalSignature('ca')}
          onSubmit={submit}
        />
      ) : null}

      {safeRoute === 'done' && done ? (
        <DonePage
          done={done}
          onViewProgress={() => navigate('workorder')}
          onScanNext={() => navigate('scan')}
          onGoHome={() => navigate('scan')}
        />
      ) : null}

      {safeRoute === 'history' ? (
        <HistoryPage
          history={history}
          pendingSubmissionCount={pending.length}
          pendingAnchorCount={pendingAnchors.length}
          online={online}
          onBack={() => navigate('scan')}
          onSyncNow={syncAll}
        />
      ) : null}
    </div>
  )
}

