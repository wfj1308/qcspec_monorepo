import React, { Suspense, lazy } from 'react'
import ReactDOM from 'react-dom/client'
import './styles/global.css'

const App = lazy(() => import('./App'))
const PublicVerifyPage = lazy(() => import('./pages/PublicVerifyPage'))
const GateRuleEditorPage = lazy(() => import('./pages/GateRuleEditorPage'))
const SpecDictEditorPage = lazy(() => import('./pages/SpecDictEditorPage'))

const path = window.location.pathname || '/'
const gateEditorMatch = path.match(/^\/admin\/gate-editor\/([^/]+)\/?$/)
const specDictEditorMatch = path.match(/^\/admin\/spec-dict\/([^/]+)\/?$/)

ReactDOM.createRoot(document.getElementById('root')!).render(
  <Suspense fallback={<div style={{ padding: 24, color: '#475569', fontFamily: 'system-ui, sans-serif' }}>Loading...</div>}>
    {path.startsWith('/v/') ? (
      <PublicVerifyPage />
    ) : gateEditorMatch ? (
      <GateRuleEditorPage subitemCode={decodeURIComponent(gateEditorMatch[1] || '')} />
    ) : specDictEditorMatch ? (
      <SpecDictEditorPage specDictKey={decodeURIComponent(specDictEditorMatch[1] || '')} />
    ) : (
      <App />
    )}
  </Suspense>
)
