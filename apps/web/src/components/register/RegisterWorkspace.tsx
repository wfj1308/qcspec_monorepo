import React from 'react'
import type {
  InspectionTypeKey,
  SegType,
  SettingsState,
  ZeroEquipmentRow,
  ZeroLedgerTab,
  ZeroMaterialRow,
  ZeroPersonnelRow,
  ZeroSubcontractRow,
} from '../../app/appShellShared'
import type { RegisterErpBindingState, RegisterFormState } from './types'
import RegisterPanelFrame from './RegisterPanelFrame'
import RegisterStepOne from './RegisterStepOne'
import RegisterStepTwo from './RegisterStepTwo'
import RegisterStepThree from './RegisterStepThree'
import RegisterStepConfirm from './RegisterStepConfirm'

interface RegisterWorkspaceProps {
  projects: any[]
  registerSegCount: number
  registerRecordCount: number
  registerStep: number
  setRegisterStep: (step: number) => void
  registerSuccess: { id: string; name: string; uri: string } | null
  registerPreviewProjects: any[]
  projectTypeOptions: Array<{ value: string; label: string }>
  typeIcon: Record<string, string>
  typeLabel: Record<string, string>
  onStartInspectionFromSuccess: () => void
  onGoProjects: () => void
  onResetRegister: () => void
  onOpenProjectDetail: (projectId: string) => void
  onEnterInspection: (project: any) => void
  regForm: RegisterFormState
  setRegForm: React.Dispatch<React.SetStateAction<RegisterFormState>>
  settings: SettingsState
  setErpBinding: React.Dispatch<React.SetStateAction<RegisterErpBindingState>>
  pullErpProjectBinding: () => void
  erpBindingLoading: boolean
  erpBinding: RegisterErpBindingState
  regUri: string
  vpathStatus: 'checking' | 'available' | 'taken' | string
  segType: SegType
  setSegType: (value: SegType) => void
  regKmInterval: number
  setRegKmInterval: (value: number) => void
  contractSegs: Array<{ name: string; range: string }>
  setContractSegs: React.Dispatch<React.SetStateAction<Array<{ name: string; range: string }>>>
  addContractSeg: () => void
  structures: Array<{ kind: string; name: string; code: string }>
  setStructures: React.Dispatch<React.SetStateAction<Array<{ kind: string; name: string; code: string }>>>
  addStructure: () => void
  inspectionTypeOptions: Array<{ key: InspectionTypeKey; label: string }>
  regInspectionTypes: InspectionTypeKey[]
  setRegInspectionTypes: React.Dispatch<React.SetStateAction<InspectionTypeKey[]>>
  toggleInspectionType: (
    key: InspectionTypeKey,
    current: InspectionTypeKey[],
    setter: React.Dispatch<React.SetStateAction<InspectionTypeKey[]>>
  ) => void
  regRangeTreeLines: string[]
  zeroLedgerTab: ZeroLedgerTab
  setZeroLedgerTab: (tab: ZeroLedgerTab) => void
  zeroPersonnel: ZeroPersonnelRow[]
  setZeroPersonnel: React.Dispatch<React.SetStateAction<ZeroPersonnelRow[]>>
  zeroEquipment: ZeroEquipmentRow[]
  setZeroEquipment: React.Dispatch<React.SetStateAction<ZeroEquipmentRow[]>>
  zeroSubcontracts: ZeroSubcontractRow[]
  setZeroSubcontracts: React.Dispatch<React.SetStateAction<ZeroSubcontractRow[]>>
  zeroMaterials: ZeroMaterialRow[]
  setZeroMaterials: React.Dispatch<React.SetStateAction<ZeroMaterialRow[]>>
  makeRowId: (prefix: string) => string
  buildExecutorUri: (name: string) => string
  buildToolUri: (name: string, modelNo: string) => string
  buildSubcontractUri: (unitName: string) => string
  getEquipmentValidity: (validUntil: string) => { label: string; color: string; bg: string }
  zeroLedgerTreeRows: Array<{ text: string; color?: string }>
  zeroLedgerSummary: string
  prevRegStep: () => void
  nextRegStep: () => void
  submitRegister: () => void
  inspectionTypeLabel: Record<string, string>
}

