import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'
import { fileURLToPath, URL } from 'node:url'

export default defineConfig({
  plugins: [react()],
  server: { host: '0.0.0.0', port: 5173, strictPort: true, proxy: {
    '/v1': 'http://localhost:8000',
  }},
  resolve: { alias: {
    '@qcspec/types': fileURLToPath(new URL('../../packages/types/index.ts', import.meta.url)),
    '@qcspec/sdk':   fileURLToPath(new URL('../../packages/sdk/index.ts', import.meta.url)),
    '@qcspec/proof': fileURLToPath(new URL('../../packages/proof/index.ts', import.meta.url)),
  }},
})
