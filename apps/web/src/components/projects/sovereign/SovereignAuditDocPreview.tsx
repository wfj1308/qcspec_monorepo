import type { MutableRefObject } from 'react'

type SignRole = 'contractor' | 'supervisor' | 'owner'

type SignMarker = {
  x: number
  y: number
} | null

type Props = {
  consensusConflict: boolean
  disputeOpen: boolean
  disputeProof: string
  consensusDeviationText: string
  consensusDeviationPercentText: string
  consensusAllowedAbsText: string
  consensusAllowedPctText: string
  finalProofReady: boolean
  qrSrc: string
  verifyUri: string
  finalProofId: string
  signFocus: SignRole | ''
  signStep: number
  executorDid: string
  supervisorDid: string
  ownerDid: string
  inputBaseCls: string
  onScrollToSign: (role: SignRole) => void
  onSupervisorDidChange: (value: string) => void
  onOwnerDidChange: (value: string) => void
  previewPdfB64: string
  pdfB64: string
  previewIsDraft: boolean
  tripStage: 'Unspent' | 'Reviewing' | 'Approved'
  evidenceCount: number
  totalHash: string
  activeCode: string
  activePath: string
  activeUri: string
  gatePass: number
  gateTotal: number
  reportedPctText: string
  onCopyText: (label: string, value: string) => void
  onOpenDocModal: () => void
  activeSignMarker: SignMarker
  pdfPage: number
  templateSourceText: string
  contractorAnchorRef: MutableRefObject<HTMLDivElement | null>
  supervisorAnchorRef: MutableRefObject<HTMLDivElement | null>
  ownerAnchorRef: MutableRefObject<HTMLDivElement | null>
  previewScrollRef: MutableRefObject<HTMLDivElement | null>
  pdfCanvasRef: MutableRefObject<HTMLCanvasElement | null>
  pdfRenderLoading: boolean
  pdfRenderError: string
  draftReady: boolean
  templateDisplay: string
  docModalOpen: boolean
  sampleId: string
  onCloseDocModal: () => void
}