export default function RegisterWorkspace({
  projects,
  registerSegCount,
  registerRecordCount,
  registerStep,
  setRegisterStep,
  registerSuccess,
  registerPreviewProjects,
  projectTypeOptions,
  typeIcon,
  typeLabel,
  onStartInspectionFromSuccess,
  onGoProjects,
  onResetRegister,
  onOpenProjectDetail,
  onEnterInspection,
  regForm,
  setRegForm,
  settings,
  setErpBinding,
  pullErpProjectBinding,
  erpBindingLoading,
  erpBinding,
  regUri,
  vpathStatus,
  segType,
  setSegType,
  regKmInterval,
  setRegKmInterval,
  contractSegs,
  setContractSegs,
  addContractSeg,
  structures,
  setStructures,
  addStructure,
  inspectionTypeOptions,
  regInspectionTypes,
  setRegInspectionTypes,
  toggleInspectionType,
  regRangeTreeLines,
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
  makeRowId,
  buildExecutorUri,
  buildToolUri,
  buildSubcontractUri,
  getEquipmentValidity,
  zeroLedgerTreeRows,
  zeroLedgerSummary,
  prevRegStep,
  nextRegStep,
  submitRegister,
  inspectionTypeLabel,
}: RegisterWorkspaceProps) {
  return (
    <RegisterPanelFrame
      projects={projects}
      registerSegCount={registerSegCount}
      registerRecordCount={registerRecordCount}
      registerStep={registerStep}
      registerSuccess={registerSuccess}
      registerPreviewProjects={registerPreviewProjects}
      typeIcon={typeIcon}
      typeLabel={typeLabel}
      onStepClick={setRegisterStep}
      onStartInspectionFromSuccess={onStartInspectionFromSuccess}
      onGoProjects={onGoProjects}
      onResetRegister={onResetRegister}
      onOpenProjectDetail={onOpenProjectDetail}
      onEnterInspection={onEnterInspection}
    >
      <>
        {registerStep === 1 && (
          <RegisterStepOne
            regForm={regForm}
            setRegForm={setRegForm}
            projectTypeOptions={projectTypeOptions}
            settings={settings}
            setErpBinding={setErpBinding}
            pullErpProjectBinding={pullErpProjectBinding}
            erpBindingLoading={erpBindingLoading}
            erpBinding={erpBinding}
            regUri={regUri}
            vpathStatus={vpathStatus}
          />
        )}

        {registerStep === 2 && (
          <RegisterStepTwo
            regForm={regForm}
            setRegForm={setRegForm}
            segType={segType}
            setSegType={setSegType}
            regKmInterval={regKmInterval}
            setRegKmInterval={setRegKmInterval}
            contractSegs={contractSegs}
            setContractSegs={setContractSegs}
            addContractSeg={addContractSeg}
            structures={structures}
            setStructures={setStructures}
            addStructure={addStructure}
            inspectionTypeOptions={inspectionTypeOptions}
            regInspectionTypes={regInspectionTypes}
            setRegInspectionTypes={setRegInspectionTypes}
            toggleInspectionType={toggleInspectionType}
            regUri={regUri}
            vpathStatus={vpathStatus}
            regRangeTreeLines={regRangeTreeLines}
          />
        )}

        {registerStep === 3 && (
          <RegisterStepThree
            zeroLedgerTab={zeroLedgerTab}
            setZeroLedgerTab={setZeroLedgerTab}
            zeroPersonnel={zeroPersonnel}
            setZeroPersonnel={setZeroPersonnel}
            zeroEquipment={zeroEquipment}
            setZeroEquipment={setZeroEquipment}
            zeroSubcontracts={zeroSubcontracts}
            setZeroSubcontracts={setZeroSubcontracts}
            zeroMaterials={zeroMaterials}
            setZeroMaterials={setZeroMaterials}
            makeRowId={makeRowId}
            buildExecutorUri={buildExecutorUri}
            buildToolUri={buildToolUri}
            buildSubcontractUri={buildSubcontractUri}
            getEquipmentValidity={getEquipmentValidity}
            regUri={regUri}
            zeroLedgerTreeRows={zeroLedgerTreeRows}
          />
        )}

        {registerStep === 4 && (
          <RegisterStepConfirm
            regForm={regForm}
            typeLabel={typeLabel}
            segType={segType}
            regKmInterval={regKmInterval}
            regInspectionTypes={regInspectionTypes}
            inspectionTypeLabel={inspectionTypeLabel}
            regUri={regUri}
            zeroLedgerSummary={zeroLedgerSummary}
          />
        )}

        <div className="btn-row">
          <button className="btn-secondary" onClick={prevRegStep} disabled={registerStep === 1}>上一步</button>
          {registerStep < 4 ? (
            <button className="btn-primary" onClick={nextRegStep}>下一步</button>
          ) : (
            <button className="btn-primary btn-green" onClick={submitRegister}>确认注册</button>
          )}
        </div>
      </>
    </RegisterPanelFrame>
  )
}
