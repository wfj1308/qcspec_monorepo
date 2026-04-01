import { useMemo } from 'react'

import type { TreeNode, TreeSearchState } from './types'
import { normalizeSearch } from './treeUtils'

type Args = {
  nodes: TreeNode[]
  treeQuery: string
}

export function useSovereignTreeSearchState({
  nodes,
  treeQuery,
}: Args) {
  const byUri = useMemo(
    () => new Map(nodes.map((node) => [node.uri, node])),
    [nodes],
  )

  const byCode = useMemo(
    () => new Map(nodes.map((node) => [node.code, node])),
    [nodes],
  )

  const roots = useMemo(
    () => nodes.filter((node) => !node.parent).map((node) => node.code),
    [nodes],
  )

  const treeSearch = useMemo<TreeSearchState>(() => {
    const query = normalizeSearch(treeQuery)
    if (!query) {
      return { active: false, visible: new Set<string>(), expanded: [], matched: [] }
    }

    const matched = nodes.filter((node) => {
      const code = normalizeSearch(node.code)
      const name = normalizeSearch(node.name)
      return code.includes(query) || name.includes(query)
    })

    const visible = new Set<string>()
    matched.forEach((node) => {
      visible.add(node.code)
      let parent = node.parent
      while (parent) {
        visible.add(parent)
        parent = byCode.get(parent)?.parent || ''
      }
    })

    if (byCode.get('400')) visible.add('400')

    const expanded = Array.from(visible).filter((code) => {
      const node = byCode.get(code)
      if (!node) return false
      return node.children.some((child) => visible.has(child))
    })

    return { active: true, visible, expanded, matched }
  }, [byCode, nodes, treeQuery])

  return {
    byUri,
    byCode,
    roots,
    treeSearch,
  }
}
