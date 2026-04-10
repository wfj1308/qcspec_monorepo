/**
 * QCSpec 报告页面
 * apps/web/src/pages/ReportsPage.tsx
 */

import { useCallback, useEffect, useMemo, useState  } from 'react'
import { Card, Button, EmptyState, ProgressBar, VPathDisplay, StatCard } from '../components/ui'
import { useProjectStore, useAuthStore, useUIStore } from '../store'
import { useReports } from '../hooks/api/reports'
import { useProof } from '../hooks/api/proof'
import { useInspections } from '../hooks/api/inspections'
import type { Report } from '@qcspec/types'

const formatDateTimeSeconds = (input?: string | null): string => {
  if (!input) return '-'
  const date = new Date(input)
  if (Number.isNaN(date.getTime())) return '-'
  const pad = (n: number) => String(n).padStart(2, '0')
  return `${date.getFullYear()}/${pad(date.getMonth() + 1)}/${pad(date.getDate())} ${pad(date.getHours())}:${pad(date.getMinutes())}:${pad(date.getSeconds())}`
}

export default function ReportsPage() {
  const { currentProject } = useProjectStore()
  const { enterprise } = useAuthStore()
  const { showToast } = useUIStore()
  const { generate, exportDocpeg, list, getById } = useReports()
  const { verify: verifyProof } = useProof()
  const { list: listInspections } = useInspections()

  const [reports, setReports] = useState<Report[]>([])
  const [allInspections, setAllInspections] = useState<Array<{ result?: string; location?: string; inspected_at?: string }>>([])
  const [reportDetails, setReportDetails] = useState<Record<string, Report>>({})
  const [generating, setGenerating] = useState(false)
  const [selectedReportId, setSelectedReportId] = useState<string | null>(null)
  const [dateFrom, setDateFrom] = useState('')
  const [dateTo, setDateTo] = useState(new Date().toISOString().split('T')[0])
  const [location, setLocation] = useState('')
  const [verifyingProofId, setVerifyingProofId] = useState<string | null>(null)
  const [loadingDetailId, setLoadingDetailId] = useState<string | null>(null)

  const refreshReports = useCallback(async () => {
    if (!currentProject?.id) return
    const res = await list(currentProject.id) as { data?: Report[] } | null
    if (!res?.data) return
    setReports(res.data)
  }, [currentProject?.id, list])

  const refreshInspections = useCallback(async () => {
    if (!currentProject?.id) return
    const pageSize = 200
    const next: Array<{ result?: string; location?: string; inspected_at?: string }> = []
    for (let offset = 0; offset < 2000; offset += pageSize) {
      // eslint-disable-next-line no-await-in-loop
      const payload = await listInspections(currentProject.id, {
        limit: String(pageSize),
        offset: String(offset),
      }) as { data?: Array<{ result?: string; location?: string; inspected_at?: string }> } | null
      const rows = payload?.data || []
      next.push(...rows)
      if (rows.length < pageSize) break
    }
    setAllInspections(next)
  }, [currentProject?.id, listInspections])

  useEffect(() => {
    setSelectedReportId(null)
    setReportDetails({})
    refreshReports()
    refreshInspections()
  }, [currentProject?.id, refreshReports, refreshInspections])

  const panelStats = useMemo(() => {
    const locationFilter = location.trim()
    const from = dateFrom ? new Date(`${dateFrom}T00:00:00`) : null
    const to = dateTo ? new Date(`${dateTo}T23:59:59.999`) : null

    const filtered = allInspections.filter((item) => {
      if (locationFilter && String(item.location || '').trim() !== locationFilter) return false
      if (from || to) {
        const t = item.inspected_at ? new Date(item.inspected_at) : null
        if (!t || Number.isNaN(t.getTime())) return false
        if (from && t < from) return false
        if (to && t > to) return false
      }
      return true
    })

    const total = filtered.length
    const pass = filtered.filter((x) => x.result === 'pass').length
    const warn = filtered.filter((x) => x.result === 'warn').length
    const fail = filtered.filter((x) => x.result === 'fail').length
    const pass_rate = total ? Math.round((pass / total) * 1000) / 10 : 0
    return { total, pass, warn, fail, pass_rate }
  }, [allInspections, dateFrom, dateTo, location])

  const handleGenerate = async () => {
    if (!currentProject || !enterprise) return
    setGenerating(true)
    const beforeCount = reports.length
    const exportRes = await exportDocpeg({
      project_id: currentProject.id,
      enterprise_id: enterprise.id,
      type: 'inspection',
      format: 'docx',
      location: location || undefined,
      date_from: dateFrom || undefined,
      date_to: dateTo || undefined,
    }) as { file_url?: string; report_no?: string } | null

    // Prefer synchronous export: immediate file URL + latest rendered template.
    if (exportRes?.file_url) {
      showToast(`导出成功：${exportRes.report_no || '报告已生成'}`)
      window.open(exportRes.file_url, '_blank', 'noopener,noreferrer')
      await refreshReports()
      await refreshInspections()
      setGenerating(false)
      return
    }

    // Fallback: keep old async generation path when export is unavailable.
    const generateRes = await generate({
      project_id: currentProject.id,
      enterprise_id: enterprise.id,
      location: location || undefined,
      date_from: dateFrom || undefined,
      date_to: dateTo || undefined,
    })
    if (generateRes) {
      showToast('导出暂不可用，已回退为异步生成，正在同步刷新列表...')
      let appeared = false
      // Poll up to ~15s to cover async worker latency.
      for (let i = 0; i < 6; i += 1) {
        // eslint-disable-next-line no-await-in-loop
        await new Promise((resolve) => setTimeout(resolve, 2500))
        // eslint-disable-next-line no-await-in-loop
        const refreshed = await list(currentProject.id) as { data?: Report[] } | null
        if (!refreshed?.data) continue
        setReports(refreshed.data)
        if (refreshed.data.length > beforeCount) {
          appeared = true
          break
        }
      }
      if (!appeared) {
        showToast('报告任务已提交，后台仍在生成，请稍后点“刷新”')
      }
      refreshInspections()
    }
    setGenerating(false)
  }

  const handleSelectReport = async (report: Report) => {
    if (selectedReportId === report.id) {
      setSelectedReportId(null)
      return
    }
    setSelectedReportId(report.id)

    if (reportDetails[report.id]) return
    setLoadingDetailId(report.id)
    const detail = await getById(report.id) as Report | null
    setLoadingDetailId(null)
    if (!detail?.id) return

    setReportDetails((prev) => ({ ...prev, [detail.id]: detail }))
    setReports((prev) => prev.map((item) => (item.id === detail.id ? { ...item, ...detail } : item)))
  }

  const handleVerifyProof = async (proofId: string) => {
    setVerifyingProofId(proofId)
    const res = await verifyProof(proofId) as { valid?: boolean; chain_length?: number } | null
    if (res?.valid) {
      showToast(`Proof 校验通过（链长 ${res.chain_length ?? 0}）`)
    } else {
      showToast('Proof 校验失败或不存在')
    }
    setVerifyingProofId(null)
  }

  const selectedReport = useMemo(() => {
    if (!selectedReportId) return null
    const fromList = reports.find((item) => item.id === selectedReportId) || null
    if (!fromList) return null
    return reportDetails[selectedReportId] ? { ...fromList, ...reportDetails[selectedReportId] } : fromList
  }, [reports, reportDetails, selectedReportId])

  const passRateColor = (rate: number) => (rate >= 90 ? '#059669' : rate >= 70 ? '#D97706' : '#DC2626')

  return (
    <div>
      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(4,1fr)', gap: 12, marginBottom: 16 }}>
        <StatCard icon="📊" value={reports.length} label="历史报告" color="#EFF6FF" />
        <StatCard icon="✅" value={panelStats.pass} label="合格记录" color="#ECFDF5" />
        <StatCard icon="❌" value={panelStats.fail} label="不合格项" color={panelStats.fail ? '#FEF2F2' : '#F8FAFF'} />
        <StatCard icon="📈" value={`${panelStats.pass_rate}%`} label="综合合格率" color={panelStats.pass_rate >= 90 ? '#ECFDF5' : '#FEF2F2'} />
      </div>

      <div style={{ display: 'grid', gridTemplateColumns: '360px 1fr', gap: 16, alignItems: 'start' }}>
        <div>
          <Card title="生成质检报告" icon="📄">
            {!currentProject ? (
              <EmptyState icon="📁" title="请先选择项目" sub="从控制台或项目列表选择项目后再生成报告" />
            ) : (
              <>
                <div style={{ background: '#0F172A', borderRadius: 8, padding: '10px 12px', marginBottom: 14 }}>
                  <div style={{ fontSize: 12, color: '#475569', marginBottom: 2 }}>当前项目</div>
                  <div style={{ fontSize: 13, color: '#60A5FA', fontWeight: 700 }}>{currentProject.name}</div>
                  <div style={{ fontFamily: 'monospace', fontSize: 12, color: '#64748B', marginTop: 2 }}>{currentProject.v_uri}</div>
                </div>

                <div style={{ display: 'flex', flexDirection: 'column', gap: 12, marginBottom: 14 }}>
                  <div>
                    <div style={{ fontSize: 12, fontWeight: 700, color: '#6B7280', marginBottom: 5, letterSpacing: '0.5px', textTransform: 'uppercase' }}>
                      检测桩号（可选）
                    </div>
                    <input
                      value={location}
                      onChange={(e) => setLocation(e.target.value)}
                      placeholder="例如 K50+200，不填则汇总全部桩号"
                      style={{ width: '100%', background: '#F0F4F8', border: '1px solid #E2E8F0', borderRadius: 8, padding: '9px 12px', fontSize: 13, outline: 'none', fontFamily: 'var(--sans)' }}
                    />
                  </div>
                  <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 8 }}>
                    <div>
                      <div style={{ fontSize: 12, fontWeight: 700, color: '#6B7280', marginBottom: 5, letterSpacing: '0.5px', textTransform: 'uppercase' }}>
                        开始日期
                      </div>
                      <input
                        type="date"
                        value={dateFrom}
                        onChange={(e) => setDateFrom(e.target.value)}
                        style={{ width: '100%', background: '#F0F4F8', border: '1px solid #E2E8F0', borderRadius: 8, padding: '9px 12px', fontSize: 13, outline: 'none', fontFamily: 'var(--sans)' }}
                      />
                    </div>
                    <div>
                      <div style={{ fontSize: 12, fontWeight: 700, color: '#6B7280', marginBottom: 5, letterSpacing: '0.5px', textTransform: 'uppercase' }}>
                        结束日期
                      </div>
                      <input
                        type="date"
                        value={dateTo}
                        onChange={(e) => setDateTo(e.target.value)}
                        style={{ width: '100%', background: '#F0F4F8', border: '1px solid #E2E8F0', borderRadius: 8, padding: '9px 12px', fontSize: 13, outline: 'none', fontFamily: 'var(--sans)' }}
                      />
                    </div>
                  </div>
                </div>

                <div style={{ background: '#F8FAFF', border: '1px solid #E2E8F0', borderRadius: 8, padding: 12, marginBottom: 14 }}>
                  <div style={{ fontSize: 12, fontWeight: 700, color: '#0F172A', marginBottom: 8 }}>将写入报告的统计</div>
                  <div style={{ display: 'flex', gap: 16, marginBottom: 8 }}>
                    {[
                      { label: '总计', value: panelStats.total, color: '#1A56DB' },
                      { label: '合格', value: panelStats.pass, color: '#059669' },
                      { label: '观察', value: panelStats.warn, color: '#D97706' },
                      { label: '不合格', value: panelStats.fail, color: '#DC2626' },
                    ].map((s) => (
                      <div key={s.label} style={{ fontSize: 12, color: '#6B7280' }}>
                        <span style={{ color: s.color, fontWeight: 900, fontSize: 16 }}>{s.value}</span> {s.label}
                      </div>
                    ))}
                  </div>
                  <ProgressBar value={panelStats.pass_rate} color={passRateColor(panelStats.pass_rate)} height={6} />
                  <div style={{ fontSize: 12, color: '#6B7280', marginTop: 4 }}>合格率 {panelStats.pass_rate}%</div>
                </div>

                <Button fullWidth icon="🧾" onClick={handleGenerate} disabled={generating || panelStats.total === 0}>
                  {generating ? '生成中...' : '生成质检报告'}
                </Button>
                {panelStats.total === 0 && (
                  <div style={{ fontSize: 12, color: '#9CA3AF', textAlign: 'center', marginTop: 8 }}>请先录入质检数据</div>
                )}
              </>
            )}
          </Card>
        </div>

        <div>
          <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: 12 }}>
            <div style={{ fontSize: 15, fontWeight: 700, color: '#0F172A' }}>
              历史报告 <span style={{ fontSize: 13, color: '#6B7280', fontWeight: 400 }}>共 {reports.length} 份</span>
            </div>
            <button
              onClick={async () => {
                await refreshReports()
                await refreshInspections()
              }}
              style={{ background: 'none', border: 'none', color: '#6B7280', cursor: 'pointer', fontSize: 13 }}
            >
              刷新
            </button>
          </div>

          {!reports.length ? (
            <EmptyState icon="📄" title="暂无报告" sub="点击左侧“生成质检报告”按钮创建第一份报告" />
          ) : (
            <div style={{ display: 'flex', flexDirection: 'column', gap: 10 }}>
              {reports.map((report) => (
                <ReportCard
                  key={report.id}
                  report={reportDetails[report.id] ? { ...report, ...reportDetails[report.id] } : report}
                  selected={selectedReport?.id === report.id}
                  loadingDetail={loadingDetailId === report.id}
                  onClick={() => handleSelectReport(report)}
                  onVerifyProof={handleVerifyProof}
                  verifyingProofId={verifyingProofId}
                />
              ))}
            </div>
          )}
        </div>
      </div>
    </div>
  )
}

