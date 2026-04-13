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

export default function ContractorWorkbench({ project, workspaceView, onNavigateView, onContextChange }: Props) {
  return (
    <div className="grid gap-3">
      <div className="rounded-2xl border border-emerald-200 bg-emerald-50 px-4 py-3 text-sm text-emerald-900">
        施工工作台聚焦工序提交、现场取证和规范校核。审计与结算操作放在后续环节处理。
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
