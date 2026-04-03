import React from 'react'
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

interface AutoregRow {
  project_code?: string
  project_name?: string
  project_uri?: string
  site_uri?: string
  updated_at?: string
  source_system?: string
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
  canUseEnterpriseApi: boolean
  syncingProjectId: string | null
  autoregRows: AutoregRow[]
  onSearchTextChange: (value: string) => void
  onStatusFilterChange: (value: string) => void
  onTypeFilterChange: (value: string) => void
  onCreateProject: () => void
  onGoInspection: () => void
  onGoProof: () => void
  onEnterInspection: (project: any) => void
  onEnterProof: (project: any) => void
  onRetryAutoreg: (projectId: string, projectName: string) => void
  onDirectAutoreg: (projectId: string, projectName: string) => void
  onEditProject: (projectId: string) => void
  onOpenProjectDetail: (projectId: string) => void
  onDeleteProject: (projectId: string, projectName: string) => void
  onRefreshAutoreg: () => Promise<void> | void
}

export default function ProjectsPanel({
  searchText,
  statusFilter,
  typeFilter,
  projectTypeOptions,
  filteredProjects,
  projectMeta,
  typeIcon,
  typeLabel,
  canUseEnterpriseApi,
  syncingProjectId,
  autoregRows,
  onSearchTextChange,
  onStatusFilterChange,
  onTypeFilterChange,
  onCreateProject,
  onGoInspection,
  onGoProof,
  onEnterInspection,
  onEnterProof,
  onRetryAutoreg,
  onDirectAutoreg,
  onEditProject,
  onOpenProjectDetail,
  onDeleteProject,
  onRefreshAutoreg,
}: ProjectsPanelProps) {
  return (
    <div>
      <Card title="项目列表" icon="🏗️">
        <div style={{ display: 'flex', justifyContent: 'flex-end', gap: 8, marginBottom: 12, flexWrap: 'wrap' }}>
          <button type="button" className="act-btn act-detail" onClick={onCreateProject}>
            ＋ 注册项目
          </button>
          <button type="button" className="act-btn act-enter" onClick={onGoInspection}>
            开始质检
          </button>
          <button type="button" className="act-btn act-proof" onClick={onGoProof}>
            Proof 工作台
          </button>
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

        <div style={{ border: '1px solid #E2E8F0', borderRadius: 10, overflow: 'hidden' }}>
          <table className="proj-table">
            <thead>
              <tr>
                {['项目名称', '类型', '业主单位', '范围模型', 'v:// URI', '记录', '状态', '操作'].map((header) => (
                  <th key={header}>{header}</th>
                ))}
              </tr>
            </thead>
            <tbody>
              {filteredProjects.map((project) => {
                const meta = projectMeta[project.id]
                const segLabel = !meta
                  ? '默认'
                  : meta.segType === 'km'
                    ? `桩号 ${meta.segStart || '-'} ~ ${meta.segEnd || '-'}`
                    : meta.segType === 'contract'
                      ? `合同段 ${meta.contractSegs.length} 个`
                      : `结构物 ${meta.structures.length} 个`
                const permLabel = meta
                  ? `${meta.permTemplate} / ${meta.memberCount}人 / 检测 ${(meta.inspectionTypes || []).length}类`
                  : '-'
                const statusClass = project.status === 'active' ? 'pill-active' : project.status === 'pending' ? 'pill-pending' : 'pill-closed'

                return (
                  <tr key={project.id}>
                    <td>
                      <div style={{ fontWeight: 700 }}>{project.name}</div>
                      <div style={{ fontSize: 12, color: '#94A3B8' }}>
                        {project.contract_no || '-'} | {project.start_date || '-'} ~ {project.end_date || '-'}
                      </div>
                    </td>
                    <td>
                      <span className={`type-chip chip-${project.type}`}>
                        {typeIcon[project.type] || '🏗️'} {typeLabel[project.type] || project.type}
                      </span>
                    </td>
                    <td style={{ color: '#475569' }}>{project.owner_unit}</td>
                    <td>
                      <div style={{ fontSize: 12, color: '#334155' }}>{segLabel}</div>
                      <div style={{ fontSize: 12, color: '#94A3B8', marginTop: 2 }}>{permLabel}</div>
                    </td>
                    <td style={{ fontFamily: 'monospace', color: '#1A56DB' }}>{project.v_uri}</td>
                    <td>🧾 {project.record_count} | 📷 {project.photo_count}</td>
                    <td>
                      <span className={`status-pill ${statusClass}`}>
                        {project.status === 'active' ? '进行中' : project.status === 'pending' ? '待开始' : '已完成'}
                      </span>
                    </td>
                    <td>
                      <div className="action-btns">
                        <button type="button" className="act-btn act-enter" onClick={() => onEnterInspection(project)}>
                          进入质检
                        </button>
                        <button type="button" className="act-btn act-proof" onClick={() => onEnterProof(project)}>
                          Proof 链
                        </button>
                        {canUseEnterpriseApi && (
                          <button
                            type="button"
                            className="act-btn act-detail"
                            onClick={() => onRetryAutoreg(project.id, project.name)}
                            disabled={syncingProjectId === project.id}
                          >
                            {syncingProjectId === project.id ? '同步中...' : '重试同步'}
                          </button>
                        )}
                        {canUseEnterpriseApi && (
                          <button
                            type="button"
                            className="act-btn act-detail"
                            onClick={() => onDirectAutoreg(project.id, project.name)}
                            disabled={syncingProjectId === project.id}
                          >
                            {syncingProjectId === project.id ? '登记中...' : '直连登记'}
                          </button>
                        )}
                        <button type="button" className="act-btn act-edit" onClick={() => onEditProject(project.id)}>
                          编辑
                        </button>
                        <button type="button" className="act-btn act-detail" onClick={() => onOpenProjectDetail(project.id)}>
                          详情
                        </button>
                        <button type="button" className="act-btn act-del" onClick={() => onDeleteProject(project.id, project.name)}>
                          删除
                        </button>
                      </div>
                    </td>
                  </tr>
                )
              })}
            </tbody>
          </table>
        </div>

        {canUseEnterpriseApi && (
          <div
            style={{
              marginTop: 12,
              border: '1px solid #E2E8F0',
              borderRadius: 10,
              padding: 12,
              background: '#FCFDFF',
            }}
          >
            <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: 8 }}>
              <div style={{ fontSize: 13, fontWeight: 700, color: '#0F172A' }}>自动登记记录</div>
              <button type="button" className="act-btn act-detail" onClick={() => onRefreshAutoreg()}>
                刷新
              </button>
            </div>
            {autoregRows.length === 0 ? (
              <div style={{ fontSize: 12, color: '#94A3B8' }}>
                暂无自动登记记录，可在项目操作列点击“重试同步/直连登记”。
              </div>
            ) : (
              <div style={{ display: 'grid', gap: 8 }}>
                {autoregRows.slice(0, 6).map((row, idx) => (
                  <div
                    key={`${row.project_code || row.project_name || 'autoreg'}-${idx}`}
                    style={{ border: '1px solid #E2E8F0', borderRadius: 8, padding: 10, background: '#fff' }}
                  >
                    <div style={{ fontSize: 13, fontWeight: 700, color: '#0F172A' }}>
                      {row.project_name || '-'}{' '}
                      <span style={{ fontWeight: 500, color: '#64748B' }}>({row.project_code || '-'})</span>
                    </div>
                    <div
                      style={{
                        fontSize: 12,
                        color: '#1A56DB',
                        fontFamily: 'monospace',
                        marginTop: 2,
                        wordBreak: 'break-all',
                      }}
                    >
                      {row.project_uri || '-'}
                    </div>
                    <div style={{ fontSize: 12, color: '#64748B', marginTop: 2 }}>
                      site: {row.site_uri || '-'} | 来源: {row.source_system || '-'}
                    </div>
                    <div style={{ fontSize: 12, color: '#94A3B8', marginTop: 4 }}>
                      更新: {row.updated_at ? new Date(row.updated_at).toLocaleString('zh-CN') : '-'}
                    </div>
                  </div>
                ))}
                {autoregRows.length > 6 && (
                  <div style={{ fontSize: 12, color: '#64748B' }}>仅展示前 6 条，共 {autoregRows.length} 条</div>
                )}
              </div>
            )}
          </div>
        )}
      </Card>
    </div>
  )
}
