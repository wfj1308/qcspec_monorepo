import React, { useEffect, useState } from 'react'
import { useProjectStore, useInspectionStore, usePhotoStore, useAuthStore, useUIStore } from '../store'
import { useProjects } from '../hooks/api/projects'
import { useInspections } from '../hooks/api/inspections'
import { getAllowedNavKeysByRole } from '../app/appShellShared'

interface ActivityItem {
  dot: string
  text: string
  time: string
}

const formatDateTime = (input?: string) => {
  if (!input) return '刚刚'
  const d = new Date(input)
  if (Number.isNaN(d.getTime())) return '刚刚'
  const pad = (n: number) => String(n).padStart(2, '0')
  return `${d.getFullYear()}年${pad(d.getMonth() + 1)}月${pad(d.getDate())}日 ${pad(d.getHours())}:${pad(d.getMinutes())}:${pad(d.getSeconds())}`
}

const FALLBACK_ACTIVITY_ITEMS: ActivityItem[] = [
  { dot: '#059669', text: '王质检在京港高速大修录入了路面平整度记录', time: '10 分钟前' },
  { dot: '#1A56DB', text: '项目中心同步了新项目：沁河特大桥定检', time: '2 小时前' },
  { dot: '#D97706', text: '系统生成了 3 月份质检汇总报告', time: '今天 09:00' },
  { dot: '#DC2626', text: 'K49+200 裂缝宽度超标，请尽快复检', time: '昨天 14:15' },
]
const DEMO_ENTERPRISE_ID = '11111111-1111-4111-8111-111111111111'

