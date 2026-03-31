import React from 'react'
import SpuRenderer from '../SpuRenderer'

type Props = React.ComponentProps<typeof SpuRenderer>

export default function PhysicalWorkbench(props: Props) {
  return (
    <>
      <div className="mb-3 rounded-xl border border-slate-600/60 bg-slate-950/40 px-3 py-2 text-[11px] text-slate-200">
        Material Tag: `physical` · 按实体工程规则动态装载，围绕设计值、实测值与允许偏差做 NormPeg 判定。
      </div>
      <SpuRenderer {...props} isContractSpu={false} />
    </>
  )
}
