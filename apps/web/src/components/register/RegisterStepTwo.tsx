import React from 'react'
import type { InspectionTypeKey, SegType } from '../../app/appShellShared'
import type { RegisterFormState } from './types'

interface RegisterStepTwoProps {
  regForm: RegisterFormState
  setRegForm: React.Dispatch<React.SetStateAction<RegisterFormState>>
  segType: SegType
  setSegType: (value: SegType) => void
  regKmInterval: number
  setRegKmInterval: (value: number) => void
  contractSegs: Array<{ name: string; range: string }>
  setContractSegs: React.Dispatch<React.SetStateAction<Array<{ name: string; range: string }>>>
  addContractSeg: () => void
  structures: Array<{ kind: string; name: string; code: string }>
  setStructures: React.Dispatch<React.SetStateAction<Array<{ kind: string; name: string; code: string }>>>
  addStructure: () => void
  inspectionTypeOptions: Array<{ key: InspectionTypeKey; label: string }>
  regInspectionTypes: InspectionTypeKey[]
  setRegInspectionTypes: React.Dispatch<React.SetStateAction<InspectionTypeKey[]>>
  toggleInspectionType: (
    key: InspectionTypeKey,
    current: InspectionTypeKey[],
    setter: React.Dispatch<React.SetStateAction<InspectionTypeKey[]>>
  ) => void
  regUri: string
  vpathStatus: 'checking' | 'available' | 'taken' | string
  regRangeTreeLines: string[]
}

