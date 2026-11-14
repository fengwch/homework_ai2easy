<template>
  <view class="container">
    <!-- 1. 输入屏 -->
    <view v-if="step === 'input'" class="section">
      <textarea
        v-model="rawText"
        class="paste-box"
        placeholder="把老师发的作业原文整段粘贴进来"
      />
      <view class="row">
        <input v-model="studentName" class="field" placeholder="孩子姓名（可选）" />
        <input v-model="dateText" class="field" placeholder="日期 YYYY-MM-DD（可选）" />
      </view>
      <button class="btn primary" :disabled="working" @click="doParse">
        {{ working ? '解析中...' : '解析作业' }}
      </button>
    </view>

    <!-- 2. 确认屏 -->
    <view v-else-if="step === 'confirm'" class="section">
      <view v-if="pendingList.length > 0" class="pending-box">
        <text class="pending-title">以下内容需要确认（{{ pendingList.length }}）</text>
        <view v-for="p in pendingList" :key="p.id" class="pending-row">
          <text class="pending-text">{{ p.text }}</text>
          <view class="pending-actions">
            <button class="mini" @click="editPending(p)">改第 1 项</button>
            <button class="mini ghost" @click="doDismiss(p.id)">忽略</button>
          </view>
        </view>
      </view>

      <view v-for="item in items" :key="item.seq" class="item-card">
        <view class="item-head">
          <text class="item-subject">{{ item.subject || '未分类' }}</text>
          <text class="badge" :class="item.priority">{{ item.priority === 'high' ? '重要' : '普通' }}</text>
        </view>
        <text class="item-task">{{ item.seq }}. {{ item.task }}</text>
        <text v-if="item.quantity" class="item-quantity">数量：{{ item.quantity }}</text>
        <text v-if="item.requirements.length" class="item-req">要求：{{ item.requirements.join('、') }}</text>
      </view>

      <view v-if="extraList.length" class="extra-box">
        <text class="extra-title">别忘了</text>
        <text v-for="e in extraList" :key="e" class="extra-text">· {{ e }}</text>
      </view>

      <button class="btn primary" :disabled="working" @click="doRender">
        {{ working ? '生成中...' : '确认无误，生成目标图' }}
      </button>
    </view>

    <!-- 3. 下载屏 -->
    <view v-else class="section">
      <image v-if="imageUrl" :src="imageUrl" mode="widthFix" class="result-image" />
      <text v-if="usedPlaceholder" class="hint">当前使用占位底图，仅用于核对排版</text>
      <text v-for="(issue, i) in issues" :key="i" class="hint warn">[{{ issue.zone }}] {{ issue.text }}：{{ issue.reason }}</text>
      <view class="row">
        <picker :range="skinNames" :value="skinIndex" @change="onSkinChange">
          <button class="btn">配色：{{ skinNames[skinIndex] }}</button>
        </picker>
        <button class="btn primary" @click="doRender">换配色重新生成</button>
      </view>
      <button class="btn ghost" @click="restart">再来一份</button>
    </view>

    <text v-if="errorText" class="error">{{ errorText }}</text>
  </view>
</template>

<script setup lang="ts">
import { ref } from 'vue'
  import {
    parseText,
    correctField,
    dismissPending,
    renderHomework,
    imageUrl as toImageUrl
  } from './homeworkCompass'


const SKINS = ['dinosaur', 'space', 'ocean', 'pixel', 'candy']
const skinNames = ['恐龙', '太空', '海底', '像素', '糖果']

const step = ref('input')
const rawText = ref('')
const studentName = ref('')
const dateText = ref('')
const working = ref(false)
const errorText = ref('')
const hw = ref(null)
const items = ref([])
const pendingList = ref([])
const extraList = ref([])
const skinIndex = ref(0)
const imageUrl = ref('')
const usedPlaceholder = ref(false)
const issues = ref([])

function applyHomework(next) {
  hw.value = next
  items.value = next.items
  pendingList.value = next.pending
  extraList.value = next.extras
}

async function doParse() {
  if (!rawText.value.trim()) {
    errorText.value = '请先粘贴作业内容'
    return
  }
  await run(async () => {
    applyHomework(await parseText(rawText.value, studentName.value, dateText.value))
    step.value = 'confirm'
  })
}

