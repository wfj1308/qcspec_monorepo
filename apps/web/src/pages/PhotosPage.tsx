/**
 * QCSpec · 照片管理页面
 * apps/web/src/pages/PhotosPage.tsx
 */

import React, { useEffect, useState, useCallback } from 'react'
import { Card, Button, EmptyState, VPathDisplay } from '../components/ui'
import PhotoUpload from '../components/photo/PhotoUpload'
import { usePhotoStore, useProjectStore, useAuthStore, useUIStore } from '../store'
import { usePhotos } from '../hooks/useApi'
import type { Photo } from '@qcspec/types'

type ViewMode = 'grid' | 'list'
type FilterMode = 'all' | 'proof' | 'noproof'

export default function PhotosPage() {
  const {
    photos,
    setPhotos,
    removePhoto,
    selected,
    toggleSelect,
    clearSelect,
    setPendingLinkPhotoIds,
  } = usePhotoStore()
  const { currentProject }  = useProjectStore()
  const { enterprise }      = useAuthStore()
  const { showToast, setActiveTab } = useUIStore()
  const { list, remove: removePhotoApi } = usePhotos()

  const [viewMode,  setViewMode]  = useState<ViewMode>('grid')
  const [filter,    setFilter]    = useState<FilterMode>('all')
  const [search,    setSearch]    = useState('')
  const [showUpload, setShowUpload] = useState(false)
  const [preview,   setPreview]   = useState<Photo | null>(null)

  // 加载照片
  useEffect(() => {
    if (!currentProject?.id) return
    list(currentProject.id).then((res: unknown) => {
      const r = res as { data?: Photo[] } | null
      if (r?.data) setPhotos(r.data)
    })
  }, [currentProject?.id])

  const filtered = photos.filter(p => {
    if (filter === 'proof'   && !p.proof_id) return false
    if (filter === 'noproof' &&  p.proof_id) return false
    if (search && !p.location?.includes(search) && !p.file_name.includes(search)) return false
    return true
  })

  const handleBatchDelete = useCallback(async () => {
    if (!selected.size) return
    const ids = Array.from(selected)
    const results = await Promise.all(ids.map(async (id) => {
      const res = await removePhotoApi(id) as { ok?: boolean } | null
      return { id, ok: !!res?.ok }
    }))
    results.filter((r) => r.ok).forEach((r) => removePhoto(r.id))
    const failed = results.length - results.filter((r) => r.ok).length
    clearSelect()
    if (failed > 0) {
      showToast(`⚠️ 已删除 ${results.length - failed} 张，失败 ${failed} 张`)
      return
    }
    showToast(`🗑️ 已删除 ${results.length} 张照片`)
  }, [selected, removePhoto, removePhotoApi, clearSelect, showToast])

  const handleLinkToInspection = useCallback(() => {
    if (!selected.size) return
    const ids = Array.from(selected)
    setPendingLinkPhotoIds(ids)
    clearSelect()
    setActiveTab('inspection')
    showToast(`已关联 ${ids.length} 张照片到待提交质检记录`)
  }, [selected, setPendingLinkPhotoIds, clearSelect, setActiveTab, showToast])

  const proofCount   = photos.filter(p => p.proof_id).length
  const totalSize    = photos.length

  return (
    <div>
      {/* 统计栏 */}
      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(4,1fr)', gap: 12, marginBottom: 16 }}>
        {[
          { icon: '📷', label: '全部照片',   value: totalSize,            color: '#EFF6FF' },
          { icon: '🔒', label: 'Proof已锚定', value: proofCount,           color: '#ECFDF5' },
          { icon: '⏳', label: '待存证',      value: totalSize - proofCount, color: '#FFFBEB' },
          { icon: '✅', label: '已选中',      value: selected.size,        color: selected.size ? '#EFF6FF' : '#F8FAFF' },
        ].map(s => (
          <div key={s.label} style={{
            background: '#fff', border: '1px solid #E2E8F0',
            borderRadius: 10, padding: '12px 16px',
            display: 'flex', alignItems: 'center', gap: 12,
          }}>
            <div style={{ width: 40, height: 40, borderRadius: 8, background: s.color,
              display: 'flex', alignItems: 'center', justifyContent: 'center', fontSize: 18 }}>
              {s.icon}
            </div>
            <div>
              <div style={{ fontSize: 22, fontWeight: 900, lineHeight: 1 }}>{s.value}</div>
              <div style={{ fontSize: 12, color: '#6B7280', marginTop: 2 }}>{s.label}</div>
            </div>
          </div>
        ))}
      </div>

      {/* 工具栏 */}
      <div style={{ display: 'flex', gap: 8, marginBottom: 14, flexWrap: 'wrap', alignItems: 'center' }}>
        <input
          value={search} onChange={e => setSearch(e.target.value)}
          placeholder="搜索桩号、文件名..."
          style={{
            flex: 1, minWidth: 160,
            background: '#fff', border: '1px solid #E2E8F0',
            borderRadius: 8, padding: '8px 12px 8px 32px',
            fontSize: 13, outline: 'none', fontFamily: 'var(--sans)',
            backgroundImage:`url("data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' fill='none' viewBox='0 0 24 24' stroke='%239CA3AF' stroke-width='2'%3E%3Cpath stroke-linecap='round' stroke-linejoin='round' d='M21 21l-6-6m2-5a7 7 0 11-14 0 7 7 0 0114 0z'/%3E%3C/svg%3E")`,
            backgroundRepeat:'no-repeat', backgroundSize:'16px', backgroundPosition:'10px center',
          }}
        />

        {/* 筛选 */}
        {([
          { key: 'all',     label: '全部' },
          { key: 'proof',   label: '🔒 已存证' },
          { key: 'noproof', label: '⏳ 未存证' },
        ] as { key: FilterMode; label: string }[]).map(f => (
          <button key={f.key} onClick={() => setFilter(f.key)} style={{
            padding: '8px 14px', borderRadius: 8, fontSize: 12, fontWeight: 700,
            cursor: 'pointer', fontFamily: 'var(--sans)',
            border: `1px solid ${filter === f.key ? '#1A56DB' : '#E2E8F0'}`,
            background: filter === f.key ? '#EFF6FF' : '#fff',
            color: filter === f.key ? '#1A56DB' : '#6B7280',
          }}>{f.label}</button>
        ))}

        {/* 视图切换 */}
        <div style={{ display: 'flex', background: '#fff', border: '1px solid #E2E8F0', borderRadius: 8, overflow: 'hidden' }}>
          {(['grid', 'list'] as ViewMode[]).map(v => (
            <button key={v} onClick={() => setViewMode(v)} style={{
              padding: '8px 12px', border: 'none', cursor: 'pointer',
              background: viewMode === v ? '#1A56DB' : 'transparent',
              color: viewMode === v ? '#fff' : '#6B7280',
              fontSize: 14, fontFamily: 'var(--sans)',
            }}>
              {v === 'grid' ? '⊞' : '☰'}
            </button>
          ))}
        </div>

        {/* 批量操作 */}
        {selected.size > 0 && (
          <>
            <button onClick={handleLinkToInspection} style={{
              padding: '8px 14px', borderRadius: 8, fontSize: 12, fontWeight: 700,
              cursor: 'pointer', fontFamily: 'var(--sans)',
              background: '#EFF6FF', color: '#1A56DB', border: '1px solid #BFDBFE',
            }}>
              🔗 关联到质检录入 ({selected.size})
            </button>
            <button onClick={handleBatchDelete} style={{
              padding: '8px 14px', borderRadius: 8, fontSize: 12, fontWeight: 700,
              cursor: 'pointer', fontFamily: 'var(--sans)',
              background: '#FEF2F2', color: '#DC2626', border: '1px solid #FECACA',
            }}>
              🗑️ 删除 {selected.size} 张
            </button>
          </>
        )}

        <Button onClick={() => setShowUpload(x => !x)} icon="📤" size="sm">
          {showUpload ? '收起' : '上传照片'}
        </Button>
      </div>

      {/* 上传区（折叠） */}
      {showUpload && currentProject && (
        <div style={{ marginBottom: 16 }}>
          <PhotoUpload
            projectId={currentProject.id}
            enterpriseId={enterprise?.id || ''}
          />
        </div>
      )}

      {/* 照片内容 */}
      {!filtered.length ? (
        <EmptyState icon="📷" title="暂无照片" sub="点击「上传照片」添加现场照片" />
      ) : viewMode === 'grid' ? (
        <GridView
          photos={filtered}
          selected={selected}
          onToggle={toggleSelect}
          onPreview={setPreview}
        />
      ) : (
        <ListView
          photos={filtered}
          selected={selected}
          onToggle={toggleSelect}
          onPreview={setPreview}
        />
      )}

      {/* 预览弹窗 */}
      {preview && (
        <PreviewModal photo={preview} onClose={() => setPreview(null)} />
      )}
    </div>
  )
}

