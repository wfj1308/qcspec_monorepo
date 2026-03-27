/**
 * QCSpec · 核心 UI 组件
 * apps/web/src/components/ui/index.tsx
 */

import React from 'react'
import { RESULT_COLORS, RESULT_LABELS, type InspectResult } from '@qcspec/types'

// ── CSS 变量（注入到 :root）──
export const CSS_VARS = `
  :root {
    --ink:    #0F172A;
    --white:  #FFFFFF;
    --bg:     #F0F4F8;
    --blue:   #1A56DB;
    --blue-l: #EFF6FF;
    --green:  #059669;
    --green-l:#ECFDF5;
    --red:    #DC2626;
    --red-l:  #FEF2F2;
    --gold:   #D97706;
    --gold-l: #FFFBEB;
    --gray:   #6B7280;
    --border: #E2E8F0;
    --mono:   'JetBrains Mono', monospace;
    --sans:   'Noto Sans SC', sans-serif;
  }
  * { box-sizing: border-box; margin: 0; padding: 0; }
  body { background: var(--bg); color: var(--ink); font-family: var(--sans); }
`

// ── Badge ──
interface BadgeProps {
  result: InspectResult
  size?:  'sm' | 'md'
}
export function ResultBadge({ result, size = 'md' }: BadgeProps) {
  const colors: Record<InspectResult, { bg: string; color: string }> = {
    pass: { bg: '#ECFDF5', color: '#059669' },
    warn: { bg: '#FFFBEB', color: '#D97706' },
    fail: { bg: '#FEF2F2', color: '#DC2626' },
  }
  const c    = colors[result]
  const fs   = size === 'sm' ? 11 : 12
  const px   = size === 'sm' ? 6  : 10
  return (
    <span style={{
      display: 'inline-block',
      background: c.bg, color: c.color,
      fontSize: fs, fontWeight: 700,
      padding: `3px ${px}px`, borderRadius: 6,
    }}>
      {RESULT_LABELS[result]}
    </span>
  )
}

// ── Progress Bar ──
interface ProgressProps {
  value: number   // 0-100
  color?: string
  height?: number
}
export function ProgressBar({ value, color = '#1A56DB', height = 6 }: ProgressProps) {
  return (
    <div style={{ background: '#E2E8F0', borderRadius: height, height, overflow: 'hidden' }}>
      <div style={{
        width: `${Math.min(100, Math.max(0, value))}%`,
        height: '100%',
        background: color,
        borderRadius: height,
        transition: 'width 0.4s ease',
      }} />
    </div>
  )
}

// ── Card ──
interface CardProps {
  children:   React.ReactNode
  title?:     string
  icon?:      string
  style?:     React.CSSProperties
  className?: string
}
export function Card({ children, title, icon, style }: CardProps) {
  return (
    <div style={{
      background: '#fff',
      border: '1px solid var(--border)',
      borderRadius: 14, padding: 20,
      marginBottom: 14,
      ...style,
    }}>
      {title && (
        <div style={{
          fontSize: 14, fontWeight: 700, color: 'var(--ink)',
          marginBottom: 14, display: 'flex', alignItems: 'center', gap: 8,
        }}>
          {icon && <span style={{ fontSize: 18 }}>{icon}</span>}
          {title}
        </div>
      )}
      {children}
    </div>
  )
}

// ── Stat Card ──
interface StatCardProps {
  value: number | string
  label: string
  icon:  string
  color?: string
  trend?: string
}
export function StatCard({ value, label, icon, color = '#EFF6FF', trend }: StatCardProps) {
  return (
    <div style={{
      background: '#fff', border: '1px solid var(--border)',
      borderRadius: 12, padding: 16,
      display: 'flex', alignItems: 'center', gap: 14,
    }}>
      <div style={{
        width: 44, height: 44, borderRadius: 10,
        background: color,
        display: 'flex', alignItems: 'center', justifyContent: 'center',
        fontSize: 20, flexShrink: 0,
      }}>
        {icon}
      </div>
      <div>
        <div style={{ fontSize: 26, fontWeight: 900, lineHeight: 1 }}>{value}</div>
        <div style={{ fontSize: 12, color: 'var(--gray)', marginTop: 3 }}>{label}</div>
        {trend && <div style={{ fontSize: 12, color: '#059669', marginTop: 2 }}>{trend}</div>}
      </div>
    </div>
  )
}

// ── Button ──
interface BtnProps {
  children:  React.ReactNode
  onClick?:  () => void
  variant?:  'primary' | 'secondary' | 'danger' | 'ghost'
  size?:     'sm' | 'md' | 'lg'
  disabled?: boolean
  fullWidth?: boolean
  icon?:     string
  type?:     'button' | 'submit'
}
export function Button({
  children, onClick, variant = 'primary',
  size = 'md', disabled, fullWidth, icon, type = 'button'
}: BtnProps) {
  const styles: Record<string, React.CSSProperties> = {
    primary:   { background: '#1A56DB', color: '#fff', border: 'none' },
    secondary: { background: '#fff',    color: '#6B7280', border: '1px solid #E2E8F0' },
    danger:    { background: '#FEF2F2', color: '#DC2626', border: '1px solid #FECACA' },
    ghost:     { background: 'transparent', color: '#6B7280', border: 'none' },
  }
  const sizes: Record<string, React.CSSProperties> = {
    sm: { padding: '6px 12px', fontSize: 12 },
    md: { padding: '10px 18px', fontSize: 13 },
    lg: { padding: '14px 24px', fontSize: 15 },
  }
  return (
    <button
      type={type}
      onClick={onClick}
      disabled={disabled}
      style={{
        ...styles[variant],
        ...sizes[size],
        borderRadius: 8,
        fontWeight: 700,
        cursor: disabled ? 'not-allowed' : 'pointer',
        opacity: disabled ? 0.6 : 1,
        fontFamily: 'var(--sans)',
        display: 'inline-flex',
        alignItems: 'center',
        gap: 6,
        width: fullWidth ? '100%' : undefined,
        justifyContent: fullWidth ? 'center' : undefined,
        transition: 'all 0.2s',
      }}
    >
      {icon && <span>{icon}</span>}
      {children}
    </button>
  )
}