export default function RegisterStepTwo({
  regForm,
  setRegForm,
  segType,
  setSegType,
  regKmInterval,
  setRegKmInterval,
  contractSegs,
  setContractSegs,
  addContractSeg,
  structures,
  setStructures,
  addStructure,
  inspectionTypeOptions,
  regInspectionTypes,
  setRegInspectionTypes,
  toggleInspectionType,
  regUri,
  vpathStatus,
  regRangeTreeLines,
}: RegisterStepTwoProps) {
  return (
    <div className="form-card">
      <div className="form-card-title">🧭 范围模型与节点</div>
      <div className="reg-info-box blue">
        <span className="reg-info-icon">ℹ️</span>
        <div className="reg-info-text">
          检测范围会映射为 v:// 子节点，并与零号台帐、质检台帐共同组成项目主节点结构。
        </div>
      </div>
      <div className="seg-grid">
        {[
          { key: 'km', icon: '🛣️', name: '按桩号', desc: 'K 起止区间自动分段', info: '推荐用于公路项目' },
          { key: 'contract', icon: '📦', name: '按合同段', desc: '按标段配置', info: '多标段项目使用' },
          { key: 'structure', icon: '🏛️', name: '按构造物', desc: '桥梁/隧道/涵洞', info: '构造物专项检测' },
        ].map((seg) => (
          <div key={seg.key} className={`seg-opt ${segType === seg.key ? 'sel' : ''}`} onClick={() => setSegType(seg.key as SegType)}>
            <div className="seg-opt-icon">{seg.icon}</div>
            <div className="seg-opt-name">{seg.name}</div>
            <div className="seg-opt-desc">{seg.desc}</div>
            <div className="seg-opt-info">{seg.info}</div>
          </div>
        ))}
      </div>

      {segType === 'km' && (
        <div style={{ marginBottom: 12 }}>
          <div className="form-group" style={{ marginBottom: 8 }}>
            <label className="form-label">桩号范围</label>
            <div className="range-row">
              <input className="form-input" value={regForm.seg_start} onChange={(e) => setRegForm({ ...regForm, seg_start: e.target.value })} placeholder="K0+000" />
              <span className="range-sep">→</span>
              <input className="form-input" value={regForm.seg_end} onChange={(e) => setRegForm({ ...regForm, seg_end: e.target.value })} placeholder="K100+000" />
            </div>
          </div>
          <div className="form-group">
            <label className="form-label">分段间隔（km）</label>
            <input className="form-input" type="number" min={1} value={regKmInterval} onChange={(e) => setRegKmInterval(Math.max(1, Number(e.target.value) || 1))} />
            <div className="form-hint">建议 10-20km，系统将自动切分子节点。</div>
          </div>
        </div>
      )}

      {segType === 'contract' && (
        <div style={{ marginBottom: 10 }}>
          {contractSegs.map((seg, idx) => (
            <div key={`${seg.name}-${idx}`} className="form-grid" style={{ marginBottom: 8, gridTemplateColumns: '1fr 1fr auto' }}>
              <input className="form-input" value={seg.name} onChange={(e) => setContractSegs((prev) => prev.map((x, i) => (i === idx ? { ...x, name: e.target.value } : x)))} placeholder="标段名称" />
              <input className="form-input" value={seg.range} onChange={(e) => setContractSegs((prev) => prev.map((x, i) => (i === idx ? { ...x, range: e.target.value } : x)))} placeholder="范围（如 K0~K30）" />
              <button className="btn-secondary" onClick={() => setContractSegs((prev) => prev.filter((_, i) => i !== idx))}>删除</button>
            </div>
          ))}
          <button className="btn-secondary" onClick={addContractSeg}>+ 添加合同段</button>
        </div>
      )}

      {segType === 'structure' && (
        <div style={{ marginBottom: 10 }}>
          {structures.map((st, idx) => (
            <div key={`${st.name}-${idx}`} className="form-grid" style={{ marginBottom: 8, gridTemplateColumns: '100px 1fr 1fr auto' }}>
              <select className="form-select" value={st.kind} onChange={(e) => setStructures((prev) => prev.map((x, i) => (i === idx ? { ...x, kind: e.target.value } : x)))}>
                <option>桥梁</option><option>隧道</option><option>涵洞</option>
              </select>
              <input className="form-input" value={st.name} onChange={(e) => setStructures((prev) => prev.map((x, i) => (i === idx ? { ...x, name: e.target.value } : x)))} placeholder="结构物名称" />
              <input className="form-input" value={st.code} onChange={(e) => setStructures((prev) => prev.map((x, i) => (i === idx ? { ...x, code: e.target.value } : x)))} placeholder="编号" />
              <button className="btn-secondary" onClick={() => setStructures((prev) => prev.filter((_, i) => i !== idx))}>删除</button>
            </div>
          ))}
          <button className="btn-secondary" onClick={addStructure}>+ 添加结构物</button>
        </div>
      )}

      <div className="form-group full" style={{ marginBottom: 10 }}>
        <label className="form-label">主要检测类型（可多选）</label>
        <div style={{ display: 'flex', flexWrap: 'wrap', gap: 6 }}>
          {inspectionTypeOptions.map((opt) => {
            const checked = regInspectionTypes.includes(opt.key)
            return (
              <label key={opt.key} className="perm-role-tag" style={{ cursor: 'pointer', background: checked ? '#DBEAFE' : '#EEF2FF', color: checked ? '#1D4ED8' : '#4338CA' }}>
                <input
                  type="checkbox"
                  checked={checked}
                  onChange={() => toggleInspectionType(opt.key, regInspectionTypes, setRegInspectionTypes)}
                  style={{ marginRight: 5 }}
                />
                {opt.label}
              </label>
            )
          })}
        </div>
      </div>

      <div className="vpath-box">
        <span className="vpath-label">v:// URI</span>
        <span className="vpath-uri">{regUri}</span>
        <span className={vpathStatus === 'taken' ? 'vpath-busy' : vpathStatus === 'available' ? 'vpath-ok' : 'vpath-checking'}>
          {vpathStatus === 'taken' ? '已占用' : vpathStatus === 'available' ? '可用' : '检测中'}
        </span>
      </div>
      <div className="node-tree">
        <div>{regUri}</div>
        {regRangeTreeLines.length > 0
          ? regRangeTreeLines.map((line, idx) => (
            <div className="node-tree-sub" key={`${line}-${idx}`}>├─ {line}</div>
          ))
          : <div className="node-tree-sub">├─ 输入范围参数后自动生成子节点</div>}
        <div className="node-tree-sub">├─ 零号台帐/（步骤3填写）</div>
        <div className="node-tree-sub">└─ 质检台帐/（监理秩签后解锁）</div>
      </div>
    </div>
  )
}