// ponytail: 只提供「改第 1 项」，足够销掉"带材料"这类片段；要按项编辑再加字段选择器
async function editPending(p) {
  const seq = p.related_seq || 1
  const target = items.value.find((i) => i.seq === seq)
  await run(async () => {
    applyHomework(await correctField(hw.value, seq, 'task',
      `${target?.task || ''} ${p.text}`.trim()))
  })
}

async function doDismiss(id) {
  await run(async () => applyHomework(await dismissPending(hw.value, id)))
}

async function doRender() {
  await run(async () => {
    const result = await renderHomework(hw.value, 'quest-map', SKINS[skinIndex.value])
    imageUrl.value = toImageUrl(result.url)
    usedPlaceholder.value = result.used_placeholder
    issues.value = result.issues
    step.value = 'result'
  })
}

function onSkinChange(e) {
  skinIndex.value = e.detail.value
}

function restart() {
  step.value = 'input'
  imageUrl.value = ''
  issues.value = []
  errorText.value = ''
}

async function run(task) {
  working.value = true
  errorText.value = ''
  try {
    await task()
  } catch (err) {
    // 409 = pending 未处理完，后端已给出逐条原因
    errorText.value = err?.message || '请求失败'
  } finally {
    working.value = false
  }
}
</script>

<style scoped>
.container {
  min-height: 100vh;
  padding: 24rpx 32rpx;
  background: #f5f5f5;
}

.section {
  display: flex;
  flex-direction: column;
  gap: 24rpx;
}

.paste-box {
  width: 100%;
  height: 360rpx;
  padding: 24rpx;
  background: #fff;
  border-radius: 16rpx;
  font-size: 28rpx;
}

.row {
  display: flex;
  gap: 16rpx;
}

.field {
  flex: 1;
  padding: 20rpx 24rpx;
  background: #fff;
  border-radius: 12rpx;
  font-size: 26rpx;
}

.btn {
  height: 80rpx;
  line-height: 80rpx;
  border-radius: 12rpx;
  font-size: 28rpx;
  color: #333;
  background: #f0f0f0;
  border: none;
}

.btn.primary {
  color: #fff;
  background: #667eea;
}

.btn.ghost {
  color: #667eea;
  background: #fff;
}

.pending-box {
  padding: 24rpx;
  background: #fff3f3;
  border: 2rpx solid #f5c2c7;
  border-radius: 16rpx;
}

.pending-title {
  display: block;
  margin-bottom: 16rpx;
  font-size: 28rpx;
  font-weight: bold;
  color: #b02a37;
}

.pending-row {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 16rpx;
  padding: 12rpx 0;
}

.pending-text {
  flex: 1;
  font-size: 26rpx;
  color: #721c24;
}

.pending-actions {
  display: flex;
  gap: 12rpx;
}

.mini {
  padding: 0 20rpx;
  height: 56rpx;
  line-height: 56rpx;
  font-size: 24rpx;
  border-radius: 8rpx;
  color: #fff;
  background: #dc3545;
  border: none;
}

.mini.ghost {
  color: #666;
  background: #eee;
}

.item-card {
  padding: 24rpx;
  background: #fff;
  border-radius: 16rpx;
}

.item-head {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: 12rpx;
}

.item-subject {
  font-size: 30rpx;
  font-weight: bold;
  color: #333;
}

.badge {
  padding: 4rpx 16rpx;
  border-radius: 16rpx;
  font-size: 22rpx;
  background: #eee;
  color: #666;
}

.badge.high {
  background: #f8d7da;
  color: #721c24;
}

.item-task {
  font-size: 28rpx;
  color: #333;
}

.item-quantity, .item-req {
  display: block;
  margin-top: 8rpx;
  font-size: 24rpx;
  color: #666;
}

.extra-box {
  padding: 24rpx;
  background: #fff8e1;
  border-radius: 16rpx;
}

.extra-title {
  display: block;
  font-size: 28rpx;
  font-weight: bold;
  color: #856404;
}

.extra-text {
  display: block;
  margin-top: 8rpx;
  font-size: 26rpx;
  color: #856404;
}

.result-image {
  width: 100%;
  border-radius: 16rpx;
  background: #fff;
}

.hint {
  font-size: 24rpx;
  color: #999;
}

.hint.warn {
  color: #b02a37;
}

.error {
  display: block;
  margin-top: 24rpx;
  font-size: 26rpx;
  color: #b02a37;
  white-space: pre-line;
}
</style>
