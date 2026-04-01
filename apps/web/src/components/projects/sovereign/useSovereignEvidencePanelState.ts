import { useMemo, useState } from 'react'

type ScanChainBadge = {
  label: string
  cls: string
}

type UseSovereignEvidencePanelStateArgs = {
  activeUri: string
  scanEntryItems: Array<Record<string, unknown>>
}

export function useSovereignEvidencePanelState({
  activeUri,
  scanEntryItems,
}: UseSovereignEvidencePanelStateArgs) {
  const [showAllScanEntries, setShowAllScanEntries] = useState(false)

  const scanEntryLatest = useMemo(() => {
    const filtered = scanEntryItems.filter((item) => {
      const itemUri = String(item.item_uri || item.boq_item_uri || '')
      if (!activeUri) return true
      return itemUri ? itemUri === activeUri : true
    })
    if (!filtered.length) return null
    const ranked = filtered
      .map((item) => {
        const t = Date.parse(String(item.created_at || item.scan_entry_at || ''))
        return { item, t: Number.isFinite(t) ? t : 0 }
      })
      .sort((a, b) => b.t - a.t)
    return ranked[0]?.item || null
  }, [activeUri, scanEntryItems])

  const scanChainStatus = String(scanEntryLatest?.chain_status || '').trim()
  const scanChainBadge: ScanChainBadge = scanChainStatus === 'onchain'
    ? { label: '已上链', cls: 'bg-emerald-900/40 text-emerald-200 border-emerald-500/60' }
    : scanChainStatus
      ? { label: '待上链', cls: 'bg-amber-900/40 text-amber-200 border-amber-500/60' }
      : { label: '未知', cls: 'bg-slate-900/40 text-slate-400 border-slate-600/60' }

  const scanEntryActiveOnly = useMemo(() => {
    return scanEntryItems.filter((item) => {
      if (showAllScanEntries || !activeUri) return true
      const itemUri = String(item.item_uri || item.boq_item_uri || '')
      return itemUri ? itemUri === activeUri : true
    })
  }, [activeUri, scanEntryItems, showAllScanEntries])

  return {
    showAllScanEntries,
    setShowAllScanEntries,
    scanEntryLatest,
    scanChainBadge,
    scanEntryActiveOnly,
  }
}
