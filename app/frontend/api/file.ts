export interface UploadFileResult {
  /** 可访问的相对路径，如 /uploads/files/images/xxx.jpg */
  url: string
  /** 推断的文件名 */
  filename: string
  /** 文件大小（字节） */
  size: number
}

/**
 * 通用文件上传
 * @param filePath - uni.chooseImage / uni.chooseFile 返回的临时文件路径
 * @param directory - 可选，目标子目录，如 "images" 或 "documents/reports"
 * @returns { url, filename, size }
 */
export function uploadFile(filePath: string, directory?: string): Promise<UploadFileResult> {
  return new Promise<UploadFileResult>((resolve, reject) => {
    // 获取 baseURL
    // #ifdef H5
    const baseUrl = import.meta.env.VITE_API_BASE_URL || import.meta.env.VUE_APP_API_BASE_URL || ''
    // #endif
    // #ifndef H5
    const baseUrl = import.meta.env.VITE_API_BASE_URL || ''
    // #endif

    const formData: Record<string, string> = {}
    if (directory) {
      formData.directory = directory
    }

    uni.uploadFile({
      url: baseUrl + '/api/v1/files/upload',
      filePath,
      name: 'file',
      formData,
      header: {
        Authorization: `Bearer ${uni.getStorageSync('token') || ''}`
      },
      success: (res) => {
        try {
          const data = JSON.parse(res.data) as {
            code: number
            data?: UploadFileResult
            message?: string
          }
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
