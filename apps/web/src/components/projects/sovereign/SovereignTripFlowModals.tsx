type Props = {
  signOpen: boolean
  tripStage: 'Unspent' | 'Reviewing' | 'Approved'
  signStep: number
  signing: boolean
  executorDid: string
  supervisorDid: string
  ownerDid: string
  consensusContractorValue: string
  consensusSupervisorValue: string
  consensusOwnerValue: string
  consensusAllowedDeviation: string
  consensusAllowedDeviationPct: string
  consensusBaseValueText: string
  consensusConflict: boolean
  consensusMinValueText: string
  consensusMaxValueText: string
  consensusDeviationText: string
  consensusDeviationPercentText: string
  consensusAllowedAbsText: string
  consensusAllowedPctText: string
  inputBaseCls: string
  btnAmberCls: string
  scanLockStage: 'idle' | 'locking' | 'done'
  scanLockProofId: string
  deltaModalOpen: boolean
  exceedTotalText: string
  onCloseSignModal: () => void
  onDoSign: () => void
  onConsensusContractorValueChange: (value: string) => void
  onConsensusSupervisorValueChange: (value: string) => void
  onConsensusOwnerValueChange: (value: string) => void
  onConsensusAllowedDeviationChange: (value: string) => void
  onConsensusAllowedDeviationPctChange: (value: string) => void
  onCloseScanLock: () => void
  onOpenAdvancedExecution: () => void
}

