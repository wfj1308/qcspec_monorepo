export type ConsensusValue = {
  role: 'contractor' | 'supervisor' | 'owner'
  did: string
  value: number
}

function parseNumber(raw: string): number {
  const cleaned = String(raw || '').replace(/,/g, '').trim()
  return Number(cleaned)
}

export function parseConsensusValue(raw: string, fallback: number): number {
  const parsed = parseNumber(raw)
  return Number.isFinite(parsed) ? parsed : fallback
}

export function parseOptionalNumber(raw: string): number | undefined {
  const cleaned = String(raw || '').replace(/,/g, '').trim()
  if (!cleaned) return undefined
  const parsed = Number(cleaned)
  return Number.isFinite(parsed) ? parsed : undefined
}

export function buildConsensusValues(input: {
  executorDid: string
  supervisorDid: string
  ownerDid: string
  consensusContractorValue: string
  consensusSupervisorValue: string
  consensusOwnerValue: string
  fallbackValue: number
}): ConsensusValue[] {
  const {
    executorDid,
    supervisorDid,
    ownerDid,
    consensusContractorValue,
    consensusSupervisorValue,
    consensusOwnerValue,
    fallbackValue,
  } = input

  const values: ConsensusValue[] = [
    { role: 'contractor', did: executorDid, value: parseConsensusValue(consensusContractorValue, fallbackValue) },
    { role: 'supervisor', did: supervisorDid, value: parseConsensusValue(consensusSupervisorValue, fallbackValue) },
    { role: 'owner', did: ownerDid, value: parseConsensusValue(consensusOwnerValue, fallbackValue) },
  ]
  return values.filter((item) => Number.isFinite(item.value))
}

export function buildSignerMetadata(consensusValues: ConsensusValue[], checkedAt: string): Record<string, unknown> {
  return {
    mode: 'liveness',
    checked_at: checkedAt,
    passed: true,
    signers: consensusValues.map((item) => ({
      role: item.role,
      did: item.did,
      biometric_passed: true,
      verified_at: checkedAt,
      measured_value: item.value,
    })),
  }
}
