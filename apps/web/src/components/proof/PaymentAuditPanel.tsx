import React, { useMemo, useState } from 'react'
import { Button, Card } from '../ui'

interface PaymentAuditPanelProps {
  projectUri: string
  paymentGenerating: boolean
  paymentResult: any | null
  railpactSubmitting: boolean
  railpactResult: any | null
  auditLoading: boolean
  auditResult: any | null
  frequencyLoading: boolean
  frequencyResult: any | null
  deliveryFinalizing: boolean
  onGeneratePaymentCertificate: (period: string) => void
  onGenerateRailPactInstruction: (paymentId: string) => void
  onOpenAuditTrace: (paymentId: string) => void
  onFinalizeDelivery: () => void
  onOpenVerifyNode?: (proofId: string) => void
}

function defaultPeriodToken(): string {
  const now = new Date()
  const m = String(now.getMonth() + 1).padStart(2, '0')
  return `${now.getFullYear()}-${m}`
}

export default function PaymentAuditPanel({
  projectUri,
  paymentGenerating,
  paymentResult,
  railpactSubmitting,
  railpactResult,
  auditLoading,
  auditResult,
  frequencyLoading,
  frequencyResult,
  deliveryFinalizing,
  onGeneratePaymentCertificate,
  onGenerateRailPactInstruction,
  onOpenAuditTrace,
  onFinalizeDelivery,
  onOpenVerifyNode,
}: PaymentAuditPanelProps) {
  const [period, setPeriod] = useState(defaultPeriodToken())
  const paymentId = String(paymentResult?.payment_id || '')

  const summary = paymentResult?.payment_certificate?.summary || {}
  const chapters = useMemo(() => {
    const rows = paymentResult?.payment_certificate?.chapters
    return Array.isArray(rows) ? rows : []
  }, [paymentResult])
  const lines = useMemo(() => {
    const rows = paymentResult?.payment_certificate?.line_items
    return Array.isArray(rows) ? rows : []
  }, [paymentResult])

  const frequencySummary = frequencyResult?.summary || {}
  const frequencyItems = useMemo(() => {
    const rows = frequencyResult?.items
    return Array.isArray(rows) ? rows : []
  }, [frequencyResult])

  return (
    <Card title="Payment + Audit + Frequency" icon="PAY">
      <div style={{ fontSize: 12, color: '#64748B', marginBottom: 8, wordBreak: 'break-all' }}>
        Project URI: {projectUri}
      </div>

      <div style={{ display: 'flex', gap: 8, alignItems: 'center', marginBottom: 10 }}>
        <input
          value={period}
          onChange={(e) => setPeriod(e.target.value)}
          placeholder="YYYY-MM"
          style={{
            flex: 1,
            padding: '8px 10px',
            border: '1px solid #CBD5E1',
            borderRadius: 8,
            fontSize: 13,
          }}
        />
        <Button
          size="sm"
          onClick={() => onGeneratePaymentCertificate(period)}
          disabled={paymentGenerating || !period}
        >
          {paymentGenerating ? 'Generating...' : 'Generate Payment Certificate'}
        </Button>
        <Button
          size="sm"
          variant="secondary"
          onClick={onFinalizeDelivery}
          disabled={deliveryFinalizing}
        >
          {deliveryFinalizing ? 'Finalizing...' : 'Finalize DocFinal'}
        </Button>
      </div>

      <div style={{ border: '1px solid #E2E8F0', borderRadius: 8, padding: 10, marginBottom: 10 }}>
        <div style={{ fontSize: 12, fontWeight: 700, color: '#0F172A', marginBottom: 6 }}>
          Inspection Frequency Dashboard
        </div>
        {frequencyLoading ? (
          <div style={{ fontSize: 12, color: '#64748B' }}>Loading...</div>
        ) : (
          <>
            <div style={{ fontSize: 12, color: '#475569', display: 'grid', gap: 2 }}>
              <div>Should Check: {Number(frequencySummary.should_check_total || 0).toLocaleString()}</div>
              <div>Already Checked: {Number(frequencySummary.already_check_total || 0).toLocaleString()}</div>
              <div>Missed Check: {Number(frequencySummary.missed_check_total || 0).toLocaleString()}</div>
              <div>Red Items: {Number(frequencySummary.red_items || 0).toLocaleString()}</div>
            </div>
            {!!frequencyItems.length && (
              <div style={{ marginTop: 6, maxHeight: 120, overflowY: 'auto', display: 'grid', gap: 4 }}>
                {frequencyItems.slice(0, 8).map((row: any) => (
                  <div key={String(row.boq_item_uri || row.item_no)} style={{ fontSize: 12, color: '#334155' }}>
                    {row.item_no || '-'} | should {Number(row.expected_tests || 0)} | done {Number(row.dual_pass_done || 0)} | missed {Number(row.missing_dual_pass || 0)}
                  </div>
                ))}
              </div>
            )}
          </>
        )}
      </div>

      {paymentResult && (
        <div style={{ border: '1px solid #E2E8F0', borderRadius: 8, padding: 10, marginBottom: 10 }}>
          <div style={{ fontSize: 12, color: '#0F172A', fontWeight: 700, marginBottom: 6 }}>
            Payment ID: {paymentId || '-'}
          </div>
          <div style={{ fontSize: 12, color: '#475569', display: 'grid', gap: 2 }}>
            <div>Payable Quantity: {Number(summary.payable_quantity_total || 0).toLocaleString()}</div>
            <div>Payable Amount: {Number(summary.payable_amount_total || 0).toLocaleString()}</div>
            <div>Status: {summary.locked ? 'LOCKED' : 'READY'}</div>
            <div>Excluded Items: {Number(summary.excluded_count || 0)}</div>
            <div>Dual-Pass Blocked: {Number(summary.dual_pass_blocked_count || 0)}</div>
          </div>
          {!!paymentId && (
            <div style={{ marginTop: 8, display: 'flex', gap: 8 }}>
              <Button size="sm" variant="secondary" onClick={() => onOpenAuditTrace(paymentId)} disabled={auditLoading}>
                {auditLoading ? 'Tracing...' : 'Open Audit Trace'}
              </Button>
              <Button
                size="sm"
                variant="secondary"
                onClick={() => onGenerateRailPactInstruction(paymentId)}
                disabled={railpactSubmitting}
              >
                {railpactSubmitting ? 'Generating...' : 'Generate RailPact Instruction'}
              </Button>
              {onOpenVerifyNode && (
                <Button size="sm" variant="secondary" onClick={() => onOpenVerifyNode(paymentId)}>
                  Open Verify
                </Button>
              )}
            </div>
          )}
          {!!railpactResult?.instruction_id && (
            <div style={{ marginTop: 6, fontSize: 12, color: '#334155' }}>
              RailPact Instruction: {String(railpactResult.instruction_id || '-')}
            </div>
          )}
        </div>
      )}

      {!!chapters.length && (
        <div style={{ marginBottom: 10 }}>
          <div style={{ fontSize: 12, fontWeight: 700, color: '#0F172A', marginBottom: 6 }}>Chapter Summary</div>
          <div style={{ display: 'grid', gap: 6 }}>
            {chapters.map((row: any) => (
              <div key={`chapter-${row.chapter}`} style={{ border: '1px solid #E2E8F0', borderRadius: 8, padding: 8, fontSize: 12 }}>
                <div style={{ fontWeight: 700, color: '#0F172A' }}>Chapter {row.chapter}</div>
                <div style={{ color: '#475569', marginTop: 2 }}>
                  Items {Number(row.item_count || 0)} | Qty {Number(row.payable_quantity || 0).toLocaleString()} | Amount {Number(row.payable_amount || 0).toLocaleString()}
                </div>
              </div>
            ))}
          </div>
        </div>
      )}

      {!!lines.length && (
        <div style={{ maxHeight: 220, overflowY: 'auto', display: 'grid', gap: 6 }}>
          {lines.slice(0, 30).map((line: any) => {
            const settlementProofId = Array.isArray(line.settlement_proof_ids) && line.settlement_proof_ids.length
              ? String(line.settlement_proof_ids[0] || '')
              : ''
            const excluded = Array.isArray(line.excluded_reasons) && line.excluded_reasons.length > 0
            return (
              <div key={String(line.boq_item_uri || line.item_no)} style={{ border: '1px solid #E2E8F0', borderRadius: 8, padding: 8 }}>
                <div style={{ fontSize: 12, color: '#0F172A', fontWeight: 700 }}>
                  {line.item_no || '-'} {line.item_name || ''}
                </div>
                <div style={{ marginTop: 2, fontSize: 12, color: excluded ? '#B45309' : '#475569' }}>
                  Payable {Number(line.payable_amount || 0).toLocaleString()} | Settled {Number(line.period_settled_quantity || 0).toLocaleString()} {line.unit || ''}
                </div>
                {excluded && (
                  <div style={{ marginTop: 2, fontSize: 12, color: '#B45309' }}>
                    Excluded: {(line.excluded_reasons || []).join(', ')}
                  </div>
                )}
                {!!settlementProofId && onOpenVerifyNode && (
                  <div style={{ marginTop: 4 }}>
                    <button
                      type="button"
                      onClick={() => onOpenVerifyNode(settlementProofId)}
                      style={{
                        border: 'none',
                        padding: 0,
                        background: 'transparent',
                        color: '#1A56DB',
                        fontSize: 12,
                        cursor: 'pointer',
                      }}
                    >
                      Open Settlement Verify
                    </button>
                  </div>
                )}
              </div>
            )
          })}
        </div>
      )}

      {!!auditResult?.nodes?.length && (
        <div style={{ marginTop: 10 }}>
          <div style={{ fontSize: 12, fontWeight: 700, color: '#0F172A', marginBottom: 6 }}>
            Audit Trace Tree
          </div>
          <div style={{ maxHeight: 240, overflowY: 'auto', display: 'grid', gap: 6 }}>
            {(auditResult.nodes as any[]).slice(0, 80).map((node) => (
              <div key={String(node.id)} style={{ border: '1px solid #E2E8F0', borderRadius: 8, padding: 8 }}>
                <div style={{ fontSize: 12, color: '#0F172A', fontWeight: 700 }}>
                  [{node.type || '-'}] {node.label || node.id}
                </div>
                {node.proof_id && (
                  <div style={{ marginTop: 2, fontSize: 12, color: '#1A56DB', wordBreak: 'break-all' }}>
                    {node.proof_id}
                  </div>
                )}
                {!!node.proof_id && onOpenVerifyNode && (
                  <button
                    type="button"
                    onClick={() => onOpenVerifyNode(String(node.proof_id))}
                    style={{
                      marginTop: 4,
                      border: 'none',
                      padding: 0,
                      background: 'transparent',
                      color: '#1A56DB',
                      fontSize: 12,
                      cursor: 'pointer',
                    }}
                  >
                    Open Verify Node
                  </button>
                )}
              </div>
            ))}
          </div>
        </div>
      )}
    </Card>
  )
}
