/**
 * 认证相关工具函数
 */

import { useUserStore } from '@/stores/user'

/**
 * 检查是否已登录
 */
export function isAuthenticated(): boolean {
  const userStore = useUserStore()
  return !!userStore.token.value
}

/**
 * 检查登录状态，未登录则跳转到登录页
 */
export function checkAuth(): boolean {
  if (!isAuthenticated()) {
    // #ifdef MP-WEIXIN
    // 小程序端：不跳登录/注册页，触发微信静默登录后由各业务页通过 ensureLoggedInThen 等等待结果
    const userStore = useUserStore()
    userStore.wechatAutoLogin()
    return false
    // #endif
    // #ifndef MP-WEIXIN
    uni.redirectTo({ url: '/pages/auth/login' })
    return false
    // #endif
  }
  return true
}

/** 小程序下等待静默微信登录完成的最长时间（毫秒） */
const MP_WAIT_TOKEN_MS = 2500
const MP_POLL_INTERVAL_MS = 300

/**
 * 确保已登录后再执行回调。
 * 小程序下若当前无 token 会先等待一段时间（给 App 内静默微信登录时间），
 * 若仍未 token 再跳转登录页；非小程序下无 token 直接跳转登录页。
 */
export function ensureLoggedInThen(callback: () => void): void {
  const userStore = useUserStore()
  if (userStore.token.value) {
    callback()
    return
  }
  // #ifdef MP-WEIXIN
  // 小程序端：触发一次微信静默登录，并在一定时间内轮询 token，失败则仅提示，不跳登录/注册页
  userStore.wechatAutoLogin()
  let elapsed = 0
  const timer = setInterval(() => {
    elapsed += MP_POLL_INTERVAL_MS
    if (useUserStore().token.value) {
      clearInterval(timer)
      callback()
      return
    }
    if (elapsed >= MP_WAIT_TOKEN_MS) {
      clearInterval(timer)
      uni.showToast({
        title: '微信登录失败，请稍后重试',
        icon: 'none',
        duration: 2500
      })
    }
  }, MP_POLL_INTERVAL_MS)
  // #endif
  // #ifndef MP-WEIXIN
  uni.reLaunch({ url: '/pages/auth/login' })
  // #endif
}

/**
 * 获取认证 token
 */
export function getToken(): string | null {
  const userStore = useUserStore()
  return userStore.token.value || null
}

/**
 * 退出登录
 */
export function logout(): void {
  const userStore = useUserStore()
  userStore.logout()
  // #ifdef MP-WEIXIN
  // 小程序端退出后返回孩子列表，由静默登录再次获取 token
  uni.reLaunch({ url: '/pages/child/list' })
  // #endif
  // #ifndef MP-WEIXIN
  uni.reLaunch({ url: '/pages/auth/login' })
  // #endif
}
