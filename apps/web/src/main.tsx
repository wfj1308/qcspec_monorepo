import React from 'react'
import ReactDOM from 'react-dom/client'
import App from './App'
import PublicVerifyPage from './pages/PublicVerifyPage'
import GateRuleEditorPage from './pages/GateRuleEditorPage'
import SpecDictEditorPage from './pages/SpecDictEditorPage'
import './styles/global.css'

const path = window.location.pathname || '/'
const gateEditorMatch = path.match(/^\/admin\/gate-editor\/([^/]+)\/?$/)
const specDictEditorMatch = path.match(/^\/admin\/spec-dict\/([^/]+)\/?$/)

ReactDOM.createRoot(document.getElementById('root')!).render(
  path.startsWith('/v/') ? (
    <PublicVerifyPage />
  ) : gateEditorMatch ? (
    <GateRuleEditorPage subitemCode={decodeURIComponent(gateEditorMatch[1] || '')} />
  ) : specDictEditorMatch ? (
    <SpecDictEditorPage specDictKey={decodeURIComponent(specDictEditorMatch[1] || '')} />
  ) : (
    <App />
  )
)
