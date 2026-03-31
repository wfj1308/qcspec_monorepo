
import React from 'react'
import { Card } from '../ui'
import SovereignProjectWorkspace from './SovereignProjectWorkspace'

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
  boqRealtime?: {
    summary?: {
      boq_item_count?: number
      design_total?: number
      settled_total?: number
      progress_percent?: number
    }
    items?: Array<{
      boq_item_uri?: string
      item_no?: string
      item_name?: string
      unit?: string
      design_quantity?: number
      settled_quantity?: number
      progress_percent?: number
      latest_settlement_proof_id?: string
    }>
  } | null
  boqRealtimeLoading?: boolean
  boqAudit?: {
    summary?: {
      item_count?: number
      baseline_total?: number
      variation_total?: number
      settled_total?: number
      deviation_total?: number
      illegal_attempt_count?: number
    }
    items?: Array<{
      subitem_code?: string
      boq_item_uri?: string
      item_name?: string
      unit?: string
      baseline_quantity?: number
      variation_quantity?: number
      settled_quantity?: number
      deviation_quantity?: number
      illegal_attempt_count?: number
      status?: string
    }>
    illegal_attempts?: Array<{
      subitem_code?: string
      proof_id?: string
      reason?: string
      action?: string
      created_at?: string
    }>
  } | null
  boqAuditLoading?: boolean
  boqProofPreview?: {
    boq_item_uri?: string
    chain_count?: number
    context?: {
      chain_root_hash?: string
      timeline_rows?: Array<{
        step?: number
        label?: string
        result?: string
        time?: string
        proof_id?: string
      }>
    }
  } | null
  boqProofLoadingUri?: string
  boqSovereignPreview?: {
    subitem_code?: string
    root_utxo_id?: string
    boq_item_uri?: string
    totals?: {
      proof_count?: number
      document_count?: number
      variation_count?: number
      settlement_count?: number
      fail_count?: number
    }
    timeline?: Array<{
      proof_id?: string
      proof_type?: string
      result?: string
      created_at?: string
      trip_action?: string
      depth?: number
    }>
    documents?: Array<{
      proof_id?: string
      file_name?: string
      doc_type?: string
      storage_url?: string
      source_utxo_id?: string
    }>
  } | null
  boqSovereignLoadingCode?: string
  onOpenBoqProofChain?: (boqItemUri: string) => void
  onOpenBoqSovereignHistory?: (subitemCode: string) => void
}

const btn: React.CSSProperties = {
  border: '1px solid #E2E8F0',
  background: '#fff',
  borderRadius: 6,
  padding: '4px 10px',
  cursor: 'pointer',
}

function asArray<T = any>(value: unknown): T[] {
  return Array.isArray(value) ? (value as T[]) : []
}

function statCard(label: string, value: string | number, tone: 'default' | 'ok' | 'warn' = 'default') {
  const fg = tone === 'ok' ? '#047857' : tone === 'warn' ? '#991B1B' : '#0F172A'
  const bg = tone === 'ok' ? '#ECFDF5' : tone === 'warn' ? '#FEF2F2' : '#F8FAFC'
  const bd = tone === 'ok' ? '#86EFAC' : tone === 'warn' ? '#FECACA' : '#E2E8F0'
  return (
    <div style={{ border: `1px solid ${bd}`, background: bg, borderRadius: 8, padding: 8 }}>
      <div style={{ fontSize: 12, color: '#64748B' }}>{label}</div>
      <div style={{ fontSize: 18, fontWeight: 800, color: fg }}>{value}</div>
    </div>
  )
}

function clamp(num: number, min: number, max: number) {
  return Math.max(min, Math.min(max, num))
}

