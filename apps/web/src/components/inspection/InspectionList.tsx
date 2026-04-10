/**
 * QCSpec · 质检记录列表
 * apps/web/src/components/inspection/InspectionList.tsx
 */

import { useEffect, useState } from 'react'
import { RESULT_LABELS, RESULT_COLORS } from '@qcspec/types'
import type { Inspection, Photo } from '@qcspec/types'
import { ResultBadge, ProgressBar, EmptyState, Button } from '../ui'
import { useInspectionStore, useUIStore, usePhotoStore } from '../../store'
import { useInspections } from '../../hooks/api/inspections'

interface Props {
  onDataChanged?: () => void | Promise<void>
}

interface PhotoPreviewState {
  photos: Photo[]
  index: number
}

const FILTER_OPTS: { value: string; label: string }[] = [
  { value: '',     label: '全部' },
  { value: 'pass', label: '✓ 合格' },
  { value: 'warn', label: '⚠ 观察' },
  { value: 'fail', label: '✗ 不合格' },
]

const formatDateTimeWithSeconds = (input?: string): string => {
  if (!input) return '-'
  const dt = new Date(input)
  if (Number.isNaN(dt.getTime())) return String(input)
  const y = dt.getFullYear()
  const m = String(dt.getMonth() + 1).padStart(2, '0')
  const d = String(dt.getDate()).padStart(2, '0')
  const hh = String(dt.getHours()).padStart(2, '0')
  const mm = String(dt.getMinutes()).padStart(2, '0')
  const ss = String(dt.getSeconds()).padStart(2, '0')
  return `${y}/${m}/${d} ${hh}:${mm}:${ss}`
}

