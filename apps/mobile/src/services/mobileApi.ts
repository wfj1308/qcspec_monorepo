const API_BASE = String(import.meta.env.VITE_API_URL || '')

function apiUrl(path: string) {
  const base = String(API_BASE || '').replace(/\/+$/, '')
  return base ? `${base}${path}` : path
}

function readAuthToken() {
  try {
    const direct = [
      localStorage.getItem('qcspec_mobile_token'),
      localStorage.getItem('qcspec_token'),
      sessionStorage.getItem('qcspec_mobile_token'),
      sessionStorage.getItem('qcspec_token'),
    ]
      .map((item) => String(item || '').trim())
      .find((item) => !!item)
    if (direct) return direct

    const persisted = localStorage.getItem('qcspec-auth')
    if (!persisted) return ''
    const parsed = JSON.parse(persisted) as { state?: { token?: string } }
    return String(parsed?.state?.token || '').trim()
  } catch {
    return ''
  }
}

function withAuthHeaders(base?: HeadersInit) {
  const headers = new Headers(base || {})
  const token = readAuthToken()
  if (token && !headers.has('Authorization')) {
    headers.set('Authorization', `Bearer ${token}`)
  }
  return headers
}

async function request<T>(path: string, init: RequestInit = {}): Promise<T> {
  const headers = withAuthHeaders(init.headers)
  if (!headers.has('Content-Type')) headers.set('Content-Type', 'application/json')
  const response = await fetch(apiUrl(path), {
    ...init,
    headers,
  })

  if (!response.ok) {
    const detail = await response.json().catch(() => ({}))
    throw new Error(String((detail as Record<string, unknown>).detail || `HTTP ${response.status}`))
  }

  const text = await response.text()
  return (text ? JSON.parse(text) : {}) as T
}

function blobToDataUrl(blob: Blob) {
  return new Promise<string>((resolve, reject) => {
    const reader = new FileReader()
    reader.onload = () => resolve(String(reader.result || ''))
    reader.onerror = reject
    reader.readAsDataURL(blob)
  })
}

function pickQrImage(value: unknown): string {
  if (typeof value === 'string') {
    if (value.startsWith('data:image') || value.startsWith('http')) return value
    return ''
  }
  if (!value || typeof value !== 'object' || Array.isArray(value)) return ''
  const row = value as Record<string, unknown>
  const candidateKeys = ['qr_code', 'qrCode', 'qrcode', 'image', 'image_url', 'imageUrl', 'data_url', 'dataUrl', 'url']
  for (const key of candidateKeys) {
    const text = row[key]
    if (typeof text === 'string' && text.trim()) {
      if (text.startsWith('data:image') || text.startsWith('http')) return text
    }
  }
  return ''
}

export const mobileApi = {
  getChainStatus() {
    return request<{
      ok?: boolean
      mode?: string
      reason?: string
      checks?: Record<string, boolean>
      server_time?: string
    }>('/api/v1/mobile/chain-status', {
      method: 'GET',
    })
  },
  getMyRole() {
    return request<{ ok?: boolean; role?: string; source?: string; user_name?: string }>('/api/v1/mobile/me-role', {
      method: 'GET',
    })
  },
  getExecutorWorkorders(executorId: string) {
    return request(`/api/v1/mobile/executor/${encodeURIComponent(executorId)}/workorder`, { method: 'GET' })
  },
  getCurrentStep(vUri: string) {
    return request(`/api/v1/mobile/component/${encodeURIComponent(vUri)}/current-step`, { method: 'GET' })
  },
  submitMobile(payload: Record<string, unknown>) {
    return request('/api/v1/mobile/trips/submit-mobile', {
      method: 'POST',
      body: JSON.stringify(payload),
    })
  },
  async getQrCode(vUri: string): Promise<string> {
    const headers = withAuthHeaders({ Accept: 'application/json,image/png,image/jpeg,image/webp' })
    const response = await fetch(apiUrl(`/api/v1/mobile/qrcode/${encodeURIComponent(vUri)}`), {
      method: 'GET',
      headers,
    })
    if (!response.ok) throw new Error(`HTTP ${response.status}`)

    const contentType = response.headers.get('content-type') || ''
    if (contentType.includes('application/json')) {
      const payload = (await response.json().catch(() => ({}))) as unknown
      return pickQrImage(payload)
    }
    if (contentType.startsWith('image/')) {
      const blob = await response.blob()
      return blobToDataUrl(blob)
    }
    const text = await response.text()
    if (text.startsWith('data:image') || text.startsWith('http')) return text
    return ''
  },
  anchorPhoto(payload: Record<string, unknown>) {
    return request('/api/v1/mobile/snappeg/anchor', {
      method: 'POST',
      body: JSON.stringify(payload),
    })
  },
  confirmSignature(payload: {
    provider: 'signpeg' | 'ca'
    componentCode: string
    stepName: string
    role: string
    payload?: Record<string, unknown>
  }) {
    return request<{
      ok?: boolean
      token?: string
      signature?: string
      signed_at?: string
      [key: string]: unknown
    }>('/api/v1/mobile/signature/confirm', {
      method: 'POST',
      body: JSON.stringify({
        provider: payload.provider,
        component_code: payload.componentCode,
        step_name: payload.stepName,
        role: payload.role,
        payload: payload.payload || {},
      }),
    })
  },
  resolveNormref(uri: string) {
    return request<{
      protocol?: Record<string, unknown>
      gates?: Array<Record<string, unknown>>
      [key: string]: unknown
    }>(`/v1/normref/resolve?uri=${encodeURIComponent(uri)}`, { method: 'GET' })
  },
  verifyNormref(payload: {
    protocolUri: string
    actualData: Record<string, unknown>
    designData?: Record<string, unknown>
    context?: Record<string, unknown>
  }) {
    return request<{
      result: 'PASS' | 'FAIL' | 'WARNING'
      failed_gates?: string[]
      explain?: string
      proof_hash?: string
      sealed_at?: string
      [key: string]: unknown
    }>('/v1/normref/verify', {
      method: 'POST',
      body: JSON.stringify({
        protocol_uri: payload.protocolUri,
        actual_data: payload.actualData || {},
        design_data: payload.designData || {},
        context: payload.context || {},
      }),
    })
  },
}
