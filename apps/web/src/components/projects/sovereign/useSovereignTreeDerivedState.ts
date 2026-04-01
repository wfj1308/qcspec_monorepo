import { useMemo } from 'react'

import type {
  ActiveGenesisSummary,
  GateStats,
  SummaryMetrics,
  TreeNode,
} from './types'

type TreeAggregate = {
  contract: number
  approved: number
  design: number
  settled: number
  consumed: number
}

type UseSovereignTreeDerivedStateArgs = {
  activeUri: string
  byUri: Map<string, TreeNode>
  nodes: TreeNode[]
  byCode: Map<string, TreeNode>
}

type UseSovereignActiveGenesisSummaryArgs = {
  active: TreeNode | null
  byCode: Map<string, TreeNode>
  filteredDocs: Array<Record<string, unknown>>
  gateStats: GateStats
  summary: SummaryMetrics
}

export function useSovereignTreeDerivedState({
  activeUri,
  byUri,
  nodes,
  byCode,
}: UseSovereignTreeDerivedStateArgs) {
  const active = useMemo(() => byUri.get(activeUri) || null, [activeUri, byUri])

  const smuOptions = useMemo(() => {
    const seen = new Set<string>()
    const values: string[] = []
    nodes.forEach((node) => {
      if (!node.isLeaf) return
      const smu = String(node.code || '').split('-')[0]
      if (!smu || seen.has(smu)) return
      seen.add(smu)
      values.push(smu)
    })
    return values.sort((left, right) => left.localeCompare(right, 'zh-CN'))
  }, [nodes])

  const aggMap = useMemo(() => {
    const memo = new Map<string, TreeAggregate>()
    const walk = (code: string): TreeAggregate => {
      if (memo.has(code)) return memo.get(code) as TreeAggregate
      const node = byCode.get(code)
      if (!node) return { contract: 0, approved: 0, design: 0, settled: 0, consumed: 0 }
      if (node.isLeaf) {
        const aggregate = {
          contract: Number.isFinite(node.contractQty) ? node.contractQty : 0,
          approved: Number.isFinite(node.approvedQty as number) ? (node.approvedQty as number) : 0,
          design: Number.isFinite(node.designQty as number) ? (node.designQty as number) : 0,
          settled: Number.isFinite(node.settledQty as number) ? (node.settledQty as number) : 0,
          consumed: Number.isFinite(node.consumedQty as number) ? (node.consumedQty as number) : 0,
        }
        memo.set(code, aggregate)
        return aggregate
      }
      const aggregate = node.children.reduce<TreeAggregate>(
        (acc, child) => {
          const childAggregate = walk(child)
          return {
            contract: acc.contract + childAggregate.contract,
            approved: acc.approved + childAggregate.approved,
            design: acc.design + childAggregate.design,
            settled: acc.settled + childAggregate.settled,
            consumed: acc.consumed + childAggregate.consumed,
          }
        },
        { contract: 0, approved: 0, design: 0, settled: 0, consumed: 0 },
      )
      memo.set(code, aggregate)
      return aggregate
    }
    nodes.forEach((node) => {
      walk(node.code)
    })
    return memo
  }, [byCode, nodes])

  const summary = useMemo<SummaryMetrics>(() => {
    if (!active) return { contract: 0, approved: 0, design: 0, settled: 0, consumed: 0, pct: 0 }
    const aggregate = aggMap.get(active.code) || { contract: 0, approved: 0, design: 0, settled: 0, consumed: 0 }
    const effective = aggregate.settled
    const baseline = aggregate.approved > 0 ? aggregate.approved : (aggregate.contract > 0 ? aggregate.contract : aggregate.design)
    return {
      contract: aggregate.contract,
      approved: aggregate.approved,
      design: aggregate.design,
      settled: aggregate.settled,
      consumed: aggregate.consumed,
      pct: baseline > 0 ? (effective * 100) / baseline : 0,
    }
  }, [active, aggMap])

  return {
    active,
    smuOptions,
    aggMap,
    summary,
  }
}

export function useSovereignActiveGenesisSummary({
  active,
  byCode,
  filteredDocs,
  gateStats,
  summary,
}: UseSovereignActiveGenesisSummaryArgs) {
  return useMemo<ActiveGenesisSummary>(() => {
    if (!active) {
      return {
        contractQty: 0,
        progressPct: 0,
        reportedPct: 0,
        leafCount: 0,
        contractDocCount: 0,
      }
    }
    let leafCount = 0
    const stack = [active.code]
    while (stack.length) {
      const code = stack.pop() as string
      const node = byCode.get(code)
      if (!node) continue
      if (node.isLeaf) {
        leafCount += 1
        continue
      }
      node.children.forEach((child) => stack.push(child))
    }
    const contractQty = summary.contract > 0 ? summary.contract : summary.design
    const reportedPct = gateStats.total > 0 ? ((gateStats.pass + gateStats.fail) * 100) / gateStats.total : summary.pct
    const contractDocCount = filteredDocs.filter((doc) => {
      const text = `${String(doc.doc_type || '')} ${String(doc.file_name || '')}`.toLowerCase()
      return text.includes('contract') || text.includes('合同')
    }).length
    return {
      contractQty,
      progressPct: summary.pct,
      reportedPct,
      leafCount,
      contractDocCount,
    }
  }, [active, byCode, filteredDocs, gateStats.fail, gateStats.pass, gateStats.total, summary.contract, summary.design, summary.pct])
}
