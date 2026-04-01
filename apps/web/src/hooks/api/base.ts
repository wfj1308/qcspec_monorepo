import { useCallback, useState } from 'react'
import { useAuthStore, useUIStore } from '../../store'

export const API_BASE = import.meta.env.VITE_API_URL || 'http://127.0.0.1:8000'
const DEFAULT_TIMEOUT_MS = Number(import.meta.env.VITE_API_TIMEOUT_MS || 30000)
const inflightGetRequests = new Map<string, Promise<unknown>>()

const utf8Decoder = typeof TextDecoder !== 'undefined' ? new TextDecoder('utf-8', { fatal: true }) : null

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

export function withAuthHeaders(token: string | null, base?: HeadersInit) {
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

export type ApiRequestFn = (
  path: string,
  options?: ApiRequestOptions,
) => Promise<unknown | null>

export function useRequest<T = unknown>() {
  const [data, setData] = useState<T | null>(null)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const { showToast } = useUIStore()
  const token = useAuthStore((s) => s.token)
  const logout = useAuthStore((s) => s.logout)

  const request = useCallback(async (
    path: string,
    options: ApiRequestOptions = {},
  ): Promise<T | null> => {
    const { timeoutMs: timeoutOverrideMs, skipAuthRedirect, ...fetchOptions } = options
    const method = String(fetchOptions.method || 'GET').toUpperCase()
    const dedupeKey = `${method}:${path}:${token || ''}`
    const canDedupe = method === 'GET' && !fetchOptions.signal
    if (canDedupe) {
      const inFlight = inflightGetRequests.get(dedupeKey) as Promise<T | null> | undefined
      if (inFlight) return inFlight
    }

    const run = (async (): Promise<T | null> => {
      setLoading(true)
      setError(null)
      const controller = new AbortController()
      const timeoutMs = Number(timeoutOverrideMs || DEFAULT_TIMEOUT_MS)
      const timeoutId = window.setTimeout(() => controller.abort(), timeoutMs)

      if (fetchOptions.signal) {
        if (fetchOptions.signal.aborted) controller.abort()
        else fetchOptions.signal.addEventListener('abort', () => controller.abort(), { once: true })
      }

      try {
        const headers = withAuthHeaders(token, fetchOptions.headers)
        const isFormData = typeof FormData !== 'undefined' && fetchOptions.body instanceof FormData
        if (!headers.has('Content-Type') && !isFormData) {
          headers.set('Content-Type', 'application/json')
        }
        const res = await fetch(`${API_BASE}${path}`, {
          headers,
          ...fetchOptions,
          signal: controller.signal,
        })
        if (!res.ok) {
          const isAuthMeRequest = path.startsWith('/v1/auth/me')
          const shouldHandleAsSessionExpired =
            (res.status === 401 || res.status === 403) &&
            !!token &&
            !path.startsWith('/v1/auth/login') &&
            !path.startsWith('/v1/auth/register-enterprise')
          const shouldHandleAuthMeServerError =
            res.status >= 500 &&
            !!token &&
            isAuthMeRequest
          if (shouldHandleAsSessionExpired && !skipAuthRedirect) {
            logout()
            throw new Error('Login expired. Please sign in again.')
          }
          if (shouldHandleAuthMeServerError && !skipAuthRedirect) {
            logout()
            throw new Error('Session invalid. Please sign in again.')
          }
          const err = await res.json().catch(() => ({}))
          throw new Error(err.detail || `HTTP ${res.status}`)
        }
        const json = await res.json()
        const normalized = normalizeApiPayload(json)
        setData(normalized)
        return normalized
      } catch (e: unknown) {
        if (fetchOptions.signal?.aborted) {
          return null
        }
        const msg = e instanceof DOMException && e.name === 'AbortError'
          ? 'Request timed out. Please retry.'
          : (e instanceof Error ? e.message : 'Request failed')
        setError(msg)
        showToast(`[Error] ${msg}`)
        return null
      } finally {
        window.clearTimeout(timeoutId)
        setLoading(false)
      }
    })()

    if (canDedupe) {
      inflightGetRequests.set(dedupeKey, run as Promise<unknown>)
      run.finally(() => {
        inflightGetRequests.delete(dedupeKey)
      })
    }

    return run
  }, [showToast, token, logout])

  return { data, loading, error, request }
}
