import React from 'react'
import type {
  PermTemplate,
  PermissionKey,
  PermissionRole,
  PermissionRow,
} from '../../app/appShellShared'

interface PermissionTreeRow {
  role: string
  granted: string
}

interface PermissionsPanelProps {
  permissionTemplate: PermTemplate
  permissionMatrix: PermissionRow[]
  permissionColumns: Array<{ key: PermissionKey; label: string }>
  permissionRoleLabel: Record<PermissionRole, string>
  permissionTreeRoot: string
  permissionTreeRows: PermissionTreeRow[]
  onApplyTemplate: (template: Exclude<PermTemplate, 'custom'>) => void
  onUpdateCell: (role: PermissionRole, key: PermissionKey, checked: boolean) => void
  onSaveMatrix: () => void
}

export default function PermissionsPanel({
  permissionTemplate,
  permissionMatrix,
  permissionColumns,
  permissionRoleLabel,
  permissionTreeRoot,
  permissionTreeRows,
  onApplyTemplate,
  onUpdateCell,
  onSaveMatrix,
}: PermissionsPanelProps) {
  return (
    <div className="form-card">
      <div className="form-card-title">🔐 权限管理矩阵</div>
      <div className="perm-toolbar">
        {(['standard', 'strict', 'open'] as const).map((template) => (
          <button
            key={template}
            className={permissionTemplate === template ? 'btn-primary' : 'btn-secondary'}
            style={{ flex: 'none', padding: '8px 12px' }}
            onClick={() => onApplyTemplate(template)}
          >
            {template}
          </button>
        ))}
        <span style={{ fontSize: 12, color: '#64748B' }}>
          当前模板：<strong>{permissionTemplate}</strong>（可继续微调）
        </span>
      </div>
      <div className="perm-layout">
        <div>
          <table className="perm-table">
            <thead>
              <tr>
                {['角色', ...permissionColumns.map((column) => column.label)].map((header) => (
                  <th key={header}>{header}</th>
                ))}
              </tr>
            </thead>
            <tbody>
              {permissionMatrix.map((row) => (
                <tr key={row.role}>
                  <td>
                    <span className={`perm-role perm-role-${row.role.toLowerCase()}`}>
                      {permissionRoleLabel[row.role]}
                    </span>
                  </td>
                  {permissionColumns.map((column) => (
                    <td key={`${row.role}-${column.key}`}>
                      <input
                        type="checkbox"
                        checked={row[column.key]}
                        onChange={(e) => onUpdateCell(row.role, column.key, e.target.checked)}
                      />
                    </td>
                  ))}
                </tr>
              ))}
            </tbody>
          </table>
          <div style={{ marginTop: 10 }}>
            <button className="btn-primary" style={{ flex: 'none' }} onClick={onSaveMatrix}>
              保存权限矩阵
            </button>
          </div>
        </div>
        <div>
          <div className="node-tree" style={{ marginTop: 0 }}>
            <div style={{ fontSize: 12, color: '#475569', letterSpacing: 1, marginBottom: 6 }}>
              V:// 节点权限结构 · 实时预览
            </div>
            <div>{permissionTreeRoot}</div>
            {permissionTreeRows.map((row, idx) => (
              <div key={`${row.role}-${idx}`} className="node-tree-sub">
                {idx === permissionTreeRows.length - 1 ? '└' : '├'}─ {row.role.toLowerCase()}/{' '}
                <span style={{ color: '#64748B' }}>{row.granted}</span>
              </div>
            ))}
          </div>
          <div style={{ fontSize: 12, color: '#64748B', lineHeight: 1.6, marginTop: 8 }}>
            修改矩阵后节点树立即更新。保存后写入 v:// DTORole 配置。
          </div>
        </div>
      </div>
    </div>
  )
}
