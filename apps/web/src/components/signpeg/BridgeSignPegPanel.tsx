import { useCallback, useEffect, useMemo, useState } from 'react'
import { useAuthStore, useUIStore } from '../../store'
import {
  useSignPegApi,
  type ExecutorSkill,
  type FieldValidationResponse,
  type GateExplainResponse,
  type ProcessExplainResponse,
  type SignPegRole,
  type SignPegStatusItem,
} from '../../hooks/api/signpeg'
import SignPegButton from './SignPegButton'

const ROLE_ORDER: SignPegRole[] = ['inspector', 'recorder', 'reviewer', 'constructor', 'supervisor']

const ROLE_TOKEN_HINTS: Record<SignPegRole, string[]> = {
  inspector: ['inspection', 'inspector', 'check', '检查'],
  recorder: ['record', 'recorder', '记录'],
  reviewer: ['review', 'reviewer', 'audit', '复核', '审核'],
  constructor: ['construction', 'constructor', 'contractor', '施工'],
  supervisor: ['bridge-inspection', 'supervisor', '监理'],
}

function normalizeBodyHash(value: string): string {
  const text = String(value || '').trim()
  if (!text) return ''
  if (text.startsWith('sha256:')) return text
  return `sha256:${text}`
}

function inferRoleText(raw: string): SignPegRole | '' {
  const text = String(raw || '').toLowerCase()
  if (!text) return ''
  if (text.includes('supervisor') || text.includes('监理')) return 'supervisor'
  if (text.includes('inspector') || text.includes('检查')) return 'inspector'
  if (text.includes('recorder') || text.includes('记录')) return 'recorder'
  if (text.includes('reviewer') || text.includes('review') || text.includes('auditor') || text.includes('复核') || text.includes('审核')) return 'reviewer'
  if (text.includes('constructor') || text.includes('contractor') || text.includes('施工')) return 'constructor'
  return ''
}

function inferCurrentRole(user: { dto_role?: string; title?: string; v_uri?: string } | null): SignPegRole | '' {
  if (!user) return ''
  const fromDto = inferRoleText(user.dto_role || '')
  if (fromDto) return fromDto
  const fromTitle = inferRoleText(user.title || '')
  if (fromTitle) return fromTitle
  return inferRoleText(user.v_uri || '')
}

function hasSkillForRole(skills: ExecutorSkill[], role: SignPegRole): boolean {
  const hints = ROLE_TOKEN_HINTS[role]
  for (const skill of skills) {
    const blob = [
      String(skill.skill_uri || ''),
      String(skill.level || ''),
      Array.isArray(skill.scope) ? skill.scope.join(' ') : '',
    ]
      .join(' ')
      .toLowerCase()
    if (hints.some((token) => blob.includes(token))) return true
  }
  return false
}

function fieldHintClass(status: 'ok' | 'warning' | 'blocking' | ''): string {
  if (status === 'blocking') return 'border-rose-400 bg-rose-50 text-rose-700'
  if (status === 'warning') return 'border-amber-400 bg-amber-50 text-amber-700'
  if (status === 'ok') return 'border-emerald-400 bg-emerald-50 text-emerald-700'
  return 'border-slate-300 bg-white text-slate-700'
}

type Props = {
  docId: string
  bodyHash: string
  projectTripRoot?: string
  executorUri?: string
  currentRole?: SignPegRole | ''
  projectUri?: string
  componentUri?: string
  stepId?: string
  processStatus?: 'locked' | 'active' | 'completed'
  gateResult?: Record<string, unknown> | null
  normContext?: Record<string, unknown> | null
  language?: 'zh' | 'en'
}

