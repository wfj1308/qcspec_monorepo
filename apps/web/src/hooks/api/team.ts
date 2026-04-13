import { useCallback } from 'react'

export function useTeam() {
  const listMembers = useCallback(async (
    _enterprise_id: string,
    _include_inactive = false,
  ) => {
    return {
      ok: true,
      data: [],
      source: 'docpeg-api-pack-empty',
    }
  }, [])

  const inviteMember = useCallback(async (_body: {
    enterprise_id: string
    name: string
    email: string
    dto_role: string
    title?: string
    project_ids?: string[]
  }) => {
    return {
      ok: false,
      unsupported: true,
      message: '同事 API 文档未提供团队成员管理接口',
    }
  }, [])

  const updateMember = useCallback(async (_user_id: string, _body: {
    name?: string
    email?: string
    dto_role?: string
    title?: string
    project_ids?: string[]
    is_active?: boolean
  }) => {
    return {
      ok: false,
      unsupported: true,
      message: '同事 API 文档未提供团队成员更新接口',
    }
  }, [])

  const removeMember = useCallback(async (_user_id: string) => {
    return {
      ok: false,
      unsupported: true,
      message: '同事 API 文档未提供团队成员删除接口',
    }
  }, [])

  return { listMembers, inviteMember, updateMember, removeMember, loading: false }
}
