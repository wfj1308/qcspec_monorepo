import React from 'react'

type Props = {
  executorDid: string
  supervisorDid: string
  ownerDid: string
  riskScore: number
  totalHash: string
}

export default function DidFloatingCard({
  executorDid,
  supervisorDid,
  ownerDid,
  riskScore,
  totalHash,
}: Props) {
  return (
    <div className="fixed bottom-4 right-4 z-[1050] w-[280px] max-w-[92vw] rounded-xl border border-slate-700/80 bg-slate-950/90 backdrop-blur px-3 py-2.5 shadow-[0_12px_30px_rgba(2,6,23,0.45)]">
      <div className="text-[11px] text-sky-300 font-semibold mb-1">DID Sovereign Card</div>
      <div className="text-[11px] text-slate-200 break-all">施工: {executorDid || '-'}</div>
      <div className="text-[11px] text-slate-400 break-all mt-0.5">监理: {supervisorDid || '-'}</div>
      <div className="text-[11px] text-slate-400 break-all mt-0.5">业主: {ownerDid || '-'}</div>
      <div className="mt-1 text-[10px] text-emerald-300">
        风险分: {Number.isFinite(riskScore) ? riskScore.toFixed(2) : '0.00'} · Hash: {totalHash ? `${totalHash.slice(0, 12)}...` : '-'}
      </div>
    </div>
  )
}

