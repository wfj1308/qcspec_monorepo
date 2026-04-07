import { guessChapterFromFileName } from './treeUtils'

const API_BASE = String(import.meta.env.VITE_API_URL || 'http://127.0.0.1:8000')

export function resolveGenesisChapterHint(fileName: string) {
  return guessChapterFromFileName(fileName || '') || '400'
}

export function buildGenesisImportParams({
  file,
  apiProjectUri,
  apiBoqRootBase,
  projectId,
  chapterHint,
  commit = false,
}: {
  file: File
  apiProjectUri: string
  apiBoqRootBase: string
  projectId: string
  chapterHint: string
  commit?: boolean
}) {
  return {
    file,
    project_uri: apiProjectUri,
    project_id: projectId || undefined,
    boq_root_uri: `${apiBoqRootBase}/${chapterHint}`,
    norm_context_root_uri: `${apiProjectUri.replace(/\/$/, '')}/normContext`,
    owner_uri: `${apiProjectUri.replace(/\/$/, '')}/role/system/`,
    ...(commit ? { commit: true } : {}),
  }
}

export async function detectAsyncImportSupport() {
  try {
    const res = await fetch(`${API_BASE}/openapi.json`)
    const json = await res.json() as { paths?: Record<string, unknown> }
    const candidatePaths = [
      '/v1/qcspec/boqpeg/import-async',
      '/v1/proof/boqpeg/import-async',
      '/v1/proof/smu/genesis/import-async',
      '/v1/docpeg/smu/genesis/import-async',
    ]
    return candidatePaths.some((path) => Boolean(json?.paths?.[path]))
  } catch {
    return false
  }
}
