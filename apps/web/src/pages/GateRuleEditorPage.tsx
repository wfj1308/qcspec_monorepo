import React, { useCallback, useEffect, useMemo, useState } from 'react'
import { Button, Card, Input, Select, Toast, VPathDisplay } from '../components/ui'
import { useProof } from '../hooks/useApi'
import { useUIStore } from '../store'

type RuleRow = {
  seq: number
  inspection_item: string
  operator: string
  threshold: string
  threshold_value?: unknown
  spec_uri: string
  context: string
  unit?: string
  source?: string
}

type VersionRow = {
  proof_id: string
  gate_id?: string
  gate_id_base?: string
  version?: string
  created_at?: string
  author?: string
  rule_pack_hash?: string
}

const OPERATOR_OPTIONS = [
  { value: '>=', label: '>= (不低于)' },
  { value: '<=', label: '<= (不高于)' },
  { value: '>', label: '> (大于)' },
  { value: '<', label: '< (小于)' },
  { value: 'range', label: 'range (区间)' },
]

const EXECUTION_STRATEGY_OPTIONS = [
  { value: 'all_pass', label: 'all_pass (全部通过)' },
  { value: 'any_pass', label: 'any_pass (任一通过)' },
]

const FAIL_ACTION_OPTIONS = [
  { value: 'trigger_review_trip', label: '触发复核 Trip' },
  { value: 'block_and_alert', label: '阻断并预警' },
  { value: 'warn_only', label: '仅预警' },
]

function parseQuery(): URLSearchParams {
  if (typeof window === 'undefined') return new URLSearchParams()
  return new URLSearchParams(window.location.search || '')
}

function normalizeRules(raw: unknown): RuleRow[] {
  if (!Array.isArray(raw)) return []
  const out: RuleRow[] = []
  for (let i = 0; i < raw.length; i += 1) {
    const row = raw[i]
    if (!row || typeof row !== 'object') continue
    const item = row as Record<string, unknown>
    out.push({
      seq: Number(item.seq || i + 1),
      inspection_item: String(item.inspection_item || ''),
      operator: String(item.operator || 'range'),
      threshold: String(item.threshold || ''),
      threshold_value: item.threshold_value,
      spec_uri: String(item.spec_uri || ''),
      context: String(item.context || ''),
      unit: String(item.unit || ''),
      source: String(item.source || ''),
    })
  }
  return out
}

