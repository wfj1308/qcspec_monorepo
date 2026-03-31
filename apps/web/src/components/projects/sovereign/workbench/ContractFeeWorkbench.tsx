import React from 'react'
import SpuRenderer from '../SpuRenderer'

type Props = React.ComponentProps<typeof SpuRenderer>

export default function ContractFeeWorkbench(props: Props) {
  return (
    <>
      <div className="mb-3 rounded-xl border border-amber-600/50 bg-amber-950/25 px-3 py-2 text-[11px] text-amber-100">
        Material Tag: `contract` · 按合同凭证规则动态装载，聚焦附件核验、金额锁定与归档闭环。
      </div>
      <SpuRenderer {...props} isContractSpu />
    </>
  )
}
