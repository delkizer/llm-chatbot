import { defineConfig } from 'vite';
import { resolve } from 'path';

export default defineConfig({
  build: {
    lib: {
      entry: resolve(__dirname, 'src/spo-chatbot.ts'),
      name: 'SpoChatbot',
      formats: ['iife'],
      fileName: () => 'embed.js'
    },
    cssCodeSplit: false,
    rollupOptions: {
      output: {
        inlineDynamicImports: true
      }
    },
    outDir: 'dist',
    minify: 'terser'
  }
});
