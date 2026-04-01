import React from 'react'

import { ROLE_PLAYBOOK } from './workbenchConfig'

type ReadinessLayer = {
  key: string
  name: string
  status?: string
}

type Props = {
  isGenesisView: boolean
  readinessOverall: string
  readinessLoading: boolean
  readinessPercent: number
  readinessLayers: ReadinessLayer[]
  readinessAction: Record<string, string>
  showRolePlaybook: boolean
  btnBlueCls: string
  btnGreenCls: string
  btnAmberCls: string
  panelCls: string
  apiProjectUri: string
  specBinding: string
  gateBinding: string
  normRefs: string[]
  isSpecBound: boolean
  lifecycle: string
  activeCode: string
  availableTotal: number
  activePath: string
  displayProjectUri: string
  onRunReadinessCheck: () => void
  onToggleRolePlaybook: () => void
  onNavigateTrip?: (() => void) | undefined
  onNavigateAudit?: (() => void) | undefined
}

export default function SovereignGenesisOverview({
  isGenesisView,
  readinessOverall,
  readinessLoading,
  readinessPercent,
  readinessLayers,
  readinessAction,
  showRolePlaybook,
  btnBlueCls,
  btnGreenCls,
  btnAmberCls,
  panelCls,
  apiProjectUri,
  specBinding,
  gateBinding,
  normRefs,
  isSpecBound,
  lifecycle,
  activeCode,
  availableTotal,
  activePath,
  displayProjectUri,
  onRunReadinessCheck,
  onToggleRolePlaybook,
  onNavigateTrip,
  onNavigateAudit,
}: Props) {
  if (!isGenesisView) return null

  return (
    <>
      <div className="mb-4 rounded-xl border border-slate-700/80 bg-slate-950/55 p-3 shadow-[0_18px_36px_rgba(2,6,23,.2)]">
        <div className="flex flex-wrap items-center justify-between gap-2">
          <div>
            <div className="text-xs uppercase tracking-[0.18em] text-slate-400">Project Readiness / 项目完备度</div>
            <div className="mt-1 text-sm font-bold text-slate-100">七步闭环落地体检</div>
          </div>
          <div className="flex items-center gap-2">
            <span className={`rounded-full border px-2.5 py-1 text-xs font-semibold ${
              readinessOverall === 'complete'
                ? 'border-emerald-500/60 bg-emerald-950/30 text-emerald-200'
                : readinessOverall === 'partial'
                  ? 'border-amber-500/60 bg-amber-950/30 text-amber-200'
                  : 'border-rose-500/60 bg-rose-950/30 text-rose-200'
            }`}>
              {readinessOverall === 'complete' ? '已落地' : readinessOverall === 'partial' ? '部分落地' : '待落地'}
            </span>
            <button type="button" onClick={onRunReadinessCheck} disabled={readinessLoading || !apiProjectUri} className={`px-3 py-1.5 text-xs disabled:opacity-60 ${btnBlueCls}`}>
              {readinessLoading ? '体检中...' : '运行体检'}
            </button>
            <button type="button" onClick={onToggleRolePlaybook} className={`px-3 py-1.5 text-xs ${btnGreenCls}`}>
              {showRolePlaybook ? '收起角色SOP' : '展开角色SOP'}
            </button>
          </div>
        </div>
        <div className="mt-3 h-2.5 w-full overflow-hidden rounded-full border border-slate-700 bg-slate-900">
          <div className="h-2.5 bg-gradient-to-r from-sky-500 to-emerald-500 transition-[width] duration-500" style={{ width: `${readinessPercent}%` }} />
        </div>
        <div className="mt-1 text-xs text-slate-400">当前落地度: {readinessPercent.toFixed(2)}%</div>

        {!!readinessLayers.length && (
          <div className="mt-3 grid gap-2 min-[1100px]:grid-cols-2">
            {readinessLayers.map((layer) => {
              const st = String(layer.status || 'missing')
              return (
                <div key={layer.key} className="rounded-lg border border-slate-700 bg-slate-900/60 p-2.5">
                  <div className="flex items-center justify-between gap-2">
                    <div className="text-sm font-semibold text-slate-100">{layer.name}</div>
                    <span className={`rounded-full px-2 py-0.5 text-[11px] font-semibold ${
                      st === 'complete'
                        ? 'bg-emerald-950/40 text-emerald-300'
                        : st === 'partial'
                          ? 'bg-amber-950/40 text-amber-300'
                          : 'bg-rose-950/40 text-rose-300'
                    }`}>
                      {st === 'complete' ? '完成' : st === 'partial' ? '部分' : '缺失'}
                    </span>
                  </div>
                  <div className="mt-1 text-xs text-slate-400">{readinessAction[layer.key] || '补齐该层关键流程数据后重试体检'}</div>
                </div>
              )
            })}
          </div>
        )}

        {showRolePlaybook && (
          <div className="mt-3 grid gap-2 min-[1200px]:grid-cols-2">
            {ROLE_PLAYBOOK.map((item) => (
              <div key={item.role} className="rounded-lg border border-slate-700 bg-slate-900/70 p-3">
                <div className="text-sm font-bold text-slate-100">{item.title} <span className="text-xs text-slate-500">({item.role})</span></div>
                <div className="mt-1 text-xs text-slate-400">目标: {item.goal}</div>
                <div className="mt-2 text-xs font-semibold text-slate-300">操作行为</div>
                <div className="text-xs text-slate-400">{item.actions.join('；')}</div>
                <div className="mt-2 text-xs font-semibold text-slate-300">技术约束</div>
                <div className="text-xs text-slate-400">{item.constraints.join('；')}</div>
                <div className="mt-2 text-xs font-semibold text-slate-300">闭环路径</div>
                <div className="text-xs text-slate-200 font-mono break-all">{item.chain}</div>
              </div>
            ))}
          </div>
        )}
      </div>

      <div className={`${panelCls} wb-panel`}>
        <div className="mb-2 flex items-center justify-between">
          <div className="text-sm font-extrabold">Project Genesis</div>
          <span className="rounded-full border border-slate-700 bg-slate-800/90 px-2 py-0.5 text-[10px] text-slate-400">Config view</span>
        </div>
        <div className="grid gap-3 min-[980px]:grid-cols-2">
          <div className="rounded-xl border border-slate-700/70 bg-slate-950/30 p-3">
            <div className="text-xs font-semibold uppercase tracking-[0.18em] text-slate-400">Norm Binding</div>
            <div className="mt-2 text-sm text-slate-100">Spec: {specBinding || 'Unbound'}</div>
            <div className="mt-1 text-sm text-slate-300">Gate: {gateBinding || 'Unbound'}</div>
            <div className="mt-1 text-xs text-slate-500">Refs: {normRefs.join(' / ') || '-'}</div>
            <div className={`mt-2 text-xs ${isSpecBound ? 'text-emerald-300' : 'text-amber-300'}`}>
              {isSpecBound ? 'NormResolver ready for routing.' : 'NormResolver still needs binding.'}
            </div>
          </div>
          <div className="rounded-xl border border-slate-700/70 bg-slate-950/30 p-3">
            <div className="text-xs font-semibold uppercase tracking-[0.18em] text-slate-400">Project Control</div>
            <div className="mt-2 text-sm text-slate-100">Lifecycle: {lifecycle}</div>
            <div className="mt-1 text-sm text-slate-300">Active node: {activeCode || '-'}</div>
            <div className="mt-1 text-sm text-slate-300">Available qty: {availableTotal.toLocaleString()}</div>
            <div className="mt-1 text-xs text-slate-500 break-all">Path: {activePath || displayProjectUri || '-'}</div>
            <div className="mt-3 flex flex-wrap gap-2">
              {onNavigateTrip && (
                <button type="button" onClick={onNavigateTrip} className={`px-3 py-2 text-sm ${btnBlueCls}`}>Open trip console</button>
              )}
              {onNavigateAudit && (
                <button type="button" onClick={onNavigateAudit} className={`px-3 py-2 text-sm ${btnAmberCls}`}>Open audit</button>
              )}
            </div>
          </div>
        </div>
      </div>
    </>
  )
}
