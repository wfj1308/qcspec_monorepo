import { useEffect } from 'react'
import type { Dispatch, SetStateAction } from 'react'
import type {
  ErpDraftState,
  ErpWritebackDraftState,
  PermissionRow,
  PermTemplate,
  SettingsState,
  TeamMember,
  TeamRole,
} from './appShellShared'
import { detectPermissionTemplate, normalizePermissionMatrix, roleToTitle, toRoleDraftMap } from './appShellShared'
import type { EnterpriseInfoState } from './settingsTypes'

interface UseTeamSettingsBootstrapArgs {
  appReady: boolean
  activeTab: string
  canUseEnterpriseApi: boolean
  enterpriseId?: string
  listMembers: (enterpriseId: string, includeInactive?: boolean) => Promise<unknown>
  getSettings: (enterpriseId: string) => Promise<unknown>
  setMembers: Dispatch<SetStateAction<TeamMember[]>>
  setMemberRoleDrafts: Dispatch<SetStateAction<Record<string, TeamRole>>>
  setSettings: Dispatch<SetStateAction<SettingsState>>
  setErpDraft: Dispatch<SetStateAction<ErpDraftState>>
  setErpWritebackDraft: Dispatch<SetStateAction<ErpWritebackDraftState>>
  setPermissionMatrix: Dispatch<SetStateAction<PermissionRow[]>>
  setPermissionTemplate: Dispatch<SetStateAction<PermTemplate>>
  setEnterpriseInfo: Dispatch<SetStateAction<EnterpriseInfoState>>
}

export function useTeamSettingsBootstrap({
  appReady,
  activeTab,
  canUseEnterpriseApi,
  enterpriseId,
  listMembers,
  getSettings,
  setMembers,
  setMemberRoleDrafts,
  setSettings,
  setErpDraft,
  setErpWritebackDraft,
  setPermissionMatrix,
  setPermissionTemplate,
  setEnterpriseInfo,
}: UseTeamSettingsBootstrapArgs): void {
  useEffect(() => {
    if (!appReady || !canUseEnterpriseApi || !enterpriseId) return
    const needTeamOrSettings =
      activeTab === 'team' ||
      activeTab === 'permissions' ||
      activeTab === 'settings'
    if (!needTeamOrSettings) return

    listMembers(enterpriseId).then((res) => {
      const r = res as {
        data?: Array<{
          id: string
          name: string
          title?: string
          email?: string
          dto_role?: string
          projects?: string[]
        }>
      } | null
      if (!r?.data || r.data.length === 0) return
      const roleFallback = (role?: string): TeamRole => {
        const normalized = String(role || '').toUpperCase()
        if (normalized === 'OWNER' || normalized === 'SUPERVISOR' || normalized === 'AI' || normalized === 'PUBLIC') {
          return normalized as TeamRole
        }
        return 'PUBLIC'
      }
      const mapped = r.data.map((member, idx) => ({
        id: member.id,
        name: member.name || '未命名成员',
        title: member.title || roleToTitle(roleFallback(member.dto_role)),
        email: member.email || '',
        role: roleFallback(member.dto_role),
        color: ['#1A56DB', '#059669', '#7C3AED', '#D97706', '#0891B2'][idx % 5],
        projects: member.projects || [],
      }))
      setMembers(mapped)
      setMemberRoleDrafts(toRoleDraftMap(mapped))
    })

    getSettings(enterpriseId).then((res) => {
      const r = res as {
        enterprise?: { name?: string; v_uri?: string; credit_code?: string }
        settings?: Partial<SettingsState> & {
          permissionMatrix?: Array<Partial<PermissionRow> & { role?: string }>
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
        }
      } | null
      if (!r?.settings) return
      const {
        permissionMatrix: matrixFromApi,
        erpnextUrl,
        erpnextSiteName,
        erpnextApiKey,
        erpnextApiSecret,
        erpnextUsername,
        erpnextPassword,
        erpnextProjectDoctype,
        erpnextProjectLookupField,
        erpnextProjectLookupValue,
        erpnextGitpegProjectUriField,
        erpnextGitpegSiteUriField,
        erpnextGitpegStatusField,
        erpnextGitpegResultJsonField,
        erpnextGitpegRegistrationIdField,
        erpnextGitpegNodeUriField,
        erpnextGitpegShellUriField,
        erpnextGitpegProofHashField,
        erpnextGitpegIndustryProfileIdField,
        ...settingsFromApi
      } = r.settings
      setSettings((prev) => ({ ...prev, ...settingsFromApi }))
      setErpDraft((prev) => ({
        ...prev,
        url: erpnextUrl ?? prev.url,
        siteName: erpnextSiteName ?? prev.siteName,
        apiKey: erpnextApiKey ?? prev.apiKey,
        apiSecret: erpnextApiSecret ?? prev.apiSecret,
        username: erpnextUsername ?? prev.username,
        password: erpnextPassword ?? prev.password,
      }))
      setErpWritebackDraft((prev) => ({
        ...prev,
        projectDoctype: erpnextProjectDoctype ?? prev.projectDoctype,
        projectLookupField: erpnextProjectLookupField ?? prev.projectLookupField,
        projectLookupValue: erpnextProjectLookupValue ?? prev.projectLookupValue,
        gitpegProjectUriField: erpnextGitpegProjectUriField ?? prev.gitpegProjectUriField,
        gitpegSiteUriField: erpnextGitpegSiteUriField ?? prev.gitpegSiteUriField,
        gitpegStatusField: erpnextGitpegStatusField ?? prev.gitpegStatusField,
        gitpegResultJsonField: erpnextGitpegResultJsonField ?? prev.gitpegResultJsonField,
        gitpegRegistrationIdField: erpnextGitpegRegistrationIdField ?? prev.gitpegRegistrationIdField,
        gitpegNodeUriField: erpnextGitpegNodeUriField ?? prev.gitpegNodeUriField,
        gitpegShellUriField: erpnextGitpegShellUriField ?? prev.gitpegShellUriField,
        gitpegProofHashField: erpnextGitpegProofHashField ?? prev.gitpegProofHashField,
        gitpegIndustryProfileIdField: erpnextGitpegIndustryProfileIdField ?? prev.gitpegIndustryProfileIdField,
      }))
      if (matrixFromApi) {
        const matrix = normalizePermissionMatrix(matrixFromApi)
        setPermissionMatrix(matrix)
        setPermissionTemplate(detectPermissionTemplate(matrix))
      }
      if (r.enterprise) {
        setEnterpriseInfo((prev) => ({
          ...prev,
          name: r.enterprise?.name || prev.name,
          vUri: r.enterprise?.v_uri || prev.vUri,
          creditCode: r.enterprise?.credit_code || prev.creditCode,
        }))
      }
    })
  }, [
    appReady,
    activeTab,
    canUseEnterpriseApi,
    enterpriseId,
    listMembers,
    getSettings,
    setMembers,
    setMemberRoleDrafts,
    setSettings,
    setErpDraft,
    setErpWritebackDraft,
    setPermissionMatrix,
    setPermissionTemplate,
    setEnterpriseInfo,
  ])
}
