import { useMemo } from 'react'

import { resolveGate } from '../../NormEngine'
import {
  expandFormSchemaRows,
  resolveFallbackSchema,
} from '../../spuUtils'
import type {
  FormRow,
  GateStats,
  TreeNode,
} from '../../types'

type Args = {
  ctx: Record<string, unknown> | null
  active: TreeNode | null
  boundSpu: string
  isContractSpu: boolean
  form: Record<string, string>
  executorDid: string
  p2pNodeId: string
}

type Result = {
  effectiveSchema: FormRow[]
  gateStats: GateStats
  offlineActorId: string
}

export function useSovereignWorkbenchInputState({
  ctx,
  active,
  boundSpu,
  isContractSpu,
  form,
  executorDid,
  p2pNodeId,
}: Args): Result {
  const formSchema = useMemo<FormRow[]>(() => {
    const spu = (ctx?.spu || {}) as Record<string, unknown>
    const apiRows = Array.isArray(spu.spu_form_schema) ? (spu.spu_form_schema as FormRow[]) : []
    if (apiRows.length) return expandFormSchemaRows(apiRows)
    const node = (ctx?.node || {}) as Record<string, unknown>
    const nodeCode = String(node.item_no || node.item_code || active?.code || '')
    const nodeName = String(node.item_name || node.name || active?.name || '')
    return expandFormSchemaRows(resolveFallbackSchema(boundSpu, nodeCode, nodeName))
  }, [active?.code, active?.name, boundSpu, ctx])

  const effectiveSchema = useMemo<FormRow[]>(() => {
    if (!isContractSpu) return formSchema
    return formSchema.filter((row) => {
      const field = String(row.field || '').toLowerCase()
      const label = String(row.label || '').toLowerCase()
      if (field.includes('quality') || label.includes('quality')) return false
      if (field.includes('design') || field.includes('measured') || field.includes('allowed')) return false
      if (label.includes('design') || label.includes('measured') || label.includes('allowed') || label.includes('tolerance')) return false
      return true
    })
  }, [formSchema, isContractSpu])

  const gateStats = useMemo(
    () => resolveGate({
      schema: effectiveSchema,
      form,
      ctx,
      isContractSpu,
    }),
    [ctx, effectiveSchema, form, isContractSpu],
  )

  const offlineActorId = useMemo(() => {
    const didSlug = String(executorDid || 'anonymous').split(':').slice(-1)[0] || 'anonymous'
    return `${p2pNodeId}:${didSlug}`
  }, [executorDid, p2pNodeId])

  return {
    effectiveSchema,
    gateStats,
    offlineActorId,
  }
}
