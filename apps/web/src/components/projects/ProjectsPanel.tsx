import { useEffect, useMemo, useState } from 'react'
import { useQuery } from '@tanstack/react-query'
import type { Project } from '@qcspec/types'
import { Card } from '../ui'
import ProjectCreateModal from './ProjectCreateModal'
import EntityWorkbench from '../workbench/EntityWorkbench'
import { fetchWorkbenchEntities, workbenchKeys } from '../workbench/workbenchApi'

interface ProjectTypeOption {
  value: string
  label: string
}

type ProjectItem = Project

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
  onCreateProject: (input: {
    code: string
    name: string
    type: string
    ownerUnit: string
  }) => Promise<boolean> | boolean
  onEnterInspection: (project: ProjectItem) => void
  onEnterProof: (project: ProjectItem) => void
  onEditProject: (projectId: string) => void
  onOpenProjectDetail: (projectId: string) => void
  onDeleteProject: (projectId: string, projectName: string) => void
}

type WorkbenchTab = 'overview' | 'components' | 'process'

type ProjectView = {
  displayCode: string
  displayUri: string
  ownerOrg: string
  clientOrg: string
  designerOrg: string
  contractorOrg: string
  supervisorOrg: string
  description: string
  lastUpdatedAt: string
  hasRecordStats: boolean
}

type ComponentRow = {
  code: string
  name: string
  kind: string
}

type MetricCard = {
  label: string
  value: string
  mono?: boolean
}

const PROJECT_ID_PATTERN = /PJT-[A-Z0-9-]+/i

function normalizeProjectType(value: unknown): string {
  const raw = String(value || '').trim()
  if (!raw) return ''
  const normalized = raw.toLowerCase().replace(/[\s-]+/g, '_')
  const aliases: Record<string, string> = {
    h: 'highway',
    highway: 'highway',
    h_highway: 'highway',
    road: 'road',
    urban: 'urban',
    bridge: 'bridge',
    bridge_repair: 'bridge_repair',
    bridgerepair: 'bridge_repair',
    tunnel: 'tunnel',
    municipal: 'municipal',
    water: 'water',
  }
  if (aliases[normalized]) return aliases[normalized]
  if (/^h\s*highway$/i.test(raw)) return 'highway'
  return normalized
}

function readProjectField(project: Project, keys: string[]): string {
  const row = project as Project & Record<string, unknown>
  for (const key of keys) {
    const value = row[key]
    const text = String(value || '').trim()
    if (text) return text
  }
  return ''
}

function toProjectView(project: Project | null): ProjectView {
  if (!project) {
    return {
      displayCode: '-',
      displayUri: '-',
      ownerOrg: '-',
      clientOrg: '-',
      designerOrg: '-',
      contractorOrg: '-',
      supervisorOrg: '-',
      description: '',
      lastUpdatedAt: '',
      hasRecordStats: false,
    }
  }

  const row = project as Project & Record<string, unknown>
  const hasRecordStats = Boolean(row.has_record_stats)

  return {
    displayCode:
      readProjectField(project, ['code']) ||
      String(project.erp_project_code || '').trim() ||
      String(project.id || '').trim() ||
      '-',
    displayUri:
      readProjectField(project, ['uri']) ||
      String(project.v_uri || '').trim() ||
      '-',
    ownerOrg:
      readProjectField(project, ['owner_org', 'ownerOrg']) ||
      String(project.owner_unit || '').trim() ||
      '-',
    clientOrg: readProjectField(project, ['client_org', 'clientOrg']) || '-',
    designerOrg: readProjectField(project, ['designer_org', 'designerOrg']) || '-',
    contractorOrg:
      readProjectField(project, ['contractor_org', 'contractorOrg']) ||
      String(project.contractor || '').trim() ||
      '-',
    supervisorOrg:
      readProjectField(project, ['supervisor_org', 'supervisorOrg']) ||
      String(project.supervisor || '').trim() ||
      '-',
    description: String(project.description || '').trim(),
    lastUpdatedAt: readProjectField(project, ['last_updated_at', 'lastUpdatedAt', 'updated_at']),
    hasRecordStats,
  }
}

