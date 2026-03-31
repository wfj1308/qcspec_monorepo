import React from 'react'
import { useProjectSovereign } from './SovereignContext'
import type { TreeNode, TreeSearchState } from './types'

const statusColor = {
  Genesis: '#64748B',
  Spending: '#2563EB',
  Settled: '#16A34A',
} as const

function spuTreeGeneLabel(spu: string) {
  const value = String(spu || '').toUpperCase()
  if (value.includes('REINFORCEMENT')) return 'SPU 钢筋'
  if (value.includes('CONCRETE')) return 'SPU 混凝土'
  if (value.includes('BRIDGE')) return 'SPU 桥梁'
  if (value.includes('LANDSCAPE')) return 'SPU 绿化'
  if (value.includes('CONTRACT')) return 'SPU 合同'
  if (value.includes('PHYSICAL')) return 'SPU 实体'
  return 'SPU 组'
}

type Props = {
  panelCls: string
  inputBaseCls: string
  btnBlueCls: string
  boqFileRef: React.RefObject<HTMLInputElement | null>
  fileName: string
  importing: boolean
  importJobId: string
  importStatusText: string
  importProgress: number
  importError: string
  showLeftSummary: boolean
  treeQuery: string
  treeSearch: TreeSearchState
  nodes: TreeNode[]
  roots: string[]
  byCode: Map<string, TreeNode>
  aggMap: Map<string, { contract: number; approved: number; design: number; settled: number; consumed: number }>
  expandedCodes: string[]
  nodePathMap: Map<string, string>
  onSelectFile: (file: File | null) => void
  onImportGenesis: () => void | Promise<void>
  onLoadBuiltinLedger400: () => void | Promise<void>
  onToggleSummary: () => void
  onTreeQueryChange: (value: string) => void
  onToggleExpanded: (code: string) => void
  onSelectNode: (code: string) => void | Promise<void>
}