export default function InspectionList({ onDataChanged }: Props) {
  const { inspections, stats, removeInspection, photoLinksByInspection } = useInspectionStore()
  const { photos } = usePhotoStore()
  const { remove } = useInspections()
  const { showToast }       = useUIStore()

  const [filter,  setFilter]  = useState('')
  const [filterType, setFilterType] = useState('')
  const [search,  setSearch]  = useState('')
  const [previewState, setPreviewState] = useState<PhotoPreviewState | null>(null)

  const typeOptions = Array.from(
    new Map(inspections.map((i) => [i.type, i.type_name])).entries()
  ).map(([value, label]) => ({ value, label }))

  // 过滤 + 搜索
  const filtered = inspections
    .filter(i => !filter  || i.result === filter)
    .filter(i => !filterType || i.type === filterType)
    .filter(i => !search  || i.location.includes(search) || i.type_name.includes(search))
    .sort((a, b) => {
      return new Date(b.inspected_at).getTime() - new Date(a.inspected_at).getTime()
    })

  const handleDelete = async (id: string) => {
    if (!confirm('确认删除此记录？')) return
    await remove(id)
    removeInspection(id)
    await onDataChanged?.()
    showToast('记录已删除')
  }

  const exportCSV = () => {
    const rows = [
      ['序号','桩号','检测项目','实测值','单位','标准值','判定结果','检测人员','备注','时间','ProofID'],
      ...filtered.map((i, idx) => [
        idx + 1, i.location, i.type_name,
        i.value, i.unit, i.standard ?? '',
        RESULT_LABELS[i.result],
        i.person ?? '', i.remark ?? '', formatDateTimeWithSeconds(i.inspected_at),
        i.proof_id ?? '',
      ])
    ]
    const csv = '\uFEFF' + rows.map(r => r.join(',')).join('\n')
    const url = URL.createObjectURL(new Blob([csv], { type: 'text/csv' }))
    const a   = document.createElement('a')
    a.href = url
    a.download = `质检记录_${new Date().toLocaleDateString('zh-CN').replace(/\//g,'')}.csv`
    a.click()
    URL.revokeObjectURL(url)
    showToast('📊 已导出 CSV')
  }

  const getLinkedPhotos = (inspectionId: string): Photo[] => {
    const mappedIds = photoLinksByInspection[inspectionId] || []
    const mappedPhotos = mappedIds.length
      ? photos.filter((p) => mappedIds.includes(p.id))
      : []
    if (mappedPhotos.length) return mappedPhotos
    return photos.filter((p) => p.inspection_id === inspectionId)
  }

  return (
    <div>
      {/* 统计栏 */}
      <div style={{
        display: 'grid', gridTemplateColumns: 'repeat(4,1fr)',
        gap: 10, marginBottom: 14,
      }}>
        {[
          { label: '合计', val: stats.total, color: '#0F172A', bg: '#F0F4F8' },
          { label: '合格', val: stats.pass,  color: '#059669', bg: '#ECFDF5' },
          { label: '观察', val: stats.warn,  color: '#D97706', bg: '#FFFBEB' },
          { label: '不合格', val: stats.fail, color: '#DC2626', bg: '#FEF2F2' },
        ].map(s => (
          <div key={s.label} style={{
            background: s.bg, borderRadius: 10, padding: '12px 14px',
          }}>
            <div style={{ fontSize: 22, fontWeight: 900, color: s.color }}>{s.val}</div>
            <div style={{ fontSize: 12, color: s.color, opacity: 0.8, marginTop: 2 }}>{s.label}</div>
          </div>
        ))}
      </div>

      {/* 合格率进度 */}
      {stats.total > 0 && (
        <div style={{ marginBottom: 14 }}>
          <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: 6 }}>
            <span style={{ fontSize: 12, color: '#6B7280' }}>合格率</span>
            <span style={{
              fontSize: 13, fontWeight: 700,
              color: stats.pass_rate >= 90 ? '#059669' : stats.pass_rate >= 70 ? '#D97706' : '#DC2626',
            }}>
              {stats.pass_rate}%
            </span>
          </div>
          <ProgressBar
            value={stats.pass_rate}
            color={stats.pass_rate >= 90 ? '#059669' : stats.pass_rate >= 70 ? '#D97706' : '#DC2626'}
          />
        </div>
      )}

      {/* 工具栏 */}
      <div style={{ display: 'flex', gap: 8, marginBottom: 12, flexWrap: 'wrap' }}>
        <input
          value={search}
          onChange={e => setSearch(e.target.value)}
          placeholder="搜索桩号或项目..."
          style={{
            flex: 1, minWidth: 160,
            background: '#fff', border: '1px solid #E2E8F0',
            borderRadius: 8, padding: '8px 12px 8px 32px',
            fontSize: 13, fontFamily: 'var(--sans)', outline: 'none',
            backgroundImage: `url("data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' fill='none' viewBox='0 0 24 24' stroke='%239CA3AF' stroke-width='2'%3E%3Cpath stroke-linecap='round' stroke-linejoin='round' d='M21 21l-6-6m2-5a7 7 0 11-14 0 7 7 0 0114 0z'/%3E%3C/svg%3E")`,
            backgroundRepeat: 'no-repeat', backgroundSize: '16px',
            backgroundPosition: '10px center',
          }}
        />
        {FILTER_OPTS.map(f => (
          <button
            key={f.value}
            onClick={() => setFilter(f.value)}
            style={{
              padding: '7px 14px', borderRadius: 8, fontSize: 12,
              fontWeight: 700, cursor: 'pointer', fontFamily: 'var(--sans)',
              border: `1px solid ${filter === f.value ? '#1A56DB' : '#E2E8F0'}`,
              background: filter === f.value ? '#EFF6FF' : '#fff',
              color: filter === f.value ? '#1A56DB' : '#6B7280',
            }}
          >
            {f.label}
          </button>
        ))}
        <select
          value={filterType}
          onChange={(e) => setFilterType(e.target.value)}
          style={{
            minWidth: 140,
            background: '#fff',
            border: '1px solid #E2E8F0',
            borderRadius: 8,
            padding: '7px 10px',
            fontSize: 12,
            fontWeight: 700,
            color: '#475569',
            fontFamily: 'var(--sans)',
          }}
        >
          <option value="">全部类型</option>
          {typeOptions.map((opt) => (
            <option key={opt.value} value={opt.value}>
              {opt.label}
            </option>
          ))}
        </select>
        <Button variant="secondary" size="sm" icon="📊" onClick={exportCSV}>
          导出
        </Button>
      </div>

      {/* 列表 */}
      {filtered.length === 0 ? (
        inspections.length ? (
          <EmptyState icon="📋" title="没有符合筛选条件的记录" sub="请调整结果筛选、类型筛选或搜索条件" />
        ) : (
          <EmptyState icon="📋" title="暂无质检记录" sub="填写上方表单录入第一条记录" />
        )
      ) : (
        <div style={{ display: 'flex', flexDirection: 'column', gap: 6 }}>
          {filtered.map((insp, idx) => (
            <InspectionRow
              key={insp.id}
              insp={insp}
              index={idx + 1}
              linkedPhotos={getLinkedPhotos(insp.id)}
              onPreviewPhoto={(photosInRecord, photoIndex) =>
                setPreviewState({ photos: photosInRecord, index: photoIndex })
              }
              onDelete={() => handleDelete(insp.id)}
            />
          ))}
        </div>
      )}

      {/* 底部统计 */}
      {filtered.length > 0 && (
        <div style={{
          marginTop: 12, padding: '10px 14px',
          background: '#F0F4F8', borderRadius: 8,
          fontSize: 12, color: '#6B7280', textAlign: 'center',
        }}>
          显示 {filtered.length} / {inspections.length} 条记录
        </div>
      )}

      {previewState && (
        <PhotoPreviewModal
          photos={previewState.photos}
          initialIndex={previewState.index}
          onClose={() => setPreviewState(null)}
        />
      )}
    </div>
  )
}

