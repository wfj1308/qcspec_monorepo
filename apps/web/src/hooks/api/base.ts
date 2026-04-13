import { useCallback, useState } from 'react'
import { useAuthStore, useUIStore } from '../../store'
import {
  API_BASE,
  assertDocpegApiPath,
  normalizeApiPayload,
  requestApiJson,
  withAuthHeaders,
  type ApiRequestOptions,
} from '../../services/http'

const inflightGetRequests = new Map<string, Promise<unknown>>()
export { API_BASE, assertDocpegApiPath, normalizeApiPayload, withAuthHeaders, type ApiRequestOptions }

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

      try {
        const normalized = await requestApiJson<T>(
          path,
          {
            ...fetchOptions,
            timeoutMs: timeoutOverrideMs,
            skipAuthRedirect,
          },
          {
            token,
            logout,
            path,
            skipAuthRedirect,
          },
        )
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
