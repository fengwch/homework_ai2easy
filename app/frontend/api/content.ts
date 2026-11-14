import { get, post } from './http'

export interface Story {
  id: string
  title: string
  theme: string
  pages: StoryPage[]
  totalPages: number
  estimatedReadingTime?: number
}

export interface StoryPage {
  pageNumber: number
  illustration?: string
  text: string
  question?: {
    id: string
    text: string
    type: string
  }
  narration?: {
    audioUrl?: string
    duration?: number
  }
}

/** 后端 /api/v1/contents/{story_id} 返回的学习材料格式 */
export interface LearningContent {
  storyId: string
  title: string
  summary?: string
  story: string
  theme?: string
  images?: string[]
  /** 插图生成状态（与作业 generate-status 的 imageStatus 一致） */
  imageStatus?: string
  image_status?: string
  imageProgress?: number
  image_progress?: number
  questions: Array<{
    id: string
    questionNumber: number
    content: string
    options: string[]
    answer: string
    analysis?: string
  }>
}

export interface LearningReport {
  date: string
  totalQuestions: number
  correctCount: number
  wrongCount: number
  correctRate: number
  timeSpent: number
  knowledgePoints: Array<{
    topic: string
    masteryRate: number
  }>
}

export function fetchStory(storyId: string) {
  return get<Story>(`/api/v1/contents/${storyId}`)
}

/** 获取学习材料（后端格式：story 字符串 + questions 数组） */
export function fetchLearningContent(storyId: string) {
  return get<LearningContent>(`/api/v1/contents/${storyId}`)
}

/** 导出学习材料为 PDF（GET /api/v1/contents/{story_id}/pdf，后端生成并返回下载链接） */
export function requestLearningContentPdf(storyId: string) {
  return get<{ url: string }>(`/api/v1/contents/${storyId}/pdf`)
}

/** 提交单题答案。无故事时传 assignmentId 直接答题；有故事时传 storyId。 */
export function submitAnswer(
  questionId: string,
  answer: string,
  options: { storyId?: string; assignmentId?: number }
) {
  const body: { answer: string; storyId?: string; assignmentId?: number } = { answer }
  if (options.storyId) {
    body.storyId = options.storyId
  } else if (options.assignmentId != null) {
    body.assignmentId = options.assignmentId
  }
  return post<{ isCorrect: boolean; feedback: string }>(`/api/v1/questions/${questionId}/answer`, body)
}

export function fetchLearningReport(assignmentId: number) {
  return get<LearningReport>(`/api/v1/assignments/${assignmentId}/report`)
}

/** 作业答题记录（批改页） */
export interface AssignmentAnswersQuestion {
  questionId: string
  questionText: string
  userAnswer: string
  correctAnswer?: string | null
  isCorrect?: boolean | null
  analysis?: string | null
  hasStandardAnswer: boolean
}

export interface AssignmentAnswers {
  assignmentId: number
  questions: AssignmentAnswersQuestion[]
  score?: number | null
  totalQuestions: number
  correctCount: number
  wrongCount: number
  correctRate: number
}

export function fetchAssignmentAnswers(assignmentId: number) {
  return get<AssignmentAnswers>(`/api/v1/assignments/${assignmentId}/answers`)
}
