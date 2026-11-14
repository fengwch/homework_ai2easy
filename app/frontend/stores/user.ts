import { reactive, computed } from 'vue'
import { login as apiLogin, wechatLogin as apiWechatLogin, type LoginResponse } from '@/api/auth'
import { fetchChildren as apiFetchChildren, type Child } from '@/api/child'
import { updateUserProfile, type UserProfile } from '@/api/user'

export interface UserInfo {
  id: number
  phone: string
  nickname?: string
  avatarUrl?: string
  avatar_url?: string // 后端返回的字段名
}

export interface Child {
  id: number | string  // 后端可能返回字符串或数字
  name: string
  nickname?: string
  grade?: string
  avatarUrl?: string
  avatar_url?: string // 后端返回的字段名
}

const TOKEN_KEY = 'token'
const USER_INFO_KEY = 'user_info'
const CURRENT_CHILD_KEY = 'current_child_id'
const CHILDREN_KEY = 'children'
const AVATAR_CACHE_BUSTER_KEY = 'avatar_cache_buster'

// 使用 reactive 创建状态（uni-app-x 不支持 pinia）
const state = reactive({
  token: uni.getStorageSync(TOKEN_KEY) || '',
  userInfo: (uni.getStorageSync(USER_INFO_KEY) || null) as UserInfo | null,
  children: (uni.getStorageSync(CHILDREN_KEY) || []) as Child[],
  currentChildId: (uni.getStorageSync(CURRENT_CHILD_KEY) || null) as number | null,
  avatarCacheBuster: (uni.getStorageSync(AVATAR_CACHE_BUSTER_KEY) || 0) as number
})

