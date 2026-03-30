import React, { useCallback, useEffect, useMemo, useState } from 'react'
import { Button, Card, Input, Toast, VPathDisplay } from '../components/ui'
import { useProof } from '../hooks/useApi'
import { useUIStore } from '../store'

export default function SpecDictEditorPage({ specDictKey }: { specDictKey: string }) {
  const normalizedKey = useMemo(() => String(specDictKey || '').trim(), [specDictKey])
  const { getSpecDict, saveSpecDict } = useProof()
  const { toastMsg, showToast } = useUIStore()

  const [loading, setLoading] = useState(false)
  const [title, setTitle] = useState('')
  const [version, setVersion] = useState('v1.0')
  const [authority, setAuthority] = useState('')
  const [specUri, setSpecUri] = useState('')
  const [itemsText, setItemsText] = useState('{}')

  const load = useCallback(async () => {
    if (!normalizedKey) return
    setLoading(true)
    try {
      const res = await getSpecDict(normalizedKey) as {
        ok?: boolean
        title?: string
        version?: string
        authority?: string
        spec_uri?: string
        items?: unknown
      } | null
      if (!res?.ok) {
        showToast('SpecDict not found. Opened in create mode.')
        return
      }
      setTitle(String(res.title || ''))
      setVersion(String(res.version || 'v1.0'))
      setAuthority(String(res.authority || ''))
      setSpecUri(String(res.spec_uri || ''))
      setItemsText(JSON.stringify(res.items || {}, null, 2))
    } finally {
      setLoading(false)
    }
  }, [getSpecDict, normalizedKey, showToast])

  useEffect(() => {
    load()
  }, [load])

  const onSave = async () => {
    let parsed: Record<string, unknown> = {}
    try {
      parsed = JSON.parse(itemsText || '{}')
    } catch {
      showToast('Invalid JSON in items')
      return
    }
    const res = await saveSpecDict({
      spec_dict_key: normalizedKey,
      title,
      version,
      authority,
      spec_uri: specUri,
      items: parsed,
      metadata: {
        source: 'specdict_editor_ui',
      },
      is_active: true,
    }) as { ok?: boolean; updated_at?: string } | null
    if (!res?.ok) {
      showToast('Failed to save SpecDict')
      return
    }
    showToast(`SpecDict saved${res.updated_at ? ` (${new Date(res.updated_at).toLocaleString('zh-CN')})` : ''}`)
    await load()
  }

  return (
    <div style={{ maxWidth: 1100, margin: '0 auto', padding: 20, paddingBottom: 80 }}>
      <Card title={`SpecDict Editor · ${normalizedKey}`} icon="DOC">
        <VPathDisplay uri={`v://specdict/${normalizedKey}`} />
        <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 10, marginBottom: 10 }}>
          <Input label="Title" value={title} onChange={setTitle} />
          <Input label="Version" value={version} onChange={setVersion} />
          <Input label="Authority" value={authority} onChange={setAuthority} />
          <Input label="Spec URI" value={specUri} onChange={setSpecUri} />
        </div>
        <div style={{ fontSize: 12, color: '#64748B', marginBottom: 6 }}>items (JSON)</div>
        <textarea
          value={itemsText}
          onChange={(e) => setItemsText(e.target.value)}
          rows={22}
          style={{
            width: '100%',
            border: '1px solid #E2E8F0',
            borderRadius: 8,
            padding: 10,
            fontSize: 12,
            fontFamily: 'JetBrains Mono, monospace',
            resize: 'vertical',
          }}
        />
      </Card>

      <div
        style={{
          position: 'fixed',
          left: 0,
          right: 0,
          bottom: 0,
          borderTop: '1px solid #E2E8F0',
          background: '#FFFFFF',
          padding: '10px 16px',
          display: 'flex',
          justifyContent: 'center',
          gap: 8,
          zIndex: 99,
        }}
      >
        <Button variant="secondary" onClick={load} disabled={loading}>
          {loading ? 'Loading...' : 'Refresh'}
        </Button>
        <Button onClick={onSave}>Save SpecDict</Button>
        <Button variant="ghost" onClick={() => { if (typeof window !== 'undefined') window.location.href = '/' }}>
          Back to Console
        </Button>
      </div>
      <Toast message={toastMsg} />
    </div>
  )
}
