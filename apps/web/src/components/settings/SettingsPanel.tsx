import type {
  ErpDraftState,
  ErpWritebackDraftState,
  SettingsState,
} from '../../app/appShellShared'
import type {
  EnterpriseInfoState,
  GitpegVerifyMessage,
  PersistSettingsPayload,
  WebhookResultState,
} from '../../app/settingsTypes'

interface SettingsPanelProps {
  enterpriseInfo: EnterpriseInfoState
  setEnterpriseInfo: React.Dispatch<React.SetStateAction<EnterpriseInfoState>>
  persistEnterpriseInfo: () => void
  settings: SettingsState
  setSettings: React.Dispatch<React.SetStateAction<SettingsState>>
  persistSettings: (payload: PersistSettingsPayload) => void
  setReportTemplateFile: (file: File | null) => void
  persistReportTemplate: () => void
  verifyGitpegToken: () => void
  gitpegVerifying: boolean
  gitpegVerifyMsg: GitpegVerifyMessage
  setGitpegVerifyMsg: React.Dispatch<React.SetStateAction<GitpegVerifyMessage>>
  setGitpegVerifying: (value: boolean) => void
  erpDraft: ErpDraftState
  setErpDraft: React.Dispatch<React.SetStateAction<ErpDraftState>>
  testErpConnection: () => void
  erpTesting: boolean
  erpTestMsg: string
  erpWritebackDraft: ErpWritebackDraftState
  setErpWritebackDraft: React.Dispatch<React.SetStateAction<ErpWritebackDraftState>>
  testWebhook: () => void
  webhookTesting: boolean
  webhookResult: WebhookResultState
}

