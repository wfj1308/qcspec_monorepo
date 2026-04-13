import { useMemo, useState } from 'react'
import type { SignPegRole, SignPegSignResponse, SignPegStatusItem } from '../../hooks/api/signpeg'

type SignRoleConfig = {
  label: string
  dtoRole: SignPegRole
  tripRole: string
  action: 'approve' | 'reject' | 'submit' | 'sign'
}

const ROLE_CONFIG: Record<SignPegRole, SignRoleConfig> = {
  inspector: { label: '质检员', dtoRole: 'inspector', tripRole: 'inspector.submit', action: 'submit' },
  recorder: { label: '记录员', dtoRole: 'recorder', tripRole: 'recorder.sign', action: 'sign' },
  reviewer: { label: '复核员', dtoRole: 'reviewer', tripRole: 'reviewer.approve', action: 'approve' },
  constructor: { label: '施工方', dtoRole: 'constructor', tripRole: 'constructor.sign', action: 'sign' },
  supervisor: { label: '监理方', dtoRole: 'supervisor', tripRole: 'supervisor.approve', action: 'approve' },
}

function toDisplayTime(value: string): string {
  const dt = new Date(value)
  if (Number.isNaN(dt.getTime())) return '--:--'
  const hh = String(dt.getHours()).padStart(2, '0')
  const mm = String(dt.getMinutes()).padStart(2, '0')
  return `${hh}:${mm}`
}

type Props = {
  role: SignPegRole
  docId: string
  bodyHash: string
  executorUri: string
  currentRole: SignPegRole | ''
  projectTripRoot?: string
  signedItem: SignPegStatusItem | null
  hasSkill: boolean
  disabled?: boolean
  onSign: (payload: {
    doc_id: string
    body_hash: string
    executor_uri: string
    dto_role: SignPegRole
    trip_role: string
    action: 'approve' | 'reject' | 'submit' | 'sign'
    project_trip_root?: string
  }) => Promise<SignPegSignResponse | null>
  onAfterSigned: () => Promise<void> | void
}

export default function SignPegButton({
  role,
  docId,
  bodyHash,
  executorUri,
  currentRole,
  projectTripRoot,
  signedItem,
  hasSkill,
  disabled = false,
  onSign,
  onAfterSigned,
}: Props) {
  const [confirmOpen, setConfirmOpen] = useState(false)
  const [submitting, setSubmitting] = useState(false)
  const [errMsg, setErrMsg] = useState('')

  const cfg = ROLE_CONFIG[role]
  const isSigned = Boolean(signedItem)
  const isCurrentRole = currentRole === role
  const isDisabled = disabled || submitting || isSigned || !isCurrentRole || !hasSkill

  const btnCls = useMemo(() => {
    if (isSigned) return 'border-emerald-500 bg-emerald-50 text-emerald-700'
    if (!isCurrentRole) return 'border-slate-300 bg-slate-100 text-slate-400'
    if (!hasSkill) return 'border-rose-400 bg-rose-50 text-rose-700'
    return 'border-sky-500 bg-sky-50 text-sky-700 hover:bg-sky-100'
  }, [hasSkill, isCurrentRole, isSigned])

  const btnText = useMemo(() => {
    if (isSigned) {
      const who = String(signedItem?.executor_name || '-')
      const at = toDisplayTime(String(signedItem?.signed_at || ''))
      return `已签：${who} | ${cfg.dtoRole} | ${at}`
    }
    if (!isCurrentRole) return '非当前角色'
    if (!hasSkill) return '资质不满足'
    return '点击签认'
  }, [cfg.dtoRole, hasSkill, isCurrentRole, isSigned, signedItem?.executor_name, signedItem?.signed_at])

  const canOpenConfirm = !isDisabled

  const doSign = async () => {
    if (submitting) return
    setSubmitting(true)
    setErrMsg('')
    try {
      const res = await onSign({
        doc_id: docId,
        body_hash: bodyHash,
        executor_uri: executorUri,
        dto_role: cfg.dtoRole,
        trip_role: cfg.tripRole,
        action: cfg.action,
        project_trip_root: projectTripRoot,
      })
      if (!res?.ok) {
        setErrMsg('签认失败，请稍后重试。')
        return
      }
      setConfirmOpen(false)
      await onAfterSigned()
    } catch (err: unknown) {
      const msg = err instanceof Error ? err.message : '签认失败'
      setErrMsg(msg)
    } finally {
      setSubmitting(false)
    }
  }

  return (
    <div className="rounded-lg border border-slate-200 bg-white p-2">
      <div className="mb-1 text-[11px] font-semibold text-slate-600">{cfg.label}</div>
      <button
        type="button"
        disabled={isDisabled}
        onClick={() => {
          if (canOpenConfirm) setConfirmOpen(true)
        }}
        className={`w-full rounded-md border px-2 py-2 text-left text-[12px] font-semibold transition ${btnCls} disabled:cursor-not-allowed`}
      >
        {btnText}
      </button>
      {signedItem?.trip_uri && (
        <div className="mt-1 break-all text-[10px] text-emerald-700">执行链路: {signedItem.trip_uri}</div>
      )}
      {errMsg && <div className="mt-1 text-[10px] text-rose-600">{errMsg}</div>}

      {confirmOpen && (
        <div className="fixed inset-0 z-[1500] grid place-items-center bg-slate-950/55 px-4">
          <div className="w-[560px] max-w-[96vw] rounded-xl border border-slate-200 bg-white p-4 text-slate-900 shadow-xl">
            <div className="mb-3 text-base font-bold">确认 SignPeg 签认</div>
            <div className="grid grid-cols-[84px_1fr] gap-2 text-sm">
              <div className="text-slate-500">执行人</div><div className="break-all font-mono">{executorUri || '-'}</div>
              <div className="text-slate-500">角色</div><div>{cfg.dtoRole}</div>
              <div className="text-slate-500">文档</div><div>{docId || '-'}</div>
              <div className="text-slate-500">正文哈希</div><div className="break-all font-mono">{bodyHash || '-'}</div>
              <div className="text-slate-500">动作</div><div>{cfg.tripRole}</div>
              <div className="text-slate-500">时间</div><div>{new Date().toLocaleString()}</div>
            </div>
            <div className="mt-4 flex justify-end gap-2">
              <button
                type="button"
                onClick={() => setConfirmOpen(false)}
                className="rounded-md border border-slate-300 bg-white px-3 py-1.5 text-sm text-slate-700"
              >
                取消
              </button>
              <button
                type="button"
                disabled={submitting}
                onClick={() => void doSign()}
                className="rounded-md border border-sky-600 bg-sky-600 px-3 py-1.5 text-sm font-semibold text-white disabled:opacity-70"
              >
                {submitting ? '签认中...' : '确认签认'}
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  )
}
