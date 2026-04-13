type Props = {
  roleAllowed: boolean
  disputeOpen: boolean
  archiveLocked: boolean
  disputeProof: string
  disputeArbiterRole: string
  labQualified: boolean
  qcCompliant: boolean
  snappegReady: boolean
  geoFenceActive: boolean
  geoTemporalBlocked: boolean
  geoDistance: number
  geoRadiusM: unknown
}

export default function AuditWarningStack({
  roleAllowed,
  disputeOpen,
  archiveLocked,
  disputeProof,
  disputeArbiterRole,
  labQualified,
  qcCompliant,
  snappegReady,
  geoFenceActive,
  geoTemporalBlocked,
  geoDistance,
  geoRadiusM,
}: Props) {
  return (
    <>
      {!roleAllowed && (
        <div className="mt-3 rounded-lg border border-rose-700/70 bg-rose-950/30 px-2 py-1.5 text-xs text-rose-300">
          身份不匹配：当前 DID 无权提交该资产，请切换到授权 DTORole。
        </div>
      )}
      {disputeOpen && (
        <div className="mt-3 rounded-lg border border-rose-700/70 bg-rose-950/30 px-2 py-1.5 text-xs text-rose-200">
          争议挂起中：{disputeProof || '争议UTXO'} 已锁定该 v:// 地址，等待 {disputeArbiterRole || '业主/第三方检测'} 签入最终判定。
        </div>
      )}
      {archiveLocked && (
        <div className="mt-3 rounded-lg border border-sky-700/70 bg-sky-950/30 px-2 py-1.5 text-xs text-sky-200">
          主权封存：DocFinal 已导出并触发 Archive_Trip，当前资产已进入只读状态。
        </div>
      )}
      {roleAllowed && !labQualified && (
        <div className="mt-3 rounded-lg border border-amber-700/70 bg-amber-950/30 px-2 py-1.5 text-xs text-amber-200">
          证据链不完整：缺少实验合格存证。
        </div>
      )}
      {roleAllowed && labQualified && !qcCompliant && (
        <div className="mt-3 rounded-lg border border-amber-700/70 bg-amber-950/30 px-2 py-1.5 text-xs text-amber-200">
          证据链不完整：工序现场判定未通过。
        </div>
      )}
      {roleAllowed && !snappegReady && (
        <div className="mt-3 rounded-lg border border-amber-700/70 bg-amber-950/30 px-2 py-1.5 text-xs text-amber-200">
          SnapPeg 证据链未就绪：请补齐带 GPS / 时间戳的现场照片。
        </div>
      )}
      {geoFenceActive && geoTemporalBlocked && (
        <div className="mt-3 rounded-lg border border-rose-700/70 bg-rose-950/30 px-2 py-1.5 text-xs text-rose-200">
          空间越界：当前位置距锚点中心 {geoDistance ? `${Math.round(geoDistance)}m` : '未知'}，允许半径 {String(geoRadiusM ?? '-')}m。
        </div>
      )}
    </>
  )
}
