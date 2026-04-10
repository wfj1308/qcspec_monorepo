type Props = {
  specdictProjectUris: string
  specdictMinSamples: string
  specdictNamespace: string
  specdictCommit: boolean
  specdictLoading: boolean
  specdictExporting: boolean
  specdictRuleTotal: number
  specdictHighRisk: number
  specdictBestPractice: number
  specdictBundleUri: string
  successPatterns: string[]
  highRiskItems: string[]
  bestPracticeItems: string[]
  weightEntriesText: string[]
  hasSpecdictRes: boolean
  inputBaseCls: string
  btnBlueCls: string
  btnGreenCls: string
  onProjectUrisChange: (value: string) => void
  onMinSamplesChange: (value: string) => void
  onNamespaceChange: (value: string) => void
  onCommitChange: (value: boolean) => void
  onRunSpecdictEvolve: () => void
  onRunSpecdictExport: () => void
  onOneClickWriteGlobal: () => void
}

export default function SpecdictPanel({
  specdictProjectUris,
  specdictMinSamples,
  specdictNamespace,
  specdictCommit,
  specdictLoading,
  specdictExporting,
  specdictRuleTotal,
  specdictHighRisk,
  specdictBestPractice,
  specdictBundleUri,
  successPatterns,
  highRiskItems,
  bestPracticeItems,
  weightEntriesText,
  hasSpecdictRes,
  inputBaseCls,
  btnBlueCls,
  btnGreenCls,
  onProjectUrisChange,
  onMinSamplesChange,
  onNamespaceChange,
  onCommitChange,
  onRunSpecdictEvolve,
  onRunSpecdictExport,
  onOneClickWriteGlobal,
}: Props) {
  return (
    <div className="border border-dashed border-slate-700 rounded-xl p-3 mt-3">
      <div className="text-xs font-extrabold mb-1">SpecDict 进化与迁移</div>
      <div className="text-[11px] text-slate-400 mb-2">项目 URI（逗号或换行分隔）</div>
      <div className="grid gap-2">
        <textarea
          value={specdictProjectUris}
          onChange={(event) => onProjectUrisChange(event.target.value)}
          rows={2}
          placeholder="v://cn/project-a, v://cn/project-b"
          className={`${inputBaseCls} resize-y`}
        />
        <div className="grid grid-cols-2 gap-2">
          <input
            value={specdictMinSamples}
            onChange={(event) => onMinSamplesChange(event.target.value)}
            placeholder="最小样本数"
            className={inputBaseCls}
          />
          <input
            value={specdictNamespace}
            onChange={(event) => onNamespaceChange(event.target.value)}
            placeholder="输出命名空间"
            className={inputBaseCls}
          />
        </div>
        <label className="flex items-center gap-2 text-[11px] text-slate-400">
          <input
            type="checkbox"
            checked={specdictCommit}
            onChange={(event) => onCommitChange(event.target.checked)}
          />
          写入 v://global/templates
        </label>
        <div className="grid grid-cols-2 gap-2">
          <button
            type="button"
            onClick={onRunSpecdictEvolve}
            disabled={specdictLoading}
            className={`px-3 py-2 text-sm font-bold ${btnBlueCls}`}
          >
            {specdictLoading ? '分析中...' : '分析进化'}
          </button>
          <button
            type="button"
            onClick={onRunSpecdictExport}
            disabled={specdictExporting}
            className={`px-3 py-2 text-sm font-bold ${btnGreenCls}`}
          >
            {specdictExporting ? '导出中...' : '导出模板'}
          </button>
        </div>
        <button
          type="button"
          onClick={onOneClickWriteGlobal}
          disabled={specdictExporting}
          className="px-3 py-2 text-sm font-bold border border-emerald-600/60 rounded-lg bg-emerald-900/40 text-emerald-100 hover:bg-emerald-900/60 disabled:opacity-60"
        >
          一键脱敏并写入全局
        </button>
        {hasSpecdictRes && (
          <div className="text-[11px] text-slate-400 grid gap-1">
            <div>规则 {specdictRuleTotal} · 高风险 {specdictHighRisk} · 最优参数 {specdictBestPractice}</div>
            <div>脱敏资产包: {specdictBundleUri || '待生成'} · 输出到 v://global/templates</div>
            {successPatterns.length > 0 && (
              <div>success_pattern: {successPatterns.join(' / ')}</div>
            )}
            {highRiskItems.length > 0 && (
              <div>高风险工序: {highRiskItems.join(' / ')}</div>
            )}
            {bestPracticeItems.length > 0 && (
              <div>最优参数: {bestPracticeItems.join(' / ')}</div>
            )}
            {weightEntriesText.length > 0 && (
              <div>默认权重建议: {weightEntriesText.join(' / ')}</div>
            )}
          </div>
        )}
      </div>
    </div>
  )
}
