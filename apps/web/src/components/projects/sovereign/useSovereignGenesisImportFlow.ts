import { useCallback, useState } from 'react'

import type { TreeNode } from './types'
import { buildGenesisImportParams, detectAsyncImportSupport, resolveGenesisChapterHint } from './genesisImportUtils'
import { pickFirstLeaf } from './treeUtils'
import { useSovereignGenesisImportJobMonitor } from './useSovereignGenesisImportJobMonitor'
import { useSovereignGenesisImportPreview } from './useSovereignGenesisImportPreview'

type Args = {
  apiProjectUri: string
  displayProjectUri: string
  forcedBoqRootBase: string
  apiBoqRootBase: string
  projectId: string
  showToast: (message: string) => void
  smuImportGenesis: (params: Record<string, unknown>) => Promise<unknown>
  smuImportGenesisAsync: (params: Record<string, unknown>) => Promise<unknown>
  smuImportGenesisPreview: (params: Record<string, unknown>) => Promise<unknown>
  smuImportGenesisJobPublic: (jobId: string) => Promise<unknown>
  smuImportGenesisJobActivePublic: (projectUri: string) => Promise<unknown>
  refreshTreeFromServer: () => Promise<TreeNode[] | null>
  autoSelectLeafAndPrefill: (leaf: TreeNode | null) => Promise<void>
  clearTreeState: () => void
  applyLocalTree: (rebuilt: TreeNode[]) => void
  clearLocalTree: () => void
}

export function useSovereignGenesisImportFlow({
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
}: Args) {
  const [importing, setImporting] = useState(false)
  const [importJobId, setImportJobId] = useState('')
  const [importProgress, setImportProgress] = useState(0)
  const [importStatusText, setImportStatusText] = useState('')
  const [importError, setImportError] = useState('')
  const [asyncImportSupported, setAsyncImportSupported] = useState<boolean | null>(null)

  const clearImportError = useCallback(() => {
    setImportError('')
  }, [])

  const {
    file,
    fileName,
    setFileName,
    onSelectFile,
    loadBuiltinLedger400,
  } = useSovereignGenesisImportPreview({
    apiProjectUri,
    displayProjectUri,
    forcedBoqRootBase,
    apiBoqRootBase,
    projectId,
    showToast,
    smuImportGenesisPreview,
    applyLocalTree,
    clearLocalTree,
    autoSelectLeafAndPrefill,
    clearImportError,
  })

  const { aliveRef, pollImportJob } = useSovereignGenesisImportJobMonitor({
    apiProjectUri,
    importing,
    showToast,
    smuImportGenesisJobPublic,
    smuImportGenesisJobActivePublic,
    refreshTreeFromServer,
    autoSelectLeafAndPrefill,
    clearTreeState,
    setImporting,
    setImportJobId,
    setImportProgress,
    setImportStatusText,
    setImportError,
    setFileName,
  })

  const importGenesis = useCallback(async () => {
    if (!file || !apiProjectUri) {
      showToast('请先选择清单文件')
      return
    }

    setImporting(true)
    setImportJobId('')
    setImportProgress(0)
    setImportStatusText('任务提交中（大文件约 1-3 分钟）')
    setImportError('')

    try {
      const chapterHint = resolveGenesisChapterHint(fileName || '')
      const params = buildGenesisImportParams({
        file,
        apiProjectUri,
        apiBoqRootBase,
        projectId,
        chapterHint,
        commit: true,
      })

      let canUseAsync = asyncImportSupported
      if (canUseAsync === null) {
        canUseAsync = await detectAsyncImportSupport()
        setAsyncImportSupported(canUseAsync)
      }

      let payload: Record<string, unknown> | null = null
      if (canUseAsync) {
        payload = await smuImportGenesisAsync(params) as Record<string, unknown> | null
      }

      const hasJobId = canUseAsync && String(payload?.job_id || '').trim().length > 0
      if (!hasJobId) {
        if (canUseAsync) {
          setImportStatusText('异步任务创建失败，已回退到同步导入')
          setImportProgress(15)
        } else {
          setImportStatusText('异步接口不可用，已回退到同步导入')
          setImportProgress(10)
        }

        const syncPayload = await smuImportGenesis(params) as Record<string, unknown> | null
        if (!syncPayload?.ok) {
          const detail = String(syncPayload?.detail || payload?.detail || '')
          setImportProgress(0)
          setImportStatusText('导入失败')
          setImportError(detail || '导入失败')
          clearTreeState()
          showToast(detail ? `Genesis 导入失败: ${detail}` : 'Genesis 导入失败')
          return
        }

        setImportProgress(100)
        setImportStatusText('导入完成')
        setImportError('')

        const rebuilt = await refreshTreeFromServer()
        const firstLeaf = pickFirstLeaf(rebuilt || [])
        if (firstLeaf) {
          await autoSelectLeafAndPrefill(firstLeaf)
          showToast(`Genesis 已导入并定位到首个细目：${firstLeaf.code}`)
        } else {
          showToast('Genesis 已导入')
        }
        return
      }

      if (!payload?.ok) {
        const detail = String(payload?.detail || '')
        setImportProgress(0)
        setImportStatusText('导入失败')
        setImportError(detail || '导入失败')
        clearTreeState()
        showToast(detail ? `Genesis 导入失败: ${detail}` : 'Genesis 导入失败')
        return
      }

      const nextJobId = String(payload.job_id || '')
      if (!nextJobId) {
        showToast('Genesis 导入任务创建失败')
        return
      }

      setImportStatusText(String(payload.message || '任务已创建'))
      setImportProgress(Number(payload.progress || 0))
      await pollImportJob(nextJobId, { skipStartToast: true })
    } finally {
      if (aliveRef.current) setImporting(false)
    }
  }, [
    aliveRef,
    apiBoqRootBase,
    apiProjectUri,
    asyncImportSupported,
    autoSelectLeafAndPrefill,
    clearTreeState,
    file,
    fileName,
    pollImportJob,
    projectId,
    refreshTreeFromServer,
    showToast,
    smuImportGenesis,
    smuImportGenesisAsync,
  ])

  return {
    fileName,
    importing,
    importJobId,
    importProgress,
    importStatusText,
    importError,
    onSelectFile,
    loadBuiltinLedger400,
    importGenesis,
  }
}
