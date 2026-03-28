import React from 'react'
import { Card } from '../ui'

interface ProjectDetailDrawerProps {
  open: boolean
  detailProject: any | null
  detailEdit: boolean
  detailProjectDraft: any | null
  detailMeta: any | null
  detailDraft: any | null
  projectTypeOptions: Array<{ value: string; label: string }>
  inspectionTypeOptions: Array<{ key: string; label: string }>
  inspectionTypeLabel: Record<string, string>
  typeLabel: Record<string, string>
  onClose: () => void
  onStartEdit: () => void
  onSave: () => void
  onCancelEdit: () => void
  onDetailProjectDraftChange: (next: any) => void
  onDetailDraftChange: (next: any) => void
  normalizeKmInterval: (value: unknown, fallback?: number) => number
  toggleInspectionType: (key: any, current: any[], setter: (next: any[]) => void) => void
}

export default function ProjectDetailDrawer({
  open,
  detailProject,
  detailEdit,
  detailProjectDraft,
  detailMeta,
  detailDraft,
  projectTypeOptions,
  inspectionTypeOptions,
  inspectionTypeLabel,
  typeLabel,
  onClose,
  onStartEdit,
  onSave,
  onCancelEdit,
  onDetailProjectDraftChange,
  onDetailDraftChange,
  normalizeKmInterval,
  toggleInspectionType,
}: ProjectDetailDrawerProps) {
  if (!open || !detailProject) return null

  return (
    <div
      style={{ position: 'fixed', inset: 0, background: 'rgba(15,23,42,0.35)', zIndex: 998 }}
      onClick={onClose}
    >
      <div
        style={{
          position: 'absolute',
          top: 0,
          right: 0,
          width: 480,
          maxWidth: '92vw',
          height: '100%',
          background: '#fff',
          borderLeft: '1px solid #E2E8F0',
          padding: 16,
          overflowY: 'auto',
        }}
        onClick={(e) => e.stopPropagation()}
      >
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 12 }}>
          <div style={{ fontSize: 16, fontWeight: 800, color: '#0F172A' }}>项目详情</div>
          <div style={{ display: 'flex', gap: 8 }}>
            {!detailEdit && (
              <button
                onClick={onStartEdit}
                style={{
                  border: '1px solid #BFDBFE',
                  background: '#EFF6FF',
                  borderRadius: 6,
                  padding: '4px 10px',
                  cursor: 'pointer',
                  color: '#1A56DB',
                }}
              >
                编辑
              </button>
            )}
            {detailEdit && (
              <>
                <button
                  onClick={onSave}
                  style={{
                    border: '1px solid #86EFAC',
                    background: '#ECFDF5',
                    borderRadius: 6,
                    padding: '4px 10px',
                    cursor: 'pointer',
                    color: '#059669',
                  }}
                >
                  保存
                </button>
                <button
                  onClick={onCancelEdit}
                  style={{
                    border: '1px solid #E2E8F0',
                    background: '#fff',
                    borderRadius: 6,
                    padding: '4px 10px',
                    cursor: 'pointer',
                  }}
                >
                  取消
                </button>
              </>
            )}
            <button
              onClick={onClose}
              style={{
                border: '1px solid #E2E8F0',
                background: '#fff',
                borderRadius: 6,
                padding: '4px 10px',
                cursor: 'pointer',
              }}
            >
              关闭
            </button>
          </div>
        </div>

        {!detailEdit && (
          <div style={{ display: 'grid', gridTemplateColumns: '110px 1fr', rowGap: 8, fontSize: 13, marginBottom: 14 }}>
            <span style={{ color: '#64748B' }}>项目名称</span><strong>{detailProject.name}</strong>
            <span style={{ color: '#64748B' }}>项目类型</span><span>{typeLabel[detailProject.type] || detailProject.type}</span>
            <span style={{ color: '#64748B' }}>业主单位</span><span>{detailProject.owner_unit}</span>
            <span style={{ color: '#64748B' }}>施工单位</span><span>{detailProject.contractor || '-'}</span>
            <span style={{ color: '#64748B' }}>监理单位</span><span>{detailProject.supervisor || '-'}</span>
            <span style={{ color: '#64748B' }}>合同编号</span><span>{detailProject.contract_no || '-'}</span>
            <span style={{ color: '#64748B' }}>ERP 项目编码</span><span>{detailProject.erp_project_code || '-'}</span>
            <span style={{ color: '#64748B' }}>ERP 项目名称</span><span>{detailProject.erp_project_name || '-'}</span>
            <span style={{ color: '#64748B' }}>工期</span><span>{detailProject.start_date || '-'} ~ {detailProject.end_date || '-'}</span>
            <span style={{ color: '#64748B' }}>v:// URI</span><code style={{ color: '#1A56DB', wordBreak: 'break-all' }}>{detailProject.v_uri}</code>
            <span style={{ color: '#64748B' }}>零号台帐</span>
            <span>
              {`${(Array.isArray(detailProject.zero_personnel) ? detailProject.zero_personnel.filter((row: any) => String(row?.name || '').trim()).length : 0)}名人员 · ${(Array.isArray(detailProject.zero_equipment) ? detailProject.zero_equipment.filter((row: any) => String(row?.name || '').trim()).length : 0)}台仪器 · 等待秩签审批`}
            </span>
            <span style={{ color: '#64748B' }}>秩签状态</span>
            <span>{detailProject.zero_sign_status || 'pending'}</span>
            <span style={{ color: '#64748B' }}>质检台帐</span>
            <span>{detailProject.qc_ledger_unlocked ? '已解锁' : '待解锁（监理秩签后）'}</span>
          </div>
        )}

        {detailEdit && detailProjectDraft && (
          <div style={{ display: 'grid', gridTemplateColumns: '110px 1fr', rowGap: 8, fontSize: 13, marginBottom: 14 }}>
            <span style={{ color: '#64748B' }}>项目名称</span>
            <input value={detailProjectDraft.name} onChange={(e) => onDetailProjectDraftChange({ ...detailProjectDraft, name: e.target.value })} style={{ padding: 8, border: '1px solid #E2E8F0', borderRadius: 6 }} />
            <span style={{ color: '#64748B' }}>项目类型</span>
            <select value={detailProjectDraft.type} onChange={(e) => onDetailProjectDraftChange({ ...detailProjectDraft, type: e.target.value })} style={{ padding: 8, border: '1px solid #E2E8F0', borderRadius: 6 }}>
              {projectTypeOptions.map((opt) => (
                <option key={`detail-${opt.value}`} value={opt.value}>{opt.label}</option>
              ))}
            </select>
            <span style={{ color: '#64748B' }}>业主单位</span>
            <input value={detailProjectDraft.owner_unit} onChange={(e) => onDetailProjectDraftChange({ ...detailProjectDraft, owner_unit: e.target.value })} style={{ padding: 8, border: '1px solid #E2E8F0', borderRadius: 6 }} />
            <span style={{ color: '#64748B' }}>施工单位</span>
            <input value={detailProjectDraft.contractor} onChange={(e) => onDetailProjectDraftChange({ ...detailProjectDraft, contractor: e.target.value })} style={{ padding: 8, border: '1px solid #E2E8F0', borderRadius: 6 }} />
            <span style={{ color: '#64748B' }}>监理单位</span>
            <input value={detailProjectDraft.supervisor} onChange={(e) => onDetailProjectDraftChange({ ...detailProjectDraft, supervisor: e.target.value })} style={{ padding: 8, border: '1px solid #E2E8F0', borderRadius: 6 }} />
            <span style={{ color: '#64748B' }}>合同编号</span>
            <input value={detailProjectDraft.contract_no} onChange={(e) => onDetailProjectDraftChange({ ...detailProjectDraft, contract_no: e.target.value })} style={{ padding: 8, border: '1px solid #E2E8F0', borderRadius: 6 }} />
            <span style={{ color: '#64748B' }}>开工日期</span>
            <input type="date" value={detailProjectDraft.start_date} onChange={(e) => onDetailProjectDraftChange({ ...detailProjectDraft, start_date: e.target.value })} style={{ padding: 8, border: '1px solid #E2E8F0', borderRadius: 6 }} />
            <span style={{ color: '#64748B' }}>完工日期</span>
            <input type="date" value={detailProjectDraft.end_date} onChange={(e) => onDetailProjectDraftChange({ ...detailProjectDraft, end_date: e.target.value })} style={{ padding: 8, border: '1px solid #E2E8F0', borderRadius: 6 }} />
            <span style={{ color: '#64748B' }}>v:// URI</span><code style={{ color: '#1A56DB', wordBreak: 'break-all' }}>{detailProject.v_uri}</code>
          </div>
        )}

        <Card title="范围模型" icon="🧭" style={{ marginBottom: 10 }}>
          {!detailMeta && <div style={{ color: '#94A3B8', fontSize: 12 }}>该项目暂无扩展注册信息（老数据）。</div>}
          {detailMeta && !detailEdit && (
            <div style={{ display: 'grid', gridTemplateColumns: '120px 1fr', rowGap: 8, fontSize: 13 }}>
              <span style={{ color: '#64748B' }}>分段方式</span><span>{detailMeta.segType}</span>
              <span style={{ color: '#64748B' }}>桩号范围</span><span>{detailMeta.segStart || '-'} ~ {detailMeta.segEnd || '-'}</span>
              <span style={{ color: '#64748B' }}>分段间隔</span><span>{detailMeta.kmInterval} km</span>
              <span style={{ color: '#64748B' }}>主要检测类型</span>
              <span>
                {(detailMeta.inspectionTypes || []).length
                  ? (detailMeta.inspectionTypes || []).map((key: string) => inspectionTypeLabel[key] || key).join(' / ')
                  : '-'}
              </span>
              <span style={{ color: '#64748B' }}>权限模板</span><span>{detailMeta.permTemplate}</span>
              <span style={{ color: '#64748B' }}>初始成员</span><span>{detailMeta.memberCount} 人</span>
            </div>
          )}
          {detailEdit && detailDraft && (
            <div style={{ display: 'grid', gridTemplateColumns: '120px 1fr', rowGap: 8, fontSize: 13 }}>
              <span style={{ color: '#64748B' }}>分段方式</span>
              <select value={detailDraft.segType} onChange={(e) => onDetailDraftChange({ ...detailDraft, segType: e.target.value })} style={{ padding: 8, border: '1px solid #E2E8F0', borderRadius: 6 }}>
                <option value="km">km</option><option value="contract">contract</option><option value="structure">structure</option>
              </select>
              <span style={{ color: '#64748B' }}>桩号起点</span>
              <input value={detailDraft.segStart} onChange={(e) => onDetailDraftChange({ ...detailDraft, segStart: e.target.value })} style={{ padding: 8, border: '1px solid #E2E8F0', borderRadius: 6 }} />
              <span style={{ color: '#64748B' }}>桩号终点</span>
              <input value={detailDraft.segEnd} onChange={(e) => onDetailDraftChange({ ...detailDraft, segEnd: e.target.value })} style={{ padding: 8, border: '1px solid #E2E8F0', borderRadius: 6 }} />
              <span style={{ color: '#64748B' }}>分段间隔(km)</span>
              <input
                type="number"
                min={1}
                value={detailDraft.kmInterval}
                onChange={(e) => onDetailDraftChange({ ...detailDraft, kmInterval: normalizeKmInterval(e.target.value, detailDraft.kmInterval) })}
                style={{ padding: 8, border: '1px solid #E2E8F0', borderRadius: 6 }}
              />
              <span style={{ color: '#64748B' }}>主要检测类型</span>
              <div style={{ display: 'flex', gap: 6, flexWrap: 'wrap' }}>
                {inspectionTypeOptions.map((opt) => {
                  const checked = detailDraft.inspectionTypes.includes(opt.key)
                  return (
                    <label
                      key={`detail-${opt.key}`}
                      style={{
                        display: 'inline-flex',
                        alignItems: 'center',
                        gap: 5,
                        padding: '4px 8px',
                        border: `1px solid ${checked ? '#1A56DB' : '#E2E8F0'}`,
                        borderRadius: 999,
                        background: checked ? '#EFF6FF' : '#fff',
                        color: checked ? '#1A56DB' : '#475569',
                        fontSize: 12,
                        cursor: 'pointer',
                        userSelect: 'none',
                      }}
                    >
                      <input
                        type="checkbox"
                        checked={checked}
                        onChange={() => toggleInspectionType(opt.key, detailDraft.inspectionTypes, (next) => onDetailDraftChange({ ...detailDraft, inspectionTypes: next }))}
                      />
                      {opt.label}
                    </label>
                  )
                })}
              </div>
              <span style={{ color: '#64748B' }}>权限模板</span>
              <select value={detailDraft.permTemplate} onChange={(e) => onDetailDraftChange({ ...detailDraft, permTemplate: e.target.value })} style={{ padding: 8, border: '1px solid #E2E8F0', borderRadius: 6 }}>
                <option value="standard">standard</option><option value="strict">strict</option><option value="open">open</option><option value="custom">custom</option>
              </select>
            </div>
          )}
        </Card>

        {detailMeta && !detailEdit && detailMeta.contractSegs.length > 0 && (
          <Card title="合同段明细" icon="📦" style={{ marginBottom: 10 }}>
            {detailMeta.contractSegs.map((seg: any, idx: number) => (
              <div key={`${seg.name}-${idx}`} style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 8, padding: '8px 0', borderBottom: '1px solid #F1F5F9', fontSize: 13 }}>
                <strong>{seg.name || `合同段 ${idx + 1}`}</strong>
                <span style={{ color: '#475569' }}>{seg.range || '-'}</span>
              </div>
            ))}
          </Card>
        )}
        {detailEdit && detailDraft && (
          <Card title="合同段明细" icon="📦" style={{ marginBottom: 10 }}>
            {detailDraft.contractSegs.map((seg: any, idx: number) => (
              <div key={`${seg.name}-${idx}`} style={{ display: 'grid', gridTemplateColumns: '1fr 1fr auto', gap: 8, padding: '8px 0', borderBottom: '1px solid #F1F5F9', fontSize: 13 }}>
                <input value={seg.name} onChange={(e) => onDetailDraftChange({ ...detailDraft, contractSegs: detailDraft.contractSegs.map((x: any, i: number) => i === idx ? { ...x, name: e.target.value } : x) })} style={{ padding: 8, border: '1px solid #E2E8F0', borderRadius: 6 }} />
                <input value={seg.range} onChange={(e) => onDetailDraftChange({ ...detailDraft, contractSegs: detailDraft.contractSegs.map((x: any, i: number) => i === idx ? { ...x, range: e.target.value } : x) })} style={{ padding: 8, border: '1px solid #E2E8F0', borderRadius: 6 }} />
                <button onClick={() => onDetailDraftChange({ ...detailDraft, contractSegs: detailDraft.contractSegs.filter((_: any, i: number) => i !== idx) })} style={{ padding: '4px 8px', border: '1px solid #FECACA', borderRadius: 6, background: '#FEF2F2', color: '#DC2626', cursor: 'pointer' }}>删</button>
              </div>
            ))}
            <button onClick={() => onDetailDraftChange({ ...detailDraft, contractSegs: [...detailDraft.contractSegs, { name: '', range: '' }] })} style={{ marginTop: 8, padding: '6px 10px', border: '1px solid #E2E8F0', borderRadius: 6, background: '#fff', cursor: 'pointer' }}>+ 添加合同段</button>
          </Card>
        )}

        {detailMeta && !detailEdit && detailMeta.structures.length > 0 && (
          <Card title="结构物明细" icon="🏛️" style={{ marginBottom: 10 }}>
            {detailMeta.structures.map((st: any, idx: number) => (
              <div key={`${st.name}-${idx}`} style={{ display: 'grid', gridTemplateColumns: '90px 1fr 100px', gap: 8, padding: '8px 0', borderBottom: '1px solid #F1F5F9', fontSize: 13 }}>
                <span style={{ color: '#1A56DB', fontWeight: 700 }}>{st.kind || '-'}</span>
                <strong>{st.name || `结构物 ${idx + 1}`}</strong>
                <span style={{ color: '#64748B' }}>{st.code || '-'}</span>
              </div>
            ))}
          </Card>
        )}
        {detailEdit && detailDraft && (
          <Card title="结构物明细" icon="🏛️" style={{ marginBottom: 10 }}>
            {detailDraft.structures.map((st: any, idx: number) => (
              <div key={`${st.name}-${idx}`} style={{ display: 'grid', gridTemplateColumns: '90px 1fr 100px auto', gap: 8, padding: '8px 0', borderBottom: '1px solid #F1F5F9', fontSize: 13 }}>
                <select value={st.kind} onChange={(e) => onDetailDraftChange({ ...detailDraft, structures: detailDraft.structures.map((x: any, i: number) => i === idx ? { ...x, kind: e.target.value } : x) })} style={{ padding: 8, border: '1px solid #E2E8F0', borderRadius: 6 }}>
                  <option>桥梁</option><option>隧道</option><option>涵洞</option>
                </select>
                <input value={st.name} onChange={(e) => onDetailDraftChange({ ...detailDraft, structures: detailDraft.structures.map((x: any, i: number) => i === idx ? { ...x, name: e.target.value } : x) })} style={{ padding: 8, border: '1px solid #E2E8F0', borderRadius: 6 }} />
                <input value={st.code} onChange={(e) => onDetailDraftChange({ ...detailDraft, structures: detailDraft.structures.map((x: any, i: number) => i === idx ? { ...x, code: e.target.value } : x) })} style={{ padding: 8, border: '1px solid #E2E8F0', borderRadius: 6 }} />
                <button onClick={() => onDetailDraftChange({ ...detailDraft, structures: detailDraft.structures.filter((_: any, i: number) => i !== idx) })} style={{ padding: '4px 8px', border: '1px solid #FECACA', borderRadius: 6, background: '#FEF2F2', color: '#DC2626', cursor: 'pointer' }}>删</button>
              </div>
            ))}
            <button onClick={() => onDetailDraftChange({ ...detailDraft, structures: [...detailDraft.structures, { kind: '桥梁', name: '', code: '' }] })} style={{ marginTop: 8, padding: '6px 10px', border: '1px solid #E2E8F0', borderRadius: 6, background: '#fff', cursor: 'pointer' }}>+ 添加结构物</button>
          </Card>
        )}
      </div>
    </div>
  )
}