// ── 单行 ──
function InspectionRow({
  insp, index, linkedPhotos, onPreviewPhoto, onDelete,
}: {
  insp: Inspection
  index: number
  linkedPhotos: Photo[]
  onPreviewPhoto: (photos: Photo[], index: number) => void
  onDelete: () => void
}) {
  const [expanded, setExpanded] = useState(false)

  return (
    <div
      style={{
        background: '#fff', border: '1px solid #E2E8F0',
        borderRadius: 10, overflow: 'hidden',
        borderLeft: `3px solid ${RESULT_COLORS[insp.result]}`,
      }}
    >
      <div
        style={{
          display: 'grid',
          gridTemplateColumns: '32px 1fr 80px 80px 80px 60px',
          gap: 10, padding: '12px 14px',
          alignItems: 'center', cursor: 'pointer',
        }}
        onClick={() => setExpanded(!expanded)}
      >
        <div style={{ fontSize: 12, color: '#9CA3AF', textAlign: 'center' }}>{index}</div>
        <div>
          <div style={{ fontSize: 13, fontWeight: 700, color: '#0F172A' }}>
            {insp.type_name}
          </div>
          <div style={{ fontSize: 12, color: '#6B7280', marginTop: 2 }}>
            📍 {insp.location}
            {insp.person && <span style={{ marginLeft: 8 }}>👤 {insp.person}</span>}
            <span style={{ marginLeft: 8 }}>🕐 {formatDateTimeWithSeconds(insp.inspected_at)}</span>
          </div>
          {linkedPhotos.length > 0 && (
            <div style={{ marginTop: 6, display: 'flex', gap: 5, flexWrap: 'wrap' }}>
              {linkedPhotos.map((p, photoIndex) => (
                <img
                  key={p.id}
                  src={p.storage_url}
                  alt={p.file_name}
                  title={p.file_name}
                  onClick={(e) => {
                    e.stopPropagation()
                    onPreviewPhoto(linkedPhotos, photoIndex)
                  }}
                  style={{
                    width: 28,
                    height: 28,
                    borderRadius: 4,
                    objectFit: 'cover',
                    border: '1px solid #E2E8F0',
                    background: '#F1F5F9',
                    cursor: 'zoom-in',
                  }}
                />
              ))}
            </div>
          )}
        </div>
        <div style={{ fontSize: 14, fontWeight: 700, color: '#0F172A', textAlign: 'center' }}>
          {insp.value}
          <span style={{ fontSize: 12, color: '#9CA3AF', marginLeft: 2 }}>{insp.unit}</span>
        </div>
        <div style={{ fontSize: 12, color: '#9CA3AF', textAlign: 'center' }}>
          标准: {insp.standard ?? '-'}{insp.unit}
        </div>
        <div style={{ textAlign: 'center' }}>
          <ResultBadge result={insp.result} />
        </div>
        <button
          onClick={e => { e.stopPropagation(); onDelete() }}
          style={{
            background: '#FEF2F2', color: '#DC2626',
            border: '1px solid #FECACA',
            borderRadius: 6, padding: '4px 8px',
            fontSize: 12, cursor: 'pointer',
            fontFamily: 'var(--sans)',
          }}
        >
          删除
        </button>
      </div>

      {/* 展开详情 */}
      {expanded && (
        <div style={{
          padding: '10px 14px 14px',
          borderTop: '1px solid #F0F4F8',
          background: '#FAFAFA',
        }}>
          {insp.remark && (
            <div style={{ fontSize: 12, color: '#6B7280', marginBottom: 8 }}>
              💬 {insp.remark}
            </div>
          )}
          {insp.proof_id && (
            <div style={{
              fontFamily: 'var(--mono)', fontSize: 12,
              color: '#D97706', background: '#FFFBEB',
              padding: '4px 10px', borderRadius: 6,
              display: 'inline-block',
            }}>
              🔒 {insp.proof_id}
            </div>
          )}
          <div style={{ fontSize: 12, color: '#9CA3AF', marginTop: 6 }}>
            {formatDateTimeWithSeconds(insp.inspected_at)}
          </div>
        </div>
      )}
    </div>
  )
}

