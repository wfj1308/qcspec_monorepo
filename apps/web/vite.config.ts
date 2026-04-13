import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'
import { fileURLToPath, URL } from 'node:url'

export default defineConfig({
  plugins: [react()],
  server: { host: '0.0.0.0', port: 5173, strictPort: true, proxy: {
    '/v1': 'http://localhost:8000',
  }},
  build: {
    rollupOptions: {
      output: {
        manualChunks(id) {
          if (id.includes('/src/components/projects/sovereign/') || id.includes('/src/components/projects/SovereignWorkbenchPanel.tsx')) {
            return 'sovereign-workbench'
          }
          if (id.includes('/src/components/proof/')) {
            return 'proof-ui'
          }
          if (id.includes('/src/components/register/') || id.includes('/src/app/useRegister') || id.includes('/src/app/register')) {
            return 'register-ui'
          }
          if (id.includes('/src/components/projects/') || id.includes('/src/app/useProject')) {
            return 'project-ui'
          }
          if (!id.includes('node_modules')) return undefined
          if (id.includes('pdfjs-dist')) return 'pdfjs-vendor'
          if (id.includes('react') || id.includes('scheduler')) return 'react-vendor'
          if (id.includes('zustand')) return 'state-vendor'
          return 'vendor'
        },
      },
    },
  },
  resolve: { alias: {
    '@qcspec/types': fileURLToPath(new URL('../../packages/types/index.ts', import.meta.url)),
    '@qcspec/proof': fileURLToPath(new URL('../../packages/proof/index.ts', import.meta.url)),
  }, dedupe: ['react', 'react-dom']},
})
