import React, { useEffect, useRef } from 'react'
import { MOBILE_ROLES } from '../types/mobile'
import type { MobileFormSpec, MobileRole, SignatureMethod } from '../types/mobile'

type SignPageProps = {
  role: MobileRole
  requiredRole: MobileRole
  canSign: boolean
  code: string
  stepName: string
  result: '合格' | '不合格'
  spec: MobileFormSpec
  values: Record<string, string>
  password: string
  signatureMethod: SignatureMethod
  onBack: () => void
  onSetPassword: (value: string) => void
  onSetHandwriteSignature: (value: string) => void
  onUseSignPeg: () => void
  onUseCaSign: () => void
  onSubmit: () => Promise<void>
}

export default function SignPage({
  role,
  requiredRole,
  canSign,
  code,
  stepName,
  result,
  spec,
  values,
  password,
  signatureMethod,
  onBack,
  onSetPassword,
  onSetHandwriteSignature,
  onUseSignPeg,
  onUseCaSign,
  onSubmit,
}: SignPageProps) {
  const canvasRef = useRef<HTMLCanvasElement | null>(null)

  useEffect(() => {
    const canvas = canvasRef.current
    if (!canvas) return
    const context = canvas.getContext('2d')
    if (!context) return

    context.lineWidth = 2
    context.lineCap = 'round'

    let drawing = false
    const getPos = (event: MouseEvent | TouchEvent) => {
      const rect = canvas.getBoundingClientRect()
      const point = event instanceof TouchEvent ? event.touches[0] : event
      return {
        x: ((point.clientX - rect.left) / rect.width) * canvas.width,
        y: ((point.clientY - rect.top) / rect.height) * canvas.height,
      }
    }

    const start = (event: MouseEvent | TouchEvent) => {
      drawing = true
      const point = getPos(event)
      context.beginPath()
      context.moveTo(point.x, point.y)
      event.preventDefault()
    }
    const move = (event: MouseEvent | TouchEvent) => {
      if (!drawing) return
      const point = getPos(event)
      context.lineTo(point.x, point.y)
      context.stroke()
      onSetHandwriteSignature(canvas.toDataURL('image/png'))
      event.preventDefault()
    }
    const end = (event: MouseEvent | TouchEvent) => {
      drawing = false
      event.preventDefault()
    }

    canvas.addEventListener('mousedown', start as EventListener)
    canvas.addEventListener('mousemove', move as EventListener)
    canvas.addEventListener('mouseup', end as EventListener)
    canvas.addEventListener('mouseleave', end as EventListener)
    canvas.addEventListener('touchstart', start as EventListener, { passive: false })
    canvas.addEventListener('touchmove', move as EventListener, { passive: false })
    canvas.addEventListener('touchend', end as EventListener, { passive: false })

    return () => {
      canvas.removeEventListener('mousedown', start as EventListener)
      canvas.removeEventListener('mousemove', move as EventListener)
      canvas.removeEventListener('mouseup', end as EventListener)
      canvas.removeEventListener('mouseleave', end as EventListener)
      canvas.removeEventListener('touchstart', start as EventListener)
      canvas.removeEventListener('touchmove', move as EventListener)
      canvas.removeEventListener('touchend', end as EventListener)
    }
  }, [onSetHandwriteSignature])

  const clearCanvas = () => {
    const canvas = canvasRef.current
    if (!canvas) return
    const context = canvas.getContext('2d')
    if (!context) return
    context.clearRect(0, 0, canvas.width, canvas.height)
    onSetHandwriteSignature('')
  }

  return (
    <section className="mobile-page">
      <div className="mobile-card mobile-header">
        <button className="mobile-icon-btn" onClick={onBack}>
          ← 返回
        </button>
        <h1>签名确认</h1>
        <div />
      </div>

      <div className="mobile-card">
        <p className="mobile-title">本次提交摘要</p>
        <div className="mobile-summary-line">
          <span>构件</span>
          <strong>{code}</strong>
        </div>
        <div className="mobile-summary-line">
          <span>工序</span>
          <strong>{stepName}</strong>
        </div>
        <div className="mobile-summary-line">
          <span>结论</span>
          <strong>{result}</strong>
        </div>
        {spec.fields.map((field) => (
          <div key={field.key} className="mobile-summary-line">
            <span>{field.label}</span>
            <strong>
              {values[field.key] || '-'}
              {field.unit || ''}
            </strong>
          </div>
        ))}

        <hr className="mobile-divider" />

        <div className="mobile-summary-line">
          <span>我的角色</span>
          <strong>{role}</strong>
        </div>
        <div className="mobile-summary-line">
          <span>可签角色</span>
          <strong>{requiredRole}</strong>
        </div>

        <div className="mobile-role-sign-grid">
          {MOBILE_ROLES.map((item) => (
            <div
              key={item}
              className={`mobile-role-tag ${
                item === requiredRole ? 'required' : item === role ? 'mine' : 'disabled'
              }`}
            >
              {item} · {item === requiredRole ? '可签' : item === role ? '我' : '不可签'}
            </div>
          ))}
        </div>

        <div className="mobile-field">
          <div className="mobile-label">请签名</div>
          <canvas ref={canvasRef} className="mobile-sign-canvas" width={460} height={180} />
          <div className="mobile-row">
            <button className="mobile-btn ghost full" onClick={clearCanvas}>
              清除重写
            </button>
            <button className="mobile-btn ghost full" onClick={onUseSignPeg}>
              SignPeg签名
            </button>
          </div>
          <button className="mobile-btn ghost full" onClick={onUseCaSign}>
            CA签名（法大大）
          </button>
          <p className="mobile-muted">当前签名方式：{signatureMethod === 'handwrite' ? '手写' : signatureMethod === 'signpeg' ? 'SignPeg' : '法大大CA'}</p>
        </div>

        <div className="mobile-field">
          <div className="mobile-label">或使用密码确认</div>
          <input
            type="password"
            className="mobile-input"
            value={password}
            onChange={(event) => onSetPassword(event.target.value)}
            placeholder="输入密码"
          />
        </div>

        <button className="mobile-btn primary full" disabled={!canSign} onClick={() => void onSubmit()}>
          {canSign ? '确认提交' : '当前角色不可签名'}
        </button>
      </div>
    </section>
  )
}


