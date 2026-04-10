
export type SpuFormRow = {
  field?: string
  label?: string
  operator?: string
  default?: string
  unit?: string
}

type Props = {
  isContractSpu: boolean
  schema: SpuFormRow[]
  form: Record<string, string>
  geoFormLocked: boolean
  onFormChange: (next: Record<string, string>) => void
  evalNorm: (op: string, threshold: string, value: string) => 'pending' | 'success' | 'fail'
  sanitizeMeasuredInput: (raw: string) => string
  metricLabel: (label: string, fieldKey: string) => string
  ruleText: (operator: string, threshold: string, unit: string) => string
}

function operatorText(operator: string) {
  const op = String(operator || '').trim().toLowerCase()
  if (!op || op === 'present') return '现场录入'
  if (op === 'range') return '区间审计'
  if (op === '>=') return '下限阈值'
  if (op === '<=') return '上限阈值'
  if (op === '=') return '定值匹配'
  return operator
}

function statusTone(status: 'pending' | 'success' | 'fail') {
  if (status === 'success') {
    return {
      border: 'border-emerald-500/70',
      glow: '0 0 0 1px rgba(16,185,129,.22), 0 0 20px rgba(16,185,129,.14)',
      bg: 'bg-emerald-950/20',
      text: 'text-emerald-200',
      label: 'NormPeg 合格',
      icon: '✓',
      hint: '实测值已落入允许阈值区间。',
      pulseClass: 'spu-pass-pulse',
    }
  }
  if (status === 'fail') {
    return {
      border: 'border-rose-500/70',
      glow: '0 0 0 1px rgba(244,63,94,.22), 0 0 20px rgba(244,63,94,.14)',
      bg: 'bg-rose-950/20',
      text: 'text-rose-200',
      label: 'NormPeg 预警',
      icon: '!',
      hint: '实测值越界，请复核或补充佐证。',
      pulseClass: 'spu-fail-pulse',
    }
  }
  return {
    border: 'border-slate-700/80',
    glow: '0 0 0 1px rgba(51,65,85,.16)',
    bg: 'bg-slate-950/40',
    text: 'text-slate-300',
    label: '待录入',
    icon: '·',
    hint: '等待当前 SPU 字段完成采集。',
    pulseClass: '',
  }
}

