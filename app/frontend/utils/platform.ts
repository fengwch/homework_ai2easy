/**
 * 平台检测工具函数
 */

/**
 * 获取当前平台
 */
export function getPlatform(): string {
  // #ifdef APP-PLUS
  return 'app'
  // #endif
  // #ifdef H5
  return 'h5'
  // #endif
  // #ifdef MP-WEIXIN
  return 'mp-weixin'
  // #endif
  // #ifdef MP-ALIPAY
  return 'mp-alipay'
  // #endif
  // #ifdef MP-BAIDU
  return 'mp-baidu'
  // #endif
  // #ifdef MP-TOUTIAO
  return 'mp-toutiao'
  // #endif
  // #ifdef MP-QQ
  return 'mp-qq'
  // #endif
  // #ifdef APP-IOS
  return 'ios'
  // #endif
  // #ifdef APP-ANDROID
  return 'android'
  // #endif
  return 'unknown'
}

/**
 * 是否为 App 平台
 */
export function isApp(): boolean {
  // #ifdef APP-PLUS
  return true
  // #endif
  return false
}

/**
 * 是否为 H5 平台
 */
export function isH5(): boolean {
  // #ifdef H5
  return true
  // #endif
  return false
}

/**
 * 是否为小程序平台
 */
export function isMp(): boolean {
  // #ifdef MP
  return true
  // #endif
  return false
}

/**
 * 是否为 iOS 平台
 */
export function isIOS(): boolean {
  // #ifdef APP-IOS
  return true
  // #endif
  return false
}

/**
 * 是否为 Android 平台
 */
export function isAndroid(): boolean {
  // #ifdef APP-ANDROID
  return true
  // #endif
  return false
}

/**
 * 获取系统信息
 */
export function getSystemInfo() {
  return uni.getSystemInfoSync()
}

/**
 * 获取状态栏高度
 */
export function getStatusBarHeight(): number {
  const systemInfo = getSystemInfo()
  return systemInfo.statusBarHeight || 0
}

/**
 * 获取安全区域信息
 */
export function getSafeAreaInsets() {
  const systemInfo = getSystemInfo()
  return systemInfo.safeAreaInsets || {
    top: 0,
    bottom: 0,
    left: 0,
    right: 0
  }
}