export const useUserStore = () => {
  return {
    // state
    token: computed(() => state.token),
    userInfo: computed(() => state.userInfo),
    children: computed(() => state.children),
    currentChildId: computed(() => state.currentChildId),
    avatarCacheBuster: computed(() => state.avatarCacheBuster),

    // actions
    async login(phone: string, code: string): Promise<void> {
      try {
        const res = await apiLogin(phone, code)
        state.token = res.token
        
        // 后端返回的格式可能是 userInfo（驼峰）或 user_info（下划线）
        // 同时处理 id 可能是字符串或数字的情况
        const backendUserInfo = (res as any).userInfo || (res as any).user_info
        if (!backendUserInfo) {
          throw new Error('登录响应中缺少用户信息')
        }
        
        // 转换后端返回的用户信息为前端的 userInfo 格式
        const userInfo: UserInfo = {
          id: typeof backendUserInfo.id === 'string' ? parseInt(backendUserInfo.id) : backendUserInfo.id,
          phone: backendUserInfo.phone,
          nickname: backendUserInfo.nickname,
          avatarUrl: backendUserInfo.avatarUrl || backendUserInfo.avatar_url,
          avatar_url: backendUserInfo.avatarUrl || backendUserInfo.avatar_url
        }
        state.userInfo = userInfo
        
        uni.setStorageSync(TOKEN_KEY, res.token)
        uni.setStorageSync(USER_INFO_KEY, userInfo)
        
        // 登录成功后加载儿童列表
        await this.loadChildren()
      } catch (err) {
        console.error('登录失败:', err)
        throw err
      }
    },

    /**
     * 小程序下使用微信账号静默登录（无需登录页）
     * 仅传 code 调用 wechat-login。昵称、头像需用户点击按钮后通过 wx.getUserProfile 获取并同步。
     */
    async wechatAutoLogin(): Promise<void> {
      try {
        const loginRes = await new Promise<any>((resolve, reject) => {
          uni.login({
            provider: 'weixin',
            success: resolve,
            fail: reject
          })
        })
        const code = loginRes?.code
        if (!code) {
          console.warn('微信静默登录未返回 code')
          return
        }
        // 昵称头像仅能通过用户点击按钮触发 wx.getUserProfile 获取，静默登录不调用
        const res = await apiWechatLogin(code)
        state.token = res.token
        const backendUserInfo = (res as any).userInfo || (res as any).user_info
        if (backendUserInfo) {
          const userInfo: UserInfo = {
            id: typeof backendUserInfo.id === 'string' ? parseInt(backendUserInfo.id) : backendUserInfo.id,
            phone: backendUserInfo.phone || '',
            nickname: backendUserInfo.nickname,
            avatarUrl: backendUserInfo.avatarUrl || backendUserInfo.avatar_url,
            avatar_url: backendUserInfo.avatarUrl || backendUserInfo.avatar_url
          }
          state.userInfo = userInfo
          uni.setStorageSync(USER_INFO_KEY, userInfo)
        }
        uni.setStorageSync(TOKEN_KEY, res.token)
        await this.loadChildren()
        uni.reLaunch({ url: '/pages/child/list' })
      } catch (err) {
        console.warn('微信静默登录失败:', err)
      }
    },

    async loadChildren(): Promise<void> {
      try {
        const children = await apiFetchChildren()
        // 转换后端返回的字段名为前端格式，处理 id 可能是字符串的情况
        const formattedChildren: Child[] = children.map(child => ({
          id: typeof child.id === 'string' ? parseInt(child.id) : child.id,
          name: child.name,
          nickname: child.nickname,
          grade: child.grade,
          avatarUrl: (child as any).avatarUrl || child.avatar_url,
          avatar_url: (child as any).avatarUrl || child.avatar_url,
          interests: child.interests || [],
          custom_interests: child.custom_interests || []
        }))
        this.setChildren(formattedChildren)
      } catch (err) {
        console.error('加载儿童列表失败:', err)
        // 如果接口失败，使用空数组并继续抛出，便于页面展示「加载失败」与重试
        this.setChildren([])
        throw err
      }
    },

    /**
     * @deprecated 2022.11 起 uni.getUserProfile 返回「微信用户」和灰头像，已废弃。
     * 请使用 button open-type="chooseAvatar" 获取头像，或 input type="nickname" 获取昵称。
     */
    async syncWechatProfile(): Promise<void> {
      throw new Error('已废弃：请使用 chooseAvatar 按钮获取头像')
    },

    /**
     * 使用已获取的昵称、头像更新服务端并同步到本地（chooseAvatar 上传后或编辑个人资料保存后调用）
     */
    async syncWechatProfileFromInfo(nickName?: string, avatarUrl?: string): Promise<void> {
      if (!nickName && !avatarUrl) return
      const updated = await updateUserProfile({
        nickname: nickName || undefined,
        avatar_url: avatarUrl || undefined
      })
      this.applyProfileUpdate(updated)
      if (avatarUrl) {
        state.avatarCacheBuster = Date.now()
        uni.setStorageSync(AVATAR_CACHE_BUSTER_KEY, state.avatarCacheBuster)
      }
    },

    /**
     * 应用服务端返回的用户资料更新到本地（编辑个人信息保存后调用）
     */
    applyProfileUpdate(updated: UserProfile): void {
      const userInfo: UserInfo = {
        id: typeof updated.id === 'string' ? parseInt(updated.id) : updated.id,
        phone: updated.phone,
        nickname: updated.nickname,
        avatarUrl: (updated as any).avatarUrl || updated.avatar_url,
        avatar_url: (updated as any).avatarUrl || updated.avatar_url
      }
      state.userInfo = userInfo
      uni.setStorageSync(USER_INFO_KEY, userInfo)
      if ((updated as any).avatar_url ?? (updated as any).avatarUrl) {
        state.avatarCacheBuster = Date.now()
        uni.setStorageSync(AVATAR_CACHE_BUSTER_KEY, state.avatarCacheBuster)
      }
    },

    logout(): void {
      state.token = ''
      state.userInfo = null
      state.children = []
      state.currentChildId = null
      state.avatarCacheBuster = 0
      uni.removeStorageSync(TOKEN_KEY)
      uni.removeStorageSync(USER_INFO_KEY)
      uni.removeStorageSync(CURRENT_CHILD_KEY)
      uni.removeStorageSync(CHILDREN_KEY)
      uni.removeStorageSync(AVATAR_CACHE_BUSTER_KEY)
    },

    setChildren(children: Child[]): void {
      state.children = children
      uni.setStorageSync(CHILDREN_KEY, children)
      if (!state.currentChildId && children.length > 0) {
        const firstChildId = typeof children[0].id === 'string' ? parseInt(children[0].id) : children[0].id
        state.currentChildId = firstChildId
        uni.setStorageSync(CURRENT_CHILD_KEY, firstChildId)
      }
    },

    setCurrentChild(id: number | string): void {
      const childId = typeof id === 'string' ? parseInt(id) : id
      state.currentChildId = childId
      uni.setStorageSync(CURRENT_CHILD_KEY, childId)
    }
  }
}
