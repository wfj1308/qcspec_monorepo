import React, { useEffect, useMemo, useRef, useState } from 'react'
import { Button, Card, Input, Toast, VPathDisplay } from '../components/ui'
import {
  createNormRefApi,
  type NormRefIngestJob,
  type NormRefIngestRuleCandidate,
  type NormRefRuleOverride,
  type NormRefRule,
  type NormRefRuleConflict,
} from '../services/normref'
import { useAuthStore, useUIStore } from '../store'

type CandidateEditor = {
  candidateId: string
  ruleId: string
  category: string
  fieldKey: string
  operator: string
  thresholdValue: string
  unit: string
  severity: string
  normRef: string
}

function parseRulesInput(value: string): string[] {
  return value
    .split(/[\n,]+/)
    .map((item) => item.trim())
    .filter(Boolean)
}

function toEditor(row: NormRefIngestRuleCandidate): CandidateEditor {
  return {
    candidateId: row.candidateId,
    ruleId: row.ruleId,
    category: row.category,
    fieldKey: row.fieldKey,
    operator: row.operator,
    thresholdValue: row.thresholdValue,
    unit: row.unit,
    severity: row.severity,
    normRef: row.normRef,
  }
}

function toLocalDateText(value: string): string {
  if (!value) return '-'
  const d = new Date(value)
  if (Number.isNaN(d.getTime())) return value
  return d.toLocaleString('zh-CN', { hour12: false })
}

function toIngestStatusText(status: string): string {
  const token = (status || '').trim().toLowerCase()
  if (token === 'queued') return '排队中'
  if (token === 'running') return '解析中'
  if (token === 'review_required') return '待复核'
  if (token === 'completed') return '已完成'
  if (token === 'failed') return '失败'
  return status || '-'
}

function isIngestProcessing(status: string): boolean {
  const token = (status || '').trim().toLowerCase()
  return token === 'queued' || token === 'running'
}

function toCandidateStatusText(status: string): string {
  const token = (status || '').trim().toLowerCase()
  if (token === 'approved') return '已通过'
  if (token === 'rejected') return '已驳回'
  if (token === 'pending') return '待处理'
  return status || '-'
}

function toScopeText(scope: string): string {
  const token = (scope || '').trim().toLowerCase()
  if (token === 'national') return '国家级'
  if (token === 'industry') return '行业级'
  if (token === 'local') return '地方级'
  if (token === 'enterprise') return '企业级'
  if (token === 'project') return '项目级'
  if (token === 'unknown') return '未知'
  return scope || '-'
}

function toOperatorText(operator: string): string {
  const token = (operator || '').trim().toLowerCase()
  if (token === 'eq') return '等于 (=)'
  if (token === 'gte') return '大于等于 (>=)'
  if (token === 'lte') return '小于等于 (<=)'
  if (token === 'range') return '区间'
  return operator || '-'
}

function toSeverityText(severity: string): string {
  const token = (severity || '').trim().toLowerCase()
  if (token === 'mandatory') return '强制'
  if (token === 'warning') return '警告'
  if (token === 'info') return '提示'
  return severity || '-'
}

function statusBadgeStyle(status: string): React.CSSProperties {
  const token = (status || '').trim().toLowerCase()
  if (token === 'approved' || token === 'completed') {
    return { ...badgeBase, background: '#ECFDF3', color: '#067647', borderColor: '#ABEFC6' }
  }
  if (token === 'rejected' || token === 'failed') {
    return { ...badgeBase, background: '#FEF3F2', color: '#B42318', borderColor: '#FECDCA' }
  }
  if (token === 'review_required' || token === 'running' || token === 'queued' || token === 'pending') {
    return { ...badgeBase, background: '#FFFAEB', color: '#B54708', borderColor: '#FEDF89' }
  }
  return { ...badgeBase, background: '#F8FAFC', color: '#334155', borderColor: '#E2E8F0' }
}

