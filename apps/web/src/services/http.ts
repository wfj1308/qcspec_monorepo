const utf8Decoder =
  typeof TextDecoder !== 'undefined' ? new TextDecoder('utf-8', { fatal: true }) : null

export const API_BASE = import.meta.env.VITE_API_URL || 'http://127.0.0.1:8000'
export const DEFAULT_TIMEOUT_MS = Number(import.meta.env.VITE_API_TIMEOUT_MS || 30000)
const ALLOW_LEGACY_QCSPEC_API = String(import.meta.env.VITE_ALLOW_LEGACY_QCSPEC_API || '').trim() === 'true'

const DOCPEG_API_PATH_RULES: RegExp[] = [
  /^\/openapi\.json$/,
  /^\/health$/,
  /^\/upload$/,
  /^\/projects(?:\/.*)?$/,
  /^\/api\/v1\/execpeg(?:\/.*)?$/,
  /^\/v1\/execpeg(?:\/.*)?$/,
  /^\/api\/v1\/dtorole(?:\/.*)?$/,
  /^\/api\/v1\/layerpeg(?:\/.*)?$/,
  /^\/api\/v1\/triprole(?:\/.*)?$/,
  /^\/api\/v1\/normref\/projects(?:\/.*)?$/,
  /^\/api\/v1\/boqitem\/projects\/[^/]+\/(items|consume|settle)$/,
  /^\/api\/v1\/proof\/[^/]+(?:\/(verify|attachments))?$/,
  /^\/api\/v1\/files\/upload$/,
]

function looksLikeMojibake(input: string): boolean {
  if (!input || /[\u4e00-\u9fff]/.test(input)) return false
  let latinExtended = 0
  for (const ch of input) {
    const code = ch.charCodeAt(0)
    if (code >= 0x00c0 && code <= 0x00ff) latinExtended += 1
  }
  return latinExtended >= 2
}

function decodeLatin1Utf8(input: string): string {
  if (!utf8Decoder || !looksLikeMojibake(input)) return input
  const bytes = new Uint8Array(Array.from(input, (ch) => ch.charCodeAt(0) & 0xff))
  try {
    const decoded = utf8Decoder.decode(bytes)
    return /[\u4e00-\u9fff]/.test(decoded) ? decoded : input
  } catch {
    return input
  }
}

export function normalizeApiPayload<T>(value: T): T {
  if (typeof value === 'string') {
    return decodeLatin1Utf8(value) as T
  }
  if (Array.isArray(value)) {
    return value.map((item) => normalizeApiPayload(item)) as T
  }
  if (value && typeof value === 'object') {
    const entries = Object.entries(value as Record<string, unknown>)
    const repaired: Record<string, unknown> = {}
    for (const [key, val] of entries) {
      repaired[key] = normalizeApiPayload(val)
    }
    return repaired as T
  }
  return value
}

export function withAuthHeaders(token: string | null, base?: HeadersInit): Headers {
  const headers = new Headers(base)
  if (token && !headers.has('Authorization')) {
    headers.set('Authorization', `Bearer ${token}`)
  }
  return headers
}

export type ApiRequestOptions = RequestInit & {
  timeoutMs?: number
  skipAuthRedirect?: boolean
}

function normalizePath(path: string): string {
  const raw = String(path || '').trim()
  if (!raw) return raw
  const withoutHash = raw.split('#')[0]
  return withoutHash.split('?')[0]
}

export function isDocpegApiPath(path: string): boolean {
  const normalized = normalizePath(path)
  if (!normalized.startsWith('/')) return false
  return DOCPEG_API_PATH_RULES.some((rule) => rule.test(normalized))
}

export function assertDocpegApiPath(path: string): void {
  if (ALLOW_LEGACY_QCSPEC_API) return
  if (isDocpegApiPath(path)) return
  throw new Error(`DocPeg strict mode blocked non-spec endpoint: ${path}`)
}

type ApiRequestContext = {
  token: string | null
  logout: () => void
  path: string
  skipAuthRedirect?: boolean
}

function parseApiErrorPayload(data: unknown, status: number): Error {
  if (data && typeof data === 'object' && 'detail' in data) {
    const detail = String((data as { detail?: unknown }).detail || '').trim()
    if (detail) return new Error(detail)
  }
  return new Error(`HTTP ${status}`)
}

export async function requestApiJson<T>(
  path: string,
  options: ApiRequestOptions,
  context: ApiRequestContext,
): Promise<T> {
  const { timeoutMs: timeoutOverrideMs, skipAuthRedirect, ...fetchOptions } = options
  const { token, logout } = context
  const controller = new AbortController()
  const timeoutMs = Number(timeoutOverrideMs || DEFAULT_TIMEOUT_MS)
  const timeoutId = window.setTimeout(() => controller.abort(), timeoutMs)

  if (fetchOptions.signal) {
    if (fetchOptions.signal.aborted) controller.abort()
    else fetchOptions.signal.addEventListener('abort', () => controller.abort(), { once: true })
  }

  try {
    assertDocpegApiPath(path)

    const headers = withAuthHeaders(token, fetchOptions.headers)
    const isFormData = typeof FormData !== 'undefined' && fetchOptions.body instanceof FormData
    if (!headers.has('Content-Type') && !isFormData) {
      headers.set('Content-Type', 'application/json')
    }

    const response = await fetch(`${API_BASE}${path}`, {
      ...fetchOptions,
      headers,
      signal: controller.signal,
    })

    if (!response.ok) {
      const shouldHandleAsSessionExpired = response.status === 401 && !!token
      const shouldHandleAuthMeServerError = false
      const shouldSkipRedirect = skipAuthRedirect || context.skipAuthRedirect

      if (shouldHandleAsSessionExpired && !shouldSkipRedirect) {
        logout()
        throw new Error('Login expired. Please sign in again.')
      }
      if (shouldHandleAuthMeServerError && !shouldSkipRedirect) {
        logout()
        throw new Error('Session invalid. Please sign in again.')
      }

      const errorPayload = await response.json().catch(() => ({}))
      throw parseApiErrorPayload(errorPayload, response.status)
    }

    const json = await response.json()
    return normalizeApiPayload(json as T)
  } finally {
    window.clearTimeout(timeoutId)
  }
}
