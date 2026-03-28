import React from 'react'
import ReactDOM from 'react-dom/client'
import App from './App'
import PublicVerifyPage from './pages/PublicVerifyPage'
import './styles/global.css'

ReactDOM.createRoot(document.getElementById('root')!).render(
  window.location.pathname.startsWith('/v/') ? <PublicVerifyPage /> : <App />
)
