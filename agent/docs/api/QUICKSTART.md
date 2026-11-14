# API 快速开始指南

## 访问 Swagger UI

启动服务后，访问以下地址查看和测试 API：

```
http://localhost:8000/swagger
```

Swagger UI 提供了：
- 完整的 API 文档
- 交互式 API 测试
- 请求/响应示例
- 参数说明

## 认证方式

大部分 API 需要 JWT Token 认证。获取 Token 的方式：

1. **手机号验证码登录**
   ```bash
   curl -X POST http://localhost:8000/api/v1/auth/login \
     -H "Content-Type: application/json" \
     -d '{
       "phone": "13800138000",
       "code": "123456"
     }'
   ```

2. **密码登录**
   ```bash
   curl -X POST http://localhost:8000/api/v1/auth/password-login \
     -H "Content-Type: application/json" \
     -d '{
       "phone": "13800138000",
       "password": "your_password"
     }'
   ```

3. **使用 Token**
   在请求头中添加：
   ```
   Authorization: Bearer <your_token>
   ```

## 在 Swagger UI 中设置认证

1. 打开 Swagger UI: http://localhost:8000/swagger
2. 点击右上角的 "Authorize" 按钮
3. 在 "BearerAuth" 输入框中输入你的 Token（不需要 "Bearer " 前缀）
4. 点击 "Authorize" 确认
5. 现在可以测试需要认证的接口了

## 常用接口示例

### 1. 发送验证码
```bash
curl -X POST http://localhost:8000/api/v1/auth/send-sms \
  -H "Content-Type: application/json" \
  -d '{
    "phone": "13800138000",
    "scene": "login"
  }'
```

### 2. 获取用户信息
```bash
curl -X GET http://localhost:8000/api/v1/user/profile \
  -H "Authorization: Bearer <your_token>"
```

### 3. 获取儿童列表
```bash
curl -X GET http://localhost:8000/api/v1/children \
  -H "Authorization: Bearer <your_token>"
```

### 4. 创建儿童档案
```bash
curl -X POST http://localhost:8000/api/v1/children \
  -H "Authorization: Bearer <your_token>" \
  -H "Content-Type: application/json" \
  -d '{
    "name": "小明",
    "gender": 1,
    "birth_date": "2015-06-01",
    "grade": "三年级"
  }'
```

## 响应格式

所有接口遵循统一的响应格式：

**成功响应:**
```json
{
  "code": 0,
  "message": "success",
  "data": {
    // 具体数据
  }
}
```

**错误响应:**
```json
{
  "code": 40001,
  "message": "参数格式错误"
}
```

## 错误码说明

- `0`: 成功
- `30000-39999`: 认证错误
- `40000-49999`: 参数错误
- `20000-29999`: 业务错误
- `10000-19999`: 系统错误

详细错误码列表请参考 [后端接口文档.md](后端接口文档.md)

## 开发建议

1. **使用 Swagger UI 进行测试**: 这是最快速的方式来测试 API
2. **查看 OpenAPI 文档**: 访问 `/api/openapi.yaml` 获取完整的 OpenAPI 规范
3. **参考示例代码**: 查看 `后端接口文档.md` 中的详细接口文档
4. **注意认证**: 大部分接口需要 Token，记得先登录获取 Token

## 问题反馈

如有问题，请查看：
- [完整 API 文档](后端接口文档.md)
- [OpenAPI 规范](openapi.yaml)
- Swagger UI: http://localhost:8000/swagger
