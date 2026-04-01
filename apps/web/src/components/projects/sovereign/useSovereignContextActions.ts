import { useCallback, useRef } from 'react'

import {
  expandFormSchemaRows,
  resolveFallbackSchema,
} from './spuUtils'
import { toApiUri } from './treeUtils'
import type { FormRow, TreeNode } from './types'

type Args = {
  apiProjectUri: string
  compType: string
  sampleId: string
  erpRetrying: boolean
  resetEvidence: () => void
  showToast: (message: string) => void
  smuNodeContext: (payload: { project_uri: string; boq_item_uri: string; component_type?: string }) => Promise<unknown>
  smuRetryErpnext: (limit?: number) => Promise<unknown>
  setCtx: (value: Record<string, unknown> | null) => void
  setContextError: (value: string) => void
  setForm: (value: Record<string, string>) => void
  setCompType: (value: string) => void
  setSampleId: (value: string) => void
  setClaimQty: (value: string) => void
  setLoadingCtx: (value: boolean) => void
  setErpRetrying: (value: boolean) => void
  setErpRetryMsg: (value: string) => void
}

export function useSovereignContextActions({
  apiProjectUri,
  compType,
  sampleId,
  erpRetrying,
  resetEvidence,
  showToast,
  smuNodeContext,
  smuRetryErpnext,
  setCtx,
  setContextError,
  setForm,
  setCompType,
  setSampleId,
  setClaimQty,
  setLoadingCtx,
  setErpRetrying,
  setErpRetryMsg,
}: Args) {
  const contextReqSeqRef = useRef(0)
  const loadContextRef = useRef<((uri: string, component?: string) => Promise<void>) | null>(null)

  const resetSelectionWorkspace = useCallback(() => {
    setCtx(null)
    setContextError('')
    setForm({})
    setCompType('generic')
    setSampleId('')
    setClaimQty('')
    resetEvidence()
  }, [resetEvidence, setClaimQty, setCompType, setContextError, setCtx, setForm, setSampleId])

  const loadContext = useCallback(async (uri: string, component = compType) => {
    if (!apiProjectUri || !uri) return
    const reqSeq = contextReqSeqRef.current + 1
    contextReqSeqRef.current = reqSeq
    setLoadingCtx(true)
    setContextError('')
    try {
      const payload = await smuNodeContext({
        project_uri: apiProjectUri,
        boq_item_uri: toApiUri(uri),
        component_type: component,
      }) as Record<string, unknown> | null
      if (contextReqSeqRef.current !== reqSeq) return
      if (!payload?.ok || !payload?.node) {
        setCtx(null)
        setForm({})
        setContextError('该细目未加载到可用门控，请检查导入数据或重新导入后重试。')
        showToast('加载门控失败')
        return
      }
      setCtx(payload)
      const payloadSpu = ((payload.spu || {}) as Record<string, unknown>)
      const payloadSpuLabel = String(payloadSpu.spu_code || payloadSpu.spu_type || '')
      const payloadNode = ((payload.node || {}) as Record<string, unknown>)
      const nodeCode = String(payloadNode.item_no || payloadNode.item_code || '')
      const nodeName = String(payloadNode.item_name || payloadNode.name || '')
      const baseRows = Array.isArray(payloadSpu.spu_form_schema)
        ? (payloadSpu.spu_form_schema as FormRow[])
        : resolveFallbackSchema(payloadSpuLabel, nodeCode, nodeName)
      const rows = expandFormSchemaRows(baseRows)
      const next: Record<string, string> = {}
      rows.forEach((row) => {
        next[String(row.field || '')] = ''
      })
      setForm(next)
    } catch {
      if (contextReqSeqRef.current !== reqSeq) return
      setCtx(null)
      setForm({})
      setContextError('加载门控请求失败，请稍后重试。')
      showToast('加载门控失败')
    } finally {
      if (contextReqSeqRef.current === reqSeq) setLoadingCtx(false)
    }
  }, [apiProjectUri, compType, setContextError, setCtx, setForm, setLoadingCtx, showToast, smuNodeContext])

  loadContextRef.current = loadContext

  const activateTreeNode = useCallback(async (node: TreeNode, nextCompType: string) => {
    setCtx(null)
    setContextError('')
    setClaimQty('')
    if (!node.isLeaf) return
    setCompType(nextCompType)
    if (!sampleId) {
      const seed = `${node.code}-${Date.now().toString().slice(-6)}`
      setSampleId(`SAMPLE-${seed}`)
    }
    await loadContextRef.current?.(node.uri, nextCompType)
  }, [sampleId, setClaimQty, setCompType, setContextError, setCtx, setSampleId])

  const retryErpnextPush = useCallback(async () => {
    if (erpRetrying) return
    setErpRetrying(true)
    setErpRetryMsg('')
    try {
      const res = await smuRetryErpnext(20) as Record<string, unknown> | null
      if (res && res.ok) {
        setErpRetryMsg(`重试完成：成功 ${String(res.success || 0)} / ${String(res.attempted || 0)}`)
      } else {
        setErpRetryMsg('重试失败：接口无响应')
      }
    } catch {
      setErpRetryMsg('重试失败：请求异常')
    } finally {
      setErpRetrying(false)
    }
  }, [erpRetrying, setErpRetryMsg, setErpRetrying, smuRetryErpnext])

  return {
    resetSelectionWorkspace,
    activateTreeNode,
    loadContext,
    retryErpnextPush,
  }
}
