import React from 'react'

interface RegisterPanelFrameProps {
  projects: any[]
  registerSegCount: number
  registerRecordCount: number
  registerStep: number
  registerSuccess: { id: string; name: string; uri: string } | null
  registerPreviewProjects: any[]
  typeIcon: Record<string, string>
  typeLabel: Record<string, string>
  onStepClick: (step: number) => void
  onStartInspectionFromSuccess: () => void
  onGoProjects: () => void
  onResetRegister: () => void
  onOpenProjectDetail: (projectId: string) => void
  onEnterInspection: (project: any) => void
  children: React.ReactNode
}

export default function RegisterPanelFrame({
  projects,
  registerSegCount,
  registerRecordCount,
  registerStep,
  registerSuccess,
  registerPreviewProjects,
  typeIcon,
  typeLabel,
  onStepClick,
  onStartInspectionFromSuccess,
  onGoProjects,
  onResetRegister,
  onOpenProjectDetail,
  onEnterInspection,
  children,
}: RegisterPanelFrameProps) {
  return (
    <div>
      <div className="register-hero">
        <div className="register-eyebrow">QCSpec Register Center</div>
        <h2 className="register-title">
          注册项目并激活 <span className="hl">v:// 质检节点</span>
        </h2>
        <p className="register-sub">每个项目将绑定唯一 v:// URI，质检记录、照片与报告统一归档，并可追溯。</p>
        <div className="register-hero-stats">
          <div className="hero-stat">
            <div className="hero-stat-val">{projects.length}</div>
            <div className="hero-stat-label">已注册项目</div>
          </div>
          <div className="hero-stat">
            <div className="hero-stat-val">{registerSegCount}</div>
            <div className="hero-stat-label">检测分段</div>
          </div>
          <div className="hero-stat">
            <div className="hero-stat-val">{registerRecordCount}</div>
            <div className="hero-stat-label">质检记录</div>
          </div>
        </div>
      </div>

      <div className="reg-steps">
        {[
          { num: 1, label: '项目信息' },
          { num: 2, label: '检测范围' },
          { num: 3, label: '零号台帐' },
          { num: 4, label: '确认注册' },
        ].map((step) => (
          <div
            key={step.num}
            className={`reg-step ${registerStep === step.num ? 'active' : registerStep > step.num ? 'done' : ''}`}
            onClick={() => {
              if (registerSuccess) return
              onStepClick(step.num)
            }}
            style={{ cursor: registerSuccess ? 'default' : 'pointer' }}
          >
            <div className="reg-step-num">{registerStep > step.num ? '✓' : step.num}</div>
            <div className="reg-step-label">{step.label}</div>
          </div>
        ))}
      </div>

      {registerSuccess ? (
        <div className="success-banner">
          <div className="success-icon-big">✓</div>
          <div style={{ fontSize: 20, fontWeight: 800, marginBottom: 6 }}>项目注册成功</div>
          <div style={{ fontSize: 13, color: '#A7F3D0' }}>已生成项目节点与基础配置</div>
          <div className="success-uri">{registerSuccess.uri}</div>
          <div style={{ fontSize: 12, color: '#D1FAE5', marginBottom: 10 }}>
            项目编号：{registerSuccess.id} | 项目名称：{registerSuccess.name}
          </div>
          <div className="btn-row" style={{ maxWidth: 620, margin: '8px auto 0' }}>
            <button className="btn-primary btn-green" onClick={onStartInspectionFromSuccess}>
              开始质检录入
            </button>
            <button className="btn-primary" onClick={onGoProjects}>
              进入项目列表
            </button>
            <button className="btn-secondary" onClick={onResetRegister}>
              继续注册
            </button>
          </div>
        </div>
      ) : (
        <>{children}</>
      )}

      <div className="register-projects">
        <div className="register-projects-head">
          <div className="register-projects-title">已注册项目</div>
          <span className="register-projects-count">{projects.length}</span>
        </div>
        {registerPreviewProjects.length === 0 ? (
          <div className="register-empty">
            <div className="register-empty-icon">🏗️</div>
            <div className="register-empty-title">暂无注册项目</div>
            <div className="register-empty-sub">完成上方步骤即可创建第一个项目。</div>
          </div>
        ) : (
          <div className="register-project-list">
            {registerPreviewProjects.map((project) => (
              <div
                key={`reg-${project.id}`}
                className="reg-proj-card"
                onClick={() => onOpenProjectDetail(project.id)}
                style={project.id === registerSuccess?.id ? { background: '#F0FDF4', borderColor: '#86EFAC' } : undefined}
              >
                <div className={`type-chip chip-${project.type}`}>
                  {typeIcon[project.type] || '🏗️'} {typeLabel[project.type] || project.type}
                </div>
                <div className="reg-proj-main">
                  <div className="reg-proj-name">
                    {project.name}
                    {project.id === registerSuccess?.id && (
                      <span style={{ marginLeft: 6, fontSize: 12, color: '#059669', fontWeight: 800 }}>NEW</span>
                    )}
                  </div>
                  <div className="reg-proj-uri">{project.v_uri}</div>
                  <div className="reg-proj-meta">
                    业主：{project.owner_unit || '-'} | 记录：{project.record_count} | 照片：{project.photo_count}
                  </div>
                </div>
                <div className="reg-proj-actions">
                  <span className={`status-pill ${project.status === 'active' ? 'pill-active' : project.status === 'pending' ? 'pill-pending' : 'pill-closed'}`}>
                    {project.status === 'active' ? '进行中' : project.status === 'pending' ? '待开始' : '已完成'}
                  </span>
                  <button
                    className="act-btn act-enter"
                    onClick={(e) => {
                      e.stopPropagation()
                      onEnterInspection(project)
                    }}
                  >
                    进入质检
                  </button>
                </div>
              </div>
            ))}
            {projects.length > registerPreviewProjects.length && (
              <button className="btn-secondary" style={{ width: '100%' }} onClick={onGoProjects}>
                查看全部项目
              </button>
            )}
          </div>
        )}
      </div>
    </div>
  )
}
