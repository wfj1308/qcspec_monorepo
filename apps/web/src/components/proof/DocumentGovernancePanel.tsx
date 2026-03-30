import React, { useCallback, useEffect, useMemo, useState } from 'react'
import { Button, Card, VPathDisplay } from '../ui'
import { useProof } from '../../hooks/useApi'
import { useUIStore } from '../../store'

interface DocumentGovernancePanelProps {
  projectUri: string
}

interface DocTreeNode {
  uri: string
  parent_uri?: string
  name?: string
  children?: string[]
  file_count?: number
  children_count?: number
}

interface DocCard {
  proof_id?: string
  proof_hash?: string
  node_uri?: string
  file_name?: string
  mime_type?: string
  file_size?: number
  storage_url?: string
  doc_type?: string
  discipline?: string
  summary?: string
  tags?: string[]
}

function parseJsonObject(input: string): Record<string, unknown> {
  const text = String(input || '').trim()
  if (!text) return {}
  try {
    const value = JSON.parse(text)
    if (value && typeof value === 'object' && !Array.isArray(value)) {
      return value as Record<string, unknown>
    }
  } catch {
    return {}
  }
  return {}
}

function formatSize(bytes: number): string {
  const n = Number(bytes || 0)
  if (!Number.isFinite(n) || n <= 0) return '-'
  if (n >= 1024 * 1024) return `${(n / 1024 / 1024).toFixed(2)} MB`
  if (n >= 1024) return `${(n / 1024).toFixed(1)} KB`
  return `${n} B`
}

