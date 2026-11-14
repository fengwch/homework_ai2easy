import { get, post } from './http'

/** 语音合成请求参数 */
export interface VoiceSynthesizeParams {
  /** 要朗读的文本，支持任意长度 */
  text: string
  /** 发音人，默认 xiaoyun。儿童友好：xiaoyun、ruoxi、siqi */
  voice?: string
  /** 音频格式，默认 mp3，可选 wav */
  format?: string
  /** 语速 -500～500，0 为默认 */
  speech_rate?: number
}

/** 提交合成任务响应 */
export interface VoiceSynthesizeSubmitResult {
  task_id: string
}

/** 合成状态：pending | processing | completed | failed */
export type VoiceSynthesizeStatus = 'pending' | 'processing' | 'completed' | 'failed'

/** 查询合成状态响应 */
export interface VoiceSynthesizeStatusResult {
  status: VoiceSynthesizeStatus
  audio_data?: string
  format?: string
  message?: string
}

/** 提交语音合成任务（异步），需登录，返回 task_id */
export function submitVoiceSynthesize(params: VoiceSynthesizeParams) {
  return post<VoiceSynthesizeSubmitResult>('/api/v1/voice/synthesize', {
    text: params.text,
    voice: params.voice ?? 'xiaoyun',
    format: params.format ?? 'mp3',
    speech_rate: params.speech_rate ?? 0
  })
}

/** 查询语音合成状态，需登录。status 为 completed 时 data 含 audio_data、format */
export function getVoiceSynthesizeStatus(taskId: string) {
  return get<VoiceSynthesizeStatusResult>('/api/v1/voice/synthesize/status', { task_id: taskId })
}
