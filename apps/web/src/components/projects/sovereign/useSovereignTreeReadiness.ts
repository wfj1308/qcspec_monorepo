import { useCallback, useEffect, useMemo, useState } from 'react'

export type ReadinessLayer = {
  key: string
  name: string
  status: 'complete' | 'partial' | 'missing' | string
  metrics?: Record<string, unknown>
}

export type ReadinessPayload = {
  ok?: boolean
  overall_status?: 'complete' | 'partial' | 'missing' | string
  readiness_percent?: number
  layers?: ReadinessLayer[]
}

type Args = {
  apiProjectUri: string
  projectReadinessCheck: (projectUri: string) => Promise<unknown>
  showToast: (message: string) => void
}

export function useSovereignTreeReadiness({
  apiProjectUri,
  projectReadinessCheck,
  showToast,
}: Args) {
  const [readinessLoading, setReadinessLoading] = useState(false)
  const [readiness, setReadiness] = useState<ReadinessPayload | null>(null)
  const [showRolePlaybook, setShowRolePlaybook] = useState(false)

  const runReadinessCheck = useCallback(async (silent = false) => {
    if (!apiProjectUri) return
    setReadinessLoading(true)
    try {
      const payload = await projectReadinessCheck(apiProjectUri) as ReadinessPayload | null
      if (!payload) {
        if (!silent) showToast('体检接口无响应')
        return
      }
      setReadiness(payload)
      if (!silent) {
        const percent = Number(payload.readiness_percent || 0)
        showToast(`闭环体检完成，${percent.toFixed(2)}%`)
      }
    } finally {
      setReadinessLoading(false)
    }
  }, [apiProjectUri, projectReadinessCheck, showToast])

  useEffect(() => {
    if (!apiProjectUri) return
    void runReadinessCheck(true)
  }, [apiProjectUri, runReadinessCheck])

  const readinessPercent = useMemo(() => {
    const value = Number(readiness?.readiness_percent || 0)
    return Number.isFinite(value) ? Math.max(0, Math.min(100, value)) : 0
  }, [readiness])

  const readinessOverall = useMemo(
    () => String(readiness?.overall_status || 'missing'),
    [readiness],
  )

  const readinessLayers = useMemo<ReadinessLayer[]>(
    () => (Array.isArray(readiness?.layers) ? readiness.layers : []),
    [readiness],
  )

  return {
    readinessLoading,
    readinessPercent,
    readinessOverall,
    readinessLayers,
    showRolePlaybook,
    setShowRolePlaybook,
    runReadinessCheck,
  }
}