// ── 网格视图 ──
function GridView({ photos, selected, onToggle, onPreview }: {
  photos: Photo[]
  selected: Set<string>
  onToggle: (id: string) => void
  onPreview: (p: Photo) => void
}) {
  return (
    <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(180px, 1fr))', gap: 10 }}>
      {photos.map(p => (
        <div
          key={p.id}
          style={{
            position: 'relative', borderRadius: 10,
            overflow: 'hidden', aspectRatio: '4/3',
            border: `2px solid ${selected.has(p.id) ? '#1A56DB' : 'transparent'}`,
            cursor: 'pointer', background: '#F0F4F8',
          }}
          onClick={() => onPreview(p)}
        >
          {p.storage_url ? (
            <img src={p.storage_url} alt="" style={{ width: '100%', height: '100%', objectFit: 'cover' }} />
          ) : (
            <div style={{ width: '100%', height: '100%', display: 'flex', alignItems: 'center', justifyContent: 'center', fontSize: 32 }}>📷</div>
          )}

          {/* 选择框 */}
          <div
            onClick={e => { e.stopPropagation(); onToggle(p.id) }}
            style={{
              position: 'absolute', top: 6, left: 6,
              width: 20, height: 20, borderRadius: 4,
              background: selected.has(p.id) ? '#1A56DB' : 'rgba(255,255,255,0.8)',
              border: `2px solid ${selected.has(p.id) ? '#1A56DB' : 'rgba(0,0,0,0.2)'}`,
              display: 'flex', alignItems: 'center', justifyContent: 'center',
              fontSize: 12, color: '#fff',
            }}
          >
            {selected.has(p.id) ? '✓' : ''}
          </div>

          {/* Proof 角标 */}
          {p.proof_id && (
            <div style={{
              position: 'absolute', top: 6, right: 6,
              background: 'rgba(5,150,105,0.85)', color: '#fff',
              fontSize: 12, padding: '2px 5px', borderRadius: 4,
            }}>🔒 Proof</div>
          )}

          {/* 底部信息 */}
          <div style={{
            position: 'absolute', bottom: 0, left: 0, right: 0,
            background: 'linear-gradient(transparent, rgba(0,0,0,0.7))',
            padding: '16px 8px 6px',
          }}>
            <div style={{ fontSize: 12, color: '#fff', fontWeight: 700 }}>
              {p.location || '未知桩号'}
            </div>
            <div style={{ fontSize: 12, color: 'rgba(255,255,255,0.6)' }}>
              {p.taken_at ? new Date(p.taken_at).toLocaleDateString('zh-CN') : ''}
            </div>
          </div>
        </div>
      ))}
    </div>
  )
}

