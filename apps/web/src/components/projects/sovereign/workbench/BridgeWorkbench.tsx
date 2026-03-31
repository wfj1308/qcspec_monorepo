import React from 'react'
import SpuRenderer from '../SpuRenderer'

type Props = React.ComponentProps<typeof SpuRenderer>

export default function BridgeWorkbench(props: Props) {
  return (
    <>
      <div className="mb-3 rounded-xl border border-emerald-600/50 bg-emerald-950/25 px-3 py-2 text-[11px] text-emerald-100">
        Material Tag: `bridge` · 按桥梁实体规则动态装载，重点关注结构实测、保护层与锁线指标。
      </div>
      <SpuRenderer {...props} isContractSpu={false} />
    </>
  )
}
