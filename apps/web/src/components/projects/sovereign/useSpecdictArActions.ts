import { useCallback, useState } from 'react'

type UseSpecdictArActionsArgs = {
  apiProjectUri: string
  specdictProjectUris: string
  specdictMinSamples: string
  specdictNamespace: string
  specdictCommit: boolean
  lat: string
  lng: string
  arRadius: string
  arLimit: string
  specdictEvolve: (payload: { project_uris: string[]; min_samples: number }) => Promise<unknown>
  specdictExport: (payload: {
    project_uris: string[]
    min_samples: number
    namespace_uri: string
    commit: boolean
  }) => Promise<unknown>
  arOverlay: (payload: {
    project_uri: string
    lat: number
    lng: number
    radius_m: number
    limit: number
  }) => Promise<unknown>
  showToast: (message: string) => void
}

function parseProjectUris(raw: string) {
  return String(raw || '')
    .split(/[\n,]+/)
    .map((item) => item.trim())
    .filter(Boolean)
}

export function useSpecdictArActions({
  apiProjectUri,
  specdictProjectUris,
  specdictMinSamples,
  specdictNamespace,
  specdictCommit,
  lat,
  lng,
  arRadius,
  arLimit,
  specdictEvolve,
  specdictExport,
  arOverlay,
  showToast,
}: UseSpecdictArActionsArgs) {
  const [specdictLoading, setSpecdictLoading] = useState(false)
  const [specdictExporting, setSpecdictExporting] = useState(false)
  const [specdictRes, setSpecdictRes] = useState<Record<string, unknown> | null>(null)
  const [arLoading, setArLoading] = useState(false)
  const [arRes, setArRes] = useState<Record<string, unknown> | null>(null)

  const runSpecdictEvolve = useCallback(async () => {
    const uris = parseProjectUris(specdictProjectUris)
    setSpecdictLoading(true)
    try {
      const payload = await specdictEvolve({
        project_uris: uris,
        min_samples: Number(specdictMinSamples || 0) || 5,
      }) as Record<string, unknown> | null
      if (!payload?.ok) {
        showToast('SpecDict 进化分析失败')
        return
      }
      setSpecdictRes(payload)
      showToast(`SpecDict 已分析：规则 ${String(payload.total_rules || 0)}`)
    } catch (err) {
      const msg = err instanceof Error ? err.message : '请求异常'
      showToast(`SpecDict 进化分析失败：${msg}`)
    } finally {
      setSpecdictLoading(false)
    }
  }, [showToast, specdictEvolve, specdictMinSamples, specdictProjectUris])

  const runSpecdictExport = useCallback(async () => {
    const uris = parseProjectUris(specdictProjectUris)
    setSpecdictExporting(true)
    try {
      const payload = await specdictExport({
        project_uris: uris,
        min_samples: Number(specdictMinSamples || 0) || 5,
        namespace_uri: specdictNamespace,
        commit: specdictCommit,
      }) as Record<string, unknown> | null
      if (!payload?.ok) {
        showToast('SpecDict 模板导出失败')
        return
      }
      setSpecdictRes(payload)
      showToast(`SpecDict 模板已导出 ${specdictCommit ? '并写入全局' : '为预览'}`)
    } catch (err) {
      const msg = err instanceof Error ? err.message : '请求异常'
      showToast(`SpecDict 模板导出失败：${msg}`)
    } finally {
      setSpecdictExporting(false)
    }
  }, [showToast, specdictCommit, specdictExport, specdictMinSamples, specdictNamespace, specdictProjectUris])

  const runArOverlay = useCallback(async () => {
    if (!apiProjectUri) {
      showToast('项目 URI 缺失')
      return
    }
    const latNum = Number(lat)
    const lngNum = Number(lng)
    if (!Number.isFinite(latNum) || !Number.isFinite(lngNum)) {
      showToast('请提供有效 GPS 坐标')
      return
    }
    setArLoading(true)
    try {
      const payload = await arOverlay({
        project_uri: apiProjectUri,
        lat: latNum,
        lng: lngNum,
        radius_m: Number(arRadius || 0) || 80,
        limit: Number(arLimit || 0) || 50,
      }) as Record<string, unknown> | null
      if (!payload?.ok) {
        showToast('AR 叠加获取失败')
        return
      }
      setArRes(payload)
      showToast(`AR 叠加完成：${String((payload.items as Array<Record<string, unknown>> | undefined)?.length || 0)} 处锚点`)
    } catch (err) {
      const msg = err instanceof Error ? err.message : '请求异常'
      showToast(`AR 叠加获取失败：${msg}`)
    } finally {
      setArLoading(false)
    }
  }, [apiProjectUri, arLimit, arOverlay, arRadius, lat, lng, showToast])

  return {
    specdictLoading,
    specdictExporting,
    specdictRes,
    runSpecdictEvolve,
    runSpecdictExport,
    arLoading,
    arRes,
    runArOverlay,
  }
}
