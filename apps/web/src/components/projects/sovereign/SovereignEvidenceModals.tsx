import type { Evidence } from './types'

type Props = {
  evidenceOpen: boolean
  evidenceFocus: Evidence | null
  geoTemporalBlocked: boolean
  activeCode: string
  activeUri: string
  lat: string
  lng: string
  executorDid: string
  sampleId: string
  onCloseEvidencePreview: () => void
  evidenceCenterFocus: Record<string, unknown> | null
  evidenceCenterDocFocus: Record<string, unknown> | null
  onCloseEvidenceFocus: () => void
  onCloseDocumentFocus: () => void
}

function asDict(value: unknown): Record<string, unknown> {
  return value && typeof value === 'object' && !Array.isArray(value) ? (value as Record<string, unknown>) : {}
}

export default function SovereignEvidenceModals({
  evidenceOpen,
  evidenceFocus,
  geoTemporalBlocked,
  activeCode,
  activeUri,
  lat,
  lng,
  executorDid,
  sampleId,
  onCloseEvidencePreview,
  evidenceCenterFocus,
  evidenceCenterDocFocus,
  onCloseEvidenceFocus,
  onCloseDocumentFocus,
}: Props) {
  return (
    <>
      {evidenceOpen && evidenceFocus && (
        <div className="fixed inset-0 z-[1200] grid place-items-center bg-slate-950/70">
          <div className="w-[520px] max-w-[92vw] rounded-xl border border-slate-700 bg-slate-950 p-4 text-slate-100">
            <div className="mb-2 text-sm font-extrabold">SnapPeg 物证详情</div>
            <div className="relative mb-2">
              <img src={evidenceFocus.url} alt={evidenceFocus.name} className={`mb-0 w-full rounded-lg border ${geoTemporalBlocked ? 'border-rose-500/80' : 'border-slate-700'}`} />
              <div className="absolute bottom-2 left-2 rounded border border-slate-600/70 bg-slate-950/75 px-2 py-1 text-[10px] text-slate-200">
                桩号 {activeCode || '-'} · GPS {lat},{lng} · NTP {evidenceFocus.ntp}
              </div>
            </div>
            <div className="break-all text-xs text-slate-400">
              <div className="text-emerald-300">主权已锁定</div>
              <div>签名 DID: {executorDid}</div>
              <div>定位: {lat}, {lng}</div>
              <div>授时戳: {evidenceFocus.ntp}</div>
              <div>样品: {sampleId || '-'}</div>
              <div>路径: {activeUri || '-'}</div>
              {geoTemporalBlocked && <div className="mt-1 text-rose-300">GPS 漂移/时间窗口异常，已触发风险拦截。</div>}
            </div>
            <div className="mt-3 flex justify-end">
              <button type="button" onClick={onCloseEvidencePreview} className="rounded-lg border border-slate-700 bg-slate-900 px-3 py-2 text-slate-200">关闭</button>
            </div>
          </div>
        </div>
      )}

      {evidenceCenterFocus && (
        <div className="fixed inset-0 z-[1200] grid place-items-center bg-slate-950/70">
          <div className="w-[560px] max-w-[92vw] rounded-xl border border-slate-700 bg-slate-950 p-4 text-slate-100">
            <div className="mb-2 text-sm font-extrabold">证据详情</div>
            {String(evidenceCenterFocus.media_type || '').startsWith('image') && String(evidenceCenterFocus.url || '') ? (
              <img src={String(evidenceCenterFocus.url || '')} alt={String(evidenceCenterFocus.file_name || 'evidence')} className="mb-2 w-full rounded-lg border border-slate-700" />
            ) : (
              <div className="mb-2 grid h-[200px] place-items-center rounded-lg border border-slate-700 text-xs text-slate-400">非图片证据</div>
            )}
            <div className="grid gap-1 break-all text-xs text-slate-400">
              <div>文件名: {String(evidenceCenterFocus.file_name || evidenceCenterFocus.id || '-')}</div>
              <div>哈希: {String(evidenceCenterFocus.evidence_hash || '-')}</div>
              <div>存证ID: {String(evidenceCenterFocus.proof_id || '-')}</div>
              <div>时间: {String(evidenceCenterFocus.time || '-')}</div>
              <div>来源: {String(evidenceCenterFocus.source || '-')}</div>
              <div>匹配: {String(evidenceCenterFocus.hash_match_text || (evidenceCenterFocus.hash_matched ? '已匹配' : '待核验'))}</div>
              <div>GPS: {String(asDict(asDict(evidenceCenterFocus).geo_location).lat || '-')}, {String(asDict(asDict(evidenceCenterFocus).geo_location).lng || '-')}</div>
              <div>NTP: {String(asDict(asDict(evidenceCenterFocus).server_timestamp_proof).ntp_server || asDict(asDict(evidenceCenterFocus).server_timestamp_proof).proof_hash || '-')}</div>
            </div>
            {String(evidenceCenterFocus.url || '') && (
              <div className="mt-2">
                <a href={String(evidenceCenterFocus.url || '')} target="_blank" rel="noreferrer" className="text-xs text-emerald-300">打开原始文件</a>
              </div>
            )}
            <div className="mt-3 flex justify-end">
              <button type="button" onClick={onCloseEvidenceFocus} className="rounded-lg border border-slate-700 bg-slate-900 px-3 py-2 text-slate-200">关闭</button>
            </div>
          </div>
        </div>
      )}

      {evidenceCenterDocFocus && (
        <div className="fixed inset-0 z-[1200] grid place-items-center bg-slate-950/70">
          <div className="w-[520px] max-w-[92vw] rounded-xl border border-slate-700 bg-slate-950 p-4 text-slate-100">
            <div className="mb-2 text-sm font-extrabold">文档详情</div>
            <div className="grid gap-1 break-all text-xs text-slate-400">
              <div>文件名: {String(evidenceCenterDocFocus.file_name || '-')}</div>
              <div>类型: {String(evidenceCenterDocFocus.doc_type || '-')}</div>
              {String(evidenceCenterDocFocus.doc_status || '') && <div>状态: {String(evidenceCenterDocFocus.doc_status || '-')}</div>}
              {String(evidenceCenterDocFocus.trip_action || '') && <div>Trip: {String(evidenceCenterDocFocus.trip_action || '-')}</div>}
              {String(evidenceCenterDocFocus.lifecycle_stage || '') && <div>阶段: {String(evidenceCenterDocFocus.lifecycle_stage || '-')}</div>}
              <div>存证ID: {String(evidenceCenterDocFocus.proof_id || '-')}</div>
              <div>存证哈希: {String(evidenceCenterDocFocus.proof_hash || '-')}</div>
              <div>创建时间: {String(evidenceCenterDocFocus.created_at || '-')}</div>
              <div>来源 UTXO: {String(evidenceCenterDocFocus.source_utxo_id || '-')}</div>
              <div>节点: {String(evidenceCenterDocFocus.node_uri || '-')}</div>
            </div>
            {String(evidenceCenterDocFocus.storage_url || '') ? (
              <div className="mt-2">
                <a href={String(evidenceCenterDocFocus.storage_url || '')} target="_blank" rel="noreferrer" className="text-xs text-emerald-300">打开文档</a>
              </div>
            ) : (
              <div className="mt-2 text-xs text-slate-500">无可用链接</div>
            )}
            <div className="mt-3 flex justify-end">
              <button type="button" onClick={onCloseDocumentFocus} className="rounded-lg border border-slate-700 bg-slate-900 px-3 py-2 text-slate-200">关闭</button>
            </div>
          </div>
        </div>
      )}
    </>
  )
}

