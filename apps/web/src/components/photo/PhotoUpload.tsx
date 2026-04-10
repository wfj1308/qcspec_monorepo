/**
 * QCSpec · 照片上传组件
 * apps/web/src/components/photo/PhotoUpload.tsx
 */

import { useState, useRef, useCallback } from 'react'
import { Card, Button } from '../ui'
import { usePhotos } from '../../hooks/api/photos'
import { usePhotoStore, useUIStore } from '../../store'

interface Props {
  projectId:    string
  enterpriseId: string
  inspectionId?: string
  location?:    string
}

interface PreviewFile {
  file:     File
  url:      string
  location: string
  gps_lat?: number
  gps_lng?: number
  status:   'pending' | 'uploading' | 'done' | 'error'
  proof_id?: string
  v_uri?:    string
}

const formatDateTime = (d: Date) => {
  const pad = (n: number) => String(n).padStart(2, '0')
  return `${d.getFullYear()}年${pad(d.getMonth() + 1)}月${pad(d.getDate())}日 ${pad(d.getHours())}:${pad(d.getMinutes())}:${pad(d.getSeconds())}`
}

export default function PhotoUpload({ projectId, enterpriseId, inspectionId, location: propLocation }: Props) {
  const { upload, uploading }   = usePhotos()
  const { addPhoto }            = usePhotoStore()
  const { showToast }           = useUIStore()
  const [files,    setFiles]    = useState<PreviewFile[]>([])
  const [location, setLocation] = useState(propLocation || '')
  const [dragging, setDragging] = useState(false)
  const inputRef = useRef<HTMLInputElement>(null)

  // 获取 GPS
  const getGPS = useCallback(() => new Promise<{ lat: number; lng: number } | null>(resolve => {
    if (!navigator.geolocation) { resolve(null); return }
    navigator.geolocation.getCurrentPosition(
      p => resolve({ lat: p.coords.latitude, lng: p.coords.longitude }),
      () => resolve(null),
      { timeout: 5000 }
    )
  }), [])

  // 添加文件到预览
  const addFiles = useCallback(async (newFiles: FileList | File[]) => {
    const gps = await getGPS()
    const arr = Array.from(newFiles).filter(f => f.type.startsWith('image/'))
    if (!arr.length) { showToast('⚠️ 只支持图片文件'); return }
    const previews: PreviewFile[] = arr.map(file => ({
      file,
      url:     URL.createObjectURL(file),
      location,
      gps_lat: gps?.lat,
      gps_lng: gps?.lng,
      status:  'pending',
    }))
    setFiles(prev => [...prev, ...previews])
  }, [location, getGPS, showToast])

  // 拖拽处理
  const onDrop = useCallback((e: React.DragEvent) => {
    e.preventDefault()
    setDragging(false)
    addFiles(e.dataTransfer.files)
  }, [addFiles])

  // 生成水印 Canvas
  const addWatermark = useCallback((file: PreviewFile): Promise<File> => {
    return new Promise(resolve => {
      const img = new Image()
      img.onload = () => {
        const canvas = document.createElement('canvas')
        canvas.width  = img.width
        canvas.height = img.height
        const ctx = canvas.getContext('2d')!
        ctx.drawImage(img, 0, 0)

        // 水印背景
        const barH = Math.max(40, img.height * 0.06)
        ctx.fillStyle = 'rgba(0,0,0,0.65)'
        ctx.fillRect(0, img.height - barH, img.width, barH)

        // 水印文字
        const fs = Math.max(12, barH * 0.38)
        ctx.fillStyle = '#FFFFFF'
        ctx.font = `${fs}px monospace`
        ctx.textBaseline = 'middle'
        const y = img.height - barH / 2

        const now   = formatDateTime(new Date())
        const gps   = file.gps_lat ? `${file.gps_lat.toFixed(4)},${file.gps_lng?.toFixed(4)}` : ''
        const label = `QCSpec · ${file.location || '未知桩号'} · ${now}${gps ? ' · ' + gps : ''}`

        ctx.fillText(label, 10, y, img.width - 20)

        canvas.toBlob(blob => {
          if (!blob) { resolve(file.file); return }
          resolve(new File([blob], file.file.name, { type: 'image/jpeg' }))
        }, 'image/jpeg', 0.88)
      }
      img.src = file.url
    })
  }, [])

  // 上传单张
  const uploadOne = useCallback(async (idx: number) => {
    const f = files[idx]
    if (!f || f.status !== 'pending') return

    setFiles(prev => prev.map((x, i) => i === idx ? { ...x, status: 'uploading' } : x))

    const watermarked = await addWatermark(f)
    const res = await upload({
      file:          watermarked,
      project_id:    projectId,
      enterprise_id: enterpriseId,
      location:      f.location || location,
      inspection_id: inspectionId,
      gps_lat:       f.gps_lat,
      gps_lng:       f.gps_lng,
    }) as { photo_id?: string; v_uri?: string; proof_id?: string } | null

    if (res?.photo_id) {
      setFiles(prev => prev.map((x, i) => i === idx
        ? { ...x, status: 'done', proof_id: res.proof_id, v_uri: res.v_uri }
        : x
      ))
      addPhoto({
        id:            res.photo_id,
        project_id:    projectId,
        inspection_id: inspectionId,
        v_uri:         res.v_uri || '',
        file_name:     f.file.name,
        storage_path:  '',
        storage_url:   f.url,
        location:      f.location,
        gps_lat:       f.gps_lat,
        gps_lng:       f.gps_lng,
        proof_id:      res.proof_id,
      })
    } else {
      setFiles(prev => prev.map((x, i) => i === idx ? { ...x, status: 'error' } : x))
    }
  }, [files, upload, addWatermark, addPhoto, projectId, enterpriseId, inspectionId, location])

  // 全部上传
  const uploadAll = useCallback(async () => {
    const pending = files.map((f, i) => f.status === 'pending' ? i : -1).filter(i => i >= 0)
    for (const idx of pending) {
      await uploadOne(idx)
    }
    showToast(`✅ ${pending.length} 张照片上传完成`)
  }, [files, uploadOne, showToast])

  const removeFile = (idx: number) => {
    URL.revokeObjectURL(files[idx].url)
    setFiles(prev => prev.filter((_, i) => i !== idx))
  }

  const pending = files.filter(f => f.status === 'pending').length
  const done    = files.filter(f => f.status === 'done').length

  return (
    <Card title="现场照片" icon="📷">
      {/* 桩号输入 */}
      <div style={{ marginBottom: 12 }}>
        <div style={{ fontSize: 12, fontWeight: 700, color: '#6B7280', marginBottom: 5, letterSpacing: '0.5px', textTransform: 'uppercase' }}>
          拍摄桩号
        </div>
        <input
          value={location}
          onChange={e => setLocation(e.target.value)}
          placeholder="K50+200（自动写入水印）"
          style={{
            width: '100%', background: '#F0F4F8',
            border: '1px solid #E2E8F0', borderRadius: 8,
            padding: '9px 12px', fontSize: 13, outline: 'none',
            fontFamily: 'var(--sans)',
          }}
        />
      </div>

      {/* 拖拽区 */}
      <div
        onDragOver={e => { e.preventDefault(); setDragging(true) }}
        onDragLeave={() => setDragging(false)}
        onDrop={onDrop}
        onClick={() => inputRef.current?.click()}
        style={{
          border: `2px dashed ${dragging ? '#1A56DB' : '#E2E8F0'}`,
          borderRadius: 10, padding: '28px 20px',
          textAlign: 'center', cursor: 'pointer',
          background: dragging ? '#EFF6FF' : '#F8FAFF',
          transition: 'all 0.2s', marginBottom: 14,
        }}
      >
        <div style={{ fontSize: 32, marginBottom: 8 }}>📸</div>
        <div style={{ fontSize: 14, fontWeight: 700, color: '#0F172A', marginBottom: 4 }}>
          点击或拖拽上传照片
        </div>
        <div style={{ fontSize: 12, color: '#9CA3AF' }}>
          自动添加水印（桩号·时间·GPS坐标）· 自动生成 Proof 存证
        </div>
        <input
          ref={inputRef} type="file" multiple accept="image/*"
          style={{ display: 'none' }}
          onChange={e => e.target.files && addFiles(e.target.files)}
        />
      </div>

      {/* 预览网格 */}
      {files.length > 0 && (
        <>
          <div style={{
            display: 'grid', gridTemplateColumns: 'repeat(3,1fr)',
            gap: 8, marginBottom: 14,
          }}>
            {files.map((f, idx) => (
              <div key={idx} style={{ position: 'relative', borderRadius: 8, overflow: 'hidden', aspectRatio: '4/3' }}>
                <img
                  src={f.url} alt=""
                  style={{ width: '100%', height: '100%', objectFit: 'cover', display: 'block' }}
                />
                {/* 状态遮罩 */}
                <div style={{
                  position: 'absolute', inset: 0,
                  background: f.status === 'uploading' ? 'rgba(26,86,219,0.3)'
                            : f.status === 'done'      ? 'rgba(5,150,105,0.2)'
                            : f.status === 'error'     ? 'rgba(220,38,38,0.3)'
                            : 'transparent',
                  display: 'flex', alignItems: 'center', justifyContent: 'center',
                  fontSize: 24,
                }}>
                  {f.status === 'uploading' && '⏳'}
                  {f.status === 'done'      && '✅'}
                  {f.status === 'error'     && '❌'}
                </div>
                {/* Proof 角标 */}
                {f.proof_id && (
                  <div style={{
                    position: 'absolute', bottom: 0, left: 0, right: 0,
                    background: 'rgba(0,0,0,0.65)',
                    padding: '3px 6px',
                    fontFamily: 'monospace', fontSize: 12, color: '#F59E0B',
                  }}>
                    {f.proof_id.slice(0, 20)}
                  </div>
                )}
                {/* 删除按钮 */}
                {f.status === 'pending' && (
                  <button
                    onClick={e => { e.stopPropagation(); removeFile(idx) }}
                    style={{
                      position: 'absolute', top: 4, right: 4,
                      width: 22, height: 22, borderRadius: '50%',
                      background: 'rgba(220,38,38,0.85)', color: '#fff',
                      border: 'none', cursor: 'pointer', fontSize: 12,
                      display: 'flex', alignItems: 'center', justifyContent: 'center',
                    }}
                  >✕</button>
                )}
              </div>
            ))}
          </div>

          {/* 操作栏 */}
          <div style={{ display: 'flex', gap: 10, alignItems: 'center' }}>
            <Button
              onClick={uploadAll}
              disabled={uploading || pending === 0}
              icon="🚀" fullWidth
            >
              {uploading
                ? '上传中...'
                : `上传 ${pending} 张照片`}
            </Button>
            <Button
              variant="secondary"
              onClick={() => { files.forEach(f => URL.revokeObjectURL(f.url)); setFiles([]) }}
            >
              清空
            </Button>
          </div>

          {/* 统计 */}
          {done > 0 && (
            <div style={{
              marginTop: 10, padding: '8px 12px',
              background: '#ECFDF5', borderRadius: 8,
              fontSize: 12, color: '#059669', fontWeight: 700,
            }}>
              ✅ 已上传 {done} 张，全部生成 Proof 存证
            </div>
          )}
        </>
      )}
    </Card>
  )
}