export default function NormRefRulesPage() {
  const token = useAuthStore((s) => s.token)
  const { toastMsg, showToast } = useUIStore()
  const api = useMemo(() => createNormRefApi({ getToken: () => token }), [token])

  const [loading, setLoading] = useState(false)

  const [category, setCategory] = useState('bridge/pile-hole-check')
  const [version, setVersion] = useState('latest')
  const [scope, setScope] = useState('')
  const [rules, setRules] = useState<NormRefRule[]>([])
  const [conflicts, setConflicts] = useState<NormRefRuleConflict[]>([])
  const [overrides, setOverrides] = useState<NormRefRuleOverride[]>([])
  const [overrideReason, setOverrideReason] = useState('项目人工裁决')
  const [overrideBy, setOverrideBy] = useState('规则管理员')

  const [ruleId, setRuleId] = useState('bridge.pile-hole-check.hole-diameter-tolerance')
  const [ruleDetailVersion, setRuleDetailVersion] = useState('latest')
  const [ruleDetailText, setRuleDetailText] = useState('{}')
  const [ruleUri, setRuleUri] = useState('')

  const [validateRulesText, setValidateRulesText] = useState('bridge.pile-hole-check.hole-diameter-tolerance')
  const [validateVersion, setValidateVersion] = useState('2026-04')
  const [validateDataText, setValidateDataText] = useState(
    JSON.stringify(
      {
        actual_data: { hole_diameter: 1.48 },
        design_data: { hole_diameter: 1.5 },
        context: { form_code: '桥施7表' },
      },
      null,
      2,
    ),
  )
  const [validateResultText, setValidateResultText] = useState('{}')

  const [ingestFile, setIngestFile] = useState<File | null>(null)
  const [ingestStdCode, setIngestStdCode] = useState('JTG-F80-1-2017')
  const [ingestTitle, setIngestTitle] = useState('公路工程质量检验评定标准 第一册 土建工程')
  const [ingestLevel, setIngestLevel] = useState('industry')
  const [backgroundParse, setBackgroundParse] = useState(true)
  const [ingestJobId, setIngestJobId] = useState('')
  const [ingestStatus, setIngestStatus] = useState('')
  const [ingestJob, setIngestJob] = useState<NormRefIngestJob | null>(null)
  const [ingestWarnings, setIngestWarnings] = useState<string[]>([])
  const [ingestCandidates, setIngestCandidates] = useState<NormRefIngestRuleCandidate[]>([])
  const [candidateStatusFilter, setCandidateStatusFilter] = useState<'all' | 'pending' | 'approved' | 'rejected'>('all')
  const [candidateEditor, setCandidateEditor] = useState<CandidateEditor | null>(null)

  const [publishVersion, setPublishVersion] = useState('2026-04')
  const [writeToDocs, setWriteToDocs] = useState(false)
  const [publishResultText, setPublishResultText] = useState('{}')
  const pollingRef = useRef<ReturnType<typeof setInterval> | null>(null)

  const statusSummary = useMemo(() => {
    const total = ingestCandidates.length
    const approved = ingestCandidates.filter((x) => x.status === 'approved').length
    const rejected = ingestCandidates.filter((x) => x.status === 'rejected').length
    return { total, approved, rejected, pending: total - approved - rejected }
  }, [ingestCandidates])

  const filteredCandidates = useMemo(() => {
    if (candidateStatusFilter === 'all') return ingestCandidates
    return ingestCandidates.filter((row) => (row.status || '').trim().toLowerCase() === candidateStatusFilter)
  }, [candidateStatusFilter, ingestCandidates])

  const isParsing = useMemo(() => isIngestProcessing(ingestStatus), [ingestStatus])

  const loadRules = async () => {
    setLoading(true)
    try {
      const out = await api.listRules(category.trim(), version.trim() || 'latest', {
        refresh: true,
        scope: scope.trim() || undefined,
      })
      setRules(out.rules || [])
      showToast(`规则已加载: ${Number(out.count || 0)} 条`)
    } catch (error) {
      showToast(`规则列表加载失败: ${String((error as Error)?.message || error)}`)
    } finally {
      setLoading(false)
    }
  }

  const loadConflicts = async () => {
    setLoading(true)
    try {
      const out = await api.listRuleConflicts(category.trim(), version.trim() || 'latest', scope.trim())
      setConflicts(out.conflicts || [])
      await refreshOverrides()
      showToast(`冲突规则: ${Number(out.count || 0)} 条`)
    } catch (error) {
      showToast(`冲突查询失败: ${String((error as Error)?.message || error)}`)
    } finally {
      setLoading(false)
    }
  }

  const refreshOverrides = async () => {
    const out = await api.listRuleOverrides()
    setOverrides(out.overrides || [])
  }

  const applyOverride = async (conflict: NormRefRuleConflict, selectedUri: string) => {
    if (!conflict.ruleId || !conflict.version || !selectedUri) return
    setLoading(true)
    try {
      await api.setRuleOverride({
        ruleId: conflict.ruleId,
        version: conflict.version,
        selectedUri,
        reason: overrideReason.trim(),
        updatedBy: overrideBy.trim(),
      })
      await Promise.all([loadRules(), loadConflicts()])
      showToast('覆盖规则已保存')
    } catch (error) {
      showToast(`覆盖保存失败: ${String((error as Error)?.message || error)}`)
    } finally {
      setLoading(false)
    }
  }

  const clearOverride = async (conflict: NormRefRuleConflict) => {
    setLoading(true)
    try {
      await api.clearRuleOverride(conflict.ruleId, conflict.version)
      await Promise.all([loadRules(), loadConflicts()])
      showToast('覆盖规则已清除')
    } catch (error) {
      showToast(`清除覆盖失败: ${String((error as Error)?.message || error)}`)
    } finally {
      setLoading(false)
    }
  }

  const getOverrideForConflict = (conflict: NormRefRuleConflict) =>
    overrides.find((row) => row.ruleId === conflict.ruleId && row.version === conflict.version)

  const stopPolling = () => {
    if (pollingRef.current) {
      clearInterval(pollingRef.current)
      pollingRef.current = null
    }
  }

  const startPolling = (jobId: string) => {
    stopPolling()
    pollingRef.current = setInterval(() => {
      void (async () => {
        try {
          const job = await api.ingestGetJob(jobId)
          const candidates = await api.ingestListCandidates(jobId)
          setIngestStatus(job.status)
          setIngestJob(job)
          setIngestWarnings(job.warnings || [])
          setIngestCandidates(candidates)
          if (job.status === 'review_required' || job.status === 'completed' || job.status === 'failed') {
            stopPolling()
            showToast(`解析完成：${toIngestStatusText(job.status)}，候选规则 ${candidates.length} 条`)
          }
        } catch {
          stopPolling()
        }
      })()
    }, 2000)
  }

  const loadRuleDetail = async () => {
    if (!ruleId.trim()) {
      showToast('请输入 rule_id')
      return
    }
    setLoading(true)
    try {
      const out = await api.getRule(ruleId.trim(), ruleDetailVersion.trim() || 'latest', scope.trim())
      setRuleUri(out.uri || '')
      setRuleDetailText(JSON.stringify(out.rule || {}, null, 2))
      showToast(`规则加载成功: ${out.resolvedVersion || '-'}`)
    } catch (error) {
      showToast(`规则详情加载失败: ${String((error as Error)?.message || error)}`)
    } finally {
      setLoading(false)
    }
  }

  const runValidate = async () => {
    const parsedRules = parseRulesInput(validateRulesText)
    if (!parsedRules.length) {
      showToast('至少输入一个 rule_id')
      return
    }

    let parsedData: Record<string, unknown> = {}
    try {
      parsedData = JSON.parse(validateDataText || '{}') as Record<string, unknown>
    } catch {
      showToast('校验数据 JSON 格式错误')
      return
    }

    setLoading(true)
    try {
      const out = await api.validateRules({
        rules: parsedRules,
        data: parsedData,
        normrefVersion: validateVersion.trim() || 'latest',
        scope: scope.trim() || undefined,
      })
      setValidateResultText(JSON.stringify(out.raw || out, null, 2))
      showToast(out.passed ? '校验通过' : '校验未通过')
    } catch (error) {
      showToast(`规则校验失败: ${String((error as Error)?.message || error)}`)
    } finally {
      setLoading(false)
    }
  }

  const runIngestUpload = async () => {
    if (!ingestFile) {
      showToast('请先选择规范文件')
      return
    }
    if (!ingestStdCode.trim()) {
      showToast('请输入标准编号')
      return
    }
    setLoading(true)
    try {
      const job = await api.ingestUpload(
        ingestFile,
        ingestStdCode.trim(),
        ingestTitle.trim(),
        ingestLevel.trim() || 'industry',
        { asyncMode: backgroundParse },
      )
      setIngestJobId(job.jobId)
      setIngestStatus(job.status)
      setIngestJob(job)
      setIngestWarnings(job.warnings || [])
      setIngestCandidates(job.candidates || [])
      setCandidateEditor(null)
      if (job.status === 'queued' || job.status === 'running') {
        showToast(`解析任务已提交，后台处理中: ${job.jobId}`)
        if (backgroundParse) {
          startPolling(job.jobId)
        }
      } else {
        showToast(`解析任务已创建: ${job.jobId}`)
      }
    } catch (error) {
      showToast(`规范解析失败: ${String((error as Error)?.message || error)}`)
    } finally {
      setLoading(false)
    }
  }

  const refreshIngestJob = async () => {
    if (!ingestJobId.trim()) {
      showToast('请输入任务 ID')
      return
    }
    setLoading(true)
    try {
      const job = await api.ingestGetJob(ingestJobId.trim())
      const candidates = await api.ingestListCandidates(ingestJobId.trim())
      setIngestStatus(job.status)
      setIngestJob(job)
      setIngestWarnings(job.warnings || [])
      setIngestCandidates(candidates)
      showToast(`任务状态: ${toIngestStatusText(job.status)}，候选规则: ${candidates.length}`)
      if (job.status === 'queued' || job.status === 'running') {
        startPolling(ingestJobId.trim())
      } else {
        stopPolling()
      }
    } catch (error) {
      showToast(`任务查询失败: ${String((error as Error)?.message || error)}`)
    } finally {
      setLoading(false)
    }
  }

  const setCandidateStatus = async (candidateId: string, status: 'approved' | 'rejected') => {
    if (!ingestJobId.trim()) {
      showToast('缺少任务 ID')
      return
    }
    setLoading(true)
    try {
      const updated = await api.ingestSetCandidateStatus(candidateId, ingestJobId.trim(), status)
      setIngestCandidates((prev) => prev.map((item) => (item.candidateId === updated.candidateId ? updated : item)))
      if (candidateEditor?.candidateId === updated.candidateId) {
        setCandidateEditor(toEditor(updated))
      }
      showToast(status === 'approved' ? '候选规则已通过' : '候选规则已驳回')
    } catch (error) {
      showToast(`候选规则审核失败: ${String((error as Error)?.message || error)}`)
    } finally {
      setLoading(false)
    }
  }

  const saveCandidatePatch = async () => {
    if (!ingestJobId.trim() || !candidateEditor) {
      showToast('缺少任务上下文，无法保存')
      return
    }
    setLoading(true)
    try {
      const updated = await api.ingestPatchCandidate(candidateEditor.candidateId, ingestJobId.trim(), {
        ruleId: candidateEditor.ruleId,
        category: candidateEditor.category,
        fieldKey: candidateEditor.fieldKey,
        operator: candidateEditor.operator,
        thresholdValue: candidateEditor.thresholdValue,
        unit: candidateEditor.unit,
        severity: candidateEditor.severity,
        normRef: candidateEditor.normRef,
      })
      setIngestCandidates((prev) => prev.map((item) => (item.candidateId === updated.candidateId ? updated : item)))
      setCandidateEditor(toEditor(updated))
      showToast('候选规则已保存')
    } catch (error) {
      showToast(`保存失败: ${String((error as Error)?.message || error)}`)
    } finally {
      setLoading(false)
    }
  }

  const runPublish = async () => {
    if (!ingestJobId.trim()) {
      showToast('请输入任务 ID')
      return
    }
    const approved = ingestCandidates.filter((item) => item.status === 'approved').map((item) => item.candidateId)
    if (!approved.length) {
      showToast('请先通过至少一条候选规则')
      return
    }
    setLoading(true)
    try {
      const result = await api.ingestPublish({
        jobId: ingestJobId.trim(),
        candidateIds: approved,
        versionTag: publishVersion.trim() || 'latest',
        writeToDocs,
      })
      setPublishResultText(JSON.stringify(result.raw || result, null, 2))
      showToast(`发布完成: ${result.publishedCount} 条规则`)
      await loadRules()
    } catch (error) {
      showToast(`发布失败: ${String((error as Error)?.message || error)}`)
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    void Promise.all([loadRules(), refreshOverrides()])
    return () => {
      stopPolling()
    }
  }, [])

  return (
    <div style={{ maxWidth: 1440, margin: '0 auto', padding: 20, paddingBottom: 32 }}>
      <Card title="规范规则管理" icon="📚">
        <VPathDisplay uri="v://normref.com/std/jtg-f80-1-2017@2017" />
        <div style={{ color: '#64748B', fontSize: 12, marginBottom: 8 }}>
          支持规则列表、规则详情、批量校验、冲突裁决与规范解析发布。
        </div>
      </Card>

      <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 12 }}>
        <Card title="规则列表" icon="🧾" style={{ marginBottom: 0 }}>
          <div style={{ display: 'grid', gridTemplateColumns: '2fr 1fr 1fr auto auto', gap: 8 }}>
            <Input label="规则分类" value={category} onChange={setCategory} />
            <Input label="版本" value={version} onChange={setVersion} />
            <Input label="层级" value={scope} onChange={setScope} />
            <div style={{ alignSelf: 'end' }}><Button onClick={loadRules} disabled={loading}>{loading ? '加载中...' : '加载规则'}</Button></div>
            <div style={{ alignSelf: 'end' }}><Button onClick={loadConflicts} disabled={loading}>查看冲突</Button></div>
          </div>

          <div style={{ marginTop: 10, maxHeight: 260, overflowY: 'auto', border: '1px solid #E2E8F0', borderRadius: 8 }}>
            <table style={{ width: '100%', borderCollapse: 'collapse', fontSize: 12 }}>
              <thead>
                <tr style={{ background: '#F8FAFC' }}>
                  <th style={th}>规则ID</th>
                  <th style={th}>版本</th>
                  <th style={th}>层级</th>
                  <th style={th}>覆盖</th>
                  <th style={th}>规则URI</th>
                  <th style={th}>哈希</th>
                </tr>
              </thead>
              <tbody>
                {rules.map((row) => (
                  <tr key={`${row.ruleId}@${row.version}`} onClick={() => { setRuleId(row.ruleId); setRuleDetailVersion(row.version) }} style={{ cursor: 'pointer' }}>
                    <td style={td}>{row.ruleId}</td>
                    <td style={td}>{row.version}</td>
                    <td style={td}>{toScopeText(row.scope || '')}</td>
                    <td style={td}>{row.overrideApplied ? '已覆盖' : '-'}</td>
                    <td style={td}>{row.uri}</td>
                    <td style={td}>{row.hash.slice(0, 16)}...</td>
                  </tr>
                ))}
                {!rules.length && (
                  <tr><td colSpan={6} style={{ ...td, textAlign: 'center', color: '#94A3B8' }}>暂无数据</td></tr>
                )}
              </tbody>
            </table>
          </div>
        </Card>

        <Card title="规则详情" icon="🔍" style={{ marginBottom: 0 }}>
          <div style={{ display: 'grid', gridTemplateColumns: '2fr 1fr auto', gap: 8 }}>
            <Input label="规则ID" value={ruleId} onChange={setRuleId} />
            <Input label="版本" value={ruleDetailVersion} onChange={setRuleDetailVersion} />
            <div style={{ alignSelf: 'end' }}><Button onClick={loadRuleDetail} disabled={loading}>加载详情</Button></div>
          </div>
          {ruleUri ? <div style={{ marginTop: 8 }}><VPathDisplay uri={ruleUri} /></div> : null}
          <textarea value={ruleDetailText} onChange={(e) => setRuleDetailText(e.target.value)} rows={14} style={textAreaStyle} />
        </Card>
      </div>

      <Card title="规则冲突裁决" icon="⚖" style={{ marginTop: 12 }}>
        <div style={{ fontSize: 12, color: '#64748B', marginBottom: 8 }}>
          同一规则在同版本下出现多来源冲突时，系统按层级优先级自动选中一条；也支持手工覆盖。
        </div>
        <div style={{ display: 'grid', gridTemplateColumns: '2fr 1fr auto', gap: 8, marginBottom: 8 }}>
          <Input label="覆盖原因" value={overrideReason} onChange={setOverrideReason} />
          <Input label="操作人" value={overrideBy} onChange={setOverrideBy} />
          <div style={{ alignSelf: 'end' }}><Button onClick={refreshOverrides} disabled={loading}>刷新覆盖列表</Button></div>
        </div>
        <div style={{ maxHeight: 220, overflowY: 'auto', border: '1px solid #E2E8F0', borderRadius: 8 }}>
          <table style={{ width: '100%', borderCollapse: 'collapse', fontSize: 12 }}>
            <thead>
              <tr style={{ background: '#F8FAFC' }}>
                <th style={th}>规则ID</th>
                <th style={th}>版本</th>
                <th style={th}>已选层级</th>
                <th style={th}>已选URI</th>
                <th style={th}>覆盖状态</th>
                <th style={th}>候选数</th>
                <th style={th}>操作</th>
              </tr>
            </thead>
            <tbody>
              {conflicts.map((row) => {
                const override = getOverrideForConflict(row)
                return (
                <tr key={`${row.ruleId}@${row.version}`}>
                  <td style={td}>{row.ruleId}</td>
                  <td style={td}>{row.version}</td>
                  <td style={td}>{toScopeText(row.selectedScope)}</td>
                  <td style={td}>{row.selectedUri}</td>
                  <td style={td}>
                    {override
                      ? `${override.selectedUri} (${override.updatedBy || '-'})`
                      : row.overrideApplied ? '已覆盖' : '-'}
                  </td>
                  <td style={td}>{row.candidateCount}</td>
                  <td style={td}>
                    <div style={{ display: 'flex', gap: 6, flexWrap: 'wrap' }}>
                      {row.candidates.map((candidate) => (
                        <Button
                          key={candidate.uri}
                          onClick={() => applyOverride(row, candidate.uri)}
                          disabled={loading}
                        >
                          选用 {toScopeText(candidate.scope)}
                        </Button>
                      ))}
                      <Button onClick={() => clearOverride(row)} disabled={loading || !override}>
                        清除覆盖
                      </Button>
                    </div>
                  </td>
                </tr>
                )})}
              {!conflicts.length && (
                <tr><td colSpan={7} style={{ ...td, textAlign: 'center', color: '#94A3B8' }}>暂无冲突</td></tr>
              )}
            </tbody>
          </table>
        </div>
      </Card>

      <Card title="批量校验（/v1|/api normref/validate）" icon="✅" style={{ marginTop: 12 }}>
        <div style={{ display: 'grid', gridTemplateColumns: '2fr 1fr 1fr auto', gap: 8, marginBottom: 8 }}>
          <Input label="规则列表（逗号/换行）" value={validateRulesText} onChange={setValidateRulesText} />
          <Input label="NormRef版本" value={validateVersion} onChange={setValidateVersion} />
          <Input label="层级（可选）" value={scope} onChange={setScope} />
          <div style={{ alignSelf: 'end' }}><Button onClick={runValidate} disabled={loading}>执行校验</Button></div>
        </div>
        <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 10 }}>
          <div>
            <div style={textLabel}>校验输入数据（JSON）</div>
            <textarea value={validateDataText} onChange={(e) => setValidateDataText(e.target.value)} rows={12} style={textAreaStyle} />
          </div>
          <div>
            <div style={textLabel}>校验输出结果（JSON）</div>
            <textarea value={validateResultText} readOnly rows={12} style={textAreaStyle} />
          </div>
        </div>
      </Card>

      <Card title="规范解析器（NormRef Ingest）" icon="🧩" style={{ marginTop: 12 }}>
        <div style={{ display: 'grid', gridTemplateColumns: '2fr 1fr 1fr', gap: 8, marginBottom: 8 }}>
          <Input label="标准编号" value={ingestStdCode} onChange={setIngestStdCode} />
          <Input label="标题" value={ingestTitle} onChange={setIngestTitle} />
              <Input label="层级" value={ingestLevel} onChange={setIngestLevel} />
        </div>

        <div style={{ display: 'flex', gap: 8, alignItems: 'center', marginBottom: 12 }}>
          <input type="file" accept=".pdf,.txt,.md" onChange={(e) => setIngestFile(e.target.files?.[0] || null)} />
          <Button onClick={runIngestUpload} disabled={loading || !ingestFile}>上传并解析</Button>
          <label style={{ fontSize: 12, color: '#334155', display: 'inline-flex', alignItems: 'center', gap: 6 }}>
            <input type="checkbox" checked={backgroundParse} onChange={(e) => setBackgroundParse(e.target.checked)} />
            后台解析（推荐）
          </label>
          <span style={{ fontSize: 12, color: '#64748B' }}>{ingestFile ? ingestFile.name : '尚未选择文件'}</span>
        </div>

        <div style={{ display: 'grid', gridTemplateColumns: '2fr 1fr auto auto', gap: 8, marginBottom: 8 }}>
          <Input label="任务编号" value={ingestJobId} onChange={setIngestJobId} />
          <div style={{ display: 'flex', flexDirection: 'column', gap: 5 }}>
            <label style={{ fontSize: 12, fontWeight: 700, color: 'var(--gray)', letterSpacing: '0.5px', textTransform: 'uppercase' }}>
              任务状态
            </label>
            <div style={{ minHeight: 38, display: 'flex', alignItems: 'center', padding: '0 8px', border: '1px solid #E2E8F0', borderRadius: 8, background: '#F0F4F8' }}>
              <span style={statusBadgeStyle(ingestStatus)}>{toIngestStatusText(ingestStatus)}</span>
            </div>
          </div>
          <div style={{ alignSelf: 'end' }}><Button onClick={refreshIngestJob} disabled={loading}>刷新任务</Button></div>
          <div style={{ alignSelf: 'end' }}><Button onClick={runPublish} disabled={loading}>发布规则</Button></div>
        </div>

        {ingestJob && isParsing ? (
          <div style={{ marginBottom: 10, padding: 12, border: '1px dashed #CBD5E1', borderRadius: 10, background: '#F8FAFC' }}>
            <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', gap: 10 }}>
              <div style={{ fontSize: 13, color: '#334155', fontWeight: 600 }}>
                正在解析规范，请稍候…
              </div>
              <span style={statusBadgeStyle(ingestStatus)}>{toIngestStatusText(ingestStatus)}</span>
            </div>
            <div style={{ marginTop: 8, fontSize: 12, color: '#64748B' }}>
              任务编号：{ingestJob.jobId}。解析期间你可以继续操作其他页面，系统会自动刷新结果。
            </div>
          </div>
        ) : null}

        {ingestJob && !isParsing ? (
          <div style={{ marginBottom: 10, padding: 10, border: '1px solid #E2E8F0', borderRadius: 8, background: '#F8FAFC' }}>
            <div style={{ fontSize: 13, color: '#334155', marginBottom: 8, fontWeight: 600 }}>解析结果基础信息</div>
            <div style={{ display: 'grid', gridTemplateColumns: 'repeat(4, minmax(0, 1fr))', gap: 8 }}>
              <div style={infoItem}><span style={infoKey}>标准编号</span><span style={infoVal}>{ingestJob.stdCode || '-'}</span></div>
              <div style={infoItem}><span style={infoKey}>标准标题</span><span style={infoVal}>{ingestJob.title || '-'}</span></div>
              <div style={infoItem}><span style={infoKey}>规则层级</span><span style={infoVal}>{toScopeText(ingestJob.level || '-')}</span></div>
              <div style={infoItem}><span style={infoKey}>任务状态</span><span style={{ ...infoVal, fontWeight: 600 }}><span style={statusBadgeStyle(ingestJob.status)}>{toIngestStatusText(ingestJob.status)}</span></span></div>
              <div style={infoItem}><span style={infoKey}>原始文件</span><span style={infoVal}>{ingestJob.fileName || '-'}</span></div>
              <div style={infoItem}><span style={infoKey}>文件指纹</span><span style={infoVal}>{ingestJob.fileHash ? `${ingestJob.fileHash.slice(0, 16)}...` : '-'}</span></div>
              <div style={infoItem}><span style={infoKey}>创建时间</span><span style={infoVal}>{toLocalDateText(ingestJob.createdAt)}</span></div>
              <div style={infoItem}><span style={infoKey}>更新时间</span><span style={infoVal}>{toLocalDateText(ingestJob.updatedAt)}</span></div>
              <div style={infoItem}><span style={infoKey}>完成时间</span><span style={infoVal}>{toLocalDateText(ingestJob.completedAt)}</span></div>
              <div style={infoItem}><span style={infoKey}>识别章节数</span><span style={infoVal}>{ingestJob.sections.length}</span></div>
              <div style={infoItem}><span style={infoKey}>候选规则数</span><span style={infoVal}>{ingestCandidates.length}</span></div>
              <div style={infoItem}><span style={infoKey}>任务ID</span><span style={infoVal}>{ingestJob.jobId || '-'}</span></div>
            </div>
            <div style={{ marginTop: 8 }}>
              <div style={textLabel}>文本预览（截断）</div>
              <textarea readOnly value={ingestJob.sourceTextPreview || ''} rows={4} style={textAreaStyle} />
            </div>
          </div>
        ) : null}

        {!isParsing ? (
          <div style={{ display: 'grid', gridTemplateColumns: 'repeat(4, minmax(0, 1fr))', gap: 8, marginBottom: 8 }}>
            <div style={summaryTile}>总数: {statusSummary.total}</div>
            <div style={summaryTile}>待处理: {statusSummary.pending}</div>
            <div style={summaryTile}>已通过: {statusSummary.approved}</div>
            <div style={summaryTile}>已驳回: {statusSummary.rejected}</div>
          </div>
        ) : null}

        {!!ingestWarnings.length && (
          <div style={{ marginBottom: 8, color: '#B45309', fontSize: 12 }}>
            解析告警: {ingestWarnings.join(' | ')}
          </div>
        )}

        {!isParsing && candidateEditor ? (
          <div style={{ marginBottom: 10, padding: 10, border: '1px solid #CBD5E1', borderRadius: 8, background: '#F8FAFC' }}>
            <div style={{ fontSize: 12, color: '#334155', marginBottom: 8 }}>编辑候选规则: {candidateEditor.candidateId}</div>
            <div style={{ display: 'grid', gridTemplateColumns: '2fr 2fr 1fr 1fr', gap: 8, marginBottom: 8 }}>
              <Input label="规则ID" value={candidateEditor.ruleId} onChange={(v) => setCandidateEditor((s) => (s ? { ...s, ruleId: v } : s))} />
              <Input label="分类" value={candidateEditor.category} onChange={(v) => setCandidateEditor((s) => (s ? { ...s, category: v } : s))} />
              <Input label="字段键" value={candidateEditor.fieldKey} onChange={(v) => setCandidateEditor((s) => (s ? { ...s, fieldKey: v } : s))} />
              <Input label="运算符" value={candidateEditor.operator} onChange={(v) => setCandidateEditor((s) => (s ? { ...s, operator: v } : s))} />
            </div>
            <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr 1fr 1fr', gap: 8 }}>
              <Input label="阈值" value={candidateEditor.thresholdValue} onChange={(v) => setCandidateEditor((s) => (s ? { ...s, thresholdValue: v } : s))} />
              <Input label="单位" value={candidateEditor.unit} onChange={(v) => setCandidateEditor((s) => (s ? { ...s, unit: v } : s))} />
              <Input label="严重级别" value={candidateEditor.severity} onChange={(v) => setCandidateEditor((s) => (s ? { ...s, severity: v } : s))} />
              <Input label="规范出处" value={candidateEditor.normRef} onChange={(v) => setCandidateEditor((s) => (s ? { ...s, normRef: v } : s))} />
            </div>
            <div style={{ display: 'flex', gap: 8, marginTop: 10 }}>
              <Button onClick={saveCandidatePatch} disabled={loading}>保存编辑</Button>
              <Button onClick={() => setCandidateEditor(null)} disabled={loading}>关闭编辑</Button>
            </div>
          </div>
        ) : null}

        {!isParsing ? (
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', gap: 8, marginTop: 8 }}>
          <div style={{ fontSize: 12, color: '#64748B' }}>
            当前筛选：{candidateStatusFilter === 'all' ? '全部' : toCandidateStatusText(candidateStatusFilter)}，共 {filteredCandidates.length} 条
          </div>
          <div style={{ display: 'flex', gap: 6 }}>
            <Button variant={candidateStatusFilter === 'all' ? 'primary' : 'secondary'} onClick={() => setCandidateStatusFilter('all')} disabled={loading}>全部</Button>
            <Button variant={candidateStatusFilter === 'pending' ? 'primary' : 'secondary'} onClick={() => setCandidateStatusFilter('pending')} disabled={loading}>待处理</Button>
            <Button variant={candidateStatusFilter === 'approved' ? 'primary' : 'secondary'} onClick={() => setCandidateStatusFilter('approved')} disabled={loading}>已通过</Button>
            <Button variant={candidateStatusFilter === 'rejected' ? 'primary' : 'secondary'} onClick={() => setCandidateStatusFilter('rejected')} disabled={loading}>已驳回</Button>
          </div>
        </div>
        ) : null}

        {!isParsing ? (
        <div style={{ marginTop: 8, maxHeight: 300, overflowY: 'auto', border: '1px solid #E2E8F0', borderRadius: 8 }}>
          <table style={{ width: '100%', borderCollapse: 'collapse', fontSize: 12 }}>
            <thead>
              <tr style={{ background: '#F8FAFC' }}>
                <th style={th}>规则ID</th>
                <th style={th}>运算符</th>
                <th style={th}>阈值</th>
                <th style={th}>单位</th>
                <th style={th}>严重级别</th>
                <th style={th}>规范出处</th>
                <th style={th}>状态</th>
                <th style={th}>操作</th>
              </tr>
            </thead>
            <tbody>
              {filteredCandidates.map((row) => (
                <tr key={row.candidateId}>
                  <td style={td}>{row.ruleId}</td>
                  <td style={td}>{toOperatorText(row.operator)}</td>
                  <td style={td}>{row.thresholdValue || '-'}</td>
                  <td style={td}>{row.unit || '-'}</td>
                  <td style={td}>{toSeverityText(row.severity)}</td>
                  <td style={td}>{row.normRef || '-'}</td>
                  <td style={td}><span style={statusBadgeStyle(row.status)}>{toCandidateStatusText(row.status)}</span></td>
                  <td style={td}>
                    <div style={{ display: 'flex', gap: 6 }}>
                      <Button onClick={() => setCandidateEditor(toEditor(row))} disabled={loading}>编辑</Button>
                      <Button onClick={() => setCandidateStatus(row.candidateId, 'approved')} disabled={loading || row.status === 'approved'}>通过</Button>
                      <Button onClick={() => setCandidateStatus(row.candidateId, 'rejected')} disabled={loading || row.status === 'rejected'}>驳回</Button>
                    </div>
                  </td>
                </tr>
              ))}
              {!filteredCandidates.length && (
                <tr><td colSpan={8} style={{ ...td, textAlign: 'center', color: '#94A3B8' }}>暂无候选规则</td></tr>
              )}
            </tbody>
          </table>
        </div>
        ) : null}

        <div style={{ display: 'grid', gridTemplateColumns: '1fr auto', gap: 8, marginTop: 10, alignItems: 'center' }}>
          <Input label="发布版本" value={publishVersion} onChange={setPublishVersion} />
          <label style={{ fontSize: 12, color: '#334155', display: 'inline-flex', alignItems: 'center', gap: 6 }}>
            <input type="checkbox" checked={writeToDocs} onChange={(e) => setWriteToDocs(e.target.checked)} />
            写入 docs/normref/rule/imported
          </label>
        </div>

        <div style={{ marginTop: 8 }}>
          <div style={textLabel}>发布结果（JSON）</div>
          <textarea value={publishResultText} readOnly rows={10} style={textAreaStyle} />
        </div>
      </Card>

      <Toast message={toastMsg} />
    </div>
  )
}

