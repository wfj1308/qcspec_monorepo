import SovereignWorkbenchPanel from '../SovereignWorkbenchPanel'
import type { SovereignWorkspaceSnapshot, SovereignWorkspaceView } from './SovereignProjectContext'

type ProjectLike = {
  id?: string
  name?: string
  v_uri?: string
} | null

type Props = {
  project: ProjectLike
  workspaceView: SovereignWorkspaceView
  onNavigateView: (view: SovereignWorkspaceView) => void
  onContextChange: (snapshot: SovereignWorkspaceSnapshot) => void
}

export default function SupervisorWorkbench({ project, workspaceView, onNavigateView, onContextChange }: Props) {
  return (
    <div className="grid gap-3">
      <div className="rounded-2xl border border-sky-200 bg-sky-50 px-4 py-3 text-sm text-sky-950">
        Supervisor Workbench prioritizes audit review, sign-off, and blocker handling. Trip data stays available, but evidence comparison and approval actions lead the page.
      </div>
      <SovereignWorkbenchPanel
        project={project}
        workspaceView={workspaceView}
        onNavigateView={onNavigateView}
        onContextChange={onContextChange}
      />
    </div>
  )
}