export default function GenesisTree({
  panelCls,
  inputBaseCls,
  btnBlueCls,
  boqFileRef,
  fileName,
  importing,
  importJobId,
  importStatusText,
  importProgress,
  importError,
  showLeftSummary,
  treeQuery,
  treeSearch,
  nodes,
  roots,
  byCode,
  aggMap,
  expandedCodes,
  nodePathMap,
  onSelectFile,
  onImportGenesis,
  onLoadBuiltinLedger400,
  onToggleSummary,
  onTreeQueryChange,
  onToggleExpanded,
  onSelectNode,
}: Props) {
  const { project, asset } = useProjectSovereign()

  const renderTree = (code: string, depth: number): React.ReactNode => {
    const node = byCode.get(code)
    if (!node) return null
    if (treeSearch.active && !treeSearch.visible.has(code)) return null

    const childList = treeSearch.active ? node.children.filter((child) => treeSearch.visible.has(child)) : node.children
    const hasChildren = childList.length > 0
    const agg = aggMap.get(code) || { contract: 0, approved: 0, design: 0, settled: 0, consumed: 0, pct: 0 }
    const baseQty = agg.approved > 0 ? agg.approved : (agg.contract > 0 ? agg.contract : agg.design)
    const expanded = hasChildren
      ? (treeSearch.active ? treeSearch.expanded.includes(code) : expandedCodes.includes(code))
      : false
    const tone = node.code.startsWith('401')
      ? 'from-emerald-950/60 via-slate-900/80 to-slate-900/60'
      : node.code.startsWith('600')
        ? 'from-lime-950/60 via-slate-900/80 to-slate-900/60'
        : node.spu === 'SPU_Contract'
          ? 'from-amber-950/50 via-slate-900/80 to-slate-900/60'
          : 'from-slate-900/70 via-slate-900/80 to-slate-900/60'
    const toneBorder = node.code.startsWith('401')
      ? 'border-emerald-600/40'
      : node.code.startsWith('600')
        ? 'border-lime-600/40'
        : node.spu === 'SPU_Contract'
          ? 'border-amber-600/40'
          : 'border-slate-500/30'
    const activeCls = project.activeUri === node.uri
      ? 'border-blue-500 shadow-[inset_0_0_0_1px_rgba(59,130,246,.35)]'
      : `${toneBorder} hover:bg-slate-900/90 hover:border-slate-400/40`
    const progressRatio = baseQty > 0 ? agg.settled / baseQty : 0
    const statusBadge = node.status === 'Settled'
      ? { label: 'Settled', cls: 'border-emerald-500/70 text-emerald-200 bg-emerald-950/30' }
      : node.status === 'Spending'
        ? { label: 'Spending', cls: 'border-sky-500/70 text-sky-200 bg-sky-950/30' }
        : { label: 'Genesis', cls: 'border-slate-500/70 text-slate-300 bg-slate-900/60' }

    return (
      <React.Fragment key={code}>
        <button
          type="button"
          onClick={() => void onSelectNode(code)}
          title={`${nodePathMap.get(code) || node.uri} · ${node.status}`}
          className={`w-full grid grid-cols-[12px_12px_1fr_auto] gap-2 items-center rounded-lg bg-gradient-to-r px-3 py-2 text-left text-[13px] leading-5 text-slate-200 transition ${tone} ${activeCls}`}
          style={{ paddingLeft: `${8 + depth * 14}px` }}
        >
          <span
            style={{
              width: 10,
              height: 10,
              borderRadius: 999,
              background: statusColor[node.status],
              boxShadow: `0 0 8px ${statusColor[node.status]}`,
              animation: 'sovereignPulse 1.8s infinite ease-in-out',
            }}
          />
          <span
            role="button"
            tabIndex={0}
            onClick={(event) => {
              event.preventDefault()
              event.stopPropagation()
              if (!hasChildren) return
              onToggleExpanded(code)
            }}
            onKeyDown={(event) => {
              if (event.key !== 'Enter' && event.key !== ' ') return
              event.preventDefault()
              event.stopPropagation()
              if (!hasChildren) return
              onToggleExpanded(code)
            }}
            className={`text-[11px] ${hasChildren ? 'cursor-pointer text-slate-400 hover:text-sky-300' : 'text-slate-700'}`}
            aria-label={hasChildren ? (expanded ? '折叠节点' : '展开节点') : '叶子节点'}
          >
            {hasChildren ? (expanded ? '▼' : '▶') : '•'}
          </span>
          <span className="truncate">
            <span className="font-mono text-slate-300">{node.code}</span> - {node.name}
            <span className="mt-0.5 block truncate text-[10px] text-slate-400">{nodePathMap.get(code) || node.uri}</span>
            <span className="mt-1.5 block h-1 w-full overflow-hidden rounded-full border border-slate-700/60 bg-slate-950/80">
              <span
                className={`block h-1 ${progressRatio >= 1 ? 'bg-rose-500' : progressRatio > 0 ? 'bg-amber-500' : 'bg-emerald-500'}`}
                style={{ width: `${Math.max(6, Math.min(100, progressRatio * 100))}%` }}
              />
            </span>
          </span>
          <span className="flex items-center justify-end gap-1.5">
            <span className="rounded-full border border-slate-700/80 bg-slate-950/70 px-1.5 py-0.5 text-[10px] text-slate-400">
              {spuTreeGeneLabel(node.spu)}
            </span>
            <span className={`rounded-full border px-1.5 py-0.5 text-[10px] ${statusBadge.cls}`}>{statusBadge.label}</span>
            <span className="rounded-full border border-slate-500/60 bg-slate-950/60 px-1.5 py-0.5 text-[10px] text-slate-300">
              {baseQty.toLocaleString()}
            </span>
          </span>
        </button>
        {expanded && childList.map((child) => renderTree(child, depth + 1))}
      </React.Fragment>
    )
  }

  const visibleRoots = treeSearch.active ? roots.filter((code) => treeSearch.visible.has(code)) : roots

  return (
    <div className={`${panelCls} wb-panel flex flex-col`}>
      <div className="mb-2 flex items-center justify-between">
        <div className="text-sm font-extrabold">步骤 1：Genesis 主权树</div>
        <span className="rounded-full border border-slate-700 bg-slate-800/90 px-2 py-0.5 text-[10px] text-slate-400">资产初始化</span>
      </div>
      <div className="grid grid-cols-[auto_auto_1fr] items-center gap-2">
        <button type="button" onClick={() => boqFileRef.current?.click()} className="rounded-lg border border-slate-700 bg-slate-950/80 px-3 py-2 text-sm leading-5 text-slate-200">
          选择清单文件
        </button>
        <button type="button" onClick={() => void onLoadBuiltinLedger400()} className={`px-3 py-2 text-sm ${btnBlueCls}`}>
          加载 0#台账-400章
        </button>
        <div className={`truncate text-sm leading-5 ${fileName ? 'text-slate-200' : 'text-slate-500'}`}>{fileName || '未选择任何文件'}</div>
        <input ref={boqFileRef} type="file" accept=".csv,.xlsx,.xls" onChange={(e) => onSelectFile(e.target.files?.[0] || null)} className="hidden" />
      </div>
      <div className="mt-1 text-[11px] text-slate-400">支持 .csv / .xlsx / .xls；建议优先使用 .xlsx 或 CSV</div>
      <button type="button" onClick={() => void onImportGenesis()} disabled={importing} className={`mt-2 w-full px-3 py-2 font-bold disabled:opacity-60 ${btnBlueCls}`}>
        {importing ? '锚定中...' : '导入并锚定清单'}
      </button>
      {(importing || importJobId) && (
        <div className="mt-2 rounded-lg border border-slate-700/70 bg-slate-950/60 p-2">
          <div className="flex items-center justify-between text-xs text-slate-300">
            <span>{importStatusText || '执行中'}</span>
            <span>{Math.max(0, Math.min(100, importProgress))}%</span>
          </div>
          <div className="mt-1 h-2 w-full overflow-hidden rounded-full border border-slate-700/80 bg-slate-900">
            <div className="h-2 bg-sky-500 transition-[width] duration-500" style={{ width: `${Math.max(0, Math.min(100, importProgress))}%` }} />
          </div>
        </div>
      )}
      {!!importError && (
        <div className="mt-2 rounded-lg border border-rose-500/70 bg-rose-950/40 p-2 text-xs text-rose-200">
          导入失败原因：{importError}
        </div>
      )}
      <div className="mt-3 rounded-2xl border border-slate-700/80 bg-[linear-gradient(135deg,rgba(8,47,73,.32),rgba(2,6,23,.86))] p-3 shadow-[0_16px_32px_rgba(2,6,23,.28)]">
        <div className="flex items-start justify-between gap-3">
          <div>
            <div className="text-[11px] uppercase tracking-[0.18em] text-sky-300/80">Genesis Summary</div>
            <div className="mt-1 text-sm font-bold text-slate-100">{project.active?.name || '等待选择主权节点'}</div>
            <div className="mt-1 break-all text-[11px] text-slate-400">{project.activePath || project.displayProjectUri || 'v://project/boq/400'}</div>
          </div>
          <span className={`rounded-full border px-2 py-0.5 text-[10px] ${project.active ? (project.active.status === 'Settled' ? 'border-emerald-500/70 bg-emerald-950/30 text-emerald-200' : project.active.status === 'Spending' ? 'border-sky-500/70 bg-sky-950/30 text-sky-200' : 'border-slate-500/70 bg-slate-900/70 text-slate-300') : 'border-slate-600/70 bg-slate-900/70 text-slate-400'}`}>
            {project.active ? project.active.status : 'Genesis'}
          </span>
        </div>
        <div className="mt-3 grid gap-2 min-[460px]:grid-cols-2">
          <div className="rounded-xl border border-slate-700/70 bg-slate-950/55 px-3 py-2">
            <div className="text-[11px] text-slate-400">合同数量</div>
            <div className="mt-1 text-lg font-semibold text-slate-50">{asset.activeGenesisSummary.contractQty.toLocaleString()}</div>
            <div className="text-[11px] text-slate-500">合同单据 {asset.activeGenesisSummary.contractDocCount} · 叶子节点 {asset.activeGenesisSummary.leafCount}</div>
          </div>
          <div className="rounded-xl border border-slate-700/70 bg-slate-950/55 px-3 py-2">
            <div className="flex items-center justify-between text-[11px] text-slate-400">
              <span>已报验进度</span>
              <span>{asset.activeGenesisSummary.reportedPct.toFixed(2)}%</span>
            </div>
            <div className="mt-2 h-2.5 w-full overflow-hidden rounded-full border border-slate-700 bg-slate-900">
              <div className="h-2.5 bg-gradient-to-r from-sky-500 via-emerald-500 to-emerald-300" style={{ width: `${Math.max(0, Math.min(100, asset.activeGenesisSummary.reportedPct))}%` }} />
            </div>
            <div className="mt-1 text-[11px] text-slate-500">Genesis 锚定进度 {asset.activeGenesisSummary.progressPct.toFixed(2)}%</div>
          </div>
        </div>
      </div>
      <div className="mt-3 flex items-center justify-between">
        <div className="text-xs text-slate-400">核心信息优先展示</div>
        <button type="button" onClick={onToggleSummary} className={`px-3 py-1.5 text-xs ${btnBlueCls}`}>
          {showLeftSummary ? '收起资产摘要' : '展开资产摘要'}
        </button>
      </div>
      {showLeftSummary && (
        <div className="mt-2 mb-3 rounded-xl border border-slate-700/70 bg-slate-900/50 p-3 text-sm leading-6">
          <div className="grid gap-1">
            <div>创世总量(BOM): {(asset.summary.contract > 0 ? asset.summary.contract : asset.summary.design).toLocaleString()}</div>
            <div className="text-xs text-slate-400">设计总量: {asset.summary.design.toLocaleString()}</div>
            <div>已结算累计量: {asset.summary.settled.toLocaleString()}</div>
            <div>剩余额度: {asset.availableTotal.toLocaleString()}</div>
            <div className="text-xs text-slate-400">SPU 基因绑定: {spuTreeGeneLabel(project.active?.spu || '')}</div>
          </div>
          <div className="mt-2 h-2.5 w-full overflow-hidden rounded-full border border-slate-700/70 bg-slate-950">
            <div style={{ width: `${Math.max(0, Math.min(100, asset.summary.pct))}%` }} className="h-2.5 bg-gradient-to-r from-slate-500 via-sky-500 to-emerald-500" />
          </div>
          <div className="mt-1 text-xs text-emerald-300">当前进度: {asset.summary.pct.toFixed(2)}%</div>
        </div>
      )}
      <div className="mb-3 grid grid-cols-[1fr_auto] gap-2">
        <input value={treeQuery} onChange={(e) => onTreeQueryChange(e.target.value)} placeholder="搜索细目号 / 名称" className={inputBaseCls} />
        <button type="button" onClick={() => onTreeQueryChange('')} className={`px-3 py-2 text-sm ${btnBlueCls}`} disabled={!treeQuery.trim()}>
          清除
        </button>
      </div>
      {treeSearch.active && (
        <div className="mb-2 text-xs text-slate-400">
          命中 {treeSearch.matched.length} 项 · 展示 {treeSearch.visible.size} 节点
        </div>
      )}
      <div className="grid min-h-[520px] flex-1 gap-2 overflow-y-auto pr-1">
        {!nodes.length && (
          <div className="grid min-h-[220px] place-items-center rounded-2xl border border-dashed border-slate-700/80 bg-slate-950/35 p-5 text-center">
            <div>
              <div className="text-sm font-semibold text-slate-200">上传 CSV 以生成 v:// 主权树</div>
              <div className="mt-1 text-xs text-slate-500">识别“子目号”后会自动递归生成左侧 Sovereign Tree，并绑定 SPU 基因。</div>
            </div>
          </div>
        )}
        {visibleRoots.map((code) => renderTree(code, 0))}
      </div>
    </div>
  )
}
