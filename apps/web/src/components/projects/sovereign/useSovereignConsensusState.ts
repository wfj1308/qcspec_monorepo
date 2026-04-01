import { useMemo } from 'react'

import {
  detectConsensusDeviation,
  parseConsensusValue,
  parseNumericInput,
} from './analysisUtils'
import type { FormRow } from './types'

type Args = {
  summary: {
    design: number
    approved: number
    contract: number
    settled: number
  }
  claimQty: string
  form: Record<string, string>
  effectiveSchema: FormRow[]
  isContractSpu: boolean
  consensus: {
    contractorValue: string
    supervisorValue: string
    ownerValue: string
    allowedDeviation: string
    allowedDeviationPct: string
  }
  identity: {
    executorDid: string
    supervisorDid: string
    ownerDid: string
  }
  context: {
    apiProjectUri: string
    activeUri: string
  }
  helpers: {
    formatNumber: (value: unknown, digits?: number) => string
  }
}

export function useSovereignConsensusState({
  summary,
  claimQty,
  form,
  effectiveSchema,
  isContractSpu,
  consensus,
  identity,
  context,
  helpers,
}: Args) {
  const designTotal = summary.design
  const approvedTotal = summary.approved
  const contractTotal = summary.contract
  const settledTotal = summary.settled
  const effectiveSpent = settledTotal
  const baselineTotal = approvedTotal > 0 ? approvedTotal : (contractTotal > 0 ? contractTotal : designTotal)
  const availableTotal = Math.max(0, baselineTotal - effectiveSpent)

  const claimValue = Number(claimQty)
  const claimQtyValue = Number.isFinite(claimValue) ? claimValue : 0
  const claimQtyProvided = String(claimQty || '').trim() !== ''

  const measuredQtyValue = useMemo(() => {
    const points: number[] = []
    effectiveSchema.forEach((row, idx) => {
      const source = String(row.source_field || row.field || '').trim().toLowerCase()
      if (source !== 'measured_value') return
      const key = String(row.field || `f_${idx}`)
      const raw = String(form[key] || '').replace(/,/g, '').trim()
      if (!raw) return
      const parsed = Number(raw)
      if (Number.isFinite(parsed)) points.push(parsed)
    })
    if (!points.length) return 0
    const avg = points.reduce((sum, value) => sum + value, 0) / points.length
    return Number(avg.toFixed(6))
  }, [effectiveSchema, form])

  const effectiveClaimQtyValue = claimQtyProvided ? claimQtyValue : (!isContractSpu ? measuredQtyValue : 0)

  const consensusBaseValue = useMemo(() => {
    if (effectiveClaimQtyValue > 0) return effectiveClaimQtyValue
    if (measuredQtyValue > 0) return measuredQtyValue
    return 0
  }, [effectiveClaimQtyValue, measuredQtyValue])

  const consensusPreview = useMemo(() => {
    const values = [
      {
        role: 'contractor',
        did: identity.executorDid,
        value: parseConsensusValue(consensus.contractorValue, consensusBaseValue),
        source: parseNumericInput(consensus.contractorValue) == null ? 'default' : 'input',
      },
      {
        role: 'supervisor',
        did: identity.supervisorDid,
        value: parseConsensusValue(consensus.supervisorValue, consensusBaseValue),
        source: parseNumericInput(consensus.supervisorValue) == null ? 'default' : 'input',
      },
      {
        role: 'owner',
        did: identity.ownerDid,
        value: parseConsensusValue(consensus.ownerValue, consensusBaseValue),
        source: parseNumericInput(consensus.ownerValue) == null ? 'default' : 'input',
      },
    ] as const
    const allowedAbs = parseNumericInput(consensus.allowedDeviation)
    const allowedPct = parseNumericInput(consensus.allowedDeviationPct)
    const deviation = detectConsensusDeviation(
      values.map((value) => value.value),
      consensusBaseValue,
      allowedAbs,
      allowedPct,
    )
    return { values, allowedAbs, allowedPct, deviation }
  }, [
    consensus.allowedDeviation,
    consensus.allowedDeviationPct,
    consensus.contractorValue,
    consensus.ownerValue,
    consensus.supervisorValue,
    consensusBaseValue,
    identity.executorDid,
    identity.ownerDid,
    identity.supervisorDid,
  ])

  const consensusDeviation = consensusPreview.deviation
  const consensusConflict = consensusDeviation.conflict
  const consensusBaseValueText = helpers.formatNumber(consensusBaseValue)
  const consensusMinValueText = helpers.formatNumber(consensusDeviation.minValue)
  const consensusMaxValueText = helpers.formatNumber(consensusDeviation.maxValue)
  const consensusDeviationText = helpers.formatNumber(consensusDeviation.deviation)
  const consensusDeviationPercentText = `${consensusDeviation.deviationPercent.toFixed(2)}%`
  const consensusAllowedAbsText = consensusDeviation.allowedDeviation != null ? helpers.formatNumber(consensusDeviation.allowedDeviation) : '-'
  const consensusAllowedPctText = consensusDeviation.allowedDeviationPercent != null
    ? `${consensusDeviation.allowedDeviationPercent.toFixed(2)}%`
    : (consensusDeviation.defaulted ? '默认 0.50%' : '-')

  const consensusConflictSummary = {
    project_uri: context.apiProjectUri,
    boq_item_uri: context.activeUri,
    base_value: consensusBaseValue,
    allowed_deviation: consensusDeviation.allowedDeviation,
    allowed_deviation_percent: consensusDeviation.allowedDeviationPercent ?? (consensusDeviation.defaulted ? 0.5 : null),
    deviation: consensusDeviation.deviation,
    deviation_percent: consensusDeviation.deviationPercent,
    values: consensusPreview.values.map((value) => ({
      role: value.role,
      did: value.did,
      value: value.value,
      source: value.source,
    })),
    conflict: consensusConflict,
  }

  const exceedBalance = effectiveClaimQtyValue > availableTotal + 1e-9
  const exceedRatio = baselineTotal > 0 ? ((effectiveSpent + effectiveClaimQtyValue) - baselineTotal) / baselineTotal : 0
  const exceedPercent = Math.max(0, exceedRatio * 100)
  const deltaSuggest = Math.max(0, (effectiveSpent + effectiveClaimQtyValue) - baselineTotal)
  const exceedTotalText = (effectiveSpent + effectiveClaimQtyValue).toLocaleString()

  return {
    baselineTotal,
    availableTotal,
    effectiveSpent,
    claimQtyProvided,
    measuredQtyValue,
    effectiveClaimQtyValue,
    consensusBaseValue,
    consensusBaseValueText,
    consensusPreview,
    consensusDeviation,
    consensusConflict,
    consensusMinValueText,
    consensusMaxValueText,
    consensusDeviationText,
    consensusDeviationPercentText,
    consensusAllowedAbsText,
    consensusAllowedPctText,
    consensusConflictSummary,
    exceedBalance,
    exceedPercent,
    deltaSuggest,
    exceedTotalText,
  }
}
