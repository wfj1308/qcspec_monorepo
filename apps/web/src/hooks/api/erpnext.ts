import { useCallback } from 'react'
import { useRequest } from './base'

export function useErpnext() {
  const { request, loading } = useRequest()

  const gateCheck = useCallback(async (params: {
    enterprise_id: string
    project_id?: string
    project_code?: string
    stake: string
    subitem: string
    result: 'pass' | 'warn' | 'fail'
  }) => {
    const qs = new URLSearchParams({
      enterprise_id: params.enterprise_id,
      ...(params.project_id ? { project_id: params.project_id } : {}),
      ...(params.project_code ? { project_code: params.project_code } : {}),
      stake: params.stake,
      subitem: params.subitem,
      result: params.result,
    }).toString()
    return request(`/v1/erpnext/gate-check?${qs}`)
  }, [request])

  const getMeteringRequests = useCallback(async (params: {
    enterprise_id: string
    project_code?: string
    stake?: string
    subitem?: string
    status?: string
  }) => {
    const qs = new URLSearchParams({
      enterprise_id: params.enterprise_id,
      ...(params.project_code ? { project_code: params.project_code } : {}),
      ...(params.stake ? { stake: params.stake } : {}),
      ...(params.subitem ? { subitem: params.subitem } : {}),
      ...(params.status ? { status: params.status } : {}),
    }).toString()
    return request(`/v1/erpnext/metering-requests?${qs}`)
  }, [request])

  const getProjectBasics = useCallback(async (params: {
    enterprise_id: string
    project_code?: string
    project_name?: string
  }) => {
    const qs = new URLSearchParams({
      enterprise_id: params.enterprise_id,
      ...(params.project_code ? { project_code: params.project_code } : {}),
      ...(params.project_name ? { project_name: params.project_name } : {}),
    }).toString()
    return request(`/v1/erpnext/project-basics?${qs}`)
  }, [request])

  return { gateCheck, getMeteringRequests, getProjectBasics, loading }
}
