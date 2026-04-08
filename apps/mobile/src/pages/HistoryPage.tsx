import React from 'react'
import type { HistoryRecord } from '../types/mobile'

type HistoryPageProps = {
  history: HistoryRecord[]
  pendingSubmissionCount: number
  pendingAnchorCount: number
  online: boolean
  onBack: () => void
  onSyncNow: () => Promise<void>
}

export default function HistoryPage({
  history,
  pendingSubmissionCount,
  pendingAnchorCount,
  online,
  onBack,
  onSyncNow,
}: HistoryPageProps) {
  return (
    <section className="mobile-page">
      <div className="mobile-card mobile-header">
        <button className="mobile-icon-btn" onClick={onBack}>
          ← 返回
        </button>
        <h1>历史记录</h1>
        <div />
      </div>

      <div className="mobile-card">
        <p className="mobile-title">最近提交</p>
        <div className="mobile-list">
          {history.length ? (
            history
              .slice()
              .reverse()
              .map((item, index) => (
                <div key={`${item.proofId}-${index}`} className="mobile-list-item">
                  <div>
                    <div>
                      <strong>{item.code}</strong> {item.step}
                    </div>
                    <div className="mobile-muted">
                      {item.time} · {item.role}
                    </div>
                    <div className="mobile-muted">{item.proofId}</div>
                  </div>
                  <span className={`mobile-badge ${item.result === '合格' ? 'success' : 'danger'}`}>{item.result}</span>
                </div>
              ))
          ) : (
            <p className="mobile-muted">暂无历史记录</p>
          )}
        </div>
      </div>

      <div className="mobile-card">
        <p className="mobile-title">待同步</p>
        <p className="mobile-muted">表单待同步：{pendingSubmissionCount} 条</p>
        <p className="mobile-muted">照片待同步：{pendingAnchorCount} 条</p>
        <button className="mobile-btn ghost full" disabled={!online} onClick={() => void onSyncNow()}>
          立即同步
        </button>
      </div>
    </section>
  )
}


