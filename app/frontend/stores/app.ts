import { reactive, computed } from 'vue'
import { getSystemInfo } from '@/utils/platform'

const APP_CONFIG_KEY = 'app_config'

interface AppConfig {
  theme: 'light' | 'dark' | 'auto'
  language: string
  notificationEnabled: boolean
}

// 使用 reactive 创建状态（uni-app-x 不支持 pinia）
const state = reactive({
  // 应用配置
  config: (uni.getStorageSync(APP_CONFIG_KEY) || {
    theme: 'light',
    language: 'zh-CN',
    notificationEnabled: true
  }) as AppConfig,
  
  // 系统信息
  systemInfo: getSystemInfo(),
  
  // 网络状态
  networkConnected: true,
  
  // 应用版本
  version: '1.0.0',
  
  // 是否首次启动
  isFirstLaunch: !uni.getStorageSync('has_launched')
})

export const useAppStore = () => {
  return {
    // state
    config: computed(() => state.config),
    systemInfo: computed(() => state.systemInfo),
    networkConnected: computed(() => state.networkConnected),
    version: computed(() => state.version),
    isFirstLaunch: computed(() => state.isFirstLaunch),

    // actions
    updateConfig(config: Partial<AppConfig>): void {
      state.config = { ...state.config, ...config }
      uni.setStorageSync(APP_CONFIG_KEY, state.config)
    },

    setNetworkStatus(connected: boolean): void {
      state.networkConnected = connected
    },

    // 标记是否为首次启动：
    // first = true 表示仍然是第一次（会继续展示新手指引）
    // first = false 表示已完成首启流程（不再展示指引）
    setFirstLaunch(first: boolean): void {
      state.isFirstLaunch = first
      if (!first) {
        uni.setStorageSync('has_launched', true)
      } else {
        uni.removeStorageSync('has_launched')
      }
    },

    updateSystemInfo(): void {
      state.systemInfo = getSystemInfo()
    }
  }
}
