export const DOCPEG_LINKAGE_STORAGE_PREFIX = 'qcspec.docpeg.inspection.linkage.'

export type DocpegInspectionContext = {
  docpegEnabled: boolean
  docpegProjectId: string
  docpegChainId: string
  docpegComponentUri: string
  docpegPileId: string
  docpegAction: string
  docpegFormCode: string
}

export const getDocpegStorageKey = (projectId: string): string =>
  `${DOCPEG_LINKAGE_STORAGE_PREFIX}${projectId || 'default'}`

export const defaultDocpegInspectionContext = (projectId: string): DocpegInspectionContext => ({
  docpegEnabled: true,
  docpegProjectId: projectId || '',
  docpegChainId: '',
  docpegComponentUri: '',
  docpegPileId: '',
  docpegAction: 'qcspec_inspection_submit',
  docpegFormCode: '桥施2表',
})

const asRecord = (value: unknown): Record<string, unknown> =>
  (value && typeof value === 'object' && !Array.isArray(value)) ? (value as Record<string, unknown>) : {}

export const readDocpegInspectionContext = (projectId: string): DocpegInspectionContext => {
  const fallback = defaultDocpegInspectionContext(projectId)
  try {
    const raw = localStorage.getItem(getDocpegStorageKey(projectId))
    if (!raw) return fallback
    const parsed = asRecord(JSON.parse(raw))
    return {
      docpegEnabled: typeof parsed.docpegEnabled === 'boolean' ? parsed.docpegEnabled : fallback.docpegEnabled,
      docpegProjectId: typeof parsed.docpegProjectId === 'string' ? parsed.docpegProjectId : fallback.docpegProjectId,
      docpegChainId: typeof parsed.docpegChainId === 'string' ? parsed.docpegChainId : fallback.docpegChainId,
      docpegComponentUri: typeof parsed.docpegComponentUri === 'string' ? parsed.docpegComponentUri : fallback.docpegComponentUri,
      docpegPileId: typeof parsed.docpegPileId === 'string' ? parsed.docpegPileId : fallback.docpegPileId,
      docpegAction: typeof parsed.docpegAction === 'string' ? parsed.docpegAction : fallback.docpegAction,
      docpegFormCode: typeof parsed.docpegFormCode === 'string' ? parsed.docpegFormCode : fallback.docpegFormCode,
    }
  } catch {
    return fallback
  }
}

export const saveDocpegInspectionContext = (
  projectId: string,
  payload: DocpegInspectionContext
): void => {
  localStorage.setItem(getDocpegStorageKey(projectId), JSON.stringify(payload))
}
