export function asDict(value: unknown): Record<string, unknown> {
  return value && typeof value === 'object' && !Array.isArray(value) ? (value as Record<string, unknown>) : {}
}

export function extractApprovedProofId(signRes: Record<string, unknown> | null): string {
  return String(
    asDict(signRes?.trip).output_proof_id ||
    signRes?.output_proof_id ||
    '',
  ).trim()
}

export function hasDocPreview(args: {
  signRes: Record<string, unknown> | null
  mockDocRes: Record<string, unknown> | null
}): boolean {
  const { signRes, mockDocRes } = args
  return Boolean(
    String(asDict(signRes?.docpeg).pdf_preview_b64 || asDict(mockDocRes?.docpeg).pdf_preview_b64 || '').trim(),
  )
}
