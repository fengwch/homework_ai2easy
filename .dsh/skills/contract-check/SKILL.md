---
name: contract-check
description: 校验 app → backend → agent 跨仓库调用契约：接口路径、字段命名、端口、认证方式是否三端一致。当用户说"检查契约"、"接口对齐了吗"、"改了接口帮我核对"时使用。
---

# 跨仓库契约校验（app → backend → agent）

调用链：`app(uni-app x) --HTTP--> backend(Go Kratos) --HTTP:8011--> agent(Python FastAPI)`，
外加 app 对 HomeworkCompass 目标图能力的对接（五屏流程）。

## 校验清单

1. **端口与地址**：
   - agent 服务端口 8011；backend 配置中引用 agent 的地址是否一致（configs/config*.yaml）
   - app 请求域名配置（manifest.json / 环境配置）指向 backend，非 agent
2. **接口路径**：backend 对 app 暴露的 HTTP 路由（api/**/*.proto 生成）与 app/frontend 的
   api/*.ts 调用路径逐条比对
3. **字段命名**：同一业务字段在 app(TS) / backend(Go) / agent(Python) 三端的命名与类型对齐；
   发现蛇形/驼峰混用、类型不匹配、可选性不一致的，逐条列出
4. **HomeworkCompass 对接**：app 五屏流程调用的 compass API（src/homework_compass/api.py）
   与 app 侧调用参数比对
5. **认证链**：JWT/微信登录只在 backend 侧；agent 不应出现认证逻辑，compass 服务如需鉴权单列

## 输出

契约核对表：`字段/接口 | app 侧 | backend 侧 | agent/compass 侧 | 结论`，
不一致项给"建议改哪端"（改字段命名必须三端协调，单端擅改即违规）。

## 边界

- 全程只读。
- 本 skill 只做核对与建议，不做修复；修复走 dispatch-task 拆单派发。
- 密钥字段只报字段名。
