import type { Dispatch, SetStateAction } from 'react'
import type { PermTemplate, PermissionKey, PermissionRole, PermissionRow } from './appShellShared'
import { clonePermissionRows, detectPermissionTemplate, normalizePermissionMatrix, PERMISSION_TEMPLATES } from './appShellShared'

interface PersistPermissionMatrixFlowArgs {
  canUseEnterpriseApi: boolean
  enterpriseId?: string
  permissionMatrix: PermissionRow[]
  saveSettings: (enterpriseId: string, patch: Record<string, unknown>) => Promise<unknown>
  setPermissionMatrix: Dispatch<SetStateAction<PermissionRow[]>>
  setPermissionTemplate: (template: PermTemplate) => void
  showToast: (message: string) => void
}

export function updatePermissionCellFlow(
  role: PermissionRole,
  key: PermissionKey,
  value: boolean,
  setPermissionMatrix: Dispatch<SetStateAction<PermissionRow[]>>,
  setPermissionTemplate: (template: PermTemplate) => void
): void {
  setPermissionMatrix((prev) =>
    prev.map((row) => (row.role === role ? { ...row, [key]: value } : row))
  )
  setPermissionTemplate('custom')
}

export function applyPermissionTemplateFlow(
  template: Exclude<PermTemplate, 'custom'>,
  setPermissionTemplate: (template: PermTemplate) => void,
  setPermissionMatrix: Dispatch<SetStateAction<PermissionRow[]>>
): void {
  setPermissionTemplate(template)
  setPermissionMatrix(clonePermissionRows(PERMISSION_TEMPLATES[template]))
}

export async function persistPermissionMatrixFlow({
  canUseEnterpriseApi,
  enterpriseId,
  permissionMatrix,
  saveSettings,
  setPermissionMatrix,
  setPermissionTemplate,
  showToast,
}: PersistPermissionMatrixFlowArgs): Promise<void> {
  if (!canUseEnterpriseApi || !enterpriseId) {
    showToast('演示环境：已本地保存')
    return
  }

  const res = (await saveSettings(enterpriseId, { permissionMatrix })) as {
    settings?: { permissionMatrix?: Array<Partial<PermissionRow> & { role?: string }> }
  } | null

  if (res?.settings?.permissionMatrix) {
    const matrix = normalizePermissionMatrix(res.settings.permissionMatrix)
    setPermissionMatrix(matrix)
    setPermissionTemplate(detectPermissionTemplate(matrix))
  }

  showToast('权限矩阵已保存')
}
