type Props = {
  meshpegCloudName: string
  meshpegBimName: string
  meshpegRunning: boolean
  meshpegRes: Record<string, unknown> | null
  formulaExpr: string
  formulaRunning: boolean
  formulaRes: Record<string, unknown> | null
  gatewayRes: Record<string, unknown> | null
  inputBaseCls: string
  btnBlueCls: string
  btnGreenCls: string
  btnAmberCls: string
  formatNumber: (value: unknown) => string
  onMeshpegCloudNameChange: (value: string) => void
  onMeshpegBimNameChange: (value: string) => void
  onRunMeshpeg: () => void
  onFormulaExprChange: (value: string) => void
  onRunFormulaPeg: () => void
  onRunGatewaySync: () => void
  onCopyGatewayJson: () => void
  onDownloadGatewayJson: () => void
}

export default function ExecutionPegPanels({
  meshpegCloudName,
  meshpegBimName,
  meshpegRunning,
  meshpegRes,
  formulaExpr,
  formulaRunning,
  formulaRes,
  gatewayRes,
  inputBaseCls,
  btnBlueCls,
  btnGreenCls,
  btnAmberCls,
  formatNumber,
  onMeshpegCloudNameChange,
  onMeshpegBimNameChange,
  onRunMeshpeg,
  onFormulaExprChange,
  onRunFormulaPeg,
  onRunGatewaySync,
  onCopyGatewayJson,
  onDownloadGatewayJson,
}: Props) {
  return (
    <>
      <div className="mt-3 rounded-xl border border-dashed border-slate-700 p-3">
        <div className="mb-1 text-xs font-extrabold">MeshPeg 数字孪生核算</div>
        <div className="mb-2 text-[11px] text-slate-400">LiDAR 点云与 BIM 模型自动比对，输出几何校核证明。</div>
        <div className="grid gap-2">
          <div className="grid grid-cols-2 gap-2">
            <input
              value={meshpegCloudName}
              onChange={(event) => onMeshpegCloudNameChange(event.target.value)}
              placeholder="点云源，例如 LiDAR-Drone-01"
              className={inputBaseCls}
            />
            <input
              value={meshpegBimName}
              onChange={(event) => onMeshpegBimNameChange(event.target.value)}
              placeholder="BIM 模型，例如 BIM-v3.2"
              className={inputBaseCls}
            />
          </div>
          <button type="button" onClick={onRunMeshpeg} disabled={meshpegRunning} className={`px-3 py-2 text-sm font-bold ${btnBlueCls}`}>
            {meshpegRunning ? '核算中...' : '运行 MeshPeg 核算'}
          </button>
          {meshpegRes && (
            <div className="grid gap-1 text-[11px] text-slate-300">
              <div>设计量: {formatNumber(meshpegRes.design_quantity)} | 实测体积: {formatNumber(meshpegRes.mesh_volume)}</div>
              <div>偏差: {String(meshpegRes.deviation_percent || 0)}% | 状态: {String(meshpegRes.status || '-')}</div>
              <div>Mesh Proof: {String(meshpegRes.proof_id || '-')}</div>
            </div>
          )}
        </div>
      </div>

      <div className="mt-3 rounded-xl border border-dashed border-slate-700 p-3">
        <div className="mb-1 text-xs font-extrabold">FormulaPeg 动态计价合约</div>
        <div className="mb-2 text-[11px] text-slate-400">质量和几何条件通过后，自动生成计价结果与 RailPact。</div>
        <div className="grid gap-2">
          <input
            value={formulaExpr}
            onChange={(event) => onFormulaExprChange(event.target.value)}
            placeholder="公式示例：qty * unit_price"
            className={inputBaseCls}
          />
          <button type="button" onClick={onRunFormulaPeg} disabled={formulaRunning} className={`px-3 py-2 text-sm font-bold ${btnGreenCls}`}>
            {formulaRunning ? '计价中...' : '生成 RailPact'}
          </button>
          {formulaRes && (
            <div className="grid gap-1 text-[11px] text-slate-300">
              <div>数量: {String(formulaRes.qty || '-')} | 单价: {String(formulaRes.unit_price || '-')}</div>
              <div>金额: {String(formulaRes.amount || '-')} | RailPact: {String(formulaRes.railpact_id || '-')}</div>
              <div>状态: {String(formulaRes.status || '-')}</div>
            </div>
          )}
        </div>
      </div>

      <div className="mt-3 rounded-xl border border-dashed border-slate-700 p-3">
        <div className="mb-1 text-xs font-extrabold">Sovereign Gateway 跨链治理</div>
        <div className="mb-2 text-[11px] text-slate-400">同步监管侧摘要，实时对齐 total proof hash。</div>
        <div className="grid gap-2">
          <button type="button" onClick={onRunGatewaySync} className={`px-3 py-2 text-sm font-bold ${btnAmberCls}`}>生成监管同步摘要</button>
          {gatewayRes && (
            <div className="grid gap-1 text-[11px] text-slate-300">
              <div>Project: {String(gatewayRes.project_uri || '-')}</div>
              <div>Total Proof Hash: {String(gatewayRes.total_proof_hash || '-')}</div>
              <div>Proof ID: {String(gatewayRes.proof_id || '-')}</div>
              <div>Scan Entry: {String(gatewayRes.scan_entry_proof || '-')}</div>
              <div>更新时间: {String(gatewayRes.updated_at || '-')}</div>
              <div className="flex items-center gap-2">
                <button type="button" onClick={onCopyGatewayJson} className="rounded border border-slate-700 bg-slate-900 px-2 py-1 text-[11px] text-slate-200">复制 JSON</button>
                <button type="button" onClick={onDownloadGatewayJson} className="rounded border border-slate-700 bg-slate-900 px-2 py-1 text-[11px] text-slate-200">导出 JSON</button>
              </div>
            </div>
          )}
        </div>
      </div>
    </>
  )
}
