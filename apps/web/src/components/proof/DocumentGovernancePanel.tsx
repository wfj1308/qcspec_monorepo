import React, { useCallback, useEffect, useMemo, useState } from 'react'
import { Button, Card, VPathDisplay } from '../ui'
import { useProof } from '../../hooks/api/proof'
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

function sectionTitle(text: string) {
  return <div style={{ fontSize: 13, fontWeight: 700, color: '#0F172A' }}>{text}</div>
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
      showToast('文档节点树加载失败')
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
      showToast('文档检索失败')
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
      showToast('AI 已完成文档预分类')
    } catch {
      showToast('AI 预分类失败')
    } finally {
      setClassifying(false)
    }
  }, [discipline, docAutoClassify, docType, excerpt, showToast, summary, uploadFile])

  const handleUpload = useCallback(async () => {
    if (!uploadFile) {
      showToast('请先选择文件')
      return
    }
    if (!sourceUtxoId.trim()) {
      showToast('来源 UTXO ID 必填')
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
        showToast('文档登记失败')
        return
      }
      showToast(`文档登记成功：${String(payload.proof_id || '-')}`)
      setUploadFile(null)
      setSourceUtxoId('')
      setExcerpt('')
      await Promise.all([loadTree(), loadCards()])
    } catch {
      showToast('文档登记失败')
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
      showToast('请输入节点名称')
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
      showToast('节点创建成功')
      return
    }
    showToast('节点创建失败')
  }, [docCreateNode, loadTree, newNodeName, newNodeParentUri, projectUri, selectedNode, showToast])

  const handleAutoGenerate = useCallback(async () => {
    const start = Number(kmStart || 0)
    const end = Number(kmEnd || 0)
    const step = Number(kmStep || 1)
    if (!Number.isFinite(start) || !Number.isFinite(end) || !Number.isFinite(step) || step <= 0) {
      showToast('里程参数不合法')
      return
    }
    if (end < start) {
      showToast('结束里程不能小于开始里程')
      return
    }
    const payload = await docAutoGenerateNodes({
      project_uri: projectUri,
      parent_uri: selectedNode || projectUri,
      start_km: start,
      end_km: end,
      step_km: step,
      leaf_name: kmLeafName || 'inspection',
    }) as { ok?: boolean; created_count?: number } | null
    if (payload?.ok) {
      await loadTree()
      showToast(`已生成 ${Number(payload.created_count || 0)} 个节点`)
      return
    }
    showToast('自动生成节点失败')
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
    <Card title="Proof 文档治理" icon="📁">
      <VPathDisplay uri={projectUri} />

      <div style={{ display: 'grid', gridTemplateColumns: '320px minmax(0,1fr)', gap: 12 }}>
        <div style={{ border: '1px solid #E2E8F0', borderRadius: 10, padding: 10, display: 'grid', gap: 10 }}>
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
            {sectionTitle('v:// 节点树')}
            <Button size="sm" variant="secondary" onClick={() => void loadTree()} disabled={treeLoading}>
              {treeLoading ? '刷新中...' : '刷新'}
            </Button>
          </div>
          <div style={{ maxHeight: 260, overflowY: 'auto', border: '1px solid #E2E8F0', borderRadius: 8, padding: 6 }}>
            {treeLoading && <div style={{ fontSize: 12, color: '#64748B' }}>节点树加载中...</div>}
            {!treeLoading && !nodes.length && <div style={{ fontSize: 12, color: '#94A3B8' }}>暂无节点</div>}
            {!treeLoading && !!nodes.length && renderTree(rootUri, 0)}
          </div>

          <div style={{ borderTop: '1px dashed #E2E8F0', paddingTop: 8, display: 'grid', gap: 6 }}>
            {sectionTitle('新建节点')}
            <input
              value={newNodeName}
              onChange={(e) => setNewNodeName(e.target.value)}
              placeholder="节点名称"
              style={{ padding: 8, border: '1px solid #CBD5E1', borderRadius: 8 }}
            />
            <input
              value={newNodeParentUri}
              onChange={(e) => setNewNodeParentUri(e.target.value)}
              placeholder={`父节点 URI（默认当前节点）`}
              style={{ padding: 8, border: '1px solid #CBD5E1', borderRadius: 8 }}
            />
            <Button size="sm" onClick={() => void handleCreateNode()}>创建节点</Button>
          </div>

          <div style={{ borderTop: '1px dashed #E2E8F0', paddingTop: 8, display: 'grid', gap: 6 }}>
            {sectionTitle('按里程自动生成节点')}
            <div style={{ display: 'grid', gridTemplateColumns: 'repeat(3,minmax(0,1fr))', gap: 6 }}>
              <input value={kmStart} onChange={(e) => setKmStart(e.target.value)} placeholder="起始里程 km" style={{ padding: 8, border: '1px solid #CBD5E1', borderRadius: 8 }} />
              <input value={kmEnd} onChange={(e) => setKmEnd(e.target.value)} placeholder="结束里程 km" style={{ padding: 8, border: '1px solid #CBD5E1', borderRadius: 8 }} />
              <input value={kmStep} onChange={(e) => setKmStep(e.target.value)} placeholder="步长 km" style={{ padding: 8, border: '1px solid #CBD5E1', borderRadius: 8 }} />
            </div>
            <input value={kmLeafName} onChange={(e) => setKmLeafName(e.target.value)} placeholder="叶子节点名（默认 inspection）" style={{ padding: 8, border: '1px solid #CBD5E1', borderRadius: 8 }} />
            <Button size="sm" variant="secondary" onClick={() => void handleAutoGenerate()}>生成里程节点</Button>
          </div>
        </div>

        <div style={{ border: '1px solid #E2E8F0', borderRadius: 10, padding: 10, display: 'grid', gap: 10 }}>
          <div style={{ display: 'grid', gap: 8, borderBottom: '1px dashed #E2E8F0', paddingBottom: 8 }}>
            {sectionTitle('检索文档')}
            <div style={{ display: 'grid', gridTemplateColumns: 'minmax(0,1fr) 180px 120px auto', gap: 8 }}>
              <input value={query} onChange={(e) => setQuery(e.target.value)} placeholder="搜索关键词（标题/摘要/类型）" style={{ padding: 8, border: '1px solid #CBD5E1', borderRadius: 8 }} />
              <input value={tagsInput} onChange={(e) => setTagsInput(e.target.value)} placeholder="标签，如 drawing,bridge" style={{ padding: 8, border: '1px solid #CBD5E1', borderRadius: 8 }} />
              <label style={{ display: 'inline-flex', alignItems: 'center', gap: 6, fontSize: 12, color: '#475569' }}>
                <input type="checkbox" checked={includeDescendants} onChange={(e) => setIncludeDescendants(e.target.checked)} />
                包含子节点
              </label>
              <Button size="sm" onClick={() => void loadCards()} disabled={docsLoading}>{docsLoading ? '检索中...' : '检索'}</Button>
            </div>
            <div style={{ fontSize: 12, color: '#64748B', wordBreak: 'break-all' }}>
              当前节点：{selectedNode}
            </div>
          </div>

          <div style={{ borderBottom: '1px dashed #E2E8F0', paddingBottom: 8, display: 'grid', gap: 8 }}>
            {sectionTitle('上传并登记文档')}
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
              placeholder="文档片段（可选，用于 AI 预分类）"
              style={{ minHeight: 68, border: '1px solid #CBD5E1', borderRadius: 8, padding: 8, resize: 'vertical' }}
            />
            <input
              value={sourceUtxoId}
              onChange={(e) => setSourceUtxoId(e.target.value)}
              placeholder="来源 UTXO ID（必填）"
              style={{ padding: 8, border: '1px solid #CBD5E1', borderRadius: 8 }}
            />
            <div style={{ display: 'grid', gridTemplateColumns: 'repeat(3,minmax(0,1fr))', gap: 8 }}>
              <input value={docType} onChange={(e) => setDocType(e.target.value)} placeholder="文档类型（doc_type）" style={{ padding: 8, border: '1px solid #CBD5E1', borderRadius: 8 }} />
              <input value={discipline} onChange={(e) => setDiscipline(e.target.value)} placeholder="专业（discipline）" style={{ padding: 8, border: '1px solid #CBD5E1', borderRadius: 8 }} />
              <input value={uploadTagsInput} onChange={(e) => setUploadTagsInput(e.target.value)} placeholder="标签，逗号分隔" style={{ padding: 8, border: '1px solid #CBD5E1', borderRadius: 8 }} />
            </div>
            <input value={summary} onChange={(e) => setSummary(e.target.value)} placeholder="摘要（summary）" style={{ padding: 8, border: '1px solid #CBD5E1', borderRadius: 8 }} />
            <textarea
              value={customMetadataRaw}
              onChange={(e) => setCustomMetadataRaw(e.target.value)}
              placeholder='自定义 JSON 元数据，例如 {"rev":"A1","drawing_no":"D-403"}'
              style={{ minHeight: 54, border: '1px solid #CBD5E1', borderRadius: 8, padding: 8, resize: 'vertical', fontFamily: 'monospace', fontSize: 12 }}
            />
            <div style={{ display: 'flex', gap: 8 }}>
              <Button size="sm" variant="secondary" onClick={() => void handleAutoClassify()} disabled={!uploadFile || classifying}>
                {classifying ? 'AI 分析中...' : 'AI 预填元数据'}
              </Button>
              <Button size="sm" onClick={() => void handleUpload()} disabled={!uploadFile || uploading}>
                {uploading ? '登记中...' : '登记文档'}
              </Button>
            </div>
          </div>

          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
            {sectionTitle('文档列表')}
            <div style={{ fontSize: 12, color: '#64748B' }}>共 {cards.length} 条</div>
          </div>
          <div style={{ maxHeight: 420, overflowY: 'auto', display: 'grid', gap: 8 }}>
            {docsLoading && <div style={{ fontSize: 12, color: '#64748B' }}>文档加载中...</div>}
            {!docsLoading && !cards.length && <div style={{ fontSize: 12, color: '#94A3B8' }}>当前节点范围暂无文档</div>}
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
                  节点：{card.node_uri || '-'}
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
                      navigator.clipboard.writeText(text).then(() => showToast('Proof Hash 已复制')).catch(() => showToast('复制失败'))
                    }}
                  >
                    复制 Hash
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
                    打开文件
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
