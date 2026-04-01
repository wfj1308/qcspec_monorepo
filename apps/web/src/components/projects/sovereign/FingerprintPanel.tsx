type MerkleStep = {
  depth: number
  position: string
  sibling_hash: string
  combined_hash: string
}

type Props = {
  currentSubdivisionText: string
  showFingerprintAdvanced: boolean
  unitLoading: boolean
  unitProofId: string
  unitMaxRows: string
  unitRes: Record<string, unknown> | null
  unitVerifying: boolean
  unitVerifyMsg: string
  itemPathSteps: MerkleStep[]
  unitPathSteps: MerkleStep[]
  inputBaseCls: string
  btnBlueCls: string
  btnAmberCls: string
  onToggleFingerprintAdvanced: () => void
  onUnitProofIdChange: (value: string) => void
  onUnitMaxRowsChange: (value: string) => void
  onCalcUnitMerkle: () => void
  onUseCurrentProofForUnit: () => void
  onVerifyUnitMerkle: () => void
  onExportMerkleJson: () => void
}

function renderMerkleSteps(title: string, steps: MerkleStep[]) {
  return (
    <div>
      <div className="mb-1 text-[11px] text-slate-200">{title}</div>
      <div className="grid gap-2">
        {steps.length === 0 && <div className="text-[11px] text-slate-500">无路径</div>}
        {steps.map((step, index) => (
          <div key={`${title}-${index}`} className="rounded border border-slate-800 p-2 text-[11px]">
            <div>深度 {step.depth} | 方向 {step.position}</div>
            <div className="break-all text-slate-400">兄弟哈希: 已锁定</div>
            <div className="break-all text-emerald-300">合并哈希: 已锁定</div>
          </div>
        ))}
      </div>
    </div>
  )
}

export default function FingerprintPanel({
  currentSubdivisionText,
  showFingerprintAdvanced,
  unitLoading,
  unitProofId,
  unitMaxRows,
  unitRes,
  unitVerifying,
  unitVerifyMsg,
  itemPathSteps,
  unitPathSteps,
  inputBaseCls,
  btnBlueCls,
  btnAmberCls,
  onToggleFingerprintAdvanced,
  onUnitProofIdChange,
  onUnitMaxRowsChange,
  onCalcUnitMerkle,
  onUseCurrentProofForUnit,
  onVerifyUnitMerkle,
  onExportMerkleJson,
}: Props) {
  return (
    <div className="mt-3 rounded-xl border border-dashed border-slate-700 p-3">
      <div className="mb-1 text-xs font-extrabold">数字资产总指纹</div>
      <div className="grid gap-2">
        <div className="rounded-lg border border-slate-800 bg-slate-900/60 px-3 py-2 text-[11px] text-slate-300">
          当前分部/分项: {currentSubdivisionText}
        </div>
        <div className="grid grid-cols-[1fr_auto] gap-2">
          <button type="button" onClick={onCalcUnitMerkle} disabled={unitLoading} className={`px-3 py-2 text-sm font-bold ${btnAmberCls}`}>
            {unitLoading ? '计算中...' : '生成数字资产总指纹'}
          </button>
          <button type="button" onClick={onUseCurrentProofForUnit} className={`px-3 py-2 text-sm ${btnBlueCls}`}>同步当前细目</button>
        </div>
        <button type="button" onClick={onToggleFingerprintAdvanced} className="text-left text-[11px] text-slate-400 hover:text-slate-200">
          {showFingerprintAdvanced ? '收起高级参数 ▲' : '展开高级参数 ▼'}
        </button>
        {showFingerprintAdvanced && (
          <div className="grid gap-2">
            <input value={unitProofId} onChange={(event) => onUnitProofIdChange(event.target.value)} placeholder="证明 ID（可选）" className={inputBaseCls} />
            <input value={unitMaxRows} onChange={(event) => onUnitMaxRowsChange(event.target.value)} placeholder="最大扫描行数" className={inputBaseCls} />
          </div>
        )}
        {!!unitRes && (
          <div className="break-all text-[11px] text-slate-400">
            <div>分部/分项总指纹: 已锁定</div>
            <div>项目总指纹: 已锁定</div>
            <div>叶子数量: {String(unitRes.leaf_count || 0)}</div>
            <div>请求叶子: {String(((unitRes.requested_leaf || {}) as Record<string, unknown>).item_uri || '')}</div>
          </div>
        )}
        {!!unitRes && (
          <div className="mt-1 rounded-lg border border-slate-800 p-2">
            <div className="mb-2 text-xs font-extrabold">本地校验器</div>
            <div className="mb-2 grid grid-cols-[1fr_auto] gap-2">
              <button type="button" onClick={onVerifyUnitMerkle} disabled={unitVerifying} className="rounded-lg border border-emerald-500/80 bg-emerald-900/80 px-3 py-2 text-sm font-bold text-emerald-100">
                {unitVerifying ? '校验中...' : '校验链路一致性'}
              </button>
              <div className={`grid items-center text-[11px] ${unitVerifyMsg.includes('通过') ? 'text-emerald-300' : 'text-red-300'}`}>
                {unitVerifyMsg || '未校验'}
              </div>
            </div>
            {!!(itemPathSteps.length || unitPathSteps.length) && (
              <div className="mt-2 grid gap-2">
                <div className="flex justify-end">
                  <button type="button" onClick={onExportMerkleJson} className="rounded border border-blue-700 bg-blue-900 px-2 py-1 text-[11px] text-blue-100">导出默克尔 JSON</button>
                </div>
                {renderMerkleSteps('叶子路径演算', itemPathSteps)}
                {renderMerkleSteps('单位路径演算', unitPathSteps)}
              </div>
            )}
          </div>
        )}
      </div>
    </div>
  )
}
