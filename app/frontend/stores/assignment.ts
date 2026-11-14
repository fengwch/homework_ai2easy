import { reactive, computed } from 'vue'

export interface AssignmentTemp {
  localImagePath: string
  uploading: boolean
}

// 使用 reactive 创建状态（uni-app-x 不支持 pinia）
const state = reactive({
  current: null as AssignmentTemp | null
})

export const useAssignmentStore = () => {
  return {
    // state
    current: computed(() => state.current),

    // actions
    setCurrent(payload: AssignmentTemp | undefined): void {
      state.current = payload || null
    }
  }
}