const th: React.CSSProperties = {
  border: '1px solid #E2E8F0',
  padding: '8px 6px',
  textAlign: 'left',
  whiteSpace: 'nowrap',
}

const td: React.CSSProperties = {
  border: '1px solid #E2E8F0',
  padding: '6px',
  verticalAlign: 'middle',
  fontFamily: 'JetBrains Mono, monospace',
}

const textAreaStyle: React.CSSProperties = {
  width: '100%',
  border: '1px solid #E2E8F0',
  borderRadius: 8,
  padding: 10,
  fontSize: 12,
  fontFamily: 'JetBrains Mono, monospace',
  resize: 'vertical',
  background: '#F8FAFC',
}

const textLabel: React.CSSProperties = {
  fontSize: 12,
  color: '#64748B',
  marginBottom: 6,
}

const summaryTile: React.CSSProperties = {
  border: '1px solid #E2E8F0',
  borderRadius: 8,
  padding: '8px 10px',
  background: '#F8FAFC',
  fontSize: 12,
  color: '#334155',
}

const badgeBase: React.CSSProperties = {
  display: 'inline-flex',
  alignItems: 'center',
  justifyContent: 'center',
  minHeight: 22,
  padding: '0 8px',
  borderRadius: 999,
  border: '1px solid #E2E8F0',
  fontSize: 12,
  lineHeight: '20px',
  whiteSpace: 'nowrap',
}

const infoItem: React.CSSProperties = {
  border: '1px solid #E2E8F0',
  borderRadius: 8,
  padding: '8px 10px',
  display: 'flex',
  flexDirection: 'column',
  gap: 4,
  background: '#FFFFFF',
}

const infoKey: React.CSSProperties = {
  fontSize: 11,
  color: '#64748B',
}

const infoVal: React.CSSProperties = {
  fontSize: 12,
  color: '#0F172A',
  wordBreak: 'break-all',
}

