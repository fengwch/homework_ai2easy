import { get, post, put, del } from './http'

export interface KnowledgePoint {
  subject: string
  topic: string
  subtopic?: string
  difficulty: 'easy' | 'medium' | 'hard'
  confidence?: number
  description?: string
}

export interface Question {
  id: string
  question_number: number
  question_type: 'multiple_choice' | 'fill_blank' | 'calculation' | 'word_problem' | 'essay'
  original_text: string
  structured_data?: {
    stem: string
    options?: Array<{ option: string; text: string }>
    answer?: string
    analysis?: string
  }
  knowledge_points?: KnowledgePoint[]
  metadata?: {
    word_count?: number
    has_image?: boolean
    has_formula?: boolean
    confidence?: number
  }
  updated_at?: string
}

export interface AssignmentDetail {
  id: number
  child_id: number
  subject: string
  grade?: string
  original_images: string[]
  questions: Question[]
  generated_content?: {
    story_id?: string
    status?: 'pending' | 'processing' | 'completed' | 'failed'
  }
  status: 'pending' | 'processing' | 'completed' | 'failed'
  estimated_time?: number
  actual_time?: number
  score?: number
  completed_at?: string
  created_at: string
  updated_at: string
}

export interface ScanStatus {
  assignment_id: number
  status: 'processing' | 'complete' | 'error'
  progress?: number
  estimated_time?: number
  questions?: Question[]
}

export interface ScanResult {
  assignment_id: number
  status: 'processing' | 'complete' | 'error'
  progress: number
  estimated_time: number
}

export interface AssignmentListItem {
  id: number
  child_id: number
  subject: string
  status: string
  created_at: string
  has_answers?: boolean
  hasAnswers?: boolean
  score?: number | null
}

export interface AssignmentListResponse {
  list: AssignmentListItem[]
  total: number
  page: number
  page_size: number
}

export interface GenerateStatus {
  content_id: string
  status: 'pending' | 'processing' | 'completed' | 'failed'
  progress?: number
  estimated_time?: number
  story_id?: string
}

/**
 * 上传作业图片
 */
export function uploadAssignment(filePath: string, childId: number) {
  return new Promise<{ id: number }>((resolve, reject) => {
    // 获取 baseURL
    // #ifdef H5
    const baseUrl = import.meta.env.VITE_API_BASE_URL || import.meta.env.VUE_APP_API_BASE_URL || ''
    // #endif
    // #ifndef H5
    const baseUrl = import.meta.env.VITE_API_BASE_URL || ''
    // #endif

    uni.uploadFile({
      url: baseUrl + '/api/v1/assignments/upload',
      filePath,
      name: 'file',
      formData: {
        child_id: String(childId)
      },
      header: {
        Authorization: `Bearer ${uni.getStorageSync('token') || ''}`
      },
      success: (res) => {
        try {
          const data = JSON.parse(res.data) as { code: number; data?: { id: number }; message?: string }
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
 * 扫描识别作业
 */
export function scanAssignment(imageData: string, childId: number, subject: string) {
  return post<ScanResult>('/api/v1/assignments/scan', {
    image_data: imageData,
    child_id: childId,
    subject
  })
}

/**
 * 按作业 ID 触发识别（后端需实现 POST /api/v1/assignments/{id}/scan）
 * 请求体可选：{ subject?: string }
 */
export function triggerAssignmentScan(assignmentId: number, subject?: string) {
  return post<{ assignmentId: number; status: string; progress?: number; estimatedTime?: number }>(
    `/api/v1/assignments/${assignmentId}/scan`,
    subject != null ? { subject } : {}
  )
}

/**
 * 获取识别进度
 */
export function getScanStatus(id: number) {
  return get<ScanStatus>(`/api/v1/assignments/${id}/scan-status`)
}

/**
 * 获取作业详情
 */
export function fetchAssignmentDetail(id: number) {
  return get<AssignmentDetail>(`/api/v1/assignments/${id}`)
}

/**
 * 编辑识别结果（接口文档约定 camelCase）
 */
export function updateQuestion(
  assignmentId: number,
  questionId: string,
  data: {
    originalText?: string
    structuredData?: Question['structured_data']
    questionType?: Question['question_type']
  }
) {
  return put<Question>(`/api/v1/assignments/${assignmentId}/questions/${questionId}`, data)
}

/**
 * 题目分割确认
 */
export function splitQuestions(assignmentId: number, questions: Array<{
  id: string
  question_number: number
  start_index?: number
  end_index?: number
}>) {
  return post<{ questions: Question[] }>(`/api/v1/assignments/${assignmentId}/split-questions`, { questions })
}

/**
 * 题目类型标注
 */
export function updateQuestionType(
  assignmentId: number,
  questionId: string,
  questionType: Question['question_type']
) {
  return put<{ id: string; question_type: string; updated_at: string }>(
    `/api/v1/assignments/${assignmentId}/questions/${questionId}/type`,
    { question_type: questionType }
  )
}

/**
 * 获取知识点
 */
export function getKnowledgePoints(assignmentId: number, questionId: string) {
  return get<{ knowledge_points: KnowledgePoint[] }>(
    `/api/v1/assignments/${assignmentId}/questions/${questionId}/knowledge-points`
  )
}

/**
 * 更新知识点
 */
export function updateKnowledgePoints(
  assignmentId: number,
  questionId: string,
  knowledgePoints: KnowledgePoint[]
) {
  return put<{ knowledge_points: KnowledgePoint[] }>(
    `/api/v1/assignments/${assignmentId}/questions/${questionId}/knowledge-points`,
    { knowledge_points: knowledgePoints }
  )
}

/**
 * 更新作业信息
 */
export function updateAssignment(
  id: number,
  data: Partial<{
    subject: string
    urgency: 'low' | 'medium' | 'high'
    notes: string
    questions: Question[]
    status: string
  }>
) {
  return put<AssignmentDetail>(`/api/v1/assignments/${id}`, data)
}

/**
 * 删除题目
 */
export function deleteQuestion(assignmentId: number, questionId: string) {
  return del(`/api/v1/assignments/${assignmentId}/questions/${questionId}`)
}

/**
 * 生成个性化内容
 */
export function generateContent(assignmentId: number) {
  return post<{ content_id: string; status: string }>(`/api/v1/assignments/${assignmentId}/generate`)
}

/**
 * 查询内容生成状态
 */
export function getGenerateStatus(assignmentId: number) {
  return get<GenerateStatus>(`/api/v1/assignments/${assignmentId}/generate-status`)
}

/**
 * 按题目生成个性化内容（单题）
 * 接口：POST /api/v1/assignments/{assignmentId}/questions/{questionId}/generate
 */
export function generateQuestionContent(assignmentId: number, questionId: string) {
  return post<{ content_id: string; status: string }>(
    `/api/v1/assignments/${assignmentId}/questions/${questionId}/generate`
  )
}

/**
 * 查询单题内容生成状态
 * 接口：GET /api/v1/assignments/{assignmentId}/questions/{questionId}/generate-status
 */
export function getQuestionGenerateStatus(assignmentId: number, questionId: string) {
  return get<GenerateStatus>(
    `/api/v1/assignments/${assignmentId}/questions/${questionId}/generate-status`
  )
}

/**
 * 获取作业列表
 */
export function fetchAssignmentList(params?: {
  child_id?: number
  status?: 'pending' | 'processing' | 'completed' | 'failed'
  has_answers?: boolean
  subject?: string
  page?: number
  page_size?: number
}) {
  return get<AssignmentListResponse>('/api/v1/assignments', params)
}
