import type { DtoRole, Enterprise, User } from '@qcspec/types'

interface LoginFormState {
  account: string
  pass: string
}

interface EnterpriseRegisterFormState {
  name: string
  adminPhone: string
  pass: string
  uscc: string
}

interface LoginResult {
  access_token?: string
  user_id?: string
  name?: string
  dto_role?: string
  enterprise_id?: string
  v_uri?: string
}

interface EnterpriseResult {
  id?: string
  name?: string
  v_uri?: string
  short_name?: string
  plan?: 'basic' | 'pro' | 'enterprise'
  proof_quota?: number
  proof_used?: number
}

interface RegisterEnterpriseResult {
  ok?: boolean
  account?: string
}

interface DoLoginFlowArgs {
  loginForm: LoginFormState
  loginApi: (payload: { email: string; password: string }) => Promise<unknown>
  getEnterpriseApi: (enterpriseId: string) => Promise<unknown>
  setUser: (user: User, enterprise: Enterprise, token: string) => void
  setProjects: (projects: []) => void
  setCurrentProject: (project: null) => void
  setAppReady: (value: boolean) => void
  setLoggingIn: (value: boolean) => void
  showToast: (message: string) => void
}

interface DoLogoutFlowArgs {
  logoutApi: () => Promise<unknown>
  logout: () => void
  setAppReady: (value: boolean) => void
  setLoginTab: (value: 'login' | 'register') => void
  setLoginForm: (value: LoginFormState) => void
  showToast: (message: string) => void
}

interface DoRegisterEnterpriseFlowArgs {
  entForm: EnterpriseRegisterFormState
  registerEnterpriseApi: (payload: {
    name: string
    adminPhone: string
    password: string
    creditCode?: string
  }) => Promise<unknown>
  setLoginForm: (value: LoginFormState) => void
  setEntForm: (value: EnterpriseRegisterFormState) => void
  setLoginTab: (value: 'login' | 'register') => void
  showToast: (message: string) => void
}

const normalizeDtoRole = (value: string | undefined): DtoRole => {
  const role = String(value || '').toUpperCase()
  if (
    role === 'PUBLIC' ||
    role === 'MARKET' ||
    role === 'AI' ||
    role === 'SUPERVISOR' ||
    role === 'OWNER' ||
    role === 'REGULATOR'
  ) {
    return role
  }
  return 'PUBLIC'
}

export async function doLoginFlow({
  loginForm,
  loginApi,
  getEnterpriseApi,
  setUser,
  setProjects,
  setCurrentProject,
  setAppReady,
  setLoggingIn,
  showToast,
}: DoLoginFlowArgs): Promise<void> {
  const account = loginForm.account.trim()
  const pass = loginForm.pass
  if (!account || !pass) {
    showToast('请填写账号和密码')
    return
  }

  setLoggingIn(true)
  try {
    const loginRes = (await loginApi({
      email: account,
      password: pass,
    })) as LoginResult | null

    if (!loginRes?.access_token || !loginRes.user_id || !loginRes.enterprise_id) {
      return
    }

    const enterpriseRes = (await getEnterpriseApi(loginRes.enterprise_id)) as EnterpriseResult | null

    setUser(
      {
        id: loginRes.user_id,
        enterprise_id: loginRes.enterprise_id,
        v_uri: loginRes.v_uri || '',
        name: loginRes.name || account,
        email: account,
        dto_role: normalizeDtoRole(loginRes.dto_role),
        title: undefined,
      },
      {
        id: enterpriseRes?.id || loginRes.enterprise_id,
        name: enterpriseRes?.name || '企业',
        v_uri: enterpriseRes?.v_uri || 'v://cn/enterprise/',
        short_name: enterpriseRes?.short_name,
        plan: enterpriseRes?.plan || 'enterprise',
        proof_quota: Number(enterpriseRes?.proof_quota || 0),
        proof_used: Number(enterpriseRes?.proof_used || 0),
      },
      loginRes.access_token
    )

    setProjects([])
    setCurrentProject(null)
    setAppReady(true)
    showToast(`欢迎回来，${loginRes.name || account}`)
  } finally {
    setLoggingIn(false)
  }
}

export async function doLogoutFlow({
  logoutApi,
  logout,
  setAppReady,
  setLoginTab,
  setLoginForm,
  showToast,
}: DoLogoutFlowArgs): Promise<void> {
  try {
    await logoutApi()
  } catch {
    // Ignore remote logout failures and always clear local session.
  }
  logout()
  setAppReady(false)
  setLoginTab('login')
  setLoginForm({ account: '', pass: '' })
  showToast('已退出登录')
}

export async function doRegisterEnterpriseFlow({
  entForm,
  registerEnterpriseApi,
  setLoginForm,
  setEntForm,
  setLoginTab,
  showToast,
}: DoRegisterEnterpriseFlowArgs): Promise<void> {
  const adminPhone = entForm.adminPhone.trim()
  if (!entForm.name || !adminPhone || !entForm.pass) {
    showToast('请完整填写企业注册信息')
    return
  }
  if (adminPhone.includes('@')) {
    showToast('管理员手机号请输入 11 位手机号码，不能填写邮箱')
    return
  }
  if (!/^1\d{10}$/.test(adminPhone)) {
    showToast('管理员手机号格式不正确，请输入 11 位手机号码')
    return
  }

  const res = (await registerEnterpriseApi({
    name: entForm.name.trim(),
    adminPhone,
    password: entForm.pass,
    creditCode: entForm.uscc.trim() || undefined,
  })) as RegisterEnterpriseResult | null

  if (!res?.ok) return

  setLoginForm({
    account: res.account || adminPhone,
    pass: entForm.pass,
  })
  setEntForm({ name: '', adminPhone: '', pass: '', uscc: '' })
  showToast('企业注册成功，请使用管理员账号登录')
  setLoginTab('login')
}

