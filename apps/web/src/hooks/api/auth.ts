import { useCallback } from 'react'
import { type ApiRequestOptions, useRequest } from './base'

export function useAuthApi() {
  const { request, loading } = useRequest()

  const login = useCallback(async (body: { email: string; password: string }) => {
    return request('/v1/auth/login', {
      method: 'POST',
      body: JSON.stringify(body),
      timeoutMs: 8000,
    })
  }, [request])

  const me = useCallback(async (options: ApiRequestOptions = {}) => {
    return request('/v1/auth/me', options)
  }, [request])

  const getEnterprise = useCallback(async (enterprise_id: string, options: ApiRequestOptions = {}) => {
    return request(`/v1/auth/enterprise/${enterprise_id}`, { timeoutMs: 8000, ...options })
  }, [request])

  const logout = useCallback(async () => {
    return request('/v1/auth/logout', {
      method: 'POST',
    })
  }, [request])

  const registerEnterprise = useCallback(async (body: {
    name: string
    adminPhone: string
    password: string
    creditCode?: string
    adminEmail?: string
    adminName?: string
  }) => {
    return request('/v1/auth/register-enterprise', {
      method: 'POST',
      body: JSON.stringify(body),
    })
  }, [request])

  return { login, me, getEnterprise, logout, registerEnterprise, loading }
}
