import React, { useEffect, useMemo, useState } from 'react'
import { Button, Card } from '../ui'

interface SpatialGovernancePanelProps {
  projectUri: string
  spatialLoading: boolean
  spatialDashboard: any | null
  aiRunning: boolean
  aiResult: any | null
  financeExporting: boolean
  defaultPaymentId?: string
  onRefreshSpatial: () => void
  onBindSpatial: (payload: {
    utxo_id: string
    project_uri: string
    bim_id?: string
    label?: string
    coordinate?: Record<string, unknown>
  }) => void
  onRunPredictive: (payload: {
    nearThresholdRatio: number
    minSamples: number
    applyDynamicGate: boolean
    defaultCriticalThreshold: number
  }) => void
  onExportFinanceProof: (payload: {
    paymentId: string
    bankCode: string
    runAnchorRounds: number
  }) => void
  onOpenVerifyNode?: (proofId: string) => void
}

export default function SpatialGovernancePanel({
  projectUri,
  spatialLoading,
  spatialDashboard,
  aiRunning,
  aiResult,
  financeExporting,
  defaultPaymentId,
  onRefreshSpatial,
  onBindSpatial,
  onRunPredictive,
  onExportFinanceProof,
  onOpenVerifyNode,
}: SpatialGovernancePanelProps) {
  const [utxoId, setUtxoId] = useState('')
  const [bimId, setBimId] = useState('')
  const [label, setLabel] = useState('')
  const [lat, setLat] = useState('')
  const [lng, setLng] = useState('')
  const [nearRatio, setNearRatio] = useState('0.9')
  const [minSamples, setMinSamples] = useState('3')
  const [criticalThreshold, setCriticalThreshold] = useState('2.0')
  const [paymentId, setPaymentId] = useState(defaultPaymentId || '')
  const [bankCode, setBankCode] = useState('CN-FACTORING-001')
  const [runAnchorRounds, setRunAnchorRounds] = useState('1')

  const summary = spatialDashboard?.summary || {}
  const assets = useMemo(() => {
    const rows = spatialDashboard?.assets
    return Array.isArray(rows) ? rows : []
  }, [spatialDashboard])

  const warnings = useMemo(() => {
    const rows = aiResult?.warnings
    return Array.isArray(rows) ? rows : []
  }, [aiResult])

  useEffect(() => {
    if (!paymentId && defaultPaymentId) {
      setPaymentId(defaultPaymentId)
    }
  }, [defaultPaymentId, paymentId])

  return (
    <Card title="空间孪生与智能治理" icon="🛰️">
      <div style={{ fontSize: 12, color: '#64748B', marginBottom: 8, wordBreak: 'break-all' }}>
        空间位置 = 资产地址 · 项目 URI: {projectUri}
      </div>

      <div style={{ border: '1px solid #E2E8F0', borderRadius: 10, padding: 10, marginBottom: 10 }}>
        <div style={{ fontSize: 12, fontWeight: 700, color: '#0F172A', marginBottom: 8 }}>Spatial-Ledger Alignment</div>
        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(3,minmax(0,1fr))', gap: 8, marginBottom: 8 }}>
          <input value={utxoId} onChange={(e) => setUtxoId(e.target.value)} placeholder="UTXO / Proof ID" style={{ padding: 8, border: '1px solid #CBD5E1', borderRadius: 8 }} />
          <input value={bimId} onChange={(e) => setBimId(e.target.value)} placeholder="BIM ID (e.g. 403-pier)" style={{ padding: 8, border: '1px solid #CBD5E1', borderRadius: 8 }} />
          <input value={label} onChange={(e) => setLabel(e.target.value)} placeholder="构件名称" style={{ padding: 8, border: '1px solid #CBD5E1', borderRadius: 8 }} />
          <input value={lat} onChange={(e) => setLat(e.target.value)} placeholder="lat" style={{ padding: 8, border: '1px solid #CBD5E1', borderRadius: 8 }} />
          <input value={lng} onChange={(e) => setLng(e.target.value)} placeholder="lng" style={{ padding: 8, border: '1px solid #CBD5E1', borderRadius: 8 }} />
          <div style={{ display: 'flex', gap: 8 }}>
            <Button
              size="sm"
              onClick={() => onBindSpatial({
                utxo_id: utxoId,
                project_uri: projectUri,
                bim_id: bimId,
                label,
                coordinate: { lat, lng },
              })}
              disabled={!utxoId}
            >
              绑定空间指纹
            </Button>
            <Button size="sm" variant="secondary" onClick={onRefreshSpatial} disabled={spatialLoading}>
              {spatialLoading ? '刷新中...' : '刷新孪生看板'}
            </Button>
          </div>
        </div>

        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(4,minmax(0,1fr))', gap: 8, marginBottom: 8 }}>
          <div style={{ border: '1px solid #E2E8F0', borderRadius: 8, padding: 8 }}>
            <div style={{ fontSize: 11, color: '#64748B' }}>构件总数</div>
            <div style={{ fontSize: 18, fontWeight: 800, color: '#0F172A' }}>{Number(summary.asset_count || 0)}</div>
          </div>
          <div style={{ border: '1px solid #DCFCE7', borderRadius: 8, padding: 8, background: '#F0FDF4' }}>
            <div style={{ fontSize: 11, color: '#166534' }}>已结算(绿)</div>
            <div style={{ fontSize: 18, fontWeight: 800, color: '#166534' }}>{Number(summary.green_count || 0)}</div>
          </div>
          <div style={{ border: '1px solid #FEF9C3', borderRadius: 8, padding: 8, background: '#FEFCE8' }}>
            <div style={{ fontSize: 11, color: '#854D0E' }}>质检中(黄)</div>
            <div style={{ fontSize: 18, fontWeight: 800, color: '#854D0E' }}>{Number(summary.yellow_count || 0)}</div>
          </div>
          <div style={{ border: '1px solid #FECACA', borderRadius: 8, padding: 8, background: '#FEF2F2' }}>
            <div style={{ fontSize: 11, color: '#991B1B' }}>失败(红)</div>
            <div style={{ fontSize: 18, fontWeight: 800, color: '#991B1B' }}>{Number(summary.red_count || 0)}</div>
          </div>
        </div>

        <div style={{ maxHeight: 240, overflowY: 'auto', display: 'grid', gap: 6 }}>
          {assets.slice(0, 80).map((asset: any) => (
            <div key={String(asset.asset_key || asset.proof_id)} style={{ border: '1px solid #E2E8F0', borderRadius: 8, padding: 8 }}>
              <div style={{ display: 'flex', justifyContent: 'space-between', gap: 8, alignItems: 'center' }}>
                <div style={{ fontSize: 12, fontWeight: 700, color: '#0F172A' }}>
                  {asset.item_no || '-'} {asset.item_name || ''}
                </div>
                <span style={{
                  display: 'inline-flex',
                  alignItems: 'center',
                  gap: 4,
                  fontSize: 11,
                  color: '#334155',
                }}>
                  <span style={{ width: 8, height: 8, borderRadius: 999, background: asset.color || '#CBD5E1', display: 'inline-block' }} />
                  {asset.status || '-'}
                </span>
              </div>
              <div style={{ marginTop: 2, fontSize: 12, color: '#64748B' }}>
                BIM: {asset.bim_id || '-'} · 坐标: {asset.coordinate?.lat ?? '-'}, {asset.coordinate?.lng ?? '-'} · 支付: {asset.payment_status || '-'}
              </div>
              <div style={{ marginTop: 2, fontSize: 12, color: '#475569' }}>
                Norm: {asset.norm_snapshot?.spec_uri || '-'} · 偏差: {asset.norm_snapshot?.deviation_percent ?? '-'}
              </div>
              {!!asset.proof_id && onOpenVerifyNode && (
                <button
                  type="button"
                  onClick={() => onOpenVerifyNode(String(asset.proof_id))}
                  style={{ marginTop: 4, border: 'none', background: 'transparent', padding: 0, color: '#1A56DB', fontSize: 12, cursor: 'pointer' }}
                >
                  打开 NormPeg 判定报告
                </button>
              )}
            </div>
          ))}
        </div>
      </div>

      <div style={{ border: '1px solid #E2E8F0', borderRadius: 10, padding: 10, marginBottom: 10 }}>
        <div style={{ fontSize: 12, fontWeight: 700, color: '#0F172A', marginBottom: 8 }}>Proactive AI Rules</div>
        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(4,minmax(0,1fr))', gap: 8, marginBottom: 8 }}>
          <input value={nearRatio} onChange={(e) => setNearRatio(e.target.value)} placeholder="near ratio" style={{ padding: 8, border: '1px solid #CBD5E1', borderRadius: 8 }} />
          <input value={minSamples} onChange={(e) => setMinSamples(e.target.value)} placeholder="min samples" style={{ padding: 8, border: '1px solid #CBD5E1', borderRadius: 8 }} />
          <input value={criticalThreshold} onChange={(e) => setCriticalThreshold(e.target.value)} placeholder="critical threshold" style={{ padding: 8, border: '1px solid #CBD5E1', borderRadius: 8 }} />
          <Button
            size="sm"
            onClick={() => onRunPredictive({
              nearThresholdRatio: Number(nearRatio || 0.9),
              minSamples: Number(minSamples || 3),
              applyDynamicGate: true,
              defaultCriticalThreshold: Number(criticalThreshold || 2.0),
            })}
            disabled={aiRunning}
          >
            {aiRunning ? '分析中...' : '运行预测治理'}
          </Button>
        </div>
        <div style={{ fontSize: 12, color: '#64748B', marginBottom: 6 }}>
          预警数: {Number(aiResult?.warning_count || 0)} · 自动门控更新: {Array.isArray(aiResult?.gate_updates) ? aiResult.gate_updates.length : 0}
        </div>
        {!!warnings.length && (
          <div style={{ maxHeight: 180, overflowY: 'auto', display: 'grid', gap: 6 }}>
            {warnings.slice(0, 30).map((w: any, idx: number) => (
              <div key={`${w.group_key || 'warn'}-${idx}`} style={{ border: '1px solid #FEF3C7', background: '#FFFBEB', borderRadius: 8, padding: 8 }}>
                <div style={{ fontSize: 12, color: '#92400E', fontWeight: 700 }}>
                  {w.boq_item_uri || '-'} · {w.team_uri || '-'} · {w.risk_level || '-'}
                </div>
                <div style={{ marginTop: 2, fontSize: 12, color: '#B45309' }}>
                  偏差均值 {w.mean_abs_deviation} / 临界 {w.critical_threshold} · near ratio {w.near_ratio}
                </div>
              </div>
            ))}
          </div>
        )}
      </div>

      <div style={{ border: '1px solid #E2E8F0', borderRadius: 10, padding: 10 }}>
        <div style={{ fontSize: 12, fontWeight: 700, color: '#0F172A', marginBottom: 8 }}>Finance Gateway Proof</div>
        <div style={{ display: 'grid', gridTemplateColumns: '2fr 1fr 1fr auto', gap: 8 }}>
          <input value={paymentId} onChange={(e) => setPaymentId(e.target.value)} placeholder="Payment Proof ID" style={{ padding: 8, border: '1px solid #CBD5E1', borderRadius: 8 }} />
          <input value={bankCode} onChange={(e) => setBankCode(e.target.value)} placeholder="Bank Code" style={{ padding: 8, border: '1px solid #CBD5E1', borderRadius: 8 }} />
          <input value={runAnchorRounds} onChange={(e) => setRunAnchorRounds(e.target.value)} placeholder="anchor rounds" style={{ padding: 8, border: '1px solid #CBD5E1', borderRadius: 8 }} />
          <Button
            size="sm"
            onClick={() => onExportFinanceProof({
              paymentId,
              bankCode,
              runAnchorRounds: Number(runAnchorRounds || 1),
            })}
            disabled={financeExporting || !paymentId}
          >
            {financeExporting ? '导出中...' : '导出金融凭证'}
          </Button>
        </div>
      </div>
    </Card>
  )
}