function computeRiskScore(row: { deviation_quantity?: number; illegal_attempt_count?: number }) {
  const deviation = Math.abs(Number(row.deviation_quantity || 0))
  const illegal = Number(row.illegal_attempt_count || 0)
  const score = clamp(Math.round(100 - deviation * 5 - illegal * 12), 0, 100)
  const tone = score >= 80 ? 'ok' : score >= 60 ? 'warn' : 'bad'
  return { score, tone }
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
  boqRealtime,
  boqRealtimeLoading,
  boqAudit,
  boqAuditLoading,
  boqProofPreview,
  boqProofLoadingUri,
  boqSovereignPreview,
  boqSovereignLoadingCode,
  onOpenBoqProofChain,
  onOpenBoqSovereignHistory,
}: ProjectDetailDrawerProps) {
  if (!open || !detailProject) return null

  const draftInspection = asArray<string>(detailDraft?.inspectionTypes)

  return (
    <div style={{ position: 'fixed', inset: 0, background: 'rgba(15,23,42,0.35)', zIndex: 998 }} onClick={onClose}>
      <div
        style={{
          position: 'absolute',
          top: 0,
          right: 0,
          width: 'min(96vw, 1500px)',
          maxWidth: '96vw',
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
            {!detailEdit && <button onClick={onStartEdit} style={{ ...btn, border: '1px solid #BFDBFE', background: '#EFF6FF', color: '#1A56DB' }}>编辑</button>}
            {detailEdit && (
              <>
                <button onClick={onSave} style={{ ...btn, border: '1px solid #86EFAC', background: '#ECFDF5', color: '#059669' }}>保存</button>
                <button onClick={onCancelEdit} style={btn}>取消</button>
              </>
            )}
            <button onClick={onClose} style={btn}>关闭</button>
          </div>
        </div>

        {!detailEdit && (
          <Card title="项目基础" icon="📌" style={{ marginBottom: 10 }}>
            <div style={{ display: 'grid', gridTemplateColumns: '140px 1fr', rowGap: 8, fontSize: 13 }}>
              <span style={{ color: '#64748B' }}>项目名称</span><strong>{detailProject.name}</strong>
              <span style={{ color: '#64748B' }}>项目类型</span><span>{typeLabel[detailProject.type] || detailProject.type}</span>
              <span style={{ color: '#64748B' }}>业主单位</span><span>{detailProject.owner_unit || '-'}</span>
              <span style={{ color: '#64748B' }}>施工单位</span><span>{detailProject.contractor || '-'}</span>
              <span style={{ color: '#64748B' }}>监理单位</span><span>{detailProject.supervisor || '-'}</span>
              <span style={{ color: '#64748B' }}>合同编号</span><span>{detailProject.contract_no || '-'}</span>
              <span style={{ color: '#64748B' }}>工期</span><span>{detailProject.start_date || '-'} ~ {detailProject.end_date || '-'}</span>
              <span style={{ color: '#64748B' }}>v:// URI</span><code style={{ color: '#1A56DB', wordBreak: 'break-all' }}>{detailProject.v_uri}</code>
            </div>
          </Card>
        )}

        {detailEdit && detailProjectDraft && (
          <Card title="编辑项目" icon="🛠" style={{ marginBottom: 10 }}>
            <div style={{ display: 'grid', gridTemplateColumns: '140px 1fr', rowGap: 8, fontSize: 13 }}>
              <span style={{ color: '#64748B' }}>项目名称</span>
              <input value={detailProjectDraft.name || ''} onChange={(e) => onDetailProjectDraftChange({ ...detailProjectDraft, name: e.target.value })} style={{ border: '1px solid #E2E8F0', borderRadius: 6, padding: 8 }} />
              <span style={{ color: '#64748B' }}>项目类型</span>
              <select value={detailProjectDraft.type || ''} onChange={(e) => onDetailProjectDraftChange({ ...detailProjectDraft, type: e.target.value })} style={{ border: '1px solid #E2E8F0', borderRadius: 6, padding: 8 }}>
                {projectTypeOptions.map((opt) => <option key={opt.value} value={opt.value}>{opt.label}</option>)}
              </select>
              <span style={{ color: '#64748B' }}>业主单位</span>
              <input value={detailProjectDraft.owner_unit || ''} onChange={(e) => onDetailProjectDraftChange({ ...detailProjectDraft, owner_unit: e.target.value })} style={{ border: '1px solid #E2E8F0', borderRadius: 6, padding: 8 }} />
              <span style={{ color: '#64748B' }}>施工单位</span>
              <input value={detailProjectDraft.contractor || ''} onChange={(e) => onDetailProjectDraftChange({ ...detailProjectDraft, contractor: e.target.value })} style={{ border: '1px solid #E2E8F0', borderRadius: 6, padding: 8 }} />
            </div>
          </Card>
        )}

        {detailEdit && detailDraft && (
          <Card title="范围参数" icon="🧱" style={{ marginBottom: 10 }}>
            <div style={{ display: 'grid', gridTemplateColumns: '140px 1fr', rowGap: 8, fontSize: 13 }}>
              <span style={{ color: '#64748B' }}>分段方式</span>
              <select value={detailDraft.segType || 'km'} onChange={(e) => onDetailDraftChange({ ...detailDraft, segType: e.target.value })} style={{ border: '1px solid #E2E8F0', borderRadius: 6, padding: 8 }}>
                <option value="km">按里程</option>
                <option value="contract">按合同段</option>
                <option value="structure">按结构物</option>
              </select>
              <span style={{ color: '#64748B' }}>里程间隔</span>
              <input type="number" min={1} value={detailDraft.kmInterval || 1} onChange={(e) => onDetailDraftChange({ ...detailDraft, kmInterval: normalizeKmInterval(e.target.value, detailDraft.kmInterval) })} style={{ border: '1px solid #E2E8F0', borderRadius: 6, padding: 8 }} />
              <span style={{ color: '#64748B' }}>检验类型</span>
              <div style={{ display: 'flex', gap: 6, flexWrap: 'wrap' }}>
                {inspectionTypeOptions.map((opt) => {
                  const checked = draftInspection.includes(opt.key)
                  return (
                    <label key={opt.key} style={{ border: `1px solid ${checked ? '#1A56DB' : '#E2E8F0'}`, borderRadius: 999, padding: '4px 8px', display: 'inline-flex', alignItems: 'center', gap: 6, background: checked ? '#EFF6FF' : '#fff' }}>
                      <input type="checkbox" checked={checked} onChange={() => toggleInspectionType(opt.key, draftInspection, (next) => onDetailDraftChange({ ...detailDraft, inspectionTypes: next }))} />
                      {inspectionTypeLabel[opt.key] || opt.label}
                    </label>
                  )
                })}
              </div>
            </div>
          </Card>
        )}

        {!detailEdit && (
          <Card title="BOQ 实时进度" icon="📊" style={{ marginBottom: 10 }}>
            {boqRealtimeLoading ? (
              <div style={{ fontSize: 12, color: '#64748B' }}>加载 BOQ 实时进度中...</div>
            ) : (
              <>
                <div style={{ display: 'grid', gridTemplateColumns: 'repeat(4,minmax(0,1fr))', gap: 8, marginBottom: 8 }}>
                  {statCard('细目数', Number(boqRealtime?.summary?.boq_item_count || 0))}
                  {statCard('设计总量', Number(boqRealtime?.summary?.design_total || 0).toLocaleString())}
                  {statCard('已结算量', Number(boqRealtime?.summary?.settled_total || 0).toLocaleString())}
                  {statCard('进度', `${Number(boqRealtime?.summary?.progress_percent || 0).toFixed(2)}%`, 'ok')}
                </div>
                <div style={{ display: 'grid', gap: 8, maxHeight: 240, overflowY: 'auto' }}>
                  {(boqRealtime?.items || []).slice(0, 40).map((item, idx) => {
                    const uri = String(item?.boq_item_uri || '')
                    const code = String(item?.item_no || '')
                    const loadingChain = boqProofLoadingUri === uri
                    const loadingSovereign = boqSovereignLoadingCode === code
                    const pct = Math.max(0, Math.min(100, Number(item?.progress_percent || 0)))
                    return (
                      <div key={`${uri || code}-${idx}`} style={{ border: '1px solid #E2E8F0', borderRadius: 8, padding: 8 }}>
                        <div style={{ fontSize: 12, fontWeight: 700 }}>{code} {item?.item_name || ''}</div>
                        <div style={{ fontSize: 12, color: '#64748B', marginTop: 2 }}>设计 {Number(item?.design_quantity || 0).toLocaleString()} / 已结算 {Number(item?.settled_quantity || 0).toLocaleString()} {item?.unit || ''}</div>
                        <div style={{ width: '100%', height: 8, marginTop: 6, borderRadius: 999, overflow: 'hidden', border: '1px solid #DBEAFE', background: '#F8FAFC' }}><div style={{ width: `${pct}%`, height: 8, background: pct >= 100 ? '#16A34A' : '#2563EB' }} /></div>
                        <div style={{ marginTop: 6, display: 'flex', gap: 6 }}>
                          <button type="button" onClick={() => uri && onOpenBoqProofChain?.(uri)} disabled={!uri || loadingChain} style={{ ...btn, border: '1px solid #BFDBFE', background: '#EFF6FF', color: '#1D4ED8' }}>{loadingChain ? '加载链路...' : 'Proof 链'}</button>
                          <button type="button" onClick={() => code && onOpenBoqSovereignHistory?.(code)} disabled={!code || loadingSovereign} style={{ ...btn, border: '1px solid #C7D2FE', background: '#EEF2FF', color: '#3730A3' }}>{loadingSovereign ? '加载穿透...' : '主权穿透'}</button>
                        </div>
                      </div>
                    )
                  })}
                </div>
              </>
            )}
          </Card>
        )}

        {!detailEdit && (
          <Card title="BOQ 主权对账" icon="🧮" style={{ marginBottom: 10 }}>
            {boqAuditLoading ? (
              <div style={{ fontSize: 12, color: '#64748B' }}>计算对账中...</div>
            ) : (
              <>
                <div style={{ display: 'grid', gridTemplateColumns: 'repeat(5,minmax(0,1fr))', gap: 8, marginBottom: 8 }}>
                  {statCard('细目数', Number(boqAudit?.summary?.item_count || 0))}
                  {statCard('批复总量', Number(boqAudit?.summary?.baseline_total || 0).toLocaleString())}
                  {statCard('变更总量', Number(boqAudit?.summary?.variation_total || 0).toLocaleString())}
                  {statCard('已结算', Number(boqAudit?.summary?.settled_total || 0).toLocaleString())}
                  {statCard('非法尝试', Number(boqAudit?.summary?.illegal_attempt_count || 0), 'warn')}
                </div>
                <div style={{ display: 'grid', gap: 6, maxHeight: 200, overflowY: 'auto' }}>
                  {(boqAudit?.items || []).slice(0, 40).map((row, idx) => {
                    const risk = computeRiskScore(row || {})
                    const color = risk.tone === 'ok' ? '#16A34A' : risk.tone === 'warn' ? '#F59E0B' : '#DC2626'
                    const bg = risk.tone === 'ok' ? '#ECFDF3' : risk.tone === 'warn' ? '#FFFBEB' : '#FEF2F2'
                    return (
                      <div key={`${row.subitem_code || 'row'}-${idx}`} style={{ border: '1px solid #E2E8F0', borderRadius: 8, padding: 8 }}>
                        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                          <div style={{ fontSize: 12, fontWeight: 700 }}>{row.subitem_code || '-'} {row.item_name || ''}</div>
                          <div style={{ fontSize: 11, color, background: bg, borderRadius: 999, padding: '2px 8px', border: `1px solid ${color}` }}>风险分值 {risk.score}</div>
                        </div>
                        <div style={{ fontSize: 12, color: '#64748B', marginTop: 2 }}>批复 {Number(row.baseline_quantity || 0).toLocaleString()} + 变更 {Number(row.variation_quantity || 0).toLocaleString()} - 结算 {Number(row.settled_quantity || 0).toLocaleString()} = 偏差 {Number(row.deviation_quantity || 0).toLocaleString()}</div>
                      </div>
                    )
                  })}
                </div>
              </>
            )}
          </Card>
        )}

        {!detailEdit && boqSovereignPreview?.subitem_code && (
          <Card title="细目主权概览" icon="🧬" style={{ marginBottom: 10 }}>
            <div style={{ fontSize: 12, color: '#475569' }}>细目: {boqSovereignPreview.subitem_code} | 根 UTXO: {boqSovereignPreview.root_utxo_id || '-'}</div>
            <div style={{ fontSize: 12, color: '#64748B', marginTop: 4 }}>证明 {Number(boqSovereignPreview?.totals?.proof_count || 0)} | 文档 {Number(boqSovereignPreview?.totals?.document_count || 0)} | 变更 {Number(boqSovereignPreview?.totals?.variation_count || 0)} | 结算 {Number(boqSovereignPreview?.totals?.settlement_count || 0)}</div>
          </Card>
        )}

        {!detailEdit && boqProofPreview?.boq_item_uri && (
          <Card title="Proof 链预览" icon="🧾" style={{ marginBottom: 10 }}>
            <div style={{ fontSize: 12, color: '#475569', wordBreak: 'break-all' }}>URI: {boqProofPreview.boq_item_uri}</div>
            <div style={{ fontSize: 12, color: '#64748B', marginTop: 4 }}>节点数: {Number(boqProofPreview.chain_count || 0)} | 根哈希: {boqProofPreview.context?.chain_root_hash || '-'}</div>
          </Card>
        )}

        {!detailEdit && (
          <SovereignProjectWorkspace project={detailProject} />
        )}
      </div>
    </div>
  )
}
