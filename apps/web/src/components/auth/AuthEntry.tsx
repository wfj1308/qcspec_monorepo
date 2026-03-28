import React from 'react'

interface LoginFormState {
  account: string
  pass: string
}

interface EnterpriseFormState {
  name: string
  adminPhone: string
  pass: string
  uscc: string
}

interface QuickLoginOption {
  key: string
  account: string
  password: string
  roleLabel: string
  desc: string
  profileName: string
}

interface AuthEntryProps {
  sessionChecking: boolean
  loginTab: 'login' | 'register'
  loginForm: LoginFormState
  loggingIn: boolean
  entForm: EnterpriseFormState
  quickLoginOptions: QuickLoginOption[]
  onSwitchTab: (tab: 'login' | 'register') => void
  onLoginFormChange: (next: LoginFormState) => void
  onEnterpriseFormChange: (next: EnterpriseFormState) => void
  onLogin: () => void
  onRegisterEnterprise: () => void
  onFillQuickLogin: (key: string) => void
  onQuickLoginNow: (key: string) => void
}

export default function AuthEntry({
  sessionChecking,
  loginTab,
  loginForm,
  loggingIn,
  entForm,
  quickLoginOptions,
  onSwitchTab,
  onLoginFormChange,
  onEnterpriseFormChange,
  onLogin,
  onRegisterEnterprise,
  onFillQuickLogin,
  onQuickLoginNow,
}: AuthEntryProps) {
  if (sessionChecking) {
    return (
      <div className="login-screen">
        <div className="login-card">
          <div className="l-hint">会话校验中...</div>
        </div>
      </div>
    )
  }

  return (
    <div className="login-screen">
      <div className="login-card">
        <div className="login-logo">
          <div className="login-brand">
            <span className="qc">QC</span>
            <span className="spec">Spec</span>
          </div>
          <div className="login-tagline">工程质检管理平台 | 企业注册中心</div>
        </div>

        <div className="login-tab">
          <button className={`ltab ${loginTab === 'login' ? 'active' : ''}`} onClick={() => onSwitchTab('login')}>
            登录
          </button>
          <button
            className={`ltab ${loginTab === 'register' ? 'active' : ''}`}
            onClick={() => onSwitchTab('register')}
          >
            注册企业
          </button>
        </div>

        {loginTab === 'login' && (
          <div className="login-form">
            <input
              className="l-input"
              value={loginForm.account}
              onChange={(e) => onLoginFormChange({ ...loginForm, account: e.target.value })}
              placeholder="手机号 / 邮箱"
            />
            <input
              className="l-input"
              type="password"
              value={loginForm.pass}
              onChange={(e) => onLoginFormChange({ ...loginForm, pass: e.target.value })}
              placeholder="密码"
            />
            <button className="l-btn" onClick={onLogin} disabled={loggingIn}>
              {loggingIn ? '登录中...' : '登录'}
            </button>
            <div className="l-hint">演示账号快速登录</div>
            <div className="demo-accounts">
              <div className="demo-title">Demo Accounts</div>
              {quickLoginOptions.map((item) => (
                <div className="demo-item" key={item.key}>
                  <div className="demo-line">
                    <strong>{item.account}</strong>
                    <span>{item.roleLabel}</span>
                  </div>
                  <div className="demo-subline">姓名：{item.profileName} · 密码：{item.password}</div>
                  <div className="demo-subline">{item.desc}</div>
                  <div className="demo-actions">
                    <button className="demo-btn demo-btn-ghost" onClick={() => onFillQuickLogin(item.key)}>
                      填充
                    </button>
                    <button className="demo-btn demo-btn-primary" onClick={() => onQuickLoginNow(item.key)}>
                      快捷登录
                    </button>
                  </div>
                </div>
              ))}
            </div>
          </div>
        )}

        {loginTab === 'register' && (
          <div className="login-form">
            <input
              className="l-input"
              value={entForm.name}
              onChange={(e) => onEnterpriseFormChange({ ...entForm, name: e.target.value })}
              placeholder="企业名称"
            />
            <input
              className="l-input"
              value={entForm.adminPhone}
              onChange={(e) => onEnterpriseFormChange({ ...entForm, adminPhone: e.target.value })}
              placeholder="管理员手机号（11位）"
            />
            <input
              className="l-input"
              type="password"
              value={entForm.pass}
              onChange={(e) => onEnterpriseFormChange({ ...entForm, pass: e.target.value })}
              placeholder="登录密码"
            />
            <input
              className="l-input"
              value={entForm.uscc}
              onChange={(e) => onEnterpriseFormChange({ ...entForm, uscc: e.target.value })}
              placeholder="统一社会信用代码"
            />
            <button
              className="l-btn"
              style={{ background: 'var(--green)' }}
              onClick={onRegisterEnterprise}
            >
              注册企业账号
            </button>
          </div>
        )}
      </div>
    </div>
  )
}
