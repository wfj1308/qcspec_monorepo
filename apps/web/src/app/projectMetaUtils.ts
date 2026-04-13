import type { Project } from '@qcspec/types'
import type { ProjectEditDraft, ProjectRegisterMeta } from './appShellShared'
import {
  normalizeContractSegs,
  normalizeInspectionTypeKeys,
  normalizeKmInterval,
  normalizePermTemplate,
  normalizeSegType,
  normalizeStructures,
  normalizeZeroEquipmentRows,
  normalizeZeroMaterialRows,
  normalizeZeroPersonnelRows,
  normalizeZeroSignStatus,
  normalizeZeroSubcontractRows,
} from './appShellShared'

export const buildDefaultProjectMeta = (memberCount: number): ProjectRegisterMeta => ({
  segType: 'km',
  segStart: 'K0+000',
  segEnd: 'K100+000',
  kmInterval: 20,
  inspectionTypes: ['flatness', 'crack'],
  contractSegs: [],
  structures: [],
  zeroPersonnel: [],
  zeroEquipment: [],
  zeroSubcontracts: [],
  zeroMaterials: [],
  zeroSignStatus: 'pending',
  qcLedgerUnlocked: false,
  permTemplate: 'standard',
  memberCount,
})

export const normalizeProjectMeta = (
  meta: Partial<ProjectRegisterMeta> | null | undefined,
  memberCount: number
): ProjectRegisterMeta => {
  const base = buildDefaultProjectMeta(memberCount)
  if (!meta) return base

  const selectedInspectionTypes = normalizeInspectionTypeKeys(meta.inspectionTypes)
  const normalizedContractSegs = normalizeContractSegs(meta.contractSegs)
  const normalizedStructures = normalizeStructures(meta.structures)
  const normalizedZeroPersonnel = normalizeZeroPersonnelRows(meta.zeroPersonnel)
  const normalizedZeroEquipment = normalizeZeroEquipmentRows(meta.zeroEquipment)
  const normalizedZeroSubcontracts = normalizeZeroSubcontractRows(meta.zeroSubcontracts)
  const normalizedZeroMaterials = normalizeZeroMaterialRows(meta.zeroMaterials)

  return {
    ...base,
    ...meta,
    segType: normalizeSegType(meta.segType ?? base.segType),
    permTemplate: normalizePermTemplate(meta.permTemplate ?? base.permTemplate),
    kmInterval: normalizeKmInterval(meta.kmInterval, base.kmInterval),
    inspectionTypes: selectedInspectionTypes.length > 0 ? selectedInspectionTypes : base.inspectionTypes,
    contractSegs: normalizedContractSegs.length > 0 ? normalizedContractSegs : base.contractSegs,
    structures: normalizedStructures.length > 0 ? normalizedStructures : base.structures,
    zeroPersonnel: normalizedZeroPersonnel.length > 0 ? normalizedZeroPersonnel : base.zeroPersonnel,
    zeroEquipment: normalizedZeroEquipment.length > 0 ? normalizedZeroEquipment : base.zeroEquipment,
    zeroSubcontracts: normalizedZeroSubcontracts.length > 0 ? normalizedZeroSubcontracts : base.zeroSubcontracts,
    zeroMaterials: normalizedZeroMaterials.length > 0 ? normalizedZeroMaterials : base.zeroMaterials,
    zeroSignStatus: normalizeZeroSignStatus(meta.zeroSignStatus),
    qcLedgerUnlocked: Boolean(meta.qcLedgerUnlocked),
    memberCount,
  }
}

export const projectMetaFromRow = (project: Project, memberCount: number): ProjectRegisterMeta | null => {
  const row = project as unknown as Record<string, unknown>
  const hasPersistedMeta =
    typeof row.seg_type === 'string' ||
    typeof row.seg_start === 'string' ||
    typeof row.seg_end === 'string' ||
    typeof row.km_interval !== 'undefined' ||
    Array.isArray(row.inspection_types) ||
    Array.isArray(row.contract_segs) ||
    Array.isArray(row.structures) ||
    Array.isArray(row.zero_personnel) ||
    Array.isArray(row.zero_equipment) ||
    Array.isArray(row.zero_subcontracts) ||
    Array.isArray(row.zero_materials) ||
    typeof row.zero_sign_status === 'string' ||
    typeof row.qc_ledger_unlocked !== 'undefined' ||
    typeof row.perm_template === 'string'

  if (!hasPersistedMeta) return null

  return normalizeProjectMeta(
    {
      segType: normalizeSegType(row.seg_type),
      segStart: String(row.seg_start || 'K0+000'),
      segEnd: String(row.seg_end || 'K100+000'),
      kmInterval: normalizeKmInterval(row.km_interval, 20),
      inspectionTypes: normalizeInspectionTypeKeys(row.inspection_types),
      contractSegs: normalizeContractSegs(row.contract_segs),
      structures: normalizeStructures(row.structures),
      zeroPersonnel: normalizeZeroPersonnelRows(row.zero_personnel),
      zeroEquipment: normalizeZeroEquipmentRows(row.zero_equipment),
      zeroSubcontracts: normalizeZeroSubcontractRows(row.zero_subcontracts),
      zeroMaterials: normalizeZeroMaterialRows(row.zero_materials),
      zeroSignStatus: normalizeZeroSignStatus(row.zero_sign_status),
      qcLedgerUnlocked: Boolean(row.qc_ledger_unlocked),
      permTemplate: normalizePermTemplate(row.perm_template),
      memberCount,
    },
    memberCount
  )
}

export const buildProjectEditDraft = (project: Project): ProjectEditDraft => ({
  name: project.name || '',
  type: project.type || 'highway',
  owner_unit: project.owner_unit || '',
  contractor: project.contractor || '',
  supervisor: project.supervisor || '',
  contract_no: project.contract_no || '',
  start_date: project.start_date || '',
  end_date: project.end_date || '',
  erp_project_code: project.erp_project_code || '',
  erp_project_name: project.erp_project_name || '',
})