export default function GateRuleEditorPage({ subitemCode }: { subitemCode: string }) {
  const normalizedSubitemCode = useMemo(() => String(subitemCode || '').trim(), [subitemCode])
  const {
    getGateEditorPayload,
    importGateRulesFromNorm,
    generateGateRulesViaAi,
    saveGateRuleVersion,
    rollbackGateRuleVersion,
  } = useProof()
  const { toastMsg, showToast } = useUIStore()

  const [projectUri, setProjectUri] = useState(() => parseQuery().get('project_uri') || 'v://project/demo/highway/JK-C08/')
  const [gateIdBase, setGateIdBase] = useState('')
  const [version, setVersion] = useState('v1.0')
  const [executionStrategy, setExecutionStrategy] = useState('all_pass')
  const [failAction, setFailAction] = useState('trigger_review_trip')
  const [rules, setRules] = useState<RuleRow[]>([])
  const [history, setHistory] = useState<VersionRow[]>([])
  const [selectedHistoryProofId, setSelectedHistoryProofId] = useState('')
  const [specUriInput, setSpecUriInput] = useState('v://norm/GB50204@2015/5.3.2#diameter_tolerance')
  const [aiPrompt, setAiPrompt] = useState('主梁部位屈服强度不低于 400MPa')
  const [specDictKey, setSpecDictKey] = useState('')
  const [loading, setLoading] = useState(false)

  const loadEditorPayload = useCallback(async () => {
    if (!projectUri || !normalizedSubitemCode) return
    setLoading(true)
    try {
      const res = await getGateEditorPayload(projectUri, normalizedSubitemCode) as {
        ok?: boolean
        gate_id_base?: string
        version?: string
        execution_strategy?: string
        fail_action?: string
        rules?: unknown
        history?: unknown
        spec_dict_key?: string
      } | null
      if (!res?.ok) {
        showToast('规则加载失败')
        return
      }
      setGateIdBase(String(res.gate_id_base || ''))
      setVersion(String(res.version || 'v1.0'))
      setExecutionStrategy(String(res.execution_strategy || 'all_pass'))
      setFailAction(String(res.fail_action || 'trigger_review_trip'))
      setRules(normalizeRules(res.rules))
      setSpecDictKey(String(res.spec_dict_key || ''))
      const historyRows = Array.isArray(res.history) ? (res.history as VersionRow[]) : []
      setHistory(historyRows)
      setSelectedHistoryProofId(historyRows[0]?.proof_id || '')
    } finally {
      setLoading(false)
    }
  }, [getGateEditorPayload, projectUri, normalizedSubitemCode, showToast])

  useEffect(() => {
    loadEditorPayload()
  }, [loadEditorPayload])

  const updateRule = (index: number, patch: Partial<RuleRow>) => {
    setRules((prev) => prev.map((item, idx) => (idx === index ? { ...item, ...patch, seq: idx + 1 } : item)))
  }

  const appendRule = () => {
    setRules((prev) => [
      ...prev,
      {
        seq: prev.length + 1,
        inspection_item: '',
        operator: 'range',
        threshold: '',
        spec_uri: '',
        context: normalizedSubitemCode,
      },
    ])
  }

  const removeRule = (index: number) => {
    setRules((prev) => prev.filter((_, idx) => idx !== index).map((item, idx) => ({ ...item, seq: idx + 1 })))
  }

  const handleImportFromNorm = async () => {
    if (!specUriInput.trim()) return
    const res = await importGateRulesFromNorm({
      spec_uri: specUriInput,
      context: normalizedSubitemCode,
    }) as { ok?: boolean; rules?: unknown } | null

    if (!res?.ok) {
      showToast('规范导入失败')
      return
    }

    const importedRules = normalizeRules(res.rules)
    if (!importedRules.length) {
      showToast('规范中未解析到可用条文')
      return
    }

    setRules(importedRules)
    showToast(`已导入 ${importedRules.length} 条规则`)
  }

  const handleGenerateViaAi = async () => {
    if (!aiPrompt.trim()) return

    const res = await generateGateRulesViaAi({
      prompt: aiPrompt,
      subitem_code: normalizedSubitemCode,
    }) as { ok?: boolean; rules?: unknown; confidence?: number } | null

    if (!res?.ok) {
      showToast('AI 规则生成失败')
      return
    }

    const generatedRules = normalizeRules(res.rules)
    if (!generatedRules.length) {
      showToast('AI 未生成有效规则')
      return
    }

    setRules(generatedRules)
    showToast(`ClawPeg 已生成规则，置信度 ${Number(res.confidence || 0).toFixed(2)}`)
  }

  const saveVersion = async (applyToSimilar: boolean) => {
    if (!rules.length) {
      showToast('请至少保留一条规则')
      return
    }

    const res = await saveGateRuleVersion({
      project_uri: projectUri,
      subitem_code: normalizedSubitemCode,
      gate_id_base: gateIdBase,
      rules,
      execution_strategy: executionStrategy,
      fail_action: failAction,
      apply_to_similar: applyToSimilar,
      executor_uri: 'v://executor/chief-engineer/',
      metadata: {
        source: 'visual_rule_editor',
      },
    }) as { ok?: boolean; version?: string; batch_apply?: { applied_count?: number }; spec_dict_key?: string } | null

    if (!res?.ok) {
      showToast('保存失败')
      return
    }

    setVersion(String(res.version || version))
    if (res.spec_dict_key) setSpecDictKey(String(res.spec_dict_key))
    showToast(`保存成功，已生成新版本 ${res.version || ''}，应用 ${Number(res.batch_apply?.applied_count || 0)} 项`)
    await loadEditorPayload()
  }

  const handleRollback = async () => {
    if (!selectedHistoryProofId) {
      showToast('请先选择回滚版本')
      return
    }

    const res = await rollbackGateRuleVersion({
      project_uri: projectUri,
      subitem_code: normalizedSubitemCode,
      target_proof_id: selectedHistoryProofId,
      apply_to_similar: true,
      executor_uri: 'v://executor/chief-engineer/',
    }) as { ok?: boolean; version?: string } | null

    if (!res?.ok) {
      showToast('回滚失败')
      return
    }

    showToast(`回滚完成，已生成新版本 ${res.version || ''}`)
    await loadEditorPayload()
  }

  const openSpecDictEditor = () => {
    if (!specDictKey) {
      showToast('当前细目尚未绑定 SpecDict')
      return
    }
    const url = `/admin/spec-dict/${encodeURIComponent(specDictKey)}`
    if (typeof window !== 'undefined') {
      window.open(url, '_blank', 'noopener,noreferrer')
    }
  }

  return (
    <div style={{ maxWidth: 1400, margin: '0 auto', padding: 20, paddingBottom: 94 }}>
      <Card title={`Gate 规则中控台 · ${normalizedSubitemCode}`} icon="🧪">
        <VPathDisplay uri={`${projectUri}/boq/${normalizedSubitemCode}`} />
        <div style={{ display: 'grid', gridTemplateColumns: '2fr 1fr', gap: 14 }}>
          <div>
            <div style={{ display: 'grid', gridTemplateColumns: '1fr auto', gap: 8, marginBottom: 10 }}>
              <Input label="项目 URI" value={projectUri} onChange={setProjectUri} />
              <Button variant="secondary" onClick={loadEditorPayload} disabled={loading}>
                {loading ? '加载中...' : '刷新'}
              </Button>
            </div>

            <Card title="规则列表（可编辑）" icon="📋" style={{ marginBottom: 0 }}>
              <div style={{ overflowX: 'auto' }}>
                <table style={{ width: '100%', borderCollapse: 'collapse', fontSize: 12 }}>
                  <thead>
                    <tr style={{ background: '#F8FAFC' }}>
                      <th style={thStyle}>序号</th>
                      <th style={thStyle}>检验项目</th>
                      <th style={thStyle}>运算符</th>
                      <th style={thStyle}>阈值</th>
                      <th style={thStyle}>v:// 规范引用</th>
                      <th style={thStyle}>适用部位</th>
                      <th style={thStyle}>操作</th>
                    </tr>
                  </thead>
                  <tbody>
                    {rules.map((rule, idx) => (
                      <tr key={`rule-${idx}`}>
                        <td style={tdStyle}>{idx + 1}</td>
                        <td style={tdStyle}>
                          <input value={rule.inspection_item} onChange={(e) => updateRule(idx, { inspection_item: e.target.value })} style={inputCellStyle} />
                        </td>
                        <td style={tdStyle}>
                          <select value={rule.operator} onChange={(e) => updateRule(idx, { operator: e.target.value })} style={inputCellStyle}>
                            {OPERATOR_OPTIONS.map((opt) => (
                              <option key={opt.value} value={opt.value}>{opt.label}</option>
                            ))}
                          </select>
                        </td>
                        <td style={tdStyle}>
                          <input value={rule.threshold} onChange={(e) => updateRule(idx, { threshold: e.target.value })} style={inputCellStyle} />
                        </td>
                        <td style={tdStyle}>
                          <input value={rule.spec_uri} onChange={(e) => updateRule(idx, { spec_uri: e.target.value })} style={inputCellStyle} />
                        </td>
                        <td style={tdStyle}>
                          <input value={rule.context} onChange={(e) => updateRule(idx, { context: e.target.value })} style={inputCellStyle} />
                        </td>
                        <td style={tdStyle}>
                          <Button size="sm" variant="danger" onClick={() => removeRule(idx)}>删除</Button>
                        </td>
                      </tr>
                    ))}
                    {!rules.length && (
                      <tr>
                        <td colSpan={7} style={{ ...tdStyle, textAlign: 'center', color: '#94A3B8' }}>暂无规则，请先导入规范或使用 AI 生成</td>
                      </tr>
                    )}
                  </tbody>
                </table>
              </div>
              <div style={{ marginTop: 10 }}>
                <Button size="sm" variant="secondary" onClick={appendRule}>新增规则行</Button>
              </div>
            </Card>
          </div>

          <div style={{ display: 'grid', gap: 10, alignContent: 'start' }}>
            <Card title="配置面板" icon="⚙️" style={{ marginBottom: 0 }}>
              <Input label="Gate 基础 ID" value={gateIdBase} onChange={setGateIdBase} />
              <div style={{ height: 8 }} />
              <Input label="当前版本" value={version} onChange={setVersion} />
              <div style={{ height: 8 }} />
              <Select label="执行策略" value={executionStrategy} onChange={setExecutionStrategy} options={EXECUTION_STRATEGY_OPTIONS} />
              <div style={{ height: 8 }} />
              <Select label="失败后动作" value={failAction} onChange={setFailAction} options={FAIL_ACTION_OPTIONS} />
              <div style={{ height: 8 }} />
              <Input label="SpecDict Key" value={specDictKey} onChange={setSpecDictKey} />
              <div style={{ marginTop: 8 }}>
                <Button size="sm" variant="secondary" onClick={openSpecDictEditor}>SpecDict 穿透查看</Button>
              </div>
            </Card>

            <Card title="规范库导入" icon="📚" style={{ marginBottom: 0 }}>
              <Input label="Spec URI" value={specUriInput} onChange={setSpecUriInput} />
              <div style={{ marginTop: 8 }}>
                <Button size="sm" onClick={handleImportFromNorm}>导入条文规则</Button>
              </div>
            </Card>

            <Card title="自然语言生成（ClawPeg）" icon="🤖" style={{ marginBottom: 0 }}>
              <textarea
                value={aiPrompt}
                onChange={(e) => setAiPrompt(e.target.value)}
                rows={4}
                style={{
                  width: '100%',
                  border: '1px solid #E2E8F0',
                  borderRadius: 8,
                  padding: 8,
                  fontSize: 12,
                  resize: 'vertical',
                }}
              />
              <div style={{ marginTop: 8 }}>
                <Button size="sm" onClick={handleGenerateViaAi}>AI 生成规则</Button>
              </div>
            </Card>

            <Card title="版本链（可回滚）" icon="🧾" style={{ marginBottom: 0 }}>
              <div style={{ display: 'grid', gap: 6, maxHeight: 180, overflowY: 'auto' }}>
                {history.map((v) => (
                  <label key={v.proof_id} style={{ border: '1px solid #E2E8F0', borderRadius: 8, padding: 8, fontSize: 12 }}>
                    <input
                      type="radio"
                      name="rollbackVersion"
                      checked={selectedHistoryProofId === v.proof_id}
                      onChange={() => setSelectedHistoryProofId(v.proof_id)}
                    />
                    <span style={{ marginLeft: 8, fontWeight: 700 }}>{v.version || '-'}</span>
                    <span style={{ marginLeft: 8, color: '#64748B' }}>{v.created_at ? new Date(v.created_at).toLocaleString('zh-CN') : '-'}</span>
                  </label>
                ))}
                {!history.length && <div style={{ color: '#94A3B8', fontSize: 12 }}>暂无历史版本</div>}
              </div>
            </Card>
          </div>
        </div>
      </Card>

      <div
        style={{
          position: 'fixed',
          left: 0,
          right: 0,
          bottom: 0,
          borderTop: '1px solid #E2E8F0',
          background: '#FFFFFF',
          padding: '10px 16px',
          display: 'flex',
          justifyContent: 'center',
          gap: 8,
          zIndex: 99,
        }}
      >
        <Button onClick={() => saveVersion(false)}>保存新版本</Button>
        <Button variant="secondary" onClick={() => saveVersion(true)}>保存并应用同类细目</Button>
        <Button variant="danger" onClick={handleRollback}>回滚到选中版本</Button>
        <Button variant="ghost" onClick={() => { if (typeof window !== 'undefined') window.location.href = '/' }}>返回控制台</Button>
      </div>
      <Toast message={toastMsg} />
    </div>
  )
}

const thStyle: React.CSSProperties = {
  border: '1px solid #E2E8F0',
  padding: '8px 6px',
  textAlign: 'left',
  whiteSpace: 'nowrap',
}

const tdStyle: React.CSSProperties = {
  border: '1px solid #E2E8F0',
  padding: '6px',
  verticalAlign: 'middle',
}

const inputCellStyle: React.CSSProperties = {
  width: '100%',
  border: '1px solid #E2E8F0',
  borderRadius: 6,
  padding: '4px 6px',
  fontSize: 12,
}
