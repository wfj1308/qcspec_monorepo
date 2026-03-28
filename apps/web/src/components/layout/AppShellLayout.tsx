import React from 'react'

type NavItem = {
  key: string
  icon: React.ReactNode
  label: string
}

type NavSection = {
  label: string
  keys: string[]
}

type ProjectOption = {
  id: string
  name: string
}

interface AppShellLayoutProps {
  sidebarOpen: boolean
  activeTab: string
  navItems: NavItem[]
  navSections: NavSection[]
  projects: ProjectOption[]
  currentProjectId: string
  currentUserName: string
  currentUserTitle: string
  onToggleSidebar: () => void
  onNavigate: (tab: string) => void
  onSelectProject: (projectId: string) => void
  onLogout: () => void
  children: React.ReactNode
}

export default function AppShellLayout({
  sidebarOpen,
  activeTab,
  navItems,
  navSections,
  projects,
  currentProjectId,
  currentUserName,
  currentUserTitle,
  onToggleSidebar,
  onNavigate,
  onSelectProject,
  onLogout,
  children,
}: AppShellLayoutProps) {
  return (
    <div className="app-shell visible">
      <div
        className={`sidebar ${sidebarOpen ? 'open' : ''}`}
        style={{ transform: sidebarOpen ? 'translateX(0)' : 'translateX(-100%)' }}
      >
        <div className="sidebar-brand">
          <div className="sb-logo">
            <span className="qc">QC</span>
            <span className="spec">Spec</span>
          </div>
          <div className="sb-version">v2.0 | qcspec.com</div>
        </div>

        <div className="sidebar-nav">
          {navSections.map((section) => (
            <div className="nav-section" key={section.label}>
              <div className="nav-section-label">{section.label}</div>
              {section.keys.map((key) => {
                const item = navItems.find((navItem) => navItem.key === key)
                if (!item) return null
                const isActive = activeTab === item.key
                return (
                  <div
                    key={item.key}
                    className={`nav-item ${isActive ? 'active' : ''}`}
                    onClick={() => onNavigate(item.key)}
                  >
                    <span className="nav-icon">{item.icon}</span>
                    <span>{item.label}</span>
                    {item.key === 'projects' && <span className="nav-badge">{projects.length}</span>}
                  </div>
                )
              })}
            </div>
          ))}
        </div>

        <div className="sidebar-footer">
          <div className="user-card">
            <div className="user-avatar">{currentUserName[0]}</div>
            <div className="user-info">
              <div className="user-name">{currentUserName}</div>
              <div className="user-role">{currentUserTitle}</div>
            </div>
            <div className="logout-btn" onClick={onLogout} title="退出登录">
              ⏻
            </div>
          </div>
        </div>
      </div>

      <div className="main-content" style={{ marginLeft: sidebarOpen ? 220 : 0 }}>
        <div className="topbar">
          <div style={{ display: 'flex', alignItems: 'center', gap: 12 }}>
            <button
              onClick={onToggleSidebar}
              style={{
                background: 'none',
                border: 'none',
                cursor: 'pointer',
                fontSize: 18,
                color: '#6B7280',
                padding: 4,
              }}
            >
              ☰
            </button>
            <div className="topbar-title">
              {navItems.find((item) => item.key === activeTab)?.label || '控制台'}
            </div>
          </div>
          <div className="topbar-right">
            <select
              value={currentProjectId}
              onChange={(e) => onSelectProject(e.target.value)}
              style={{
                background: '#F0F4F8',
                border: '1px solid #E2E8F0',
                borderRadius: 8,
                padding: '6px 12px',
                fontSize: 13,
                fontFamily: 'var(--sans)',
                outline: 'none',
              }}
            >
              {projects.map((project) => (
                <option key={project.id} value={project.id}>
                  {project.name}
                </option>
              ))}
            </select>
            <button className="topbar-btn btn-outline" onClick={() => onNavigate('register')}>
              ＋ 注册项目
            </button>
            <button className="topbar-btn btn-blue" onClick={() => onNavigate('inspection')}>
              📷 开始质检
            </button>
            <button className="topbar-btn btn-logout" onClick={onLogout}>
              退出登录
            </button>
          </div>
        </div>

        <div className="content-body">{children}</div>
      </div>
    </div>
  )
}