export default function Dashboard() {
  const { enterprise, token, user } = useAuthStore()
  const { currentProject, projects, setProjects, setCurrentProject } = useProjectStore()
  const { stats } = useInspectionStore()
  const { photos } = usePhotoStore()
  const { setActiveTab, showToast } = useUIStore()
  const { list: listProjects, listActivity, exportCsv } = useProjects()
  const { list: listInspections } = useInspections()
  const isDemoSession = enterprise?.id === DEMO_ENTERPRISE_ID || String(token || '').startsWith('demo-token-')

  const [projStats, setProjStats] = useState<Record<string, { passRate: number; total: number }>>({})
  const [activityItems, setActivityItems] = useState<ActivityItem[]>(FALLBACK_ACTIVITY_ITEMS)

  useEffect(() => {
    if (!enterprise?.id || isDemoSession) return
    listProjects(enterprise.id).then((res: unknown) => {
      const r = res as { data?: Parameters<typeof setProjects>[0] } | null
      if (r?.data) setProjects(r.data)
    })
  }, [enterprise?.id, isDemoSession, listProjects, setProjects])

  useEffect(() => {
    if (!enterprise?.id || isDemoSession) return
    listActivity(enterprise.id, 12).then((res: unknown) => {
      const r = res as { data?: Array<{ dot?: string; text?: string; created_at?: string }> } | null
      if (!r?.data?.length) return
      setActivityItems(
        r.data.map((item) => ({
          dot: item.dot || '#64748B',
          text: item.text || '系统更新',
          time: formatDateTime(item.created_at),
        }))
      )
    })
  }, [enterprise?.id, isDemoSession, listActivity])

  useEffect(() => {
    if (isDemoSession) {
      setProjStats({})
      return
    }
    let cancelled = false
    const load = async () => {
      const entries = await Promise.all(
        projects.map(async (p) => {
          const res = await listInspections(p.id, {}) as { data?: { result: string }[] } | null
          if (!res?.data) return [p.id, { total: 0, passRate: 0 }] as const
          const total = res.data.length
          const passed = res.data.filter((i) => i.result === 'pass').length
          const passRate = total ? Math.round((passed / total) * 1000) / 10 : 0
          return [p.id, { total, passRate }] as const
        })
      )
      if (!cancelled) setProjStats(Object.fromEntries(entries))
    }
    if (projects.length) load()
    return () => { cancelled = true }
  }, [projects, isDemoSession, listInspections])

  const totalProjects = projects.length
  const activeProjects = projects.filter((p) => p.status === 'active').length
  const totalPhotos = photos.length
  const quickAllowedTabs = getAllowedNavKeysByRole(user?.dto_role)

  const canQuickProjects = quickAllowedTabs.includes('projects')
  const canQuickInspection = quickAllowedTabs.includes('inspection')
  const canQuickReports = quickAllowedTabs.includes('reports')
  const canQuickProof = quickAllowedTabs.includes('proof')
  const canQuickTeam = quickAllowedTabs.includes('team')

  const ensureProjectSelected = () => {
    const selected = currentProject || projects[0]
    if (selected) {
      setCurrentProject(selected)
      return true
    }
    showToast('请先在上游系统创建并同步项目')
    setActiveTab('projects')
    return false
  }

  const handleQuickProjects = () => {
    if (!canQuickProjects) {
      showToast('当前角色无项目访问权限')
      return
    }
    setActiveTab('projects')
  }

  const handleQuickInspection = () => {
    if (!canQuickInspection) {
      showToast('当前角色无质检录入权限')
      return
    }
    if (!ensureProjectSelected()) return
    setActiveTab('inspection')
  }

  const handleQuickReports = () => {
    if (!canQuickReports) {
      showToast('当前角色无报告生成功能权限')
      return
    }
    if (!ensureProjectSelected()) return
    setActiveTab('reports')
  }

  const handleQuickProof = () => {
    if (!canQuickProof) {
      showToast('当前角色无 Proof 工作台权限')
      return
    }
    if (!ensureProjectSelected()) return
    setActiveTab('proof')
  }

  const handleQuickTeam = () => {
    if (!canQuickTeam) {
      showToast('当前角色无团队管理权限')
      return
    }
    setActiveTab('team')
  }

  const downloadProjectCsv = async () => {
    if (!enterprise?.id) {
      showToast('请先登录企业账号')
      return
    }
    const blob = await exportCsv(enterprise.id)
    if (!blob) return
    const url = URL.createObjectURL(blob)
    const a = document.createElement('a')
    a.href = url
    a.download = `projects-${new Date().toISOString().slice(0, 10)}.csv`
    document.body.appendChild(a)
    a.click()
    a.remove()
    URL.revokeObjectURL(url)
    showToast('项目清单已导出')
  }

  return (
    <div>
      <div className="dash-stats">
        <div className="stat-card">
          <div className="stat-icon si-blue">🏗️</div>
          <div>
            <div className="stat-val">{activeProjects}</div>
            <div className="stat-label">在建项目</div>
            <div className="stat-trend trend-up">共 {totalProjects} 个项目</div>
          </div>
        </div>
        <div className="stat-card">
          <div className="stat-icon si-green">✅</div>
          <div>
            <div className="stat-val">{stats.total}</div>
            <div className="stat-label">质检记录</div>
            <div className="stat-trend trend-up">合格率 {stats.pass_rate}%</div>
          </div>
        </div>
        <div className="stat-card">
          <div className="stat-icon si-gold">📷</div>
          <div>
            <div className="stat-val">{totalPhotos}</div>
            <div className="stat-label">现场照片</div>
            <div className="stat-trend trend-up">已接入 Proof</div>
          </div>
        </div>
        <div className="stat-card">
          <div className="stat-icon si-purple">👥</div>
          <div>
            <div className="stat-val">{Object.keys(projStats).length}</div>
            <div className="stat-label">活跃项目看板</div>
            <div className="stat-trend">{stats.pass_rate >= 90 ? '状态健康' : '需持续跟踪'}</div>
          </div>
        </div>
      </div>

      <div className="dash-grid">
        <div style={{ background: 'var(--white)', border: '1px solid var(--border)', borderRadius: 14, padding: 20 }}>
          <div style={{ fontSize: 15, fontWeight: 700, color: 'var(--dark)', marginBottom: 16, display: 'flex', alignItems: 'center', gap: 8 }}>
            <span>📌</span> 最新动态
          </div>
          <div>
            {activityItems.map((item, idx) => (
              <div className="activity-item" key={`${item.text}-${idx}`}>
                <div className="activity-dot" style={{ background: item.dot }} />
                <div>
                  <div className="activity-text">{item.text}</div>
                  <div className="activity-time">{item.time}</div>
                </div>
              </div>
            ))}
          </div>
        </div>

        <div>
          <div style={{ background: 'var(--white)', border: '1px solid var(--border)', borderRadius: 14, padding: 20, marginBottom: 14 }}>
            <div style={{ fontSize: 15, fontWeight: 700, color: 'var(--dark)', marginBottom: 14 }}>快捷操作</div>
            <div className="quick-actions">
              <button className="quick-btn" onClick={handleQuickProjects} disabled={!canQuickProjects} title={canQuickProjects ? '进入项目工作台' : '当前角色无项目访问权限'}>
                <div className="quick-btn-icon">🏗️</div>项目工作台
              </button>
              <button className="quick-btn" onClick={handleQuickInspection} disabled={!canQuickInspection} title={canQuickInspection ? '开始质检' : '当前角色无质检录入权限'}>
                <div className="quick-btn-icon">📷</div>开始质检
              </button>
              <button className="quick-btn" onClick={handleQuickReports} disabled={!canQuickReports} title={canQuickReports ? '生成报告' : '当前角色无报告生成功能权限'}>
                <div className="quick-btn-icon">🧾</div>生成报告
              </button>
              <button className="quick-btn" onClick={handleQuickProof} disabled={!canQuickProof} title={canQuickProof ? '进入 Proof 工作台' : '当前角色无 Proof 工作台权限'}>
                <div className="quick-btn-icon">🔒</div>Proof 工作台
              </button>
              <button className="quick-btn" onClick={handleQuickTeam} disabled={!canQuickTeam} title={canQuickTeam ? '团队成员管理' : '当前角色无团队管理权限'}>
                <div className="quick-btn-icon">👥</div>邀请成员
              </button>
              <button className="quick-btn" onClick={downloadProjectCsv}>
                <div className="quick-btn-icon">📊</div>导出清单
              </button>
            </div>
          </div>

          <div style={{ background: 'var(--dark)', borderRadius: 14, padding: 16 }}>
            <div style={{ fontSize: 12, color: '#475569', marginBottom: 10, fontWeight: 700, letterSpacing: '1px', textTransform: 'uppercase' }}>
              v:// 节点状态
            </div>
            <div style={{ fontFamily: 'var(--mono)', fontSize: 12, lineHeight: 2.2 }}>
              <div style={{ color: '#34D399' }}>● {enterprise?.v_uri || 'v://cn.enterprise/'} <span style={{ color: '#475569' }}>激活</span></div>
              {projects.slice(0, 3).map((p) => (
                <div key={p.id} style={{ color: '#60A5FA', paddingLeft: 16 }}>
                  ├ {p.type}/{p.name.slice(0, 12)}... <span style={{ color: p.status === 'active' ? '#34D399' : '#F59E0B' }}>●</span>
                </div>
              ))}
            </div>
            <div style={{ marginTop: 12, paddingTop: 12, borderTop: '1px solid rgba(255,255,255,0.05)' }}>
              <div style={{ fontSize: 12, color: '#475569' }}>Proof 存证</div>
              <div style={{ fontFamily: 'var(--mono)', fontSize: 12, color: '#64748B', marginTop: 4 }}>
                后续版本自动接入 GitPeg v:// Proof 链
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  )
}