export default function SpuRenderer({
  isContractSpu,
  schema,
  form,
  geoFormLocked,
  onFormChange,
  evalNorm,
  sanitizeMeasuredInput,
  metricLabel,
  ruleText,
}: Props) {
  let pass = 0
  let fail = 0
  let pending = 0

  schema.forEach((row, idx) => {
    const key = String(row.field || `f_${idx}`)
    const status = evalNorm(String(row.operator || ''), String(row.default || ''), form[key] || '')
    if (status === 'success') pass += 1
    else if (status === 'fail') fail += 1
    else pending += 1
  })

  return (
    <div className="mb-3 overflow-hidden rounded-2xl border border-slate-700/80 bg-[linear-gradient(180deg,rgba(2,6,23,.94),rgba(15,23,42,.88))] shadow-[0_0_0_1px_rgba(51,65,85,.18),0_18px_40px_rgba(2,6,23,.42)]">
      <style>{`@keyframes spuPassPulse{0%{transform:scale(.92);box-shadow:0 0 0 rgba(16,185,129,0)}50%{transform:scale(1.05);box-shadow:0 0 16px rgba(16,185,129,.32)}100%{transform:scale(.92);box-shadow:0 0 0 rgba(16,185,129,0)}}
      @keyframes spuFailPulse{0%{transform:scale(.96);box-shadow:0 0 0 rgba(244,63,94,0)}50%{transform:scale(1.04);box-shadow:0 0 16px rgba(244,63,94,.28)}100%{transform:scale(.96);box-shadow:0 0 0 rgba(244,63,94,0)}}
      .spu-pass-pulse{animation:spuPassPulse 1.4s ease-in-out infinite}
      .spu-fail-pulse{animation:spuFailPulse 1.1s ease-in-out infinite}`}</style>

      <div className="border-b border-slate-700/80 bg-[linear-gradient(90deg,rgba(8,47,73,.38),rgba(15,23,42,.18),rgba(2,6,23,.02))] px-4 py-3">
        <div className="flex flex-wrap items-center justify-between gap-3">
          <div>
            <div className="text-[11px] uppercase tracking-[0.22em] text-sky-300/80">SPU Dynamic Form</div>
            <div className="mt-1 text-sm font-semibold text-slate-100">
              {isContractSpu ? '合同凭证录入台' : '参数化质检录入台'}
            </div>
            <div className="mt-1 text-[11px] text-slate-400">
              {isContractSpu ? '附件核验、金额锁定与签认前置。' : '检测项目、规定值与实测值联动判定。'}
            </div>
          </div>
          <div className="grid grid-cols-3 gap-2 text-[11px]">
            <div className="rounded-xl border border-emerald-500/50 bg-emerald-950/30 px-3 py-2 text-center text-emerald-200">
              <div className="font-semibold">{pass}</div>
              <div className="text-emerald-300/80">合格</div>
            </div>
            <div className="rounded-xl border border-rose-500/50 bg-rose-950/30 px-3 py-2 text-center text-rose-200">
              <div className="font-semibold">{fail}</div>
              <div className="text-rose-300/80">预警</div>
            </div>
            <div className="rounded-xl border border-slate-600/70 bg-slate-900/60 px-3 py-2 text-center text-slate-200">
              <div className="font-semibold">{pending}</div>
              <div className="text-slate-400">待录入</div>
            </div>
          </div>
        </div>
      </div>

      <div className="grid grid-cols-[1.25fr_.95fr_1fr_.7fr] gap-3 border-b border-slate-700/80 bg-slate-950/85 px-4 py-3 text-[11px] font-semibold uppercase tracking-[0.16em] text-slate-400 max-[960px]:hidden">
        <span>{isContractSpu ? '凭证字段' : '检测项目'}</span>
        <span>{isContractSpu ? '要求口径' : '规定值'}</span>
        <span>{isContractSpu ? '录入值' : '实测值'}</span>
        <span>{isContractSpu ? '状态' : '判定'}</span>
      </div>

      <div className="max-h-[360px] overflow-y-auto px-3 py-3">
        {!schema.length && (
          <div className="rounded-2xl border border-amber-500/40 bg-amber-950/25 px-4 py-6 text-center text-sm text-amber-100">
            当前节点未解析到 SPU 条款或门控规则，提交已锁定。
          </div>
        )}

        <div className="grid gap-3">
          {schema.map((row, idx) => {
            const key = String(row.field || `f_${idx}`)
            const value = form[key] || ''
            const status = evalNorm(String(row.operator || ''), String(row.default || ''), value)
            const tone = statusTone(status)
            const inputId = `spu-field-${key}-${idx}`
            const inputMode = String(row.operator || '').toLowerCase() === 'present' ? 'text' : 'decimal'
            const label = metricLabel(String(row.label || ''), key)

            return (
              <div
                key={`${key}-${idx}`}
                className={`grid grid-cols-[1.25fr_.95fr_1fr_.7fr] gap-3 rounded-2xl border px-3 py-3 transition ${tone.border} ${tone.bg} max-[960px]:grid-cols-1`}
                style={{ boxShadow: tone.glow }}
              >
                <label htmlFor={inputId} className="flex min-w-0 flex-col justify-center">
                  <div className="flex flex-wrap items-center gap-2">
                    <span className="inline-flex h-6 min-w-6 items-center justify-center rounded-full border border-slate-600/80 bg-slate-950/80 px-1.5 text-[10px] font-semibold text-slate-300">
                      {String(idx + 1).padStart(2, '0')}
                    </span>
                    <span className="truncate text-sm font-semibold text-slate-100">{label}</span>
                  </div>
                  <div className="mt-2 flex flex-wrap items-center gap-2 text-[11px] text-slate-400">
                    <span className="rounded-full border border-slate-700/80 bg-slate-950/80 px-2 py-0.5">
                      {operatorText(String(row.operator || 'present'))}
                    </span>
                    {!!row.unit && (
                      <span className="rounded-full border border-slate-700/80 bg-slate-950/60 px-2 py-0.5 text-slate-300">
                        单位 {row.unit}
                      </span>
                    )}
                  </div>
                </label>

                <div className="flex flex-col justify-center text-sm">
                  <div className="mb-1 hidden text-[10px] uppercase tracking-[0.14em] text-slate-500 max-[960px]:block">
                    {isContractSpu ? '要求口径' : '规定值'}
                  </div>
                  <div className="font-medium text-slate-100">{ruleText(String(row.operator || ''), String(row.default || '-'), String(row.unit || ''))}</div>
                  <div className="mt-1 text-[11px] text-slate-500">
                    {isContractSpu ? '字段校核完成后进入签认链路。' : 'NormPeg 会在每次变更时即时校验。'}
                  </div>
                </div>

                <div className="flex flex-col justify-center">
                  <div className="mb-1 hidden text-[10px] uppercase tracking-[0.14em] text-slate-500 max-[960px]:block">
                    {isContractSpu ? '录入值' : '实测值'}
                  </div>
                  <input
                    id={inputId}
                    value={value}
                    inputMode={inputMode}
                    disabled={geoFormLocked}
                    onChange={(e) => {
                      const raw = e.target.value
                      const nextValue = inputMode === 'text' ? raw : sanitizeMeasuredInput(raw)
                      onFormChange({ ...form, [key]: nextValue })
                    }}
                    className={`w-full rounded-xl border bg-slate-950/90 px-3 py-2.5 text-sm text-slate-100 placeholder:text-slate-500 focus:outline-none focus:ring-2 focus:ring-sky-500/30 ${
                      geoFormLocked ? 'cursor-not-allowed opacity-60' : ''
                    } ${tone.border}`}
                    placeholder={isContractSpu ? '请输入凭证内容' : '请输入现场实测值'}
                  />
                  <div className="mt-1 text-[11px] text-slate-500">
                    {geoFormLocked ? '字段已锁定，等待链上回写完成。' : '受控输入，带实时审计反馈。'}
                  </div>
                </div>

                <div className="flex min-w-0 flex-col justify-center">
                  <div className="mb-1 hidden text-[10px] uppercase tracking-[0.14em] text-slate-500 max-[960px]:block">
                    {isContractSpu ? '状态' : '判定'}
                  </div>
                  <div className={`flex items-center gap-2 text-sm font-semibold ${tone.text}`}>
                    <span
                      className={`inline-flex h-7 w-7 items-center justify-center rounded-full border ${tone.pulseClass}`}
                      style={{
                        borderColor: status === 'success' ? 'rgba(16,185,129,.65)' : status === 'fail' ? 'rgba(244,63,94,.65)' : 'rgba(100,116,139,.5)',
                        background: status === 'success' ? 'rgba(16,185,129,.14)' : status === 'fail' ? 'rgba(244,63,94,.14)' : 'rgba(15,23,42,.85)',
                        boxShadow: status === 'pending' ? 'none' : tone.glow,
                      }}
                    >
                      {tone.icon}
                    </span>
                    <span className="truncate">{tone.label}</span>
                  </div>
                  <div className="mt-1 text-[11px] text-slate-400">{tone.hint}</div>
                </div>
              </div>
            )
          })}
        </div>
      </div>
    </div>
  )
}
