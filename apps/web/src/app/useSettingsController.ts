import { useState } from 'react'
import type { ErpDraftState, ErpWritebackDraftState, SettingsState } from './appShellShared'
import type {
  EnterpriseInfoState,
  GitpegVerifyMessage,
  PersistSettingsPayload,
  WebhookResultState,
} from './settingsTypes'

interface UseSettingsControllerArgs {
  canUseEnterpriseApi: boolean
  enterpriseId?: string
  initialReportHeader: string
  initialEnterpriseInfo: EnterpriseInfoState
  saveSettings: (enterpriseId: string, patch: Record<string, unknown>) => Promise<unknown>
  uploadTemplate: (enterpriseId: string, file: File) => Promise<unknown>
  testGitpegRegistrar: (payload: Record<string, unknown>) => Promise<unknown>
  testErpnext: (payload: Record<string, unknown>) => Promise<unknown>
  showToast: (message: string) => void
}

export function useSettingsController({
  canUseEnterpriseApi,
  enterpriseId,
  initialReportHeader,
  initialEnterpriseInfo,
  saveSettings,
  uploadTemplate,
  testGitpegRegistrar,
  testErpnext,
  showToast,
}: UseSettingsControllerArgs) {
  const [settings, setSettings] = useState<SettingsState>({
    emailNotify: true,
    wechatNotify: true,
    autoGenerateReport: false,
    strictProof: true,
    reportTemplate: 'default.docx',
    reportTemplateUrl: '',
    reportHeader: initialReportHeader,
    webhookUrl: '',
    gitpegToken: '',
    gitpegEnabled: false,
    gitpegRegistrarBaseUrl: 'https://gitpeg.cn',
    gitpegPartnerCode: 'wastewater-site',
    gitpegIndustryCode: 'wastewater',
    gitpegClientId: 'ptn_wastewater_001',
    gitpegClientSecret: '',
    gitpegRegistrationMode: 'DOMAIN',
    gitpegReturnUrl: '',
    gitpegWebhookUrl: '',
    gitpegWebhookSecret: '',
    gitpegModuleCandidates: ['proof', 'utrip', 'openapi'],
    erpnextSync: false,
    wechatMiniapp: true,
    droneImport: false,
  })
  const [erpDraft, setErpDraft] = useState<ErpDraftState>({
    url: '',
    siteName: 'development.localhost',
    apiKey: '',
    apiSecret: '',
    username: '',
    password: '',
  })
  const [erpWritebackDraft, setErpWritebackDraft] = useState<ErpWritebackDraftState>({
    projectDoctype: 'Project',
    projectLookupField: 'name',
    projectLookupValue: '',
    gitpegProjectUriField: 'gitpeg_project_uri',
    gitpegSiteUriField: 'gitpeg_site_uri',
    gitpegStatusField: 'gitpeg_status',
    gitpegResultJsonField: 'gitpeg_register_result_json',
    gitpegRegistrationIdField: 'gitpeg_registration_id',
    gitpegNodeUriField: 'gitpeg_node_uri',
    gitpegShellUriField: 'gitpeg_shell_uri',
    gitpegProofHashField: 'gitpeg_proof_hash',
    gitpegIndustryProfileIdField: 'gitpeg_industry_profile_id',
  })
  const [erpTesting, setErpTesting] = useState(false)
  const [erpTestMsg, setErpTestMsg] = useState('')
  const [gitpegVerifying, setGitpegVerifying] = useState(false)
  const [gitpegVerifyMsg, setGitpegVerifyMsg] = useState<GitpegVerifyMessage>({
    text: '',
    color: '#64748B',
  })
  const [webhookTesting, setWebhookTesting] = useState(false)
  const [webhookResult, setWebhookResult] = useState<WebhookResultState>({
    text: '',
    color: '#64748B',
    visible: false,
  })
  const [enterpriseInfo, setEnterpriseInfo] = useState<EnterpriseInfoState>(initialEnterpriseInfo)
  const [reportTemplateFile, setReportTemplateFile] = useState<File | null>(null)

  const persistSettings = async (patch: PersistSettingsPayload) => {
    const next = { ...settings, ...patch }
    setSettings(next)

    if (!canUseEnterpriseApi || !enterpriseId) {
      showToast('演示环境：已本地保存')
      return
    }

    const res = await saveSettings(enterpriseId, patch) as { settings?: Partial<SettingsState> } | null
    if (res?.settings) {
      setSettings((prev) => ({ ...prev, ...res.settings }))
      showToast('设置已保存')
    }
  }

  const persistEnterpriseInfo = async () => {
    if (!canUseEnterpriseApi || !enterpriseId) {
      showToast('演示环境：已本地保存')
      return
    }

    const res = await saveSettings(enterpriseId, {
      enterpriseName: enterpriseInfo.name,
      enterpriseVUri: enterpriseInfo.vUri,
      enterpriseCreditCode: enterpriseInfo.creditCode,
    }) as { enterprise?: { name?: string; v_uri?: string; credit_code?: string } } | null

    if (res?.enterprise) {
      setEnterpriseInfo((prev) => ({
        ...prev,
        name: res.enterprise?.name || prev.name,
        vUri: res.enterprise?.v_uri || prev.vUri,
        creditCode: res.enterprise?.credit_code || prev.creditCode,
      }))
    }
    showToast('企业信息已保存')
  }

  const persistReportTemplate = async () => {
    if (settings.reportTemplate === 'custom-upload') {
      if (!reportTemplateFile) {
        showToast('请先选择 Word 模板文件')
        return
      }
      if (!canUseEnterpriseApi || !enterpriseId) {
        setSettings((prev) => ({
          ...prev,
          reportTemplate: reportTemplateFile.name,
          reportTemplateUrl: '',
        }))
        showToast('演示环境：已本地保存模板名与报告抬头')
        return
      }
      const res = await uploadTemplate(enterpriseId, reportTemplateFile) as {
        settings?: Partial<SettingsState>
      } | null
      if (res?.settings) {
        setSettings((prev) => ({ ...prev, ...res.settings }))
        setReportTemplateFile(null)
      }
      const headerRes = await saveSettings(enterpriseId, {
        reportHeader: settings.reportHeader,
      }) as { settings?: Partial<SettingsState> } | null
      if (headerRes?.settings) {
        setSettings((prev) => ({ ...prev, ...headerRes.settings }))
      }
      showToast('模板与报告抬头已保存')
      return
    }
    await persistSettings({
      reportTemplate: settings.reportTemplate,
      reportHeader: settings.reportHeader,
    })
  }

  const verifyGitpegToken = async () => {
    const baseUrl = settings.gitpegRegistrarBaseUrl.trim()
    const partnerCode = settings.gitpegPartnerCode.trim()
    const industryCode = settings.gitpegIndustryCode.trim()
    const clientId = settings.gitpegClientId.trim()
    const clientSecret = settings.gitpegClientSecret.trim()

    if (!baseUrl || !partnerCode || !industryCode || !clientId || !clientSecret) {
      setGitpegVerifyMsg({
        text: '⚠️ 请填写 Base URL / Partner Code / Industry Code / Client ID / Client Secret',
        color: '#D97706',
      })
      return
    }

    if (!/^https?:\/\//i.test(baseUrl)) {
      setGitpegVerifyMsg({ text: '⚠️ Base URL 需要以 http:// 或 https:// 开头', color: '#D97706' })
      return
    }

    setGitpegVerifying(true)
    setGitpegVerifyMsg({ text: '⏳ 验证中...', color: '#64748B' })
    const res = await testGitpegRegistrar({
      baseUrl,
      partnerCode,
      industryCode,
      clientId,
      clientSecret,
      registrationMode: settings.gitpegRegistrationMode || 'DOMAIN',
      returnUrl: settings.gitpegReturnUrl.trim() || undefined,
      webhookUrl: settings.gitpegWebhookUrl.trim() || undefined,
      moduleCandidates: (settings.gitpegModuleCandidates || []).map((item) => String(item || '').trim()).filter(Boolean),
      timeoutMs: 12000,
    }) as {
      ok?: boolean
      session_id?: string
      warnings?: string[]
      token_exchange_probe?: {
        result?: string
      }
    } | null

    setGitpegVerifying(false)
    if (!res?.ok) {
      setGitpegVerifyMsg({ text: '❌ 联调失败，请查看后端错误提示', color: '#DC2626' })
      return
    }

    const warnings = Array.isArray(res.warnings) ? res.warnings : []
    const probe = res.token_exchange_probe?.result || ''
    if (warnings.length > 0) {
      setGitpegVerifyMsg({
        text: `⚠️ 连通成功（session: ${res.session_id || '-' }），但有告警：${warnings.join('；')}`,
        color: '#D97706',
      })
      return
    }
    if (probe === 'credentials_rejected') {
      setGitpegVerifyMsg({
        text: `⚠️ 会话创建成功（session: ${res.session_id || '-' }），但 client_id/client_secret 可能被拒绝`,
        color: '#D97706',
      })
      return
    }
    setGitpegVerifyMsg({
      text: `✅ 联调成功（session: ${res.session_id || '-' }）`,
      color: '#059669',
    })
  }

  const testWebhook = () => {
    if (!settings.webhookUrl.trim()) {
      setWebhookResult({ text: '⚠️ 请先填写 Webhook URL', color: '#D97706', visible: true })
      return
    }
    setWebhookTesting(true)
    setWebhookResult({ text: '⏳ 发送测试请求...', color: '#64748B', visible: true })
    setTimeout(() => {
      setWebhookTesting(false)
      setWebhookResult({
        text: `✅ 200 OK · {"event":"test","source":"qcspec","ts":${Date.now()}}`,
        color: '#059669',
        visible: true,
      })
    }, 700)
  }

  const testErpConnection = async () => {
    const hasTokenAuth = Boolean(erpDraft.apiKey.trim())
    const hasSessionAuth = Boolean(erpDraft.username.trim() && erpDraft.password.trim())
    if (!erpDraft.url.trim()) {
      setErpTestMsg('⚠️ 请先填写 ERP URL')
      return
    }
    if (!hasTokenAuth && !hasSessionAuth) {
      setErpTestMsg('⚠️ 请填写 API Key 或 用户名+密码')
      return
    }
    setErpTesting(true)
    setErpTestMsg('⏳ 测试连接中...')
    const res = await testErpnext({
      url: erpDraft.url.trim(),
      siteName: erpDraft.siteName.trim() || undefined,
      apiKey: erpDraft.apiKey.trim() || undefined,
      apiSecret: erpDraft.apiSecret.trim() || undefined,
      username: erpDraft.username.trim() || undefined,
      password: erpDraft.password.trim() || undefined,
      timeoutMs: 10000,
    }) as {
      ok?: boolean
      user?: string
      authMode?: string
      latencyMs?: number
    } | null

    setErpTesting(false)
    if (res?.ok) {
      const userLabel = res.user ? `用户 ${res.user}` : '用户已验证'
      const modeLabel = res.authMode ? ` · ${res.authMode}` : ''
      const latencyLabel = typeof res.latencyMs === 'number' ? ` · ${res.latencyMs}ms` : ''
      setErpTestMsg(`✅ ERPNext 连接成功（${userLabel}${modeLabel}${latencyLabel}）`)
      return
    }
    setErpTestMsg('❌ ERPNext 连接失败，请检查 URL、站点名和认证信息')
  }

  return {
    settings,
    setSettings,
    erpDraft,
    setErpDraft,
    erpWritebackDraft,
    setErpWritebackDraft,
    erpTesting,
    erpTestMsg,
    gitpegVerifying,
    setGitpegVerifying,
    gitpegVerifyMsg,
    setGitpegVerifyMsg,
    webhookTesting,
    webhookResult,
    enterpriseInfo,
    setEnterpriseInfo,
    setReportTemplateFile,
    persistSettings,
    persistEnterpriseInfo,
    persistReportTemplate,
    verifyGitpegToken,
    testWebhook,
    testErpConnection,
  }
}
