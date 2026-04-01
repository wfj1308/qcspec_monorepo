import { useCallback, useMemo, useState } from 'react'

import { parseNumericInput } from './analysisUtils'
import { normalizeItemNo, toDisplayUri } from './treeUtils'

type ArNode = {
  code: string
}

type UseSovereignArViewArgs = {
  arItems: Array<Record<string, unknown>>
  byCode: Map<string, ArNode>
  byUri: Map<string, ArNode>
  selectNode: (code: string) => Promise<void>
  showToast: (message: string) => void
}

export function useSovereignArView({
  arItems,
  byCode,
  byUri,
  selectNode,
  showToast,
}: UseSovereignArViewArgs) {
  const [arFocus, setArFocus] = useState<Record<string, unknown> | null>(null)
  const [arFullscreen, setArFullscreen] = useState(false)
  const [arFilterMax, setArFilterMax] = useState('120')

  const arItemsSorted = useMemo(() => {
    return [...arItems].sort((a, b) => {
      const da = Number(a.distance_m ?? 0)
      const db = Number(b.distance_m ?? 0)
      return da - db
    })
  }, [arItems])

  const arFilterMaxValue = useMemo(() => {
    const parsed = parseNumericInput(arFilterMax)
    return parsed != null && parsed > 0 ? parsed : 0
  }, [arFilterMax])

  const arFilteredItems = useMemo(() => {
    if (!arFilterMaxValue) return arItemsSorted
    return arItemsSorted.filter((item) => Number(item.distance_m ?? 0) <= arFilterMaxValue)
  }, [arItemsSorted, arFilterMaxValue])

  const arPrimary = arItems.length ? arItems[0] : null

  const jumpToArItem = useCallback(async (item: Record<string, unknown>) => {
    const code = normalizeItemNo(String(item.item_no || item.item_code || ''))
    const uri = toDisplayUri(String(item.boq_item_uri || item.segment_uri || ''))
    const node = (code && byCode.get(code)) || (uri && byUri.get(uri)) || null
    if (!node) {
      showToast('未找到对应细目')
      return
    }
    await selectNode(node.code)
    setArFocus(null)
  }, [byCode, byUri, selectNode, showToast])

  const openArFocus = useCallback((item: Record<string, unknown>) => {
    setArFocus(item)
  }, [])

  const closeArFocus = useCallback(() => {
    setArFocus(null)
  }, [])

  const openArFullscreen = useCallback(() => {
    setArFullscreen(true)
  }, [])

  const closeArFullscreen = useCallback(() => {
    setArFullscreen(false)
  }, [])

  const selectArFullscreenItem = useCallback((item: Record<string, unknown>) => {
    setArFocus(item)
    setArFullscreen(false)
  }, [])

  return {
    arFocus,
    arFullscreen,
    arFilterMax,
    arItemsSorted,
    arFilteredItems,
    arPrimary,
    setArFilterMax,
    openArFocus,
    closeArFocus,
    openArFullscreen,
    closeArFullscreen,
    selectArFullscreenItem,
    jumpToArItem,
  }
}
