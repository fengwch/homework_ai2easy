/**
 * 表单验证工具函数
 */

/**
 * 验证手机号
 */
export function validatePhone(phone: string): boolean {
  const phoneReg = /^1[3-9]\d{9}$/
  return phoneReg.test(phone)
}

/**
 * 验证验证码（6位数字）
 */
export function validateCode(code: string): boolean {
  const codeReg = /^\d{6}$/
  return codeReg.test(code)
}

/**
 * 验证邮箱
 */
export function validateEmail(email: string): boolean {
  const emailReg = /^[^\s@]+@[^\s@]+\.[^\s@]+$/
  return emailReg.test(email)
}

/**
 * 验证密码（6-20位，包含字母和数字）
 */
export function validatePassword(password: string): boolean {
  const passwordReg = /^(?=.*[A-Za-z])(?=.*\d)[A-Za-z\d]{6,20}$/
  return passwordReg.test(password)
}

/**
 * 验证身份证号
 */
export function validateIdCard(idCard: string): boolean {
  const idCardReg = /(^\d{15}$)|(^\d{18}$)|(^\d{17}(\d|X|x)$)/
  return idCardReg.test(idCard)
}

/**
 * 验证是否为空
 */
export function isEmpty(value: any): boolean {
  if (value === null || value === undefined) {
    return true
  }
  if (typeof value === 'string') {
    return value.trim().length === 0
  }
  if (Array.isArray(value)) {
    return value.length === 0
  }
  if (typeof value === 'object') {
    return Object.keys(value).length === 0
  }
  return false
}

/**
 * 验证年龄（0-120）
 */
export function validateAge(age: number | string): boolean {
  const ageNum = typeof age === 'string' ? parseInt(age) : age
  return !isNaN(ageNum) && ageNum >= 0 && ageNum <= 120
}

/**
 * 验证年级格式（如：一年级、1年级、Grade 1等）
 */
export function validateGrade(grade: string): boolean {
  if (!grade || grade.trim().length === 0) {
    return false
  }
  // 简单的年级验证，可以根据实际需求调整
  return grade.trim().length > 0 && grade.trim().length <= 20
}