// ── 列表视图 ──
function ListView({ photos, selected, onToggle, onPreview }: {
  photos: Photo[]
  selected: Set<string>
  onToggle: (id: string) => void
  onPreview: (p: Photo) => void
}) {
  return (
    <div style={{ background: '#fff', border: '1px solid #E2E8F0', borderRadius: 12, overflow: 'hidden' }}>
      {photos.map((p, i) => (
        <div key={p.id} style={{
          display: 'flex', alignItems: 'center', gap: 12,
          padding: '12px 14px',
          borderBottom: i < photos.length - 1 ? '1px solid #F0F4F8' : 'none',
          cursor: 'pointer',
        }} onClick={() => onPreview(p)}>
          {/* 选择框 */}
          <div onClick={e => { e.stopPropagation(); onToggle(p.id) }} style={{
            width: 18, height: 18, borderRadius: 4, flexShrink: 0,
            background: selected.has(p.id) ? '#1A56DB' : '#F0F4F8',
            border: `2px solid ${selected.has(p.id) ? '#1A56DB' : '#E2E8F0'}`,
            display: 'flex', alignItems: 'center', justifyContent: 'center',
            fontSize: 12, color: '#fff',
          }}>{selected.has(p.id) ? '✓' : ''}</div>

          {/* 缩略图 */}
          <div style={{ width: 48, height: 36, borderRadius: 6, overflow: 'hidden',
            background: '#F0F4F8', flexShrink: 0 }}>
            {p.storage_url
              ? <img src={p.storage_url} style={{ width: '100%', height: '100%', objectFit: 'cover' }} alt="" />
              : <div style={{ width: '100%', height: '100%', display: 'flex', alignItems: 'center', justifyContent: 'center' }}>📷</div>
            }
          </div>

          {/* 信息 */}
          <div style={{ flex: 1, minWidth: 0 }}>
            <div style={{ fontSize: 13, fontWeight: 700, color: '#0F172A' }}>
              {p.file_name}
            </div>
            <div style={{ fontSize: 12, color: '#6B7280', display: 'flex', gap: 10, marginTop: 2 }}>
              <span>📍 {p.location || '未知'}</span>
              {p.gps_lat && <span>🛰️ {p.gps_lat.toFixed(4)},{p.gps_lng?.toFixed(4)}</span>}
              {p.taken_at && <span>🕐 {new Date(p.taken_at).toLocaleString('zh-CN').slice(0, 16)}</span>}
            </div>
          </div>

          {/* Proof */}
          {p.proof_id ? (
            <div style={{ fontFamily: 'monospace', fontSize: 12, color: '#D97706',
              background: '#FFFBEB', padding: '3px 8px', borderRadius: 4 }}>
              🔒 {p.proof_id.slice(0, 14)}
            </div>
          ) : (
            <div style={{ fontSize: 12, color: '#9CA3AF' }}>未存证</div>
          )}
        </div>
      ))}
    </div>
  )
}

