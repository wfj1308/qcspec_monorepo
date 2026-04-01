import { useCallback, useState } from 'react'

import type { TreeNode } from './types'
import { buildGenesisImportParams, resolveGenesisChapterHint } from './genesisImportUtils'
import { buildTreeFromRealtimeItems, parseCsv, pickFirstLeaf } from './treeUtils'

type Args = {
  apiProjectUri: string
  displayProjectUri: string
  forcedBoqRootBase: string
  apiBoqRootBase: string
  projectId: string
  showToast: (message: string) => void
  smuImportGenesisPreview: (params: Record<string, unknown>) => Promise<unknown>
  applyLocalTree: (rebuilt: TreeNode[]) => void
  clearLocalTree: () => void
  autoSelectLeafAndPrefill: (leaf: TreeNode | null) => Promise<void>
  clearImportError: () => void
}

export function useSovereignGenesisImportPreview({
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
}: Args) {
  const [file, setFile] = useState<File | null>(null)
  const [fileName, setFileName] = useState('')

  const onSelectFile = useCallback(async (nextFile: File | null) => {
    setFile(nextFile)
    setFileName(nextFile?.name || '')
    clearImportError()
    if (!nextFile) return

    if (/\.csv$/i.test(nextFile.name)) {
      nextFile.arrayBuffer().then((buffer) => {
        const decode = (encoding: string) => {
          try {
            return new TextDecoder(encoding).decode(buffer)
          } catch {
            return ''
          }
        }

        let text = decode('utf-8')
        const chapterHint = resolveGenesisChapterHint(nextFile.name || '')
        let parsed = parseCsv(text, displayProjectUri, chapterHint, forcedBoqRootBase)

        if (!parsed.length) {
          const gbText = decode('gb18030')
          if (gbText) {
            text = gbText
            parsed = parseCsv(text, displayProjectUri, chapterHint, forcedBoqRootBase)
          }
        }

        if (!parsed.length) {
          showToast('CSV 解析失败，请检查表头或编码')
          return
        }

        applyLocalTree(parsed)
        const firstLeaf = pickFirstLeaf(parsed)
        if (firstLeaf) void autoSelectLeafAndPrefill(firstLeaf)
      })
      return
    }

    try {
      const chapterHint = resolveGenesisChapterHint(nextFile.name || '')
      const preview = await smuImportGenesisPreview(
        buildGenesisImportParams({
          file: nextFile,
          apiProjectUri,
          apiBoqRootBase,
          projectId,
          chapterHint,
        }),
      ) as Record<string, unknown> | null

      const items = Array.isArray(preview?.preview_items)
        ? (preview.preview_items as Array<Record<string, unknown>>)
        : []
      if (!items.length) return

      const rebuilt = buildTreeFromRealtimeItems(items, displayProjectUri)
      applyLocalTree(rebuilt)
      const firstLeaf = pickFirstLeaf(rebuilt)
      if (firstLeaf) void autoSelectLeafAndPrefill(firstLeaf)
    } catch {
      clearLocalTree()
    }
  }, [
    apiBoqRootBase,
    apiProjectUri,
    applyLocalTree,
    autoSelectLeafAndPrefill,
    clearImportError,
    clearLocalTree,
    displayProjectUri,
    forcedBoqRootBase,
    projectId,
    showToast,
    smuImportGenesisPreview,
  ])

  const loadBuiltinLedger400 = useCallback(async () => {
    try {
      const res = await fetch('/boq_0_400_sample.csv', { cache: 'no-store' })
      if (!res.ok) {
        showToast('示例台账不存在，请手动上传 CSV')
        return
      }

      const text = await res.text()
      const blob = new Blob([text], { type: 'text/csv;charset=utf-8' })
      const builtInFile = new File([blob], '0#台账-400章.csv', { type: 'text/csv' })
      await onSelectFile(builtInFile)
      showToast('已加载示例台账：0#台账-400章.csv')
    } catch {
      showToast('示例台账加载失败，请手动上传')
    }
  }, [onSelectFile, showToast])

  return {
    file,
    fileName,
    setFileName,
    onSelectFile,
    loadBuiltinLedger400,
  }
}
