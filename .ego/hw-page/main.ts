import { createApp, h } from 'vue'
import Page from './homework-compass.vue'

// 浏览器没有 uni-app x 的 <image> 组件：用 background-image 模拟，方便本地预览
const patchedImage = {
  props: ['src', 'mode'],
  setup(props) {
    return () => h('image', { style: { display: 'block', 'min-height': '360px', 'background-image': `url("${props.src}")`, 'aspect-ratio': '2480 / 3508' } })
  }
}

const app = createApp({ render: () => h(Page) })
app.component('image', patchedImage)
app.mount('#app')
