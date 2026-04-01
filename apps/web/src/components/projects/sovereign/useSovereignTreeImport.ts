import { useCallback, useEffect, useState } from 'react'

import type { TreeNode } from './types'
import {
  buildTreeFromRealtimeItems,
  getAllExpandedCodes,
  getFocusedExpandedCodes,
  mergeExpandedCodes,
  pickFirstLeaf,
} from './treeUtils'
import { useSovereignGenesisImportFlow } from './useSovereignGenesisImportFlow'
import { useSovereignTreeReadiness } from './useSovereignTreeReadiness'
import { useSovereignTreeSearchState } from './useSovereignTreeSearchState'

type UseSovereignTreeImportArgs = {
  apiProjectUri: string
  displayProjectUri: string
  forcedBoqRootBase: string
  apiBoqRootBase: string
  projectId: string
  showToast: (message: string) => void
  projectReadinessCheck: (projectUri: string) => Promise<unknown>
  boqRealtimeStatus: (projectUri: string) => Promise<unknown>
  smuImportGenesis: (params: Record<string, unknown>) => Promise<unknown>
  smuImportGenesisAsync: (params: Record<string, unknown>) => Promise<unknown>
  smuImportGenesisPreview: (params: Record<string, unknown>) => Promise<unknown>
  smuImportGenesisJobPublic: (jobId: string) => Promise<unknown>
  smuImportGenesisJobActivePublic: (projectUri: string) => Promise<unknown>
  resetSelectionWorkspace: () => void
  onActivateNode: (node: TreeNode, componentType: string) => Promise<void>
}

function resolveComponentType(node: TreeNode) {
  if (node.spu === 'SPU_Reinforcement' || node.spu === 'SPU_Bridge') return 'main_beam'
  if (node.spu === 'SPU_Concrete') return 'pier'
  return 'generic'
}

export function useSovereignTreeImport({
  apiProjectUri,
  displayProjectUri,
  forcedBoqRootBase,
  apiBoqRootBase,
  projectId,
  showToast,
  projectReadinessCheck,
  boqRealtimeStatus,
  smuImportGenesis,
  smuImportGenesisAsync,
  smuImportGenesisPreview,
  smuImportGenesisJobPublic,
  smuImportGenesisJobActivePublic,
  resetSelectionWorkspace,
  onActivateNode,
}: UseSovereignTreeImportArgs) {
  const [showLeftSummary, setShowLeftSummary] = useState(true)
  const [nodes, setNodes] = useState<TreeNode[]>([])
  const [expandedCodes, setExpandedCodes] = useState<string[]>([])
  const [activeUri, setActiveUri] = useState('')
  const [treeQuery, setTreeQuery] = useState('')

  const {
    readinessLoading,
    readinessPercent,
    readinessOverall,
    readinessLayers,
    showRolePlaybook,
    setShowRolePlaybook,
    runReadinessCheck,
  } = useSovereignTreeReadiness({
    apiProjectUri,
    projectReadinessCheck,
    showToast,
  })

  const {
    byUri,
    byCode,
    roots,
    treeSearch,
  } = useSovereignTreeSearchState({
    nodes,
    treeQuery,
  })

  const refreshTreeFromServer = useCallback(async () => {
    if (!apiProjectUri) return null
    const payload = await boqRealtimeStatus(apiProjectUri) as Record<string, unknown> | null
    const items = Array.isArray(payload?.items) ? (payload.items as Array<Record<string, unknown>>) : []
    if (!items.length) return null

    const rebuilt = buildTreeFromRealtimeItems(items, displayProjectUri)
    if (!rebuilt.length) return null

    setNodes(rebuilt)
    setExpandedCodes(getAllExpandedCodes(rebuilt))
    return rebuilt
  }, [apiProjectUri, boqRealtimeStatus, displayProjectUri])

  const activateNode = useCallback(async (node: TreeNode) => {
    setActiveUri(node.uri)
    await onActivateNode(node, resolveComponentType(node))
  }, [onActivateNode])

  const autoSelectLeafAndPrefill = useCallback(async (leaf: TreeNode | null) => {
    if (!leaf) return
    await activateNode(leaf)
  }, [activateNode])

  const clearTreeState = useCallback(() => {
    setNodes([])
    setExpandedCodes([])
    setActiveUri('')
    resetSelectionWorkspace()
  }, [resetSelectionWorkspace])

  const applyLocalTree = useCallback((rebuilt: TreeNode[]) => {
    setNodes(rebuilt)
    setExpandedCodes(getAllExpandedCodes(rebuilt))
  }, [])

  const clearLocalTree = useCallback(() => {
    setNodes([])
    setExpandedCodes([])
    setActiveUri('')
  }, [])

  const {
    fileName,
    importing,
    importJobId,
    importProgress,
    importStatusText,
    importError,
    onSelectFile,
    loadBuiltinLedger400,
    importGenesis,
  } = useSovereignGenesisImportFlow({
    apiProjectUri,
    displayProjectUri,
    forcedBoqRootBase,
    apiBoqRootBase,
    projectId,
    showToast,
    smuImportGenesis,
    smuImportGenesisAsync,
    smuImportGenesisPreview,
    smuImportGenesisJobPublic,
    smuImportGenesisJobActivePublic,
    refreshTreeFromServer,
    autoSelectLeafAndPrefill,
    clearTreeState,
    applyLocalTree,
    clearLocalTree,
  })

  useEffect(() => {
    if (!apiProjectUri || nodes.length > 0) return
    void (async () => {
      const rebuilt = await refreshTreeFromServer()
      if (!rebuilt?.length || activeUri) return
      const firstLeaf = pickFirstLeaf(rebuilt)
      if (firstLeaf) await autoSelectLeafAndPrefill(firstLeaf)
    })()
  }, [activeUri, apiProjectUri, autoSelectLeafAndPrefill, nodes.length, refreshTreeFromServer])

  const selectNode = useCallback(async (code: string) => {
    const node = byCode.get(code)
    if (!node) return
    setExpandedCodes((prev) => mergeExpandedCodes(prev, getFocusedExpandedCodes(nodes, code)))
    await activateNode(node)
  }, [activateNode, byCode, nodes])

  const toggleExpanded = useCallback((code: string) => {
    setExpandedCodes((prev) => (prev.includes(code) ? prev.filter((item) => item !== code) : [...prev, code]))
  }, [])

  return {
    fileName,
    importing,
    importJobId,
    importProgress,
    importStatusText,
    importError,
    readinessLoading,
    readinessPercent,
    readinessOverall,
    readinessLayers,
    showRolePlaybook,
    setShowRolePlaybook,
    showLeftSummary,
    setShowLeftSummary,
    nodes,
    setNodes,
    expandedCodes,
    activeUri,
    treeQuery,
    setTreeQuery,
    byUri,
    byCode,
    roots,
    treeSearch,
    runReadinessCheck,
    refreshTreeFromServer,
    onSelectFile,
    loadBuiltinLedger400,
    importGenesis,
    selectNode,
    toggleExpanded,
  }
}