function PhotoPreviewModal({
  photos,
  initialIndex,
  onClose,
}: {
  photos: Photo[]
  initialIndex: number
  onClose: () => void
}) {
  const [index, setIndex] = useState(initialIndex)

  useEffect(() => {
    setIndex(initialIndex)
  }, [initialIndex])

  useEffect(() => {
    const onKeyDown = (e: KeyboardEvent) => {
      if (e.key === 'Escape') onClose()
      if (e.key === 'ArrowLeft') setIndex((cur) => Math.max(0, cur - 1))
      if (e.key === 'ArrowRight') setIndex((cur) => Math.min(photos.length - 1, cur + 1))
    }
    window.addEventListener('keydown', onKeyDown)
    return () => window.removeEventListener('keydown', onKeyDown)
  }, [photos.length, onClose])

  const photo = photos[index]
  if (!photo) return null

  const canPrev = index > 0
  const canNext = index < photos.length - 1

  return (
    <div
      onClick={onClose}
      style={{
        position: 'fixed',
        inset: 0,
        background: 'rgba(0,0,0,0.82)',
        zIndex: 1200,
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'center',
        padding: 20,
      }}
    >
      <div
        onClick={(e) => e.stopPropagation()}
        style={{
          width: 'min(900px, 100%)',
          background: '#0F172A',
          borderRadius: 14,
          overflow: 'hidden',
          border: '1px solid rgba(255,255,255,0.08)',
        }}
      >
        <div
          style={{
            background: '#000',
            maxHeight: '70vh',
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
            position: 'relative',
          }}
        >
          {photos.length > 1 && (
            <>
              <button
                onClick={(e) => {
                  e.stopPropagation()
                  if (canPrev) setIndex((cur) => cur - 1)
                }}
                disabled={!canPrev}
                style={{
                  position: 'absolute',
                  left: 12,
                  top: '50%',
                  transform: 'translateY(-50%)',
                  width: 32,
                  height: 32,
                  borderRadius: '50%',
                  border: '1px solid rgba(255,255,255,0.2)',
                  background: canPrev ? 'rgba(15,23,42,0.7)' : 'rgba(15,23,42,0.35)',
                  color: canPrev ? '#E2E8F0' : '#64748B',
                  cursor: canPrev ? 'pointer' : 'not-allowed',
                  fontSize: 16,
                }}
              >
                ‹
              </button>
              <button
                onClick={(e) => {
                  e.stopPropagation()
                  if (canNext) setIndex((cur) => cur + 1)
                }}
                disabled={!canNext}
                style={{
                  position: 'absolute',
                  right: 12,
                  top: '50%',
                  transform: 'translateY(-50%)',
                  width: 32,
                  height: 32,
                  borderRadius: '50%',
                  border: '1px solid rgba(255,255,255,0.2)',
                  background: canNext ? 'rgba(15,23,42,0.7)' : 'rgba(15,23,42,0.35)',
                  color: canNext ? '#E2E8F0' : '#64748B',
                  cursor: canNext ? 'pointer' : 'not-allowed',
                  fontSize: 16,
                }}
              >
                ›
              </button>
            </>
          )}
          {photo.storage_url ? (
            <img
              src={photo.storage_url}
              alt={photo.file_name}
              style={{ maxWidth: '100%', maxHeight: '70vh', objectFit: 'contain' }}
            />
          ) : (
            <div style={{ color: '#64748B', fontSize: 40, padding: 40 }}>📷</div>
          )}
        </div>
        <div style={{ padding: '12px 14px', display: 'flex', justifyContent: 'space-between', gap: 8 }}>
          <div style={{ minWidth: 0 }}>
            <div style={{ fontSize: 12, fontWeight: 700, color: '#E2E8F0', whiteSpace: 'nowrap', overflow: 'hidden', textOverflow: 'ellipsis' }}>
              {photo.file_name}
            </div>
            <div style={{ fontSize: 12, color: '#94A3B8', marginTop: 2 }}>
              📍 {photo.location || '未知桩号'}
            </div>
            <div style={{ fontSize: 12, color: '#64748B', marginTop: 2 }}>
              {index + 1} / {photos.length}
            </div>
          </div>
          <div style={{ display: 'flex', gap: 8 }}>
            {photo.storage_url && (
              <a
                href={photo.storage_url}
                download={photo.file_name}
                onClick={(e) => e.stopPropagation()}
                style={{
                  border: '1px solid rgba(255,255,255,0.18)',
                  background: 'rgba(255,255,255,0.08)',
                  color: '#E2E8F0',
                  borderRadius: 8,
                  padding: '6px 10px',
                  fontSize: 12,
                  textDecoration: 'none',
                  whiteSpace: 'nowrap',
                }}
              >
                下载
              </a>
            )}
            <button
              onClick={onClose}
              style={{
                border: '1px solid rgba(255,255,255,0.18)',
                background: 'rgba(255,255,255,0.08)',
                color: '#E2E8F0',
                borderRadius: 8,
                padding: '6px 10px',
                fontSize: 12,
                cursor: 'pointer',
                fontFamily: 'var(--sans)',
                whiteSpace: 'nowrap',
              }}
            >
              关闭
            </button>
          </div>
        </div>
      </div>
    </div>
  )
}

