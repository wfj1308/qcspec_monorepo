type Props = {
  finalPiecePrompt: string
  onCopyFinalPiece: () => void
}

export default function FinalPiecePanel({
  finalPiecePrompt,
  onCopyFinalPiece,
}: Props) {
  return (
    <div className="mt-3 rounded-xl border border-dashed border-slate-700 p-3">
      <div className="mb-1 flex items-center justify-between">
        <div className="text-xs font-extrabold">The Final Piece · 完工态提示</div>
        <button
          type="button"
          onClick={onCopyFinalPiece}
          className="rounded border border-slate-700 bg-slate-900 px-2 py-1 text-[11px] text-slate-200 hover:bg-slate-800"
        >
          复制提示语
        </button>
      </div>
      <div className="whitespace-pre-line text-[11px] text-slate-400">{finalPiecePrompt}</div>
    </div>
  )
}
