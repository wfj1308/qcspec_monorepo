import React from 'react'
import type { HistoryRecord } from '../types/mobile'

type DonePageProps = {
  done: HistoryRecord
  onViewProgress: () => void
  onScanNext: () => void
  onGoHome: () => void
}

export default function DonePage({ done, onViewProgress, onScanNext, onGoHome }: DonePageProps) {
  const syncState = done.chainSyncState || 'fallback'
  const syncLabel =
    syncState === 'chained' ? '已写入主链' : syncState === 'pending' ? '待同步（离线缓存）' : '已提交（主链待补偿）'
  const syncClass = syncState === 'chained' ? 'success' : syncState === 'pending' ? 'warning' : 'neutral'

  return (
    <section className="mobile-page">
      <div className="mobile-card mobile-center">
        <div className="mobile-check">✓</div>
        <h2>提交成功</h2>
        <div>{done.code}</div>
        <div>{done.step} 已完成</div>
        <div className="mobile-muted">Proof ID</div>
        <div className="mobile-proof">{done.proofId}</div>
        <div className={`mobile-sync-pill ${syncClass}`}>{syncLabel}</div>
        {done.chainSyncMessage ? <div className="mobile-muted">{done.chainSyncMessage}</div> : null}
        {done.chainSyncError ? <div className="mobile-muted">链路详情：{done.chainSyncError}</div> : null}
        <div className="mobile-muted">下一步：{done.nextStep || '等待施工员操作'}</div>

        <div className="mobile-row full">
          <button className="mobile-btn ghost full" onClick={onViewProgress}>
            查看工序进度
          </button>
          <button className="mobile-btn primary full" onClick={onScanNext}>
            扫描下一个构件
          </button>
        </div>
        <button className="mobile-btn ghost full" onClick={onGoHome}>
          返回首页
        </button>
      </div>
    </section>
  )
}


