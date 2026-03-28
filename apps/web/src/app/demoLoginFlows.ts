import { DEMO_ENTERPRISE, DEMO_PROJECTS, QUICK_LOGIN_ACCOUNTS, QUICK_USERS } from './appShellShared'

type QuickUserKey = keyof typeof QUICK_USERS

interface LoginFormState {
  account: string
  pass: string
}

interface DoDemoLoginFlowArgs {
  key?: QuickUserKey
  hasProjects: boolean
  setUser: (user: (typeof QUICK_USERS)[QuickUserKey], enterprise: typeof DEMO_ENTERPRISE, token: string) => void
  setProjects: (projects: typeof DEMO_PROJECTS) => void
  setCurrentProject: (project: (typeof DEMO_PROJECTS)[number] | null) => void
  setAppReady: (value: boolean) => void
  showToast: (message: string) => void
}

interface FillQuickLoginFlowArgs {
  key: QuickUserKey
  setLoginForm: (value: LoginFormState) => void
  showToast: (message: string) => void
}

export function doDemoLoginFlow({
  key = 'admin',
  hasProjects,
  setUser,
  setProjects,
  setCurrentProject,
  setAppReady,
  showToast,
}: DoDemoLoginFlowArgs): void {
  const user = QUICK_USERS[key]
  setUser(user, DEMO_ENTERPRISE, `demo-token-${key}`)
  if (!hasProjects) {
    setProjects(DEMO_PROJECTS)
    setCurrentProject(DEMO_PROJECTS[0])
  }
  setAppReady(true)
  showToast(`欢迎回来，${user.name}`)
}

export function fillQuickLoginFlow({
  key,
  setLoginForm,
  showToast,
}: FillQuickLoginFlowArgs): void {
  const preset = QUICK_LOGIN_ACCOUNTS.find((item) => item.key === key)
  if (!preset) return
  setLoginForm({
    account: preset.account,
    pass: preset.password,
  })
  showToast(`已填充 ${preset.roleLabel} 账号信息`)
}

export function getQuickLoginOptions() {
  return QUICK_LOGIN_ACCOUNTS.map((item) => ({
    ...item,
    profileName: QUICK_USERS[item.key].name,
  }))
}