export default function SovereignTripFlowModals({
  signOpen,
  tripStage,
  signStep,
  signing,
  executorDid,
  supervisorDid,
  ownerDid,
  consensusContractorValue,
  consensusSupervisorValue,
  consensusOwnerValue,
  consensusAllowedDeviation,
  consensusAllowedDeviationPct,
  consensusBaseValueText,
  consensusConflict,
  consensusMinValueText,
  consensusMaxValueText,
  consensusDeviationText,
  consensusDeviationPercentText,
  consensusAllowedAbsText,
  consensusAllowedPctText,
  inputBaseCls,
  btnAmberCls,
  scanLockStage,
  scanLockProofId,
  deltaModalOpen,
  exceedTotalText,
  onCloseSignModal,
  onDoSign,
  onConsensusContractorValueChange,
  onConsensusSupervisorValueChange,
  onConsensusOwnerValueChange,
  onConsensusAllowedDeviationChange,
  onConsensusAllowedDeviationPctChange,
  onCloseScanLock,
  onOpenAdvancedExecution,
}: Props) {
  return (
    <>
      {signOpen && (
        <div className="fixed inset-0 z-[1200] grid place-items-center bg-slate-950/70">
          <div className="w-[460px] max-w-[92vw] rounded-xl border border-slate-700 bg-slate-950 p-4 text-slate-100">
            <div className="mb-2 text-sm font-extrabold">OrdoSign 共识签认</div>
            <div className="mb-3 text-xs text-slate-400">DID 签名链路: 施工员 → 监理 → 业主</div>
            <div className="mb-3 rounded-xl border border-slate-700/80 bg-slate-900/60 px-3 py-3">
              <div className="flex items-center justify-between text-[10px] uppercase tracking-[0.14em] text-slate-500">
                <span>TripRole Flow</span>
                <span>{tripStage}</span>
              </div>
              <div className="mt-3 flex items-center justify-between gap-2">
                {[
                  { step: 1, label: '施工员', active: signStep >= 1 },
                  { step: 2, label: '监理', active: signStep >= 2 },
                  { step: 3, label: '业主', active: signStep >= 3 },
                ].map((item, idx) => (
                  <div key={`sign-step-wrap-${item.step}`} className="contents">
                    <div className="flex min-w-0 flex-1 flex-col items-center gap-1">
                      <div
                        className={`grid h-8 w-8 place-items-center rounded-full border text-[11px] font-bold ${
                          item.active
                            ? 'border-emerald-500/70 bg-emerald-950/40 text-emerald-200 shadow-[0_0_16px_rgba(16,185,129,.22)]'
                            : 'border-slate-600/70 bg-slate-950/80 text-slate-400'
                        }`}
                      >
                        {item.step}
                      </div>
                      <div className={`text-[11px] ${item.active ? 'text-emerald-200' : 'text-slate-500'}`}>{item.label}</div>
                    </div>
                    {idx < 2 && (
                      <div className={`h-px flex-1 ${signStep > item.step ? 'bg-emerald-500/70' : 'bg-slate-700/80'}`} />
                    )}
                  </div>
                ))}
              </div>
            </div>
            <div className="mb-3 rounded-lg border border-slate-700/70 bg-slate-900/40 px-3 py-2">
              <div className="flex items-center gap-2 text-[11px]">
                <span className={`rounded-full border px-2 py-0.5 ${tripStage === 'Unspent' ? 'border-slate-500/70 text-slate-300' : 'border-slate-700/60 text-slate-500'}`}>Unspent</span>
                <span className="text-slate-600">→</span>
                <span className={`rounded-full border px-2 py-0.5 ${tripStage === 'Reviewing' ? 'border-sky-500/70 text-sky-200' : tripStage === 'Approved' ? 'border-sky-700/60 text-sky-400' : 'border-slate-700/60 text-slate-500'}`}>Reviewing</span>
                <span className="text-slate-600">→</span>
                <span className={`rounded-full border px-2 py-0.5 ${tripStage === 'Approved' ? 'border-emerald-500/70 text-emerald-200' : 'border-slate-700/60 text-slate-500'}`}>Approved</span>
              </div>
            </div>
            {signing && (
              <div className="mb-3 flex items-center gap-3 rounded-xl border border-emerald-500/60 bg-emerald-950/20 p-3">
                <div className="h-10 w-10 rounded-full border border-emerald-400/80" style={{ animation: 'ordosealPulse 1.2s infinite ease-in-out' }} />
                <div className="text-xs text-emerald-200">OrdoSign 封印中，正在生成主权签章与 total_proof_hash ...</div>
              </div>
            )}
            <div className="mb-3 grid gap-2">
              {[
                { step: 1, label: '施工方', did: executorDid },
                { step: 2, label: '监理', did: supervisorDid },
                { step: 3, label: '业主', did: ownerDid },
              ].map((item) => (
                <div key={`signer-${item.step}`} className="flex items-center justify-between rounded-lg border border-slate-700 bg-slate-900/35 p-2 text-xs">
                  <div className="min-w-0">
                    <div className="flex items-center gap-2">
                      <div>{item.label} 签名</div>
                      <span className="rounded-full border border-slate-700/80 bg-slate-950/80 px-2 py-0.5 text-[10px] text-slate-400">
                        DID {item.did ? `${item.did.slice(0, 10)}...` : '-'}
                      </span>
                    </div>
                    <div className="mt-1 truncate text-slate-400">{item.did}</div>
                  </div>
                  <div className={`font-bold ${signStep >= item.step ? 'text-emerald-300' : 'text-slate-500'}`}>
                    {signStep >= item.step ? '已签' : '待签'}
                  </div>
                </div>
              ))}
            </div>
            <div className="mb-3 rounded-lg border border-slate-700/80 bg-slate-900/40 px-3 py-2 text-[11px] text-slate-400">
              审批完成后，节点状态会从 <span className="text-sky-300">Reviewing</span> 切换到 <span className="text-emerald-300">Approved</span>，并触发 SMU 冻结与 DocPeg 哈希锁定。
            </div>
            <div className="mb-3 rounded-lg border border-slate-700/80 p-2 text-[11px] text-slate-300">
              <div className="mb-2 font-semibold text-slate-200">共识量值（可调以触发冲突）</div>
              <div className="grid gap-2">
                <input
                  value={consensusContractorValue}
                  onChange={(e) => onConsensusContractorValueChange(e.target.value)}
                  placeholder={`施工方量值（默认 ${consensusBaseValueText}）`}
                  className={inputBaseCls}
                />
                <input
                  value={consensusSupervisorValue}
                  onChange={(e) => onConsensusSupervisorValueChange(e.target.value)}
                  placeholder={`监理量值（默认 ${consensusBaseValueText}）`}
                  className={inputBaseCls}
                />
                <input
                  value={consensusOwnerValue}
                  onChange={(e) => onConsensusOwnerValueChange(e.target.value)}
                  placeholder={`业主量值（默认 ${consensusBaseValueText}）`}
                  className={inputBaseCls}
                />
                <div className="grid grid-cols-2 gap-2">
                  <input
                    value={consensusAllowedDeviation}
                    onChange={(e) => onConsensusAllowedDeviationChange(e.target.value)}
                    placeholder="允许偏差（绝对值）"
                    className={inputBaseCls}
                  />
                  <input
                    value={consensusAllowedDeviationPct}
                    onChange={(e) => onConsensusAllowedDeviationPctChange(e.target.value)}
                    placeholder="允许偏差（%）"
                    className={inputBaseCls}
                  />
                </div>
                <div className="text-[10px] text-slate-500">未填写时使用默认量值与系统阈值（约 0.5%）。</div>
                <div className={`rounded-lg border px-3 py-2 text-[11px] ${consensusConflict ? 'border-rose-600/60 bg-rose-950/40 text-rose-100' : 'border-slate-700/70 bg-slate-900/40 text-slate-300'}`}>
                  <div className="mb-1 font-semibold">共识冲突检查器</div>
                  <div className="text-slate-400">
                    最小 {consensusMinValueText} · 最大 {consensusMaxValueText} · 偏差 {consensusDeviationText} ({consensusDeviationPercentText})
                  </div>
                  <div className="text-slate-400">允许偏差: {consensusAllowedAbsText} / {consensusAllowedPctText}</div>
                  <div className={consensusConflict ? 'text-rose-200' : 'text-emerald-300'}>
                    {consensusConflict ? '检测到逻辑背离，将触发 Dispute UTXO 并挂起结算 Trip' : '共识一致，允许进入结算'}
                  </div>
                </div>
              </div>
            </div>
            <div className="flex justify-end gap-2">
              <button type="button" onClick={onCloseSignModal} disabled={signing} className="rounded-lg border border-slate-700 bg-slate-900 px-3 py-2 text-slate-200">取消</button>
              <button type="button" onClick={onDoSign} disabled={signing} className={`px-3 py-2 font-bold ${btnAmberCls}`}>
                {signing ? '签认中...' : '执行多方签认'}
              </button>
            </div>
          </div>
        </div>
      )}

      {scanLockStage !== 'idle' && (
        <div className="fixed inset-0 z-[1300] grid place-items-center bg-slate-950/90">
          <div className="w-[520px] max-w-[92vw] rounded-2xl border border-emerald-700/60 bg-gradient-to-b from-emerald-950/70 via-slate-950/90 to-slate-950 p-6 text-center text-slate-100 shadow-[0_0_40px_rgba(16,185,129,0.25)]">
            {scanLockStage === 'locking' ? (
              <>
                <div className="mb-2 text-lg font-extrabold">主权资产锁定中...</div>
                <div className="mb-5 text-xs text-emerald-200/80">请勿关闭，链上指纹正在生成</div>
                <div className="flex items-center justify-center">
                  <div className="h-16 w-16 animate-spin rounded-full border-2 border-emerald-400/60 border-t-transparent" />
                </div>
              </>
            ) : (
              <>
                <div className="mb-2 text-lg font-extrabold">资产已锁定</div>
                <div className="mb-4 text-xs text-emerald-200/80">Final Proof 已生成</div>
                <div className="break-all rounded-lg border border-emerald-700/70 bg-emerald-950/40 px-3 py-2 text-[11px]">
                  {scanLockProofId || '未返回 Proof ID'}
                </div>
                <button
                  type="button"
                  onClick={onCloseScanLock}
                  className="mt-4 rounded-lg border border-emerald-500/70 bg-emerald-900/70 px-4 py-2 text-sm font-bold text-emerald-100 hover:bg-emerald-800/80"
                >
                  关闭
                </button>
              </>
            )}
          </div>
        </div>
      )}

      {deltaModalOpen && (
        <div className="fixed inset-0 z-[1200] grid place-items-center bg-slate-950/70">
          <div className="w-[520px] max-w-[92vw] rounded-xl border border-rose-700 bg-slate-950 p-4 text-slate-100">
            <div className="mb-2 text-sm font-extrabold">量值超出批复边界</div>
            <div className="mb-3 text-xs text-slate-300">当前申报量已超过批复量，请执行变更补差 Trip 后再提交。</div>
            <div className="mb-3 text-xs text-slate-400">申报量 + 已结算累计量 = {exceedTotalText}</div>
            <div className="flex justify-end gap-2">
              <button type="button" onClick={onOpenAdvancedExecution} className={`px-3 py-2 font-bold ${btnAmberCls}`}>
                执行变更补差
              </button>
            </div>
          </div>
        </div>
      )}
    </>
  )
}