export default function BridgeSignPegPanel({
  docId,
  bodyHash,
  projectTripRoot,
  executorUri,
  currentRole = '',
  projectUri = '',
  componentUri = '',
  stepId = '',
  processStatus = 'active',
  gateResult = null,
  normContext = null,
  language = 'zh',
}: Props) {
  const { user } = useAuthStore((s) => ({ user: s.user }))
  const { showToast } = useUIStore()
  const { sign, status, getExecutor, explainGate, explainProcess, validateFieldRealtime } = useSignPegApi()

  const resolvedExecutorUri = useMemo(() => String(executorUri || user?.v_uri || '').trim(), [executorUri, user?.v_uri])
  const resolvedRole = useMemo(() => (currentRole || inferCurrentRole(user)), [currentRole, user])
  const normalizedHash = useMemo(() => normalizeBodyHash(bodyHash), [bodyHash])

  const [signatures, setSignatures] = useState<Record<string, SignPegStatusItem>>({})
  const [executorSkills, setExecutorSkills] = useState<ExecutorSkill[]>([])
  const [executorLoaded, setExecutorLoaded] = useState(false)
  const [executorFound, setExecutorFound] = useState(false)

  const [holeDiameter, setHoleDiameter] = useState('')
  const [fieldValidation, setFieldValidation] = useState<FieldValidationResponse['result'] | null>(null)
  const [gateExplainResult, setGateExplainResult] = useState<GateExplainResponse['result'] | null>(null)
  const [processExplainResult, setProcessExplainResult] = useState<ProcessExplainResponse['result'] | null>(null)
  const [explainingGate, setExplainingGate] = useState(false)

  const reloadStatus = useCallback(async () => {
    const id = String(docId || '').trim()
    if (!id) {
      setSignatures({})
      return
    }
    const res = await status(id)
    const rows = Array.isArray(res?.signatures) ? res.signatures : []
    const mapped: Record<string, SignPegStatusItem> = {}
    for (const item of rows) {
      const key = String(item.dto_role || '').trim().toLowerCase()
      if (key && !mapped[key]) mapped[key] = item
    }
    setSignatures(mapped)
  }, [docId, status])

  const reloadExecutor = useCallback(async () => {
    const uri = String(resolvedExecutorUri || '').trim()
    setExecutorLoaded(false)
    if (!uri) {
      setExecutorSkills([])
      setExecutorFound(false)
      setExecutorLoaded(true)
      return
    }
    const res = await getExecutor(uri)
    const skills = Array.isArray(res?.executor?.skills) ? res.executor.skills : []
    setExecutorSkills(skills)
    setExecutorFound(Boolean(res?.executor))
    setExecutorLoaded(true)
  }, [getExecutor, resolvedExecutorUri])

  useEffect(() => {
    void reloadStatus()
  }, [reloadStatus])

  useEffect(() => {
    void reloadExecutor()
  }, [reloadExecutor])

  useEffect(() => {
    const doExplain = async () => {
      if (!projectUri || !componentUri || !stepId) {
        setProcessExplainResult(null)
        return
      }
      const out = await explainProcess({
        project_uri: projectUri,
        component_uri: componentUri,
        step_id: stepId,
        current_status: processStatus,
        language,
      })
      setProcessExplainResult(out?.result || null)
    }
    void doExplain()
  }, [componentUri, explainProcess, language, processStatus, projectUri, stepId])

  const disabledByPayload = !docId || !normalizedHash || !resolvedExecutorUri

  const handleFieldBlur = async () => {
    const numeric = Number(holeDiameter)
    if (!Number.isFinite(numeric)) {
      setFieldValidation({
        field: 'hole_diameter',
        value: holeDiameter,
        status: 'warning',
        message: language === 'en' ? 'Please enter a numeric value.' : '请输入数字。',
        norm_ref: '',
        expected: '',
        actual: String(holeDiameter || ''),
        deviation: '',
        language,
      })
      return
    }
    const out = await validateFieldRealtime({
      form_code: '桥施7表',
      field_key: 'hole_diameter',
      value: numeric,
      context: {
        design_diameter: 1.5,
        tolerance_pct: 5,
        unit: 'm',
        norm_ref: 'JTG F80/1-2017 第7.1条',
      },
      language,
    })
    setFieldValidation(out?.result || null)
  }

  const runGateExplain = async () => {
    setExplainingGate(true)
    try {
      const n = Number(holeDiameter)
      const fallbackGateResult: Record<string, unknown> =
        gateResult && typeof gateResult === 'object'
          ? gateResult
          : {
              result: fieldValidation?.status === 'blocking' ? 'FAIL' : 'PASS',
              checks: [
                {
                  check_id: 'hole_diameter',
                  label: language === 'en' ? 'Hole diameter' : '孔径检查',
                  pass: fieldValidation?.status !== 'blocking',
                  severity: 'mandatory',
                  actual_value: Number.isFinite(n) ? n : null,
                  design_value: 1.5,
                  threshold: { operator: 'gte', value: 1.5, unit: 'm' },
                  norm_ref: 'JTG F80/1-2017 第7.1条',
                  deviation: fieldValidation?.deviation || '',
                },
              ],
            }

      const out = await explainGate({
        form_code: '桥施7表',
        gate_result: fallbackGateResult,
        norm_context: normContext || {
          protocol_uri: 'v://normref.com/doc-type/bridge/pile-hole-check@v1',
        },
        language,
      })
      setGateExplainResult(out?.result || null)
    } finally {
      setExplainingGate(false)
    }
  }

  return (
    <div className="mt-3 rounded-lg border border-slate-200 bg-white p-2">
      <div className="mb-2 text-[11px] font-semibold text-slate-500">桥施7表 SignPeg 签字区</div>
      <div className="grid gap-2">
        {ROLE_ORDER.map((role) => {
          const signedItem = signatures[role] || null
          const hasSkill = !executorLoaded ? true : executorFound ? hasSkillForRole(executorSkills, role) : false
          return (
            <SignPegButton
              key={role}
              role={role}
              docId={docId}
              bodyHash={normalizedHash}
              executorUri={resolvedExecutorUri}
              currentRole={resolvedRole}
              projectTripRoot={projectTripRoot}
              signedItem={signedItem}
              hasSkill={hasSkill}
              disabled={disabledByPayload}
              onSign={sign}
              onAfterSigned={async () => {
                await reloadStatus()
                showToast(language === 'en' ? 'SignPeg signed successfully' : 'SignPeg 签名成功')
              }}
            />
          )
        })}
      </div>

      {disabledByPayload && (
        <div className="mt-2 text-[10px] text-amber-600">
          {language === 'en'
            ? 'Missing sign prerequisites: doc_id / body_hash / executor_uri.'
            : '签字条件不足：请确认 doc_id、body_hash、executor_uri。'}
        </div>
      )}

      <div className="mt-3 rounded-lg border border-slate-200 p-2">
        <div className="text-[11px] font-semibold text-slate-600">
          {language === 'en' ? 'Realtime Fill Hint (Gate Preview)' : '实时填表提示（Gate预警）'}
        </div>
        <div className="mt-2 grid gap-2 min-[560px]:grid-cols-[1fr_auto]">
          <input
            value={holeDiameter}
            onChange={(event) => setHoleDiameter(event.target.value)}
            onBlur={() => void handleFieldBlur()}
            placeholder={language === 'en' ? 'Hole diameter (m), e.g. 1.38' : '孔径（m），例如 1.38'}
            className={`rounded-md border px-2 py-1.5 text-xs ${fieldHintClass(fieldValidation?.status || '')}`}
          />
          <button
            type="button"
            onClick={() => void runGateExplain()}
            disabled={explainingGate}
            className="rounded-md border border-sky-500 bg-sky-50 px-3 py-1.5 text-xs font-semibold text-sky-700 disabled:opacity-70"
          >
            {explainingGate
              ? language === 'en'
                ? 'Explaining...'
                : '解释中...'
              : language === 'en'
                ? 'Explain Gate Result'
                : '生成Gate解释'}
          </button>
        </div>
        {fieldValidation && (
          <div className={`mt-2 rounded-md border px-2 py-1.5 text-[11px] ${fieldHintClass(fieldValidation.status)}`}>
            <div className="font-semibold">{fieldValidation.status.toUpperCase()}</div>
            <div className="mt-1 whitespace-pre-wrap">{fieldValidation.message}</div>
            {!!fieldValidation.norm_ref && <div className="mt-1">Norm: {fieldValidation.norm_ref}</div>}
          </div>
        )}
      </div>

      {gateExplainResult && (
        <div className="mt-3 rounded-lg border border-slate-200 p-2 text-xs">
          <div className={`font-semibold ${gateExplainResult.passed ? 'text-emerald-700' : 'text-rose-700'}`}>
            {gateExplainResult.summary}
          </div>
          {!!gateExplainResult.issues.length && (
            <div className="mt-2 grid gap-2">
              {gateExplainResult.issues.map((item, idx) => (
                <div key={`${item.field}-${idx}`} className="rounded-md border border-slate-200 bg-slate-50 p-2">
                  <div className="font-semibold">{item.field}</div>
                  <div className="mt-1 text-slate-600">{item.explanation}</div>
                  <div className="mt-1 text-[11px] text-slate-500">
                    期望: {item.expected || '-'} | 实际: {item.actual || '-'} | 偏差: {item.deviation || '-'}
                  </div>
                  <div className="mt-1 text-[11px] text-slate-500">Norm: {item.norm_ref || '-'}</div>
                </div>
              ))}
            </div>
          )}
          {!!gateExplainResult.next_steps.length && (
            <div className="mt-2 grid gap-1">
              {gateExplainResult.next_steps.map((step, idx) => (
                <button
                  key={`${step}-${idx}`}
                  type="button"
                  className="rounded-md border border-slate-300 bg-white px-2 py-1 text-left text-[11px] text-slate-700"
                >
                  {idx + 1}. {step}
                </button>
              ))}
            </div>
          )}
        </div>
      )}

      {processExplainResult && (
        <div className="mt-3 rounded-lg border border-slate-200 p-2 text-xs">
          <div className="font-semibold text-slate-700">{processExplainResult.step}</div>
          <div className="mt-1 text-slate-600">{processExplainResult.summary}</div>
          {!!processExplainResult.blocking_reasons.length && (
            <div className="mt-2 grid gap-2">
              {processExplainResult.blocking_reasons.map((reason, idx) => (
                <div key={`${reason.type}-${idx}`} className="rounded-md border border-amber-300 bg-amber-50 p-2">
                  <div className="font-semibold text-amber-800">{reason.type}</div>
                  <div className="mt-1 text-amber-700">{reason.description}</div>
                  <button type="button" className="mt-1 rounded border border-amber-400 bg-white px-2 py-0.5 text-[11px] text-amber-800">
                    {reason.action}
                  </button>
                </div>
              ))}
            </div>
          )}
          {!!processExplainResult.estimated_unblock && (
            <div className="mt-2 text-slate-500">{processExplainResult.estimated_unblock}</div>
          )}
        </div>
      )}
    </div>
  )
}