// ── 照片预览弹窗 ──
function PreviewModal({ photo: p, onClose }: { photo: Photo; onClose: () => void }) {
  return (
    <div
      onClick={onClose}
      style={{
        position: 'fixed', inset: 0, background: 'rgba(0,0,0,0.85)',
        zIndex: 1000, display: 'flex', alignItems: 'center', justifyContent: 'center',
        padding: 20,
      }}
    >
      <div onClick={e => e.stopPropagation()} style={{
        background: '#0F172A', borderRadius: 16,
        maxWidth: 800, width: '100%', overflow: 'hidden',
      }}>
        {/* 图片 */}
        <div style={{ background: '#000', maxHeight: '60vh', display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
          {p.storage_url
            ? <img src={p.storage_url} style={{ maxWidth: '100%', maxHeight: '60vh', objectFit: 'contain' }} alt="" />
            : <div style={{ padding: 60, fontSize: 48, color: '#475569' }}>📷</div>
          }
        </div>

        {/* 信息 */}
        <div style={{ padding: 20 }}>
          <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 12, marginBottom: 14 }}>
            {[
              { label: '文件名',  value: p.file_name },
              { label: '拍摄桩号', value: p.location || '未知' },
              { label: 'GPS坐标', value: p.gps_lat ? `${p.gps_lat.toFixed(5)}, ${p.gps_lng?.toFixed(5)}` : '无' },
              { label: '拍摄时间', value: p.taken_at ? new Date(p.taken_at).toLocaleString('zh-CN') : '未知' },
            ].map(item => (
              <div key={item.label}>
                <div style={{ fontSize: 12, color: '#475569', marginBottom: 3 }}>{item.label}</div>
                <div style={{ fontSize: 13, color: '#E5E7EB' }}>{item.value}</div>
              </div>
            ))}
          </div>

          {p.v_uri && <VPathDisplay uri={p.v_uri} proofId={p.proof_id} />}

          <div style={{ display: 'flex', gap: 10, justifyContent: 'flex-end' }}>
            {p.storage_url && (
              <a href={p.storage_url} download={p.file_name} style={{
                padding: '8px 16px', background: '#1A56DB', color: '#fff',
                borderRadius: 8, fontSize: 13, fontWeight: 700, textDecoration: 'none',
              }}>⬇️ 下载原图</a>
            )}
            <button onClick={onClose} style={{
              padding: '8px 16px', background: 'rgba(255,255,255,0.08)',
              color: '#94A3B8', border: '1px solid rgba(255,255,255,0.1)',
              borderRadius: 8, fontSize: 13, cursor: 'pointer', fontFamily: 'var(--sans)',
            }}>关闭</button>
          </div>
        </div>
      </div>
    </div>
  )
}

