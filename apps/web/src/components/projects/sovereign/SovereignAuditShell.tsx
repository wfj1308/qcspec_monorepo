
import SovereignAdvancedOpsPanels from './SovereignAdvancedOpsPanels'
import SovereignAuditDocPreview from './SovereignAuditDocPreview'
import SovereignConsensusAuditPanels from './SovereignConsensusAuditPanels'

type Props = {
  isAuditView: boolean
  panelCls: string
  draftReady: boolean
  auditDocPreviewProps: React.ComponentProps<typeof SovereignAuditDocPreview>
  consensusAuditPanelProps: React.ComponentProps<typeof SovereignConsensusAuditPanels>
  advancedOpsPanelProps: React.ComponentProps<typeof SovereignAdvancedOpsPanels>
}

export default function SovereignAuditShell({
  isAuditView,
  panelCls,
  draftReady,
  auditDocPreviewProps,
  consensusAuditPanelProps,
  advancedOpsPanelProps,
}: Props) {
  if (!isAuditView) return null

  return (
    <div className={`${panelCls} wb-panel min-[980px]:col-span-2 min-[1480px]:col-span-1`}>
      <div className="mb-2 flex items-center justify-between">
        <div className="text-sm font-extrabold">步骤 3：共识见证 · OrdoSign</div>
        <div className="flex items-center gap-2">
          <span className="rounded-full bg-slate-800/90 border border-slate-700 px-2 py-0.5 text-[10px] text-slate-400">共识层</span>
          <span className={`rounded-full border px-2 py-0.5 text-[10px] ${draftReady ? 'border-emerald-500/60 text-emerald-300 bg-emerald-950/30' : 'border-slate-600/60 text-slate-400 bg-slate-950/30'}`}>
            {draftReady ? '实时编译' : '待编译'}
          </span>
        </div>
      </div>
      <SovereignAuditDocPreview {...auditDocPreviewProps} />
      <SovereignConsensusAuditPanels {...consensusAuditPanelProps} />
      <SovereignAdvancedOpsPanels {...advancedOpsPanelProps} />
    </div>
  )
}
