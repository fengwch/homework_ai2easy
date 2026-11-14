import { ref } from 'vue'
import { useUserStore } from '../stores/user'

// 根据环境变量和平台配置 baseURL
// #ifdef H5
const BASE_URL = import.meta.env.VITE_API_BASE_URL || import.meta.env.VUE_APP_API_BASE_URL || ''
// #endif
// #ifndef H5
const BASE_URL = import.meta.env.VITE_API_BASE_URL || ''
// #endif

export interface HttpResponse<T = any> {
  code: number
  message: string
  data: T
}

const pending = ref(0)

// uni-app-x 中的请求选项类型
type RequestOptions = {
  url: string
  method?: 'GET' | 'POST' | 'PUT' | 'DELETE'
  data?: any
  header?: Record<string, string>
  timeout?: number
}

function request<T = any>(options: RequestOptions): Promise<T> {
  const userStore = useUserStore()

  return new Promise((resolve, reject) => {
    pending.value++

    const headers: Record<string, string> = options.header || {}
    const token = userStore.token.value

    // 添加认证 token
    if (token) {
      headers['Authorization'] = `Bearer ${token}`
    }

    // 添加平台信息
    const systemInfo = uni.getSystemInfoSync()
    const platform = systemInfo.uniPlatform || ''
    headers['X-Platform'] = platform
    
    // 获取设备 ID
    const deviceId = systemInfo.deviceId || 'unknown'
    headers['X-Device-Id'] = deviceId

    // H5 端可能需要额外的请求头
    // #ifdef H5
    headers['Content-Type'] = headers['Content-Type'] || 'application/json'
    // #endif

    uni.request<HttpResponse<T>>({
      url: BASE_URL + options.url,
      method: options.method || 'GET',
      data: options.data,
      header: headers,
      timeout: options.timeout || 10000,
      success(res) {
        const { statusCode, data } = res

        // 处理 401 未授权
        if (statusCode === 401) {
          userStore.logout()
          uni.redirectTo({ url: '/pages/auth/login' })
          reject(new Error('未授权'))
          return
        }

        // 处理业务错误
        if (!data || data.code !== 0) {
          uni.showToast({
            title: data?.message || '请求失败',
            icon: 'none'
          })
          reject(new Error(data?.message || '请求失败'))
          return
        }

        resolve(data.data as T)
      },
      fail(err) {
        // H5 端跨域错误提示
        // #ifdef H5
        const errMsg = err.errMsg || ''
        if (errMsg.includes('CORS') || errMsg.includes('cross-origin') || errMsg.includes('strict-origin')) {
          console.error('CORS 错误:', err)
          uni.showToast({
            title: '跨域请求失败，请检查后端 CORS 配置或使用代理',
            icon: 'none',
            duration: 4000
          })
        } else if (errMsg.includes('fail') || errMsg.includes('timeout')) {
          uni.showToast({
            title: '网络错误，请检查网络连接或后端服务是否启动',
            icon: 'none',
            duration: 3000
          })
        } else {
          uni.showToast({
            title: '网络错误: ' + (errMsg || '未知错误'),
            icon: 'none',
            duration: 3000
          })
        }
        // #endif
        // #ifndef H5
        const errMsg = (err as any).errMsg || (err as any).message || ''
        console.error('请求失败:', errMsg, err)
        // 预览/正式版常见：域名未配置
        if (errMsg.indexOf('domain') !== -1 || errMsg.indexOf('url not in domain list') !== -1) {
          uni.showToast({
            title: '请在小程序后台配置 request 合法域名',
            icon: 'none',
            duration: 4000
          })
        } else {
          uni.showToast({
            title: '网络错误',
            icon: 'none'
          })
        }
        // #endif
        reject(err)
      },
      complete() {
        pending.value--
      }
    })
  })
}

export function get<T = any>(url: string, data?: any) {
  return request<T>({ url, data, method: 'GET' })
}

export function post<T = any>(url: string, data?: any) {
  return request<T>({ url, data, method: 'POST' })
}

export function put<T = any>(url: string, data?: any) {
  return request<T>({ url, data, method: 'PUT' })
}

export function del<T = any>(url: string, data?: any) {
  return request<T>({ url, data, method: 'DELETE' })
}

export function useHttpLoading() {
  return pending
}
