import type { ComponentProps, CSSProperties } from 'react'

import EvidenceVault from './EvidenceVault'
import GenesisTree from './GenesisTree'
import SovereignAuditShell from './SovereignAuditShell'
import SovereignEvidenceModals from './SovereignEvidenceModals'
import SovereignGenesisOverview from './SovereignGenesisOverview'
import SovereignOfflineFooter from './SovereignOfflineFooter'
import SovereignTripFlowModals from './SovereignTripFlowModals'
import SovereignWorkbench from './SovereignWorkbench'
import SovereignWorkbenchHero from './SovereignWorkbenchHero'
import SovereignWorkbenchOverlays from './SovereignWorkbenchOverlays'

type Props = {
  shell: {
    isGenesisView: boolean
    isTripView: boolean
    isAuditView: boolean
    frameStyleText: string
    gridOverlayStyle: CSSProperties
  }
  primary: {
    workbenchHeroProps: ComponentProps<typeof SovereignWorkbenchHero>
    genesisOverviewProps: ComponentProps<typeof SovereignGenesisOverview>
    genesisTreeProps: ComponentProps<typeof GenesisTree>
    tripWorkbenchProps: ComponentProps<typeof SovereignWorkbench>
  }
  secondary: {
    auditShellProps: ComponentProps<typeof SovereignAuditShell>
    evidenceVaultProps: ComponentProps<typeof EvidenceVault>
    tripFlowModalProps: ComponentProps<typeof SovereignTripFlowModals>
    evidenceModalProps: ComponentProps<typeof SovereignEvidenceModals>
    workbenchOverlayProps: ComponentProps<typeof SovereignWorkbenchOverlays>
    offlineFooterProps: ComponentProps<typeof SovereignOfflineFooter>
  }
}

export default function SovereignWorkbenchSections({
  shell,
  primary,
  secondary,
}: Props) {
  const {
    isGenesisView,
    isTripView,
    isAuditView,
    frameStyleText,
    gridOverlayStyle,
  } = shell
  const {
    workbenchHeroProps,
    genesisOverviewProps,
    genesisTreeProps,
    tripWorkbenchProps,
  } = primary
  const {
    auditShellProps,
    evidenceVaultProps,
    tripFlowModalProps,
    evidenceModalProps,
    workbenchOverlayProps,
    offlineFooterProps,
  } = secondary

  return (
    <>
      <style>{frameStyleText}</style>
      <div className="relative rounded-2xl border border-slate-800 bg-[radial-gradient(circle_at_top_left,rgba(14,116,144,.18),transparent_28%),radial-gradient(circle_at_top_right,rgba(34,197,94,.08),transparent_22%),linear-gradient(180deg,#020617,#0f172a_62%,#111827)] p-6 text-slate-100 shadow-[inset_0_1px_0_rgba(148,163,184,.08),0_28px_60px_rgba(2,6,23,.55)]">
        <div
          className="pointer-events-none absolute inset-0 rounded-2xl opacity-20"
          style={gridOverlayStyle}
        />
        <SovereignWorkbenchHero {...workbenchHeroProps} />

        <SovereignGenesisOverview {...genesisOverviewProps} />

        <div className={`grid gap-6 ${isGenesisView ? 'grid-cols-1 min-[1260px]:grid-cols-[460px_minmax(0,1fr)]' : 'grid-cols-1'}`}>
          {isGenesisView && (
            <GenesisTree {...genesisTreeProps} />
          )}

          {isTripView && (
            <SovereignWorkbench {...tripWorkbenchProps} />
          )}

          <SovereignAuditShell {...auditShellProps} />
        </div>
      </div>

      {isAuditView && (
        <EvidenceVault {...evidenceVaultProps} />
      )}

      <SovereignTripFlowModals {...tripFlowModalProps} />
      <SovereignEvidenceModals {...evidenceModalProps} />
      <SovereignWorkbenchOverlays {...workbenchOverlayProps} />
      <SovereignOfflineFooter {...offlineFooterProps} />
    </>
  )
}
