import React, { useCallback, useEffect, useState } from 'react'
import InspectionForm from '../components/inspection/InspectionForm'
import InspectionList from '../components/inspection/InspectionList'
import PhotoUpload from '../components/photo/PhotoUpload'
import { Card, EmptyState } from '../components/ui'
import { useProjectStore, useInspectionStore, useAuthStore } from '../store'
import { useInspections } from '../hooks/api/inspections'
import type { Project } from '@qcspec/types'

type Tab = 'form' | 'photos'

export default function InspectionPage() {
  const { currentProject, projects, setCurrentProject } = useProjectStore()
  const { setInspections, stats: localStats } = useInspectionStore()
  const { enterprise } = useAuthStore()
  const { list, stats: getStats } = useInspections()
  const [tab, setTab] = useState<Tab>('form')
  const [apiStats, setApiStats] = useState(localStats)

  const refreshInspectionData = useCallback(async () => {
    if (!currentProject?.id) return
    const [listRes, statsRes] = await Promise.all([
      list(currentProject.id),
      getStats(currentProject.id),
    ])

    const listPayload = listRes as { data?: Parameters<typeof setInspections>[0] } | null
    if (listPayload?.data) setInspections(listPayload.data)

    const statsPayload = statsRes as {
      total?: number
      pass?: number
      warn?: number
      fail?: number
      pass_rate?: number
    } | null
    if (!statsPayload) return

    setApiStats({
      total: Number(statsPayload.total || 0),
      pass: Number(statsPayload.pass || 0),
      warn: Number(statsPayload.warn || 0),
      fail: Number(statsPayload.fail || 0),
      pass_rate: Number(statsPayload.pass_rate || 0),
    })
  }, [currentProject?.id, list, getStats, setInspections])

  useEffect(() => {
    if (!currentProject?.id) return
    refreshInspectionData()
  }, [currentProject?.id, refreshInspectionData])

  useEffect(() => {
    if (!currentProject?.id) return
    setApiStats(localStats)
  }, [currentProject?.id, localStats])

  if (!currentProject) {
    return (
      <Card title="选择项目开始质检" icon="🏗️">
        {!projects.length ? (
          <EmptyState icon="🧾" title="暂无项目" sub="请先注册项目" />
        ) : (
          <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 10 }}>
            {projects.map((p) => (
              <ProjectSelectCard key={p.id} project={p} onSelect={() => setCurrentProject(p)} />
            ))}
          </div>
        )}
      </Card>
    )
  }

  return (
    <div style={{ display: 'grid', gridTemplateColumns: '380px 1fr', gap: 16, alignItems: 'start' }}>
      <div>
        <div style={{ background: '#0F172A', borderRadius: 10, padding: '12px 14px', marginBottom: 12 }}>
          <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
            <div style={{ flex: 1, minWidth: 0 }}>
              <div style={{ fontSize: 12, color: '#475569', marginBottom: 2 }}>当前项目</div>
              <div
                style={{
                  fontSize: 13,
                  color: '#60A5FA',
                  fontWeight: 700,
                  overflow: 'hidden',
                  textOverflow: 'ellipsis',
                  whiteSpace: 'nowrap',
                }}
              >
                {currentProject.name}
              </div>
            </div>
            <button
              onClick={() => setCurrentProject(null)}
              style={{
                background: 'rgba(255,255,255,0.06)',
                border: '1px solid rgba(255,255,255,0.1)',
                borderRadius: 6,
                padding: '5px 10px',
                cursor: 'pointer',
                fontSize: 12,
                color: '#64748B',
                fontFamily: 'var(--sans)',
                marginLeft: 10,
              }}
            >
              切换
            </button>
          </div>
          <div style={{ fontFamily: 'monospace', fontSize: 12, color: '#475569', marginTop: 4 }}>
            {currentProject.v_uri}
          </div>

          <div
            style={{
              display: 'flex',
              gap: 12,
              marginTop: 10,
              paddingTop: 10,
              borderTop: '1px solid rgba(255,255,255,0.06)',
            }}
          >
            {[
              { label: '总计', value: apiStats.total, color: '#94A3B8' },
              { label: '合格', value: apiStats.pass, color: '#34D399' },
              { label: '观察', value: apiStats.warn, color: '#F59E0B' },
              { label: '不合格', value: apiStats.fail, color: '#F87171' },
              {
                label: '合格率',
                value: `${apiStats.pass_rate}%`,
                color: apiStats.pass_rate >= 90 ? '#34D399' : '#F59E0B',
              },
            ].map((s) => (
              <div key={s.label} style={{ textAlign: 'center' }}>
                <div style={{ fontSize: 14, fontWeight: 900, color: s.color, lineHeight: 1 }}>{s.value}</div>
                <div style={{ fontSize: 12, color: '#475569', marginTop: 2 }}>{s.label}</div>
              </div>
            ))}
          </div>
        </div>

        <div
          style={{
            display: 'flex',
            background: '#fff',
            border: '1px solid #E2E8F0',
            borderRadius: 10,
            marginBottom: 12,
            padding: 4,
            gap: 4,
          }}
        >
          {([
            { key: 'form', icon: '📝', label: '质检录入' },
            { key: 'photos', icon: '📷', label: '照片上传' },
          ] as { key: Tab; icon: string; label: string }[]).map((t) => (
            <button
              key={t.key}
              onClick={() => setTab(t.key)}
              style={{
                flex: 1,
                padding: '9px 0',
                borderRadius: 7,
                border: 'none',
                cursor: 'pointer',
                fontFamily: 'var(--sans)',
                fontSize: 13,
                fontWeight: 700,
                background: tab === t.key ? '#1A56DB' : 'transparent',
                color: tab === t.key ? '#fff' : '#6B7280',
                transition: 'all 0.2s',
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'center',
                gap: 6,
              }}
            >
              <span>{t.icon}</span>
              {t.label}
            </button>
          ))}
        </div>

        {tab === 'form' ? (
          <InspectionForm
            projectId={currentProject.id}
            enterpriseId={enterprise?.id || ''}
            onSuccess={refreshInspectionData}
          />
        ) : (
          <PhotoUpload projectId={currentProject.id} enterpriseId={enterprise?.id || ''} location="" />
        )}
      </div>

      <div>
        <InspectionList projectId={currentProject.id} onDataChanged={refreshInspectionData} />
      </div>
    </div>
  )
}

function ProjectSelectCard({ project: p, onSelect }: { project: Project; onSelect: () => void }) {
  const TYPE_ICONS: Record<string, string> = {
    highway: '🛣️',
    road: '🛤️',
    bridge: '🌉',
    tunnel: '🚇',
    municipal: '🏗️',
    urban: '🏙️',
    water: '💧',
    building: '🏢',
  }

  return (
    <div
      onClick={onSelect}
      style={{
        padding: 16,
        background: '#F8FAFF',
        border: '1px solid #E2E8F0',
        borderRadius: 12,
        cursor: 'pointer',
        transition: 'all 0.2s',
      }}
    >
      <div style={{ fontSize: 24, marginBottom: 8 }}>{TYPE_ICONS[p.type] || '🏗️'}</div>
      <div style={{ fontSize: 13, fontWeight: 700, color: '#0F172A', marginBottom: 4 }}>{p.name}</div>
      <div style={{ fontSize: 12, color: '#6B7280', marginBottom: 6 }}>{p.owner_unit}</div>
      <div style={{ fontFamily: 'monospace', fontSize: 12, color: '#94A3B8' }}>{p.v_uri}</div>
    </div>
  )
}

