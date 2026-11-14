/**
 * 图片处理工具函数
 */

// 后端 API 基准地址（作业图片等静态资源由后端提供）
function getApiBaseUrl(): string {
  // #ifdef H5
  return import.meta.env.VITE_API_BASE_URL || import.meta.env.VUE_APP_API_BASE_URL || ''
  // #endif
  // #ifndef H5
  return import.meta.env.VITE_API_BASE_URL || ''
  // #endif
}

// 用户上传资源（头像等）的域名，优先使用 VITE_UPLOAD_BASE_URL
function getUploadBaseUrl(): string {
  const uploadBase = import.meta.env.VITE_UPLOAD_BASE_URL
  if (uploadBase) return uploadBase.replace(/\/$/, '')
  return getApiBaseUrl().replace(/\/$/, '')
}

/**
 * 解析作业/资源图片 URL：若为相对路径则拼上后端 base，避免请求到前端域名导致 404
 * 后端返回相对路径如 /uploads/assignments/1/0.jpg 时，会解析为 http://localhost:8000/uploads/...
 */
export function resolveResourceUrl(url: string): string {
  if (!url) return ''
  const trimmed = url.trim()
  if (trimmed.startsWith('http://') || trimmed.startsWith('https://')) return trimmed
  const base = getApiBaseUrl().replace(/\/$/, '')
  const path = trimmed.startsWith('/') ? trimmed : '/' + trimmed
  return base ? base + path : path
}

/**
 * 解析用户头像 URL：自己上传的头像为相对路径如 /uploads/users/26/avatar.png，需补全域名
 * @param url 头像路径（相对或绝对）
 * @param cacheBuster 时间戳，用于 CDN 缓存穿透，上传后立即展示新头像
 */
export function resolveAvatarUrl(url: string | undefined, cacheBuster?: number): string {
  if (!url) return ''
  const trimmed = url.trim()
  if (trimmed.startsWith('http://') || trimmed.startsWith('https://')) {
    const full = trimmed
    return cacheBuster ? (full.includes('?') ? `${full}&t=${cacheBuster}` : `${full}?t=${cacheBuster}`) : full
  }
  const base = getUploadBaseUrl()
  const path = trimmed.startsWith('/') ? trimmed : '/' + trimmed
  const full = base ? base + path : path
  return cacheBuster ? (full.includes('?') ? `${full}&t=${cacheBuster}` : `${full}?t=${cacheBuster}`) : full
}

/**
 * 图片懒加载
 */
export function lazyLoadImage(img: HTMLImageElement, src: string) {
  const observer = new IntersectionObserver((entries) => {
    entries.forEach((entry) => {
      if (entry.isIntersecting) {
        img.src = src
        observer.unobserve(img)
      }
    })
  })
  observer.observe(img)
}

/**
 * 压缩图片
 */
export function compressImage(
  filePath: string,
  quality: number = 0.8
): Promise<string> {
  return new Promise((resolve, reject) => {
    // #ifndef H5
    uni.compressImage({
      src: filePath,
      quality,
      success: (res) => {
        resolve(res.tempFilePath)
      },
      fail: reject
    })
    // #endif

    // #ifdef H5
    // H5 端使用 canvas 压缩
    const img = new Image()
    img.onload = () => {
      const canvas = document.createElement('canvas')
      const ctx = canvas.getContext('2d')
      if (!ctx) {
        reject(new Error('无法创建canvas上下文'))
        return
      }

      canvas.width = img.width
      canvas.height = img.height
      ctx.drawImage(img, 0, 0)

      canvas.toBlob(
        (blob) => {
          if (blob) {
            const url = URL.createObjectURL(blob)
            resolve(url)
          } else {
            reject(new Error('压缩失败'))
          }
        },
        'image/jpeg',
        quality
      )
    }
    img.onerror = reject
    img.src = filePath
    // #endif
  })
}

/**
 * 获取图片信息
 */
export function getImageInfo(src: string): Promise<{
  width: number
  height: number
  path: string
}> {
  return new Promise((resolve, reject) => {
    uni.getImageInfo({
      src,
      success: resolve,
      fail: reject
    })
  })
}
