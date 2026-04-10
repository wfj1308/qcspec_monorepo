import { Suspense, lazy  } from 'react'
import ReactDOM from 'react-dom/client'
import './styles/global.css'

const App = lazy(() => import('./App'))

ReactDOM.createRoot(document.getElementById('root')!).render(
  <Suspense fallback={<div style={{ padding: 24, color: '#475569', fontFamily: 'system-ui, sans-serif' }}>Loading...</div>}>
    <App />
  </Suspense>
)
