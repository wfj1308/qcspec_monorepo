interface LoginFormState {
  account: string
  pass: string
}

interface AuthEntryProps {
  sessionChecking: boolean
  loginForm: LoginFormState
  loggingIn: boolean
  onLoginFormChange: (next: LoginFormState) => void
  onLogin: () => void
}

export default function AuthEntry({
  sessionChecking,
  loginForm,
  loggingIn,
  onLoginFormChange,
  onLogin,
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
          <div className="login-tagline">工程质检管理平台</div>
        </div>

        <div className="login-form">
          <input
            className="l-input"
            value={loginForm.account}
            autoComplete="username"
            onChange={(e) => onLoginFormChange({ ...loginForm, account: e.target.value })}
            onKeyDown={(e) => {
              if (e.key === 'Enter') onLogin()
            }}
            placeholder="手机号 / 邮箱"
          />
          <input
            className="l-input"
            type="password"
            value={loginForm.pass}
            autoComplete="current-password"
            onChange={(e) => onLoginFormChange({ ...loginForm, pass: e.target.value })}
            onKeyDown={(e) => {
              if (e.key === 'Enter') onLogin()
            }}
            placeholder="密码"
          />
          <button className="l-btn" onClick={onLogin} disabled={loggingIn}>
            {loggingIn ? '登录中...' : '登录'}
          </button>
        </div>
      </div>
    </div>
  )
}