// ── Input ──
interface InputProps {
  label?:       string
  value:        string | number
  onChange:     (v: string) => void
  onBlur?:      () => void
  placeholder?: string
  type?:        string
  required?:    boolean
  hint?:        string
}
export function Input({ label, value, onChange, onBlur, placeholder, type = 'text', required, hint }: InputProps) {
  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: 5 }}>
      {label && (
        <label style={{ fontSize: 12, fontWeight: 700, color: 'var(--gray)', letterSpacing: '0.5px', textTransform: 'uppercase' }}>
          {label}{required && <span style={{ color: '#DC2626', marginLeft: 2 }}>*</span>}
        </label>
      )}
      <input
        type={type}
        value={value}
        onChange={e => onChange(e.target.value)}
        onBlur={onBlur}
        placeholder={placeholder}
        style={{
          background: '#F0F4F8', border: '1px solid #E2E8F0',
          borderRadius: 8, padding: '9px 12px',
          fontSize: 13, fontFamily: 'var(--sans)',
          color: 'var(--ink)', outline: 'none', width: '100%',
        }}
      />
      {hint && <div style={{ fontSize: 12, color: '#9CA3AF' }}>{hint}</div>}
    </div>
  )
}

// ── Select ──
interface SelectProps {
  label?:    string
  value:     string
  onChange:  (v: string) => void
  options:   { value: string; label: string }[]
  required?: boolean
}
export function Select({ label, value, onChange, options, required }: SelectProps) {
  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: 5 }}>
      {label && (
        <label style={{ fontSize: 12, fontWeight: 700, color: 'var(--gray)', letterSpacing: '0.5px', textTransform: 'uppercase' }}>
          {label}{required && <span style={{ color: '#DC2626', marginLeft: 2 }}>*</span>}
        </label>
      )}
      <select
        value={value}
        onChange={e => onChange(e.target.value)}
        style={{
          background: '#F0F4F8', border: '1px solid #E2E8F0',
          borderRadius: 8, padding: '9px 12px',
          fontSize: 13, fontFamily: 'var(--sans)',
          color: 'var(--ink)', outline: 'none', width: '100%',
        }}
      >
        {options.map(o => (
          <option key={o.value} value={o.value}>{o.label}</option>
        ))}
      </select>
    </div>
  )
}

// ── Toast ──
interface ToastProps { message: string }
export function Toast({ message }: ToastProps) {
  if (!message) return null
  return (
    <div style={{
      position: 'fixed', bottom: 24, left: '50%',
      transform: 'translateX(-50%)',
      background: '#0F172A', color: '#fff',
      padding: '10px 20px', borderRadius: 20,
      fontSize: 13, fontWeight: 500,
      zIndex: 9999, whiteSpace: 'nowrap',
      animation: 'fadeIn 0.3s ease',
    }}>
      {message}
    </div>
  )
}

// ── Empty State ──
interface EmptyProps { icon: string; title: string; sub?: string }
export function EmptyState({ icon, title, sub }: EmptyProps) {
  return (
    <div style={{ textAlign: 'center', padding: '48px 20px', color: '#9CA3AF' }}>
      <div style={{ fontSize: 48, marginBottom: 12 }}>{icon}</div>
      <div style={{ fontSize: 15, fontWeight: 700, color: '#6B7280', marginBottom: 6 }}>{title}</div>
      {sub && <div style={{ fontSize: 13 }}>{sub}</div>}
    </div>
  )
}

// ── VPath Display ──
interface VPathProps { uri: string; proofId?: string }
export function VPathDisplay({ uri, proofId }: VPathProps) {
  return (
    <div style={{
      background: '#0F172A', borderRadius: 8,
      padding: '10px 14px', marginBottom: 12,
      display: 'flex', alignItems: 'center', gap: 10,
    }}>
      <span style={{ fontSize: 12, color: '#475569', whiteSpace: 'nowrap' }}>v://</span>
      <span style={{
        fontFamily: 'var(--mono)', fontSize: 12,
        color: '#60A5FA', fontWeight: 700, flex: 1, wordBreak: 'break-all',
      }}>
        {uri}
      </span>
      {proofId && (
        <span style={{
          fontFamily: 'var(--mono)', fontSize: 12,
          color: '#F59E0B', background: 'rgba(245,158,11,0.1)',
          padding: '2px 8px', borderRadius: 4, whiteSpace: 'nowrap',
        }}>
          {proofId.substring(0, 18)}
        </span>
      )}
    </div>
  )
}

