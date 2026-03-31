import React, { useEffect, useMemo, useRef, useState } from 'react'
import AuditorWorkbench from './sovereign/AuditorWorkbench'
import ContractorWorkbench from './sovereign/ContractorWorkbench'
import SidebarNavigation from './sovereign/SidebarNavigation'
import SovereignStatusBar from './sovereign/SovereignStatusBar'
import {
  SovereignProjectProvider,
  type SovereignWorkspaceSnapshot,
  type SovereignWorkspaceView,
} from './sovereign/SovereignProjectContext'
import {
  SovereignViewProvider,
  type SovereignWorkbenchRole,
  useSovereignView,
} from './sovereign/SovereignViewProvider'
import SupervisorWorkbench from './sovereign/SupervisorWorkbench'

type ProjectLike = {
  id?: string
  name?: string
  v_uri?: string
} | null

type Props = {
  project: ProjectLike
}

const EMPTY_SNAPSHOT: SovereignWorkspaceSnapshot = {
  activePath: '',
  lifecycle: 'Genesis',
  activeCode: '',
  activeStatus: '',
  totalHash: '',
  verifyUri: '',
  finalProofReady: false,
  isOnline: true,
  offlineQueueSize: 0,
  disputeOpen: false,
  disputeProof: '',
  archiveLocked: false,
}

type WorkspaceRoute = {
  routeRole: SovereignWorkbenchRole | null
  routeView: SovereignWorkspaceView | null
}

function normalizeWorkspacePath(projectId: string, role: SovereignWorkbenchRole, view: SovereignWorkspaceView) {
  return `/project/${encodeURIComponent(projectId)}/${role}/workbench?view=${view}`
}

function parseWorkspaceRoute(projectId: string, pathname: string, search: string): WorkspaceRoute {
  const match = pathname.match(/^\/project\/([^/]+)\/(contractor|supervisor|auditor)\/workbench\/?$/)
  if (!match) return { routeRole: null, routeView: null }
  if (decodeURIComponent(match[1] || '') !== projectId) return { routeRole: null, routeView: null }
  const params = new URLSearchParams(search || '')
  const viewParam = params.get('view')
  const routeView = viewParam === 'trip' || viewParam === 'audit' || viewParam === 'genesis'
    ? viewParam
    : null
  return {
    routeRole: match[2] as SovereignWorkbenchRole,
    routeView,
  }
}

function useSovereignWorkspaceRoute(
  projectId: string,
  role: SovereignWorkbenchRole,
  allowedViews: SovereignWorkspaceView[],
  defaultView: SovereignWorkspaceView,
) {
  const fallbackPathRef = useRef<string>('/')
  const [workspaceView, setWorkspaceView] = useState<SovereignWorkspaceView>(defaultView)

  useEffect(() => {
    if (typeof window === 'undefined' || !projectId) return
    const currentPath = `${window.location.pathname || '/'}${window.location.search || ''}${window.location.hash || ''}`
    const route = parseWorkspaceRoute(projectId, window.location.pathname || '', window.location.search || '')
    const matched = Boolean(route.routeRole)
    fallbackPathRef.current = matched ? '/' : currentPath

    const requestedView = route.routeView && allowedViews.includes(route.routeView) ? route.routeView : defaultView
    setWorkspaceView(requestedView)
    window.history.replaceState(window.history.state, '', normalizeWorkspacePath(projectId, role, requestedView))

    const handlePopState = () => {
      const nextRoute = parseWorkspaceRoute(projectId, window.location.pathname || '', window.location.search || '')
      if (nextRoute.routeRole) {
        const nextView = nextRoute.routeView && allowedViews.includes(nextRoute.routeView) ? nextRoute.routeView : defaultView
        setWorkspaceView(nextView)
        return
      }
      setWorkspaceView(defaultView)
    }

    window.addEventListener('popstate', handlePopState)
    return () => {
      window.removeEventListener('popstate', handlePopState)
      window.history.replaceState(window.history.state, '', fallbackPathRef.current || '/')
    }
  }, [allowedViews, defaultView, projectId, role])

  const navigate = (view: SovereignWorkspaceView) => {
    if (typeof window === 'undefined' || !projectId) return
    const nextView = allowedViews.includes(view) ? view : defaultView
    const nextPath = normalizeWorkspacePath(projectId, role, nextView)
    if (`${window.location.pathname || ''}${window.location.search || ''}` !== nextPath) {
      window.history.pushState(window.history.state, '', nextPath)
    }
    setWorkspaceView(nextView)
  }

  return { workspaceView, navigate }
}

function WorkspaceBody({ project }: { project: ProjectLike }) {
  const projectId = String(project?.id || '')
  const { workbenchRole, allowedViews, defaultView } = useSovereignView()
  const { workspaceView, navigate } = useSovereignWorkspaceRoute(projectId, workbenchRole, allowedViews, defaultView)
  const [snapshot, setSnapshot] = useState<SovereignWorkspaceSnapshot>(EMPTY_SNAPSHOT)

  const navItems = useMemo(() => {
    const items: Array<{ view: SovereignWorkspaceView; label: string; title: string; detail: string }> = []
    if (allowedViews.includes('trip')) {
      items.push({
        view: 'trip',
        label: workbenchRole === 'contractor' ? '任务录入' : '执行中心',
        title: 'Trip Console',
        detail: 'SPU submit, field photo, and SOP guidance.',
      })
    }
    if (allowedViews.includes('audit')) {
      items.push({
        view: 'audit',
        label: workbenchRole === 'supervisor' ? '审核工作台' : '证据与审计',
        title: 'Evidence & Audit',
        detail: 'Proof chain, dual gate, and conflict review.',
      })
    }
    if (allowedViews.includes('genesis')) {
      items.push({
        view: 'genesis',
        label: '资产对账',
        title: 'Project Genesis',
        detail: '0# ledger, NormRef binding, and delta controls.',
      })
    }
    return items
  }, [allowedViews, workbenchRole])

  const contextValue = useMemo(() => ({
    projectId,
    projectName: String(project?.name || ''),
    projectUri: String(project?.v_uri || ''),
    workspaceView,
    navigate,
    snapshot,
    setSnapshot,
  }), [navigate, project?.name, project?.v_uri, projectId, snapshot, workspaceView])

  const sharedProps = {
    project,
    workspaceView,
    onNavigateView: navigate,
    onContextChange: setSnapshot,
  }

  return (
    <SovereignProjectProvider value={contextValue}>
      <div className="mt-3 rounded-3xl border border-slate-200 bg-slate-50/70 p-3">
        <SovereignStatusBar />
        <div className="grid gap-4 xl:grid-cols-[260px_minmax(0,1fr)]">
          <SidebarNavigation items={navItems} activeView={workspaceView} onNavigate={navigate} />
          <div className="min-w-0">
            {workbenchRole === 'contractor' && <ContractorWorkbench {...sharedProps} />}
            {workbenchRole === 'supervisor' && <SupervisorWorkbench {...sharedProps} />}
            {workbenchRole === 'auditor' && <AuditorWorkbench {...sharedProps} />}
          </div>
        </div>
      </div>
    </SovereignProjectProvider>
  )
}

export default function SovereignProjectWorkspace({ project }: Props) {
  return (
    <SovereignViewProvider>
      <WorkspaceBody project={project} />
    </SovereignViewProvider>
  )
}
