import React, { useCallback, useEffect, useMemo, useState } from 'react'
import { Button, Card, EmptyState, ProgressBar, StatCard, VPathDisplay } from '../components/ui'
import { useAuthStore, useProjectStore, useUIStore } from '../store'
import { type LogPegDailyLog, useLogPegApi } from '../hooks/api/logpeg'

function todayIso(): string {
  const d = new Date()
  const p = (n: number) => String(n).padStart(2, '0')
  return `${d.getFullYear()}-${p(d.getMonth() + 1)}-${p(d.getDate())}`
}

function weekStartIso(dateText: string): string {
  const d = new Date(`${dateText}T00:00:00`)
  const day = d.getDay() || 7
  d.setDate(d.getDate() - day + 1)
  const p = (n: number) => String(n).padStart(2, '0')
  return `${d.getFullYear()}-${p(d.getMonth() + 1)}-${p(d.getDate())}`
}

function monthToken(dateText: string): string {
  return dateText.slice(0, 7)
}

function fmtMoney(value: number): string {
  return `¥${Number(value || 0).toLocaleString('zh-CN', { minimumFractionDigits: 2, maximumFractionDigits: 2 })}`
}

function fmtClock(ts?: string): string {
  if (!ts) return '--:--'
  const d = new Date(ts)
  if (Number.isNaN(d.getTime())) return '--:--'
  return `${String(d.getHours()).padStart(2, '0')}:${String(d.getMinutes()).padStart(2, '0')}`
}

