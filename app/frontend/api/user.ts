import { get, post, put } from './http'

export interface UserProfile {
  id: number
  phone: string
  nickname?: string
  avatar_url?: string
  email?: string
  gender?: number
  birthday?: string
  created_at?: string
  updated_at?: string
}

// 订阅信息相关接口：个人主体暂不开放付费订阅，接口保留但前端不再调用
export interface SubscriptionInfo {
  plan: 'basic' | 'premium'
  status: 'active' | 'expired' | 'cancelled'
  expires_at?: string
  features: {
    unlimited_children?: boolean
    unlimited_assignments?: boolean
    advanced_reports?: boolean
  }
}

/**
 * 获取用户信息
 */
export function getUserProfile() {
  return get<UserProfile>('/api/v1/user/profile')
}

/**
 * 更新用户信息
 * 修改手机号时需同时传 phone 和 code（验证码）
 */
export function updateUserProfile(data: Partial<{
  nickname: string
  avatar_url: string
  email: string
  gender: number
  birthday: string
  phone: string
  code: string
}>) {
  return put<UserProfile>('/api/v1/user/profile', data)
}

/**
 * 上传头像
 */
export function uploadAvatar(filePath: string) {
  return new Promise<{ avatar_url?: string; avatarUrl?: string }>((resolve, reject) => {
    // 获取 baseURL
    // #ifdef H5
    const baseUrl = import.meta.env.VITE_API_BASE_URL || import.meta.env.VUE_APP_API_BASE_URL || ''
    // #endif
    // #ifndef H5
    const baseUrl = import.meta.env.VITE_API_BASE_URL || ''
    // #endif

    uni.uploadFile({
      url: baseUrl + '/api/v1/user/avatar',
      filePath,
      name: 'file',
      header: {
        Authorization: `Bearer ${uni.getStorageSync('token') || ''}`
      },
      success: (res) => {
        try {
          const data = JSON.parse(res.data) as { code: number; data?: { avatar_url?: string; avatarUrl?: string }; message?: string }
          if (data.code === 0 && data.data) {
            resolve(data.data)
          } else {
            reject(new Error(data.message || '上传失败'))
          }
        } catch (e) {
          reject(new Error('解析响应失败'))
        }
      },
      fail: (err) => {
        reject(err)
      }
    })
  })
}

/**
 * 修改密码
 */
export function changePassword(oldPassword: string, newPassword: string) {
  return post('/api/v1/user/change-password', {
    old_password: oldPassword,
    new_password: newPassword
  })
}

/**
 * 绑定手机号
 */
export function bindPhone(phone: string, code: string) {
  return post<{ phone: string }>('/api/v1/user/bind-phone', {
    phone,
    code
  })
}

// /**
//  * 获取订阅信息
//  */
// export function getSubscription() {
//   return get<SubscriptionInfo>('/api/v1/user/subscription')
// }
//
// /**
//  * 更新订阅
//  */
// export function updateSubscription(plan: 'basic' | 'premium', paymentMethod: 'wechat' | 'alipay') {
//   return post<{
//     order_id: string
//     payment_url: string
//   }>('/api/v1/user/subscription', {
//     plan,
//     payment_method: paymentMethod
//   })
// }
