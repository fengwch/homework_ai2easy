import { defineConfig } from '/Applications/HBuilderX.app/Contents/HBuilderX/plugins/uniapp-cli-vite/node_modules/vite/dist/node/index.js'
import vue from '/Applications/HBuilderX.app/Contents/HBuilderX/plugins/uniapp-cli-vite/node_modules/@vitejs/plugin-vue/dist/index.mjs'

export default defineConfig({
  root: '/Users/fengwanchang/Documents/homework_ai2easy/.ego/hw-page',
  plugins: [vue()],
  optimizeDeps: { noDiscovery: true, include: [] },
  resolve: {
    alias: {
      vue: '/Applications/HBuilderX.app/Contents/HBuilderX/plugins/uniapp-cli-vite/node_modules/@dcloudio/uni-h5-vue/dist/vue.runtime.esm.js'
    }
  },
  server: { port: 5199, strictPort: true }
})