export default function LogPegPage() {
  const { currentProject } = useProjectStore()
  const { user } = useAuthStore()
  const { showToast } = useUIStore()
  const { daily, weekly, monthly, sign, exportDaily, loading } = useLogPegApi()

  const [date, setDate] = useState(todayIso)
  const [weather, setWeather] = useState('')
  const [temperatureRange, setTemperatureRange] = useState('')
  const [windLevel, setWindLevel] = useState('')
  const [language, setLanguage] = useState<'zh' | 'en'>('zh')
  const [dailyLog, setDailyLog] = useState<LogPegDailyLog | null>(null)
  const [weeklyCost, setWeeklyCost] = useState(0)
  const [monthlyCost, setMonthlyCost] = useState(0)
  const [signing, setSigning] = useState(false)

  const projectId = currentProject?.id || ''
  const executorUri = String(user?.v_uri || '').trim()
  const weekStart = useMemo(() => weekStartIso(date), [date])
  const month = useMemo(() => monthToken(date), [date])

  const refreshDaily = useCallback(async () => {
    if (!projectId) {
      setDailyLog(null)
      return
    }
    const res = await daily({
      project_id: projectId,
      date,
      weather,
      temperature_range: temperatureRange,
      wind_level: windLevel,
      language,
    })
    if (!res?.log) return
    setDailyLog(res.log)
    if (!weather && res.log.weather) setWeather(res.log.weather)
    if (!temperatureRange && res.log.temperature_range) setTemperatureRange(res.log.temperature_range)
    if (!windLevel && res.log.wind_level) setWindLevel(res.log.wind_level)
  }, [daily, projectId, date, weather, temperatureRange, windLevel, language])

  const refreshSummary = useCallback(async () => {
    if (!projectId) return
    const [w, m] = await Promise.all([
      weekly({ project_id: projectId, week_start: weekStart, language }),
      monthly({ project_id: projectId, month, language }),
    ])
    setWeeklyCost(Number(w?.weekly_summary?.total_cost || 0))
    setMonthlyCost(Number(m?.monthly_summary?.total_cost || 0))
  }, [weekly, monthly, projectId, weekStart, month, language])

  useEffect(() => {
    void refreshDaily()
    void refreshSummary()
  }, [refreshDaily, refreshSummary])

  const handleSign = async () => {
    if (!projectId) return showToast('请先选择项目')
    setSigning(true)
    const res = await sign({
      project_id: projectId,
      date,
      executor_uri: executorUri,
      signed_by: String(user?.name || ''),
      weather,
      temperature_range: temperatureRange,
      wind_level: windLevel,
      language,
    })
    setSigning(false)
    if (!res?.log) return showToast('签名失败')
    setDailyLog(res.log)
    showToast('日志已签名并锁定')
  }

  const handleExport = async (format: 'pdf' | 'word' | 'json') => {
    if (!projectId) return showToast('请先选择项目')
    const file = await exportDaily({ project_id: projectId, date, format, language })
    if (!file) return showToast('导出失败')
    const href = URL.createObjectURL(file.blob)
    const a = document.createElement('a')
    a.href = href
    a.download = file.filename
    document.body.appendChild(a)
    a.click()
    a.remove()
    URL.revokeObjectURL(href)
  }

  const passRate = dailyLog?.quality_summary?.pass_rate || 0

  return (
    <div>
      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(4,1fr)', gap: 12, marginBottom: 16 }}>
        <StatCard icon="📌" value={dailyLog?.progress_summary?.completed_steps || 0} label="今日完成工序" color="#ECFDF5" />
        <StatCard icon="🧾" value={dailyLog?.progress_summary?.generated_proofs || 0} label="生成 Proof" color="#EFF6FF" />
        <StatCard icon="⏳" value={dailyLog?.progress_summary?.pending_steps || 0} label="待处理工序" color="#FFFBEB" />
        <StatCard icon="💰" value={fmtMoney(dailyLog?.cost_summary?.daily_total || 0)} label="今日造价" color="#FEF2F2" />
      </div>

      <div style={{ display: 'grid', gridTemplateColumns: '360px 1fr', gap: 16 }}>
        <Card title="日志设置" icon="🗓️">
          {!currentProject ? (
            <EmptyState icon="📁" title="请先选择项目" />
          ) : (
            <>
              <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 8, marginBottom: 8 }}>
                <input type="date" value={date} onChange={(e) => setDate(e.target.value)} />
                <select value={language} onChange={(e) => setLanguage(e.target.value === 'en' ? 'en' : 'zh')}>
                  <option value="zh">中文</option>
                  <option value="en">English</option>
                </select>
              </div>
              <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 8, marginBottom: 8 }}>
                <input value={weather} onChange={(e) => setWeather(e.target.value)} placeholder="天气" />
                <input value={temperatureRange} onChange={(e) => setTemperatureRange(e.target.value)} placeholder="温度范围" />
              </div>
              <input value={windLevel} onChange={(e) => setWindLevel(e.target.value)} placeholder="风力（例如3级）" style={{ width: '100%', marginBottom: 8 }} />

              <div style={{ background: '#0F172A', borderRadius: 8, padding: 10, marginBottom: 10 }}>
                <div style={{ color: '#64748B', fontSize: 12 }}>当前项目</div>
                <div style={{ color: '#60A5FA', fontWeight: 700 }}>{currentProject.name}</div>
                <div style={{ color: '#94A3B8', fontSize: 12 }}>{currentProject.v_uri}</div>
              </div>

              <div style={{ display: 'flex', gap: 8, flexWrap: 'wrap' }}>
                <Button onClick={() => void refreshDaily()} disabled={loading}>刷新</Button>
                <Button onClick={handleSign} disabled={loading || signing || !!dailyLog?.locked}>{dailyLog?.locked ? '已签名' : signing ? '签名中…' : '签名确认'}</Button>
                <Button variant="secondary" onClick={() => void handleExport('pdf')}>导出PDF</Button>
                <Button variant="secondary" onClick={() => void handleExport('word')}>导出Word</Button>
                <Button variant="secondary" onClick={() => void handleExport('json')}>导出JSON</Button>
              </div>
            </>
          )}
        </Card>

        {!dailyLog ? (
          <Card><EmptyState icon="📄" title="暂无日志数据" /></Card>
        ) : (
          <div style={{ display: 'flex', flexDirection: 'column', gap: 12 }}>
            <Card title={`${dailyLog.log_date} 施工日志`} icon="📒">
              <div>{dailyLog.project_name} | {dailyLog.contract_section || '-'} | 天气:{dailyLog.weather || '-'} 温度:{dailyLog.temperature_range || '-'} 风力:{dailyLog.wind_level || '-'}</div>
              <VPathDisplay uri={dailyLog.v_uri} proofId={dailyLog.sign_proof || ''} />
              <div style={{ fontSize: 12, color: '#6B7280' }}>hash: <span style={{ fontFamily: 'monospace' }}>{dailyLog.data_hash}</span></div>
              {dailyLog.signed_by ? <div style={{ marginTop: 6, color: '#059669' }}>签名：{dailyLog.signed_by} {fmtClock(dailyLog.signed_at || '')}</div> : null}
            </Card>

            <Card title="今日施工记录" icon="🧱">
              {!dailyLog.activities.length ? <EmptyState icon="📝" title="今日暂无记录" /> : (
                <div style={{ display: 'flex', flexDirection: 'column', gap: 8 }}>
                  {dailyLog.activities.map((a, i) => (
                    <div key={`${a.trip_id}-${i}`} style={{ border: '1px solid #E2E8F0', borderRadius: 8, padding: 10 }}>
                      <div style={{ display: 'flex', justifyContent: 'space-between' }}>
                        <div style={{ fontWeight: 700 }}>{fmtClock(a.time)} {a.pile_id} {a.process_step}</div>
                        <div style={{ color: a.gate_result === '不合格' || a.gate_result === 'Fail' ? '#DC2626' : '#059669' }}>{a.gate_result || '-'}</div>
                      </div>
                      <div style={{ fontSize: 12, color: '#64748B' }}>{a.primary_executor || '-'} | {a.executor_org || '-'} | {a.form_code || '-'}</div>
                      <div style={{ fontSize: 12, color: '#64748B' }}>{a.equipment_used.join('、') || '无设备记录'} | {a.proof_id || '-'}</div>
                    </div>
                  ))}
                </div>
              )}
            </Card>

            <Card title="今日汇总" icon="📊">
              <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 12 }}>
                <div>
                  <div style={{ fontWeight: 700, marginBottom: 6 }}>材料</div>
                  {dailyLog.material_summary.map((m) => <div key={`${m.code}-${m.unit}`} style={{ fontSize: 13 }}>{m.name} {m.total_qty}{m.unit} {fmtMoney(m.total_cost)}</div>)}
                </div>
                <div>
                  <div style={{ fontWeight: 700, marginBottom: 6 }}>设备</div>
                  {dailyLog.equipment_summary.map((e) => <div key={e.name} style={{ fontSize: 13 }}>{e.name} {e.shifts}台班 {fmtMoney(e.cost)}</div>)}
                </div>
              </div>
              <div style={{ marginTop: 10 }}>
                <div style={{ fontSize: 13 }}>完工构件：{dailyLog.progress_summary.components_completed} | 在建构件：{dailyLog.progress_summary.components_in_progress} | 质检合格率：{passRate}%</div>
                <ProgressBar value={Math.min(Math.max(passRate, 0), 100)} color="#1A56DB" />
              </div>
              <div style={{ marginTop: 10, fontWeight: 700 }}>
                人工费 {fmtMoney(dailyLog.cost_summary.daily_labor)} | 机械费 {fmtMoney(dailyLog.cost_summary.daily_equipment)} | 材料费 {fmtMoney(dailyLog.cost_summary.daily_material)} | 合计 {fmtMoney(dailyLog.cost_summary.daily_total)}
              </div>
              <div style={{ fontSize: 12, color: '#64748B', marginTop: 4 }}>周累计 {fmtMoney(weeklyCost)} | 月累计 {fmtMoney(monthlyCost)}</div>
            </Card>

            <Card title="异常记录" icon="⚠️">
              {!dailyLog.anomalies.length ? <div>暂无异常 ✅</div> : dailyLog.anomalies.map((x, i) => (
                <div key={`${x.type}-${i}`} style={{ padding: '6px 0', borderBottom: '1px dashed #E5E7EB' }}>
                  <div style={{ fontWeight: 700 }}>{x.type} ({x.severity})</div>
                  <div style={{ fontSize: 13 }}>{x.description}</div>
                  <div style={{ fontSize: 12, color: '#64748B' }}>建议：{x.action_required}</div>
                </div>
              ))}
            </Card>
          </div>
        )}
      </div>
    </div>
  )
}
