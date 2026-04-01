type ScanChainBadge = {
  cls: string
  label: string
}

type ComponentTypeOption = {
  value: string
  label: string
}

type Props = {
  activePathText: string
  templateDisplay: string
  isSpecBound: boolean
  isContractSpu: boolean
  specBinding: string
  gateBinding: string
  displayMeta: { unitProject: string; subdivisionProject: string }
  compType: string
  componentTypeOptions: ComponentTypeOption[]
  loadingCtx: boolean
  geoFormLocked: boolean
  scanEntryStatus: 'idle' | 'ok' | 'blocked'
  scanEntryAt: string
  scanEntryToken: string
  scanEntryRequired: boolean
  scanEntryTokenHash: string
  scanChainBadge: ScanChainBadge
  scanEntryLatest: Record<string, unknown> | null
  normRefs: string[]
  contextError: string
  sampleId: string
  executorDid: string
  inputBaseCls: string
  btnBlueCls: string
  toChineseCompType: (value: string) => string
  onScanEntry: () => void
  onScanEntryTokenChange: (value: string) => void
  onScanEntryRequiredChange: (checked: boolean) => void
  onSampleIdChange: (value: string) => void
  onCompTypeChange: (value: string) => void
  onExecutorDidChange: (value: string) => void
  onLoadContext: () => void
  canScan: boolean
  canLoadContext: boolean
}

export default function WorkbenchNodeContextPanel({
  activePathText,
  templateDisplay,
  isSpecBound,
  isContractSpu,
  specBinding,
  gateBinding,
  displayMeta,
  compType,
  componentTypeOptions,
  loadingCtx,
  geoFormLocked,
  scanEntryStatus,
  scanEntryAt,
  scanEntryToken,
  scanEntryRequired,
  scanEntryTokenHash,
  scanChainBadge,
  scanEntryLatest,
  normRefs,
  contextError,
  sampleId,
  executorDid,
  inputBaseCls,
  btnBlueCls,
  toChineseCompType,
  onScanEntry,
  onScanEntryTokenChange,
  onScanEntryRequiredChange,
  onSampleIdChange,
  onCompTypeChange,
  onExecutorDidChange,
  onLoadContext,
  canScan,
  canLoadContext,
}: Props) {
  const lockedCls = geoFormLocked ? 'cursor-not-allowed opacity-60' : ''

  return (
    <>
      <div className="mb-3 rounded-xl border border-slate-700/70 p-3 text-sm">
        <div className="mb-1 text-xs text-sky-300">当前节点</div>
        <div className="break-all">{activePathText || '-'}</div>
        <div className="mt-2 text-xs text-slate-400">模板绑定: {templateDisplay}</div>
        <div className={`text-xs ${isSpecBound ? 'text-emerald-300' : 'text-amber-300'}`}>
          规范绑定: {specBinding || (isContractSpu ? '合同凭证类' : '未绑定')}
          {gateBinding ? ` | 门控 ${gateBinding}` : ''}
        </div>
        <div className="text-xs text-slate-500">自动预填: {displayMeta.unitProject} / {displayMeta.subdivisionProject}</div>
        <div className="text-xs text-slate-500">构件类型: {toChineseCompType(compType)}</div>
        <div className="mt-2 grid grid-cols-[1fr_auto] items-center gap-2">
          <button type="button" onClick={onScanEntry} disabled={!canScan} className={`px-3 py-2 text-xs font-bold ${btnBlueCls} disabled:opacity-60`}>扫码进入节点</button>
          <div className="text-[11px] text-slate-400">
            扫码状态: {scanEntryStatus === 'ok' ? '已通过' : scanEntryStatus === 'blocked' ? '已拦截' : '未扫码'}
            {scanEntryAt ? ` | ${scanEntryAt.slice(11, 19)}` : ''}
          </div>
        </div>
        <div className="mt-2 grid gap-2">
          <div className="grid grid-cols-[1fr_auto] items-center gap-2">
            <input value={scanEntryToken} onChange={(event) => onScanEntryTokenChange(event.target.value)} placeholder="扫码令牌（scan_entry_token）" className={inputBaseCls} />
            <label className="flex items-center gap-2 text-[11px] text-slate-400">
              <input type="checkbox" checked={scanEntryRequired} onChange={(event) => onScanEntryRequiredChange(event.target.checked)} />
              令牌必填
            </label>
          </div>
          <div className="flex items-center gap-2 text-[11px] text-slate-400">
            <span>链状态</span>
            <span className={`rounded-full border px-2 py-0.5 ${scanChainBadge.cls}`}>{scanChainBadge.label}</span>
            {scanEntryLatest?.proof_id && <span className="truncate text-slate-500">Proof: {String(scanEntryLatest.proof_id || '-')}</span>}
          </div>
          {scanEntryTokenHash && <div className="break-all text-[11px] text-slate-500">令牌哈希: {scanEntryTokenHash}</div>}
        </div>
        {!!normRefs.length && <div className="text-xs text-slate-400">规范索引: {normRefs.join(' / ')}</div>}
        {!!contextError && <div className="mt-2 rounded-lg border border-amber-700/70 bg-amber-950/30 px-2 py-1.5 text-xs text-amber-300">{contextError}</div>}
        {!isSpecBound && <div className="mt-2 rounded-lg border border-rose-700/70 bg-rose-950/30 px-2 py-1.5 text-xs text-rose-300">未绑定规范/门控，已锁定提交</div>}
      </div>

      <div className="mb-3 grid grid-cols-2 gap-3 max-[1180px]:grid-cols-1">
        <input value={sampleId} disabled={geoFormLocked} onChange={(event) => onSampleIdChange(event.target.value)} placeholder="UTXO_Identifier（样品编号）" className={`${inputBaseCls} ${lockedCls}`} />
        <div className="rounded-lg border border-dashed border-slate-700 px-3 py-2 text-sm leading-5 text-slate-400">UTXO_Identifier 会自动映射到链上样品字段</div>
      </div>

      <div className="mb-3 grid grid-cols-[1fr_1fr_auto] gap-3 max-[1180px]:grid-cols-1">
        <select value={compType} disabled={geoFormLocked} onChange={(event) => onCompTypeChange(event.target.value)} className={`${inputBaseCls} ${lockedCls}`}>
          {componentTypeOptions.map((option) => <option key={option.value} value={option.value}>{option.label}</option>)}
        </select>
        <input value={executorDid} disabled={geoFormLocked} onChange={(event) => onExecutorDidChange(event.target.value)} placeholder="执行人 DID" className={`${inputBaseCls} ${lockedCls}`} />
        <button type="button" disabled={!canLoadContext} onClick={onLoadContext} className={`px-3 py-2 text-sm disabled:opacity-60 ${btnBlueCls}`}>
          {loadingCtx ? '加载中...' : '加载门控'}
        </button>
      </div>
    </>
  )
}
