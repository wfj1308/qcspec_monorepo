/**
 * QCSpec · 照片上传组件
 * apps/web/src/components/photo/PhotoUploader.tsx
 */

import React, { useState, useRef, useCallback, useEffect } from 'react'
import { Button, Card, VPathDisplay } from '../ui'
import { usePhotos } from '../../hooks/useApi'
import { usePhotoStore, useUIStore, useProjectStore } from '../../store'
import type { Photo } from '@qcspec/types'

interface Props {
  projectId:    string
  enterpriseId: string
  inspectionId?: string
}

interface PreviewFile {
  id:      string
  file:    File
  url:     string
  name:    string
  size:    string
  status:  'pending' | 'uploading' | 'done' | 'error'
  proofId?: string
  vUri?:   string
}

export default function PhotoUploader({ projectId, enterpriseId, inspectionId }: Props) {
  const { upload, uploading } = usePhotos()
  const { addPhoto }          = usePhotoStore()
  const { showToast }         = useUIStore()
  const { currentProject }    = useProjectStore()

  const [previews,  setPreviews]  = useState<PreviewFile[]>([])
  const [location,  setLocation]  = useState('')
  const [gps,       setGps]       = useState<[number, number] | null>(null)
  const [dragOver,  setDragOver]  = useState(false)
  const inputRef = useRef<HTMLInputElement>(null)

  // 自动获取 GPS
  useEffect(() => {
    if (navigator.geolocation) {
      navigator.geolocation.getCurrentPosition(
        pos => setGps([pos.coords.latitude, pos.coords.longitude]),
        () => {}
      )
    }
  }, [])

  const addFiles = useCallback((files: FileList | File[]) => {
    const arr = Array.from(files).filter(f => f.type.startsWith('image/'))
    if (!arr.length) return showToast('⚠️ 请选择图片文件')

    const news: PreviewFile[] = arr.map(f => ({
      id:     Math.random().toString(36).slice(2),
      file:   f,
      url:    URL.createObjectURL(f),
      name:   f.name,
      size:   (f.size / 1024).toFixed(0) + 'KB',
      status: 'pending' as const,
    }))
    setPreviews(p => [...p, ...news])
  }, [showToast])

  const handleDrop = (e: React.DragEvent) => {
    e.preventDefault()
    setDragOver(false)
    addFiles(e.dataTransfer.files)
  }

  const handleFileInput = (e: React.ChangeEvent<HTMLInputElement>) => {
    if (e.target.files) addFiles(e.target.files)
  }

  // 上传单张
  const uploadOne = async (pf: PreviewFile) => {
    setPreviews(prev => prev.map(p =>
      p.id === pf.id ? { ...p, status: 'uploading' } : p
    ))
    const res = await upload({
      file: pf.file, project_id: projectId,
      enterprise_id: enterpriseId,
      location: location || undefined,
      inspection_id: inspectionId,
      gps_lat: gps?.[0], gps_lng: gps?.[1],
    }) as { photo_id?: string; proof_id?: string; v_uri?: string; storage_url?: string } | null

    if (res?.photo_id) {
      setPreviews(prev => prev.map(p =>
        p.id === pf.id ? { ...p, status: 'done', proofId: res.proof_id, vUri: res.v_uri } : p
      ))
      addPhoto({
        id: res.photo_id,
        project_id: projectId,
        inspection_id: inspectionId,
        v_uri: res.v_uri || '',
        file_name: pf.file.name,
        storage_path: '',
        storage_url: res.storage_url,
        location,
        gps_lat: gps?.[0], gps_lng: gps?.[1],
        taken_at: new Date().toISOString(),
        proof_id: res.proof_id,
      })
    } else {
      setPreviews(prev => prev.map(p =>
        p.id === pf.id ? { ...p, status: 'error' } : p
      ))
    }
  }

  // 批量上传
  const uploadAll = async () => {
    const pending = previews.filter(p => p.status === 'pending')
    if (!pending.length) return showToast('⚠️ 没有待上传的照片')
    for (const pf of pending) {
      await uploadOne(pf)
    }
    showToast(`✅ ${pending.length}张照片上传完成`)
  }

  const removePreview = (id: string) => {
    setPreviews(p => {
      const target = p.find(x => x.id === id)
      if (target) URL.revokeObjectURL(target.url)
      return p.filter(x => x.id !== id)
    })
  }

  const pendingCount = previews.filter(p => p.status === 'pending').length
  const doneCount    = previews.filter(p => p.status === 'done').length

  return (
    <Card title="现场照片" icon="📷">
      {/* 拖拽区 */}
      <div
        onDragOver={e => { e.preventDefault(); setDragOver(true) }}
        onDragLeave={() => setDragOver(false)}
        onDrop={handleDrop}
        onClick={() => inputRef.current?.click()}
        style={{
          border: `2px dashed ${dragOver ? '#1A56DB' : '#E2E8F0'}`,
          borderRadius: 10, padding: '24px 16px',
          textAlign: 'center', cursor: 'pointer',
          background: dragOver ? '#EFF6FF' : '#F8FAFF',
          marginBottom: 12, transition: 'all 0.2s',
        }}
      >
        <div style={{ fontSize: 32, marginBottom: 8 }}>📷</div>
        <div style={{ fontSize: 13, fontWeight: 700, color: '#0F172A', marginBottom: 4 }}>
          点击选择或拖拽照片到此处
        </div>
        <div style={{ fontSize: 11, color: '#9CA3AF' }}>
          支持 JPG / PNG · 最大 20MB / 张
        </div>
        <input
          ref={inputRef}
          type="file" accept="image/*"
          multiple hidden
          onChange={handleFileInput}
        />
      </div>

      {/* 位置 + GPS */}
      <div style={{ display: 'flex', gap: 8, marginBottom: 12, alignItems: 'center' }}>
        <input
          value={location}
          onChange={e => setLocation(e.target.value)}
          placeholder="拍摄桩号 K50+200"
          style={{
            flex: 1, background: '#F0F4F8',
            border: '1px solid #E2E8F0', borderRadius: 8,
            padding: '8px 12px', fontSize: 13,
            fontFamily: 'var(--sans)', outline: 'none',
          }}
        />
        <div style={{
          fontSize: 11, color: gps ? '#059669' : '#9CA3AF',
          background: gps ? '#ECFDF5' : '#F0F4F8',
          padding: '8px 12px', borderRadius: 8,
          border: `1px solid ${gps ? '#A7F3D0' : '#E2E8F0'}`,
          whiteSpace: 'nowrap',
        }}>
          {gps ? `📍 GPS已获取` : '📍 定位中...'}
        </div>
      </div>

      {/* 预览网格 */}
      {previews.length > 0 && (
        <>
          <div style={{
            display: 'grid', gridTemplateColumns: 'repeat(3,1fr)',
            gap: 8, marginBottom: 12,
          }}>
            {previews.map(pf => (
              <div key={pf.id} style={{ position: 'relative', borderRadius: 8, overflow: 'hidden' }}>
                <img
                  src={pf.url} alt={pf.name}
                  style={{
                    width: '100%', aspectRatio: '4/3',
                    objectFit: 'cover', display: 'block',
                    opacity: pf.status === 'uploading' ? 0.5 : 1,
                  }}
                />
                {/* 状态蒙层 */}
                {pf.status === 'uploading' && (
                  <div style={{
                    position: 'absolute', inset: 0,
                    background: 'rgba(0,0,0,0.4)',
                    display: 'flex', alignItems: 'center', justifyContent: 'center',
                    fontSize: 20,
                  }}>
                    ⏳
                  </div>
                )}
                {pf.status === 'done' && (
                  <div style={{
                    position: 'absolute', top: 6, right: 6,
                    background: '#059669', color: '#fff',
                    borderRadius: '50%', width: 22, height: 22,
                    display: 'flex', alignItems: 'center', justifyContent: 'center',
                    fontSize: 12,
                  }}>✓</div>
                )}
                {pf.status === 'error' && (
                  <div style={{
                    position: 'absolute', top: 6, right: 6,
                    background: '#DC2626', color: '#fff',
                    borderRadius: '50%', width: 22, height: 22,
                    display: 'flex', alignItems: 'center', justifyContent: 'center',
                    fontSize: 12,
                  }}>✗</div>
                )}
                {/* 删除按钮 */}
                {pf.status !== 'uploading' && (
                  <button
                    onClick={() => removePreview(pf.id)}
                    style={{
                      position: 'absolute', top: 6, left: 6,
                      background: 'rgba(0,0,0,0.5)', color: '#fff',
                      border: 'none', borderRadius: '50%',
                      width: 22, height: 22, cursor: 'pointer',
                      fontSize: 11, display: 'flex',
                      alignItems: 'center', justifyContent: 'center',
                    }}
                  >✕</button>
                )}
                {/* Proof 标记 */}
                {pf.proofId && (
                  <div style={{
                    position: 'absolute', bottom: 0, left: 0, right: 0,
                    background: 'rgba(0,0,0,0.7)',
                    padding: '3px 6px',
                    fontFamily: 'monospace', fontSize: 9, color: '#F59E0B',
                  }}>
                    {pf.proofId.slice(0, 20)}
                  </div>
                )}
                {/* 文件名 + 大小 */}
                <div style={{
                  fontSize: 10, color: '#6B7280',
                  padding: '4px 6px', background: '#F8FAFF',
                  whiteSpace: 'nowrap', overflow: 'hidden', textOverflow: 'ellipsis',
                }}>
                  {pf.name} · {pf.size}
                </div>
              </div>
            ))}
          </div>

          {/* 上传按钮 */}
          <div style={{ display: 'flex', gap: 8 }}>
            <Button
              fullWidth
              onClick={uploadAll}
              disabled={uploading || pendingCount === 0}
              icon="🚀"
            >
              {uploading
                ? '上传中...'
                : `上传 ${pendingCount} 张照片`}
            </Button>
            <Button
              variant="secondary"
              onClick={() => setPreviews([])}
              icon="🗑️"
            >
              清空
            </Button>
          </div>

          {/* 上传结果 */}
          {doneCount > 0 && (
            <div style={{
              marginTop: 10, padding: '8px 12px',
              background: '#ECFDF5', borderRadius: 8,
              fontSize: 12, color: '#059669', fontWeight: 700,
            }}>
              ✅ {doneCount} 张已上传并生成 Proof 存证
            </div>
          )}
        </>
      )}
    </Card>
  )
}
