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
  onMeshpegCloudNameChange: (value: string) => void
  onMeshpegBimNameChange: (value: string) => void
  onRunMeshpeg: () => void
  onFormulaExprChange: (value: string) => void
  onRunFormulaPeg: () => void
  onRunGatewaySync: () => void
  onCopyGatewayJson: () => void
  onExportGatewayJson: () => void
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
  onMeshpegCloudNameChange,
  onMeshpegBimNameChange,
  onRunMeshpeg,
  onFormulaExprChange,
  onRunFormulaPeg,
  onRunGatewaySync,
  onCopyGatewayJson,
  onExportGatewayJson,
}: Props) {
  return (
    <>
      <div className="border border-dashed border-slate-700 rounded-xl p-3 mt-3">
        <div className="text-xs font-extrabold mb-1">MeshPeg 数字孪生核算</div>
        <div className="text-[11px] text-slate-400 mb-2">LiDAR 点云 vs BIM 模型自动比对，生成几何 Proof。</div>
        <div className="grid gap-2">
          <div className="grid grid-cols-2 gap-2">
            <input
              value={meshpegCloudName}
              onChange={(event) => onMeshpegCloudNameChange(event.target.value)}
              placeholder="点云源（如 LiDAR-Drone-01）"
              className={inputBaseCls}
            />
            <input
              value={meshpegBimName}
              onChange={(event) => onMeshpegBimNameChange(event.target.value)}
              placeholder="BIM 模型（如 BIM-v3.2）"
              className={inputBaseCls}
            />
          </div>
          <button type="button" onClick={onRunMeshpeg} disabled={meshpegRunning} className={`px-3 py-2 text-sm font-bold ${btnBlueCls}`}>
            {meshpegRunning ? '核算中...' : '运行 MeshPeg 核算'}
          </button>
          {meshpegRes && (
            <div className="text-[11px] text-slate-300 grid gap-1">
              <div>设计量: {String(meshpegRes.design_quantity || '-')} · 实测体积: {String(meshpegRes.mesh_volume || '-')}</div>
              <div>偏差: {String(meshpegRes.deviation_percent || 0)}% · 状态 {String(meshpegRes.status || '-')}</div>
              <div>Mesh Proof: {String(meshpegRes.proof_id || '-')}</div>
            </div>
          )}
        </div>
      </div>
      <div className="border border-dashed border-slate-700 rounded-xl p-3 mt-3">
        <div className="text-xs font-extrabold mb-1">FormulaPeg 动态计价合约</div>
        <div className="text-[11px] text-slate-400 mb-2">质量合格 + 几何合格后自动计价生成 RailPact。</div>
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
            <div className="text-[11px] text-slate-300 grid gap-1">
              <div>数量: {String(formulaRes.qty || '-')} · 单价: {String(formulaRes.unit_price || '-')}</div>
              <div>金额: {String(formulaRes.amount || '-')} · RailPact: {String(formulaRes.railpact_id || '-')}</div>
              <div>状态: {String(formulaRes.status || '-')}</div>
            </div>
          )}
        </div>
      </div>
      <div className="border border-dashed border-slate-700 rounded-xl p-3 mt-3">
        <div className="text-xs font-extrabold mb-1">Sovereign Gateway 跨链治理</div>
        <div className="text-[11px] text-slate-400 mb-2">同步监管侧节点，实时对齐 total_proof_hash。</div>
        <div className="grid gap-2">
          <button type="button" onClick={onRunGatewaySync} className={`px-3 py-2 text-sm font-bold ${btnAmberCls}`}>生成监管同步摘要</button>
          {gatewayRes && (
            <div className="text-[11px] text-slate-300 grid gap-1">
              <div>Project: {String(gatewayRes.project_uri || '-')}</div>
              <div>Total Proof Hash: {String(gatewayRes.total_proof_hash || '-')}</div>
              <div>Proof ID: {String(gatewayRes.proof_id || '-')}</div>
              <div>Scan Entry: {String(gatewayRes.scan_entry_proof || '-')}</div>
              <div>更新时间: {String(gatewayRes.updated_at || '-')}</div>
              <div className="flex items-center gap-2">
                <button type="button" onClick={onCopyGatewayJson} className="px-2 py-1 text-[11px] border border-slate-700 rounded bg-slate-900 text-slate-200">复制 JSON</button>
                <button type="button" onClick={onExportGatewayJson} className="px-2 py-1 text-[11px] border border-slate-700 rounded bg-slate-900 text-slate-200">导出 JSON</button>
              </div>
            </div>
          )}
        </div>
      </div>
    </>
  )
}
