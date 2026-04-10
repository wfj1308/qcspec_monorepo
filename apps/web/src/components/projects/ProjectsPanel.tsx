import { useEffect, useMemo, useState } from 'react'
import { Card } from '../ui'

interface ProjectTypeOption {
  value: string
  label: string
}

type ProjectItem = any

interface ProjectMetaItem {
  segType: 'km' | 'contract' | 'structure' | string
  segStart?: string
  segEnd?: string
  contractSegs: Array<unknown>
  structures: Array<unknown>
  permTemplate: string
  memberCount: number
  inspectionTypes: Array<unknown>
}

interface ProjectsPanelProps {
  searchText: string
  statusFilter: string
  typeFilter: string
  projectTypeOptions: ProjectTypeOption[]
  filteredProjects: ProjectItem[]
  projectMeta: Record<string, ProjectMetaItem | undefined>
  typeIcon: Record<string, string>
  typeLabel: Record<string, string>
  onSearchTextChange: (value: string) => void
  onStatusFilterChange: (value: string) => void
  onTypeFilterChange: (value: string) => void
  onEnterInspection: (project: any) => void
  onEnterProof: (project: any) => void
  onEditProject: (projectId: string) => void
  onOpenProjectDetail: (projectId: string) => void
  onDeleteProject: (projectId: string, projectName: string) => void
}

type WorkbenchTab = 'overview' | 'components' | 'process'

