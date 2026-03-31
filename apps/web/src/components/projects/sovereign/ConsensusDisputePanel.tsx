type Props = {
  minValueText: string
  maxValueText: string
  deviationText: string
  deviationPercentText: string
  consensusAllowedAbsText: string
  consensusAllowedPctText: string
  consensusConflict: boolean
  disputeProof: string
  disputeOpen: boolean
  disputeProofId: string
  disputeResolutionNote: string
  disputeResult: 'PASS' | 'REJECT'
  disputeResolving: boolean
  disputeResolveRes: Record<string, unknown> | null
  inputBaseCls: string
  btnAmberCls: string
  onCopyConflictSummary: () => void
  onJumpToDispute: () => void
  onDisputeProofIdChange: (value: string) => void
  onDisputeResolutionNoteChange: (value: string) => void
  onDisputeResultChange: (value: 'PASS' | 'REJECT') => void
  onResolveDispute: () => void
}

export default function ConsensusDisputePanel({
  minValueText,
  maxValueText,
  deviationText,
  deviationPercentText,
  consensusAllowedAbsText,
  consensusAllowedPctText,
  consensusConflict,
  disputeProof,
  disputeOpen,
  disputeProofId,
  disputeResolutionNote,
  disputeResult,
  disputeResolving,
  disputeResolveRes,
  inputBaseCls,
  btnAmberCls,
  onCopyConflictSummary,
  onJumpToDispute,
  onDisputeProofIdChange,
  onDisputeResolutionNoteChange,
  onDisputeResultChange,
  onResolveDispute,
}: Props) {
  return (
    <>
      <div className="border border-dashed border-slate-700 rounded-xl p-3 mt-3">
        <div className="text-xs font-extrabold mb-1">共识冲突检查器</div>
        <div className="text-[11px] text-slate-400 mb-2">对比多方签名元数据中的实测值，偏差超出 NormPeg 阈值将自动挂起结算 Trip。</div>
        <div className="grid gap-2">
          <div className="rounded-lg border border-slate-800 bg-slate-900/60 px-3 py-2 text-[11px] text-slate-300">
            <div>最小值: {minValueText}</div>
            <div>最大值: {maxValueText}</div>
            <div>偏差: {deviationText} ({deviationPercentText})</div>
            <div>阈值: {consensusAllowedAbsText} / {consensusAllowedPctText}</div>
          </div>
          <div className={`rounded-lg border px-3 py-2 text-[11px] ${consensusConflict ? 'border-rose-600/60 bg-rose-950/40 text-rose-100' : 'border-emerald-600/50 bg-emerald-950/30 text-emerald-200'}`}>
            {consensusConflict ? '共识冲突警告：将生成 Dispute UTXO 并锁定结算权限' : '共识一致：允许进入结算流程'}
          </div>
          <div className="grid grid-cols-[1fr_auto] gap-2">
            <button
              type="button"
              onClick={onCopyConflictSummary}
              className="px-3 py-2 text-sm border border-slate-700 rounded-lg bg-slate-900 text-slate-200 hover:bg-slate-800"
            >
              复制冲突摘要
            </button>
            <button
              type="button"
              onClick={onJumpToDispute}
              className={`px-3 py-2 text-sm font-bold ${btnAmberCls}`}
            >
              跳转仲裁
            </button>
          </div>
          <div className="text-[11px] text-slate-400">
            Dispute UTXO: {disputeProof || (consensusConflict ? '待生成' : '未触发')}
          </div>
        </div>
      </div>
      <div className="border border-dashed border-slate-700 rounded-xl p-3 mt-3">
        <div className="text-xs font-extrabold mb-1">共识争议仲裁</div>
        <div className="text-[11px] text-slate-400 mb-2">争议状态: {disputeOpen ? '待仲裁' : '暂无未决争议'}</div>
        <div className="text-[11px] text-slate-500 mb-2">Dispute UTXOResolution Trip：三方达成新哈希共识后解除锁定</div>
        <div className="grid gap-2">
          <input
            value={disputeProofId}
            onChange={(event) => onDisputeProofIdChange(event.target.value)}
            placeholder="争议 Proof ID"
            className={inputBaseCls}
          />
          <textarea
            value={disputeResolutionNote}
            onChange={(event) => onDisputeResolutionNoteChange(event.target.value)}
            placeholder="仲裁说明（可选）"
            rows={2}
            className={`${inputBaseCls} resize-y`}
          />
          <div className="grid grid-cols-2 gap-2">
            <select
              value={disputeResult}
              onChange={(event) => onDisputeResultChange(event.target.value as 'PASS' | 'REJECT')}
              className={inputBaseCls}
            >
              <option value="PASS">解除争议</option>
              <option value="REJECT">驳回/否决</option>
            </select>
            <button
              type="button"
              onClick={onResolveDispute}
              disabled={disputeResolving}
              className={`px-3 py-2 text-sm font-bold ${btnAmberCls}`}
            >
              {disputeResolving ? '仲裁中...' : '执行仲裁'}
            </button>
          </div>
          {!!disputeResolveRes && (
            <div className="text-[11px] text-emerald-300">
              仲裁 Proof: {String((disputeResolveRes as Record<string, unknown>).output_proof_id || (disputeResolveRes as Record<string, unknown>).proof_id || '')}
            </div>
          )}
        </div>
      </div>
    </>
  )
}
