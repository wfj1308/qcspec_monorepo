import React from 'react'
import type { MobileRole, MobileWorkorder } from '../types/mobile'

type WorkorderPageProps = {
  role: MobileRole
  workorder: MobileWorkorder
  qrCodeImage: string
  qrCodeLoading: boolean
  onBack: () => void
  onStartForm: () => void
  onLoadQrCode: () => Promise<void>
  onQuickSwitchRole: (role: MobileRole) => void
}

function stepIcon(status: string) {
  if (status === 'done') return '✓'
  if (status === 'current') return '→'
  return ''
}

export default function WorkorderPage({
  role,
  workorder,
  qrCodeImage,
  qrCodeLoading,
  onBack,
  onStartForm,
  onLoadQrCode,
  onQuickSwitchRole,
}: WorkorderPageProps) {
  const currentStep =
    workorder.steps.find((step) => step.status === 'current') ||
    workorder.steps.find((step) => step.status === 'todo') ||
    workorder.steps[0]
  const doneSteps = workorder.steps.filter((step) => step.status === 'done')
  const roleSteps = workorder.steps.filter((step) => step.requiredRole === role)
  const roleTodoSteps = roleSteps.filter((step) => step.status !== 'done')
  const canStart = !!currentStep && currentStep.requiredRole === role

  return (
    <section className="mobile-page">
      <div className="mobile-card mobile-header">
        <button className="mobile-icon-btn" onClick={onBack}>
          ← 返回
        </button>
        <h1>QCSpec</h1>
        <div />
      </div>

      <div className="mobile-card">
        <h2 className="mobile-code">{workorder.code}</h2>
        <p className="mobile-muted">{workorder.name}</p>
        <div className="mobile-row" style={{ marginTop: 8 }}>
          <button className="mobile-btn ghost full" disabled={qrCodeLoading} onClick={() => void onLoadQrCode()}>
            {qrCodeLoading ? '二维码加载中...' : '查看二维码'}
          </button>
        </div>
        {qrCodeImage ? (
          <div className="mobile-qr-wrap">
            <img src={qrCodeImage} alt="构件二维码" className="mobile-qr-image" />
            <div className="mobile-muted">请现场扫码使用</div>
          </div>
        ) : null}
      </div>

      <div className="mobile-card">
        <p className="mobile-title">工序进度</p>
        <div className="mobile-progress">
          {workorder.steps.map((step) => (
            <div key={step.key} className={`mobile-progress-step ${step.status === 'done' ? 'is-done' : step.status === 'current' ? 'is-current' : ''}`}>
              <div className="dot">{stepIcon(step.status)}</div>
              <div>{step.name}</div>
            </div>
          ))}
        </div>
      </div>

      <div className="mobile-card">
        <p className="mobile-title">我的可操作工序</p>
        <div className="mobile-list">
          {roleTodoSteps.length ? (
            roleTodoSteps.map((step) => (
              <div key={step.key} className="mobile-list-item">
                <div>
                  <strong>{step.name}</strong>
                  <div className="mobile-muted">{step.formName || '检查表'}</div>
                </div>
                <span className={`mobile-badge ${step.status === 'current' ? 'success' : 'neutral'}`}>
                  {step.status === 'current' ? '当前处理' : '待处理'}
                </span>
              </div>
            ))
          ) : (
            <p className="mobile-muted">当前角色没有待处理工序</p>
          )}
        </div>
        <p className="mobile-muted" style={{ marginTop: 6 }}>
          其他角色工序已收起，仅显示与你相关的工序。
        </p>
      </div>

      <div className="mobile-card">
        <p className="mobile-title">当前应处理</p>
        <div className="mobile-summary-line">
          <strong>{currentStep?.name || '无'}</strong>
          <span>{currentStep?.formName || ''}</span>
        </div>
        <div className="mobile-summary-line">
          <span>要求角色</span>
          <span>{currentStep?.requiredRole || '-'}</span>
        </div>
        <div className="mobile-summary-line">
          <span>我的角色</span>
          <span>{role}</span>
        </div>
        <button className="mobile-btn primary full" disabled={!canStart} onClick={onStartForm}>
          {canStart ? '开始填写' : `等待${currentStep?.requiredRole || '指定角色'}处理`}
        </button>
        {!canStart && currentStep?.requiredRole ? (
          <button
            className="mobile-btn ghost full"
            style={{ marginTop: 8 }}
            onClick={() => onQuickSwitchRole(currentStep.requiredRole)}
          >
            切换为{currentStep.requiredRole}
          </button>
        ) : null}
      </div>

      <div className="mobile-card">
        <p className="mobile-title">已完成工序</p>
        <div className="mobile-list">
          {doneSteps.length ? (
            doneSteps.map((step) => (
              <div key={step.key} className="mobile-list-item">
                <div>
                  <div>
                    <strong>✓ {step.name}</strong> {step.doneAt || ''}
                  </div>
                  <div className="mobile-muted">
                    {step.doneBy || '-'} | {step.proofId || '-'}
                  </div>
                </div>
              </div>
            ))
          ) : (
            <p className="mobile-muted">暂无已完成工序</p>
          )}
        </div>
      </div>
    </section>
  )
}