export default function ProjectsPanel({
  searchText,
  statusFilter,
  typeFilter,
  projectTypeOptions,
  filteredProjects,
  projectMeta,
  typeIcon,
  typeLabel,
  onSearchTextChange,
  onStatusFilterChange,
  onTypeFilterChange,
  onEnterInspection,
  onEnterProof,
  onEditProject,
  onOpenProjectDetail,
  onDeleteProject,
}: ProjectsPanelProps) {
  const [activeProjectId, setActiveProjectId] = useState<string>('')
  const [workbenchTab, setWorkbenchTab] = useState<WorkbenchTab>('overview')

  useEffect(() => {
    if (!filteredProjects.length) {
      setActiveProjectId('')
      return
    }
    const exists = filteredProjects.some((project) => project.id === activeProjectId)
    if (!exists) {
      setActiveProjectId(filteredProjects[0]?.id || '')
    }
  }, [activeProjectId, filteredProjects])

  useEffect(() => {
    setWorkbenchTab('overview')
  }, [activeProjectId])

  const activeProject = useMemo(
    () => filteredProjects.find((project) => project.id === activeProjectId) || filteredProjects[0] || null,
    [activeProjectId, filteredProjects],
  )

  const activeMeta = activeProject ? projectMeta[activeProject.id] : undefined
  const activeStatus = String(activeProject?.status || '')
  const activeStatusClass = activeStatus === 'active' ? 'pill-active' : activeStatus === 'pending' ? 'pill-pending' : 'pill-closed'
  const activeStatusLabel = activeStatus === 'active' ? '进行中' : activeStatus === 'pending' ? '待开始' : '已完成'

  const activeSegLabel = !activeMeta
    ? '默认'
    : activeMeta.segType === 'km'
      ? `桩号 ${activeMeta.segStart || '-'} ~ ${activeMeta.segEnd || '-'}`
      : activeMeta.segType === 'contract'
        ? `合同段 ${activeMeta.contractSegs.length} 个`
        : `结构物 ${activeMeta.structures.length} 个`

  const activePermLabel = activeMeta
    ? `${activeMeta.permTemplate} / ${activeMeta.memberCount}人 / 检测 ${(activeMeta.inspectionTypes || []).length}类`
    : '-'

  const componentRows = useMemo(() => {
    if (!activeMeta) return []
    const structureRows = (activeMeta.structures || []).map((row, idx) => {
      const obj = (row && typeof row === 'object' && !Array.isArray(row)) ? (row as Record<string, unknown>) : {}
      return {
        code: String(obj.code || `STR-${idx + 1}`),
        name: String(obj.name || '未命名构件'),
        kind: String(obj.kind || 'structure'),
      }
    })
    const contractRows = (activeMeta.contractSegs || []).map((row, idx) => {
      const obj = (row && typeof row === 'object' && !Array.isArray(row)) ? (row as Record<string, unknown>) : {}
      return {
        code: String(obj.range || `SEG-${idx + 1}`),
        name: String(obj.name || '合同段'),
        kind: 'contract-segment',
      }
    })
    return [...structureRows, ...contractRows]
  }, [activeMeta])

  const processSteps = useMemo(() => {
    const recordCount = Number(activeProject?.record_count || 0)
    const proofCount = Number(activeProject?.proof_count || 0)
    const hasComponents = componentRows.length > 0
    const initialized = activeStatus !== 'pending'
    const qualityDone = recordCount > 0
    const settlementProgress = proofCount > 0 || activeStatus === 'closed'

    return [
      { name: '项目初始化', status: initialized ? '已完成' : '待处理' },
      { name: '构件绑定', status: hasComponents ? '已完成' : '待处理' },
      { name: '质量验收', status: qualityDone ? '进行中' : '待处理' },
      { name: '计量与结算', status: settlementProgress ? '进行中' : '待处理' },
      { name: '审计归档', status: activeStatus === 'closed' ? '已完成' : '待处理' },
    ]
  }, [activeProject?.proof_count, activeProject?.record_count, activeStatus, componentRows.length])

  const nextActionHint = useMemo(() => {
    const recordCount = Number(activeProject?.record_count || 0)
    if (!activeProject) return '-'
    if (activeStatus === 'pending') return '先补充构件信息，再发起首件质检。'
    if (componentRows.length === 0) return '先在项目详情中补充构件/合同段，再推进工序。'
    if (recordCount === 0) return '进入质量验收录入首条记录，形成第一份 proof。'
    if (activeStatus === 'closed') return '项目已完结，建议进入审计与追溯复核。'
    return '进入计量与结算，核对 BOQ 与守恒状态。'
  }, [activeProject, activeStatus, componentRows.length])

  return (
    <div>
      <Card title="项目工作台" icon="🏗️">
        <div style={{ fontSize: 12, color: '#64748B', marginBottom: 12 }}>
          QCSpec 仅做施工质检闭环，不提供项目注册。先选择已同步项目，再推进构件与工序。
        </div>

        <div className="toolbar">
          <input
            className="search-input"
            value={searchText}
            onChange={(e) => onSearchTextChange(e.target.value)}
            placeholder="搜索项目/业主"
          />
          <select
            className="filter-select"
            value={statusFilter}
            onChange={(e) => onStatusFilterChange(e.target.value)}
          >
            <option value="">全部状态</option>
            <option value="active">进行中</option>
            <option value="pending">待开始</option>
            <option value="closed">已完成</option>
          </select>
          <select
            className="filter-select"
            value={typeFilter}
            onChange={(e) => onTypeFilterChange(e.target.value)}
          >
            <option value="">全部类型</option>
            {projectTypeOptions.map((option) => (
              <option key={`filter-${option.value}`} value={option.value}>
                {option.label}
              </option>
            ))}
          </select>
        </div>

        <div style={{ display: 'grid', gridTemplateColumns: '360px minmax(0, 1fr)', gap: 12, alignItems: 'start' }}>
          <div style={{ border: '1px solid #E2E8F0', borderRadius: 10, background: '#fff', maxHeight: 680, overflowY: 'auto' }}>
            <div style={{ padding: '10px 12px', borderBottom: '1px solid #EEF2F7', fontSize: 12, color: '#64748B', fontWeight: 700 }}>
              项目列表（{filteredProjects.length}）
            </div>
            {filteredProjects.length === 0 ? (
              <div style={{ padding: 12, fontSize: 12, color: '#94A3B8' }}>无匹配项目，请调整筛选条件。</div>
            ) : (
              filteredProjects.map((project) => {
                const active = project.id === activeProject?.id
                return (
                  <button
                    key={project.id}
                    type="button"
                    onClick={() => setActiveProjectId(project.id)}
                    style={{
                      width: '100%',
                      textAlign: 'left',
                      border: 'none',
                      borderBottom: '1px solid #F1F5F9',
                      background: active ? '#EFF6FF' : '#fff',
                      padding: '10px 12px',
                      cursor: 'pointer',
                    }}
                  >
                    <div style={{ display: 'flex', justifyContent: 'space-between', gap: 8 }}>
                      <strong style={{ fontSize: 13, color: '#0F172A' }}>{project.name}</strong>
                      <span className={`status-pill ${project.status === 'active' ? 'pill-active' : project.status === 'pending' ? 'pill-pending' : 'pill-closed'}`}>
                        {project.status === 'active' ? '进行中' : project.status === 'pending' ? '待开始' : '已完成'}
                      </span>
                    </div>
                    <div style={{ fontSize: 12, color: '#64748B', marginTop: 4 }}>
                      🧾 {project.record_count} | 📷 {project.photo_count}
                    </div>
                  </button>
                )
              })
            )}
          </div>

          <div style={{ border: '1px solid #E2E8F0', borderRadius: 10, background: '#fff', padding: 12 }}>
            {!activeProject ? (
              <div style={{ fontSize: 12, color: '#94A3B8' }}>请先在左侧选择一个项目。</div>
            ) : (
              <>
                <div style={{ display: 'flex', justifyContent: 'space-between', gap: 8, alignItems: 'start' }}>
                  <div>
                    <div style={{ fontSize: 18, fontWeight: 800, color: '#0F172A' }}>{activeProject.name}</div>
                    <div style={{ fontSize: 12, color: '#64748B', marginTop: 3 }}>
                      {activeProject.contract_no || '-'} | {activeProject.start_date || '-'} ~ {activeProject.end_date || '-'}
                    </div>
                  </div>
                  <span className={`status-pill ${activeStatusClass}`}>{activeStatusLabel}</span>
                </div>

                <div
                  style={{
                    display: 'flex',
                    gap: 6,
                    marginTop: 12,
                    marginBottom: 10,
                    padding: 4,
                    borderRadius: 8,
                    border: '1px solid #E2E8F0',
                    background: '#F8FAFC',
                  }}
                >
                  {([
                    { key: 'overview', label: '项目概览' },
                    { key: 'components', label: `构件列表 (${componentRows.length})` },
                    { key: 'process', label: '工序推进' },
                  ] as { key: WorkbenchTab; label: string }[]).map((item) => (
                    <button
                      key={item.key}
                      type="button"
                      onClick={() => setWorkbenchTab(item.key)}
                      style={{
                        border: 'none',
                        borderRadius: 6,
                        padding: '8px 10px',
                        fontSize: 12,
                        fontWeight: 700,
                        cursor: 'pointer',
                        background: workbenchTab === item.key ? '#1A56DB' : 'transparent',
                        color: workbenchTab === item.key ? '#fff' : '#475569',
                      }}
                    >
                      {item.label}
                    </button>
                  ))}
                </div>

                {workbenchTab === 'overview' && (
                  <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 10 }}>
                    <MetricLine label="类型" value={`${typeIcon[activeProject.type] || '🏗️'} ${typeLabel[activeProject.type] || activeProject.type}`} />
                    <MetricLine label="业主单位" value={String(activeProject.owner_unit || '-')} />
                    <MetricLine label="范围模型" value={activeSegLabel} />
                    <MetricLine label="权限/团队" value={activePermLabel} />
                    <MetricLine label="记录统计" value={`🧾 ${activeProject.record_count} | 📷 ${activeProject.photo_count} | 🔐 ${activeProject.proof_count}`} />
                    <MetricLine label="V URI" mono value={String(activeProject.v_uri || '-')} />
                  </div>
                )}

                {workbenchTab === 'components' && (
                  <div style={{ border: '1px solid #E2E8F0', borderRadius: 8, overflow: 'hidden' }}>
                    <div style={{ padding: '8px 10px', fontSize: 12, color: '#64748B', background: '#F8FAFC', borderBottom: '1px solid #E2E8F0' }}>
                      构件与合同段对象（项目内）
                    </div>
                    {componentRows.length === 0 ? (
                      <div style={{ padding: 10, fontSize: 12, color: '#94A3B8' }}>
                        暂无构件数据，建议在“项目详情”中补充结构物或合同段。
                      </div>
                    ) : (
                      <div style={{ display: 'grid', gap: 0 }}>
                        {componentRows.map((row, idx) => (
                          <div
                            key={`${row.code}-${idx}`}
                            style={{
                              padding: '9px 10px',
                              borderBottom: idx === componentRows.length - 1 ? 'none' : '1px solid #F1F5F9',
                              display: 'grid',
                              gridTemplateColumns: '140px 1fr 120px',
                              gap: 8,
                              alignItems: 'center',
                              fontSize: 12,
                            }}
                          >
                            <strong style={{ color: '#0F172A' }}>{row.code}</strong>
                            <span style={{ color: '#334155' }}>{row.name}</span>
                            <span style={{ color: '#64748B' }}>{row.kind}</span>
                          </div>
                        ))}
                      </div>
                    )}
                  </div>
                )}

                {workbenchTab === 'process' && (
                  <>
                    <div
                      style={{
                        border: '1px solid #E2E8F0',
                        borderRadius: 8,
                        background: '#F8FAFC',
                        padding: '9px 10px',
                        fontSize: 12,
                        color: '#334155',
                        marginBottom: 10,
                      }}
                    >
                      下一步建议：{nextActionHint}
                    </div>
                    <div style={{ border: '1px solid #E2E8F0', borderRadius: 8, overflow: 'hidden' }}>
                      <div style={{ padding: '8px 10px', fontSize: 12, color: '#64748B', background: '#F8FAFC', borderBottom: '1px solid #E2E8F0' }}>
                        项目工序推进状态
                      </div>
                      {processSteps.map((step, idx) => (
                        <div
                          key={step.name}
                          style={{
                            padding: '9px 10px',
                            borderBottom: idx === processSteps.length - 1 ? 'none' : '1px solid #F1F5F9',
                            display: 'flex',
                            justifyContent: 'space-between',
                            alignItems: 'center',
                            fontSize: 12,
                          }}
                        >
                          <span style={{ color: '#0F172A' }}>{step.name}</span>
                          <span style={{ color: step.status === '已完成' ? '#15803D' : step.status === '进行中' ? '#1D4ED8' : '#B45309' }}>
                            {step.status}
                          </span>
                        </div>
                      ))}
                    </div>
                  </>
                )}

                <div style={{ marginTop: 14, paddingTop: 12, borderTop: '1px solid #EEF2F7', display: 'flex', gap: 8, flexWrap: 'wrap' }}>
                  <button type="button" className="act-btn act-enter" onClick={() => onEnterInspection(activeProject)}>
                    进入项目流程
                  </button>
                  <button type="button" className="act-btn act-detail" onClick={() => onOpenProjectDetail(activeProject.id)}>
                    项目详情
                  </button>
                  <details style={{ position: 'relative' }}>
                    <summary className="act-btn act-detail" style={{ listStyle: 'none', cursor: 'pointer' }}>
                      更多
                    </summary>
                    <div
                      style={{
                        position: 'absolute',
                        left: 0,
                        top: 28,
                        zIndex: 20,
                        minWidth: 150,
                        background: '#fff',
                        border: '1px solid #E2E8F0',
                        borderRadius: 8,
                        padding: 8,
                        display: 'grid',
                        gap: 6,
                        boxShadow: '0 8px 16px rgba(15, 23, 42, 0.08)',
                      }}
                    >
                      <button type="button" className="act-btn act-proof" onClick={() => onEnterProof(activeProject)}>
                        Proof 链
                      </button>
                      <button type="button" className="act-btn act-edit" onClick={() => onEditProject(activeProject.id)}>
                        编辑
                      </button>
                      <button type="button" className="act-btn act-del" onClick={() => onDeleteProject(activeProject.id, activeProject.name)}>
                        删除
                      </button>
                    </div>
                  </details>
                </div>
              </>
            )}
          </div>
        </div>

      </Card>
    </div>
  )
}

function MetricLine({ label, value, mono = false }: { label: string; value: string; mono?: boolean }) {
  return (
    <div style={{ border: '1px solid #E2E8F0', borderRadius: 8, padding: '8px 10px', background: '#F8FAFC' }}>
      <div style={{ fontSize: 12, color: '#64748B' }}>{label}</div>
      <div style={{ fontSize: 12, fontWeight: 700, color: '#0F172A', marginTop: 4, fontFamily: mono ? 'monospace' : 'var(--sans)', wordBreak: 'break-word' }}>
        {value}
      </div>
    </div>
  )
}
