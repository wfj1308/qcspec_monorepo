import React from 'react'

import {
  chainIcon,
  formatTimestamp,
  normalizeStatusToken,
  usePublicVerifyController,
} from './usePublicVerifyController'

type PublicVerifyViewModel = ReturnType<typeof usePublicVerifyController>

type Props = {
  vm: PublicVerifyViewModel
}

export default function PublicVerifyView({ vm }: Props) {
  const {
    loading,
    error,
    payload,
    hashState,
    hashVerified,
    showAudit,
    specModal,
    showRectify,
    downloadingDsp,
    lineageDepth,
    traceMode,
    summary,
    context,
    qcgate,
    remediation,
    gateHashOk,
    remediationRecords,
    hasRemediation,
    execInfo,
    personInfo,
    businessFail,
    chainItems,
    auditRows,
    timelineView,
    gateRules,
    evidenceItems,
    proofIdDisplay,
    hashDisplay,
    vpath,
    gitpegStatus,
    lineageMerkle,
    gitpegMessage,
    anchorRef,
    handleDownloadDsp,
    handleLineageDepthChange,
    openSpecModal,
    closeSpecModal,
    toggleAudit,
    toggleRectify,
  } = vm

  if (loading) {
    return (
      <div className="loading">
        <div className="loading-ring" />
        <div className="loading-text">正在验证 Proof...</div>
      </div>
    )
  }

  if (error || !payload) {
    return (
      <div className="loading">
        <div className="error-card">
          <div className="error-title">验证失败</div>
          <div className="error-text">{error || '未获取到验证数据'}</div>
        </div>
      </div>
    )
  }

  return (
    <>
      <div className="status-bar">
        <div className={`status-icon ${hashVerified ? 'ok' : 'fail'}`}>{hashVerified ? 'OK' : '!'}</div>
        <div className={`status-text ${hashVerified ? 'ok' : 'fail'}`}>
          {hashVerified ? '哈希校验通过 / 主权可验证' : '哈希校验失败 / 数据异常'}
        </div>
        <div className={`status-badge ${hashVerified ? '' : 'fail'}`}>{hashVerified ? 'VERIFIED' : 'HASH FAIL'}</div>
      </div>

      <div className={`wrap ${traceMode ? 'trace-mode' : ''}`}>
        <div className="proof-id-card">
          <div className="pic-label">Proof ID</div>
          <div className="pic-id">{proofIdDisplay}</div>
          <div className="pic-hash">{hashDisplay}</div>
          <div className={`verify-stamp ${hashVerified ? 'pass' : 'fail'}`}>
            {hashVerified ? '验证通过' : '校验异常'}
          </div>
        </div>

        <div className={`result-card ${businessFail ? 'fail' : 'pass'}`}>
          <div className="rc-icon">{businessFail ? 'FAIL' : 'PASS'}</div>
          <div>
            <div className={`rc-title ${businessFail ? 'fail' : 'pass'}`}>
              业务结论：{businessFail ? '不合格' : '合格'}
            </div>
            <div className="rc-sub">
              {businessFail
                ? '当前业务判定为不合格，系统已进入红色预警态。'
                : '当前业务判定为合格，链路追溯结果完整。'}
            </div>
            <div className="result-actions">
              {businessFail ? (
                <button type="button" className="result-btn warn" onClick={toggleRectify}>
                  {showRectify ? '收起整改链路' : '查看整改链路'}
                </button>
              ) : null}
              <button type="button" className="result-btn" onClick={handleDownloadDsp} disabled={downloadingDsp}>
                {downloadingDsp ? '正在打包...' : '下载 DSP 包'}
              </button>
            </div>
            {businessFail ? (
              <div className="result-action-id">
                Action Item: {summary.action_item_id || remediation.issue_id || '-'}
              </div>
            ) : null}
          </div>
        </div>

        <div className="info-card">
          <div className="ic-header"><span className="ic-icon">执行</span><span className="ic-title">执行信息</span></div>
          <div className="ic-body">
            <div className="ic-row"><span className="ic-key">检测项目</span><span className="ic-val">{execInfo.testType}</span></div>
            <div className="ic-row"><span className="ic-key">桩号位置</span><span className="ic-val blue">{execInfo.stake}</span></div>
            <div className="ic-row"><span className="ic-key">实测值</span><span className={`ic-val ${businessFail ? '' : 'green'}`} style={businessFail ? { color: 'var(--red)' } : undefined}>{execInfo.value}</span></div>
            <div className="ic-row"><span className="ic-key">标准值</span><span className="ic-val">{execInfo.standard}</span></div>
            <div className="ic-row"><span className="ic-key">偏差百分比</span><span className={`ic-val ${Number(summary.deviation_percent) > 0 ? '' : 'green'}`} style={Number(summary.deviation_percent) > 0 ? { color: 'var(--red)' } : undefined}>{typeof summary.deviation_percent === 'number' ? `${summary.deviation_percent > 0 ? '+' : ''}${summary.deviation_percent.toFixed(2)}%` : '-'}</span></div>
            <div className="ic-row"><span className="ic-key">规范地址</span><span className="ic-val blue">{execInfo.norm}</span></div>
          </div>
        </div>

        <div className="info-card">
          <div className="ic-header"><span className="ic-icon">证据</span><span className="ic-title">原始物证</span></div>
          <div className="ic-body">
            {evidenceItems.length ? (
              <div className="evidence-grid">
                {evidenceItems.map((ev, idx) => {
                  const mediaType = String(ev.media_type || '').toLowerCase()
                  const isImage = mediaType === 'image'
                  const isVideo = mediaType === 'video'
                  const hashOk = ev.hash_matched === true
                  const url = String(ev.url || '')
                  const lat = ev.geo_location?.lat
                  const lng = ev.geo_location?.lng
                  const geoText = lat !== undefined && lng !== undefined ? `${lat}, ${lng}` : '-'
                  const ntpFingerprint = ev.server_timestamp_proof?.timestamp_fingerprint || ev.spatiotemporal_anchor_hash || '-'

                  return (
                    <div className="evidence-item" key={`${ev.id || ev.proof_id || ev.file_name || 'evidence'}-${idx}`}>
                      <div className="evidence-preview">
                        {isImage && url ? <img src={url} alt={String(ev.file_name || 'evidence')} loading="lazy" /> : null}
                        {isVideo && url ? <video src={url} controls preload="metadata" /> : null}
                        {!url ? <div className="evidence-empty">无预览</div> : null}
                      </div>
                      <div className="evidence-name">{ev.file_name || '-'}</div>
                      <div className={`evidence-hash-badge ${hashOk ? 'ok' : 'pending'}`}>
                        {ev.hash_match_text || (hashOk ? '文件哈希已匹配' : '文件哈希待校验')}
                      </div>
                      <div className="evidence-hash">sha256: {ev.evidence_hash || '-'}</div>
                      <div className="evidence-meta">
                        <span>{formatTimestamp(ev.time)}</span>
                        <span>{ev.proof_id || '-'}</span>
                        <span>GPS: {geoText}</span>
                        <span>NTP: {ntpFingerprint}</span>
                      </div>
                    </div>
                  )
                })}
              </div>
            ) : (
              <div className="empty-note">暂无关联物证</div>
            )}
          </div>
        </div>

        <div className="info-card">
          <div className="ic-header"><span className="ic-icon">时间</span><span className="ic-title">追溯时间轴</span></div>
          <div className="ic-body">
            {timelineView.map((node, idx) => {
              const status = normalizeStatusToken(String(node.status || 'pending'))
              return (
                <div className={`timeline-node ${status} ${traceMode ? 'trace-step' : ''} ${node.from_remediation ? 'remediation-append' : ''}`} style={{ ['--trace-order' as string]: idx + 1 }} key={`${node.step}-${node.title}-${idx}`}>
                  <div className="timeline-head">
                    <span className={`timeline-dot ${status}`} />
                    <span className="timeline-title">{chainIcon(String(node.type || 'proof'))} {node.title || '节点'}</span>
                    <span className="timeline-time">{formatTimestamp(node.time)}</span>
                  </div>
                  <div className="timeline-desc">{node.description || '-'}</div>
                  <div className="timeline-meta">执行体：{node.executor || '-'}</div>
                  {node.proof_id ? <div className="timeline-meta">Proof: {node.proof_id}</div> : null}
                  {node.spec_uri ? (
                    <div className="timeline-spec-wrap">
                      <button type="button" className="timeline-spec-link" onClick={() => openSpecModal(node)}>
                        {node.spec_uri}
                      </button>
                      <div className="timeline-spec-tooltip">{node.spec_excerpt || '规范摘要暂未提供'}</div>
                    </div>
                  ) : null}
                </div>
              )
            })}
          </div>
        </div>

        {businessFail && showRectify ? (
          <div className="info-card">
            <div className="ic-header"><span className="ic-icon">整改</span><span className="ic-title">整改闭环追溯</span></div>
            <div className="ic-body">
              <div className="ic-row"><span className="ic-key">整改单</span><span className="ic-val blue">{remediation.issue_id || '-'}</span></div>
              <div className="ic-row"><span className="ic-key">整改状态</span><span className={`ic-val ${hasRemediation ? 'green' : ''}`} style={!hasRemediation ? { color: 'var(--red)' } : undefined}>{hasRemediation ? '已关联后续记录' : '未发现后续整改记录'}</span></div>
              <div className="ic-row"><span className="ic-key">复检合格 Proof</span><span className="ic-val">{remediation.latest_pass_proof_id || '-'}</span></div>
              {hasRemediation ? (
                <div className="rectify-list">
                  {remediationRecords.map((rec, idx) => {
                    const fail = String(rec.result || '').toUpperCase() === 'FAIL'
                    return (
                      <div className={`rectify-item ${fail ? 'fail' : 'pass'}`} key={`${rec.proof_id}-${idx}`}>
                        <div className="rectify-head">
                          <span>{rec.proof_type || '整改记录'}</span>
                          <span>{formatTimestamp(rec.time)}</span>
                        </div>
                        <div className="rectify-desc">{rec.description || '-'}</div>
                        <div className="rectify-meta">{rec.executor || '-'} / {rec.proof_id || '-'}</div>
                      </div>
                    )
                  })}
                </div>
              ) : null}
            </div>
          </div>
        ) : null}

        <div className="info-card">
          <div className="ic-header"><span className="ic-icon">人员</span><span className="ic-title">执行人</span></div>
          <div className="ic-body">
            <div className="ic-row"><span className="ic-key">检测人员</span><span className="ic-val green">{personInfo.name}</span></div>
            <div className="ic-row"><span className="ic-key">执行体节点</span><span className="ic-val blue">{personInfo.uri}</span></div>
            <div className="ic-row"><span className="ic-key">DTORole</span><span className="ic-val">{personInfo.role}</span></div>
            <div className="ic-row"><span className="ic-key">执行时间</span><span className="ic-val">{personInfo.time}</span></div>
            <div className="ic-row"><span className="ic-key">OrdoSign</span><span className="ic-val orange">{personInfo.sign}</span></div>
          </div>
        </div>

        <div className="chain-card">
          <div className="ic-header"><span className="ic-icon">Chain</span><span className="ic-title">Proof Chain</span></div>
          <div>
            {chainItems.map((step, idx) => (
              <div className={`chain-step ${step.current ? 'current' : ''} ${traceMode ? 'trace-step' : ''}`} style={{ ['--trace-order' as string]: idx + 1 }} key={`${step.proof}-${idx}`}>
                <div className={`cs-dot ${step.status}`} />
                <div className="cs-content">
                  <div className={`cs-type ${step.status}`}>
                    {chainIcon(step.type)} {step.label}
                    {step.current ? <span className="cs-current">当前</span> : null}
                  </div>
                  <div className="cs-meta">{step.actor} / {step.time}</div>
                  <div className="cs-proof">{step.proof}</div>
                </div>
                <div className="cs-arrow">-&gt;</div>
              </div>
            ))}
          </div>
        </div>

        <div className="info-card">
          <div className="ic-header"><span className="ic-icon">Gate</span><span className="ic-title">QCGate 规则执行</span></div>
          <div className="ic-body">
            <div className="ic-row"><span className="ic-key">Gate</span><span className="ic-val">{qcgate.gate_id || '-'}</span></div>
            <div className="ic-row"><span className="ic-key">状态</span><span className={`ic-val ${String(qcgate.status || '').toUpperCase() === 'FAIL' ? '' : 'green'}`} style={String(qcgate.status || '').toUpperCase() === 'FAIL' ? { color: 'var(--red)' } : undefined}>{qcgate.status || '-'}</span></div>
            <div className="ic-row"><span className="ic-key">通过策略</span><span className="ic-val">{qcgate.pass_policy || 'all_pass'}</span></div>
            <div className="ic-row"><span className="ic-key">规则数</span><span className="ic-val">{qcgate.rule_count ?? gateRules.length}</span></div>
            <div className="ic-row"><span className="ic-key">哈希一致性</span><span className={`ic-val ${gateHashOk ? 'green' : ''}`} style={!gateHashOk ? { color: 'var(--red)' } : undefined}>{gateHashOk ? '全部通过' : '存在异常'}</span></div>
            <div className="gate-rules-wrap">
              <table className="gate-rules-table">
                <thead>
                  <tr>
                    <th>Rule</th>
                    <th>Spec</th>
                    <th>Operator</th>
                    <th>Threshold</th>
                    <th>Measured</th>
                    <th>Result</th>
                    <th>ProofHash</th>
                    <th>Hash</th>
                  </tr>
                </thead>
                <tbody>
                  {gateRules.map((rule, idx) => {
                    const fail = String(rule.result || '').toUpperCase() === 'FAIL'
                    const hasHash = Boolean(String(rule.proof_hash || '').trim())
                    const hashOk = rule.hash_valid === true
                    return (
                      <tr key={`${rule.rule_id}-${idx}`} className={fail ? 'gate-rule-fail-row' : ''}>
                        <td className="audit-mono">{rule.rule_id || '-'}</td>
                        <td className="audit-mono">{rule.spec_uri || '-'}</td>
                        <td>{rule.operator || '-'}</td>
                        <td>{rule.threshold || '-'}</td>
                        <td>{rule.measured || '-'}</td>
                        <td className={fail ? 'audit-fail' : 'audit-pass'}>
                          {rule.result || '-'}{typeof rule.deviation_percent === 'number' ? ` (${rule.deviation_percent > 0 ? '+' : ''}${rule.deviation_percent.toFixed(2)}%)` : ''}
                        </td>
                        <td className="audit-mono">{rule.proof_hash || '-'}</td>
                        <td className={hasHash ? (hashOk ? 'audit-pass' : 'audit-fail') : ''}>{hasHash ? (hashOk ? 'OK' : 'FAIL') : '-'}</td>
                      </tr>
                    )
                  })}
                </tbody>
              </table>
            </div>
          </div>
        </div>

        <div className="info-card">
          <div className="ic-header"><span className="ic-icon">Audit</span><span className="ic-title">链审计详情</span></div>
          <div className="ic-body">
            <button type="button" className="audit-toggle" onClick={toggleAudit}>
              {showAudit ? '收起审计表' : '展开审计表'}
            </button>
            {showAudit ? (
              <div className="audit-table-wrap">
                <table className="audit-table">
                  <thead>
                    <tr>
                      <th>#</th>
                      <th>Proof ID</th>
                      <th>Result</th>
                      <th>Parent ID</th>
                      <th>Type</th>
                      <th>ProofType</th>
                      <th>SpecIR</th>
                      <th>ProofHash</th>
                      <th>Hash</th>
                      <th>时间</th>
                    </tr>
                  </thead>
                  <tbody>
                    {auditRows.map((row, idx) => {
                      const fail = String(row.result || '').toUpperCase() === 'FAIL'
                      const hasHash = Boolean(String(row.proof_hash || '').trim())
                      const hashOk = row.hash_valid === true
                      return (
                        <tr key={`${row.proof_id}-${idx}`} className={fail ? 'audit-fail-row' : ''}>
                          <td>{row.index || idx + 1}</td>
                          <td className="audit-mono">{row.proof_id || '-'}</td>
                          <td className={fail ? 'audit-fail' : 'audit-pass'}>{row.result || '-'}</td>
                          <td className="audit-mono">{row.parent || '-'}</td>
                          <td>{row.type || '-'}</td>
                          <td>{row.proof_type || '-'}</td>
                          <td className="audit-mono">{row.spec_uri || '-'}</td>
                          <td className="audit-mono">{row.proof_hash || '-'}</td>
                          <td className={hasHash ? (hashOk ? 'audit-pass' : 'audit-fail') : ''}>{hasHash ? (hashOk ? 'OK' : 'FAIL') : '-'}</td>
                          <td>{row.time || '-'}</td>
                        </tr>
                      )
                    })}
                  </tbody>
                </table>
              </div>
            ) : null}
          </div>
        </div>

        <div className="vpath-box">
          <span className="vb-pre">v://</span>
          <span className="vb-uri">{vpath}</span>
          <span className="vb-ok">{gitpegStatus.anchored ? '已锚定' : '待锚定'}</span>
        </div>

        <div className="info-card">
          <div className="ic-header"><span className="ic-icon">Peg</span><span className="ic-title">GitPeg 锚定信息</span></div>
          <div className="ic-body">
            <div className="ic-row">
              <span className="ic-key">血缘穿透深度</span>
              <span className="ic-val">
                <select
                  className="lineage-depth-select"
                  value={lineageDepth}
                  onChange={(e) => handleLineageDepthChange(e.target.value as 'item' | 'unit' | 'project')}
                >
                  <option value="item">Item 级</option>
                  <option value="unit">Unit 级</option>
                  <option value="project">Project 级</option>
                </select>
              </span>
            </div>
            <div className="ic-row"><span className="ic-key">锚定状态</span><span className={`ic-val ${gitpegStatus.anchored ? 'green' : ''}`}>{gitpegMessage || '已在本地存证，等待全局锚定'}</span></div>
            <div className="ic-row"><span className="ic-key">锚定引用</span><span className="ic-val blue">{anchorRef}</span></div>
            <div className="ic-row"><span className="ic-key">Merkle 根</span><span className="ic-val">{gitpegStatus.merkle_root || '-'}</span></div>
            <div className="ic-row"><span className="ic-key">Unit Root</span><span className="ic-val">{lineageMerkle.unit_root_hash || '-'}</span></div>
            <div className="ic-row"><span className="ic-key">Project Root</span><span className="ic-val">{lineageMerkle.project_root_hash || lineageMerkle.global_project_fingerprint || '-'}</span></div>
            <div className="ic-row"><span className="ic-key">Unit Code</span><span className="ic-val">{lineageMerkle.resolved_unit_code || '-'}</span></div>
            <div className="ic-row"><span className="ic-key">叶子索引</span><span className="ic-val">{typeof lineageMerkle.item_index === 'number' ? lineageMerkle.item_index : '-'}</span></div>
            <div className="ic-row"><span className="ic-key">Unit 叶子数</span><span className="ic-val">{lineageMerkle.leaf_count ?? '-'}</span></div>
            <div className="ic-row"><span className="ic-key">三维锚定</span><span className="ic-val">{context.project_uri || '-'} | {context.segment_uri || '-'} | {context.executor_uri || '-'}</span></div>
            <div className="ic-row"><span className="ic-key">源头要求</span><span className="ic-val">{context.contract_uri || '-'} | {context.design_uri || '-'}</span></div>
            <div className="ic-row"><span className="ic-key">重算 Hash</span><span className="ic-val">{hashState.computed || payload.hash_verification?.recomputed_hash || '-'}</span></div>
          </div>
        </div>

        <div className="footer-card">
          <div className="fc-brand">QCSpec / coordOS</div>
          <div className="fc-sub">
            本验证页由 GitPeg v:// 主权协议驱动
            <br />
            Proof Hash 不可篡改 / 链上永久存证
          </div>
          <a className="fc-btn" href={payload.verify_url || '/'}>进入项目控制台</a>
        </div>
      </div>

      {specModal ? (
        <div className="spec-modal-mask" role="presentation" onClick={closeSpecModal}>
          <div className="spec-modal" role="dialog" aria-modal="true" onClick={(e) => e.stopPropagation()}>
            <div className="spec-modal-head">
              <div className="spec-modal-title">{specModal.title || '规范条文摘要'}</div>
              <button type="button" className="spec-modal-close" onClick={closeSpecModal}>关闭</button>
            </div>
            <div className="spec-modal-uri">{specModal.uri}</div>
            <div className="spec-modal-content">{specModal.excerpt || '规范摘要暂未提供'}</div>
            {specModal.source ? <div className="spec-modal-source">规则来源: {specModal.source}</div> : null}
          </div>
        </div>
      ) : null}
    </>
  )
}
