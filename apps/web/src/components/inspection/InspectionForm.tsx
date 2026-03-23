/**
 * QCSpec · 质检录入组件
 * apps/web/src/components/inspection/InspectionForm.tsx
 */

import React, { useState, useCallback } from 'react'
import { INSPECTION_TYPES } from '@qcspec/types'
import type { InspectResult } from '@qcspec/types'
import { Button, Input, Select, Card, VPathDisplay } from '../ui'
import { useInspections } from '../../hooks/useApi'
import { useInspectionStore, useUIStore, useProjectStore, usePhotoStore } from '../../store'

const TYPE_OPTIONS = [
  { value: '', label: '请选择检测类型' },
  // 路面
  { value: 'flatness',   label: '路面平整度' },
  { value: 'crack',      label: '裂缝宽度' },
  { value: 'rut',        label: '车辙深度' },
  { value: 'slope',      label: '横坡坡度' },
  // 结构
  { value: 'settlement', label: '路基沉降' },
  { value: 'compaction', label: '压实度' },
  { value: 'bearing',    label: '路基承载力' },
  // 桥梁
  { value: 'bridge_crack',   label: '桥梁裂缝' },
  { value: 'bridge_deflect', label: '挠度' },
  { value: 'bridge_erosion', label: '混凝土碳化' },
  // 房建
  { value: 'concrete_str',  label: '混凝土强度' },
  { value: 'rebar_spacing', label: '钢筋间距' },
]

// 快捷模板
const TEMPLATES = [
  { key: 'flatness',   icon: '🛣️', label: '路面平整度', std: 'IRI ≤ 2.0' },
  { key: 'crack',      icon: '🔍', label: '裂缝宽度',   std: '≤ 0.2mm' },
  { key: 'compaction', icon: '🏗️', label: '压实度',     std: '≥ 96%' },
  { key: 'settlement', icon: '📏', label: '路基沉降',   std: '≤ 30mm' },
]

interface Props {
  projectId:    string
  enterpriseId: string
  onSuccess?:   () => void
}

