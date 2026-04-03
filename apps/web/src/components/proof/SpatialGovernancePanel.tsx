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
        项目 URI：{projectUri}
      </div>

      <div style={{ border: '1px solid #E2E8F0', borderRadius: 10, padding: 10, marginBottom: 10 }}>
        <div style={{ fontSize: 12, fontWeight: 700, color: '#0F172A', marginBottom: 8 }}>空间绑定（UTXO ↔ BIM）</div>
        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(3,minmax(0,1fr))', gap: 8, marginBottom: 8 }}>
          <input value={utxoId} onChange={(e) => setUtxoId(e.target.value)} placeholder="UTXO / Proof ID" style={{ padding: 8, border: '1px solid #CBD5E1', borderRadius: 8, fontFamily: 'var(--sans)' }} />
          <input value={bimId} onChange={(e) => setBimId(e.target.value)} placeholder="BIM ID（例如 403-pier）" style={{ padding: 8, border: '1px solid #CBD5E1', borderRadius: 8, fontFamily: 'var(--sans)' }} />
          <input value={label} onChange={(e) => setLabel(e.target.value)} placeholder="构件名称" style={{ padding: 8, border: '1px solid #CBD5E1', borderRadius: 8, fontFamily: 'var(--sans)' }} />
          <input value={lat} onChange={(e) => setLat(e.target.value)} placeholder="纬度 lat" style={{ padding: 8, border: '1px solid #CBD5E1', borderRadius: 8, fontFamily: 'var(--sans)' }} />
          <input value={lng} onChange={(e) => setLng(e.target.value)} placeholder="经度 lng" style={{ padding: 8, border: '1px solid #CBD5E1', borderRadius: 8, fontFamily: 'var(--sans)' }} />
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
              {spatialLoading ? '刷新中...' : '刷新看板'}
            </Button>
          </div>
        </div>

        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(4,minmax(0,1fr))', gap: 8, marginBottom: 8 }}>
          <div style={{ border: '1px solid #E2E8F0', borderRadius: 8, padding: 8 }}>
            <div style={{ fontSize: 11, color: '#64748B' }}>构件总数</div>
            <div style={{ fontSize: 18, fontWeight: 800, color: '#0F172A' }}>{Number(summary.asset_count || 0)}</div>
          </div>
          <div style={{ border: '1px solid #DCFCE7', borderRadius: 8, padding: 8, background: '#F0FDF4' }}>
            <div style={{ fontSize: 11, color: '#166534' }}>已结算（绿）</div>
            <div style={{ fontSize: 18, fontWeight: 800, color: '#166534' }}>{Number(summary.green_count || 0)}</div>
          </div>
          <div style={{ border: '1px solid #FEF9C3', borderRadius: 8, padding: 8, background: '#FEFCE8' }}>
            <div style={{ fontSize: 11, color: '#854D0E' }}>质检中（黄）</div>
            <div style={{ fontSize: 18, fontWeight: 800, color: '#854D0E' }}>{Number(summary.yellow_count || 0)}</div>
          </div>
          <div style={{ border: '1px solid #FECACA', borderRadius: 8, padding: 8, background: '#FEF2F2' }}>
            <div style={{ fontSize: 11, color: '#991B1B' }}>失败（红）</div>
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
                <span style={{ display: 'inline-flex', alignItems: 'center', gap: 4, fontSize: 11, color: '#334155' }}>
                  <span style={{ width: 8, height: 8, borderRadius: 999, background: asset.color || '#CBD5E1', display: 'inline-block' }} />
                  {asset.status || '-'}
                </span>
              </div>
              <div style={{ marginTop: 2, fontSize: 12, color: '#64748B' }}>
                BIM：{asset.bim_id || '-'} | 坐标：{asset.coordinate?.lat ?? '-'}, {asset.coordinate?.lng ?? '-'} | 支付：{asset.payment_status || '-'}
              </div>
              <div style={{ marginTop: 2, fontSize: 12, color: '#475569' }}>
                规范：{asset.norm_snapshot?.spec_uri || '-'} | 偏差：{asset.norm_snapshot?.deviation_percent ?? '-'}
              </div>
              {!!asset.proof_id && onOpenVerifyNode && (
                <button
                  type="button"
                  onClick={() => onOpenVerifyNode(String(asset.proof_id))}
                  style={{ marginTop: 4, border: 'none', background: 'transparent', padding: 0, color: '#1A56DB', fontSize: 12, cursor: 'pointer', fontFamily: 'var(--sans)' }}
                >
                  打开 NormPeg 判定报告
                </button>
              )}
            </div>
          ))}
        </div>
      </div>

      <div style={{ border: '1px solid #E2E8F0', borderRadius: 10, padding: 10, marginBottom: 10 }}>
        <div style={{ fontSize: 12, fontWeight: 700, color: '#0F172A', marginBottom: 8 }}>主动预警规则</div>
        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(4,minmax(0,1fr))', gap: 8, marginBottom: 8 }}>
          <input value={nearRatio} onChange={(e) => setNearRatio(e.target.value)} placeholder="临界比（near ratio）" style={{ padding: 8, border: '1px solid #CBD5E1', borderRadius: 8, fontFamily: 'var(--sans)' }} />
          <input value={minSamples} onChange={(e) => setMinSamples(e.target.value)} placeholder="最小样本数" style={{ padding: 8, border: '1px solid #CBD5E1', borderRadius: 8, fontFamily: 'var(--sans)' }} />
          <input value={criticalThreshold} onChange={(e) => setCriticalThreshold(e.target.value)} placeholder="临界阈值" style={{ padding: 8, border: '1px solid #CBD5E1', borderRadius: 8, fontFamily: 'var(--sans)' }} />
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
          预警数：{Number(aiResult?.warning_count || 0)} | 自动门控更新：{Array.isArray(aiResult?.gate_updates) ? aiResult.gate_updates.length : 0}
        </div>
        {!!warnings.length && (
          <div style={{ maxHeight: 180, overflowY: 'auto', display: 'grid', gap: 6 }}>
            {warnings.slice(0, 30).map((w: any, idx: number) => (
              <div key={`${w.group_key || 'warn'}-${idx}`} style={{ border: '1px solid #FEF3C7', background: '#FFFBEB', borderRadius: 8, padding: 8 }}>
                <div style={{ fontSize: 12, color: '#92400E', fontWeight: 700 }}>
                  {w.boq_item_uri || '-'} | {w.team_uri || '-'} | {w.risk_level || '-'}
                </div>
                <div style={{ marginTop: 2, fontSize: 12, color: '#B45309' }}>
                  均值偏差 {w.mean_abs_deviation} / 临界 {w.critical_threshold} | near ratio {w.near_ratio}
                </div>
              </div>
            ))}
          </div>
        )}
      </div>

      <div style={{ border: '1px solid #E2E8F0', borderRadius: 10, padding: 10 }}>
        <div style={{ fontSize: 12, fontWeight: 700, color: '#0F172A', marginBottom: 8 }}>金融网关凭证</div>
        <div style={{ display: 'grid', gridTemplateColumns: '2fr 1fr 1fr auto', gap: 8 }}>
          <input value={paymentId} onChange={(e) => setPaymentId(e.target.value)} placeholder="支付凭证 ID" style={{ padding: 8, border: '1px solid #CBD5E1', borderRadius: 8, fontFamily: 'var(--sans)' }} />
          <input value={bankCode} onChange={(e) => setBankCode(e.target.value)} placeholder="银行编码" style={{ padding: 8, border: '1px solid #CBD5E1', borderRadius: 8, fontFamily: 'var(--sans)' }} />
          <input value={runAnchorRounds} onChange={(e) => setRunAnchorRounds(e.target.value)} placeholder="锚定轮数" style={{ padding: 8, border: '1px solid #CBD5E1', borderRadius: 8, fontFamily: 'var(--sans)' }} />
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
