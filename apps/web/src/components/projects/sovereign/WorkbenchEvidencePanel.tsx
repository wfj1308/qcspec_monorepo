import type { RefObject } from 'react'

import type { Evidence } from './types'

type Props = {
  lat: string
  lng: string
  geoFormLocked: boolean
  evidenceFileRef: RefObject<HTMLInputElement | null>
  evidenceLabel: string
  evidenceName: string
  evidenceAccept: string
  evidenceHint: string
  geoValid: boolean
  geoFenceWarning: string
  geoFenceActive: boolean
  geoDistance: number
  activeIsLeaf: boolean
  sampleId: string
  executorDid: string
  activeUri: string
  hashing: boolean
  evidence: Evidence[]
  showAdvancedExecution: boolean
  deltaAmount: string
  deltaReason: string
  applyingDelta: boolean
  variationRes: Record<string, unknown> | null
  inputBaseCls: string
  btnAmberCls: string
  onLatChange: (value: string) => void
  onLngChange: (value: string) => void
  onEvidence: (files: FileList | null) => void | Promise<void>
  onFingerprintOpen: () => void
  onEvidencePreview: (item: Evidence) => void
  onDeltaAmountChange: (value: string) => void
  onDeltaReasonChange: (value: string) => void
  onApplyDelta: () => void
}

export default function WorkbenchEvidencePanel({
  lat,
  lng,
  geoFormLocked,
  evidenceFileRef,
  evidenceLabel,
  evidenceName,
  evidenceAccept,
  evidenceHint,
  geoValid,
  geoFenceWarning,
  geoFenceActive,
  geoDistance,
  activeIsLeaf,
  sampleId,
  executorDid,
  activeUri,
  hashing,
  evidence,
  showAdvancedExecution,
  deltaAmount,
  deltaReason,
  applyingDelta,
  variationRes,
  inputBaseCls,
  btnAmberCls,
  onLatChange,
  onLngChange,
  onEvidence,
  onFingerprintOpen,
  onEvidencePreview,
  onDeltaAmountChange,
  onDeltaReasonChange,
  onApplyDelta,
}: Props) {
  const lockedCls = geoFormLocked ? 'cursor-not-allowed opacity-60' : ''

  return (
    <>
      <div className="mb-3 grid grid-cols-2 gap-3 max-[1180px]:grid-cols-1">
        <input value={lat} disabled={geoFormLocked} onChange={(event) => onLatChange(event.target.value)} placeholder="GPS 纬度" className={`${inputBaseCls} ${lockedCls}`} />
        <input value={lng} disabled={geoFormLocked} onChange={(event) => onLngChange(event.target.value)} placeholder="GPS 经度" className={`${inputBaseCls} ${lockedCls}`} />
      </div>

      <div className="grid grid-cols-[auto_1fr] items-center gap-2">
        <button type="button" disabled={geoFormLocked} onClick={() => evidenceFileRef.current?.click()} className={`rounded-lg border border-slate-700 bg-slate-950/80 px-3 py-2 text-sm leading-5 text-slate-200 ${lockedCls}`}>{evidenceLabel}</button>
        <div className={`truncate text-sm leading-5 ${evidenceName ? 'text-slate-200' : 'text-slate-500'}`}>{evidenceName || `未选择任何文件（${evidenceHint}）`}</div>
        <input ref={evidenceFileRef} type="file" multiple disabled={geoFormLocked} accept={evidenceAccept} onChange={(event) => void onEvidence(event.target.files)} className="hidden" />
      </div>

      <div className="mt-2 flex items-center justify-between text-xs text-slate-400">
        <span className="flex items-center gap-2">主权指纹<button type="button" onClick={onFingerprintOpen} className="rounded border border-slate-600 bg-slate-900/70 px-2 py-0.5 text-[11px] text-slate-200">查看</button></span>
        <span className={`rounded-full border px-2 py-0.5 ${hashing ? 'border-amber-500/60 text-amber-300' : 'border-emerald-500/60 text-emerald-300'}`}>{hashing ? '计算中...' : `数量 ${evidence.length}`}</span>
      </div>
      <div className={`mt-1 text-xs ${geoValid ? 'text-emerald-300' : 'text-amber-300'}`}>位置校验: {geoValid ? '坐标已采集' : '疑似虚假影像（坐标缺失）'}</div>
      {!!geoFenceWarning && <div className="mt-1 text-xs text-rose-300">位置警告: {geoFenceWarning}</div>}

      <div className="mt-3 mb-3 grid max-h-[190px] grid-cols-2 gap-2 overflow-y-auto">
        {evidence.map((item) => (
          <button type="button" key={item.hash} onClick={() => onEvidencePreview(item)} className={`relative overflow-hidden rounded-lg border bg-transparent p-0 ${geoFenceActive && geoDistance > 0 ? 'border-rose-500/80' : 'border-slate-700'}`}>
            <img src={item.url} alt={item.name} className="block h-[108px] w-full object-cover" />
            <div className="absolute inset-0 flex flex-col justify-end gap-0.5 bg-gradient-to-t from-slate-950/80 to-slate-950/20 p-2 text-[11px] leading-4 text-slate-200">
              <div className={`inline-flex w-fit rounded-full border px-1.5 py-0 text-[10px] ${geoFenceActive && geoDistance > 0 ? 'border-rose-400/70 bg-rose-950/40 text-rose-200' : 'border-emerald-400/70 bg-emerald-950/40 text-emerald-200'}`}>{geoFenceActive && geoDistance > 0 ? 'SnapPeg 拦截' : 'SnapPeg 已封存'}</div>
              <div>v:// 路径: {activeUri || '-'}</div>
              <div>GPS 坐标: {lat}, {lng}</div>
              <div>NTP 时间戳: {item.ntp}</div>
              <div>DID 签名者: {executorDid}</div>
              <div>样品编号: {sampleId || '-'}</div>
            </div>
          </button>
        ))}
      </div>

      {showAdvancedExecution && (
        <div className="mb-3 rounded-xl border border-dashed border-rose-600/60 bg-rose-950/20 p-3">
          <div className="mb-1 text-xs font-extrabold">变更补差 (Delta UTXO)</div>
          <div className="mb-3 grid grid-cols-2 gap-3 max-[1180px]:grid-cols-1">
            <input value={deltaAmount} onChange={(event) => onDeltaAmountChange(event.target.value)} placeholder="变更数量 (+/-)" className={inputBaseCls} />
            <input value={deltaReason} onChange={(event) => onDeltaReasonChange(event.target.value)} placeholder="变更原因" className={inputBaseCls} />
          </div>
          <button type="button" onClick={onApplyDelta} disabled={applyingDelta || !activeIsLeaf} className={`w-full px-3 py-2 text-sm font-bold disabled:opacity-60 ${btnAmberCls}`}>{applyingDelta ? '提交中...' : '提交变更补差'}</button>
          {!!variationRes && <div className="mt-1 text-[11px] text-amber-200">变更 Proof: {String(variationRes.output_proof_id || '')}</div>}
        </div>
      )}
    </>
  )
}
