import React from 'react'
import { useSovereignProjectContext } from './SovereignProjectContext'
import { useSovereignView } from './SovereignViewProvider'
import { useUTXOStatus } from './useUTXOStatus'

export default function SovereignStatusBar() {
  const { snapshot } = useSovereignProjectContext()
  const { identity, roleLabel } = useSovereignView()
  const utxoStatus = useUTXOStatus(snapshot)

  return (
    <div className="sticky top-0 z-10 mb-3 rounded-2xl border border-slate-200 bg-white/92 px-4 py-3 shadow-sm backdrop-blur">
      {!snapshot.isOnline && (
        <div className="mb-3 flex flex-wrap items-center justify-between gap-2 rounded-2xl border border-amber-300 bg-amber-50 px-3 py-2 text-xs text-amber-900">
          <span className="font-semibold">离线主权模式</span>
          <span>待同步任务 {snapshot.offlineQueueSize}</span>
        </div>
      )}
      <div className="flex flex-wrap items-start justify-between gap-3">
        <div>
          <div className="text-[11px] font-semibold uppercase tracking-[0.18em] text-slate-500">Sovereign Status</div>
          <div className="mt-1 text-sm font-semibold text-slate-900">{snapshot.activePath || '-'}</div>
          <div className="mt-1 break-all text-xs text-slate-500">{identity.did || 'did:qcspec:anonymous'}</div>
        </div>
        <div className="flex flex-wrap items-center gap-2 text-[11px]">
          <span className="rounded-full border border-slate-300 bg-slate-100 px-2.5 py-1 text-slate-700">{roleLabel}</span>
          <span className="rounded-full border border-slate-300 bg-slate-100 px-2.5 py-1 text-slate-600">DTORole {identity.dtoRole}</span>
          <span className="rounded-full border border-slate-300 bg-slate-100 px-2.5 py-1 text-slate-600">UTXO {utxoStatus}</span>
          <span className="rounded-full border border-slate-300 bg-slate-100 px-2.5 py-1 text-slate-600">Node {snapshot.activeCode || '-'}</span>
          <span className={`rounded-full border px-2.5 py-1 ${snapshot.isOnline ? 'border-emerald-300 bg-emerald-50 text-emerald-700' : 'border-amber-300 bg-amber-50 text-amber-800'}`}>
            {snapshot.isOnline ? '在线' : `离线 ${snapshot.offlineQueueSize}`}
          </span>
          <span className={`rounded-full border px-2.5 py-1 ${snapshot.disputeOpen ? 'border-rose-300 bg-rose-50 text-rose-700' : 'border-slate-300 bg-slate-100 text-slate-600'}`}>
            {snapshot.disputeOpen ? `争议 ${snapshot.disputeProof || '-'}` : '争议清零'}
          </span>
          {snapshot.archiveLocked && (
            <span className="rounded-full border border-sky-300 bg-sky-50 px-2.5 py-1 text-sky-700">Archive Locked</span>
          )}
        </div>
      </div>
    </div>
  )
}
