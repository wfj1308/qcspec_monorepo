import React from 'react'
import type { FieldValidation, MobileFormSpec } from '../types/mobile'
import type { MobileRole } from '../types/mobile'

type FormPageProps = {
  title: string
  stepIndex: number
  stepTotal: number
  componentCode: string
  componentName: string
  requiredRole: MobileRole
  role: MobileRole
  spec: MobileFormSpec
  values: Record<string, string>
  checks: Record<string, FieldValidation>
  result: '合格' | '不合格'
  remoteGateHint: string
  photos: Array<{ preview: string; hash: string }>
  onBack: () => void
  onBaseChange: (key: string, value: string) => void
  onFieldChange: (key: string, value: string) => void
  onResultChange: (value: '合格' | '不合格') => void
  onRemarkChange: (value: string) => void
  onTakePhoto: () => Promise<void>
  onNextSign: () => void
}

export default function FormPage({
  title,
  stepIndex,
  stepTotal,
  componentCode,
  componentName,
  requiredRole,
  role,
  spec,
  values,
  checks,
  result,
  remoteGateHint,
  photos,
  onBack,
  onBaseChange,
  onFieldChange,
  onResultChange,
  onRemarkChange,
  onTakePhoto,
  onNextSign,
}: FormPageProps) {
  return (
    <section className="mobile-page">
      <div className="mobile-card mobile-header">
        <button className="mobile-icon-btn" onClick={onBack}>
          ← 返回
        </button>
        <h1>{title}</h1>
        <div />
      </div>

      <div className="mobile-card">
        <div className="mobile-step-badge">
          步骤 {stepIndex}/{stepTotal}
        </div>
        <div className="mobile-summary-line">
          <span>构件</span>
          <strong>{componentCode}</strong>
        </div>
        <div className="mobile-summary-line">
          <span>名称</span>
          <strong>{componentName}</strong>
        </div>
        <div className="mobile-summary-line">
          <span>当前工序</span>
          <strong>{title}</strong>
        </div>
        <div className="mobile-summary-line">
          <span>要求角色</span>
          <strong>{requiredRole}</strong>
        </div>
        <div className="mobile-summary-line" style={{ marginBottom: 8 }}>
          <span>我的角色</span>
          <strong>{role}</strong>
        </div>

        <div className="mobile-muted" style={{ marginBottom: 8 }}>
          {spec.subtitle}
        </div>

        {spec.baseFields.map((field) => (
          <div key={field.key} className="mobile-field">
            <div className="mobile-label">{field.label}</div>
            <input
              className="mobile-input"
              type={field.type || 'text'}
              value={values[field.key] || ''}
              readOnly={!!field.readonly}
              onChange={(event) => onBaseChange(field.key, event.target.value)}
            />
          </div>
        ))}

        {spec.fields.map((field) => {
          const check = checks[field.key]
          return (
            <div key={field.key} className="mobile-field">
              <div className="mobile-label">
                {field.label}（{field.hint || '必填'}）
              </div>
              <div className="mobile-row">
                <input
                  className="mobile-input"
                  inputMode="decimal"
                  placeholder="请输入"
                  value={values[field.key] || ''}
                  onChange={(event) => onFieldChange(field.key, event.target.value)}
                />
                <div className="mobile-unit">{field.unit || ''}</div>
              </div>
              {check ? (
                <div className={`mobile-validation ${check.ok ? 'ok' : 'bad'}`}>
                  <div>
                    {check.ok ? '✓' : '✗'} {check.message}
                  </div>
                  {check.detail ? <div>{check.detail}</div> : null}
                  {check.tip ? <div>{check.tip}</div> : null}
                </div>
              ) : null}
            </div>
          )
        })}

        <div className="mobile-field">
          <div className="mobile-label">检查结论</div>
          <div className="mobile-row">
            {(['合格', '不合格'] as const).map((item) => (
              <button
                key={item}
                className={`mobile-btn ghost full ${result === item ? 'is-active' : ''}`}
                onClick={() => onResultChange(item)}
              >
                {item}
              </button>
            ))}
          </div>
        </div>

        <div className="mobile-field">
          <div className="mobile-label">备注（可选）</div>
          <textarea
            className="mobile-textarea"
            value={values.remark || ''}
            onChange={(event) => onRemarkChange(event.target.value)}
          />
        </div>

        {remoteGateHint ? <div className="mobile-validation bad">✗ {remoteGateHint}</div> : null}

        <div className="mobile-field">
          <div className="mobile-label">照片存证</div>
          <div className="mobile-row">
            <button className="mobile-btn ghost full" onClick={onTakePhoto}>
              拍照存证
            </button>
            <button className="mobile-btn primary full" onClick={onNextSign}>
              下一步→签名
            </button>
          </div>
          {photos.length ? (
            <div className="mobile-photo-grid">
              {photos.map((photo, index) => (
                <div key={`${photo.hash}-${index}`} className="mobile-photo-item">
                  <img src={photo.preview} alt={`证据${index + 1}`} />
                  <div className="meta">{photo.hash.slice(0, 14)}</div>
                </div>
              ))}
            </div>
          ) : (
            <p className="mobile-muted">暂无照片</p>
          )}
        </div>
      </div>
    </section>
  )
}

