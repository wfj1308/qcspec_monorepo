import React, { createContext, useContext, useMemo } from 'react'
import type { FormRow, GateStats } from './types'
import {
  describeNormRule,
  deriveGateReason,
  evaluateNormValue,
  resolveGateState,
  resolveNormThreshold,
  type ResolveGateArgs,
  type ThresholdResolution,
} from './NormResolver'

type NormStatus = 'pending' | 'success' | 'fail'

type NormEngineValue = {
  gateStats: GateStats
  gateReason: string
  evalNorm: (op: string, threshold: string, value: string) => NormStatus
  resolveThreshold: (op: string, threshold: string) => ThresholdResolution
  resolveGate: (args: ResolveGateArgs) => GateStats
  ruleText: (operator: string, threshold: string, unit: string) => string
}

const NormEngineContext = createContext<NormEngineValue | null>(null)

type ProviderProps = ResolveGateArgs & {
  children: React.ReactNode
}

export function resolveGate(args: ResolveGateArgs) {
  return resolveGateState(args)
}

export { deriveGateReason }

export function NormEngineProvider({ children, schema, form, ctx, isContractSpu }: ProviderProps) {
  const gateStats = useMemo(
    () => resolveGateState({ schema, form, ctx, isContractSpu }),
    [ctx, form, isContractSpu, schema],
  )
  const gateReason = useMemo(() => deriveGateReason(gateStats), [gateStats])
  const value = useMemo<NormEngineValue>(() => ({
    gateStats,
    gateReason,
    evalNorm: evaluateNormValue,
    resolveThreshold: resolveNormThreshold,
    resolveGate: resolveGateState,
    ruleText: describeNormRule,
  }), [gateReason, gateStats])

  return (
    <NormEngineContext.Provider value={value}>
      {children}
    </NormEngineContext.Provider>
  )
}

export function useNormEngine() {
  const ctx = useContext(NormEngineContext)
  if (!ctx) {
    throw new Error('useNormEngine must be used within NormEngineProvider')
  }
  return ctx
}

export type { FormRow, ResolveGateArgs, ThresholdResolution }
