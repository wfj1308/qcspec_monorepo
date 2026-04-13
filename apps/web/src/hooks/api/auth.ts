import { useCallback } from 'react'
import { type ApiRequestOptions } from './base'

export function useAuthApi() {
  const loading = false

  const login = useCallback(async (_body: { email: string; password: string }) => {
    return null
  }, [])

  const me = useCallback(async (_options: ApiRequestOptions = {}) => {
    return null
  }, [])

  const getEnterprise = useCallback(async (_enterprise_id: string, _options: ApiRequestOptions = {}) => {
    return null
  }, [])

  const logout = useCallback(async () => {
    return null
  }, [])

  return { login, me, getEnterprise, logout, loading }
}


