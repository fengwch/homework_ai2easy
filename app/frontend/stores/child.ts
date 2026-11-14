import { reactive, computed } from 'vue'
import { Child } from '@/api/child'

const CHILDREN_KEY = 'children'
const CURRENT_CHILD_KEY = 'current_child_id'

// 使用 reactive 创建状态（uni-app-x 不支持 pinia）
const state = reactive({
  children: (uni.getStorageSync(CHILDREN_KEY) || []) as Child[],
  currentChildId: (uni.getStorageSync(CURRENT_CHILD_KEY) || null) as number | null
})

export const useChildStore = () => {
  return {
    // state
    children: computed(() => state.children),
    currentChildId: computed(() => state.currentChildId),
    currentChild: computed(() => {
      if (!state.currentChildId) return null
      return state.children.find(c => c.id === state.currentChildId) || null
    }),

    // actions
    setChildren(children: Child[]): void {
      state.children = children
      uni.setStorageSync(CHILDREN_KEY, children)
      // 如果没有当前选中的孩子，且列表不为空，则选中第一个
      if (!state.currentChildId && children.length > 0) {
        state.currentChildId = children[0].id
        uni.setStorageSync(CURRENT_CHILD_KEY, children[0].id)
      }
    },

    setCurrentChild(id: number): void {
      state.currentChildId = id
      uni.setStorageSync(CURRENT_CHILD_KEY, id)
    },

    addChild(child: Child): void {
      state.children.push(child)
      uni.setStorageSync(CHILDREN_KEY, state.children)
      // 如果当前没有选中的孩子，则选中新添加的
      if (!state.currentChildId) {
        state.currentChildId = child.id
        uni.setStorageSync(CURRENT_CHILD_KEY, child.id)
      }
    },

    updateChild(id: number, data: Partial<Child>): void {
      const index = state.children.findIndex(c => c.id === id)
      if (index !== -1) {
        state.children[index] = { ...state.children[index], ...data }
        uni.setStorageSync(CHILDREN_KEY, state.children)
      }
    },

    removeChild(id: number): void {
      const index = state.children.findIndex(c => c.id === id)
      if (index !== -1) {
        state.children.splice(index, 1)
        uni.setStorageSync(CHILDREN_KEY, state.children)
        // 如果删除的是当前选中的孩子
        if (state.currentChildId === id) {
          // 如果还有孩子，选中第一个；否则清空
          if (state.children.length > 0) {
            state.currentChildId = state.children[0].id
            uni.setStorageSync(CURRENT_CHILD_KEY, state.children[0].id)
          } else {
            state.currentChildId = null
            uni.removeStorageSync(CURRENT_CHILD_KEY)
          }
        }
      }
    },

    clearChildren(): void {
      state.children = []
      state.currentChildId = null
      uni.removeStorageSync(CHILDREN_KEY)
      uni.removeStorageSync(CURRENT_CHILD_KEY)
    }
  }
}
