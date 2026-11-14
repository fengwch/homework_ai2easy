# SMS 服务快速配置指南

## 当前状态

✅ **开发模式（Mock）**：当前已配置为开发模式，验证码会打印在日志中，不会实际发送短信。

## 切换到生产环境

### 步骤 1: 选择短信服务商

推荐使用 **阿里云短信服务**（稳定性高，到达率高）

### 步骤 2: 在服务商平台完成配置

#### 阿里云配置步骤：

1. **开通服务**
   - 登录 [阿里云控制台](https://ecs.console.aliyun.com/)
   - 进入 **短信服务** > **国内消息**
   - 完成实名认证

2. **获取 AccessKey**
   - 进入 **访问控制** > **用户** > **创建用户**
   - 创建 AccessKey（保存 AccessKey ID 和 Secret）
   - 授予权限：`AliyunDysmsFullAccess`

3. **申请短信签名**
   - 进入 **短信服务** > **国内消息** > **签名管理**
   - 添加签名：`作业助手`（或你的应用名称）
   - 等待审核通过（1-2小时）

4. **申请短信模板**
   - 进入 **短信服务** > **国内消息** > **模板管理**
   - 添加模板，内容示例：
     ```
     您的验证码是${code}，5分钟内有效，请勿泄露给他人。
     ```
   - 等待审核通过

### 步骤 3: 更新配置文件

编辑 `configs/config.yaml`：

```yaml
sms:
  expires_in: 300s
  provider: aliyun  # 改为 aliyun
  access_key_id: "LTAI5txxxxxxxxxxxxx"  # 填写你的 AccessKey ID
  access_key_secret: "xxxxxxxxxxxxxxxxxxxxxxxxxxxxx"  # 填写你的 AccessKey Secret
  sign_name: "作业助手"  # 填写你申请的签名名称
  template_code: "SMS_123456789"  # 填写你申请的模板代码
  region: "cn-hangzhou"  # 区域（通常使用 cn-hangzhou）
```

### 步骤 4: 安装依赖

```bash
go get github.com/aliyun/alibaba-cloud-sdk-go/services/dysmsapi
go mod tidy
```

### 步骤 5: 实现发送逻辑

将 `internal/pkg/sms/aliyun_example.go` 中的代码集成到 `internal/pkg/sms/sms.go` 的 `sendAliyunSMS` 方法中。

### 步骤 6: 重新生成配置代码

```bash
make api
```

### 步骤 7: 重新编译和启动

```bash
make wire
make build
./bin/server
```

### 步骤 8: 测试

```bash
# 发送验证码
curl -X POST http://localhost:8000/api/v1/auth/send-sms \
  -H "Content-Type: application/json" \
  -d '{
    "phone": "13800138000",
    "scene": "login"
  }'

# 检查手机是否收到短信
# 检查服务日志确认发送状态
```

## 安全建议

⚠️ **重要**：不要将 AccessKey 提交到 Git！

1. **使用环境变量**：
   ```yaml
   sms:
     access_key_id: "${SMS_ACCESS_KEY_ID}"
     access_key_secret: "${SMS_ACCESS_KEY_SECRET}"
   ```

2. **使用生产环境配置文件**：
   - 创建 `configs/config.prod.yaml`（不提交到 Git）
   - 在 `.gitignore` 中添加：`configs/*.prod.yaml`

3. **使用 Kubernetes Secret**：
   ```yaml
   env:
     - name: SMS_ACCESS_KEY_ID
       valueFrom:
         secretKeyRef:
           name: sms-secret
           key: access-key-id
   ```

## 其他服务商

### 腾讯云

1. 安装依赖：`go get github.com/tencentcloud/tencentcloud-sdk-go/tencentcloud/sms/v20210111`
2. 配置 provider: `tencent`
3. 参考文档：`docs/sms-configuration.md`

### 华为云

1. 安装依赖：`go get github.com/huaweicloud/huaweicloud-sdk-go-v3`
2. 配置 provider: `huawei`
3. 参考文档：`docs/sms-configuration.md`

## 详细文档

完整的配置文档请参考：[docs/sms-configuration.md](sms-configuration.md)

## 常见问题

**Q: 如何知道当前是开发模式还是生产模式？**

A: 查看配置文件中的 `sms.provider` 字段：
- `mock` 或空 = 开发模式（不发送短信）
- `aliyun/tencent/huawei` = 生产模式（实际发送短信）

**Q: 开发模式下的验证码在哪里查看？**

A: 查看服务日志，搜索 "send sms code" 或 "[MOCK]"

**Q: 配置后仍然收不到短信？**

A: 
1. 检查签名和模板是否审核通过
2. 检查 AccessKey 权限是否正确
3. 查看服务日志中的错误信息
4. 在服务商控制台查看发送记录
