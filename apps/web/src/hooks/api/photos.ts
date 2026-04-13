import { useCallback, useState } from 'react'
import { useUIStore } from '../../store'
import { docpegHttpClient } from '../../services/docpeg/httpClient'

type Dict = Record<string, unknown>

const DOCPEG_UPLOAD_TOKEN = String(import.meta.env.VITE_DOCPEG_UPLOAD_TOKEN || '').trim()
const DOCPEG_UPLOAD_SESSION_TOKEN = String(import.meta.env.VITE_DOCPEG_UPLOAD_SESSION_TOKEN || '').trim()

function asDict(value: unknown): Dict {
  return value && typeof value === 'object' && !Array.isArray(value)
    ? (value as Dict)
    : {}
}

function toText(value: unknown): string {
  return String(value || '').trim()
}

function buildUploadHeaders(): Record<string, string> {
  const headers: Record<string, string> = {}
  if (DOCPEG_UPLOAD_TOKEN) headers['x-upload-token'] = DOCPEG_UPLOAD_TOKEN
  if (DOCPEG_UPLOAD_SESSION_TOKEN) headers['x-upload-session-token'] = DOCPEG_UPLOAD_SESSION_TOKEN
  return headers
}

export function usePhotos() {
  const [uploading, setUploading] = useState(false)
  const { showToast } = useUIStore()

  const upload = useCallback(async (params: {
    file: File
    project_id: string
    enterprise_id: string
    location?: string
    inspection_id?: string
    gps_lat?: number
    gps_lng?: number
  }) => {
    setUploading(true)
    try {
      const form = new FormData()
      form.append('file', params.file)
      form.append('project_id', String(params.project_id || ''))
      form.append('enterprise_id', String(params.enterprise_id || ''))
      if (params.location) form.append('location', params.location)
      if (params.inspection_id) form.append('inspection_id', params.inspection_id)
      if (typeof params.gps_lat === 'number') form.append('gps_lat', String(params.gps_lat))
      if (typeof params.gps_lng === 'number') form.append('gps_lng', String(params.gps_lng))

      const headers = buildUploadHeaders()
      let payload: Dict | null = null

      try {
        payload = await docpegHttpClient.post<Dict>('/api/v1/files/upload', form, { headers })
      } catch {
        payload = await docpegHttpClient.post<Dict>('/upload', form, { headers })
      }

      const row = asDict(payload)
      const fileId =
        toText(row.file_id) ||
        toText(row.photo_id) ||
        toText(row.id) ||
        `FILE-${Date.now()}`

      const storageUrl =
        toText(row.url) ||
        toText(row.storage_url) ||
        toText(row.file_url) ||
        ''

      const proofId = toText(row.proof_id)
      const vUri =
        toText(row.v_uri) ||
        toText(row.uri) ||
        `v://cn.docpeg/project/${params.project_id}/file/${fileId}`

      showToast('照片已上传至同事 API')
      return {
        ok: true,
        photo_id: fileId,
        proof_id: proofId || undefined,
        v_uri: vUri,
        storage_url: storageUrl || undefined,
      }
    } catch (error) {
      const message = error instanceof Error ? error.message : '上传失败'
      showToast(`上传失败：${message}`)
      return null
    } finally {
      setUploading(false)
    }
  }, [showToast])

  const list = useCallback(async (
    _project_id: string,
    _inspection_id?: string,
  ) => {
    return {
      ok: true,
      data: [],
      source: 'docpeg-api-pack-empty',
    }
  }, [])

  const remove = useCallback(async (_photo_id: string) => {
    return {
      ok: false,
      unsupported: true,
      message: '同事 API 文档未提供照片删除接口',
    }
  }, [])

  return { upload, list, remove, uploading }
}