export default function InspectionForm({ projectId, enterpriseId, onSuccess }: Props) {
  const { submit, loading } = useInspections()
  const { addInspection, setInspectionPhotoLinks } = useInspectionStore()
  const { showToast, setActiveTab } = useUIStore()
  const { currentProject }  = useProjectStore()
  const { photos, pendingLinkPhotoIds, clearPendingLinkPhotoIds } = usePhotoStore()

  const [type,     setType]     = useState('')
  const [location, setLocation] = useState('')
  const [value,    setValue]    = useState('')
  const [person,   setPerson]   = useState('')
  const [remark,   setRemark]   = useState('')
  const [result,   setResult]   = useState<InspectResult | ''>('')
  const [lastProof, setLastProof] = useState('')
  const [inspectedAt, setInspectedAt] = useState(
    () => new Date(Date.now() - new Date().getTimezoneOffset() * 60000).toISOString().slice(0, 16)
  )

  // 选类型时自动填标准值和自动判定
  const typeConfig = type ? INSPECTION_TYPES[type] : null
  const linkedPhotos = photos.filter((p) => pendingLinkPhotoIds.includes(p.id))

  const autoJudge = useCallback((val: string) => {
    if (!typeConfig || !val) return
    const v = parseFloat(val)
    if (isNaN(v)) return
    const std = typeConfig.standard
    let r: InspectResult = 'pass'
    if (typeConfig.better === 'less') {
      if (v > std * 1.2) r = 'fail'
      else if (v > std)  r = 'warn'
    } else if (typeConfig.better === 'more') {
      if (v < std * 0.95) r = 'fail'
      else if (v < std)   r = 'warn'
    }
    setResult(r)
  }, [typeConfig])

  const loadTemplate = (key: string) => {
    setType(key)
    setInspectedAt(new Date(Date.now() - new Date().getTimezoneOffset() * 60000).toISOString().slice(0, 16))
    autoJudge(value)
  }

  const handleSubmit = async () => {
    if (!type || !location || !value || !result) {
      showToast('⚠️ 请填写检测类型、桩号、实测值并选择结果')
      return
    }
    const body = {
      project_id:  projectId,
      location,
      type,
      type_name:   typeConfig?.label || type,
      value:       parseFloat(value),
      standard:    typeConfig?.standard,
      unit:        typeConfig?.unit || '',
      result,
      person:      person || undefined,
      remark:      remark || undefined,
      inspected_at: inspectedAt ? new Date(inspectedAt).toISOString() : new Date().toISOString(),
      photo_ids: pendingLinkPhotoIds.length ? pendingLinkPhotoIds : undefined,
    }
    const res = await submit(body) as { inspection_id?: string; proof_id?: string } | null
    if (res?.inspection_id) {
      addInspection({
        id:           res.inspection_id,
        project_id:   projectId,
        v_uri:        `${currentProject?.v_uri || ''}inspection/${res.inspection_id}/`,
        location, type,
        type_name:    typeConfig?.label || type,
        value:        parseFloat(value),
        standard:     typeConfig?.standard,
        unit:         typeConfig?.unit || '',
        result,
        person, remark,
        proof_id:     res.proof_id,
        proof_status: 'confirmed',
        seal_status:  'unsigned',
        inspected_at: inspectedAt ? new Date(inspectedAt).toISOString() : new Date().toISOString(),
      })
      if (pendingLinkPhotoIds.length) {
        setInspectionPhotoLinks(res.inspection_id, pendingLinkPhotoIds)
        clearPendingLinkPhotoIds()
      }
      setLastProof(res.proof_id || '')
      // 重置表单
      setValue('')
      setRemark('')
      setResult('')
      setInspectedAt(new Date(Date.now() - new Date().getTimezoneOffset() * 60000).toISOString().slice(0, 16))
      onSuccess?.()
    }
  }

  const resultBtns: { key: InspectResult; label: string; color: string; bg: string }[] = [
    { key: 'pass', label: '✓ 合格', color: '#059669', bg: '#ECFDF5' },
    { key: 'warn', label: '⚠ 观察', color: '#D97706', bg: '#FFFBEB' },
    { key: 'fail', label: '✗ 不合格', color: '#DC2626', bg: '#FEF2F2' },
  ]

  return (
    <Card title="质检录入" icon="📋">
      {/* 快捷模板 */}
      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(4,1fr)', gap: 8, marginBottom: 16 }}>
        {TEMPLATES.map(t => (
          <button
            key={t.key}
            onClick={() => loadTemplate(t.key)}
            style={{
              padding: '10px 8px',
              background: type === t.key ? '#EFF6FF' : '#F0F4F8',
              border: `1px solid ${type === t.key ? '#1A56DB' : '#E2E8F0'}`,
              borderRadius: 8, cursor: 'pointer',
              fontSize: 12, textAlign: 'left',
              fontFamily: 'var(--sans)',
            }}
          >
            <div style={{ fontSize: 18, marginBottom: 4 }}>{t.icon}</div>
            <div style={{ fontWeight: 700, color: '#0F172A' }}>{t.label}</div>
            <div style={{ fontSize: 10, color: '#9CA3AF', marginTop: 2 }}>{t.std}</div>
          </button>
        ))}
      </div>

      {/* 表单 */}
      <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 12, marginBottom: 12 }}>
        <Select
          label="检测类型" required
          value={type} onChange={setType}
          options={TYPE_OPTIONS}
        />
        <Input
          label="检测桩号" required
          value={location} onChange={setLocation}
          placeholder="K50+200"
        />
        <div>
          <Input
            label="实测值" required
            value={value} type="number"
            onChange={v => { setValue(v); autoJudge(v) }}
            placeholder="0.00"
          />
          {typeConfig && (
            <div style={{ fontSize: 11, color: '#1A56DB', marginTop: 4 }}>
              规范标准：{typeConfig.standard} {typeConfig.unit}
              {typeConfig.normRef && (
                <span style={{ color: '#9CA3AF', marginLeft: 6 }}>{typeConfig.normRef}</span>
              )}
            </div>
          )}
        </div>
        <Input
          label="检测人员"
          value={person} onChange={setPerson}
          placeholder="姓名"
        />
        <div>
          <div style={{ fontSize: 11, fontWeight: 700, color: '#6B7280', marginBottom: 5, letterSpacing: '0.5px', textTransform: 'uppercase' }}>
            检测时间
          </div>
          <input
            type="datetime-local"
            value={inspectedAt}
            onChange={(e) => setInspectedAt(e.target.value)}
            style={{
              width: '100%',
              background: '#F0F4F8',
              border: '1px solid #E2E8F0',
              borderRadius: 8,
              padding: '9px 12px',
              fontSize: 13,
              fontFamily: 'var(--sans)',
              color: '#0F172A',
              outline: 'none',
            }}
          />
        </div>
      </div>

      {/* 合格判定 */}
      <div style={{ marginBottom: 12 }}>
        <div style={{ fontSize: 11, fontWeight: 700, color: '#6B7280', marginBottom: 8, letterSpacing: '0.5px', textTransform: 'uppercase' }}>
          合格判定 <span style={{ color: '#DC2626' }}>*</span>
        </div>
        <div style={{ display: 'flex', gap: 8 }}>
          {resultBtns.map(b => (
            <button
              key={b.key}
              onClick={() => setResult(b.key)}
              style={{
                flex: 1, padding: '10px 0', borderRadius: 8,
                border: `1.5px solid ${result === b.key ? b.color : '#E2E8F0'}`,
                background: result === b.key ? b.bg : '#F0F4F8',
                color: result === b.key ? b.color : '#6B7280',
                fontSize: 13, fontWeight: 700, cursor: 'pointer',
                fontFamily: 'var(--sans)',
              }}
            >
              {b.label}
            </button>
          ))}
        </div>
      </div>

      {/* 备注 */}
      <div style={{ marginBottom: 14 }}>
        <div style={{ fontSize: 11, fontWeight: 700, color: '#6B7280', marginBottom: 5, letterSpacing: '0.5px', textTransform: 'uppercase' }}>备注</div>
        <textarea
          value={remark}
          onChange={e => setRemark(e.target.value)}
          placeholder="检测情况描述、异常说明..."
          rows={2}
          style={{
            width: '100%', background: '#F0F4F8',
            border: '1px solid #E2E8F0', borderRadius: 8,
            padding: '9px 12px', fontSize: 13,
            fontFamily: 'var(--sans)', resize: 'vertical', outline: 'none',
          }}
        />
      </div>

      {/* 提交 */}
      <div style={{ marginBottom: 14 }}>
        <div style={{ fontSize: 11, fontWeight: 700, color: '#6B7280', marginBottom: 5, letterSpacing: '0.5px', textTransform: 'uppercase' }}>
          关联照片
        </div>
        {linkedPhotos.length ? (
          <div style={{ display: 'flex', gap: 6, flexWrap: 'wrap' }}>
            {linkedPhotos.map((p) => (
              <img
                key={p.id}
                src={p.storage_url}
                alt={p.file_name}
                title={p.file_name}
                style={{ width: 56, height: 56, borderRadius: 6, objectFit: 'cover', border: '1px solid #E2E8F0' }}
              />
            ))}
            <button
              onClick={clearPendingLinkPhotoIds}
              style={{
                padding: '0 10px',
                borderRadius: 6,
                border: '1px solid #FECACA',
                background: '#FEF2F2',
                color: '#DC2626',
                fontSize: 12,
                cursor: 'pointer',
                fontFamily: 'var(--sans)',
              }}
            >
              清空关联
            </button>
          </div>
        ) : (
          <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', gap: 8 }}>
            <div style={{ fontSize: 12, color: '#94A3B8' }}>可在“现场照片”页多选后点击“关联到质检录入”。</div>
            <button
              onClick={() => setActiveTab('photos')}
              style={{
                border: '1px solid #BFDBFE',
                background: '#EFF6FF',
                color: '#1A56DB',
                borderRadius: 6,
                padding: '4px 8px',
                fontSize: 12,
                cursor: 'pointer',
                fontFamily: 'var(--sans)',
                whiteSpace: 'nowrap',
              }}
            >
              去现场照片
            </button>
          </div>
        )}
      </div>

      <Button
        fullWidth onClick={handleSubmit}
        disabled={loading || !type || !location || !value || !result}
        icon="✅"
      >
        {loading ? '保存中...' : '保存质检记录'}
      </Button>

      {/* 最新 Proof */}
      {lastProof && (
        <div style={{ marginTop: 10 }}>
          <VPathDisplay
            uri={`${currentProject?.v_uri || ''}inspection/latest/`}
            proofId={lastProof}
          />
        </div>
      )}
    </Card>
  )
}
