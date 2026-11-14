// 目标生成器 HTTP 封装的最小自检：用真实 FastAPI（8100）跑一遍 解析 → 修改 → 生成
// 运行：node --test tests/compass/compass-api.test.mjs
import test from 'node:test'
import assert from 'node:assert/strict'

const BASE = process.env.COMPASS_API || 'http://127.0.0.1:8100'
const post = async (path, body) => {
  const res = await fetch(BASE + path, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(body)
  })
  return { status: res.status, body: await res.json() }
}

test('parse → correct → render 全链路', async () => {
  const parsed = await post('/api/parse', { text: '1.数学：完成练习册第12-13页\n2.语文：抄写本课生字每个2遍', name: '小宇' })
  assert.equal(parsed.status, 200)
  assert.equal(parsed.body.data.items.length, 2)

  const fixed = await post('/api/correct', { hw: parsed.body.data, seq: 1, field: 'task', value: '练习册第12-13页（家长检查）' })
  assert.equal(fixed.body.data.items[0].task, '练习册第12-13页（家长检查）')

  const patched = await post('/api/patch', { hw: fixed.body.data, slogan: '小宇的闯关地图' })
  assert.equal(patched.body.data.slogan, '小宇的闯关地图')

  const rendered = await post('/api/render', { hw: patched.body.data, skeleton: 'quest-map', skin: 'space' })
  assert.equal(rendered.status, 200)
  assert.equal(rendered.body.data.width, 2480)
  assert.equal(rendered.body.data.height, 3508)
  assert.equal(rendered.body.data.dpi, 300)
})

test('存在 pending 时拒绝出图（409）', async () => {
  // 故意让覆盖率校验留下缺口：原文有「明天带美术材料」，解析结果却只认领了数学
  const { body } = await post('/api/parse', { text: '1.数学：完成练习册P12-13\n2.明天带美术材料：彩泥' })
  const hw = { ...body.data, items: body.data.items.slice(0, 1), pending: [] }
  hw.pending = [{ id: 'uncovered-1', text: '明天带美术材料', reason: 'uncovered' }]
  const res = await post('/api/render', { hw })
  assert.equal(res.status, 409)
  assert.match(res.body.detail, /待家长确认/)
})
