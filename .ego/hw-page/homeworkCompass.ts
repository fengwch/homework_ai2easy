// HomeworkCompass 独立服务（FastAPI，默认 8100），不走 api/http.ts 的 backend 基址。
import { compassApiBase } from './compassEnv'

// ponytail: H5 开发期直连；同源部署时把 VITE_COMPASS_API 置空即可
const COMPASS_BASE = 'http://localhost:8100'

export interface CompassItem {
  seq: number
  subject: string
  task: string
  quantity: string
  requirements: string[]
  priority: string
  type: string
}

export interface CompassPending {
  id: string
  text: string
  reason: string
  source_sentence?: string
  related_seq?: number | null
}

export interface CompassHomework {
  date: string
  student_name: string
  slogan: string
  items: CompassItem[]
  extras: string[]
  pending: CompassPending[]
  source_text?: string
  ocr_text?: string
}

export interface CompassRender {
  url: string
  width: number
  height: number
  dpi: number
  used_placeholder: boolean
  issues: Array<{ zone: string; text: string; reason: string }>
}

function request<T>(path: string, data?: any): Promise<T> {
  return new Promise((resolve, reject) => {
    uni.request({
      url: COMPASS_BASE + path,
      method: data === undefined ? 'GET' : 'POST',
      data,
      header: { 'Content-Type': 'application/json' },
      timeout: 60000,
      success(res) {
        const body: any = res.data
        if (res.statusCode === 409) {
          // 409 = pending 未处理完，原样把原因交给页面
          reject(new Error(String(body?.detail || '存在待确认项')))
          return
        }
        if (res.statusCode !== 200 || !body || body.code !== 0) {
          reject(new Error(String(body?.detail || body?.message || '请求失败')))
          return
        }
        resolve(body.data as T)
      },
      fail(err) {
        reject(new Error((err as any).errMsg || '网络错误'))
      }
    })
  })
}

export const parseText = (text: string, name: string, date: string) =>
  request<CompassHomework>('/api/parse', { text, name, date })

export const correctField = (hw: CompassHomework, seq: number, field: string, value: string) =>
  request<CompassHomework>('/api/correct', { hw, seq, field, value })

export const dismissPending = (hw: CompassHomework, pendingId: string) =>
  request<CompassHomework>('/api/dismiss', { hw, pending_id: pendingId })

export const renderHomework = (hw: CompassHomework, skeleton: string, skin: string) =>
  request<CompassRender>('/api/render', { hw, skeleton, skin })

export const imageUrl = (url: string) => COMPASS_BASE + url
