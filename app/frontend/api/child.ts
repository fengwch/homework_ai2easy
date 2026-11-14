import { get, post, put, del } from './http'

export interface Child {
  id: number | string  // 后端可能返回字符串或数字
  name: string
  nickname?: string
  gender?: number
  birth_date?: string
  grade?: string
  avatar_url?: string
  avatarUrl?: string  // 后端可能返回驼峰格式
  interests?: string[]
  custom_interests?: string[]
  learning_style?: string
  attention_span?: number
  weak_subjects?: string[]
  learning_stats?: {
    total_study_time?: number
    completed_assignments?: number
    average_score?: number
    last_study_date?: string
  }
  created_at?: string
  updated_at?: string
}

/**
 * 获取儿童列表
 */
export function fetchChildren() {
  return get<Child[]>('/api/v1/children')
}

/**
 * 获取儿童详情
 */
export function fetchChildDetail(id: number) {
  return get<Child>(`/api/v1/children/${id}`)
}

/**
 * 创建儿童档案
 */
export function createChild(data: {
  name: string
  nickname?: string
  gender: number
  birth_date: string
  grade: string
  avatar_url?: string
  interests?: string[]
  custom_interests?: string[]
  learning_style?: string
  attention_span?: number
  weak_subjects?: string[]
}) {
  return post<Child>('/api/v1/children', data)
}

/**
 * 更新儿童档案
 */
export function updateChild(id: number, data: Partial<{
  name: string
  nickname?: string
  gender?: number
  birth_date?: string
  grade?: string
  avatar_url?: string
  interests?: string[]
  custom_interests?: string[]
  learning_style?: string
  attention_span?: number
  weak_subjects?: string[]
}>) {
  return put<Child>(`/api/v1/children/${id}`, data)
}

/**
 * 删除儿童档案
 */
export function deleteChild(id: number) {
  return del(`/api/v1/children/${id}`)
}

/**
 * 上传儿童头像
 */
export function uploadChildAvatar(id: number, filePath: string) {
  return new Promise<{ avatar_url: string }>((resolve, reject) => {
    // 获取 baseURL
    // #ifdef H5
    const baseUrl = import.meta.env.VITE_API_BASE_URL || import.meta.env.VUE_APP_API_BASE_URL || ''
    // #endif
    // #ifndef H5
    const baseUrl = import.meta.env.VITE_API_BASE_URL || ''
    // #endif

    uni.uploadFile({
      url: baseUrl + `/api/v1/children/${id}/avatar`,
      filePath,
      name: 'file',
      header: {
        Authorization: `Bearer ${uni.getStorageSync('token') || ''}`
      },
      success: (res) => {
        try {
          const data = JSON.parse(res.data) as { code: number; data?: { avatar_url: string }; message?: string }
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
