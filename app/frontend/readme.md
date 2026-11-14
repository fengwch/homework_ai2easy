# 作业 AI 助手 · 前端

基于 uni-app x 的跨平台家长端应用，支持 H5、小程序、App。页面以 `.uvue` 为扩展名。

[uni-app x 开发文档](https://doc.dcloud.net.cn/uni-app-x/)

---

## 一、技术栈

- **框架**：uni-app x + Vue 3 + TypeScript
- **状态**：Pinia
- **构建**：Vite
- **引擎**：HBuilderX ^3.99

---

## 二、环境要求

- Node.js（推荐 LTS）
- HBuilderX ^3.99（用于 App/小程序构建）
- 后端 API 服务（开发时默认 `http://localhost:8000`）

---

## 三、配置说明

### 3.1 环境变量

在 `frontend/` 根目录创建或修改 `.env`：

```env
# 开发环境：使用相对路径，通过 Vite 代理转发到后端
# 生产环境：设置为完整的后端 API 地址，例如：https://api.example.com
VITE_API_BASE_URL=http://localhost:8000
```

| 变量 | 说明 |
|------|------|
| `VITE_API_BASE_URL` | 后端 API 基准地址，用于请求与静态资源 |

### 3.2 Vite 代理（vite.config.ts）

开发模式下，`/api` 请求会代理到 `http://localhost:8000`：

```ts
server: {
  port: 5173,
  proxy: {
    '/api': {
      target: 'http://localhost:8000',
      changeOrigin: true,
      secure: false,
    },
  },
},
```

### 3.3 env.js（运行配置）

`env.js` 用于 H5、微信小程序、App 的运行配置，例如：

- H5：headless、executablePath
- mp-weixin：port、account、launch
- app-plus：Android/iOS 模拟器 ID 与路径

修改前请参考当前 `env.js` 内容，按本机环境调整。

### 3.4 manifest.json（应用配置）

应用名称、版本、平台能力等在此配置。打包前需修改：

- `name`：应用名称
- `appid`：应用 ID
- 微信小程序：`mp-weixin.appid`
- 其他平台能力按需开启/关闭

---

## 四、使用说明

### 4.1 安装依赖

```bash
cd frontend
npm install
```

### 4.2 启动开发服务器（H5）

```bash
npm run dev:h5
```

浏览器访问：`http://localhost:5173/web/#/`

> 确保后端服务已启动（默认 `http://localhost:8000`），否则接口会失败。

### 4.3 构建

```bash
# H5
npm run build:h5

# 微信小程序
npm run build:mp-weixin

# App
# 使用 HBuilderX 打开项目，菜单：发行 -> 原生 App-云打包
```

### 4.4 运行到真机/模拟器

- **H5**：`npm run dev:h5` 后直接用浏览器访问
- **App**：在 HBuilderX 中运行到 iOS 模拟器 / Android 模拟器或真机
- **微信小程序**：运行到微信开发者工具（需先 `npm run build:mp-weixin`）

### 4.5 微信小程序开发说明

#### 请求域名限制

微信小程序要求所有 `wx.request` / `uni.request` 的域名必须在「request 合法域名」中配置，且：

- 仅支持 **HTTPS**（正式环境）
- **localhost** 不能加入合法域名

开发时若请求 `http://localhost:8000` 等地址，会报错：`request:fail url not in domain list`。

#### 开发阶段：允许 localhost 调用 API

本项目已在 `manifest.json`（mp-weixin.setting）和 `project.config.json`（setting）中配置 `urlCheck: false`，本地开发时默认允许请求 `localhost` 等地址，无需在微信开发者工具中手动勾选「不校验合法域名」。

若仍出现 `request:fail url not in domain list`，请在微信开发者工具中：

1. 打开右上角 **「详情」**
2. 切换到 **「本地设置」**
3. 勾选：**「不校验合法域名、web-view（业务域名）、TLS 版本以及 HTTPS 证书」**

#### 生产环境

正式上线时：

- 在 [微信公众平台](https://mp.weixin.qq.com) → 小程序 → 开发管理 → 开发设置 → **服务器域名** → **request 合法域名** 中配置后端接口域名（如 `https://api.xxx.com`）
- 将 `.env` 或构建配置中的 `VITE_API_BASE_URL` 改为正式域名（HTTPS）

#### 预览时发生网络错误

**现象**：真机调试正常，但点击「预览」生成二维码扫码后出现「网络错误」或请求失败。

**原因**：预览与正式版会校验「request 合法域名」，不再使用开发者工具里的「不校验合法域名」。

**处理步骤**：

1. 登录 [微信公众平台](https://mp.weixin.qq.com) → 你的小程序 → **开发管理** → **开发设置** → **服务器域名**。
2. 在 **request 合法域名** 中新增你的 API 域名，例如：`https://hw.gameyeah.net`（不要带路径，不要带末尾斜杠）。
3. 确认该域名已启用 **HTTPS** 且证书有效；若为自签名或过期，预览/正式版也会报网络错误。
4. 保存后等待几分钟生效，再重新生成预览二维码测试。

若头像等图片也加载失败，需在 **downloadFile 合法域名** 中配置同一域名（或图片所在 CDN 域名）。

#### downloadFile:fail 小程序要求的 TLS 版本必须大于等于 1.2

**现象**：导出 PDF 或下载文件时出现 `downloadFile:fail 小程序要求的 TLS 版本必须大于等于 1.2`。

**原因**：微信小程序要求所有网络请求（含 `uni.downloadFile`）的域名必须使用 **TLS 1.2 或以上**。若后端或 CDN 仍使用 TLS 1.0/1.1，会触发该错误。

**处理步骤**（需后端/运维配合）：

1. 确认 `data.url` 或下载资源所在域名的 **服务器**（Nginx、负载均衡、云厂商）已启用 TLS 1.2（及以上），并**关闭** TLS 1.0、TLS 1.1。
2. 若使用 Nginx，可配置：`ssl_protocols TLSv1.2 TLSv1.3; ssl_prefer_server_ciphers on;`，然后重载配置。
3. 若使用云厂商（阿里云、腾讯云等）负载均衡或 CDN，在控制台中将 HTTPS 的 TLS 版本设置为「仅 1.2 及以上」或「1.2 和 1.3」。
4. 修改后重启服务或等待 CDN 生效，再在小程序中重试下载。

同时确认该域名已在公众平台 **downloadFile 合法域名** 中配置。

**若后端返回的 PDF 下载地址是 localhost**（例如 `https://localhost:8000/api/v1/contents/pdf-download?token=xxx`）：小程序无法使用该地址（设备上的 localhost 不是开发机，且本地 TLS 通常不满足要求）。处理方式二选一：
- **推荐**：后端在生成 PDF 时使用**正式域名**拼装下载链接（如配置 `PUBLIC_BASE_URL=https://hw.gameyeah.net`），不要用请求里的 Host（localhost）。
- **临时**：前端已做兼容：当返回的 URL 为 localhost/127.0.0.1 时，会替换为 `.env` 里配置的 `VITE_API_BASE_URL` 的域名再下载；因此小程序测试时请把 `VITE_API_BASE_URL` 设为已部署的 HTTPS 地址（如 `https://hw.gameyeah.net`），并确保该后端就是生成 PDF 的服务（token 在该环境有效）。

## 五、目录结构

```
frontend/
├── api/                 # API 接口
│   ├── auth.ts
│   ├── assignment.ts
│   ├── child.ts
│   ├── content.ts
│   ├── http.ts
│   └── user.ts
├── components/          # 组件
│   ├── business/        # 业务组件
│   └── common/          # 通用组件
├── pages/               # 页面
│   ├── auth/            # 登录、注册、忘记密码
│   ├── child/           # 儿童档案
│   ├── assignment/      # 作业扫描、上传、详情、列表、批改、解题引导
│   ├── content/         # 内容预览
│   ├── learning/        # 故事阅读、答题、学习报告
│   ├── print/           # 打印预览
│   ├── profile/         # 个人中心
│   ├── parent/          # 家长仪表盘、作业管理、设置
│   └── reward/          # 奖励中心、排行榜
├── stores/              # Pinia 状态
├── utils/               # 工具函数
├── .env                 # 环境变量（需自行创建/配置）
├── env.js               # 运行配置（H5/小程序/App）
├── vite.config.ts       # Vite 配置
├── pages.json           # 页面路由
├── manifest.json        # 应用配置（appid、版本、平台能力、微信 appid 等）
└── Info.plist           # iOS 权限与 URL Scheme
```

---

## 六、主要页面路由

| 路径 | 说明 |
|------|------|
| `/pages/auth/login` | 登录 |
| `/pages/auth/register` | 注册 |
| `/pages/auth/forgot-password` | 忘记密码 |
| `/pages/child/list` | 儿童档案列表（登录后首页） |
| `/pages/child/edit` | 创建/编辑儿童档案 |
| `/pages/assignment/scan` | 扫描作业 |
| `/pages/assignment/upload` | 上传作业 |
| `/pages/assignment/list` | 作业列表 |
| `/pages/assignment/detail` | 作业详情 |
| `/pages/assignment/recognize` | 识别结果 |
| `/pages/assignment/review` | 作业批改 |
| `/pages/assignment/guide` | 解题引导 |
| `/pages/learning/story` | 故事学习 |
| `/pages/learning/answer` | 在线答题 |
| `/pages/content/preview` | 内容预览 |
| `/pages/print/preview` | 打印预览 |
| `/pages/profile/index` | 个人中心 |

---

## 七、权限说明（Info.plist）

iOS 所需权限（相册、位置等）在 `Info.plist` 中配置。如接入新能力，需在此补充对应权限描述。

---

## 八、注意事项

1. **API 地址**：生产环境务必修改 `.env` 中的 `VITE_API_BASE_URL`，指向正式后端地址。
2. **代理**：开发时若后端端口不是 8000，需同步修改 `vite.config.ts` 的 proxy 和 `.env`。
3. **页面测试**：以 `.uvue` 为扩展名的页面，可配套 `.test.js` 做自动化测试。
4. **提交检查**：项目配置了 `check-commit`，提交前会自动执行校验。
