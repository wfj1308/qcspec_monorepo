type Props = {
  assetAppraising: boolean
  assetAppraisal: Record<string, unknown> | null
  btnGreenCls: string
  onBuildAssetAppraisal: () => void
  onCopyAssetAppraisalJson: () => void
  onDownloadAssetAppraisalJson: () => void
}

export default function AssetAppraisalPanel({
  assetAppraising,
  assetAppraisal,
  btnGreenCls,
  onBuildAssetAppraisal,
  onCopyAssetAppraisalJson,
  onDownloadAssetAppraisalJson,
}: Props) {
  return (
    <div className="mt-3 rounded-xl border border-dashed border-slate-700 p-3">
      <div className="mb-1 text-xs font-extrabold">主权资产评估接口</div>
      <div className="mb-2 text-[11px] text-slate-400">面向金融机构输出证明强度评分，结果可直接用于授信参考。</div>
      <div className="grid gap-2">
        <button type="button" onClick={onBuildAssetAppraisal} disabled={assetAppraising} className={`px-3 py-2 text-sm font-bold ${btnGreenCls}`}>
          {assetAppraising ? '评估中...' : '生成资产评估'}
        </button>
        {assetAppraisal && (
          <div className="grid gap-1 text-[11px] text-slate-300">
            <div>评分: {String(assetAppraisal.score || '-')} | 等级: {String(assetAppraisal.grade || '-')}</div>
            <div>Proof: {String(assetAppraisal.proof_id || '-')}</div>
            <div>哈希: {String(assetAppraisal.total_proof_hash || '-')}</div>
            <div>风险: dispute={String(assetAppraisal.dispute_open)} | consensus={String(assetAppraisal.consensus_conflict)} | risk_score={String(assetAppraisal.risk_score || 0)}</div>
            <div>证据 {String(assetAppraisal.evidence_count || 0)} | 文档 {String(assetAppraisal.document_count || 0)}</div>
            <div className="flex items-center gap-2">
              <button type="button" onClick={onCopyAssetAppraisalJson} className="rounded border border-slate-700 bg-slate-900 px-2 py-1 text-[11px] text-slate-200">复制 JSON</button>
              <button type="button" onClick={onDownloadAssetAppraisalJson} className="rounded border border-slate-700 bg-slate-900 px-2 py-1 text-[11px] text-slate-200">导出 JSON</button>
            </div>
          </div>
        )}
      </div>
    </div>
  )
}

