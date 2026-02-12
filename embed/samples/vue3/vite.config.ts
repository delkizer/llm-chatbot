import { defineConfig } from 'vite'
import vue from '@vitejs/plugin-vue'

export default defineConfig({
  plugins: [
    vue({
      template: {
        compilerOptions: {
          isCustomElement: (tag) => tag === 'spo-chatbot'
        }
      }
    })
  ],
  base: '/sample/vue3/',
  server: { port: 5171 }
})