export default function SettingsPanel({
  enterpriseInfo,
  setEnterpriseInfo,
  persistEnterpriseInfo,
  settings,
  setSettings,
  persistSettings,
  setReportTemplateFile,
  persistReportTemplate,
  verifyGitpegToken,
  gitpegVerifying,
  gitpegVerifyMsg,
  setGitpegVerifyMsg,
  setGitpegVerifying,
  erpDraft,
  setErpDraft,
  testErpConnection,
  erpTesting,
  erpTestMsg,
  erpWritebackDraft,
  setErpWritebackDraft,
  testWebhook,
  webhookTesting,
  webhookResult,
}: SettingsPanelProps) {
  return (
    <div className="settings-grid">
      <div className="settings-section">
        <div className="settings-title">🏢 企业信息</div>
        <div style={{ display: 'grid', gap: 8 }}>
          <input className="setting-input" value={enterpriseInfo.name} onChange={(e) => setEnterpriseInfo({ ...enterpriseInfo, name: e.target.value })} placeholder="企业名称" />
          <input className="setting-input" value={enterpriseInfo.vUri} onChange={(e) => setEnterpriseInfo({ ...enterpriseInfo, vUri: e.target.value })} placeholder="v:// 企业根节点" style={{ fontFamily: 'var(--mono)' }} />
          <input className="setting-input" value={enterpriseInfo.creditCode} onChange={(e) => setEnterpriseInfo({ ...enterpriseInfo, creditCode: e.target.value })} placeholder="统一社会信用代码（可选）" />
          <input className="setting-input" value={enterpriseInfo.adminEmail} readOnly />
        </div>
        <div style={{ marginTop: 10 }}>
          <button className="btn-primary" style={{ flex: 'none' }} onClick={persistEnterpriseInfo}>保存企业信息</button>
        </div>
      </div>

      <div className="settings-section">
        <div className="settings-title">🔔 通知设置</div>
        <div className="toggle-row">
          <span className="toggle-label">邮件通知</span>
          <input type="checkbox" checked={settings.emailNotify} onChange={(e) => setSettings({ ...settings, emailNotify: e.target.checked })} />
        </div>
        <div className="toggle-row">
          <span className="toggle-label">自动生成报告</span>
          <input type="checkbox" checked={settings.autoGenerateReport} onChange={(e) => setSettings({ ...settings, autoGenerateReport: e.target.checked })} />
        </div>
        <div className="toggle-row">
          <span className="toggle-label">强制 Proof 存证</span>
          <input type="checkbox" checked={settings.strictProof} onChange={(e) => setSettings({ ...settings, strictProof: e.target.checked })} />
        </div>
        <div style={{ marginTop: 10 }}>
          <button
            className="btn-primary"
            style={{ flex: 'none' }}
            onClick={() => persistSettings({
              emailNotify: settings.emailNotify,
              autoGenerateReport: settings.autoGenerateReport,
              strictProof: settings.strictProof,
            })}
          >
            保存通知设置
          </button>
        </div>
      </div>

      <div className="settings-section">
        <div className="settings-title">📄 报告模板</div>
        <div style={{ display: 'grid', gap: 8 }}>
          <select className="setting-select" value={settings.reportTemplate} onChange={(e) => setSettings({ ...settings, reportTemplate: e.target.value })}>
            <option>default.docx</option>
            <option>highway-monthly.docx</option>
            <option>bridge-inspection.docx</option>
            <option value="custom-upload">自定义模板（上传Word）</option>
            {!['default.docx', 'highway-monthly.docx', 'bridge-inspection.docx', 'custom-upload'].includes(settings.reportTemplate) && (
              <option value={settings.reportTemplate}>{settings.reportTemplate}</option>
            )}
          </select>
          {settings.reportTemplate === 'custom-upload' && (
            <input type="file" accept=".doc,.docx" onChange={(e) => setReportTemplateFile(e.target.files?.[0] || null)} className="setting-input" />
          )}
          <input className="setting-input" value={settings.reportHeader} onChange={(e) => setSettings({ ...settings, reportHeader: e.target.value })} placeholder="报告抬头（例如：XX工程有限公司）" />
          {settings.reportTemplateUrl && (
            <a href={settings.reportTemplateUrl} target="_blank" rel="noreferrer" style={{ fontSize: 12, color: '#1A56DB', textDecoration: 'none' }}>
              查看当前模板文件
            </a>
          )}
          <div className="setting-note">数字签章：后续版本将接入 QCPeg / SealPeg 协议，支持报告自动签章与验签。</div>
          <button className="btn-primary" style={{ flex: 'none' }} onClick={persistReportTemplate}>保存模板设置</button>
        </div>
      </div>

      <div className="settings-section">
        <div className="settings-title">🔗 系统集成</div>
        <div style={{ display: 'grid', gap: 0 }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: 12, padding: '10px 0', borderBottom: '1px solid #E2E8F0' }}>
            <div style={{ fontSize: 20, width: 28, textAlign: 'center' }}>⚡</div>
            <div style={{ flex: 1 }}>
              <div style={{ display: 'flex', alignItems: 'center', gap: 6, marginBottom: 2 }}>
                <div style={{ fontSize: 13, fontWeight: 700, color: '#0F172A' }}>GitPeg v:// Proof 存证</div>
                <span style={{
                  fontSize: 12,
                  fontWeight: 700,
                  borderRadius: 10,
                  padding: '2px 8px',
                  background: settings.gitpegEnabled ? '#ECFDF5' : '#F8FAFC',
                  color: settings.gitpegEnabled ? '#059669' : '#64748B',
                }}>
                  {settings.gitpegEnabled ? '已启用' : '未接入'}
                </span>
              </div>
              <div style={{ fontSize: 12, color: '#64748B' }}>质检记录自动推送到 GitPeg v:// 链，不可篡改存证</div>
            </div>
            <input
              type="checkbox"
              checked={settings.gitpegEnabled}
              onChange={(e) => {
                setSettings({ ...settings, gitpegEnabled: e.target.checked })
                if (!e.target.checked) {
                  setGitpegVerifyMsg({ text: '', color: '#64748B' })
                  setGitpegVerifying(false)
                }
              }}
            />
          </div>
          {settings.gitpegEnabled && (
            <div style={{ padding: '0 0 10px 40px' }}>
              <div style={{ background: '#F8FAFC', border: '1px solid #E2E8F0', borderRadius: 8, padding: 12 }}>
                <div style={{ fontSize: 12, fontWeight: 700, color: '#334155', marginBottom: 8 }}>GitPeg 连接配置</div>
                <div style={{ display: 'grid', gap: 8 }}>
                  <input
                    className="setting-input"
                    value={settings.gitpegToken}
                    onChange={(e) => setSettings({ ...settings, gitpegToken: e.target.value })}
                    placeholder="可选：兼容模式 Token（官方 Partner 接口可留空）"
                    type="password"
                    style={{ fontFamily: 'var(--mono)' }}
                  />
                  <input className="setting-input" value={enterpriseInfo.vUri} readOnly style={{ fontFamily: 'var(--mono)', color: '#1A56DB' }} />
                  <input
                    className="setting-input"
                    value={settings.gitpegRegistrarBaseUrl}
                    onChange={(e) => setSettings({ ...settings, gitpegRegistrarBaseUrl: e.target.value })}
                    placeholder="GitPeg Registrar Base URL（例如：https://gitpeg.cn）"
                    style={{ fontFamily: 'var(--mono)' }}
                  />
                  <input
                    className="setting-input"
                    value={settings.gitpegPartnerCode}
                    onChange={(e) => setSettings({ ...settings, gitpegPartnerCode: e.target.value })}
                    placeholder="Partner Code（例如：wastewater-site）"
                    style={{ fontFamily: 'var(--mono)' }}
                  />
                  <input
                    className="setting-input"
                    value={settings.gitpegIndustryCode}
                    onChange={(e) => setSettings({ ...settings, gitpegIndustryCode: e.target.value })}
                    placeholder="Industry Code（例如：wastewater）"
                    style={{ fontFamily: 'var(--mono)' }}
                  />
                  <input
                    className="setting-input"
                    value={settings.gitpegClientId}
                    onChange={(e) => setSettings({ ...settings, gitpegClientId: e.target.value })}
                    placeholder="Client ID（例如：ptn_wastewater_001）"
                    style={{ fontFamily: 'var(--mono)' }}
                  />
                  <input
                    className="setting-input"
                    value={settings.gitpegClientSecret}
                    onChange={(e) => setSettings({ ...settings, gitpegClientSecret: e.target.value })}
                    placeholder="Client Secret"
                    type="password"
                    style={{ fontFamily: 'var(--mono)' }}
                  />
                  <select
                    className="setting-select"
                    value={settings.gitpegRegistrationMode}
                    onChange={(e) => setSettings({ ...settings, gitpegRegistrationMode: e.target.value })}
                  >
                    <option value="DOMAIN">DOMAIN</option>
                    <option value="SHELL">SHELL</option>
                  </select>
                  <input
                    className="setting-input"
                    value={settings.gitpegReturnUrl}
                    onChange={(e) => setSettings({ ...settings, gitpegReturnUrl: e.target.value })}
                    placeholder="Return URL（GitPeg 回跳地址）"
                    style={{ fontFamily: 'var(--mono)' }}
                  />
                  <input
                    className="setting-input"
                    value={settings.gitpegWebhookUrl}
                    onChange={(e) => setSettings({ ...settings, gitpegWebhookUrl: e.target.value })}
                    placeholder="Webhook URL（GitPeg 回调到 QCSpec）"
                    style={{ fontFamily: 'var(--mono)' }}
                  />
                  <input
                    className="setting-input"
                    value={settings.gitpegWebhookSecret}
                    onChange={(e) => setSettings({ ...settings, gitpegWebhookSecret: e.target.value })}
                    placeholder="Webhook Secret（用于 X-Gitpeg-Signature HMAC-SHA256 校验）"
                    type="password"
                    style={{ fontFamily: 'var(--mono)' }}
                  />
                  <input
                    className="setting-input"
                    value={(settings.gitpegModuleCandidates || []).join(',')}
                    onChange={(e) => setSettings({
                      ...settings,
                      gitpegModuleCandidates: e.target.value
                        .split(',')
                        .map((item) => item.trim())
                        .filter(Boolean),
                    })}
                    placeholder="Module Candidates（逗号分隔：proof,utrip,openapi）"
                    style={{ fontFamily: 'var(--mono)' }}
                  />
                  <button className="btn-primary" style={{ flex: 'none' }} onClick={verifyGitpegToken} disabled={gitpegVerifying}>
                    {gitpegVerifying ? '验证中...' : '验证'}
                  </button>
                  {gitpegVerifyMsg.text && (
                    <div style={{ fontSize: 12, color: gitpegVerifyMsg.color }}>{gitpegVerifyMsg.text}</div>
                  )}
                </div>
              </div>
            </div>
          )}

          <div style={{ display: 'flex', alignItems: 'center', gap: 12, padding: '10px 0', borderBottom: '1px solid #E2E8F0' }}>
            <div style={{ fontSize: 20, width: 28, textAlign: 'center' }}>📊</div>
            <div style={{ flex: 1 }}>
              <div style={{ display: 'flex', alignItems: 'center', gap: 6, marginBottom: 2 }}>
                <div style={{ fontSize: 13, fontWeight: 700, color: '#0F172A' }}>ERPNext 数据同步</div>
                <span style={{
                  fontSize: 12,
                  fontWeight: 700,
                  borderRadius: 10,
                  padding: '2px 8px',
                  background: settings.erpnextSync ? '#ECFDF5' : '#F8FAFC',
                  color: settings.erpnextSync ? '#059669' : '#64748B',
                }}>
                  {settings.erpnextSync ? '已启用' : '未接入'}
                </span>
              </div>
              <div style={{ fontSize: 12, color: '#64748B' }}>与 ERPNext 系统同步，质检合格才能计量</div>
            </div>
            <input type="checkbox" checked={settings.erpnextSync} onChange={(e) => setSettings({ ...settings, erpnextSync: e.target.checked })} />
          </div>
          {settings.erpnextSync && (
            <div style={{ padding: '0 0 10px 40px' }}>
              <div style={{ background: '#F8FAFC', border: '1px solid #E2E8F0', borderRadius: 8, padding: 12 }}>
                <div style={{ fontSize: 12, fontWeight: 700, color: '#334155', marginBottom: 8 }}>ERPNext 连接配置</div>
                <div style={{ display: 'grid', gap: 8 }}>
                  <input
                    className="setting-input"
                    value={erpDraft.url}
                    onChange={(e) => setErpDraft((prev) => ({ ...prev, url: e.target.value }))}
                    placeholder="http://development.localhost:8000"
                    style={{ fontFamily: 'var(--mono)' }}
                  />
                  <input
                    className="setting-input"
                    value={erpDraft.siteName}
                    onChange={(e) => setErpDraft((prev) => ({ ...prev, siteName: e.target.value }))}
                    placeholder="development.localhost（可选）"
                    style={{ fontFamily: 'var(--mono)' }}
                  />
                  <input
                    className="setting-input"
                    value={erpDraft.apiKey}
                    onChange={(e) => setErpDraft((prev) => ({ ...prev, apiKey: e.target.value }))}
                    placeholder="API Key 或 token key:secret"
                    type="password"
                  />
                  <input
                    className="setting-input"
                    value={erpDraft.apiSecret}
                    onChange={(e) => setErpDraft((prev) => ({ ...prev, apiSecret: e.target.value }))}
                    placeholder="API Secret（若上面填 key:secret 可留空）"
                    type="password"
                  />
                  <input
                    className="setting-input"
                    value={erpDraft.username}
                    onChange={(e) => setErpDraft((prev) => ({ ...prev, username: e.target.value }))}
                    placeholder="用户名（可选，用于 session 测试）"
                  />
                  <input
                    className="setting-input"
                    value={erpDraft.password}
                    onChange={(e) => setErpDraft((prev) => ({ ...prev, password: e.target.value }))}
                    placeholder="密码（可选，用于 session 测试）"
                    type="password"
                  />
                  <button className="btn-primary" style={{ flex: 'none' }} onClick={testErpConnection} disabled={erpTesting}>
                    {erpTesting ? '测试中...' : '测试连接'}
                  </button>
                  {erpTestMsg && <div style={{ fontSize: 12, color: erpTestMsg.includes('✅') ? '#059669' : '#D97706' }}>{erpTestMsg}</div>}
                  <div style={{ fontSize: 12, color: '#64748B' }}>
                    推荐先用 API Key/Secret；若本地 `frappe-bench` 仅有账号密码，可填写用户名/密码测试。
                  </div>
                  <div style={{ marginTop: 8, paddingTop: 8, borderTop: '1px dashed #CBD5E1', fontSize: 12, color: '#334155', fontWeight: 700 }}>
                    ERP 回写映射（Project on_submit 同步）
                  </div>
                  <input
                    className="setting-input"
                    value={erpWritebackDraft.projectDoctype}
                    onChange={(e) => setErpWritebackDraft((prev) => ({ ...prev, projectDoctype: e.target.value }))}
                    placeholder="ERP Project Doctype（默认 Project）"
                  />
                  <input
                    className="setting-input"
                    value={erpWritebackDraft.projectLookupField}
                    onChange={(e) => setErpWritebackDraft((prev) => ({ ...prev, projectLookupField: e.target.value }))}
                    placeholder="查找字段（默认 name，可改 custom 字段）"
                  />
                  <input
                    className="setting-input"
                    value={erpWritebackDraft.projectLookupValue}
                    onChange={(e) => setErpWritebackDraft((prev) => ({ ...prev, projectLookupValue: e.target.value }))}
                    placeholder="固定查找值（可空；空时回退合同号/项目名）"
                  />
                  <input
                    className="setting-input"
                    value={erpWritebackDraft.gitpegProjectUriField}
                    onChange={(e) => setErpWritebackDraft((prev) => ({ ...prev, gitpegProjectUriField: e.target.value }))}
                    placeholder="回写字段：gitpeg_project_uri"
                  />
                  <input
                    className="setting-input"
                    value={erpWritebackDraft.gitpegSiteUriField}
                    onChange={(e) => setErpWritebackDraft((prev) => ({ ...prev, gitpegSiteUriField: e.target.value }))}
                    placeholder="回写字段：gitpeg_site_uri"
                  />
                  <input
                    className="setting-input"
                    value={erpWritebackDraft.gitpegStatusField}
                    onChange={(e) => setErpWritebackDraft((prev) => ({ ...prev, gitpegStatusField: e.target.value }))}
                    placeholder="回写字段：gitpeg_status"
                  />
                  <input
                    className="setting-input"
                    value={erpWritebackDraft.gitpegResultJsonField}
                    onChange={(e) => setErpWritebackDraft((prev) => ({ ...prev, gitpegResultJsonField: e.target.value }))}
                    placeholder="回写字段：gitpeg_register_result_json"
                  />
                  <input
                    className="setting-input"
                    value={erpWritebackDraft.gitpegRegistrationIdField}
                    onChange={(e) => setErpWritebackDraft((prev) => ({ ...prev, gitpegRegistrationIdField: e.target.value }))}
                    placeholder="回写字段：gitpeg_registration_id"
                  />
                  <input
                    className="setting-input"
                    value={erpWritebackDraft.gitpegNodeUriField}
                    onChange={(e) => setErpWritebackDraft((prev) => ({ ...prev, gitpegNodeUriField: e.target.value }))}
                    placeholder="回写字段：gitpeg_node_uri"
                  />
                  <input
                    className="setting-input"
                    value={erpWritebackDraft.gitpegShellUriField}
                    onChange={(e) => setErpWritebackDraft((prev) => ({ ...prev, gitpegShellUriField: e.target.value }))}
                    placeholder="回写字段：gitpeg_shell_uri"
                  />
                  <input
                    className="setting-input"
                    value={erpWritebackDraft.gitpegProofHashField}
                    onChange={(e) => setErpWritebackDraft((prev) => ({ ...prev, gitpegProofHashField: e.target.value }))}
                    placeholder="回写字段：gitpeg_proof_hash"
                  />
                  <input
                    className="setting-input"
                    value={erpWritebackDraft.gitpegIndustryProfileIdField}
                    onChange={(e) => setErpWritebackDraft((prev) => ({ ...prev, gitpegIndustryProfileIdField: e.target.value }))}
                    placeholder="回写字段：gitpeg_industry_profile_id"
                  />
                </div>
              </div>
            </div>
          )}

          <div style={{ display: 'flex', alignItems: 'center', gap: 12, padding: '10px 0' }}>
            <div style={{ fontSize: 20, width: 28, textAlign: 'center' }}>🚁</div>
            <div style={{ flex: 1 }}>
              <div style={{ display: 'flex', alignItems: 'center', gap: 6, marginBottom: 2 }}>
                <div style={{ fontSize: 13, fontWeight: 700, color: '#0F172A' }}>无人机数据接入</div>
                <span style={{
                  fontSize: 12,
                  fontWeight: 700,
                  borderRadius: 10,
                  padding: '2px 8px',
                  background: settings.droneImport ? '#ECFDF5' : '#FFFBEB',
                  color: settings.droneImport ? '#059669' : '#D97706',
                }}>
                  {settings.droneImport ? '已启用' : 'Beta'}
                </span>
              </div>
              <div style={{ fontSize: 12, color: '#64748B' }}>大疆无人机巡检数据自动接入质检系统</div>
            </div>
            <input type="checkbox" checked={settings.droneImport} onChange={(e) => setSettings({ ...settings, droneImport: e.target.checked })} />
          </div>
        </div>

        <div style={{ marginTop: 14, paddingTop: 14, borderTop: '1px solid #E2E8F0' }}>
          <div style={{ fontSize: 12, fontWeight: 700, color: '#334155', marginBottom: 8 }}>Webhook URL（可选）</div>
          <div style={{ display: 'flex', gap: 8, alignItems: 'center' }}>
            <input
              className="setting-input"
              value={settings.webhookUrl}
              onChange={(e) => setSettings({ ...settings, webhookUrl: e.target.value })}
              placeholder="https://your-server.com/qcspec/webhook"
              style={{ fontFamily: 'var(--mono)' }}
            />
            <button className="btn-secondary" style={{ padding: '10px 12px', whiteSpace: 'nowrap' }} onClick={testWebhook} disabled={webhookTesting}>
              {webhookTesting ? '发送中...' : '发送测试'}
            </button>
          </div>
          {webhookResult.visible && (
            <div style={{ marginTop: 6, fontSize: 12, color: webhookResult.color, fontFamily: 'var(--mono)' }}>
              {webhookResult.text}
            </div>
          )}
        </div>

        <div style={{ marginTop: 12 }}>
          <button
            className="btn-primary btn-green"
            style={{ flex: 'none' }}
            onClick={() =>
              persistSettings({
                webhookUrl: settings.webhookUrl,
                gitpegToken: settings.gitpegToken,
                gitpegEnabled: settings.gitpegEnabled,
                gitpegRegistrarBaseUrl: settings.gitpegRegistrarBaseUrl,
                gitpegPartnerCode: settings.gitpegPartnerCode,
                gitpegIndustryCode: settings.gitpegIndustryCode,
                gitpegClientId: settings.gitpegClientId,
                gitpegClientSecret: settings.gitpegClientSecret,
                gitpegRegistrationMode: settings.gitpegRegistrationMode,
                gitpegReturnUrl: settings.gitpegReturnUrl,
                gitpegWebhookUrl: settings.gitpegWebhookUrl,
                gitpegWebhookSecret: settings.gitpegWebhookSecret,
                gitpegModuleCandidates: settings.gitpegModuleCandidates,
                erpnextSync: settings.erpnextSync,
                erpnextUrl: erpDraft.url,
                erpnextSiteName: erpDraft.siteName,
                erpnextApiKey: erpDraft.apiKey,
                erpnextApiSecret: erpDraft.apiSecret,
                erpnextUsername: erpDraft.username,
                erpnextPassword: erpDraft.password,
                erpnextProjectDoctype: erpWritebackDraft.projectDoctype,
                erpnextProjectLookupField: erpWritebackDraft.projectLookupField,
                erpnextProjectLookupValue: erpWritebackDraft.projectLookupValue,
                erpnextGitpegProjectUriField: erpWritebackDraft.gitpegProjectUriField,
                erpnextGitpegSiteUriField: erpWritebackDraft.gitpegSiteUriField,
                erpnextGitpegStatusField: erpWritebackDraft.gitpegStatusField,
                erpnextGitpegResultJsonField: erpWritebackDraft.gitpegResultJsonField,
                erpnextGitpegRegistrationIdField: erpWritebackDraft.gitpegRegistrationIdField,
                erpnextGitpegNodeUriField: erpWritebackDraft.gitpegNodeUriField,
                erpnextGitpegShellUriField: erpWritebackDraft.gitpegShellUriField,
                erpnextGitpegProofHashField: erpWritebackDraft.gitpegProofHashField,
                erpnextGitpegIndustryProfileIdField: erpWritebackDraft.gitpegIndustryProfileIdField,
                droneImport: settings.droneImport,
              })
            }
          >
            保存配置
          </button>
        </div>
      </div>
    </div>
  )
}

