import React, { useMemo, useState } from 'react'
import { useSignPegApi, type ExecutorCertificate, type ExecutorRegisterPayload, type ExecutorSkill } from '../hooks/api/signpeg'

type ExecutorType = 'human' | 'machine' | 'tool' | 'ai' | 'org'
type ToolCategory = 'consumable' | 'reusable' | 'capability'

function hashPlaceholder(seed: string): string {
  let hash = 0
  for (let i = 0; i < seed.length; i += 1) hash = ((hash << 5) - hash) + seed.charCodeAt(i)
  return `sha256:${Math.abs(hash).toString(16).padStart(8, '0')}`
}

export default function ExecutorRegisterPage() {
  const { registerExecutor, loading } = useSignPegApi()
  const [step, setStep] = useState<1 | 2 | 3 | 4 | 5>(1)
  const [executorType, setExecutorType] = useState<ExecutorType>('human')
  const [name, setName] = useState('')
  const [orgUri, setOrgUri] = useState('v://cn.zhongbei/')
  const [capacityMax, setCapacityMax] = useState(10)
  const [capacityUnit, setCapacityUnit] = useState('tasks')
  const [billingUnit, setBillingUnit] = useState('hour')
  const [rate, setRate] = useState(280)
  const [machineCode, setMachineCode] = useState('')
  const [toolCode, setToolCode] = useState('')
  const [aiVersion, setAiVersion] = useState('v1')
  const [toolCategory, setToolCategory] = useState<ToolCategory>('reusable')
  const [requiresText, setRequiresText] = useState('')
  const [businessLicenseNo, setBusinessLicenseNo] = useState('')
  const [businessLicenseFile, setBusinessLicenseFile] = useState('')
  const [branchCount, setBranchCount] = useState(50)
  const [certificates, setCertificates] = useState<ExecutorCertificate[]>([])
  const [skills, setSkills] = useState<ExecutorSkill[]>([])
  const [result, setResult] = useState<any>(null)

  const canContinue = useMemo(() => {
    if (!name.trim()) return false
    if (executorType === 'org') return true
    return Boolean(orgUri.trim())
  }, [name, orgUri, executorType])

  const addCertificate = () => {
    const index = certificates.length + 1
    const certNo = `CERT-${index}`
    setCertificates((prev) => [
      ...prev,
      {
        cert_id: `cert-${index}`,
        cert_type: 'qualification',
        cert_no: certNo,
        issued_by: 'v://cn.registry/',
        issued_date: new Date().toISOString().slice(0, 10),
        valid_until: new Date(Date.now() + 365 * 24 * 3600 * 1000).toISOString().slice(0, 10),
        v_uri: `${(orgUri || 'v://cn.org').replace(/\/$/, '')}/cert/${certNo.toLowerCase()}`,
        status: 'active',
        scan_hash: hashPlaceholder(certNo),
      },
    ])
  }

  const addSkill = () => {
    const index = skills.length + 1
    setSkills((prev) => [
      ...prev,
      {
        skill_uri: `v://normref.com/skill/custom-${index}@v1`,
        skill_name: `skill-${index}`,
        level: 3,
        verified_by: 'v://normref.com/',
        valid_until: new Date(Date.now() + 365 * 24 * 3600 * 1000).toISOString().slice(0, 10),
        proof_uri: `${(orgUri || 'v://cn.org').replace(/\/$/, '')}/proof/skill-${index}`,
        cert_no: '',
        issued_by: '',
      },
    ])
  }

  const buildToolSpec = (): ExecutorRegisterPayload['tool_spec'] => {
    if (executorType !== 'tool') return undefined
    if (toolCategory === 'consumable') {
      return {
        tool_category: 'consumable',
        consumable: {
          sku_uri: `${orgUri.replace(/\/$/, '')}/sku/${(toolCode || name).toLowerCase().replace(/\s+/g, '-')}`,
          initial_qty: 1,
          remaining_qty: 1,
          unit: 'count',
          replenish_threshold: 1,
        },
      }
    }
    if (toolCategory === 'capability') {
      return {
        tool_category: 'capability',
        capability: {
          api_endpoint: 'https://api.anthropic.com',
          model_version: 'claude-sonnet-4-6',
          quota_total: 100000,
          quota_used: 0,
          quota_remaining: 100000,
          cost_per_1k_tokens: 0.003,
        },
      }
    }
    return {
      tool_category: 'reusable',
      reusable: {
        purchase_price: 0,
        expected_life: 200,
        current_uses: 0,
        remaining_uses: 200,
        maintenance_cycle: 50,
        next_maintenance_at: 50,
        depreciation_per_use: 0,
      },
    }
  }

  const submit = async () => {
    if (!canContinue) return
    const requires = requiresText.split('\n').map((item) => item.trim()).filter(Boolean)
    const payload: ExecutorRegisterPayload = {
      name: name.trim(),
      executor_type: executorType,
      org_uri: orgUri.trim(),
      capacity: { maximum: capacityMax, unit: capacityUnit, current: 0 },
      energy: {
        billing_unit: billingUnit,
        rate,
        currency: 'CNY',
        billing_formula: 'trip.units * rate',
        smu_type: executorType === 'tool' ? 'tool' : executorType === 'machine' ? 'equipment' : executorType,
      },
      certificates,
      skills,
      requires,
      tool_spec: buildToolSpec(),
      holder_name: name.trim(),
      holder_id: name.trim().toLowerCase().replace(/\s+/g, '-'),
      machine_code: machineCode.trim(),
      tool_code: toolCode.trim(),
      ai_version: aiVersion.trim(),
    }
    if (executorType === 'org') {
      payload.org_uri = orgUri.trim()
      ;(payload as any).org_spec = {
        org_type: 'designer',
        business_license: businessLicenseNo.trim(),
        qualification_summary: {
          design: 'A',
          survey: 'A',
          supervision: 'A',
          consulting: 'A',
          planning: 'A',
        },
        branch_count: branchCount,
      }
      ;(payload as any).business_license_file = businessLicenseFile.trim()
    }
    const out = await registerExecutor(payload)
    setResult(out)
    setStep(5)
  }

  return (
    <div style={{ padding: 20, maxWidth: 920 }}>
      <h2>Unified ExecutorPeg Register</h2>

      {step === 1 && (
        <section>
          <p>Executor Type</p>
          <label><input type="radio" checked={executorType === 'human'} onChange={() => setExecutorType('human')} /> human</label>
          <label style={{ marginLeft: 12 }}><input type="radio" checked={executorType === 'machine'} onChange={() => setExecutorType('machine')} /> machine</label>
          <label style={{ marginLeft: 12 }}><input type="radio" checked={executorType === 'tool'} onChange={() => setExecutorType('tool')} /> tool</label>
          <label style={{ marginLeft: 12 }}><input type="radio" checked={executorType === 'ai'} onChange={() => setExecutorType('ai')} /> ai</label>
          <label style={{ marginLeft: 12 }}><input type="radio" checked={executorType === 'org'} onChange={() => setExecutorType('org')} /> org</label>
          <p><input placeholder="name" value={name} onChange={(e) => setName(e.target.value)} /></p>
          <p><input placeholder="org uri (for org can be empty)" value={orgUri} onChange={(e) => setOrgUri(e.target.value)} style={{ width: '100%' }} /></p>
          <button onClick={() => setStep(2)} disabled={!canContinue}>next</button>
        </section>
      )}

      {step === 2 && (
        <section>
          <p>max capacity: <input type="number" value={capacityMax} onChange={(e) => setCapacityMax(Number(e.target.value || 0))} /></p>
          <p>capacity unit: <input value={capacityUnit} onChange={(e) => setCapacityUnit(e.target.value)} /></p>
          <p>billing unit: <input value={billingUnit} onChange={(e) => setBillingUnit(e.target.value)} /></p>
          <p>rate: <input type="number" value={rate} onChange={(e) => setRate(Number(e.target.value || 0))} /></p>
          {executorType === 'machine' && (
            <p>machine code: <input value={machineCode} onChange={(e) => setMachineCode(e.target.value)} /></p>
          )}
          {executorType === 'tool' && (
            <>
              <p>tool code: <input value={toolCode} onChange={(e) => setToolCode(e.target.value)} /></p>
              <p>
                tool category:
                <select value={toolCategory} onChange={(e) => setToolCategory(e.target.value as ToolCategory)}>
                  <option value="consumable">consumable</option>
                  <option value="reusable">reusable</option>
                  <option value="capability">capability</option>
                </select>
              </p>
            </>
          )}
          {executorType === 'ai' && (
            <p>ai version: <input value={aiVersion} onChange={(e) => setAiVersion(e.target.value)} /></p>
          )}
          {executorType === 'org' && (
            <>
              <p>business license no: <input value={businessLicenseNo} onChange={(e) => setBusinessLicenseNo(e.target.value)} /></p>
              <p>business license file(raw text/hash): <input value={businessLicenseFile} onChange={(e) => setBusinessLicenseFile(e.target.value)} style={{ width: '100%' }} /></p>
              <p>branch count: <input type="number" value={branchCount} onChange={(e) => setBranchCount(Number(e.target.value || 0))} /></p>
            </>
          )}
          <button onClick={() => setStep(1)}>back</button>
          <button onClick={() => setStep(3)} style={{ marginLeft: 8 }}>next</button>
        </section>
      )}

      {step === 3 && (
        <section>
          <button onClick={addCertificate}>+ certificate</button>
          <button onClick={addSkill} style={{ marginLeft: 8 }}>+ skill</button>
          <ul>{certificates.map((item) => <li key={item.cert_id}>{item.cert_type} / {item.cert_no}</li>)}</ul>
          <ul>{skills.map((item) => <li key={item.skill_uri}>{item.skill_uri}</li>)}</ul>
          <button onClick={() => setStep(2)}>back</button>
          <button onClick={() => setStep(4)} style={{ marginLeft: 8 }}>next</button>
        </section>
      )}

      {step === 4 && (
        <section>
          <p>required tool executors (one uri per line, optional)</p>
          <textarea
            value={requiresText}
            onChange={(e) => setRequiresText(e.target.value)}
            placeholder="v://cn.zhongbei/executor/welder-miller-03"
            rows={5}
            style={{ width: '100%' }}
          />
          <button onClick={() => setStep(3)}>back</button>
          <button onClick={submit} disabled={loading || !canContinue} style={{ marginLeft: 8 }}>register</button>
        </section>
      )}

      {step === 5 && (
        <section>
          <h3>Registered</h3>
          <p>{result?.executor_uri || result?.executor?.executor_uri}</p>
          <p>Registration Proof: {result?.registration_proof || result?.executor?.registration_proof}</p>
          <p>Status: {result?.status || result?.executor?.status}</p>
          <p style={{ color: '#475569', fontSize: 13 }}>Use sidebar "执行体管理" for org member lifecycle operations.</p>
          <button onClick={() => setStep(1)}>register next</button>
        </section>
      )}
    </div>
  )
}