function ReportCard({
  report,
  selected,
  loadingDetail,
  onClick,
  onVerifyProof,
  verifyingProofId,
}: {
  report: Report
  selected: boolean
  loadingDetail: boolean
  onClick: () => void
  onVerifyProof: (proofId: string) => void
  verifyingProofId: string | null
}) {
  const passRateColor = report.pass_rate != null
    ? (report.pass_rate >= 90 ? '#059669' : report.pass_rate >= 70 ? '#D97706' : '#DC2626')
    : '#6B7280'
  const generatedAt = formatDateTimeSeconds(report.generated_at)

  return (
    <div
      onClick={onClick}
      style={{
        background: '#fff',
        border: `1px solid ${selected ? '#1A56DB' : '#E2E8F0'}`,
        borderRadius: 12,
        padding: 16,
        cursor: 'pointer',
        transition: 'all 0.2s',
        boxShadow: selected ? '0 4px 16px rgba(26,86,219,0.1)' : 'none',
      }}
    >
      <div style={{ display: 'flex', alignItems: 'flex-start', justifyContent: 'space-between', marginBottom: 10 }}>
        <div>
          <div style={{ fontSize: 14, fontWeight: 700, color: '#0F172A', marginBottom: 3 }}>{report.report_no}</div>
          <div style={{ fontSize: 12, color: '#6B7280', display: 'flex', gap: 10 }}>
            {report.location && <span>📍 {report.location}</span>}
            <span>🕓 {generatedAt}</span>
          </div>
        </div>
        <div style={{ textAlign: 'right' }}>
          <div style={{ fontSize: 24, fontWeight: 900, color: passRateColor, fontFamily: 'monospace', lineHeight: 1 }}>
            {report.pass_rate ?? '-'}%
          </div>
          <div style={{ fontSize: 12, color: '#9CA3AF', marginTop: 2 }}>合格率</div>
        </div>
      </div>

      {report.pass_rate != null && <ProgressBar value={report.pass_rate} color={passRateColor} height={5} />}

      <div style={{ display: 'flex', gap: 16, marginTop: 8, marginBottom: 8 }}>
        {[
          { label: '总计', value: report.total_count, color: '#1A56DB' },
          { label: '合格', value: report.pass_count, color: '#059669' },
          { label: '观察', value: report.warn_count, color: '#D97706' },
          { label: '不合格', value: report.fail_count, color: '#DC2626' },
        ].map((s) => (
          <div key={s.label} style={{ fontSize: 12, color: '#6B7280' }}>
            <span style={{ color: s.color, fontWeight: 700 }}>{s.value}</span> {s.label}
          </div>
        ))}
      </div>

      {selected && (
        <div style={{ borderTop: '1px solid #F0F4F8', paddingTop: 12, marginTop: 4 }}>
          {loadingDetail && <div style={{ fontSize: 12, color: '#64748B', marginBottom: 8 }}>加载报告详情中...</div>}

          {report.conclusion && (
            <div
              style={{
                background: report.fail_count === 0 ? '#ECFDF5' : '#FEF2F2',
                borderRadius: 6,
                padding: '8px 12px',
                marginBottom: 10,
                fontSize: 12,
                color: report.fail_count === 0 ? '#059669' : '#DC2626',
                fontWeight: 700,
              }}
            >
              {report.conclusion}
            </div>
          )}

          {report.fail_items && report.fail_items !== '无' && (
            <div style={{ fontSize: 12, color: '#DC2626', marginBottom: 8 }}>不合格项：{report.fail_items}</div>
          )}

          {report.v_uri && <VPathDisplay uri={report.v_uri} proofId={report.proof_id} />}

          <div style={{ display: 'flex', gap: 8, marginTop: 10 }}>
            {report.file_url ? (
              <a
                href={report.file_url}
                download={`${report.report_no}.docx`}
                style={{
                  padding: '8px 16px',
                  background: '#1A56DB',
                  color: '#fff',
                  borderRadius: 8,
                  fontSize: 13,
                  fontWeight: 700,
                  textDecoration: 'none',
                  display: 'inline-flex',
                  alignItems: 'center',
                  gap: 6,
                }}
              >
                ⬇ 下载 Word 报告
              </a>
            ) : (
              <div style={{ padding: '8px 16px', background: '#F0F4F8', color: '#9CA3AF', borderRadius: 8, fontSize: 12 }}>
                报告生成中...
              </div>
            )}
            {report.proof_id && (
              <button
                onClick={(e) => {
                  e.stopPropagation()
                  onVerifyProof(report.proof_id as string)
                }}
                disabled={verifyingProofId === report.proof_id}
                style={{
                  padding: '8px 16px',
                  background: '#FFFBEB',
                  color: '#D97706',
                  border: '1px solid #FDE68A',
                  borderRadius: 8,
                  fontSize: 12,
                  cursor: verifyingProofId === report.proof_id ? 'not-allowed' : 'pointer',
                  fontFamily: 'var(--sans)',
                  fontWeight: 700,
                  opacity: verifyingProofId === report.proof_id ? 0.7 : 1,
                }}
              >
                {verifyingProofId === report.proof_id ? '校验中...' : '🔎 验证 Proof'}
              </button>
            )}
          </div>
        </div>
      )}
    </div>
  )
}

