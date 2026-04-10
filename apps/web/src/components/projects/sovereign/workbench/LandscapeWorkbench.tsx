import SpuRenderer from '../SpuRenderer'

type Props = React.ComponentProps<typeof SpuRenderer>

export default function LandscapeWorkbench(props: Props) {
  return (
    <>
      <div className="mb-3 rounded-xl border border-lime-600/50 bg-lime-950/20 px-3 py-2 text-[11px] text-lime-100">
        Material Tag: `landscape` · 按绿化验收规则动态装载，优先展示成活率、覆盖率与高度偏差。
      </div>
      <SpuRenderer {...props} isContractSpu={false} />
    </>
  )
}
