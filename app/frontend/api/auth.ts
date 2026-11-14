import { post } from './http'

export interface UserInfo {
  id: number | string  // 后端可能返回字符串或数字
  phone: string
  nickname?: string
  avatar_url?: string
  avatarUrl?: string  // 后端可能返回驼峰格式
  wechat_openid?: string
  wechatOpenid?: string  // 后端可能返回驼峰格式
  email?: string
  gender?: number
  birthday?: string
  created_at?: string
  updated_at?: string
}

export interface LoginResponse {
  token: string
  user_info?: UserInfo  // 下划线格式（前端期望）
  userInfo?: UserInfo   // 驼峰格式（后端实际返回）
}

export interface SendSmsResponse {
  expires_in: number
}

/**
 * 发送验证码
 * @param phone 手机号
 * @param scene 场景：login（登录）/ reset_password（重置密码）/ bind_phone（绑定/更换手机号）
 */
export function sendSmsCode(phone: string, scene: 'login' | 'reset_password' | 'bind_phone' = 'login') {
  return post<SendSmsResponse>('/api/v1/auth/send-sms', { phone, scene })
}

/**
 * 手机号验证码登录
 */
export function login(phone: string, code: string) {
  return post<LoginResponse>('/api/v1/auth/login', { phone, code })
}

/**
 * 密码登录
 */
export function passwordLogin(phone: string, password: string) {
  return post<LoginResponse>('/api/v1/auth/password-login', { phone, password })
}

/**
 * 微信一键登录
 * @param code 微信 wx.login 返回的 code
 * @param nickName 用户昵称（uni.getUserProfile 获取，可选）
 * @param avatarUrl 头像 URL（uni.getUserProfile 获取，可选）
 */
export function wechatLogin(code: string, nickName?: string, avatarUrl?: string) {
  const body: Record<string, string> = { code }
  if (nickName) body.nickName = nickName
  if (avatarUrl) body.avatarUrl = avatarUrl
  return post<LoginResponse>('/api/v1/auth/wechat-login', body)
}

/**
 * 用户注册
 */
export function register(phone: string, code: string, password?: string, agreed: boolean = true) {
  return post<LoginResponse>('/api/v1/auth/register', {
    phone,
    code,
    password,
    agreed
  })
}

/**
 * 刷新 Token
 */
export function refreshToken() {
  return post<{ token: string }>('/api/v1/auth/refresh')
}

/**
 * 重置密码
 */
export function resetPassword(phone: string, code: string, newPassword: string) {
  return post('/api/v1/auth/reset-password', {
    phone,
    code,
    new_password: newPassword
  })
}