export default function DocumentGovernancePanel({ projectUri }: DocumentGovernancePanelProps) {
  const {
    docAutoClassify,
    docTree,
    docCreateNode,
    docAutoGenerateNodes,
    docSearch,
    docRegister,
  } = useProof()
  const { showToast } = useUIStore()

  const [treeLoading, setTreeLoading] = useState(false)
  const [docsLoading, setDocsLoading] = useState(false)
  const [uploading, setUploading] = useState(false)
  const [classifying, setClassifying] = useState(false)

  const [nodes, setNodes] = useState<DocTreeNode[]>([])
  const [selectedNodeUri, setSelectedNodeUri] = useState('')
  const [cards, setCards] = useState<DocCard[]>([])

  const [query, setQuery] = useState('')
  const [tagsInput, setTagsInput] = useState('')
  const [includeDescendants, setIncludeDescendants] = useState(true)

  const [newNodeName, setNewNodeName] = useState('')
  const [newNodeParentUri, setNewNodeParentUri] = useState('')

  const [kmStart, setKmStart] = useState('0')
  const [kmEnd, setKmEnd] = useState('20')
  const [kmStep, setKmStep] = useState('1')
  const [kmLeafName, setKmLeafName] = useState('inspection')

  const [uploadFile, setUploadFile] = useState<File | null>(null)
  const [sourceUtxoId, setSourceUtxoId] = useState('')
  const [excerpt, setExcerpt] = useState('')
  const [docType, setDocType] = useState('')
  const [discipline, setDiscipline] = useState('')
  const [summary, setSummary] = useState('')
  const [uploadTagsInput, setUploadTagsInput] = useState('')
  const [customMetadataRaw, setCustomMetadataRaw] = useState('{}')

  const selectedNode = selectedNodeUri || projectUri

  const nodeMap = useMemo(() => {
    const map = new Map<string, DocTreeNode>()
    for (const n of nodes) {
      if (!n?.uri) continue
      map.set(n.uri, n)
    }
    return map
  }, [nodes])

  const rootUri = useMemo(() => {
    if (nodeMap.has(projectUri)) return projectUri
    const first = nodes.find((n) => n.parent_uri === '' || !n.parent_uri)?.uri
    return first || projectUri
  }, [nodes, nodeMap, projectUri])

  const loadTree = useCallback(async () => {
    if (!projectUri) return
    setTreeLoading(true)
    try {
      const payload = await docTree(projectUri) as { ok?: boolean; nodes?: DocTreeNode[] } | null
      if (payload?.ok && Array.isArray(payload.nodes)) {
        setNodes(payload.nodes)
        const safeDefault = selectedNodeUri && payload.nodes.some((n) => n.uri === selectedNodeUri)
          ? selectedNodeUri
          : (payload.nodes.find((n) => n.uri === projectUri)?.uri || payload.nodes[0]?.uri || projectUri)
        setSelectedNodeUri(safeDefault)
      } else {
        setNodes([])
      }
    } catch {
      showToast('Document tree load failed')
    } finally {
      setTreeLoading(false)
    }
  }, [docTree, projectUri, selectedNodeUri, showToast])

  const loadCards = useCallback(async () => {
    if (!projectUri) return
    setDocsLoading(true)
    try {
      const payload = await docSearch({
        project_uri: projectUri,
        node_uri: selectedNode,
        include_descendants: includeDescendants,
        query: query.trim(),
        tags: tagsInput.split(',').map((x) => x.trim()).filter(Boolean),
        limit: 300,
      }) as { ok?: boolean; cards?: DocCard[] } | null
      if (payload?.ok && Array.isArray(payload.cards)) {
        setCards(payload.cards)
      } else {
        setCards([])
      }
    } catch {
      showToast('Document search failed')
    } finally {
      setDocsLoading(false)
    }
  }, [docSearch, includeDescendants, projectUri, query, selectedNode, showToast, tagsInput])

  const handleAutoClassify = useCallback(async () => {
    if (!uploadFile) return
    setClassifying(true)
    try {
      const payload = await docAutoClassify({
        file_name: uploadFile.name,
        text_excerpt: excerpt.slice(0, 2000),
        mime_type: uploadFile.type || 'application/octet-stream',
      }) as { ok?: boolean; suggestion?: Record<string, unknown> } | null
      const suggestion = payload?.suggestion || {}
      setDocType(String(suggestion.doc_type || docType))
      setDiscipline(String(suggestion.discipline || discipline))
      setSummary(String(suggestion.summary || summary))
      const tags = Array.isArray(suggestion.tags) ? suggestion.tags.map((x) => String(x)) : []
      if (tags.length) setUploadTagsInput(tags.join(', '))
      showToast('AI metadata ready')
    } catch {
      showToast('AI classify failed')
    } finally {
      setClassifying(false)
    }
  }, [discipline, docAutoClassify, docType, excerpt, showToast, summary, uploadFile])

  const handleUpload = useCallback(async () => {
    if (!uploadFile) {
      showToast('Please choose a file')
      return
    }
    if (!sourceUtxoId.trim()) {
      showToast('source_utxo_id is required')
      return
    }
    setUploading(true)
    try {
      const aiMetadata: Record<string, unknown> = {
        doc_type: docType || undefined,
        discipline: discipline || undefined,
        summary: summary || undefined,
        tags: uploadTagsInput.split(',').map((x) => x.trim()).filter(Boolean),
      }
      const payload = await docRegister({
        file: uploadFile,
        project_uri: projectUri,
        source_utxo_id: sourceUtxoId.trim(),
        node_uri: selectedNode,
        text_excerpt: excerpt.slice(0, 2000),
        tags: uploadTagsInput.split(',').map((x) => x.trim()).filter(Boolean),
        ai_metadata: aiMetadata,
        custom_metadata: parseJsonObject(customMetadataRaw),
        auto_classify: false,
      }) as { ok?: boolean; proof_id?: string } | null
      if (!payload?.ok) {
        showToast('Document register failed')
        return
      }
      showToast(`Registered: ${String(payload.proof_id || '-')}`)
      setUploadFile(null)
      setSourceUtxoId('')
      setExcerpt('')
      await Promise.all([loadTree(), loadCards()])
    } catch {
      showToast('Document register failed')
    } finally {
      setUploading(false)
    }
  }, [
    customMetadataRaw,
    discipline,
    docRegister,
    docType,
    excerpt,
    loadCards,
    loadTree,
    projectUri,
    selectedNode,
    showToast,
    summary,
    uploadFile,
    sourceUtxoId,
    uploadTagsInput,
  ])

  const handleCreateNode = useCallback(async () => {
    if (!newNodeName.trim()) {
      showToast('Node name required')
      return
    }
    const parent = newNodeParentUri.trim() || selectedNode || projectUri
    const payload = await docCreateNode({
      project_uri: projectUri,
      parent_uri: parent,
      node_name: newNodeName.trim(),
    }) as { ok?: boolean; node_uri?: string } | null
    if (payload?.ok) {
      setNewNodeName('')
      setNewNodeParentUri('')
      setSelectedNodeUri(String(payload.node_uri || parent))
      await loadTree()
      showToast('Node created')
      return
    }
    showToast('Create node failed')
  }, [docCreateNode, loadTree, newNodeName, newNodeParentUri, projectUri, selectedNode, showToast])

  const handleAutoGenerate = useCallback(async () => {
    const payload = await docAutoGenerateNodes({
      project_uri: projectUri,
      parent_uri: selectedNode || projectUri,
      start_km: Number(kmStart || 0),
      end_km: Number(kmEnd || 0),
      step_km: Number(kmStep || 1),
      leaf_name: kmLeafName || 'inspection',
    }) as { ok?: boolean; created_count?: number } | null
    if (payload?.ok) {
      await loadTree()
      showToast(`Generated ${Number(payload.created_count || 0)} nodes`)
      return
    }
    showToast('Auto-generate failed')
  }, [docAutoGenerateNodes, kmEnd, kmLeafName, kmStart, kmStep, loadTree, projectUri, selectedNode, showToast])

  useEffect(() => {
    if (!projectUri) return
    setSelectedNodeUri(projectUri)
    void loadTree()
  }, [projectUri, loadTree])

  useEffect(() => {
    if (!projectUri || !selectedNode) return
    void loadCards()
  }, [projectUri, selectedNode, loadCards])

  const renderTree = useCallback((uri: string, depth: number): React.ReactNode => {
    const node = nodeMap.get(uri)
    if (!node) return null
    const selected = selectedNode === uri
    const children = Array.isArray(node.children) ? node.children : []
    return (
      <React.Fragment key={uri}>
        <button
          type="button"
          onClick={() => setSelectedNodeUri(uri)}
          style={{
            width: '100%',
            textAlign: 'left',
            border: selected ? '1px solid #93C5FD' : '1px solid transparent',
            background: selected ? '#EFF6FF' : 'transparent',
            color: selected ? '#1D4ED8' : '#334155',
            borderRadius: 8,
            padding: `6px 8px 6px ${8 + depth * 14}px`,
            fontSize: 12,
            cursor: 'pointer',
          }}
        >
          {node.name || uri.split('/').filter(Boolean).pop() || 'node'} ({Number(node.file_count || 0)})
        </button>
        {children.map((childUri) => renderTree(childUri, depth + 1))}
      </React.Fragment>
    )
  }, [nodeMap, selectedNode])

  return (
    <Card title="Sovereign Document Governance" icon="🗂️">
      <VPathDisplay uri={projectUri} />
      <div style={{ display: 'grid', gridTemplateColumns: '320px minmax(0,1fr)', gap: 12 }}>
        <div style={{ border: '1px solid #E2E8F0', borderRadius: 10, padding: 10, display: 'grid', gap: 10 }}>
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
            <div style={{ fontSize: 12, fontWeight: 700, color: '#0F172A' }}>v:// Node Tree</div>
            <Button size="sm" variant="secondary" onClick={() => void loadTree()} disabled={treeLoading}>
              {treeLoading ? 'Loading...' : 'Refresh'}
            </Button>
          </div>
          <div style={{ maxHeight: 260, overflowY: 'auto', border: '1px solid #E2E8F0', borderRadius: 8, padding: 6 }}>
            {treeLoading && <div style={{ fontSize: 12, color: '#64748B' }}>Loading tree...</div>}
            {!treeLoading && !nodes.length && <div style={{ fontSize: 12, color: '#94A3B8' }}>No nodes yet</div>}
            {!treeLoading && !!nodes.length && renderTree(rootUri, 0)}
          </div>

          <div style={{ borderTop: '1px dashed #E2E8F0', paddingTop: 8, display: 'grid', gap: 6 }}>
            <div style={{ fontSize: 12, fontWeight: 700, color: '#0F172A' }}>Create Node</div>
            <input
              value={newNodeName}
              onChange={(e) => setNewNodeName(e.target.value)}
              placeholder="node name"
              style={{ padding: 8, border: '1px solid #CBD5E1', borderRadius: 8 }}
            />
            <input
              value={newNodeParentUri}
              onChange={(e) => setNewNodeParentUri(e.target.value)}
              placeholder={`parent uri (default: ${selectedNode})`}
              style={{ padding: 8, border: '1px solid #CBD5E1', borderRadius: 8 }}
            />
            <Button size="sm" onClick={() => void handleCreateNode()}>Create</Button>
          </div>

          <div style={{ borderTop: '1px dashed #E2E8F0', paddingTop: 8, display: 'grid', gap: 6 }}>
            <div style={{ fontSize: 12, fontWeight: 700, color: '#0F172A' }}>Auto Stake Nodes</div>
            <div style={{ display: 'grid', gridTemplateColumns: 'repeat(3,minmax(0,1fr))', gap: 6 }}>
              <input value={kmStart} onChange={(e) => setKmStart(e.target.value)} placeholder="K start" style={{ padding: 8, border: '1px solid #CBD5E1', borderRadius: 8 }} />
              <input value={kmEnd} onChange={(e) => setKmEnd(e.target.value)} placeholder="K end" style={{ padding: 8, border: '1px solid #CBD5E1', borderRadius: 8 }} />
              <input value={kmStep} onChange={(e) => setKmStep(e.target.value)} placeholder="step" style={{ padding: 8, border: '1px solid #CBD5E1', borderRadius: 8 }} />
            </div>
            <input value={kmLeafName} onChange={(e) => setKmLeafName(e.target.value)} placeholder="leaf name" style={{ padding: 8, border: '1px solid #CBD5E1', borderRadius: 8 }} />
            <Button size="sm" variant="secondary" onClick={() => void handleAutoGenerate()}>Generate K Nodes</Button>
          </div>
        </div>

        <div style={{ border: '1px solid #E2E8F0', borderRadius: 10, padding: 10, display: 'grid', gap: 10 }}>
          <div style={{ display: 'grid', gap: 8, borderBottom: '1px dashed #E2E8F0', paddingBottom: 8 }}>
            <div style={{ display: 'grid', gridTemplateColumns: 'minmax(0,1fr) 180px 120px auto', gap: 8 }}>
              <input value={query} onChange={(e) => setQuery(e.target.value)} placeholder="Search text" style={{ padding: 8, border: '1px solid #CBD5E1', borderRadius: 8 }} />
              <input value={tagsInput} onChange={(e) => setTagsInput(e.target.value)} placeholder="tags: drawing,bridge" style={{ padding: 8, border: '1px solid #CBD5E1', borderRadius: 8 }} />
              <label style={{ display: 'inline-flex', alignItems: 'center', gap: 6, fontSize: 12, color: '#475569' }}>
                <input type="checkbox" checked={includeDescendants} onChange={(e) => setIncludeDescendants(e.target.checked)} />
                include children
              </label>
              <Button size="sm" onClick={() => void loadCards()} disabled={docsLoading}>{docsLoading ? 'Searching...' : 'Search'}</Button>
            </div>
            <div style={{ fontSize: 12, color: '#64748B', wordBreak: 'break-all' }}>
              Current node: {selectedNode}
            </div>
          </div>

          <div style={{ borderBottom: '1px dashed #E2E8F0', paddingBottom: 8, display: 'grid', gap: 8 }}>
            <div style={{ fontSize: 12, fontWeight: 700, color: '#0F172A' }}>Upload + AI Pre-review</div>
            <input
              type="file"
              onChange={async (e) => {
                const f = e.target.files?.[0] || null
                setUploadFile(f)
                if (!f) return
                try {
                  const text = await f.slice(0, 8192).text()
                  setExcerpt(text.slice(0, 2000))
                } catch {
                  setExcerpt('')
                }
              }}
            />
            <textarea
              value={excerpt}
              onChange={(e) => setExcerpt(e.target.value)}
              placeholder="text excerpt (optional)"
              style={{ minHeight: 68, border: '1px solid #CBD5E1', borderRadius: 8, padding: 8, resize: 'vertical' }}
            />
            <input
              value={sourceUtxoId}
              onChange={(e) => setSourceUtxoId(e.target.value)}
              placeholder="source UTXO ID (required)"
              style={{ padding: 8, border: '1px solid #CBD5E1', borderRadius: 8 }}
            />
            <div style={{ display: 'grid', gridTemplateColumns: 'repeat(3,minmax(0,1fr))', gap: 8 }}>
              <input value={docType} onChange={(e) => setDocType(e.target.value)} placeholder="doc_type" style={{ padding: 8, border: '1px solid #CBD5E1', borderRadius: 8 }} />
              <input value={discipline} onChange={(e) => setDiscipline(e.target.value)} placeholder="discipline" style={{ padding: 8, border: '1px solid #CBD5E1', borderRadius: 8 }} />
              <input value={uploadTagsInput} onChange={(e) => setUploadTagsInput(e.target.value)} placeholder="tags comma separated" style={{ padding: 8, border: '1px solid #CBD5E1', borderRadius: 8 }} />
            </div>
            <input value={summary} onChange={(e) => setSummary(e.target.value)} placeholder="summary" style={{ padding: 8, border: '1px solid #CBD5E1', borderRadius: 8 }} />
            <textarea
              value={customMetadataRaw}
              onChange={(e) => setCustomMetadataRaw(e.target.value)}
              placeholder='custom metadata JSON, e.g. {"rev":"A1","drawing_no":"D-403"}'
              style={{ minHeight: 54, border: '1px solid #CBD5E1', borderRadius: 8, padding: 8, resize: 'vertical', fontFamily: 'monospace', fontSize: 12 }}
            />
            <div style={{ display: 'flex', gap: 8 }}>
              <Button size="sm" variant="secondary" onClick={() => void handleAutoClassify()} disabled={!uploadFile || classifying}>
                {classifying ? 'Classifying...' : 'AI Suggest'}
              </Button>
              <Button size="sm" onClick={() => void handleUpload()} disabled={!uploadFile || uploading}>
                {uploading ? 'Registering...' : 'Register Document'}
              </Button>
            </div>
          </div>

          <div style={{ maxHeight: 420, overflowY: 'auto', display: 'grid', gap: 8 }}>
            {docsLoading && <div style={{ fontSize: 12, color: '#64748B' }}>Loading documents...</div>}
            {!docsLoading && !cards.length && <div style={{ fontSize: 12, color: '#94A3B8' }}>No documents in this node scope</div>}
            {!docsLoading && cards.map((card, idx) => (
              <div key={String(card.proof_id || `${card.file_name || 'doc'}-${idx}`)} style={{ border: '1px solid #E2E8F0', borderRadius: 8, padding: 10, background: '#F8FAFC' }}>
                <div style={{ display: 'flex', justifyContent: 'space-between', gap: 8 }}>
                  <div style={{ fontSize: 12, fontWeight: 700, color: '#0F172A' }}>
                    {card.file_name || '-'}
                  </div>
                  <div style={{ fontSize: 11, color: '#64748B' }}>{formatSize(Number(card.file_size || 0))}</div>
                </div>
                <div style={{ marginTop: 2, fontSize: 12, color: '#475569', wordBreak: 'break-all' }}>
                  {card.doc_type || '-'} / {card.discipline || '-'} / {card.mime_type || '-'}
                </div>
                <div style={{ marginTop: 2, fontSize: 12, color: '#64748B' }}>{card.summary || '-'}</div>
                <div style={{ marginTop: 4, fontSize: 12, color: '#334155', wordBreak: 'break-all' }}>
                  Node: {card.node_uri || '-'}
                </div>
                <div style={{ marginTop: 4, display: 'flex', flexWrap: 'wrap', gap: 6 }}>
                  {(card.tags || []).map((tag) => (
                    <span key={tag} style={{ fontSize: 11, padding: '2px 6px', borderRadius: 999, background: '#EEF2FF', color: '#3730A3' }}>
                      {tag}
                    </span>
                  ))}
                </div>
                <div style={{ marginTop: 6, display: 'grid', gridTemplateColumns: '1fr auto auto', gap: 8, alignItems: 'center' }}>
                  <code style={{ fontSize: 11, color: '#0F172A', wordBreak: 'break-all' }}>{card.proof_hash || '-'}</code>
                  <Button
                    size="sm"
                    variant="secondary"
                    onClick={() => {
                      const text = String(card.proof_hash || '')
                      if (!text) return
                      navigator.clipboard.writeText(text).then(() => showToast('Proof hash copied')).catch(() => showToast('Copy failed'))
                    }}
                  >
                    Copy Hash
                  </Button>
                  <Button
                    size="sm"
                    onClick={() => {
                      const url = String(card.storage_url || '')
                      if (!url) return
                      window.open(url, '_blank', 'noopener,noreferrer')
                    }}
                    disabled={!card.storage_url}
                  >
                    Open File
                  </Button>
                </div>
              </div>
            ))}
          </div>
        </div>
      </div>
    </Card>
  )
}
