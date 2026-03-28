import React from 'react'
import type {
  TeamRole,
  ZeroEquipmentRow,
  ZeroLedgerTab,
  ZeroMaterialRow,
  ZeroPersonnelRow,
  ZeroSubcontractRow,
} from '../../app/appShellShared'

interface ZeroLedgerTreeRow {
  text: string
  color?: string
}

interface EquipmentValidity {
  label: string
  color: string
  bg: string
}

interface RegisterStepThreeProps {
  zeroLedgerTab: ZeroLedgerTab
  setZeroLedgerTab: (tab: ZeroLedgerTab) => void
  zeroPersonnel: ZeroPersonnelRow[]
  setZeroPersonnel: React.Dispatch<React.SetStateAction<ZeroPersonnelRow[]>>
  zeroEquipment: ZeroEquipmentRow[]
  setZeroEquipment: React.Dispatch<React.SetStateAction<ZeroEquipmentRow[]>>
  zeroSubcontracts: ZeroSubcontractRow[]
  setZeroSubcontracts: React.Dispatch<React.SetStateAction<ZeroSubcontractRow[]>>
  zeroMaterials: ZeroMaterialRow[]
  setZeroMaterials: React.Dispatch<React.SetStateAction<ZeroMaterialRow[]>>
  makeRowId: (prefix: string) => string
  buildExecutorUri: (name: string) => string
  buildToolUri: (name: string, modelNo: string) => string
  buildSubcontractUri: (unitName: string) => string
  getEquipmentValidity: (validUntil: string) => EquipmentValidity
  regUri: string
  zeroLedgerTreeRows: ZeroLedgerTreeRow[]
}

