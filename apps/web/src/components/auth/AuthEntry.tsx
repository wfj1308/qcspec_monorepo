
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
          <div className="l-hint">�ỰУ����...</div>
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
          <div className="login-tagline">�����ʼ����ƽ̨</div>
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
            placeholder="�ֻ��� / ����"
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
            placeholder="����"
          />
          <button className="l-btn" onClick={onLogin} disabled={loggingIn}>
            {loggingIn ? '��¼��...' : '��¼'}
          </button>
        </div>
      </div>
    </div>
  )
}