export default function SovereignAuditDocPreview({
  consensusConflict,
  disputeOpen,
  disputeProof,
  consensusDeviationText,
  consensusDeviationPercentText,
  consensusAllowedAbsText,
  consensusAllowedPctText,
  finalProofReady,
  qrSrc,
  verifyUri,
  finalProofId,
  signFocus,
  signStep,
  executorDid,
  supervisorDid,
  ownerDid,
  inputBaseCls,
  onScrollToSign,
  onSupervisorDidChange,
  onOwnerDidChange,
  previewPdfB64,
  pdfB64,
  previewIsDraft,
  tripStage,
  evidenceCount,
  totalHash,
  activeCode,
  activePath,
  activeUri,
  gatePass,
  gateTotal,
  reportedPctText,
  onCopyText,
  onOpenDocModal,
  activeSignMarker,
  pdfPage,
  templateSourceText,
  contractorAnchorRef,
  supervisorAnchorRef,
  ownerAnchorRef,
  previewScrollRef,
  pdfCanvasRef,
  pdfRenderLoading,
  pdfRenderError,
  draftReady,
  templateDisplay,
  docModalOpen,
  sampleId,
  onCloseDocModal,
}: Props) {
  return (
    <>
      {(consensusConflict || disputeOpen) && (
        <div className={`mb-3 rounded-xl border p-3 ${consensusConflict ? 'border-rose-600/70 bg-rose-950/30 text-rose-100' : 'border-amber-600/70 bg-amber-950/30 text-amber-100'}`}>
          <div className="text-xs font-extrabold">共识冲突警告</div>
          <div className="mt-1 text-[11px]">
            偏差 {consensusDeviationText} ({consensusDeviationPercentText}) · 阈值 {consensusAllowedAbsText}/{consensusAllowedPctText}
          </div>
          <div className="mt-1 text-[11px]">Dispute UTXO: {disputeProof || (consensusConflict ? '待生成' : '-')}</div>
          <div className="mt-1 text-[11px]">结算权限已锁定，需通过 Dispute UTXOResolution Trip 解除。</div>
        </div>
      )}

      {finalProofReady && (
        <div className="mb-3 rounded-xl border border-emerald-500/70 bg-emerald-950/30 p-3 shadow-[0_0_24px_rgba(16,185,129,0.2)]">
          <div className="text-xs font-extrabold text-emerald-200">Final Proof · 主权二维码</div>
          <div className="mt-2 grid items-center gap-3 max-[600px]:grid-cols-1 grid-cols-[140px_1fr]">
            <div className="grid h-[140px] w-[140px] place-items-center border border-emerald-500/60 bg-white">
              <img src={qrSrc} alt="Final Proof 二维码" className="h-[128px] w-[128px]" />
            </div>
            <div className="text-xs leading-5 text-emerald-100">
              <div>扫码溯源验证 Final Proof</div>
              <div className="mt-1 break-all text-emerald-200">{verifyUri || '未生成验真 URI'}</div>
              {finalProofId && <div className="mt-1 break-all text-emerald-300">Proof ID: {finalProofId}</div>}
            </div>
          </div>
        </div>
      )}

      <div className="grid gap-3 min-[1100px]:grid-cols-[280px_1fr]">
        <div className="rounded-xl border border-slate-700 bg-slate-950/30 p-3">
          <div className="mb-2 text-xs text-sky-300">DID 身份卡片</div>
          <div className="relative pl-4">
            <div className="absolute bottom-3 left-1.5 top-3 w-px bg-slate-700/70" />
            {[
              { key: 'contractor' as const, label: '施工员', did: executorDid, step: 1 },
              { key: 'supervisor' as const, label: '监理', did: supervisorDid, step: 2 },
              { key: 'owner' as const, label: '业主', did: ownerDid, step: 3 },
            ].map((item) => {
              const activeCard = signFocus === item.key
              const signed = signStep >= item.step
              return (
                <button
                  type="button"
                  key={item.key}
                  onClick={() => onScrollToSign(item.key)}
                  className={`mb-2 w-full cursor-pointer rounded-xl border px-3 py-2 text-left transition ${activeCard ? 'border-emerald-500/70 bg-emerald-950/30' : 'border-slate-700/70 bg-slate-950/40 hover:border-slate-500/60'}`}
                >
                  <div className="flex items-center justify-between">
                    <div className="text-sm font-bold text-slate-100">{item.label}</div>
                    <div className={`text-[11px] font-semibold ${signed ? 'text-emerald-300' : 'text-slate-400'}`}>{signed ? '已签' : '待签'}</div>
                  </div>
                  <div className="mt-1 text-[11px] text-slate-400">{item.did}</div>
                  <div className="mt-2 flex items-center gap-1 text-[11px] text-emerald-300">
                    <svg width="14" height="14" viewBox="0 0 24 24" fill="none" aria-hidden="true">
                      <path d="M12 3l7 3v6c0 5-3.5 9-7 12-3.5-3-7-7-7-12V6l7-3Z" stroke="currentColor" strokeWidth="1.6" strokeLinejoin="round" />
                      <path d="M9 12l2 2 4-4" stroke="currentColor" strokeWidth="1.6" strokeLinecap="round" strokeLinejoin="round" />
                    </svg>
                    CA 认证已通过
                  </div>
                </button>
              )
            })}
          </div>
          <div className="mt-3 grid gap-2">
            <input value={supervisorDid} onChange={(e) => onSupervisorDidChange(e.target.value)} placeholder="监理 DID" className={inputBaseCls} />
            <input value={ownerDid} onChange={(e) => onOwnerDidChange(e.target.value)} placeholder="业主 DID" className={inputBaseCls} />
          </div>
        </div>

        <div className="rounded-xl border border-slate-700 bg-slate-950/30 p-3">
          <div className="mb-2 flex items-center justify-between">
            <div className="text-xs text-slate-400">DocPeg 分屏预览 · 共识见证</div>
            <div className={`text-[11px] ${previewPdfB64 ? 'text-emerald-300' : 'text-slate-400'}`}>
              {pdfB64 ? '正式 DocPeg 已生成' : previewIsDraft ? '草稿已编译' : '等待施工员签认'}
            </div>
          </div>
          <div className="mb-3 grid gap-2 min-[720px]:grid-cols-4">
            <div className="rounded-xl border border-slate-700/80 bg-slate-900/70 px-3 py-2">
              <div className="text-[10px] uppercase tracking-[0.16em] text-slate-500">提交流程</div>
              <div className={`mt-1 text-sm font-semibold ${tripStage === 'Approved' ? 'text-emerald-300' : tripStage === 'Reviewing' ? 'text-sky-300' : 'text-slate-200'}`}>
                {tripStage === 'Approved' ? '已批准' : tripStage === 'Reviewing' ? '审核中' : '未提交'}
              </div>
            </div>
            <div className="rounded-xl border border-slate-700/80 bg-slate-900/70 px-3 py-2">
              <div className="text-[10px] uppercase tracking-[0.16em] text-slate-500">证明ID</div>
              <div className="mt-1 text-sm font-semibold text-slate-100">{finalProofId ? `${finalProofId.slice(0, 10)}...` : '-'}</div>
            </div>
            <div className="rounded-xl border border-slate-700/80 bg-slate-900/70 px-3 py-2">
              <div className="text-[10px] uppercase tracking-[0.16em] text-slate-500">SnapPeg</div>
              <div className="mt-1 text-sm font-semibold text-slate-100">{evidenceCount}</div>
            </div>
            <div className="rounded-xl border border-slate-700/80 bg-slate-900/70 px-3 py-2">
              <div className="text-[10px] uppercase tracking-[0.16em] text-slate-500">哈希锁</div>
              <div className="mt-1 text-sm font-semibold text-slate-100">{totalHash ? `${totalHash.slice(0, 10)}...` : '-'}</div>
            </div>
          </div>
          <div className="mb-3 rounded-xl border border-slate-700/80 bg-[linear-gradient(135deg,rgba(15,23,42,.95),rgba(8,47,73,.24))] px-3 py-2 text-[11px] text-slate-300">
            <div className="flex flex-wrap items-center justify-between gap-2">
              <span className="text-slate-400">当前 SMU 路径</span>
              <span className={`rounded-full border px-2 py-0.5 ${previewIsDraft ? 'border-amber-500/60 text-amber-200 bg-amber-950/30' : 'border-emerald-500/60 text-emerald-200 bg-emerald-950/30'}`}>
                {previewIsDraft ? '草稿预览' : '验真预览'}
              </span>
            </div>
            <div className="mt-1 break-all font-mono text-slate-100">{activePath || activeUri || '-'}</div>
            <div className="mt-1 text-slate-500">门控通过 {gatePass}/{gateTotal || 0} · 已报验 {reportedPctText}%</div>
          </div>
          <div className="mb-3 flex flex-wrap items-center gap-2">
            <button
              type="button"
              onClick={() => onCopyText('验真 URI', verifyUri || '')}
              disabled={!verifyUri}
              className="rounded-lg border border-slate-700 bg-slate-900/80 px-3 py-1.5 text-[11px] text-slate-200 disabled:opacity-50"
            >
              复制验真 URI
            </button>
            <button
              type="button"
              onClick={() => onCopyText('Proof ID', finalProofId || '')}
              disabled={!finalProofId}
              className="rounded-lg border border-slate-700 bg-slate-900/80 px-3 py-1.5 text-[11px] text-slate-200 disabled:opacity-50"
            >
              复制证明ID
            </button>
            <button
              type="button"
              onClick={onOpenDocModal}
              disabled={!previewPdfB64}
              className="rounded-lg border border-sky-500/60 bg-sky-950/30 px-3 py-1.5 text-[11px] text-sky-200 disabled:opacity-50"
            >
              全屏预览
            </button>
          </div>
          {previewPdfB64 && signFocus && !activeSignMarker && (
            <div className="mb-2 text-[11px] text-amber-300">未提供签认坐标，已定位到第 {pdfPage} 页</div>
          )}
          <div className="mb-2 text-[11px] text-slate-400">验真 URI: {verifyUri || '-'}</div>
          <div className="mb-2 break-all text-[11px] text-slate-500">模板来源: {templateSourceText}</div>
          <div className="overflow-hidden rounded-lg border border-slate-700 bg-white">
            <div className="grid grid-cols-[1fr_auto] gap-2 border-b border-slate-200 bg-slate-100 px-3 py-2 text-[11px]">
              <div className="flex flex-wrap items-center gap-2">
                <span className="rounded-full border border-slate-300 bg-white px-2 py-0.5 text-slate-700">《3、桥施表》</span>
                <span className="rounded-full border border-slate-300 bg-white px-2 py-0.5 text-slate-600">SMU {activeCode || '-'}</span>
                <span className="rounded-full border border-slate-300 bg-white px-2 py-0.5 text-slate-600">第 {pdfPage} 页</span>
              </div>
              <div className="text-right text-slate-500">{previewIsDraft ? '草稿联编' : '正式预览'}</div>
            </div>
            <div className="grid min-[1180px]:grid-cols-[180px_1fr]">
              <div className="border-r border-slate-200 bg-slate-50 p-3 text-[11px] text-slate-600">
                <div className="text-[10px] uppercase tracking-[0.14em] text-slate-400">签认侧栏</div>
                <div className="mt-2 grid gap-2">
                  <div ref={contractorAnchorRef} className={`rounded-lg border px-2 py-2 ${signFocus === 'contractor' ? 'border-emerald-400 bg-emerald-50 text-emerald-700' : 'border-slate-200 bg-white'}`}>
                    <div className="font-semibold">施工员签认区</div>
                    <div className="mt-1 text-[10px] text-slate-500">点击左侧身份卡可跳转定位</div>
                  </div>
                  <div ref={supervisorAnchorRef} className={`rounded-lg border px-2 py-2 ${signFocus === 'supervisor' ? 'border-emerald-400 bg-emerald-50 text-emerald-700' : 'border-slate-200 bg-white'}`}>
                    <div className="font-semibold">监理签认区</div>
                    <div className="mt-1 text-[10px] text-slate-500">证据回溯与复核签认</div>
                  </div>
                  <div ref={ownerAnchorRef} className={`rounded-lg border px-2 py-2 ${signFocus === 'owner' ? 'border-emerald-400 bg-emerald-50 text-emerald-700' : 'border-slate-200 bg-white'}`}>
                    <div className="font-semibold">业主签认区</div>
                    <div className="mt-1 text-[10px] text-slate-500">最终共识与哈希锁定</div>
                  </div>
                </div>
                <div className="mt-3 rounded-lg border border-slate-200 bg-white px-2 py-2">
                  <div className="text-[10px] uppercase tracking-[0.14em] text-slate-400">验真链路</div>
                  <div className="mt-1 break-all font-mono text-[10px] text-slate-600">{verifyUri || '-'}</div>
                </div>
              </div>
              <div ref={previewScrollRef} className="relative h-[320px] overflow-y-auto bg-white">
                <div className="relative">
                  {previewPdfB64 ? (
                    <div className="relative bg-white">
                      <canvas ref={pdfCanvasRef} className="block h-auto w-full" />
                      {pdfRenderLoading && (
                        <div className="absolute inset-0 grid place-items-center bg-white/70 text-sm text-slate-500">
                          PDF 渲染中...
                        </div>
                      )}
                      {pdfRenderError && (
                        <div className="absolute inset-0 grid place-items-center bg-white/80 text-sm text-rose-500">
                          {pdfRenderError}
                        </div>
                      )}
                    </div>
                  ) : draftReady ? (
                    <div className="grid h-[360px] place-items-center text-sm text-slate-500">草稿版 PDF 实时编译中…</div>
                  ) : (
                    <div className="grid h-[360px] place-items-center text-sm text-slate-400">等待施工员签认后生成草稿预览</div>
                  )}
                  {previewPdfB64 && activeSignMarker && !pdfRenderError && (
                    <div className="pointer-events-none absolute inset-0">
                      <div
                        className="absolute -translate-x-1/2 -translate-y-1/2 rounded-full border border-emerald-500 bg-emerald-400/70 shadow-[0_0_12px_rgba(52,211,153,0.5)]"
                        style={{ left: `${activeSignMarker.x * 100}%`, top: `${activeSignMarker.y * 100}%`, width: 14, height: 14 }}
                      />
                      <div
                        className="absolute -translate-x-1/2 -translate-y-1/2 text-[10px] font-bold text-emerald-700"
                        style={{ left: `${activeSignMarker.x * 100}%`, top: `calc(${activeSignMarker.y * 100}% + 14px)` }}
                      >
                        签认点
                      </div>
                    </div>
                  )}
                  {previewIsDraft && (
                    <div className="pointer-events-none absolute inset-0 flex items-center justify-center text-4xl font-black tracking-[0.25em] text-emerald-600/30">
                      DRAFT
                    </div>
                  )}
                </div>
              </div>
            </div>
          </div>
          <div className="mt-2 grid gap-2 min-[720px]:grid-cols-3">
            <div className="rounded-lg border border-slate-700/80 bg-slate-900/60 px-3 py-2 text-[11px]">
              <div className="text-slate-500">模板</div>
              <div className="mt-1 truncate text-slate-200">{templateDisplay}</div>
            </div>
            <div className="rounded-lg border border-slate-700/80 bg-slate-900/60 px-3 py-2 text-[11px]">
              <div className="text-slate-500">签认页</div>
              <div className="mt-1 text-slate-200">第 {pdfPage} 页</div>
            </div>
            <div className="rounded-lg border border-slate-700/80 bg-slate-900/60 px-3 py-2 text-[11px]">
              <div className="text-slate-500">渲染状态</div>
              <div className={`mt-1 ${pdfRenderError ? 'text-rose-300' : pdfRenderLoading ? 'text-amber-300' : previewPdfB64 ? 'text-emerald-300' : 'text-slate-400'}`}>
                {pdfRenderError ? '渲染异常' : pdfRenderLoading ? '渲染中' : previewPdfB64 ? '就绪' : '待机'}
              </div>
            </div>
          </div>
          <div className="mt-3 grid grid-cols-[140px_1fr] gap-3 rounded-xl border border-slate-700 p-3 max-[600px]:grid-cols-1">
            <div className="grid h-[140px] w-[140px] place-items-center border border-slate-800 bg-white">
              <img src={qrSrc} alt="DocPeg 验真二维码" className="h-[128px] w-[128px]" />
            </div>
            <div className="text-xs leading-5 text-slate-400">
              扫码验真 DocPeg
              <div className="mt-1 break-all text-slate-200">{verifyUri || '暂无 URI'}</div>
              <div className="mt-2 grid gap-2 min-[720px]:grid-cols-2">
                <div className="rounded-lg border border-slate-700/80 bg-slate-900/70 px-3 py-2">
                  <div className="text-[10px] uppercase tracking-[0.14em] text-slate-500">证明ID</div>
                  <div className="mt-1 break-all text-slate-200">{finalProofId || '-'}</div>
                </div>
                <div className="rounded-lg border border-slate-700/80 bg-slate-900/70 px-3 py-2">
                  <div className="text-[10px] uppercase tracking-[0.14em] text-slate-500">总证明哈希</div>
                  <div className="mt-1 break-all text-slate-200">{totalHash || '-'}</div>
                </div>
              </div>
              <div className="mt-2 flex flex-wrap items-center gap-2">
                <button
                  type="button"
                  onClick={() => onCopyText('验真 URI', verifyUri || '')}
                  disabled={!verifyUri}
                  className="rounded border border-slate-700 bg-slate-900 px-2 py-1 text-[11px] text-slate-200 disabled:opacity-50"
                >
                  复制验真 URI
                </button>
                <button
                  type="button"
                  onClick={() => onCopyText('Total Proof Hash', totalHash || '')}
                  disabled={!totalHash}
                  className="rounded border border-slate-700 bg-slate-900 px-2 py-1 text-[11px] text-slate-200 disabled:opacity-50"
                >
                  复制 Hash
                </button>
              </div>
            </div>
          </div>
        </div>
      </div>

      {docModalOpen && pdfB64 && (
        <div className="fixed inset-0 z-[1200] grid place-items-center bg-slate-950/70">
          <div className="w-[640px] max-w-[96vw] rounded-xl border border-slate-700 bg-slate-950 p-4 text-slate-100">
            <div className="mb-2 text-sm font-extrabold">DocPeg 正式报告</div>
            <iframe title="docpeg-modal" src={`data:application/pdf;base64,${pdfB64}`} className="h-[420px] w-full rounded-lg border border-slate-700 bg-white" />
            <div className="mt-2 grid grid-cols-[140px_1fr] gap-2">
              <div className="grid h-[140px] w-[140px] place-items-center border border-slate-800 bg-white">
                <img src={qrSrc} alt="DocPeg 验真二维码" className="h-[128px] w-[128px]" />
              </div>
              <div className="break-all text-[11px] text-slate-400">
                <div>验真 URI: {verifyUri || '-'}</div>
                <div>Total Proof Hash: {totalHash || '-'}</div>
                <div>样品编号: {sampleId || '-'}</div>
                <div>路径: {activeUri || '-'}</div>
              </div>
            </div>
            <div className="mt-3 flex justify-end">
              <button type="button" onClick={onCloseDocModal} className="rounded-lg border border-slate-700 bg-slate-900 px-3 py-2 text-slate-200">
                关闭
              </button>
            </div>
          </div>
        </div>
      )}
    </>
  )
}
