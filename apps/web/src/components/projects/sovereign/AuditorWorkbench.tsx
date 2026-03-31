import React from 'react'
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

export default function AuditorWorkbench({ project, workspaceView, onNavigateView, onContextChange }: Props) {
  return (
    <div className="grid gap-3">
      <div className="rounded-2xl border border-amber-200 bg-amber-50 px-4 py-3 text-sm text-amber-950">
        Sovereign Vault focuses on evidence lineage, genesis control, norm versioning, and delta actions. Recording widgets stay hidden until needed.
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
