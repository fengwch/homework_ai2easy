// 目标生成器的跨屏状态：五屏都在同一浏览栈上，用页面级单例保持，不引入 Pinia（项目未使用）。
import { reactive } from 'vue'
import type { CompassHomework, CompassRender } from '@/api/compass'

export interface CompassState {
  childId: string
  childName: string
  hw: CompassHomework | null
  skin: string
  render: CompassRender | null
}

const state = reactive<CompassState>({
  childId: '',
  childName: '',
  hw: null,
  skin: 'dinosaur',
  render: null
})

export function useCompassStore() {
  return {
    state,
    setChild(childId: string, childName: string) {
      state.childId = childId
      state.childName = childName
      state.hw = null
      state.render = null
    },
    setHomework(hw: CompassHomework) {
      state.hw = hw
      state.render = null
    },
    setSkin(skin: string) {
      state.skin = skin
      state.render = null
    },
    setRender(render: CompassRender) {
      state.render = render
    },
    reset() {
      state.hw = null
      state.render = null
    }
  }
}
