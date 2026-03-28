import React from 'react'
import type { SettingsState } from '../../app/appShellShared'
import type { RegisterErpBindingState, RegisterFormState } from './types'

interface RegisterStepOneProps {
  regForm: RegisterFormState
  setRegForm: React.Dispatch<React.SetStateAction<RegisterFormState>>
  projectTypeOptions: Array<{ value: string; label: string }>
  settings: SettingsState
  setErpBinding: React.Dispatch<React.SetStateAction<RegisterErpBindingState>>
  pullErpProjectBinding: () => void
  erpBindingLoading: boolean
  erpBinding: RegisterErpBindingState
  regUri: string
  vpathStatus: 'checking' | 'available' | 'taken' | string
}

export default function RegisterStepOne({
  regForm,
  setRegForm,
  projectTypeOptions,
  settings,
  setErpBinding,
  pullErpProjectBinding,
  erpBindingLoading,
  erpBinding,
  regUri,
  vpathStatus,
}: RegisterStepOneProps) {
  return (
    <div className="form-card">
      <div className="form-card-title">📧 项目基础信息</div>
      <div className="form-grid">
        <div className="form-group">
          <label className="form-label">
            项目名称 <span className="req">*</span>
          </label>
          <input
            className="form-input"
            value={regForm.name}
            onChange={(e) => setRegForm({ ...regForm, name: e.target.value })}
            placeholder="例如：京港高速大修工程（2026）"
          />
        </div>
        <div className="form-group">
          <label className="form-label">
            项目类型 <span className="req">*</span>
          </label>
          <select
            className="form-select"
            value={regForm.type}
            onChange={(e) => setRegForm({ ...regForm, type: e.target.value })}
          >
            {projectTypeOptions.map((option) => (
              <option key={`reg-${option.value}`} value={option.value}>
                {option.label}
              </option>
            ))}
          </select>
        </div>
        <div className="form-group">
          <label className="form-label">
            业主单位 <span className="req">*</span>
          </label>
          <input
            className="form-input"
            value={regForm.owner_unit}
            onChange={(e) => setRegForm({ ...regForm, owner_unit: e.target.value })}
            placeholder="业主单位全称"
          />
        </div>
        <div className="form-group">
          <label className="form-label">施工单位</label>
          <input
            className="form-input"
            value={regForm.contractor}
            onChange={(e) => setRegForm({ ...regForm, contractor: e.target.value })}
            placeholder="施工单位名称"
          />
        </div>
        <div className="form-group">
          <label className="form-label">监理单位</label>
          <input
            className="form-input"
            value={regForm.supervisor}
            onChange={(e) => setRegForm({ ...regForm, supervisor: e.target.value })}
            placeholder="监理单位名称"
          />
        </div>
        <div className="form-group">
          <label className="form-label">合同编号</label>
          <input
            className="form-input"
            value={regForm.contract_no}
            onChange={(e) => setRegForm({ ...regForm, contract_no: e.target.value })}
            placeholder="合同编号"
          />
        </div>
        <div className="form-group">
          <label className="form-label">ERP 项目编码</label>
          <input
            className="form-input"
            value={regForm.erp_project_code}
            onChange={(e) => {
              const value = e.target.value
              setRegForm((prev) => ({ ...prev, erp_project_code: value }))
              if (settings.erpnextSync) {
                setErpBinding({ success: false, code: '', name: '', reason: 'dirty' })
              }
            }}
            placeholder="例如：PROJ-0001"
          />
        </div>
        <div className="form-group">
          <label className="form-label">ERP 项目名称</label>
          <input
            className="form-input"
            value={regForm.erp_project_name}
            onChange={(e) => {
              const value = e.target.value
              setRegForm((prev) => ({ ...prev, erp_project_name: value }))
              if (settings.erpnextSync) {
                setErpBinding({ success: false, code: '', name: '', reason: 'dirty' })
              }
            }}
            placeholder={settings.erpnextSync ? '将由 ERP 拉取后自动回填' : '可选：用于 ERP 精确匹配'}
          />
        </div>
        {settings.erpnextSync && (
          <div className="form-group full">
            <div style={{ display: 'flex', gap: 8, alignItems: 'center', flexWrap: 'wrap' }}>
              <button className="btn-secondary" onClick={pullErpProjectBinding} disabled={erpBindingLoading}>
                {erpBindingLoading ? '拉取中...' : '从 ERP 拉取并绑定'}
              </button>
              <span
                style={{
                  fontSize: 12,
                  color: erpBinding.success ? '#047857' : '#B45309',
                  background: erpBinding.success ? '#ECFDF5' : '#FFFBEB',
                  border: `1px solid ${erpBinding.success ? '#A7F3D0' : '#FCD34D'}`,
                  borderRadius: 999,
                  padding: '4px 10px',
                  fontWeight: 600,
                }}
              >
                {erpBinding.success
                  ? `已绑定：${erpBinding.code} / ${erpBinding.name}`
                  : '未绑定：请先从 ERP 拉取后再进入下一步'}
              </span>
            </div>
          </div>
        )}
        {!settings.erpnextSync && (
          <div className="form-group full">
            <div className="form-hint">ERP 同步未启用，当前注册不做 ERP 强制绑定。</div>
          </div>
        )}
        <div className="form-group">
          <label className="form-label">开工日期</label>
          <input
            className="form-input"
            type="date"
            value={regForm.start_date}
            onChange={(e) => setRegForm({ ...regForm, start_date: e.target.value })}
          />
        </div>
        <div className="form-group">
          <label className="form-label">完工日期</label>
          <input
            className="form-input"
            type="date"
            value={regForm.end_date}
            onChange={(e) => setRegForm({ ...regForm, end_date: e.target.value })}
          />
        </div>
        <div className="form-group full">
          <label className="form-label">项目说明</label>
          <textarea
            className="form-textarea"
            value={regForm.description}
            onChange={(e) => setRegForm({ ...regForm, description: e.target.value })}
            placeholder="项目背景、检测重点等（可选）"
          />
        </div>
      </div>
      <div className="vpath-box" style={{ marginTop: 12 }}>
        <span className="vpath-label">v:// 节点预览</span>
        <span className="vpath-uri">{regUri}</span>
        <span className={vpathStatus === 'taken' ? 'vpath-busy' : vpathStatus === 'available' ? 'vpath-ok' : 'vpath-checking'}>
          {vpathStatus === 'taken' ? '已占用' : vpathStatus === 'available' ? '可用' : '检测中'}
        </span>
      </div>
    </div>
  )
}
