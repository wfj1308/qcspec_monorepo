import React, { useMemo, useState } from 'react'
import { useSignPegApi } from '../hooks/api/signpeg'

type MemberRow = {
  executor_id: string
  executor_uri: string
  name: string
  executor_type: string
  status: string
  role_keys?: string[]
  project_uris?: string[]
}

function splitTokens(raw: string): string[] {
  return String(raw || '')
    .split(/[,\n]/g)
    .map((item) => item.trim())
    .filter(Boolean)
}

export default function ExecutorAdminPage() {
  const { loading, getOrgMembers, createOrgMember, updateOrgMember, disableOrgMember } = useSignPegApi()
  const [orgUri, setOrgUri] = useState('v://cn.zhongbei/')
  const [membersLoading, setMembersLoading] = useState(false)
  const [members, setMembers] = useState<MemberRow[]>([])
  const [message, setMessage] = useState('')

  const [keyword, setKeyword] = useState('')
  const [typeFilter, setTypeFilter] = useState('all')
  const [statusFilter, setStatusFilter] = useState('all')
  const [selectedUris, setSelectedUris] = useState<string[]>([])

  const [newName, setNewName] = useState('')
  const [newRoles, setNewRoles] = useState('constructor')
  const [newProjects, setNewProjects] = useState('')

  const [editRoles, setEditRoles] = useState('')
  const [editProjects, setEditProjects] = useState('')
  const [editStatus, setEditStatus] = useState('available')

  const selectedMember = useMemo(
    () => (selectedUris.length === 1 ? members.find((item) => item.executor_uri === selectedUris[0]) ?? null : null),
    [members, selectedUris],
  )

  const filteredMembers = useMemo(() => {
    const q = keyword.trim().toLowerCase()
    return members.filter((item) => {
      if (typeFilter !== 'all' && item.executor_type !== typeFilter) return false
      if (statusFilter !== 'all' && item.status !== statusFilter) return false
      if (!q) return true
      return (
        item.name.toLowerCase().includes(q) ||
        item.executor_uri.toLowerCase().includes(q) ||
        (item.role_keys || []).join(',').toLowerCase().includes(q)
      )
    })
  }, [keyword, members, statusFilter, typeFilter])

  const loadMembers = async () => {
    const org = orgUri.trim()
    if (!org) return
    setMembersLoading(true)
    setMessage('')
    try {
      const out = await getOrgMembers(org)
      const rows = Array.isArray(out?.members) ? (out.members as MemberRow[]) : []
      setMembers(rows)
      setSelectedUris([])
    } finally {
      setMembersLoading(false)
    }
  }

  const onCreateMember = async () => {
    const org = orgUri.trim()
    const name = newName.trim()
    if (!org || !name) return
    const out = await createOrgMember(org, {
      name,
      executor_type: 'human',
      role_keys: splitTokens(newRoles),
      project_uris: splitTokens(newProjects),
      certificates: [],
      skills: [],
    })
    if (out?.ok) {
      setMessage(`Member created: ${out.member_executor_uri || name}`)
      setNewName('')
      await loadMembers()
    }
  }

  const onPick = (uri: string) => {
    setSelectedUris((prev) => {
      if (prev.includes(uri)) return prev.filter((item) => item !== uri)
      return [...prev, uri]
    })
  }

  const onSelectAllFiltered = () => {
    setSelectedUris(filteredMembers.map((item) => item.executor_uri))
  }

  const onClearSelection = () => setSelectedUris([])

  const onLoadEditFromSelected = () => {
    if (!selectedMember) return
    setEditRoles((selectedMember.role_keys || []).join(','))
    setEditProjects((selectedMember.project_uris || []).join(','))
    setEditStatus(selectedMember.status || 'available')
  }

  const onUpdateSelected = async () => {
    const org = orgUri.trim()
    if (!org || !selectedMember) return
    const out = await updateOrgMember(org, selectedMember.executor_uri, {
      role_keys: splitTokens(editRoles),
      project_uris: splitTokens(editProjects),
      status: editStatus as any,
    })
    if (out?.ok) {
      setMessage(`Member updated: ${selectedMember.executor_uri}`)
      await loadMembers()
    }
  }

  const onBulkDisable = async () => {
    const org = orgUri.trim()
    if (!org || selectedUris.length === 0) return
    for (const uri of selectedUris) {
      // Keep sequential calls to make failures easy to trace.
      await disableOrgMember(org, uri, 'bulk_disable_by_org_admin')
    }
    setMessage(`Bulk disabled: ${selectedUris.length} member(s)`)
    await loadMembers()
  }

  return (
    <div style={{ padding: 20 }}>
      <h2 style={{ marginBottom: 12 }}>Executor Admin</h2>

      <div style={{ display: 'grid', gap: 10, background: '#fff', border: '1px solid #e2e8f0', borderRadius: 10, padding: 12, marginBottom: 12 }}>
        <div style={{ display: 'flex', gap: 8, alignItems: 'center', flexWrap: 'wrap' }}>
          <input
            placeholder="org uri"
            value={orgUri}
            onChange={(e) => setOrgUri(e.target.value)}
            style={{ minWidth: 320, flex: 1, padding: '8px 10px', border: '1px solid #cbd5e1', borderRadius: 8 }}
          />
          <button type="button" onClick={loadMembers} disabled={membersLoading}>
            {membersLoading ? 'loading...' : 'load members'}
          </button>
        </div>
        <div style={{ display: 'flex', gap: 8, alignItems: 'center', flexWrap: 'wrap' }}>
          <input
            placeholder="search name/uri/role"
            value={keyword}
            onChange={(e) => setKeyword(e.target.value)}
            style={{ minWidth: 260, padding: '8px 10px', border: '1px solid #cbd5e1', borderRadius: 8 }}
          />
          <select value={typeFilter} onChange={(e) => setTypeFilter(e.target.value)} style={{ padding: '8px 10px', borderRadius: 8 }}>
            <option value="all">type: all</option>
            <option value="human">human</option>
            <option value="machine">machine</option>
            <option value="tool">tool</option>
            <option value="ai">ai</option>
          </select>
          <select value={statusFilter} onChange={(e) => setStatusFilter(e.target.value)} style={{ padding: '8px 10px', borderRadius: 8 }}>
            <option value="all">status: all</option>
            <option value="available">available</option>
            <option value="busy">busy</option>
            <option value="offline">offline</option>
            <option value="in_use">in_use</option>
            <option value="maintenance">maintenance</option>
            <option value="suspended">suspended</option>
          </select>
          <button type="button" onClick={onSelectAllFiltered} disabled={filteredMembers.length === 0}>select all filtered</button>
          <button type="button" onClick={onClearSelection} disabled={selectedUris.length === 0}>clear selection</button>
          <button type="button" onClick={onBulkDisable} disabled={selectedUris.length === 0 || loading} style={{ color: '#b91c1c' }}>
            bulk disable
          </button>
        </div>
      </div>

      <div style={{ display: 'grid', gridTemplateColumns: '1fr 360px', gap: 12 }}>
        <div style={{ background: '#fff', border: '1px solid #e2e8f0', borderRadius: 10, padding: 12, overflowX: 'auto' }}>
          <div style={{ marginBottom: 8, fontWeight: 600 }}>
            Members ({filteredMembers.length}) / Selected ({selectedUris.length})
          </div>
          <table style={{ width: '100%', borderCollapse: 'collapse', fontSize: 13 }}>
            <thead>
              <tr style={{ background: '#f8fafc' }}>
                <th style={{ textAlign: 'left', padding: '8px 6px', borderBottom: '1px solid #e2e8f0' }}>Sel</th>
                <th style={{ textAlign: 'left', padding: '8px 6px', borderBottom: '1px solid #e2e8f0' }}>Name</th>
                <th style={{ textAlign: 'left', padding: '8px 6px', borderBottom: '1px solid #e2e8f0' }}>Type</th>
                <th style={{ textAlign: 'left', padding: '8px 6px', borderBottom: '1px solid #e2e8f0' }}>Status</th>
                <th style={{ textAlign: 'left', padding: '8px 6px', borderBottom: '1px solid #e2e8f0' }}>Roles</th>
                <th style={{ textAlign: 'left', padding: '8px 6px', borderBottom: '1px solid #e2e8f0' }}>Projects</th>
              </tr>
            </thead>
            <tbody>
              {filteredMembers.map((item) => {
                const checked = selectedUris.includes(item.executor_uri)
                return (
                  <tr key={item.executor_uri} style={{ background: checked ? '#eff6ff' : 'transparent' }}>
                    <td style={{ padding: '8px 6px', borderBottom: '1px solid #f1f5f9' }}>
                      <input type="checkbox" checked={checked} onChange={() => onPick(item.executor_uri)} />
                    </td>
                    <td style={{ padding: '8px 6px', borderBottom: '1px solid #f1f5f9' }}>
                      <div style={{ fontWeight: 600 }}>{item.name}</div>
                      <div style={{ fontFamily: 'var(--mono)', color: '#64748b', fontSize: 12 }}>{item.executor_uri}</div>
                    </td>
                    <td style={{ padding: '8px 6px', borderBottom: '1px solid #f1f5f9' }}>{item.executor_type}</td>
                    <td style={{ padding: '8px 6px', borderBottom: '1px solid #f1f5f9' }}>{item.status}</td>
                    <td style={{ padding: '8px 6px', borderBottom: '1px solid #f1f5f9' }}>{(item.role_keys || []).join(', ') || '-'}</td>
                    <td style={{ padding: '8px 6px', borderBottom: '1px solid #f1f5f9' }}>{(item.project_uris || []).join(', ') || '-'}</td>
                  </tr>
                )
              })}
            </tbody>
          </table>
        </div>

        <div style={{ display: 'grid', gap: 12, alignContent: 'start' }}>
          <div style={{ background: '#fff', border: '1px solid #e2e8f0', borderRadius: 10, padding: 12 }}>
            <div style={{ marginBottom: 8, fontWeight: 600 }}>Create member</div>
            <input
              placeholder="member name"
              value={newName}
              onChange={(e) => setNewName(e.target.value)}
              style={{ width: '100%', marginBottom: 8, padding: '8px 10px', border: '1px solid #cbd5e1', borderRadius: 8 }}
            />
            <input
              placeholder="roles (comma)"
              value={newRoles}
              onChange={(e) => setNewRoles(e.target.value)}
              style={{ width: '100%', marginBottom: 8, padding: '8px 10px', border: '1px solid #cbd5e1', borderRadius: 8 }}
            />
            <input
              placeholder="projects (comma)"
              value={newProjects}
              onChange={(e) => setNewProjects(e.target.value)}
              style={{ width: '100%', marginBottom: 8, padding: '8px 10px', border: '1px solid #cbd5e1', borderRadius: 8 }}
            />
            <button type="button" onClick={onCreateMember} disabled={!newName.trim() || loading}>create</button>
          </div>

          <div style={{ background: '#fff', border: '1px solid #e2e8f0', borderRadius: 10, padding: 12 }}>
            <div style={{ marginBottom: 8, fontWeight: 600 }}>Update selected member</div>
            <div style={{ fontSize: 12, color: '#64748b', marginBottom: 8 }}>
              {selectedMember ? selectedMember.executor_uri : 'Select exactly one member from table'}
            </div>
            <button type="button" onClick={onLoadEditFromSelected} disabled={!selectedMember} style={{ marginBottom: 8 }}>
              load selected fields
            </button>
            <input
              placeholder="roles (comma)"
              value={editRoles}
              onChange={(e) => setEditRoles(e.target.value)}
              style={{ width: '100%', marginBottom: 8, padding: '8px 10px', border: '1px solid #cbd5e1', borderRadius: 8 }}
            />
            <input
              placeholder="projects (comma)"
              value={editProjects}
              onChange={(e) => setEditProjects(e.target.value)}
              style={{ width: '100%', marginBottom: 8, padding: '8px 10px', border: '1px solid #cbd5e1', borderRadius: 8 }}
            />
            <select value={editStatus} onChange={(e) => setEditStatus(e.target.value)} style={{ width: '100%', marginBottom: 8, padding: '8px 10px', borderRadius: 8 }}>
              <option value="available">available</option>
              <option value="busy">busy</option>
              <option value="offline">offline</option>
              <option value="in_use">in_use</option>
              <option value="maintenance">maintenance</option>
              <option value="suspended">suspended</option>
            </select>
            <button type="button" onClick={onUpdateSelected} disabled={!selectedMember || loading}>update</button>
          </div>
        </div>
      </div>

      {message && <div style={{ marginTop: 10, color: '#0f766e' }}>{message}</div>}
    </div>
  )
}

