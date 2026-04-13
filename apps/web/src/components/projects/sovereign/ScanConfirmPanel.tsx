type Props = {
  scanConfirmUri: string
  scanProofId: string
  scanPayload: string
  scanDid: string
  scanConfirmToken: string
  scanning: boolean
  showAcceptanceAdvanced: boolean
  scanRes: Record<string, unknown> | null
  inputBaseCls: string
  btnBlueCls: string
  btnGreenCls: string
  onScanPayloadChange: (value: string) => void
  onScanDidChange: (value: string) => void
  onScanProofIdChange: (value: string) => void
  onFillScanToken: () => void
  onScanConfirm: () => void
  onToggleAdvanced: () => void
}

export default function ScanConfirmPanel({
  scanConfirmUri,
  scanProofId,
  scanPayload,
  scanDid,
  scanConfirmToken,
  scanning,
  showAcceptanceAdvanced,
  scanRes,
  inputBaseCls,
  btnBlueCls,
  btnGreenCls,
  onScanPayloadChange,
  onScanDidChange,
  onScanProofIdChange,
  onFillScanToken,
  onScanConfirm,
  onToggleAdvanced,
}: Props) {
  return (
    <div className="border border-dashed border-slate-700 rounded-xl p-3 mt-3">
      <div className="text-xs font-extrabold mb-1">现场联合验收</div>
      <div className="text-[11px] text-slate-400 mb-2">验收 URI: {scanConfirmUri || '未生成'}</div>
      <div className="grid gap-2">
        <div className="rounded-lg border border-slate-800 bg-slate-900/60 px-3 py-2 text-[11px]">
          <div className="text-slate-400">当前构件 存证ID</div>
          <div className="text-slate-200 break-all">{scanProofId || '未绑定'}</div>
        </div>
        <textarea
          value={scanPayload}
          onChange={(event) => onScanPayloadChange(event.target.value)}
          placeholder="验收令牌（scan_confirm_token）"
          rows={3}
          className={`${inputBaseCls} resize-y`}
        />
        <input
          value={scanDid}
          onChange={(event) => onScanDidChange(event.target.value)}
          placeholder="验收人 DID"
          className={inputBaseCls}
        />
        <div className="grid grid-cols-2 gap-2">
          <button
            type="button"
            onClick={onFillScanToken}
            disabled={!scanConfirmToken}
            className={`px-3 py-2 text-sm disabled:opacity-60 ${btnBlueCls}`}
          >
            填充验收令牌
          </button>
          <button
            type="button"
            onClick={onScanConfirm}
            disabled={scanning}
            className={`px-3 py-2 text-sm font-bold ${btnGreenCls}`}
          >
            {scanning ? '验收中...' : '执行现场联合验收'}
          </button>
        </div>
        <button
          type="button"
          onClick={onToggleAdvanced}
          className="text-[11px] text-slate-400 text-left hover:text-slate-200"
        >
          {showAcceptanceAdvanced ? '收起高级设置 ▲' : '展开高级设置 ▼'}
        </button>
        {showAcceptanceAdvanced && (
          <div className="grid gap-2">
            <input
              value={scanProofId}
              onChange={(event) => onScanProofIdChange(event.target.value)}
              placeholder="手动指定 存证ID（可选）"
              className={inputBaseCls}
            />
          </div>
        )}
        {!!scanRes && (
          <div className="text-[11px] text-emerald-300">
            验收完成: {String((scanRes as Record<string, unknown>).output_proof_id || '')}
          </div>
        )}
      </div>
    </div>
  )
}

