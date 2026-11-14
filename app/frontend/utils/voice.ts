import { ref } from 'vue'
import { submitVoiceSynthesize, getVoiceSynthesizeStatus } from '@/api/voice'

const POLL_INTERVAL = 800
const POLL_MAX = 120

/** 将 base64 转为 data URL，供 H5 播放 */
function toDataUrl(base64: string, format: string): string {
  const mime = format === 'wav' ? 'audio/wav' : 'audio/mpeg'
  return `data:${mime};base64,${base64}`
}

/**
 * 从后端返回的 base64 音频创建小程序可播放的 src：
 * - H5：使用 data URL
 * - 微信小程序：写入本地临时文件，返回文件路径（iOS 不支持 data:audio/... 播放）
 */
async function createAudioSrcFromBase64(base64: string, format: string): Promise<string> {
  const ext = format === 'wav' ? 'wav' : 'mp3'

  // #ifdef MP-WEIXIN
  const fs = wx.getFileSystemManager()
  const filePath = `${wx.env.USER_DATA_PATH}/voice_${Date.now()}.${ext}`

  await new Promise<void>((resolve, reject) => {
    try {
      fs.writeFile({
        filePath,
        data: base64,
        encoding: 'base64',
        success: () => resolve(),
        fail: (err) => reject(err)
      })
    } catch (e) {
      reject(e as any)
    }
  })

  return filePath
  // #endif

  // #ifndef MP-WEIXIN
  return toDataUrl(base64, format)
  // #endif
}

function sleep(ms: number): Promise<void> {
  return new Promise((resolve) => setTimeout(resolve, ms))
}

/** 语音朗读：异步合成（提交任务 + 轮询状态）并播放，支持暂停/继续。 */
export function useVoicePlay() {
  const loading = ref(false)
  const playing = ref(false)
  const paused = ref(false)
  let audioCtx: InnerAudioContext | null = null
  let pollAborted = false

  function stop() {
    pollAborted = true
    if (audioCtx) {
      audioCtx.stop()
      audioCtx.destroy()
      audioCtx = null
    }
    playing.value = false
    paused.value = false
  }

  function pause() {
    if (audioCtx && playing.value && !paused.value) {
      audioCtx.pause()
      paused.value = true
    }
  }

  function resume() {
    if (audioCtx && paused.value) {
      audioCtx.play()
      paused.value = false
    }
  }

  async function speak(
    text: string,
    options?: { voice?: string; format?: string; speech_rate?: number }
  ): Promise<void> {
    const toRead = (text || '').trim()
    if (!toRead) {
      uni.showToast({ title: '没有可朗读的内容', icon: 'none' })
      return
    }

    stop()
    pollAborted = false
    loading.value = true
    try {
      const { task_id } = await submitVoiceSynthesize({
        text: toRead,
        voice: options?.voice ?? 'xiaoyun',
        format: options?.format ?? 'mp3',
        speech_rate: options?.speech_rate ?? 0
      })

      let count = 0
      let statusRes: { status: string; audio_data?: string; format?: string; message?: string } | null = null
      while (count < POLL_MAX) {
        if (pollAborted) return
        statusRes = await getVoiceSynthesizeStatus(task_id)
        if (statusRes.status === 'completed' && statusRes.audio_data) {
          break
        }
        if (statusRes.status === 'failed') {
          uni.showToast({ title: statusRes.message || '语音合成失败', icon: 'none' })
          return
        }
        await sleep(POLL_INTERVAL)
        count++
      }

      if (pollAborted) return
      if (!statusRes || statusRes.status !== 'completed' || !statusRes.audio_data) {
        uni.showToast({ title: '合成超时，请稍后重试', icon: 'none' })
        return
      }

      const src = await createAudioSrcFromBase64(statusRes.audio_data, statusRes.format || 'mp3')
      audioCtx = uni.createInnerAudioContext()
      audioCtx.src = src
      playing.value = true

      audioCtx.onPlay(() => {
        playing.value = true
        paused.value = false
      })
      audioCtx.onPause(() => {
        paused.value = true
      })
      audioCtx.onEnded(() => {
        playing.value = false
        paused.value = false
        if (audioCtx) {
          audioCtx.destroy()
          audioCtx = null
        }
      })
      audioCtx.onError((err) => {
        console.error('语音播放错误:', err)
        playing.value = false
        paused.value = false
        if (audioCtx) {
          audioCtx.destroy()
          audioCtx = null
        }
        uni.showToast({ title: '播放失败', icon: 'none' })
      })

      audioCtx.play()
      paused.value = false
    } catch (e) {
      if (!pollAborted) {
        console.error('语音合成请求失败:', e)
        uni.showToast({ title: '朗读失败，请稍后重试', icon: 'none' })
      }
    } finally {
      loading.value = false
    }
  }

  return { loading, playing, paused, speak, pause, resume, stop }
}
