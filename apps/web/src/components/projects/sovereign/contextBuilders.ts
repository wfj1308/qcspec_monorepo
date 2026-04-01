import type { ProjectSovereignContextValue } from './SovereignContext'
import type { SovereignWorkspaceSnapshot } from './SovereignProjectContext'

type BuildWorkspaceSnapshotArgs = {
  activePath: string
  lifecycle: string
  activeCode: string
  activeStatus: string
  totalHash: string
  verifyUri: string
  finalProofReady: boolean
  isOnline: boolean
  offlineQueueSize: number
  disputeOpen: boolean
  disputeProof: string
  archiveLocked: boolean
}

type BuildProjectSovereignValueArgs = {
  project: ProjectSovereignContextValue['project']
  identity: ProjectSovereignContextValue['identity']
  asset: ProjectSovereignContextValue['asset']
  audit: ProjectSovereignContextValue['audit']
}

export function buildWorkspaceSnapshot(args: BuildWorkspaceSnapshotArgs): SovereignWorkspaceSnapshot {
  return {
    activePath: args.activePath,
    lifecycle: args.lifecycle,
    activeCode: args.activeCode,
    activeStatus: args.activeStatus,
    totalHash: args.totalHash,
    verifyUri: args.verifyUri,
    finalProofReady: args.finalProofReady,
    isOnline: args.isOnline,
    offlineQueueSize: args.offlineQueueSize,
    disputeOpen: args.disputeOpen,
    disputeProof: args.disputeProof,
    archiveLocked: args.archiveLocked,
  }
}

export function buildProjectSovereignValue({
  project,
  identity,
  asset,
  audit,
}: BuildProjectSovereignValueArgs): ProjectSovereignContextValue {
  return {
    project,
    identity,
    asset,
    audit,
  }
}
