import { useCallback } from 'react'
import { useAuthStore, useUIStore } from '../../store'
import { API_BASE, useRequest, withAuthHeaders } from './base'

export function useSettings() {
  const { request, loading } = useRequest()
  const { showToast } = useUIStore()
  const token = useAuthStore((s) => s.token)
  const logout = useAuthStore((s) => s.logout)

  const getSettings = useCallback(async (enterprise_id: string) => {
    return request(`/v1/settings/?enterprise_id=${enterprise_id}`)
  }, [request])

  const saveSettings = useCallback(async (enterprise_id: string, body: {
    enterpriseName?: string
    enterpriseVUri?: string
    enterpriseCreditCode?: string
    emailNotify?: boolean
    wechatNotify?: boolean
    autoGenerateReport?: boolean
    strictProof?: boolean
    reportTemplate?: string
    reportHeader?: string
    webhookUrl?: string
    gitpegToken?: string
    gitpegEnabled?: boolean
    gitpegRegistrarBaseUrl?: string
    gitpegPartnerCode?: string
    gitpegIndustryCode?: string
    gitpegClientId?: string
    gitpegClientSecret?: string
    gitpegRegistrationMode?: string
    gitpegReturnUrl?: string
    gitpegWebhookUrl?: string
    gitpegWebhookSecret?: string
    gitpegModuleCandidates?: string[]
    erpnextSync?: boolean
    erpnextUrl?: string
    erpnextSiteName?: string
    erpnextApiKey?: string
    erpnextApiSecret?: string
    erpnextUsername?: string
    erpnextPassword?: string
    erpnextProjectDoctype?: string
    erpnextProjectLookupField?: string
    erpnextProjectLookupValue?: string
    erpnextGitpegProjectUriField?: string
    erpnextGitpegSiteUriField?: string
    erpnextGitpegStatusField?: string
    erpnextGitpegResultJsonField?: string
    erpnextGitpegRegistrationIdField?: string
    erpnextGitpegNodeUriField?: string
    erpnextGitpegShellUriField?: string
    erpnextGitpegProofHashField?: string
    erpnextGitpegIndustryProfileIdField?: string
    wechatMiniapp?: boolean
    droneImport?: boolean
    permissionMatrix?: Array<{
      role: string
      view: boolean
      input: boolean
      approve: boolean
      manage: boolean
      settle: boolean
      regulator: boolean
    }>
  }) => {
    return request(`/v1/settings/?enterprise_id=${enterprise_id}`, {
      method: 'PATCH',
      body: JSON.stringify(body),
    })
  }, [request])

  const testErpnext = useCallback(async (body: {
    url: string
    siteName?: string
    apiKey?: string
    apiSecret?: string
    username?: string
    password?: string
    timeoutMs?: number
  }) => {
    return request('/v1/settings/erpnext/test', {
      method: 'POST',
      body: JSON.stringify(body),
    })
  }, [request])

  const testGitpegRegistrar = useCallback(async (body: {
    baseUrl: string
    partnerCode: string
    industryCode: string
    clientId?: string
    clientSecret?: string
    registrationMode?: string
    returnUrl?: string
    webhookUrl?: string
    moduleCandidates?: string[]
    timeoutMs?: number
  }) => {
    return request('/v1/settings/gitpeg/test', {
      method: 'POST',
      body: JSON.stringify(body),
    })
  }, [request])

  const uploadTemplate = useCallback(async (enterprise_id: string, file: File) => {
    try {
      const form = new FormData()
      form.append('enterprise_id', enterprise_id)
      form.append('file', file)
      const res = await fetch(`${API_BASE}/v1/settings/template/upload`, {
        method: 'POST',
        body: form,
        headers: withAuthHeaders(token),
      })
      if (res.status === 401 || res.status === 403) {
        logout()
        throw new Error('Login expired. Please sign in again.')
      }
      if (!res.ok) {
        const err = await res.json().catch(() => ({}))
        throw new Error(err.detail || `HTTP ${res.status}`)
      }
      return await res.json()
    } catch (e: unknown) {
      const msg = e instanceof Error ? e.message : 'Template upload failed'
      showToast(`[Error] ${msg}`)
      return null
    }
  }, [showToast, token, logout])

  return { getSettings, saveSettings, testErpnext, testGitpegRegistrar, uploadTemplate, loading }
}
