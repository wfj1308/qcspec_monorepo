import { useEffect, useState } from 'react'
import type { Enterprise, Project, User } from '@qcspec/types'

type SessionMeResponse = {
  id?: string
  name?: string
  email?: string
  title?: string
  dto_role?: string
  enterprise_id?: string
  v_uri?: string
}

type SessionEnterpriseResponse = {
  id?: string
  name?: string
  v_uri?: string
  short_name?: string
  plan?: 'basic' | 'pro' | 'enterprise'
  proof_quota?: number
  proof_used?: number
}

type LoginFormState = {
  account: string
  pass: string
}

type EnterpriseFormState = {
  name: string
  adminPhone: string
  pass: string
  uscc: string
}

interface UseAuthSessionControllerArgs {
  token?: string | null
  user?: User | null
  enterprise?: Enterprise | null
  projectsLength: number
  demoEnterprise: Enterprise
  demoProjects: Project[]
  meApi: (options?: { signal?: AbortSignal; timeoutMs?: number }) => Promise<unknown>
  getEnterpriseApi: (
    enterpriseId: string,
    options?: { signal?: AbortSignal; timeoutMs?: number },
  ) => Promise<unknown>
  setUser: (user: User, enterprise: Enterprise, token: string) => void
  setProjects: (projects: Project[]) => void
  setCurrentProject: (project: Project | null) => void
}

export function useAuthSessionController({
  token,
  user,
  enterprise,
  projectsLength,
  demoEnterprise,
  demoProjects,
  meApi,
  getEnterpriseApi,
  setUser,
  setProjects,
  setCurrentProject,
}: UseAuthSessionControllerArgs) {
  const isDemoToken = typeof token === 'string' && token.startsWith('demo-token-')
  const hasPersistedSession = Boolean(token && user?.id && enterprise?.id)
  const [appReady, setAppReady] = useState(hasPersistedSession && isDemoToken)
  const [sessionChecking, setSessionChecking] = useState(Boolean(token) && !isDemoToken)
  const [loginTab, setLoginTab] = useState<'login' | 'register'>('login')
  const [loginForm, setLoginForm] = useState<LoginFormState>({ account: '', pass: '' })
  const [loggingIn, setLoggingIn] = useState(false)
  const [entForm, setEntForm] = useState<EnterpriseFormState>({ name: '', adminPhone: '', pass: '', uscc: '' })

  useEffect(() => {
    if (!appReady) return
    if (!projectsLength && enterprise?.id === demoEnterprise.id) {
      setProjects(demoProjects)
      setCurrentProject(demoProjects[0] || null)
    }
  }, [appReady, projectsLength, enterprise?.id, demoEnterprise.id, demoProjects, setProjects, setCurrentProject])

  useEffect(() => {
    let cancelled = false
    const abortController = new AbortController()
    const bootstrapTimeoutMs = Number(import.meta.env.VITE_BOOTSTRAP_TIMEOUT_MS || 8000)

    const restoreSession = async () => {
      if (!token) {
        setAppReady(false)
        setSessionChecking(false)
        return
      }

      const hasLocalSession = Boolean(user?.id && enterprise?.id)
      if (token.startsWith('demo-token-')) {
        setAppReady(hasLocalSession)
        setSessionChecking(false)
        return
      }
      if (hasLocalSession && appReady) {
        setSessionChecking(false)
        return
      }

      setAppReady(false)
      setSessionChecking(true)

      const meRes = await meApi({
        signal: abortController.signal,
        timeoutMs: bootstrapTimeoutMs,
      }) as SessionMeResponse | null
      if (cancelled || abortController.signal.aborted) return
      if (!meRes?.id || !meRes.enterprise_id) {
        setAppReady(false)
        setSessionChecking(false)
        return
      }

      const enterpriseRes = await getEnterpriseApi(meRes.enterprise_id, {
        signal: abortController.signal,
        timeoutMs: bootstrapTimeoutMs,
      }) as SessionEnterpriseResponse | null
      if (cancelled || abortController.signal.aborted) return
      if (!enterpriseRes?.id) {
        setAppReady(false)
        setSessionChecking(false)
        return
      }

      setUser(
        {
          id: meRes.id,
          enterprise_id: meRes.enterprise_id,
          v_uri: meRes.v_uri || '',
          name: meRes.name || '用户',
          email: meRes.email || undefined,
          dto_role: (meRes.dto_role || 'PUBLIC') as 'PUBLIC' | 'MARKET' | 'AI' | 'SUPERVISOR' | 'OWNER' | 'REGULATOR',
          title: meRes.title || undefined,
        },
        {
          id: enterpriseRes.id,
          name: enterpriseRes.name || '企业',
          v_uri: enterpriseRes.v_uri || 'v://cn/enterprise/',
          short_name: enterpriseRes.short_name,
          plan: enterpriseRes.plan || 'enterprise',
          proof_quota: Number(enterpriseRes.proof_quota || 0),
          proof_used: Number(enterpriseRes.proof_used || 0),
        },
        token,
      )
      setAppReady(true)
      setSessionChecking(false)
    }

    restoreSession()
    return () => {
      cancelled = true
      abortController.abort()
    }
  }, [token, user?.id, enterprise?.id, appReady, meApi, getEnterpriseApi, setUser])

  return {
    appReady,
    setAppReady,
    sessionChecking,
    loginTab,
    setLoginTab,
    loginForm,
    setLoginForm,
    loggingIn,
    setLoggingIn,
    entForm,
    setEntForm,
  }
}
