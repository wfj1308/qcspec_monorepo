import React, { useMemo, useState } from 'react'
import {
  useSignPegApi,
  type CapabilitySpec,
  type ConsumableSpec,
  type ReusableSpec,
  type ToolCertificate,
  type ToolType,
} from '../hooks/api/signpeg'

function sha256Placeholder(input: string) {
  let hash = 0
  for (let i = 0; i < input.length; i += 1) hash = ((hash << 5) - hash) + input.charCodeAt(i)
  return `sha256:${Math.abs(hash).toString(16).padStart(8, '0')}`
}

export default function ToolRegisterPage() {
  const { registerTool, loading } = useSignPegApi()
  const [step, setStep] = useState<1 | 2 | 3 | 4>(1)
  const [toolType, setToolType] = useState<ToolType>('reusable')
  const [toolName, setToolName] = useState('')
  const [toolCode, setToolCode] = useState('')
  const [ownerUri, setOwnerUri] = useState('v://cn.中北/executor/zhang-driller')
  const [projectUri, setProjectUri] = useState('v://cn.大锦/DJGS')
  const [certificates, setCertificates] = useState<ToolCertificate[]>([])
  const [consumableSpec, setConsumableSpec] = useState<ConsumableSpec>({
    sku_uri: 'v://cn.中北/sku/DRILL-BIT-1500',
    initial_qty: 5,
    remaining_qty: 5,
    unit: '个',
    replenish_threshold: 1,
    unit_price: 45,
  })
  const [reusableSpec, setReusableSpec] = useState<ReusableSpec>({
    purchase_price: 450000,
    expected_life: 200,
    current_uses: 0,
    maintenance_cycle: 50,
    next_maintenance_at: 50,
    depreciation_per_use: 2250,
  })
  const [capabilitySpec, setCapabilitySpec] = useState<CapabilitySpec>({
    api_endpoint: 'api.anthropic.com',
    model_version: 'claude-sonnet-4-6',
    quota_total: 1000000,
    quota_used: 0,
    quota_remaining: 1000000,
    rate_limit: '100/min',
    cost_per_1k_tokens: 0.003,
  })
  const [result, setResult] = useState<any>(null)

  const canSubmit = useMemo(() => !!toolName.trim() && !!toolCode.trim() && !!ownerUri.trim(), [toolName, toolCode, ownerUri])

  const addCertificate = () => {
    const index = certificates.length + 1
    const certNo = `TOOL-CERT-${index}`
    setCertificates((prev) => [
      ...prev,
      {
        cert_type: '检定证书',
        cert_no: certNo,
        issued_by: 'v://cn.市场监督管理局/',
        valid_until: new Date(Date.now() + 365 * 24 * 3600 * 1000).toISOString().slice(0, 10),
        status: 'active',
        scan_hash: sha256Placeholder(certNo),
      },
    ])
  }

  const submit = async () => {
    if (!canSubmit) return
    const payload: any = {
      tool_name: toolName.trim(),
      tool_code: toolCode.trim(),
      tool_type: toolType,
      owner_type: ownerUri.includes('/executor/') ? 'executor' : 'org',
      owner_uri: ownerUri.trim(),
      project_uri: projectUri.trim(),
      certificates,
    }
    if (toolType === 'consumable') payload.consumable_spec = consumableSpec
    if (toolType === 'reusable') payload.reusable_spec = reusableSpec
    if (toolType === 'capability') payload.capability_spec = capabilitySpec
    const out = await registerTool(payload)
    setResult(out)
    setStep(4)
  }

  return (
    <div style={{ padding: 20, maxWidth: 880 }}>
      <h2>工具注册（ToolPeg）</h2>
      {step === 1 && (
        <section>
          <div>
            <label><input type="radio" checked={toolType === 'consumable'} onChange={() => setToolType('consumable')} /> 消耗性</label>
            <label style={{ marginLeft: 12 }}><input type="radio" checked={toolType === 'reusable'} onChange={() => setToolType('reusable')} /> 周转性</label>
            <label style={{ marginLeft: 12 }}><input type="radio" checked={toolType === 'capability'} onChange={() => setToolType('capability')} /> 能力性</label>
          </div>
          <p><input placeholder="工具名称" value={toolName} onChange={(e) => setToolName(e.target.value)} /></p>
          <p><input placeholder="工具编号" value={toolCode} onChange={(e) => setToolCode(e.target.value)} /></p>
          <p><input placeholder="归属URI" value={ownerUri} onChange={(e) => setOwnerUri(e.target.value)} style={{ width: '100%' }} /></p>
          <p><input placeholder="项目URI" value={projectUri} onChange={(e) => setProjectUri(e.target.value)} style={{ width: '100%' }} /></p>
          <button onClick={() => setStep(2)} disabled={!canSubmit}>下一步</button>
        </section>
      )}

      {step === 2 && (
        <section>
          <button onClick={addCertificate}>+ 添加证书</button>
          <ul>
            {certificates.map((item, idx) => <li key={`${item.cert_no}-${idx}`}>{item.cert_type} · {item.cert_no} · {item.valid_until}</li>)}
          </ul>
          <button onClick={() => setStep(1)}>上一步</button>
          <button onClick={() => setStep(3)} style={{ marginLeft: 8 }}>下一步</button>
        </section>
      )}

      {step === 3 && (
        <section>
          {toolType === 'consumable' && (
            <>
              <p>初始数量：<input type="number" value={consumableSpec.initial_qty} onChange={(e) => setConsumableSpec((prev) => ({ ...prev, initial_qty: Number(e.target.value || 0), remaining_qty: Number(e.target.value || 0) }))} /></p>
              <p>单位：<input value={consumableSpec.unit} onChange={(e) => setConsumableSpec((prev) => ({ ...prev, unit: e.target.value }))} /></p>
              <p>预警阈值：<input type="number" value={consumableSpec.replenish_threshold} onChange={(e) => setConsumableSpec((prev) => ({ ...prev, replenish_threshold: Number(e.target.value || 0) }))} /></p>
            </>
          )}
          {toolType === 'reusable' && (
            <>
              <p>购置价格：<input type="number" value={reusableSpec.purchase_price} onChange={(e) => setReusableSpec((prev) => ({ ...prev, purchase_price: Number(e.target.value || 0) }))} /></p>
              <p>设计寿命：<input type="number" value={reusableSpec.expected_life} onChange={(e) => setReusableSpec((prev) => ({ ...prev, expected_life: Number(e.target.value || 0) }))} /></p>
              <p>维保周期：<input type="number" value={reusableSpec.maintenance_cycle} onChange={(e) => setReusableSpec((prev) => ({ ...prev, maintenance_cycle: Number(e.target.value || 0), next_maintenance_at: Number(e.target.value || 0) }))} /></p>
            </>
          )}
          {toolType === 'capability' && (
            <>
              <p>API地址：<input value={capabilitySpec.api_endpoint} onChange={(e) => setCapabilitySpec((prev) => ({ ...prev, api_endpoint: e.target.value }))} /></p>
              <p>模型版本：<input value={capabilitySpec.model_version} onChange={(e) => setCapabilitySpec((prev) => ({ ...prev, model_version: e.target.value }))} /></p>
              <p>总配额：<input type="number" value={capabilitySpec.quota_total} onChange={(e) => setCapabilitySpec((prev) => ({ ...prev, quota_total: Number(e.target.value || 0), quota_remaining: Number(e.target.value || 0) }))} /></p>
            </>
          )}
          <button onClick={() => setStep(2)}>上一步</button>
          <button onClick={submit} disabled={loading || !canSubmit} style={{ marginLeft: 8 }}>注册工具</button>
        </section>
      )}

      {step === 4 && (
        <section>
          <h3>注册成功</h3>
          <p>{result?.tool_uri || result?.tool?.tool_uri}</p>
          <p>Registration Proof: {result?.registration_proof || result?.tool?.registration_proof}</p>
          <p>状态：{result?.status || result?.tool?.status}</p>
          <button onClick={() => setStep(1)}>继续注册</button>
        </section>
      )}
    </div>
  )
}

