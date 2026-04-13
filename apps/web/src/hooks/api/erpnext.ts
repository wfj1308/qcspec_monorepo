import { useCallback } from 'react'

export function useErpnext() {
  const gateCheck = useCallback(async (params: {
    enterprise_id: string
    project_id?: string
    project_code?: string
    stake: string
    subitem: string
    result: 'pass' | 'warn' | 'fail'
  }) => {
    const blocked = params.result === 'fail'
    return {
      ok: true,
      gate: {
        action: blocked ? 'block' : 'release',
        reason: blocked ? 'inspection_not_passed' : '',
        can_release: !blocked,
      },
      unsupported: true,
      message: '同事 API 暂未提供 ERPNext 门禁接口，当前为前端占位模式。',
    }
  }, [])

  const getMeteringRequests = useCallback(async (_params: {
    enterprise_id: string
    project_code?: string
    stake?: string
    subitem?: string
    status?: string
  }) => {
    return { ok: true, data: [], total: 0 }
  }, [])

  const getProjectBasics = useCallback(async (_params: {
    enterprise_id: string
    project_code?: string
    project_name?: string
  }) => {
    return { ok: true, data: [], total: 0 }
  }, [])

  return { gateCheck, getMeteringRequests, getProjectBasics, loading: false }
}
