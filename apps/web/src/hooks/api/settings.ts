import { useCallback } from 'react'
import { useUIStore } from '../../store'
import { docpegHttpClient } from '../../services/docpeg/httpClient'

type SettingsPatch = {
  enterpriseName?: string
  enterpriseVUri?: string
  enterpriseCreditCode?: string
  emailNotify?: boolean
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
}

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

function uploadHeaders(): Record<string, string> {
  const headers: Record<string, string> = {}
  if (DOCPEG_UPLOAD_TOKEN) headers['x-upload-token'] = DOCPEG_UPLOAD_TOKEN
  if (DOCPEG_UPLOAD_SESSION_TOKEN) headers['x-upload-session-token'] = DOCPEG_UPLOAD_SESSION_TOKEN
  return headers
}

export function useSettings() {
  const { showToast } = useUIStore()

  const getSettings = useCallback(async (_enterprise_id: string) => {
    return {
      ok: true,
      settings: {},
      enterprise: {
        name: '',
        v_uri: '',
        credit_code: '',
      },
      source: 'docpeg-api-pack-empty',
    }
  }, [])

  const saveSettings = useCallback(async (_enterprise_id: string, body: SettingsPatch) => {
    const patch = { ...(body || {}) }
    return {
      ok: true,
      settings: patch,
      enterprise: {
        name: String(patch.enterpriseName || ''),
        v_uri: String(patch.enterpriseVUri || ''),
        credit_code: String(patch.enterpriseCreditCode || ''),
      },
      unsupported: true,
      source: 'docpeg-api-pack-placeholder',
    }
  }, [])

  const testErpnext = useCallback(async (_body: {
    url: string
    siteName?: string
    apiKey?: string
    apiSecret?: string
    username?: string
    password?: string
    timeoutMs?: number
  }) => {
    return {
      ok: false,
      unsupported: true,
      message: '同事 API 暂未提供 ERPNext 测试接口',
    }
  }, [])

  const testGitpegRegistrar = useCallback(async (_body: {
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
    return {
      ok: false,
      unsupported: true,
      message: '同事 API 暂未提供 GitPeg 测试接口',
    }
  }, [])

  const uploadTemplate = useCallback(async (_enterprise_id: string, file: File) => {
    try {
      const form = new FormData()
      form.append('file', file)

      const headers = uploadHeaders()
      let payload: Dict | null = null

      try {
        payload = await docpegHttpClient.post<Dict>('/api/v1/files/upload', form, { headers })
      } catch {
        payload = await docpegHttpClient.post<Dict>('/upload', form, { headers })
      }

      const row = asDict(payload)
      const reportTemplateUrl =
        toText(row.url) ||
        toText(row.storage_url) ||
        toText(row.file_url) ||
        ''

      return {
        ok: true,
        settings: {
          reportTemplate: file.name,
          reportTemplateUrl,
        },
      }
    } catch (error) {
      const message = error instanceof Error ? error.message : '上传失败'
      showToast(`模板上传失败：${message}`)
      return {
        ok: true,
        settings: {
          reportTemplate: file.name,
          reportTemplateUrl: '',
        },
        unsupported: true,
      }
    }
  }, [showToast])

  return { getSettings, saveSettings, testErpnext, testGitpegRegistrar, uploadTemplate, loading: false }
}