export default function RegisterStepThree({
  zeroLedgerTab,
  setZeroLedgerTab,
  zeroPersonnel,
  setZeroPersonnel,
  zeroEquipment,
  setZeroEquipment,
  zeroSubcontracts,
  setZeroSubcontracts,
  zeroMaterials,
  setZeroMaterials,
  makeRowId,
  buildExecutorUri,
  buildToolUri,
  buildSubcontractUri,
  getEquipmentValidity,
  regUri,
  zeroLedgerTreeRows,
}: RegisterStepThreeProps) {
  return (
    <div className="form-card">
      <div className="form-card-title">📋 零号台帐</div>
      <div className="reg-info-box green">
        <span className="reg-info-icon">ℹ️</span>
        <div className="reg-info-text">开工前建立零号台帐，监理秩签审批通过后质检台帐解锁。</div>
      </div>
      <div style={{ display: 'flex', gap: 8, flexWrap: 'wrap', marginBottom: 12 }}>
        {[
          { key: 'personnel', label: '👤 施工人员' },
          { key: 'equipment', label: '🔧 检测仪器' },
          { key: 'subcontract', label: '🏢 分包单位' },
          { key: 'materials', label: '📦 原材料' },
        ].map((tab) => (
          <button
            key={tab.key}
            className="btn-secondary"
            style={{
              padding: '8px 14px',
              borderColor: zeroLedgerTab === tab.key ? '#1D4ED8' : '#CBD5E1',
              color: zeroLedgerTab === tab.key ? '#1D4ED8' : '#475569',
              background: zeroLedgerTab === tab.key ? '#EFF6FF' : '#fff',
            }}
            onClick={() => setZeroLedgerTab(tab.key as ZeroLedgerTab)}
          >
            {tab.label}
          </button>
        ))}
      </div>

      {zeroLedgerTab === 'personnel' && (
        <div style={{ marginBottom: 14 }}>
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 8 }}>
            <div style={{ fontSize: 12, color: '#64748B' }}>姓名 · 职务 · DTORole · 资质证书 · executor 节点地址实时生成</div>
            <button
              className="btn-secondary"
              onClick={() => setZeroPersonnel((prev) => [...prev, {
                id: makeRowId('zp'),
                name: '',
                title: '质检员',
                dtoRole: 'AI',
                certificate: '',
              }])}
            >
              + 添加人员
            </button>
          </div>
          <div style={{ overflowX: 'auto' }}>
            <table className="perm-table" style={{ minWidth: 900 }}>
              <thead>
                <tr>
                  <th>姓名</th><th>职务</th><th>DTORole</th><th>资质证书</th><th>executor 节点</th><th style={{ width: 68 }}>操作</th>
                </tr>
              </thead>
              <tbody>
                {zeroPersonnel.map((row) => (
                  <tr key={row.id}>
                    <td><input className="form-input" value={row.name} onChange={(e) => setZeroPersonnel((prev) => prev.map((x) => x.id === row.id ? { ...x, name: e.target.value } : x))} placeholder="姓名" /></td>
                    <td><input className="form-input" value={row.title} onChange={(e) => setZeroPersonnel((prev) => prev.map((x) => x.id === row.id ? { ...x, title: e.target.value } : x))} placeholder="职务/职称" /></td>
                    <td>
                      <select className="form-select" value={row.dtoRole} onChange={(e) => setZeroPersonnel((prev) => prev.map((x) => x.id === row.id ? { ...x, dtoRole: e.target.value as TeamRole } : x))}>
                        <option value="OWNER">OWNER</option>
                        <option value="SUPERVISOR">SUPERVISOR</option>
                        <option value="AI">AI</option>
                        <option value="PUBLIC">PUBLIC</option>
                      </select>
                    </td>
                    <td><input className="form-input" value={row.certificate} onChange={(e) => setZeroPersonnel((prev) => prev.map((x) => x.id === row.id ? { ...x, certificate: e.target.value } : x))} placeholder="资质证书" /></td>
                    <td><code style={{ color: '#1D4ED8', fontSize: 12 }}>{buildExecutorUri(row.name)}</code></td>
                    <td><button className="act-btn act-del" onClick={() => setZeroPersonnel((prev) => prev.filter((x) => x.id !== row.id))}>删除</button></td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      )}

      {zeroLedgerTab === 'equipment' && (
        <div style={{ marginBottom: 14 }}>
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 8 }}>
            <div style={{ fontSize: 12, color: '#64748B' }}>检定有效期自动计算剩余天数：&gt;90天有效，&lt;90天预警，已过期标红</div>
            <button
              className="btn-secondary"
              onClick={() => setZeroEquipment((prev) => [...prev, {
                id: makeRowId('ze'),
                name: '',
                modelNo: '',
                inspectionItem: '压实度',
                validUntil: '',
              }])}
            >
              + 添加仪器
            </button>
          </div>
          <div style={{ overflowX: 'auto' }}>
            <table className="perm-table" style={{ minWidth: 980 }}>
              <thead>
                <tr>
                  <th>仪器名称</th><th>型号编号</th><th>检测项目</th><th>检定有效期</th><th>ToolPeg 节点</th><th>状态</th><th style={{ width: 68 }}>操作</th>
                </tr>
              </thead>
              <tbody>
                {zeroEquipment.map((row) => {
                  const validity = getEquipmentValidity(row.validUntil)
                  return (
                    <tr key={row.id}>
                      <td><input className="form-input" value={row.name} onChange={(e) => setZeroEquipment((prev) => prev.map((x) => x.id === row.id ? { ...x, name: e.target.value } : x))} placeholder="仪器名称" /></td>
                      <td><input className="form-input" value={row.modelNo} onChange={(e) => setZeroEquipment((prev) => prev.map((x) => x.id === row.id ? { ...x, modelNo: e.target.value } : x))} placeholder="型号/编号" /></td>
                      <td><input className="form-input" value={row.inspectionItem} onChange={(e) => setZeroEquipment((prev) => prev.map((x) => x.id === row.id ? { ...x, inspectionItem: e.target.value } : x))} placeholder="检测项目" /></td>
                      <td><input className="form-input" type="date" value={row.validUntil} onChange={(e) => setZeroEquipment((prev) => prev.map((x) => x.id === row.id ? { ...x, validUntil: e.target.value } : x))} /></td>
                      <td><code style={{ color: '#1D4ED8', fontSize: 12 }}>{buildToolUri(row.name, row.modelNo)}</code></td>
                      <td><span style={{ fontSize: 12, fontWeight: 700, color: validity.color, background: validity.bg, borderRadius: 999, padding: '3px 10px' }}>{validity.label}</span></td>
                      <td><button className="act-btn act-del" onClick={() => setZeroEquipment((prev) => prev.filter((x) => x.id !== row.id))}>删除</button></td>
                    </tr>
                  )
                })}
              </tbody>
            </table>
          </div>
        </div>
      )}

      {zeroLedgerTab === 'subcontract' && (
        <div style={{ marginBottom: 14 }}>
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 8 }}>
            <div style={{ fontSize: 12, color: '#64748B' }}>单位名称 · 分包内容 · 桩号范围 · 自动生成子节点</div>
            <button
              className="btn-secondary"
              onClick={() => setZeroSubcontracts((prev) => [...prev, {
                id: makeRowId('zs'),
                unitName: '',
                content: '路面施工',
                range: '',
              }])}
            >
              + 添加分包
            </button>
          </div>
          <div style={{ overflowX: 'auto' }}>
            <table className="perm-table" style={{ minWidth: 860 }}>
              <thead>
                <tr>
                  <th>单位名称</th><th>分包内容</th><th>桩号范围</th><th>自动生成子节点</th><th style={{ width: 68 }}>操作</th>
                </tr>
              </thead>
              <tbody>
                {zeroSubcontracts.map((row) => (
                  <tr key={row.id}>
                    <td><input className="form-input" value={row.unitName} onChange={(e) => setZeroSubcontracts((prev) => prev.map((x) => x.id === row.id ? { ...x, unitName: e.target.value } : x))} placeholder="分包单位全称" /></td>
                    <td><input className="form-input" value={row.content} onChange={(e) => setZeroSubcontracts((prev) => prev.map((x) => x.id === row.id ? { ...x, content: e.target.value } : x))} placeholder="分包内容" /></td>
                    <td><input className="form-input" value={row.range} onChange={(e) => setZeroSubcontracts((prev) => prev.map((x) => x.id === row.id ? { ...x, range: e.target.value } : x))} placeholder="K0~K20" /></td>
                    <td><code style={{ color: '#1D4ED8', fontSize: 12 }}>{buildSubcontractUri(row.unitName)}</code></td>
                    <td><button className="act-btn act-del" onClick={() => setZeroSubcontracts((prev) => prev.filter((x) => x.id !== row.id))}>删除</button></td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      )}

      {zeroLedgerTab === 'materials' && (
        <div style={{ marginBottom: 14 }}>
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 8 }}>
            <div style={{ fontSize: 12, color: '#64748B' }}>材料名称 · 规格 · 供应商 · 检测频率要求</div>
            <button
              className="btn-secondary"
              onClick={() => setZeroMaterials((prev) => [...prev, {
                id: makeRowId('zm'),
                name: '',
                spec: '',
                supplier: '',
                freq: '每批次检测',
              }])}
            >
              + 添加材料
            </button>
          </div>
          <div style={{ overflowX: 'auto' }}>
            <table className="perm-table" style={{ minWidth: 860 }}>
              <thead>
                <tr>
                  <th>材料名称</th><th>规格</th><th>供应商</th><th>检测频率要求</th><th style={{ width: 68 }}>操作</th>
                </tr>
              </thead>
              <tbody>
                {zeroMaterials.map((row) => (
                  <tr key={row.id}>
                    <td><input className="form-input" value={row.name} onChange={(e) => setZeroMaterials((prev) => prev.map((x) => x.id === row.id ? { ...x, name: e.target.value } : x))} placeholder="材料名称" /></td>
                    <td><input className="form-input" value={row.spec} onChange={(e) => setZeroMaterials((prev) => prev.map((x) => x.id === row.id ? { ...x, spec: e.target.value } : x))} placeholder="规格型号" /></td>
                    <td><input className="form-input" value={row.supplier} onChange={(e) => setZeroMaterials((prev) => prev.map((x) => x.id === row.id ? { ...x, supplier: e.target.value } : x))} placeholder="供应商" /></td>
                    <td><input className="form-input" value={row.freq} onChange={(e) => setZeroMaterials((prev) => prev.map((x) => x.id === row.id ? { ...x, freq: e.target.value } : x))} placeholder="每批次检测" /></td>
                    <td><button className="act-btn act-del" onClick={() => setZeroMaterials((prev) => prev.filter((x) => x.id !== row.id))}>删除</button></td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      )}

      <div style={{ fontSize: 12, color: '#475569', fontWeight: 700, marginBottom: 6 }}>节点树实时预览</div>
      <div className="node-tree" style={{ marginBottom: 12 }}>
        <div>{regUri}</div>
        <div className="node-tree-sub" style={{ color: '#F59E0B' }}>├─ 零号台帐/</div>
        {zeroLedgerTreeRows.length > 0 ? zeroLedgerTreeRows.map((row, idx) => (
          <div key={`${row.text}-${idx}`} className="node-tree-sub" style={{ color: row.color || '#34D399' }}>
            {idx === zeroLedgerTreeRows.length - 1 ? '└─' : '├─'} {row.text}
          </div>
        )) : (
          <div className="node-tree-sub">└─ （等待填写零号台帐）</div>
        )}
        <div className="node-tree-sub" style={{ color: '#94A3B8' }}>└─ 质检台帐/（等待监理秩签后解锁）</div>
      </div>

      <div className="reg-info-box green" style={{ marginBottom: 0, alignItems: 'center', justifyContent: 'space-between', flexWrap: 'wrap' }}>
        <div>
          <div style={{ fontSize: 13, fontWeight: 700, color: '#047857', marginBottom: 4 }}>🔏 秩签（Ordosign）审批</div>
          <div style={{ fontSize: 12, color: '#334155' }}>项目负责人秩签 → 监理工程师秩签 → 质检台帐解锁</div>
        </div>
        <div style={{ display: 'flex', alignItems: 'center', gap: 10 }}>
          <div style={{ textAlign: 'center' }}>
            <div style={{ width: 42, height: 42, borderRadius: '50%', border: '2px dashed #6EE7B7', display: 'flex', alignItems: 'center', justifyContent: 'center', background: '#fff' }}>项</div>
            <div style={{ fontSize: 10, color: '#64748B' }}>待签</div>
          </div>
          <span style={{ color: '#10B981' }}>→</span>
          <div style={{ textAlign: 'center' }}>
            <div style={{ width: 42, height: 42, borderRadius: '50%', border: '2px dashed #6EE7B7', display: 'flex', alignItems: 'center', justifyContent: 'center', background: '#fff' }}>监</div>
            <div style={{ fontSize: 10, color: '#64748B' }}>待签</div>
          </div>
          <span style={{ color: '#10B981' }}>→</span>
          <div style={{ textAlign: 'center' }}>
            <div style={{ width: 42, height: 42, borderRadius: '50%', border: '2px dashed #6EE7B7', display: 'flex', alignItems: 'center', justifyContent: 'center', background: '#fff' }}>🔓</div>
            <div style={{ fontSize: 10, color: '#64748B' }}>质检台帐</div>
          </div>
        </div>
      </div>
    </div>
  )
}
