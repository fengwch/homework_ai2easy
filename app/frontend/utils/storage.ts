/**
 * 本地存储工具函数
 * 封装 uni.setStorageSync 和 uni.getStorageSync，提供类型安全
 */

export function setStorage<T>(key: string, value: T): void {
  try {
    uni.setStorageSync(key, value)
  } catch (e) {
    console.error(`Storage set error for key "${key}":`, e)
  }
}

export function getStorage<T>(key: string, defaultValue?: T): T | null {
  try {
    const value = uni.getStorageSync(key)
    return value != null ? (value as T) : (defaultValue || null)
  } catch (e) {
    console.error(`Storage get error for key "${key}":`, e)
    return defaultValue || null
  }
}

export function removeStorage(key: string): void {
  try {
    uni.removeStorageSync(key)
  } catch (e) {
    console.error(`Storage remove error for key "${key}":`, e)
  }
}

export function clearStorage(): void {
  try {
    uni.clearStorageSync()
  } catch (e) {
    console.error('Storage clear error:', e)
  }
}

export function hasStorage(key: string): boolean {
  try {
    const info = uni.getStorageInfoSync()
    return info.keys.includes(key)
  } catch (e) {
    console.error(`Storage has check error for key "${key}":`, e)
    return false
  }
}
