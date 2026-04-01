import { useCallback } from 'react'
import { useRequest } from './base'

export function useTeam() {
  const { request, loading } = useRequest()

  const listMembers = useCallback(async (
    enterprise_id: string,
    include_inactive = false,
  ) => {
    const qs = new URLSearchParams({
      enterprise_id,
      include_inactive: String(include_inactive),
    }).toString()
    return request(`/v1/team/members?${qs}`)
  }, [request])

  const inviteMember = useCallback(async (body: {
    enterprise_id: string
    name: string
    email: string
    dto_role: string
    title?: string
    project_ids?: string[]
  }) => {
    return request('/v1/team/members', {
      method: 'POST',
      body: JSON.stringify(body),
    })
  }, [request])

  const updateMember = useCallback(async (user_id: string, body: {
    name?: string
    email?: string
    dto_role?: string
    title?: string
    project_ids?: string[]
    is_active?: boolean
  }) => {
    return request(`/v1/team/members/${user_id}`, {
      method: 'PATCH',
      body: JSON.stringify(body),
    })
  }, [request])

  const removeMember = useCallback(async (user_id: string) => {
    return request(`/v1/team/members/${user_id}`, { method: 'DELETE' })
  }, [request])

  return { listMembers, inviteMember, updateMember, removeMember, loading }
}
