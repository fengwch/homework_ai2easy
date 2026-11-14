// HomeworkCompass 目标生成器 HTTP 封装：独立域名服务，直连 api.py，不经 api/http.ts。
// 基址只读 .env 的 VITE_COMPASS_API（开发/生产各配一套），源码里不回落到 localhost。
const COMPASS_BASE: string = import.meta.env.VITE_COMPASS_API || ''

export interface CompassItem {
  seq: number
  subject: string
  task: string
  quantity: string
  requirements: string[]
  requirements_all?: string[]
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
  reward?: string
}

export interface CompassRender {
  url: string
  width: number
  height: number
  dpi: number
  used_placeholder: boolean
  issues: Array<{ zone: string; text: string; reason: string }>
}

// 主题元信息由服务端 /api/options 下发；这里保留 5 个兜底，防止服务端未就绪时白屏
export const COMPASS_SKINS = ['dinosaur', 'space', 'ocean', 'pixel', 'candy']
export const COMPASS_SKIN_NAMES = ['恐龙', '太空', '海底', '像素', '糖果']

export interface CompassTheme {
  key: string
  cn: string
  interests: string[]
}

export async function compassFetchThemes(): Promise<CompassTheme[]> {
  const opts = await request<any>('/api/options')
  return (opts?.themes || []).map((t: any) => ({ key: t.key, cn: t.cn, interests: t.interests || [] }))
}

// 按兴趣返回推荐主题顺序（服务端排序）
export async function compassSuggestThemes(interests: string[]): Promise<string[]> {
  const data = await request<any[]>(`/api/themes/suggest?interests=${encodeURIComponent(interests.join(','))}`)
  return (data || []).map((t: any) => t.key)
}

function assertConfigured() {
  if (!COMPASS_BASE) {
    // 配置缺失时直接失败，避免把请求发到当前站点根路径后得到 404 无从判断
    throw new Error('未配置 VITE_COMPASS_API，请检查 .env')
  }
}

// 跨域时 uni.request 不会带 Origin 之外的凭据；这里统一约定后端 CORS 为 *（服务无会话状态）
function request<T>(path: string, data?: any): Promise<T> {
  return new Promise((resolve, reject) => {
    try {
      assertConfigured()
    } catch (err: any) {
      reject(err)
      return
    }
    uni.request({
      url: COMPASS_BASE + path,
      method: data === undefined ? 'GET' : 'POST',
      data,
      header: { 'Content-Type': 'application/json' },
      timeout: 60000,
      success(res) {
        const body: any = res.data
        if (res.statusCode === 409) {
          // pending 未处理完：后端已给出逐条原因，交给页面原样展示
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
        reject(new Error('Compass 服务不可达：' + ((err as any).errMsg || '网络错误')))
      }
    })
  })
}

export const compassOptions = () =>
  request<{ skeletons: string[]; skins: string[] }>('/api/options')

// smart=true 时服务端走大模型结构化（条目质量高，但每次解析会计费）。
// 默认 false 走离线兜底，只在确认屏出现问题时由家长手动切换。
export const compassParse = (text: string, name: string, date: string, smart = true) =>
  request<CompassHomework>('/api/parse', { text, name, date, llm: smart })

export const compassParseImage = (filePath: string, name: string, date: string, smart = true) =>
  new Promise<CompassHomework>((resolve, reject) => {
    try {
      assertConfigured()
    } catch (err: any) {
      reject(err)
      return
    }
    uni.uploadFile({
      url: COMPASS_BASE + '/api/parse/image?name=' + encodeURIComponent(name)
        + '&date=' + encodeURIComponent(date) + '&llm=' + (smart ? 'true' : 'false'),
      filePath,
      name: 'file',
      timeout: 120000,
      success(res) {
        let body: any = null
        try {
          body = JSON.parse(res.data)
        } catch (e) {
          reject(new Error('识别结果解析失败'))
          return
        }
        if (res.statusCode !== 200 || !body || body.code !== 0) {
          reject(new Error(String(body?.detail || '图片识别失败')))
          return
        }
        resolve(body.data as CompassHomework)
      },
      fail(err) {
        reject(new Error('Compass 服务不可达：' + ((err as any).errMsg || '网络错误')))
      }
    })
  })

export const compassCorrect = (hw: CompassHomework, seq: number, field: string, value: string) =>
  request<CompassHomework>('/api/correct', { hw, seq, field, value })

export const compassDropItem = (hw: CompassHomework, seq: number) =>
  request<CompassHomework>('/api/drop', { hw, seq })

export const compassDismiss = (hw: CompassHomework, pendingId: string) =>
  request<CompassHomework>('/api/dismiss', { hw, pending_id: pendingId })

export const compassPatch = (hw: CompassHomework, patch: { slogan?: string; student_name?: string; reward?: string }) =>
  request<CompassHomework>('/api/patch', Object.assign({ hw }, patch))

export const compassRender = (hw: CompassHomework, skeleton: string, skin: string) =>
  request<CompassRender>('/api/render', { hw, skeleton, skin })

export const compassImageUrl = (url: string) => COMPASS_BASE + url
