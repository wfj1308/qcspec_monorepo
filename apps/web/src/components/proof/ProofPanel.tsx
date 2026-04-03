import React, { useMemo, useState } from 'react'
import { Button, Card, VPathDisplay } from '../ui'

interface ProofRow {
  proof_id: string
  summary?: string
  object_type?: string
  action?: string
  created_at?: string
}

interface ProofStats {
  total: number
  by_type: Record<string, number>
  by_action: Record<string, number>
}

interface ProofNodeRow {
  uri?: string
  node_type?: string
  status?: string
}

interface ProofPanelProps {
  projectUri: string
  proofStats: ProofStats
  proofNodeRows: ProofNodeRow[]
  proofLoading: boolean
  proofRows: ProofRow[]
  proofVerifying: string | null
  onVerifyProof: (proofId: string) => void
  onGoInspection?: () => void
  onGoReports?: () => void
}

export default function ProofPanel({
  projectUri,
  proofStats,
  proofNodeRows,
  proofLoading,
  proofRows,
  proofVerifying,
  onVerifyProof,
  onGoInspection,
  onGoReports,
}: ProofPanelProps) {
  const [keyword, setKeyword] = useState('')
  const [objectFilter, setObjectFilter] = useState('')

  const objectTypes = useMemo(() => {
    return Array.from(new Set((proofRows || []).map((row) => String(row.object_type || '').trim()).filter(Boolean)))
  }, [proofRows])

  const filteredRows = useMemo(() => {
    const kw = keyword.trim().toLowerCase()
    return (proofRows || []).filter((row) => {
      if (objectFilter && String(row.object_type || '') !== objectFilter) return false
      if (!kw) return true
      const haystack = `${row.proof_id} ${row.object_type || ''} ${row.action || ''} ${row.summary || ''}`.toLowerCase()
      return haystack.includes(kw)
    })
  }, [proofRows, keyword, objectFilter])

  return (
    <Card title="Proof 存证链" icon="🔒">
      <VPathDisplay uri={projectUri} />

      <div
        style={{
          display: 'grid',
          gridTemplateColumns: 'repeat(3, minmax(0, 1fr))',
          gap: 8,
          marginBottom: 10,
        }}
      >
        <div style={{ background: '#F8FAFF', border: '1px solid #DBEAFE', borderRadius: 8, padding: 10 }}>
          <div style={{ fontSize: 12, color: '#64748B' }}>总存证</div>
          <div style={{ fontSize: 20, fontWeight: 800, color: '#1A56DB', lineHeight: 1.2 }}>{proofStats.total}</div>
        </div>
        <div style={{ background: '#F8FAFF', border: '1px solid #E2E8F0', borderRadius: 8, padding: 10 }}>
          <div style={{ fontSize: 12, color: '#64748B' }}>对象类型</div>
          <div style={{ fontSize: 20, fontWeight: 800, color: '#0F172A', lineHeight: 1.2 }}>
            {Object.keys(proofStats.by_type).length}
          </div>
        </div>
        <div style={{ background: '#F8FAFF', border: '1px solid #E2E8F0', borderRadius: 8, padding: 10 }}>
          <div style={{ fontSize: 12, color: '#64748B' }}>动作类型</div>
          <div style={{ fontSize: 20, fontWeight: 800, color: '#0F172A', lineHeight: 1.2 }}>
            {Object.keys(proofStats.by_action).length}
          </div>
        </div>
      </div>

      <div
        style={{
          border: '1px solid #E2E8F0',
          borderRadius: 8,
          padding: 10,
          marginBottom: 12,
          background: '#FCFDFF',
        }}
      >
        <div style={{ fontSize: 12, fontWeight: 700, color: '#0F172A', marginBottom: 8 }}>节点树（v://）</div>
        {proofNodeRows.length === 0 ? (
          <div style={{ fontSize: 12, color: '#94A3B8' }}>当前项目暂无节点数据</div>
        ) : (
          <div style={{ display: 'grid', gap: 5 }}>
            {proofNodeRows.slice(0, 8).map((node, idx) => (
              <div
                key={`${node.uri || 'node'}-${idx}`}
                style={{
                  display: 'grid',
                  gridTemplateColumns: '1fr 86px 70px',
                  gap: 8,
                  alignItems: 'center',
                  fontSize: 12,
                }}
              >
                <span style={{ fontFamily: 'monospace', color: '#334155', wordBreak: 'break-all' }}>{node.uri || '-'}</span>
                <span style={{ color: '#64748B' }}>{node.node_type || '-'}</span>
                <span style={{ color: '#1A56DB', fontWeight: 700 }}>{node.status || '-'}</span>
              </div>
            ))}
            {proofNodeRows.length > 8 && <div style={{ fontSize: 12, color: '#64748B' }}>仅展示前 8 条，共 {proofNodeRows.length} 条</div>}
          </div>
        )}
      </div>

      <div style={{ display: 'grid', gridTemplateColumns: '1fr 180px', gap: 8, marginBottom: 10 }}>
        <input
          value={keyword}
          onChange={(e) => setKeyword(e.target.value)}
          placeholder="搜索 proof_id / 摘要 / 动作"
          style={{ border: '1px solid #E2E8F0', borderRadius: 8, padding: '8px 10px', fontSize: 13, fontFamily: 'var(--sans)' }}
        />
        <select
          value={objectFilter}
          onChange={(e) => setObjectFilter(e.target.value)}
          style={{ border: '1px solid #E2E8F0', borderRadius: 8, padding: '8px 10px', fontSize: 13, fontFamily: 'var(--sans)' }}
        >
          <option value="">全部对象</option>
          {objectTypes.map((type) => (
            <option key={type} value={type}>{type}</option>
          ))}
        </select>
      </div>

      {proofLoading ? (
        <div style={{ fontSize: 13, color: '#64748B', padding: '8px 2px' }}>加载中...</div>
      ) : filteredRows.length === 0 ? (
        <div style={{ border: '1px dashed #CBD5E1', borderRadius: 8, padding: 12 }}>
          <div style={{ fontSize: 13, color: '#94A3B8' }}>暂无匹配的 Proof 记录</div>
          <div style={{ display: 'flex', gap: 8, marginTop: 10 }}>
            {onGoInspection && (
              <button type="button" className="act-btn act-enter" onClick={onGoInspection}>去录入质检</button>
            )}
            {onGoReports && (
              <button type="button" className="act-btn act-proof" onClick={onGoReports}>去生成报告</button>
            )}
          </div>
        </div>
      ) : (
        <div style={{ display: 'grid', gap: 8 }}>
          {filteredRows.map((row) => (
            <div key={row.proof_id} style={{ border: '1px solid #E2E8F0', borderRadius: 8, padding: 10, background: '#F8FAFC' }}>
              <div style={{ fontFamily: 'monospace', fontSize: 12, color: '#0F172A', fontWeight: 700 }}>{row.proof_id}</div>
              <div style={{ fontSize: 12, color: '#64748B', marginTop: 2 }}>
                {(row.object_type || 'object')} · {(row.action || 'create')} · {row.summary || '-'}
              </div>
              <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginTop: 8 }}>
                <span style={{ fontSize: 12, color: '#94A3B8' }}>
                  {row.created_at ? new Date(row.created_at).toLocaleString('zh-CN').slice(0, 16) : '-'}
                </span>
                <Button
                  size="sm"
                  variant="secondary"
                  onClick={() => onVerifyProof(row.proof_id)}
                  disabled={proofVerifying === row.proof_id}
                >
                  {proofVerifying === row.proof_id ? '校验中...' : '校验'}
                </Button>
              </div>
            </div>
          ))}
        </div>
      )}
    </Card>
  )
}
