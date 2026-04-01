import { useCallback, useEffect, useRef } from 'react'
import type { Dispatch, SetStateAction } from 'react'

import type { TreeNode } from './types'
import { pickFirstLeaf } from './treeUtils'

type Args = {
  apiProjectUri: string
  importing: boolean
  showToast: (message: string) => void
  smuImportGenesisJobPublic: (jobId: string) => Promise<unknown>
  smuImportGenesisJobActivePublic: (projectUri: string) => Promise<unknown>
  refreshTreeFromServer: () => Promise<TreeNode[] | null>
  autoSelectLeafAndPrefill: (leaf: TreeNode | null) => Promise<void>
  clearTreeState: () => void
  setImporting: Dispatch<SetStateAction<boolean>>
  setImportJobId: Dispatch<SetStateAction<string>>
  setImportProgress: Dispatch<SetStateAction<number>>
  setImportStatusText: Dispatch<SetStateAction<string>>
  setImportError: Dispatch<SetStateAction<string>>
  setFileName: Dispatch<SetStateAction<string>>
}

export function useSovereignGenesisImportJobMonitor({
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
}: Args) {
  const aliveRef = useRef(true)
  const resumedProjectRef = useRef('')

  useEffect(() => {
    aliveRef.current = true
    return () => {
      aliveRef.current = false
    }
  }, [])

  const pollImportJob = useCallback(async (
    jobId: string,
    options: { skipStartToast?: boolean } = {},
  ) => {
    const normalizedJobId = String(jobId || '').trim()
    if (!normalizedJobId) return

    setImporting(true)
    setImportJobId(normalizedJobId)
    if (!options.skipStartToast) {
      showToast('已连接到导入任务，正在后台处理中')
    }

    const startedAt = Date.now()
    const maxWaitMs = 10 * 60 * 1000
    let pollFailure = 0
    let pollRound = 0

    while (aliveRef.current) {
      const job = await smuImportGenesisJobPublic(normalizedJobId) as Record<string, unknown> | null
      if (!job) {
        pollFailure += 1
        if (pollFailure >= 8) {
          setImportStatusText('导入状态查询失败，后台任务可能仍在执行')
          showToast('Genesis 导入状态查询失败，请稍后重试')
          break
        }
        await new Promise((resolve) => window.setTimeout(resolve, 1500))
        continue
      }

      pollFailure = 0
      const state = String(job.state || '')
      const stage = String(job.stage || '')
      const progress = Number(job.progress || 0)
      const message = String(job.message || '')
      const phaseLabel = stage ? `[${stage}] ` : ''

      if (aliveRef.current) {
        setImportProgress(Number.isFinite(progress) ? progress : 0)
        const fallback = state === 'running'
          ? '后台处理中（大文件约 1-3 分钟）'
          : '执行中'
        setImportStatusText(`${phaseLabel}${message || fallback}`)
      }

      if (state === 'success') {
        setImportError('')
        const result = (job.result || {}) as Record<string, unknown>
        const totalNodes = Number(result.total_nodes || 0)
        const leafNodes = Number(result.leaf_nodes || 0)
        const rebuilt = await refreshTreeFromServer()
        const firstLeaf = pickFirstLeaf(rebuilt || [])

        if (firstLeaf) {
          await autoSelectLeafAndPrefill(firstLeaf)
          showToast(`Genesis 已完成：节点 ${totalNodes}，叶子 ${leafNodes}，已定位 ${firstLeaf.code}`)
        } else {
          showToast(`Genesis 已完成：节点 ${totalNodes}，叶子 ${leafNodes}`)
        }
        break
      }

      if (state === 'failed') {
        const err = (job.error || {}) as Record<string, unknown>
        const detail = String(err.detail || job.message || 'unknown error')
        setImportStatusText('导入失败')
        setImportError(detail || '导入失败')
        clearTreeState()
        showToast(`Genesis 导入失败: ${detail}`)
        break
      }

      if (Date.now() - startedAt > maxWaitMs) {
        setImportStatusText('后台仍在执行，请稍后重试')
        showToast('导入任务仍在后台执行，请稍后重试查询状态')
        break
      }

      pollRound += 1
      const waitMs = pollRound < 10 ? 1200 : pollRound < 30 ? 2200 : 3500
      await new Promise((resolve) => window.setTimeout(resolve, waitMs))
    }

    if (aliveRef.current) setImporting(false)
  }, [
    autoSelectLeafAndPrefill,
    clearTreeState,
    refreshTreeFromServer,
    setImportError,
    setImporting,
    setImportJobId,
    setImportProgress,
    setImportStatusText,
    showToast,
    smuImportGenesisJobPublic,
  ])

  useEffect(() => {
    if (!apiProjectUri || importing) return
    if (resumedProjectRef.current === apiProjectUri) return

    resumedProjectRef.current = apiProjectUri
    void (async () => {
      const activeJob = await smuImportGenesisJobActivePublic(apiProjectUri) as Record<string, unknown> | null
      if (!activeJob?.active) return

      const activeJobId = String(activeJob.job_id || '')
      if (!activeJobId) return

      const nextFileName = String(activeJob.file_name || '').trim()
      if (nextFileName) setFileName(nextFileName)
      setImportStatusText(String(activeJob.message || '检测到未完成导入任务，正在恢复'))
      setImportProgress(Number(activeJob.progress || 0))
      await pollImportJob(activeJobId, { skipStartToast: true })
    })()
  }, [
    apiProjectUri,
    importing,
    pollImportJob,
    setFileName,
    setImportProgress,
    setImportStatusText,
    smuImportGenesisJobActivePublic,
  ])

  return {
    aliveRef,
    pollImportJob,
  }
}
