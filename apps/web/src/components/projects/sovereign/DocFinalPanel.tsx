type Props = {
  archiveLocked: boolean
  docFinalPassphrase: string
  docFinalIncludeUnsettled: boolean
  docFinalExporting: boolean
  docFinalFinalizing: boolean
  docFinalRes: Record<string, unknown> | null
  docFinalAuditUrl: string
  docFinalVerifyBaseUrl: string
  verifyUri: string
  disputeOpen: boolean
  disputeProofShort: string
  offlineQueueSize: number
  offlineSyncConflicts: number
  apiProjectUri: string
  docFinalQrSrc: string
  inputBaseCls: string
  btnBlueCls: string
  btnGreenCls: string
  onDocFinalPassphraseChange: (value: string) => void
  onDocFinalIncludeUnsettledChange: (value: boolean) => void
  onExportProjectDocFinal: () => void
  onFinalizeProjectDocFinal: () => void
}

export default function DocFinalPanel({
  archiveLocked,
  docFinalPassphrase,
  docFinalIncludeUnsettled,
  docFinalExporting,
  docFinalFinalizing,
  docFinalRes,
  docFinalAuditUrl,
  docFinalVerifyBaseUrl,
  verifyUri,
  disputeOpen,
  disputeProofShort,
  offlineQueueSize,
  offlineSyncConflicts,
  apiProjectUri,
  docFinalQrSrc,
  inputBaseCls,
  btnBlueCls,
  btnGreenCls,
  onDocFinalPassphraseChange,
  onDocFinalIncludeUnsettledChange,
  onExportProjectDocFinal,
  onFinalizeProjectDocFinal,
}: Props) {
  return (
    <div className="border border-dashed border-slate-700 rounded-xl p-3 mt-3">
      <div className="flex flex-wrap items-start justify-between gap-3">
        <div>
          <div className="text-xs font-extrabold mb-1">DocFinal 穿透式导出</div>
          <div className="text-[11px] text-slate-400">聚合 Genesis / Trip / Lab 指纹，并在导出后可触发 Archive_Trip 封存。</div>
        </div>
        <span className={`rounded-full border px-2 py-0.5 text-[11px] ${archiveLocked ? 'border-sky-500/60 bg-sky-950/30 text-sky-200' : 'border-slate-600 bg-slate-900/60 text-slate-300'}`}>
          {archiveLocked ? '已封存只读' : '可导出'}
        </span>
      </div>
      <div className="mt-3 grid gap-3 xl:grid-cols-[minmax(0,1fr)_140px]">
        <div className="grid gap-2">
          <input
            value={docFinalPassphrase}
            onChange={(event) => onDocFinalPassphraseChange(event.target.value)}
            placeholder="封存口令（可选）"
            className={inputBaseCls}
          />
          <label className="flex items-center gap-2 text-[11px] text-slate-400">
            <input
              type="checkbox"
              checked={docFinalIncludeUnsettled}
              onChange={(event) => onDocFinalIncludeUnsettledChange(event.target.checked)}
            />
            导出时包含未结项
          </label>
          <div className="grid grid-cols-2 gap-2">
            <button
              type="button"
              onClick={onExportProjectDocFinal}
              disabled={docFinalExporting || !apiProjectUri}
              className={`px-3 py-2 text-sm font-bold disabled:opacity-60 ${btnBlueCls}`}
            >
              {docFinalExporting ? '导出中...' : '导出审计 PDF'}
            </button>
            <button
              type="button"
              onClick={onFinalizeProjectDocFinal}
              disabled={docFinalFinalizing || !apiProjectUri || archiveLocked}
              className={`px-3 py-2 text-sm font-bold disabled:opacity-60 ${btnGreenCls}`}
            >
              {docFinalFinalizing ? '封存中...' : archiveLocked ? '已封存' : '发起 Archive_Trip'}
            </button>
          </div>
          <div className="rounded-lg border border-slate-800 bg-slate-900/60 px-3 py-2 text-[11px] text-slate-300">
            <div>穿透链接: {docFinalAuditUrl || verifyUri || '-'}</div>
            <div>验真基座: {docFinalVerifyBaseUrl || '-'}</div>
            <div>争议状态: {disputeOpen ? `挂起 ${disputeProofShort || '-'}` : '清零'}</div>
            <div>离线待同步: {offlineQueueSize} 条{offlineSyncConflicts > 0 ? ` · 向量钟冲突折叠 ${offlineSyncConflicts}` : ''}</div>
          </div>
          {!!docFinalRes && (
            <div className="rounded-lg border border-emerald-700/50 bg-emerald-950/20 px-3 py-2 text-[11px] text-emerald-200">
              <div>模式: {String(docFinalRes.mode || '-')}</div>
              <div>Proof: {String(docFinalRes.proofId || '-')}</div>
              <div>根哈希: {String(docFinalRes.rootHash || '-')}</div>
              <div>GitPeg: {String(docFinalRes.finalGitpegAnchor || docFinalRes.gitpegAnchor || '-')}</div>
              <div>文件: {String(docFinalRes.filename || '-')}</div>
            </div>
          )}
        </div>
        <div className="rounded-xl border border-slate-700 bg-slate-950/60 p-3 text-center">
          <img src={docFinalQrSrc} alt="DocFinal audit QR" className="mx-auto h-[120px] w-[120px]" />
          <div className="mt-2 text-[11px] text-slate-400">扫描直达证据中心审计页</div>
        </div>
      </div>
    </div>
  )
}

