import { Suspense, lazy } from 'react'
import ReactDOM from 'react-dom/client'
import { QueryClientProvider } from '@tanstack/react-query'
import './styles/global.css'
import { queryClient } from './lib/queryClient'

const App = lazy(() => import('./App'))

ReactDOM.createRoot(document.getElementById('root')!).render(
  <QueryClientProvider client={queryClient}>
    <Suspense fallback={<div style={{ padding: 24, color: '#475569', fontFamily: 'system-ui, sans-serif' }}>加载中...</div>}>
      <App />
    </Suspense>
  </QueryClientProvider>
)
