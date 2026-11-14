# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in the `app/frontend` uni-app x frontend.

## Project Overview

The app is the cross-platform client for the children's homework tutoring product. It targets H5, WeChat Mini Program (MP), iOS, Android, and HarmonyOS through **uni-app x** (uni-app 2.0) with Vue 3 Composition API + TypeScript + Vite. Primary platforms are H5 and WeChat MP.

## Common Commands

### H5 Development

Build is driven by HBuilderX (v3.99+ required), with Vite as the bundler. There is no standard `npm run dev`.

- Open `app/frontend` in **HBuilderX** → Run → Run to browser / H5.
- If using CLI: `npx uni` (uni-app x CLI) for preview and build. Check HBuilderX docs for exact CLI flags.

### WeChat MP

- HBuilderX → Run → WeChat Developer Tools.
- Ensure `manifest.json` → MP Weixin → `urlCheck: false` for local dev.
- WeChat Developer Tools must have TLS 1.2+, request domains, and downloadFile domains configured for the backend.

### Tests

Jest is configured for unit tests:
```bash
cd app/frontend
npx jest
npx jest --watch
```

## Architecture

### Technology Stack

- **Framework**: uni-app x (uni-app 2.0), Vue 3 Composition API
- **Language**: TypeScript (`.ts`, `.uts` for uni-app-specific files)
- **State**: Pinia (`stores/`)
- **Bundler**: Vite (`vite.config.ts`)
- **UI**: uni-ui components (via `uni_modules/`), plus custom Vant (`wxcomponents/vant`) and Widget UI (`wxcomponents/widget-ui`)
- **HTTP**: `uni.request` wrapper in `api/http.ts` — **not axios** (uni-app x runtime does not guarantee axios compatibility)

### Directory Layout

| Directory | Purpose |
|---|---|
| `pages/` | One folder per page domain (`auth`, `assignment`, `child`, `content`, `learning`, `parent`, `print`, `profile`, `reward`, `tabBar`) |
| `components/` | Reusable Vue components (`business/`, `common/`, ...) |
| `api/` | API service wrappers per domain (`auth.ts`, `user.ts`, `child.ts`, `assignment.ts`, `content.ts`, `voice.ts`, `http.ts`) |
| `stores/` | Pinia stores (`app.ts`, `user.ts`, `child.ts`, `assignment.ts`) |
| `utils/` | Shared utility functions |
| `styles/` | Global / shared styles |
| `uni_modules/` | Third-party uni-app plugins |
| `wxcomponents/` | WeChat custom components (Vant, widget-ui, wxml-to-canvas) |
| `static/` | Static assets (images, fonts) |
| `api/` (package.json sibling) | No — API code is under `app/frontend/api/`, not the root `api/` |

### Page Files

Pages are written in **`.uvue`** (uni-app x Vue SFC), not `.vue`. Main entry points: `App.uvue` and `main.uts`.

Page routes are declared in `pages.json` (do not edit manually for large refactors — use HBuilderX page creation or understand the schema).

### HTTP Client (`api/http.ts`)

All network requests go through `api/http.ts`, which wraps `uni.request`:

- `BASE_URL` from `import.meta.env.VITE_API_BASE_URL`
- Auto-attaches `Authorization: Bearer <token>` from `stores/user`
- Auto-attaches `X-Platform` and `X-Device-Id` headers
- Timeout default: 10s
- On `401`: calls `userStore.logout()` and redirects to `/pages/auth/login`
- On business error (`code !== 0`): shows toast with `message`

Helper exports: `get`, `post`, `put`, `del`, `useHttpLoading()`.

**Rule**: never call `uni.request` directly outside `api/http.ts`; always use the wrapper or the domain API modules.

### API Modules (`api/*.ts`)

One file per backend domain, mirroring backend service boundaries:

| Module | Backend Service | Example Route |
|---|---|---|
| `auth.ts` | AuthService | `/api/v1/auth/login` |
| `user.ts` | UserService | `/api/v1/user/profile` |
| `child.ts` | ChildService | `/api/v1/children` |
| `assignment.ts` | AssignmentService | `/api/v1/assignments/upload` |
| `content.ts` | ContentService | `/api/v1/content/...` |
| `voice.ts` | AI agent (via backend proxy) | TTS endpoints |

### State Management (`stores/`)

Pinia stores (Composition API style):
- `user.ts` — token, user info, login/logout/refresh
- `child.ts` — current child profile, child list
- `assignment.ts` — assignment list, current assignment state
- `app.ts` — global UI state (theme, loading, etc.)

Use `storeToRefs` when reading reactive state in components.

### Environment Variables

| Variable | Purpose |
|---|---|
| `VITE_API_BASE_URL` | Backend base URL |
| `VUE_APP_API_BASE_URL` | Fallback (legacy) |

These are consumed at build time via Vite. For H5 local dev, set in HBuilderX run config or `.env` file.

## Platform-Specific Rules

### WeChat Mini Program

- `manifest.json` → `mp-weixin.urlCheck: false` (dev only)
- Request / downloadFile / uploadFile domains must be whitelisted in WeChat MP Console
- TLS 1.2+ required; no self-signed certs
- `wxcomponents/` holds Vant WeChat components; register in page JSON when needed

### H5

- Standard browser CORS applies; backend must allow the H5 origin
- `Content-Type: application/json` auto-added in H5 path
- `uni.getSystemInfoSync()` available

### App (iOS / Android / Harmony)

- Uses `.uvue` native rendering where supported
- `nativeResources/android` and `nativeResources/ios` for platform-specific manifests / assets
- `harmony-configs/` for HarmonyOS specific config

## Code Style

- 2-space indent (standard for uni-app x / Vue SFC in this project)
- Single quotes for strings unless escaping required
- Composition API with `<script setup>` preferred
- TypeScript types on function params and returns
- Use `uni.xxx` APIs for platform capabilities (file, network, storage, media)

## Testing

- Jest for unit tests; `jest.config.js` and `jest-setup.js` at repo root
- Page tests under `pages/pages.test.js`
- Mock `uni.request` in tests rather than mocking network layers deep inside uni-app runtime

## Cross-Project Contracts

- This app consumes the **backend** Go Kratos service (HTTP on port 8000).
- Never talk directly to the Python `agent/` service; always route through backend's `ContentService` / `AssignmentService`.
- Backend error response shape: `{ code: number, message: string, data: T }`. `code === 0` is success.
- Backend fields may arrive in either snake_case or camelCase (legacy dual format); front-end types currently declare both for safety.
