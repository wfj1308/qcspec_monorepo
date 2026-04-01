type Props = {
  claimQty: string
  geoFormLocked: boolean
  disputeOpen: boolean
  archiveLocked: boolean
  claimQtyProvided: boolean
  measuredQtyValue: number
  deltaSuggest: number
  exceedBalance: boolean
  baselineTotal: number
  effectiveSpent: number
  effectiveClaimQtyValue: number
  isContractSpu: boolean
  inputBaseCls: string
  btnAmberCls: string
  onClaimQtyChange: (value: string) => void
  onSuggestDelta: () => void
}

export default function SettlementPreviewPanel({
  claimQty,
  geoFormLocked,
  disputeOpen,
  archiveLocked,
  claimQtyProvided,
  measuredQtyValue,
  deltaSuggest,
  exceedBalance,
  baselineTotal,
  effectiveSpent,
  effectiveClaimQtyValue,
  isContractSpu,
  inputBaseCls,
  btnAmberCls,
  onClaimQtyChange,
  onSuggestDelta,
}: Props) {
  const disabled = geoFormLocked || disputeOpen || archiveLocked
  const progress = Math.max(0, Math.min(100, baselineTotal > 0 ? ((effectiveSpent + effectiveClaimQtyValue) * 100) / baselineTotal : 0))

  return (
    <div className="rounded-xl border border-slate-700/70 bg-slate-950/30 p-3">
      <div className="mb-2 text-xs font-semibold text-slate-300">结算预警栏</div>
      <div className={`mb-2 rounded-lg px-2.5 py-1 text-[11px] font-semibold ${exceedBalance ? 'border border-rose-500/70 bg-rose-950/30 text-rose-200' : 'border border-emerald-500/60 bg-emerald-950/20 text-emerald-200'}`}>
        {exceedBalance ? '余额不足 | 需先执行变更补差 Trip' : '守恒通过 | 可继续提交'}
      </div>
      <div className="mb-2 grid grid-cols-3 gap-2 text-xs text-slate-300">
        <div>设计总量: {baselineTotal.toLocaleString()}</div>
        <div>已结算累计量: {effectiveSpent.toLocaleString()}</div>
        <div>剩余额度: {(baselineTotal - effectiveSpent).toLocaleString()}</div>
      </div>
      <div className="grid grid-cols-[1fr_auto] items-center gap-2">
        <input
          value={claimQty}
          disabled={disabled}
          onChange={(event) => onClaimQtyChange(event.target.value)}
          placeholder="本次申报量（留空则取实测值）"
          className={`${inputBaseCls} ${disabled ? 'cursor-not-allowed opacity-60' : ''}`}
        />
        <span className={`text-xs ${exceedBalance ? 'text-rose-300' : 'text-emerald-300'}`}>
          {exceedBalance ? 'Genesis UTXO Deviation Warning' : '余额充足'}
        </span>
      </div>
      {!isContractSpu && !claimQtyProvided && measuredQtyValue > 0 && (
        <div className="mt-1 text-[11px] text-slate-500">未填申报量，已取实测值 {measuredQtyValue.toLocaleString()}</div>
      )}
      <div className="mt-2 h-2.5 w-full overflow-hidden rounded-full border border-slate-700/70 bg-slate-900">
        <div className={`h-2.5 ${exceedBalance ? 'bg-rose-500' : 'bg-emerald-500'}`} style={{ width: `${progress}%` }} />
      </div>
      <div className="mt-1 text-[11px] text-slate-400">公式：申报量 + 已结算累计量 ≤ Genesis Approved 总量</div>
      <div className="mt-1 text-[11px] text-slate-500">当前申报量 + 已结算累计量 = {(effectiveSpent + effectiveClaimQtyValue).toLocaleString()}</div>
      {exceedBalance && deltaSuggest > 0 && (
        <div className="mt-2 flex items-center gap-2 text-[11px] text-rose-300">
          <span>建议补差量 {deltaSuggest.toFixed(3)}</span>
          <button type="button" onClick={onSuggestDelta} className={`rounded border border-amber-600/60 px-2 py-0.5 text-amber-200 ${btnAmberCls}`}>
            一键填入
          </button>
        </div>
      )}
    </div>
  )
}