function resolveProjectPathId(project: Project | null): string {
  if (!project) return ''
  const row = project as Project & Record<string, unknown>
  const uriCandidates = [
    String(row.uri || '').trim(),
    String(project.v_uri || '').trim(),
  ]

  for (const candidate of uriCandidates) {
    const match = candidate.match(PROJECT_ID_PATTERN)
    if (match?.[0]) return match[0].toUpperCase()
  }

  const idCandidates = [
    String(project.id || '').trim(),
    String(row.project_id || '').trim(),
    String(row.code || '').trim(),
    String(project.erp_project_code || '').trim(),
  ]
  return idCandidates.find((item) => Boolean(item)) || ''
}

function statusLabel(status: string): string {
  if (status === 'active') return '进行中'
  if (status === 'pending') return '待开始'
  return '已完成'
}

function statusClass(status: string): string {
  if (status === 'active') return 'pill-active'
  if (status === 'pending') return 'pill-pending'
  return 'pill-closed'
}

export default function ProjectsPanel({
  searchText,
  statusFilter,
  typeFilter,
  projectTypeOptions,
  filteredProjects,
  projectMeta: _projectMeta,
  typeIcon,
  typeLabel,
  onSearchTextChange,
  onStatusFilterChange,
  onTypeFilterChange,
  onCreateProject,
  onEnterInspection,
  onEnterProof,
  onEditProject,
  onOpenProjectDetail,
  onDeleteProject,
}: ProjectsPanelProps) {
  const [activeProjectId, setActiveProjectId] = useState<string>('')
  const [workbenchTab, setWorkbenchTab] = useState<WorkbenchTab>('overview')

  const [createOpen, setCreateOpen] = useState(false)
  const [createCode, setCreateCode] = useState('')
  const [createName, setCreateName] = useState('')
  const [createType, setCreateType] = useState(projectTypeOptions[0]?.value || 'highway')
  const [createOwnerUnit, setCreateOwnerUnit] = useState('')
  const [createError, setCreateError] = useState('')
  const [createSubmitting, setCreateSubmitting] = useState(false)

  useEffect(() => {
    if (!filteredProjects.length) {
      setActiveProjectId('')
      return
    }
    const exists = filteredProjects.some((project) => project.id === activeProjectId)
    if (!exists) setActiveProjectId(filteredProjects[0]?.id || '')
  }, [activeProjectId, filteredProjects])

  useEffect(() => {
    setWorkbenchTab('overview')
  }, [activeProjectId])

  const activeProject = useMemo(
    () => filteredProjects.find((project) => project.id === activeProjectId) || filteredProjects[0] || null,
    [activeProjectId, filteredProjects],
  )

  const activeProjectView = useMemo(() => toProjectView(activeProject), [activeProject])
  const projectPathId = useMemo(() => resolveProjectPathId(activeProject), [activeProject])

  const entitiesQuery = useQuery({
    queryKey: workbenchKeys.entities(projectPathId),
    queryFn: () => fetchWorkbenchEntities(projectPathId),
    enabled: Boolean(projectPathId),
    staleTime: 60_000,
  })

  const componentRows = useMemo<ComponentRow[]>(() => {
    const items = entitiesQuery.data?.items || []
    return items.map((entity, idx) => ({
      code: String(entity.entity_code || `ENT-${idx + 1}`),
      name: String(entity.entity_name || '未命名实体'),
      kind: String(entity.entity_type || 'entity'),
    }))
  }, [entitiesQuery.data?.items])

  const overviewCards = useMemo(() => {
    if (!activeProject) return [] as MetricCard[]
    const projectTypeKey = normalizeProjectType(activeProject.type)
    const projectTypeIcon = typeIcon[projectTypeKey] || typeIcon[activeProject.type || ''] || '🏗️'
    const projectTypeText =
      typeLabel[projectTypeKey] ||
      typeLabel[activeProject.type || ''] ||
      '未分类'
    const cards: MetricCard[] = [
      { label: '项目编码', value: activeProjectView.displayCode, mono: true },
      { label: '项目类型', value: `${projectTypeIcon} ${projectTypeText}` },
      { label: '业主单位', value: activeProjectView.ownerOrg },
      { label: '客户单位', value: activeProjectView.clientOrg },
      { label: '设计单位', value: activeProjectView.designerOrg },
      { label: '施工单位', value: activeProjectView.contractorOrg },
      { label: '监理单位', value: activeProjectView.supervisorOrg },
      { label: 'V URI', value: activeProjectView.displayUri, mono: true },
    ]

    if (activeProjectView.description) {
      cards.splice(7, 0, { label: '项目说明', value: activeProjectView.description })
    }

    if (activeProjectView.hasRecordStats) {
      cards.splice(7, 0, {
        label: '记录统计',
        value: `记录 ${Number(activeProject.record_count || 0)} | 图片 ${Number(activeProject.photo_count || 0)} | 存证 ${Number(activeProject.proof_count || 0)}`,
      })
    }

    if (activeProjectView.lastUpdatedAt) {
      cards.splice(7, 0, { label: '最近更新', value: activeProjectView.lastUpdatedAt })
    }

    return cards
  }, [activeProject, activeProjectView, typeIcon, typeLabel])

  const processSteps = useMemo(() => {
    const status = String(activeProject?.status || 'pending')
    const hasComponents = componentRows.length > 0
    const canUseStatDrivenStep = activeProjectView.hasRecordStats
    const recordCount = Number(activeProject?.record_count || 0)
    const proofCount = Number(activeProject?.proof_count || 0)

    return [
      { name: '项目初始化', status: status === 'pending' ? '待处理' : '已完成' },
      { name: '构件绑定', status: hasComponents ? '已完成' : '待处理' },
      { name: '质量验收', status: canUseStatDrivenStep && recordCount > 0 ? '进行中' : '待处理' },
      { name: '质量追溯', status: canUseStatDrivenStep && proofCount > 0 ? '进行中' : '待处理' },
      { name: '项目归档', status: status === 'closed' ? '已完成' : '待处理' },
    ]
  }, [activeProject?.proof_count, activeProject?.record_count, activeProject?.status, activeProjectView.hasRecordStats, componentRows.length])

  const hasAnyFilter = Boolean(searchText || statusFilter || typeFilter)
  const isEmptyProjects = filteredProjects.length === 0 && !hasAnyFilter

  const openCreateModal = () => {
    setCreateCode('')
    setCreateName('')
    setCreateType(projectTypeOptions[0]?.value || 'highway')
    setCreateOwnerUnit('')
    setCreateError('')
    setCreateOpen(true)
  }

  const closeCreateModal = () => {
    if (createSubmitting) return
    setCreateOpen(false)
    setCreateError('')
  }

  const submitCreateProject = async () => {
    const code = createCode.trim()
    const name = createName.trim()
    const ownerUnit = createOwnerUnit.trim()

    if (!code) {
      setCreateError('请先输入项目编码')
      return
    }
    if (!name) {
      setCreateError('请先输入项目名称')
      return
    }
    if (!ownerUnit) {
      setCreateError('请先输入业主单位')
      return
    }

    setCreateSubmitting(true)
    setCreateError('')
    try {
      const ok = await onCreateProject({
        code,
        name,
        type: createType,
        ownerUnit,
      })
      if (ok) {
        setCreateOpen(false)
      } else {
        setCreateError('创建失败，请稍后重试')
      }
    } finally {
      setCreateSubmitting(false)
    }
  }

  return (
    <div>
      <Card title="项目工作台" icon="🏗️">
        <div className="toolbar">
          <input
            className="search-input"
            value={searchText}
            onChange={(e) => onSearchTextChange(e.target.value)}
            placeholder="搜索项目/编码/单位"
          />
          <select className="filter-select" value={statusFilter} onChange={(e) => onStatusFilterChange(e.target.value)}>
            <option value="">全部状态</option>
            <option value="active">进行中</option>
            <option value="pending">待开始</option>
            <option value="closed">已完成</option>
          </select>
          <select className="filter-select" value={typeFilter} onChange={(e) => onTypeFilterChange(e.target.value)}>
            <option value="">全部类型</option>
            {projectTypeOptions.map((option) => (
              <option key={`filter-${option.value}`} value={option.value}>{option.label}</option>
            ))}
          </select>
          <button type="button" className="act-btn act-enter" onClick={openCreateModal}>新建项目</button>
        </div>

        {isEmptyProjects ? (
          <div className="project-empty">
            <div className="project-empty-icon">🏗️</div>
            <div className="project-empty-title">暂无项目</div>
            <div className="project-empty-sub">当前没有项目，请点击“新建项目”开始。</div>
          </div>
        ) : (
          <div style={{ display: 'grid', gridTemplateColumns: '360px minmax(0, 1fr)', gap: 12, alignItems: 'start' }}>
            <div style={{ border: '1px solid #E2E8F0', borderRadius: 10, background: '#fff', maxHeight: 680, overflowY: 'auto' }}>
              <div style={{ padding: '10px 12px', borderBottom: '1px solid #EEF2F7', fontSize: 12, color: '#64748B', fontWeight: 700 }}>
                项目列表 ({filteredProjects.length})
              </div>
              {filteredProjects.length === 0 ? (
                <div style={{ padding: 12, fontSize: 12, color: '#94A3B8' }}>无匹配项目，请调整筛选条件。</div>
              ) : (
                filteredProjects.map((project) => {
                  const active = project.id === activeProject?.id
                  const view = toProjectView(project)
                  const summaryParts = [view.displayCode]
                  if (view.hasRecordStats) {
                    summaryParts.push(`记录 ${Number(project.record_count || 0)}`)
                    summaryParts.push(`图片 ${Number(project.photo_count || 0)}`)
                  } else if (view.lastUpdatedAt) {
                    summaryParts.push(`更新 ${view.lastUpdatedAt}`)
                  }

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
                        <span className={`status-pill ${statusClass(String(project.status || 'active'))}`}>
                          {statusLabel(String(project.status || 'active'))}
                        </span>
                      </div>
                      <div style={{ fontSize: 12, color: '#64748B', marginTop: 4 }}>
                        {summaryParts.join(' | ')}
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
                        {activeProjectView.displayCode} | 业主：{activeProjectView.ownerOrg}
                      </div>
                    </div>
                    <span className={`status-pill ${statusClass(String(activeProject.status || 'active'))}`}>
                      {statusLabel(String(activeProject.status || 'active'))}
                    </span>
                  </div>

                  <div style={{ display: 'flex', gap: 6, marginTop: 12, marginBottom: 10, padding: 4, borderRadius: 8, border: '1px solid #E2E8F0', background: '#F8FAFC' }}>
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
                      {overviewCards.map((card) => (
                        <MetricLine key={card.label} label={card.label} value={card.value} mono={card.mono} />
                      ))}
                    </div>
                  )}

                  {workbenchTab === 'components' && (
                    <div style={{ border: '1px solid #E2E8F0', borderRadius: 8, overflow: 'hidden' }}>
                      <div style={{ padding: '8px 10px', fontSize: 12, color: '#64748B', background: '#F8FAFC', borderBottom: '1px solid #E2E8F0' }}>
                        构件与合同段对象
                      </div>
                      {entitiesQuery.isLoading ? (
                        <div style={{ padding: 10, fontSize: 12, color: '#94A3B8' }}>正在加载构件数据...</div>
                      ) : componentRows.length === 0 ? (
                        <div style={{ padding: 10, fontSize: 12, color: '#94A3B8' }}>暂无构件数据。</div>
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
                    <EntityWorkbench projectId={projectPathId || activeProject.id} />
                  )}

                  <div style={{ marginTop: 14, paddingTop: 12, borderTop: '1px solid #EEF2F7', display: 'flex', gap: 8, flexWrap: 'wrap' }}>
                    <button type="button" className="act-btn act-enter" onClick={() => onEnterInspection(activeProject)}>进入项目流程</button>
                    <button type="button" className="act-btn act-detail" onClick={() => onOpenProjectDetail(activeProject.id)}>项目详情</button>
                    <button type="button" className="act-btn act-proof" onClick={() => onEnterProof(activeProject)}>存证链</button>
                    <button type="button" className="act-btn act-edit" onClick={() => onEditProject(activeProject.id)}>编辑</button>
                    <button type="button" className="act-btn act-del" onClick={() => onDeleteProject(activeProject.id, activeProject.name)}>删除</button>
                  </div>
                </>
              )}
            </div>
          </div>
        )}
      </Card>

      <ProjectCreateModal
        open={createOpen}
        submitting={createSubmitting}
        code={createCode}
        name={createName}
        type={createType}
        ownerUnit={createOwnerUnit}
        typeOptions={projectTypeOptions}
        error={createError}
        onChangeCode={setCreateCode}
        onChangeName={setCreateName}
        onChangeType={setCreateType}
        onChangeOwnerUnit={setCreateOwnerUnit}
        onClose={closeCreateModal}
        onSubmit={submitCreateProject}
      />
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



