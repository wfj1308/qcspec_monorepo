import axios, { AxiosError, type AxiosRequestConfig } from 'axios'
import { useAuthStore } from '../../store'

type ActorRole = 'designer' | 'contractor' | 'supervisor' | 'owner' | 'admin'

class DocpegBusinessError extends Error {
  code?: string
  status?: number

  constructor(message: string, options?: { code?: string; status?: number }) {
    super(message)
    this.name = 'DocpegBusinessError'
    this.code = options?.code
    this.status = options?.status
  }
}

const DOCPEG_BASE_URL = String(
  import.meta.env.VITE_DOCPEG_API_BASE || import.meta.env.VITE_DOCPEG_API_URL || 'https://api.docpeg.cn',
).replace(/\/+$/, '')
const DOCPEG_API_KEY = String(import.meta.env.VITE_DOCPEG_API_KEY || '').trim()
const DOCPEG_BEARER_TOKEN = String(import.meta.env.VITE_DOCPEG_BEARER_TOKEN || '').trim()
const DOCPEG_USE_APP_AUTH = String(import.meta.env.VITE_DOCPEG_USE_APP_AUTH || '').trim() === 'true'

const ENV_ACTOR_ROLE = String(import.meta.env.VITE_DOCPEG_ACTOR_ROLE || '').trim()
const ENV_ACTOR_NAME = String(import.meta.env.VITE_DOCPEG_ACTOR_NAME || '').trim()

function mapDtoRoleToActorRole(dtoRole?: string | null): ActorRole {
  const role = String(dtoRole || '').trim().toUpperCase()
  if (role === 'SUPERVISOR') return 'supervisor'
  if (role === 'OWNER') return 'owner'
  if (role === 'REGULATOR') return 'admin'
  if (role === 'MARKET') return 'contractor'
  return 'designer'
}

function resolveActorHeaderState() {
  const state = useAuthStore.getState()
  const user = state.user
  const role = user?.dto_role
    ? mapDtoRoleToActorRole(user.dto_role)
    : (ENV_ACTOR_ROLE || 'designer')
  const name = String(user?.name || user?.email || ENV_ACTOR_NAME || 'designer-user').trim()
  return {
    token: state.token,
    actorRole: role,
    actorName: name,
  }
}

function resolveBusinessMessage(payload: Record<string, unknown>): string {
  const candidates = [payload.detail, payload.message, payload.error, payload.reason]
  for (const candidate of candidates) {
    const text = String(candidate || '').trim()
    if (text) return text
  }
  return 'DocPeg API business validation failed'
}

function assertDocpegOk(data: unknown, status?: number): void {
  if (!data || typeof data !== 'object' || Array.isArray(data)) {
    throw new DocpegBusinessError('Unexpected API response shape', { status })
  }

  const payload = data as Record<string, unknown>
  if (payload.ok !== true) {
    throw new DocpegBusinessError(resolveBusinessMessage(payload), {
      code: String(payload.code || ''),
      status,
    })
  }
}

const instance = axios.create({
  baseURL: DOCPEG_BASE_URL,
  timeout: Number(import.meta.env.VITE_API_TIMEOUT_MS || 30000),
})

instance.interceptors.request.use((config) => {
  const { token, actorRole, actorName } = resolveActorHeaderState()
  const headers = config.headers

  if (!headers.Authorization) {
    if (DOCPEG_BEARER_TOKEN) {
      headers.Authorization = `Bearer ${DOCPEG_BEARER_TOKEN}`
    } else if (DOCPEG_USE_APP_AUTH && token) {
      headers.Authorization = `Bearer ${token}`
    }
  }
  if (DOCPEG_API_KEY && !headers['x-api-key']) {
    headers['x-api-key'] = DOCPEG_API_KEY
  }
  if (!headers['x-actor-role'] && actorRole) {
    headers['x-actor-role'] = actorRole
  }
  if (!headers['x-actor-name'] && actorName) {
    headers['x-actor-name'] = actorName
  }

  return config
})

instance.interceptors.response.use(
  (response) => {
    assertDocpegOk(response.data, response.status)
    return response
  },
  (error: AxiosError<Record<string, unknown>>) => {
    const status = error.response?.status
    const payload = error.response?.data
    const message = payload ? resolveBusinessMessage(payload) : (error.message || 'DocPeg network error')
    return Promise.reject(new DocpegBusinessError(message, { status }))
  },
)

export const docpegHttpClient = {
  get: async <T>(url: string, config?: AxiosRequestConfig): Promise<T> => {
    const response = await instance.get<T>(url, config)
    return response.data
  },
  post: async <T>(url: string, data?: unknown, config?: AxiosRequestConfig): Promise<T> => {
    const response = await instance.post<T>(url, data, config)
    return response.data
  },
  patch: async <T>(url: string, data?: unknown, config?: AxiosRequestConfig): Promise<T> => {
    const response = await instance.patch<T>(url, data, config)
    return response.data
  },
}

export function resolveActorContext() {
  const { actorRole, actorName } = resolveActorHeaderState()
  return {
    actor_role: actorRole,
    actor_name: actorName,
  }
}
