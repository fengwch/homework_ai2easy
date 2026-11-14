/**
 * 缓存管理工具函数
 */

import { setStorage, getStorage, removeStorage } from './storage'

const CACHE_PREFIX = 'cache_'
const CACHE_EXPIRE_PREFIX = 'cache_expire_'
const DEFAULT_EXPIRE = 24 * 60 * 60 * 1000 // 24小时

interface CacheItem<T> {
  data: T
  expire: number
}

/**
 * 设置缓存
 */
export function setCache<T>(key: string, data: T, expire: number = DEFAULT_EXPIRE): void {
  const expireTime = Date.now() + expire
  setStorage(CACHE_PREFIX + key, data)
  setStorage(CACHE_EXPIRE_PREFIX + key, expireTime)
}

/**
 * 获取缓存
 */
export function getCache<T>(key: string): T | null {
  const expireTime = getStorage<number>(CACHE_EXPIRE_PREFIX + key)
  
  if (!expireTime || Date.now() > expireTime) {
    // 缓存已过期，清除
    removeCache(key)
    return null
  }
  
  return getStorage<T>(CACHE_PREFIX + key)
}

/**
 * 移除缓存
 */
export function removeCache(key: string): void {
  removeStorage(CACHE_PREFIX + key)
  removeStorage(CACHE_EXPIRE_PREFIX + key)
}

/**
 * 清除所有缓存
 */
export function clearAllCache(): void {
  const storageInfo = uni.getStorageInfoSync()
  storageInfo.keys.forEach((key) => {
    if (key.startsWith(CACHE_PREFIX) || key.startsWith(CACHE_EXPIRE_PREFIX)) {
      removeStorage(key)
    }
  })
}

/**
 * 检查缓存是否存在且未过期
 */
export function hasCache(key: string): boolean {
  const expireTime = getStorage<number>(CACHE_EXPIRE_PREFIX + key)
  return expireTime !== null && Date.now() <= expireTime
}
