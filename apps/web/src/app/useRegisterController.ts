import { useEffect, useState } from 'react'
import type {
  InspectionTypeKey,
  ProjectRegisterMeta,
  SegType,
  SettingsState,
  TeamRole,
  ZeroEquipmentRow,
  ZeroLedgerTab,
  ZeroMaterialRow,
  ZeroPersonnelRow,
  ZeroSubcontractRow,
} from './appShellShared'
import type { RegisterErpBindingState, RegisterFormState } from '../components/register/types'

interface ProjectLike {
  id: string
  v_uri: string
  record_count?: number
}

interface UseRegisterControllerArgs<TProject extends ProjectLike> {
  projects: TProject[]
  projectMeta: Record<string, ProjectRegisterMeta>
  settings: SettingsState
  showToast: (message: string) => void
}

export function useRegisterController<TProject extends ProjectLike>({
  projects,
  projectMeta,
  settings,
  showToast,
}: UseRegisterControllerArgs<TProject>) {
  const [registerStep, setRegisterStep] = useState(1)
  const [segType, setSegType] = useState<SegType>('km')
  const [regForm, setRegForm] = useState<RegisterFormState>({
    name: '',
    type: 'highway',
    owner_unit: '',
    erp_project_code: '',
    erp_project_name: '',
    contractor: '',
    supervisor: '',
    contract_no: '',
    start_date: '',
    end_date: '',
    description: '',
    seg_start: 'K0+000',
    seg_end: 'K100+000',
  })
  const [erpBindingLoading, setErpBindingLoading] = useState(false)
  const [erpBinding, setErpBinding] = useState<RegisterErpBindingState>({
    success: false,
    code: '',
    name: '',
    reason: 'pending',
  })
  const [regKmInterval, setRegKmInterval] = useState(20)
  const [registerSuccess, setRegisterSuccess] = useState<{ id: string; name: string; uri: string } | null>(null)
  const [vpathStatus, setVpathStatus] = useState<'checking' | 'available' | 'taken'>('checking')
  const [regInspectionTypes, setRegInspectionTypes] = useState<InspectionTypeKey[]>(['flatness', 'crack'])
  const [contractSegs, setContractSegs] = useState([{ name: '一标段', range: 'K0~K30' }])
  const [structures, setStructures] = useState([{ kind: '桥梁', name: '沁河大桥', code: 'QH-B01' }])
  const [zeroLedgerTab, setZeroLedgerTab] = useState<ZeroLedgerTab>('personnel')
  const [zeroPersonnel, setZeroPersonnel] = useState<ZeroPersonnelRow[]>([
    { id: 'zp-1', name: '石玉山', title: '项目负责人', dtoRole: 'OWNER', certificate: '一级建造师' },
    { id: 'zp-2', name: '王质检', title: '质检员', dtoRole: 'AI', certificate: '质检员证' },
  ])
  const [zeroEquipment, setZeroEquipment] = useState<ZeroEquipmentRow[]>([
    { id: 'ze-1', name: '灌砂筒', modelNo: 'BZY-001', inspectionItem: '压实度', validUntil: '2027-03-01' },
    { id: 'ze-2', name: '弯沉仪', modelNo: 'BZY-002', inspectionItem: '弯沉值', validUntil: '2026-12-31' },
  ])
  const [zeroSubcontracts, setZeroSubcontracts] = useState<ZeroSubcontractRow[]>([
    { id: 'zs-1', unitName: '', content: '路面施工', range: '' },
  ])
  const [zeroMaterials, setZeroMaterials] = useState<ZeroMaterialRow[]>([
    { id: 'zm-1', name: '沥青混合料', spec: 'AC-13C', supplier: '', freq: '每批次检测' },
  ])

  const parseKm = (s: string) => {
    const m = (s || '').match(/K?(\d+)\+?(\d{1,3})?/)
    if (!m) return Number.NaN
    return Number(m[1]) + Number((m[2] || '0').padStart(3, '0')) / 1000
  }

  const formatKmCompact = (v: number) => {
    const k = Math.floor(v)
    const m = Math.round((v - k) * 1000)
    if (m === 0) return `K${k}`
    return `K${k}+${String(m).padStart(3, '0')}`
  }

  const makeRowId = (prefix: string) => `${prefix}-${Date.now().toString(36)}-${Math.random().toString(36).slice(2, 7)}`
  const normalizeNodeSegment = (value: string, fallback = '（待填）') => {
    const cleaned = String(value || '').trim().replace(/[\\/]/g, '-').replace(/\s+/g, '')
    return cleaned || fallback
  }
  const normalizeCodeSegment = (value: string) => String(value || '').trim().replace(/[^\w\u4e00-\u9fa5-]/g, '').replace(/\s+/g, '')
  const buildExecutorUri = (name: string) => `v://cn.zhongbei/executor/${normalizeNodeSegment(name)}/`
  const buildToolNodeName = (name: string, modelNo: string) => {
    const safeName = normalizeNodeSegment(name, '待填仪器')
    const safeModel = normalizeCodeSegment(modelNo)
    return safeModel ? `${safeName}-${safeModel}` : safeName
  }
  const buildToolUri = (name: string, modelNo: string) => `v://cn.zhongbei/tools/${buildToolNodeName(name, modelNo)}/`
  const buildSubcontractUri = (unitName: string) => `v://cn.zhongbei/subcontract/${normalizeNodeSegment(unitName, '待填分包')}/`
  const getEquipmentValidity = (validUntil: string) => {
    if (!validUntil) {
      return { label: '待填', color: '#64748B', bg: '#F1F5F9', ok: false }
    }
    const now = new Date()
    const target = new Date(`${validUntil}T23:59:59`)
    const days = Math.floor((target.getTime() - now.getTime()) / 86400000)
    if (days < 0) {
      return { label: '❌ 已过期', color: '#DC2626', bg: '#FEE2E2', ok: false }
    }
    if (days < 90) {
      return { label: `⚠️ ${days}天`, color: '#D97706', bg: '#FEF3C7', ok: false }
    }
    return { label: '✓ 有效', color: '#059669', bg: '#DCFCE7', ok: true }
  }

  const regUri = `v://cn.zhongbei/${regForm.type}/${(regForm.name || 'project').replace(/\s+/g, '').slice(0, 20).toLowerCase()}/`
  const regRangeTreeLines = (() => {
    if (segType === 'km') {
      const s = parseKm(regForm.seg_start)
      const e = parseKm(regForm.seg_end)
      if (Number.isNaN(s) || Number.isNaN(e) || e <= s) return []
      const lines: string[] = []
      for (let cur = s; cur < e; cur += regKmInterval) {
        lines.push(`${formatKmCompact(cur)}~${formatKmCompact(Math.min(cur + regKmInterval, e))}/`)
        if (lines.length >= 12) {
          lines.push('...(更多分段)')
          break
        }
      }
      return lines
    }
    if (segType === 'contract') {
      return contractSegs
        .filter((seg) => seg.name.trim() || seg.range.trim())
        .map((seg, idx) => `${seg.name || `标段${idx + 1}`}${seg.range ? ` (${seg.range})` : ''}/`)
    }
    return structures
      .filter((st) => st.kind.trim() || st.name.trim() || st.code.trim())
      .map((st, idx) => `${st.kind || '构造物'}/${st.name || `节点${idx + 1}`}${st.code ? ` (${st.code})` : ''}/`)
  })()
  const zeroPersonnelCount = zeroPersonnel.filter((row) => row.name.trim()).length
  const zeroEquipmentCount = zeroEquipment.filter((row) => row.name.trim()).length
  const zeroLedgerSummary = `${zeroPersonnelCount}名人员 · ${zeroEquipmentCount}台仪器 · 等待秩签审批`
  const zeroLedgerTreeRows = (() => {
    const rows: Array<{ text: string; color?: string }> = []
    zeroPersonnel
      .filter((row) => row.name.trim())
      .forEach((row) => rows.push({ text: `executor/${normalizeNodeSegment(row.name)}/ [${row.dtoRole}]`, color: '#34D399' }))
    zeroEquipment
      .filter((row) => row.name.trim())
      .forEach((row) => {
        const validity = getEquipmentValidity(row.validUntil)
        rows.push({ text: `tools/${buildToolNodeName(row.name, row.modelNo)}/ ${validity.label}`, color: validity.ok ? '#A78BFA' : validity.color })
      })
    zeroSubcontracts
      .filter((row) => row.unitName.trim())
      .forEach((row) => rows.push({ text: `subcontract/${normalizeNodeSegment(row.unitName)}/ 自动生成`, color: '#60A5FA' }))
    zeroMaterials
      .filter((row) => row.name.trim())
      .forEach((row) => rows.push({ text: `materials/${normalizeNodeSegment(row.name)}${row.spec ? `-${normalizeCodeSegment(row.spec)}` : ''}/`, color: '#F59E0B' }))
    return rows
  })()
  const registerSegCount = projects.reduce((sum, project) => {
    const meta = projectMeta[project.id]
    if (!meta) return sum + 1
    if (meta.segType === 'contract') return sum + Math.max(1, meta.contractSegs.length)
    if (meta.segType === 'structure') return sum + Math.max(1, meta.structures.length)
    const s = parseKm(meta.segStart)
    const e = parseKm(meta.segEnd)
    if (Number.isNaN(s) || Number.isNaN(e) || e <= s) return sum + 1
    return sum + Math.max(1, Math.ceil((e - s) / 20))
  }, 0)
  const registerRecordCount = projects.reduce((sum, project) => sum + Number(project.record_count || 0), 0)
  const registerPreviewProjects = projects.slice(0, 5)

  const toggleInspectionType = (
    key: InspectionTypeKey,
    selected: InspectionTypeKey[],
    setter: (next: InspectionTypeKey[]) => void
  ) => {
    if (selected.includes(key)) {
      setter(selected.filter((x) => x !== key))
      return
    }
    setter([...selected, key])
  }

  const nextRegStep = () => {
    if (registerStep === 1 && (!regForm.name || !regForm.owner_unit || !regForm.type)) {
      showToast('请先完成项目基本信息')
      return
    }
    if (
      registerStep === 1 &&
      settings.erpnextSync &&
      (!erpBinding.success
        || erpBinding.code !== String(regForm.erp_project_code || '').trim()
        || erpBinding.name !== String(regForm.erp_project_name || '').trim())
    ) {
      showToast('ERP 同步已启用，请先点击“从 ERP 拉取并绑定”')
      return
    }
    if (registerStep === 2 && regInspectionTypes.length === 0) {
      showToast('请至少选择一个检测类型')
      return
    }
    if (registerStep === 3 && zeroPersonnelCount === 0 && zeroEquipmentCount === 0) {
      showToast('请至少填写零号台帐中的人员或设备')
      return
    }
    setRegisterStep((s) => Math.min(4, s + 1))
  }

  const prevRegStep = () => setRegisterStep((s) => Math.max(1, s - 1))
  const addContractSeg = () => setContractSegs((prev) => [...prev, { name: `新标段${prev.length + 1}`, range: '' }])
  const addStructure = () => setStructures((prev) => [...prev, { kind: '桥梁', name: '', code: '' }])
  const resetRegister = () => {
    setRegisterStep(1)
    setRegForm({
      name: '',
      type: 'highway',
      owner_unit: '',
      erp_project_code: '',
      erp_project_name: '',
      contractor: '',
      supervisor: '',
      contract_no: '',
      start_date: '',
      end_date: '',
      description: '',
      seg_start: 'K0+000',
      seg_end: 'K100+000',
    })
    setErpBinding({
      success: false,
      code: '',
      name: '',
      reason: 'pending',
    })
    setSegType('km')
    setRegKmInterval(20)
    setRegInspectionTypes(['flatness', 'crack'])
    setContractSegs([{ name: '一标段', range: 'K0~K30' }])
    setStructures([{ kind: '桥梁', name: '沁河大桥', code: 'QH-B01' }])
    setZeroLedgerTab('personnel')
    setZeroPersonnel([
      { id: 'zp-1', name: '石玉山', title: '项目负责人', dtoRole: 'OWNER', certificate: '一级建造师' },
      { id: 'zp-2', name: '王质检', title: '质检员', dtoRole: 'AI', certificate: '质检员证' },
    ])
    setZeroEquipment([
      { id: 'ze-1', name: '灌砂筒', modelNo: 'BZY-001', inspectionItem: '压实度', validUntil: '2027-03-01' },
      { id: 'ze-2', name: '弯沉仪', modelNo: 'BZY-002', inspectionItem: '弯沉值', validUntil: '2026-12-31' },
    ])
    setZeroSubcontracts([{ id: 'zs-1', unitName: '', content: '路面施工', range: '' }])
    setZeroMaterials([{ id: 'zm-1', name: '沥青混合料', spec: 'AC-13C', supplier: '', freq: '每批次检测' }])
    setRegisterSuccess(null)
  }

  useEffect(() => {
    if (registerSuccess) {
      setVpathStatus('available')
      return
    }
    if (!regForm.name.trim() || !regForm.type) {
      setVpathStatus('checking')
      return
    }
    setVpathStatus('checking')
    const timer = setTimeout(() => {
      const taken = projects.some((p) => p.v_uri === regUri)
      setVpathStatus(taken ? 'taken' : 'available')
    }, 420)
    return () => clearTimeout(timer)
  }, [projects, regForm.name, regForm.type, regUri, registerSuccess])

  return {
    registerStep,
    setRegisterStep,
    segType,
    setSegType,
    regForm,
    setRegForm,
    erpBindingLoading,
    setErpBindingLoading,
    erpBinding,
    setErpBinding,
    regKmInterval,
    setRegKmInterval,
    registerSuccess,
    setRegisterSuccess,
    vpathStatus,
    setVpathStatus,
    regInspectionTypes,
    setRegInspectionTypes,
    contractSegs,
    setContractSegs,
    structures,
    setStructures,
    zeroLedgerTab,
    setZeroLedgerTab,
    zeroPersonnel,
    setZeroPersonnel,
    zeroEquipment,
    setZeroEquipment,
    zeroSubcontracts,
    setZeroSubcontracts,
    zeroMaterials,
    setZeroMaterials,
    regUri,
    makeRowId,
    buildExecutorUri,
    buildToolUri,
    buildSubcontractUri,
    getEquipmentValidity,
    regRangeTreeLines,
    zeroPersonnelCount,
    zeroEquipmentCount,
    zeroLedgerSummary,
    zeroLedgerTreeRows,
    registerSegCount,
    registerRecordCount,
    registerPreviewProjects,
    toggleInspectionType,
    nextRegStep,
    prevRegStep,
    addContractSeg,
    addStructure,
    resetRegister,
  }
}
