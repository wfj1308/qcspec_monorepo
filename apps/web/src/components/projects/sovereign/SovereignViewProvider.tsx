import { createContext, useContext, useMemo  } from 'react'
import { useAuthStore } from '../../../store'
import type { SovereignWorkspaceView } from './SovereignProjectContext'

export type SovereignPermission =
  | 'VIEW_BOQ'
  | 'SUBMIT_TRIP'
  | 'AUDIT_PROOF'
  | 'MANAGE_GENESIS'
  | 'MANAGE_NORM'
  | 'MINT_DELTA'
  | 'VIEW_EVIDENCE'

export type SovereignWorkbenchRole = 'contractor' | 'supervisor' | 'auditor'

export type SovereignIdentity = {
  did: string
  dtoRole: string
  title: string
  displayName: string
}

type SovereignViewContextValue = {
  identity: SovereignIdentity
  workbenchRole: SovereignWorkbenchRole
  permissions: SovereignPermission[]
  allowedViews: SovereignWorkspaceView[]
  defaultView: SovereignWorkspaceView
  roleLabel: string
}

const SovereignViewContext = createContext<SovereignViewContextValue | null>(null)

function mapDtoRoleToWorkbench(dtoRole: string): SovereignWorkbenchRole {
  if (dtoRole === 'AI') return 'contractor'
  if (dtoRole === 'SUPERVISOR') return 'supervisor'
  return 'auditor'
}

function permissionsForRole(role: SovereignWorkbenchRole): SovereignPermission[] {
  if (role === 'contractor') {
    return ['VIEW_BOQ', 'SUBMIT_TRIP', 'VIEW_EVIDENCE']
  }
  if (role === 'supervisor') {
    return ['VIEW_BOQ', 'AUDIT_PROOF', 'VIEW_EVIDENCE', 'SUBMIT_TRIP']
  }
  return ['VIEW_BOQ', 'AUDIT_PROOF', 'VIEW_EVIDENCE', 'MANAGE_GENESIS', 'MANAGE_NORM', 'MINT_DELTA']
}

function allowedViewsForRole(role: SovereignWorkbenchRole): SovereignWorkspaceView[] {
  if (role === 'contractor') return ['trip']
  if (role === 'supervisor') return ['audit', 'trip']
  return ['genesis', 'audit']
}

function defaultViewForRole(role: SovereignWorkbenchRole): SovereignWorkspaceView {
  if (role === 'contractor') return 'trip'
  if (role === 'supervisor') return 'audit'
  return 'genesis'
}

function roleLabelForRole(role: SovereignWorkbenchRole) {
  if (role === 'contractor') return 'Contractor Workbench'
  if (role === 'supervisor') return 'Supervisor Workbench'
  return 'Sovereign Vault'
}

type Props = {
  children: React.ReactNode
}

export function SovereignViewProvider({ children }: Props) {
  const user = useAuthStore((state) => state.user)

  const value = useMemo<SovereignViewContextValue>(() => {
    const dtoRole = String(user?.dto_role || 'PUBLIC').toUpperCase()
    const workbenchRole = mapDtoRoleToWorkbench(dtoRole)
    return {
      identity: {
        did: String(user?.v_uri || ''),
        dtoRole,
        title: String(user?.title || ''),
        displayName: String(user?.name || ''),
      },
      workbenchRole,
      permissions: permissionsForRole(workbenchRole),
      allowedViews: allowedViewsForRole(workbenchRole),
      defaultView: defaultViewForRole(workbenchRole),
      roleLabel: roleLabelForRole(workbenchRole),
    }
  }, [user?.dto_role, user?.name, user?.title, user?.v_uri])

  return (
    <SovereignViewContext.Provider value={value}>
      {children}
    </SovereignViewContext.Provider>
  )
}

export function useSovereignView() {
  const ctx = useContext(SovereignViewContext)
  if (!ctx) {
    throw new Error('useSovereignView must be used within SovereignViewProvider')
  }
  return ctx
}
