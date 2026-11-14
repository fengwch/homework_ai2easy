// ponytail: 自定义 env 变量在 uni-app x 没有类型声明，单独取免得污染其它模块
export function compassApiBase(): string {
  return (import.meta as any).env?.VITE_COMPASS_API || ''
}
