import React, { useEffect, useMemo, useState } from 'react'
import { Button, Card } from '../ui'

interface RwaOmEvolutionPanelProps {
  projectUri: string
  rwaConverting: boolean
  omExporting: boolean
  omEventSubmitting: boolean
  normRunning: boolean
  normResult: any | null
  lastPaymentId?: string
  lastOmRootProofId?: string
  onConvertRwa: (payload: { boqGroupId: string; bankCode: string; runAnchorRounds: number }) => void
  onExportOmBundle: (payload: { omOwnerUri: string; runAnchorRounds: number }) => void
  onRegisterOmEvent: (payload: { omRootProofId: string; title: string; eventType: string }) => void
  onGenerateNormEvolution: (payload: { minSamples: number; nearThresholdRatio: number; anonymize: boolean }) => void
}

export default function RwaOmEvolutionPanel({
  projectUri,
  rwaConverting,
  omExporting,
  omEventSubmitting,
  normRunning,
  normResult,
  lastPaymentId,
  lastOmRootProofId,
  onConvertRwa,
  onExportOmBundle,
  onRegisterOmEvent,
  onGenerateNormEvolution,
}: RwaOmEvolutionPanelProps) {
  const [boqGroupId, setBoqGroupId] = useState('403')
  const [bankCode, setBankCode] = useState('CN-RWA-001')
  const [rwaAnchorRounds, setRwaAnchorRounds] = useState('1')

  const [omOwnerUri, setOmOwnerUri] = useState('v://operator/om/default')
  const [omAnchorRounds, setOmAnchorRounds] = useState('1')
  const [omRootProofId, setOmRootProofId] = useState(lastOmRootProofId || '')
  const [omEventTitle, setOmEventTitle] = useState('桥梁加固巡检')
  const [omEventType, setOmEventType] = useState('maintenance')

  const [minSamples, setMinSamples] = useState('5')
  const [nearThresholdRatio, setNearThresholdRatio] = useState('0.9')
  const [anonymize, setAnonymize] = useState(true)

  useEffect(() => {
    if (!omRootProofId && lastOmRootProofId) {
      setOmRootProofId(lastOmRootProofId)
    }
  }, [lastOmRootProofId, omRootProofId])

  const findings = useMemo(() => {
    const rows = normResult?.report?.findings
    return Array.isArray(rows) ? rows : []
  }, [normResult])

  return (
    <Card title="资产金融化与运维主权" icon="R">
      <div style={{ fontSize: 12, color: '#64748B', marginBottom: 10, wordBreak: 'break-all' }}>
        项目 URI：{projectUri} {lastPaymentId ? `| 最近支付单 ${lastPaymentId}` : ''}
      </div>

      <div style={{ border: '1px solid #E2E8F0', borderRadius: 10, padding: 10, marginBottom: 10 }}>
        <div style={{ fontSize: 12, fontWeight: 700, color: '#0F172A', marginBottom: 8 }}>RWA 转换</div>
        <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr 1fr auto', gap: 8 }}>
          <input
            value={boqGroupId}
            onChange={(e) => setBoqGroupId(e.target.value)}
            placeholder="BOQ 分组（如 403）"
            style={{ padding: 8, border: '1px solid #CBD5E1', borderRadius: 8, fontFamily: 'var(--sans)' }}
          />
          <input
            value={bankCode}
            onChange={(e) => setBankCode(e.target.value)}
            placeholder="银行编码"
            style={{ padding: 8, border: '1px solid #CBD5E1', borderRadius: 8, fontFamily: 'var(--sans)' }}
          />
          <input
            value={rwaAnchorRounds}
            onChange={(e) => setRwaAnchorRounds(e.target.value)}
            placeholder="锚定轮数"
            style={{ padding: 8, border: '1px solid #CBD5E1', borderRadius: 8, fontFamily: 'var(--sans)' }}
          />
          <Button
            size="sm"
            onClick={() => onConvertRwa({ boqGroupId, bankCode, runAnchorRounds: Number(rwaAnchorRounds || 1) })}
            disabled={rwaConverting || !boqGroupId}
          >
            {rwaConverting ? '转换中...' : '转换为 RWA 资产'}
          </Button>
        </div>
      </div>

      <div style={{ border: '1px solid #E2E8F0', borderRadius: 10, padding: 10, marginBottom: 10 }}>
        <div style={{ fontSize: 12, fontWeight: 700, color: '#0F172A', marginBottom: 8 }}>主权运维移交</div>
        <div style={{ display: 'grid', gridTemplateColumns: '2fr 1fr auto', gap: 8, marginBottom: 8 }}>
          <input
            value={omOwnerUri}
            onChange={(e) => setOmOwnerUri(e.target.value)}
            placeholder="运维方 URI"
            style={{ padding: 8, border: '1px solid #CBD5E1', borderRadius: 8, fontFamily: 'var(--sans)' }}
          />
          <input
            value={omAnchorRounds}
            onChange={(e) => setOmAnchorRounds(e.target.value)}
            placeholder="锚定轮数"
            style={{ padding: 8, border: '1px solid #CBD5E1', borderRadius: 8, fontFamily: 'var(--sans)' }}
          />
          <Button
            size="sm"
            onClick={() => onExportOmBundle({ omOwnerUri, runAnchorRounds: Number(omAnchorRounds || 1) })}
            disabled={omExporting}
          >
            {omExporting ? '导出中...' : '导出运维移交包'}
          </Button>
        </div>
        <div style={{ display: 'grid', gridTemplateColumns: '2fr 1fr 1fr auto', gap: 8 }}>
          <input
            value={omRootProofId}
            onChange={(e) => setOmRootProofId(e.target.value)}
            placeholder="运维根证明 ID"
            style={{ padding: 8, border: '1px solid #CBD5E1', borderRadius: 8, fontFamily: 'var(--sans)' }}
          />
          <input
            value={omEventTitle}
            onChange={(e) => setOmEventTitle(e.target.value)}
            placeholder="事件标题"
            style={{ padding: 8, border: '1px solid #CBD5E1', borderRadius: 8, fontFamily: 'var(--sans)' }}
          />
          <input
            value={omEventType}
            onChange={(e) => setOmEventType(e.target.value)}
            placeholder="事件类型"
            style={{ padding: 8, border: '1px solid #CBD5E1', borderRadius: 8, fontFamily: 'var(--sans)' }}
          />
          <Button
            size="sm"
            variant="secondary"
            onClick={() => onRegisterOmEvent({ omRootProofId, title: omEventTitle, eventType: omEventType })}
            disabled={omEventSubmitting || !omRootProofId || !omEventTitle}
          >
            {omEventSubmitting ? '登记中...' : '登记运维事件'}
          </Button>
        </div>
      </div>

      <div style={{ border: '1px solid #E2E8F0', borderRadius: 10, padding: 10 }}>
        <div style={{ fontSize: 12, fontWeight: 700, color: '#0F172A', marginBottom: 8 }}>规范反馈引擎</div>
        <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr auto auto', gap: 8, marginBottom: 8 }}>
          <input
            value={minSamples}
            onChange={(e) => setMinSamples(e.target.value)}
            placeholder="最小样本数"
            style={{ padding: 8, border: '1px solid #CBD5E1', borderRadius: 8, fontFamily: 'var(--sans)' }}
          />
          <input
            value={nearThresholdRatio}
            onChange={(e) => setNearThresholdRatio(e.target.value)}
            placeholder="临界比 near ratio"
            style={{ padding: 8, border: '1px solid #CBD5E1', borderRadius: 8, fontFamily: 'var(--sans)' }}
          />
          <label style={{ display: 'inline-flex', alignItems: 'center', gap: 6, fontSize: 12, color: '#475569' }}>
            <input type="checkbox" checked={anonymize} onChange={(e) => setAnonymize(e.target.checked)} />
            匿名提交
          </label>
          <Button
            size="sm"
            onClick={() => onGenerateNormEvolution({ minSamples: Number(minSamples || 5), nearThresholdRatio: Number(nearThresholdRatio || 0.9), anonymize })}
            disabled={normRunning}
          >
            {normRunning ? '分析中...' : '生成规范演进报告'}
          </Button>
        </div>
        <div style={{ fontSize: 12, color: '#64748B', marginBottom: 6 }}>
          发现数：{Number(normResult?.report?.finding_count || 0)} | 样本总数：{Number(normResult?.report?.total_samples || 0)}
        </div>
        {!!findings.length && (
          <div style={{ maxHeight: 220, overflowY: 'auto', display: 'grid', gap: 6 }}>
            {findings.slice(0, 20).map((item: any, idx: number) => (
              <div key={`${item.norm_uri || 'norm'}-${idx}`} style={{ border: '1px solid #E2E8F0', borderRadius: 8, padding: 8 }}>
                <div style={{ fontSize: 12, fontWeight: 700, color: '#0F172A' }}>
                  {item.norm_uri || '-'} | {item.context_key || '-'}
                </div>
                <div style={{ marginTop: 2, fontSize: 12, color: '#475569' }}>
                  样本 {item.sample_count} | near {item.near_share} | fail {item.fail_share}
                </div>
                <div style={{ marginTop: 2, fontSize: 12, color: '#1A56DB' }}>
                  建议：{item.suggestion}（{item.rationale}）
                </div>
              </div>
            ))}
          </div>
        )}
      </div>
    </Card>
  )
}
