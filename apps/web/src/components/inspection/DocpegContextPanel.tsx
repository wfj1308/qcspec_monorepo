import React, { useEffect, useMemo, useState } from 'react'
import { Button, Card, Input } from '../ui'
import {
  defaultDocpegInspectionContext,
  readDocpegInspectionContext,
  saveDocpegInspectionContext,
  type DocpegInspectionContext,
} from './docpegContext'

interface Props {
  projectId: string
  onSaved?: () => void
}

export default function DocpegContextPanel({ projectId, onSaved }: Props) {
  const [expanded, setExpanded] = useState(false)
  const [context, setContext] = useState<DocpegInspectionContext>(() => readDocpegInspectionContext(projectId))

  useEffect(() => {
    setContext(readDocpegInspectionContext(projectId))
  }, [projectId])

  const summary = useMemo(() => {
    const project = context.docpegProjectId.trim() || '-'
    const chain = context.docpegChainId.trim() || '自动绑定'
    const component = context.docpegComponentUri.trim() || '-'
    const pile = context.docpegPileId.trim() || '-'
    return { project, chain, component, pile }
  }, [context])

  const patch = (next: Partial<DocpegInspectionContext>) => setContext((prev) => ({ ...prev, ...next }))

  const save = () => {
    saveDocpegInspectionContext(projectId, context)
    onSaved?.()
  }

  const reset = () => {
    const next = defaultDocpegInspectionContext(projectId)
    setContext(next)
    saveDocpegInspectionContext(projectId, next)
    onSaved?.()
  }

  return (
    <Card title="工序上下文（项目/构件）" icon="🧩">
      <div style={{ fontSize: 12, color: '#475569', marginBottom: 8, lineHeight: 1.6 }}>
        在这里统一维护 DocPeg 上下文，质检页只负责录入和提交，不再重复填写基础参数。
      </div>

      <div
        style={{
          display: 'grid',
          gridTemplateColumns: '1fr 1fr',
          gap: 8,
          marginBottom: 10,
          padding: 10,
          borderRadius: 8,
          border: '1px solid #E2E8F0',
          background: '#F8FAFC',
          fontSize: 12,
          color: '#334155',
        }}
      >
        <div>projectId: <strong>{summary.project}</strong></div>
        <div>chainId: <strong>{summary.chain}</strong></div>
        <div style={{ gridColumn: '1 / -1' }}>component_uri: <strong>{summary.component}</strong></div>
        <div>pile_id: <strong>{summary.pile}</strong></div>
        <div>formCode: <strong>{context.docpegFormCode || '-'}</strong></div>
      </div>

      <div style={{ display: 'flex', gap: 8, marginBottom: expanded ? 10 : 0 }}>
        <Button variant="secondary" size="sm" onClick={() => setExpanded((v) => !v)}>
          {expanded ? '收起高级配置' : '展开高级配置'}
        </Button>
        <Button size="sm" onClick={save}>保存上下文</Button>
        <Button variant="secondary" size="sm" onClick={reset}>重置</Button>
      </div>

      {expanded && (
        <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 10 }}>
          <Input
            label="DocPeg projectId"
            value={context.docpegProjectId}
            onChange={(v) => patch({ docpegProjectId: v })}
            placeholder="对接方 projectId"
          />
          <Input
            label="DocPeg chainId"
            value={context.docpegChainId}
            onChange={(v) => patch({ docpegChainId: v })}
            placeholder="工序链 ID（可留空自动绑定）"
          />
          <Input
            label="component_uri"
            value={context.docpegComponentUri}
            onChange={(v) => patch({ docpegComponentUri: v })}
            placeholder="v://.../component/..."
          />
          <Input
            label="pile_id"
            value={context.docpegPileId}
            onChange={(v) => patch({ docpegPileId: v })}
            placeholder="默认可用检测桩号"
          />
          <Input
            label="formCode"
            value={context.docpegFormCode}
            onChange={(v) => patch({ docpegFormCode: v })}
            placeholder="桥施2表 / qc-form-001"
          />
          <Input
            label="trip action"
            value={context.docpegAction}
            onChange={(v) => patch({ docpegAction: v })}
            placeholder="qcspec_inspection_submit"
          />
          <label style={{ display: 'flex', alignItems: 'center', gap: 8, fontSize: 12, color: '#334155' }}>
            <input
              type="checkbox"
              checked={context.docpegEnabled}
              onChange={(e) => patch({ docpegEnabled: e.target.checked })}
            />
            启用提交后自动联动
          </label>
        </div>
      )}
    </Card>
  )
}
