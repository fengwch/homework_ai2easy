/**
 * 离线管理工具函数
 * 用于处理离线数据存储和同步
 */

import { setStorage, getStorage } from './storage'

const OFFLINE_QUEUE_KEY = 'offline_queue'
const SYNC_STATUS_KEY = 'sync_status'

export interface OfflineTask {
  id: string
  type: 'create' | 'update' | 'delete'
  resource: string // 资源类型，如 'child', 'assignment'
  data: any
  timestamp: number
  synced: boolean
}

/**
 * 添加离线任务到队列
 */
export function addOfflineTask(task: Omit<OfflineTask, 'id' | 'timestamp' | 'synced'>): void {
  const queue = getOfflineQueue()
  const newTask: OfflineTask = {
    id: `${Date.now()}_${Math.random().toString(36).substr(2, 9)}`,
    timestamp: Date.now(),
    synced: false,
    ...task
  }
  queue.push(newTask)
  setStorage(OFFLINE_QUEUE_KEY, queue)
}

/**
 * 获取离线任务队列
 */
export function getOfflineQueue(): OfflineTask[] {
  return getStorage<OfflineTask[]>(OFFLINE_QUEUE_KEY, []) || []
}

/**
 * 标记任务为已同步
 */
export function markTaskSynced(taskId: string): void {
  const queue = getOfflineQueue()
  const task = queue.find(t => t.id === taskId)
  if (task) {
    task.synced = true
    setStorage(OFFLINE_QUEUE_KEY, queue)
  }
}

/**
 * 移除已同步的任务
 */
export function removeSyncedTasks(): void {
  const queue = getOfflineQueue()
  const unsyncedTasks = queue.filter(t => !t.synced)
  setStorage(OFFLINE_QUEUE_KEY, unsyncedTasks)
}

/**
 * 获取未同步的任务
 */
export function getUnsyncedTasks(): OfflineTask[] {
  const queue = getOfflineQueue()
  return queue.filter(t => !t.synced)
}

/**
 * 检查网络状态
 */
export function checkNetworkStatus(): Promise<boolean> {
  return new Promise((resolve) => {
    uni.getNetworkType({
      success(res) {
        resolve(res.networkType !== 'none')
      },
      fail() {
        resolve(false)
      }
    })
  })
}

/**
 * 监听网络状态变化
 */
export function onNetworkStatusChange(callback: (isConnected: boolean) => void): void {
  uni.onNetworkStatusChange((res) => {
    callback(res.isConnected)
  })
}
