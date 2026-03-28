import React from 'react'
import type { RegisterFormState } from './types'

interface RegisterStepConfirmProps {
  regForm: RegisterFormState
  typeLabel: Record<string, string>
  segType: string
  regKmInterval: number
  regInspectionTypes: string[]
  inspectionTypeLabel: Record<string, string>
  regUri: string
  zeroLedgerSummary: string
}

export default function RegisterStepConfirm({
  regForm,
  typeLabel,
  segType,
  regKmInterval,
  regInspectionTypes,
  inspectionTypeLabel,
  regUri,
  zeroLedgerSummary,
}: RegisterStepConfirmProps) {
  return (
    <div className="form-card">
      <div className="form-card-title">✅ 确认项目信息</div>
      <div className="reg-info-box green">
        <span className="reg-info-icon">✅</span>
        <div className="reg-info-text">确认后将创建项目主节点并写入初始范围模型。</div>
      </div>
      <div className="reg-info-box gold">
        <span className="reg-info-icon">⚠️</span>
        <div className="reg-info-text">建议再次确认项目名称与业主单位，注册后 URI 作为主键不建议频繁变更。</div>
      </div>
      <div style={{ display: 'grid', gridTemplateColumns: '120px 1fr', rowGap: 8, fontSize: 13 }}>
        <span style={{ color: '#64748B' }}>项目名称</span>
        <strong>{regForm.name || '-'}</strong>
        <span style={{ color: '#64748B' }}>项目类型</span>
        <span>{typeLabel[regForm.type] || regForm.type}</span>
        <span style={{ color: '#64748B' }}>业主单位</span>
        <span>{regForm.owner_unit || '-'}</span>
        <span style={{ color: '#64748B' }}>施工单位</span>
        <span>{regForm.contractor || '-'}</span>
        <span style={{ color: '#64748B' }}>监理单位</span>
        <span>{regForm.supervisor || '-'}</span>
        <span style={{ color: '#64748B' }}>合同编号</span>
        <span>{regForm.contract_no || '-'}</span>
        <span style={{ color: '#64748B' }}>ERP 项目编码</span>
        <span>{regForm.erp_project_code || '-'}</span>
        <span style={{ color: '#64748B' }}>ERP 项目名称</span>
        <span>{regForm.erp_project_name || '-'}</span>
        <span style={{ color: '#64748B' }}>工期</span>
        <span>
          {regForm.start_date || '-'} ~ {regForm.end_date || '-'}
        </span>
        <span style={{ color: '#64748B' }}>分段方式</span>
        <span>{segType === 'km' ? '按桩号' : segType === 'contract' ? '按合同段' : '按构造物'}</span>
        <span style={{ color: '#64748B' }}>分段间隔</span>
        <span>{regKmInterval} km</span>
        <span style={{ color: '#64748B' }}>主要检测类型</span>
        <span>
          {regInspectionTypes.length ? regInspectionTypes.map((key) => inspectionTypeLabel[key]).join(' / ') : '-'}
        </span>
        <span style={{ color: '#64748B' }}>v:// URI</span>
        <code style={{ color: '#1A56DB', wordBreak: 'break-all' }}>{regUri}</code>
        <span style={{ color: '#64748B' }}>零号台帐</span>
        <span style={{ color: '#047857', fontWeight: 700 }}>{zeroLedgerSummary}</span>
      </div>
    </div>
  )
}
