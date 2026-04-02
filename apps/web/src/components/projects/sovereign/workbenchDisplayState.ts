import {
  buildWorkbenchDisplayTexts,
  WORKBENCH_STYLES,
} from './workbenchConfig'

type BuildSovereignWorkbenchDisplayStateArgs = {
  latestEvidenceNode: Record<string, unknown> | null
  inputProofId: string
  totalHash: string
  arPrimary: Record<string, unknown> | null
  active: Record<string, unknown> | null
  unitRes: Record<string, unknown> | null
}

export function buildSovereignWorkbenchDisplayState({
  latestEvidenceNode,
  inputProofId,
  totalHash,
  arPrimary,
  active,
  unitRes,
}: BuildSovereignWorkbenchDisplayStateArgs) {
  const styles = WORKBENCH_STYLES
  const display = buildWorkbenchDisplayTexts({
    latestEvidenceNode,
    inputProofId,
    totalHash,
    arPrimary,
    active,
    unitRes,
  })
  return {
    ...styles,
    ...display,
  }
}
