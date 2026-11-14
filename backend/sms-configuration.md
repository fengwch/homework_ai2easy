# SMS 服务配置指引

本文档说明如何配置和使用正式的短信服务。

## 目录

- [当前实现](#当前实现)
- [支持的短信服务商](#支持的短信服务商)
- [配置步骤](#配置步骤)
- [各服务商详细配置](#各服务商详细配置)
- [测试验证](#测试验证)
- [常见问题](#常见问题)

---

## 当前实现

当前 SMS 服务实现为**开发模式**，仅将验证码存储到 Redis 并打印日志，**不会实际发送短信**。

**开发模式特点：**
- ✅ 验证码生成和存储正常
- ✅ 验证码验证功能正常
- ❌ 不会实际发送短信到手机
- ✅ 适合开发和测试环境

**生产环境必须配置正式的短信服务商！**

---

## 支持的短信服务商

项目支持以下短信服务商：

1. **阿里云短信服务** (推荐)
   - 官方文档：https://help.aliyun.com/product/44282.html
   - 稳定性高，到达率高
   - 支持国内和国际短信

2. **腾讯云短信服务**
   - 官方文档：https://cloud.tencent.com/document/product/382
   - 与微信生态集成好
   - 价格相对较低

3. **华为云短信服务**
   - 官方文档：https://support.huaweicloud.com/msgsms/
   - 企业级服务

4. **自定义实现**
   - 可集成其他短信服务商
   - 需要实现 `SMSProvider` 接口

---

## 配置步骤

### 步骤 1: 更新配置结构

在 `internal/conf/conf.proto` 中添加短信服务商配置：

```protobuf
message SMS {
  google.protobuf.Duration expires_in = 1;
  string provider = 2;  // 服务商: aliyun/tencent/huawei/custom
  string access_key_id = 3;  // AccessKey ID
  string access_key_secret = 4;  // AccessKey Secret
  string sign_name = 5;  // 短信签名
  string template_code = 6;  // 模板代码
  string region = 7;  // 区域（可选）
  string endpoint = 8;  // 自定义端点（可选）
}
```

### 步骤 2: 更新配置文件

在 `configs/config.yaml` 中添加短信服务配置：

```yaml
sms:
  expires_in: 300s  # 验证码过期时间（5分钟）
  provider: aliyun  # 服务商: aliyun/tencent/huawei/custom
  access_key_id: "your-access-key-id"
  access_key_secret: "your-access-key-secret"
  sign_name: "作业助手"  # 短信签名（需要在服务商平台申请）
  template_code: "SMS_123456789"  # 模板代码（需要在服务商平台申请）
  region: "cn-hangzhou"  # 区域（阿里云示例）
```

### 步骤 3: 安装依赖

根据选择的服务商安装对应的 SDK：

**阿里云：**
```bash
go get github.com/aliyun/alibaba-cloud-sdk-go/services/dysmsapi
```

**腾讯云：**
```bash
go get github.com/tencentcloud/tencentcloud-sdk-go/tencentcloud/sms/v20210111
```

**华为云：**
```bash
go get github.com/huaweicloud/huaweicloud-sdk-go-v3
```

### 步骤 4: 实现短信发送

更新 `internal/pkg/sms/sms.go`，实现实际的短信发送逻辑。

### 步骤 5: 重新生成配置代码

```bash
make api
```

---

## 各服务商详细配置

### 阿里云短信服务

#### 1. 开通服务

1. 登录 [阿里云控制台](https://ecs.console.aliyun.com/)
2. 进入 **短信服务** > **国内消息**
3. 完成实名认证
4. 申请短信签名和模板

#### 2. 获取 AccessKey

1. 进入 **访问控制** > **用户** > **创建用户**
2. 创建 AccessKey（保存 AccessKey ID 和 Secret）
3. 授予短信服务权限：`AliyunDysmsFullAccess`

#### 3. 申请短信签名

1. 进入 **短信服务** > **国内消息** > **签名管理**
2. 点击 **添加签名**
3. 填写签名信息（如：作业助手）
4. 等待审核通过（通常 1-2 小时）

#### 4. 申请短信模板

1. 进入 **短信服务** > **国内消息** > **模板管理**
2. 点击 **添加模板**
3. 模板内容示例：
   ```
   您的验证码是${code}，5分钟内有效，请勿泄露给他人。
   ```
4. 等待审核通过

#### 5. 配置文件示例

```yaml
sms:
  expires_in: 300s
  provider: aliyun
  access_key_id: "LTAI5txxxxxxxxxxxxx"
  access_key_secret: "xxxxxxxxxxxxxxxxxxxxxxxxxxxxx"
  sign_name: "作业助手"
  template_code: "SMS_123456789"
  region: "cn-hangzhou"
```

#### 6. 代码实现示例

```go
// internal/pkg/sms/aliyun.go
package sms

import (
    "github.com/aliyun/alibaba-cloud-sdk-go/services/dysmsapi"
    "github.com/aliyun/alibaba-cloud-sdk-go/sdk"
)

type AliyunProvider struct {
    client    *dysmsapi.Client
    signName  string
    templateCode string
}

func NewAliyunProvider(accessKeyID, accessKeySecret, signName, templateCode, region string) (*AliyunProvider, error) {
    client, err := dysmsapi.NewClientWithAccessKey(region, accessKeyID, accessKeySecret)
    if err != nil {
        return nil, err
    }
    return &AliyunProvider{
        client: client,
        signName: signName,
        templateCode: templateCode,
    }, nil
}

func (p *AliyunProvider) Send(ctx context.Context, phone, code string) error {
    request := dysmsapi.CreateSendSmsRequest()
    request.Scheme = "https"
    request.PhoneNumbers = phone
    request.SignName = p.signName
    request.TemplateCode = p.templateCode
    request.TemplateParam = fmt.Sprintf(`{"code":"%s"}`, code)
    
    response, err := p.client.SendSms(request)
    if err != nil {
        return err
    }
    
    if response.Code != "OK" {
        return fmt.Errorf("aliyun sms error: %s, %s", response.Code, response.Message)
    }
    
    return nil
}
```

---

### 腾讯云短信服务

#### 1. 开通服务

1. 登录 [腾讯云控制台](https://console.cloud.tencent.com/)
2. 进入 **短信** > **国内短信**
3. 完成实名认证
4. 申请短信签名和模板

#### 2. 获取密钥

1. 进入 **访问管理** > **API密钥管理**
2. 创建密钥（保存 SecretId 和 SecretKey）

#### 3. 申请短信签名

1. 进入 **短信** > **国内短信** > **签名管理**
2. 点击 **创建签名**
3. 填写签名信息
4. 等待审核通过

#### 4. 申请短信模板

1. 进入 **短信** > **国内短信** > **正文模板管理**
2. 点击 **创建正文模板**
3. 模板内容示例：
   ```
   您的验证码是{1}，5分钟内有效，请勿泄露给他人。
   ```
4. 等待审核通过

#### 5. 配置文件示例

```yaml
sms:
  expires_in: 300s
  provider: tencent
  access_key_id: "AKIDxxxxxxxxxxxxxxxxxxxxxxxxxxxxx"
  access_key_secret: "xxxxxxxxxxxxxxxxxxxxxxxxxxxxx"
  sign_name: "作业助手"
  template_code: "1234567"  # 模板 ID
  region: "ap-guangzhou"
```

---

### 华为云短信服务

#### 1. 开通服务

1. 登录 [华为云控制台](https://console.huaweicloud.com/)
2. 进入 **消息&短信** > **国内短信**
3. 完成实名认证
4. 申请短信签名和模板

#### 2. 获取 AK/SK

1. 进入 **统一身份认证** > **访问密钥**
2. 创建访问密钥（保存 AK 和 SK）

#### 3. 配置文件示例

```yaml
sms:
  expires_in: 300s
  provider: huawei
  access_key_id: "your-ak"
  access_key_secret: "your-sk"
  sign_name: "作业助手"
  template_code: "xxxxxxxxxxxxxxxxxxxxx"
  region: "cn-north-4"
```

---

## 测试验证

### 开发环境测试

在开发环境中，可以暂时使用模拟模式（当前实现），验证码会打印在日志中：

```bash
# 查看日志
tail -f logs/app.log | grep "send sms code"
```

### 生产环境测试

1. **配置正式服务商**
   - 按照上述步骤配置阿里云/腾讯云/华为云

2. **发送测试短信**
   ```bash
   curl -X POST http://localhost:8000/api/v1/auth/send-sms \
     -H "Content-Type: application/json" \
     -d '{
       "phone": "13800138000",
       "scene": "login"
     }'
   ```

3. **检查发送结果**
   - 查看服务日志确认发送状态
   - 检查手机是否收到短信
   - 在服务商控制台查看发送记录

4. **验证验证码**
   ```bash
   curl -X POST http://localhost:8000/api/v1/auth/login \
     -H "Content-Type: application/json" \
     -d '{
       "phone": "13800138000",
       "code": "123456"
     }'
   ```

---

## 安全建议

### 1. 密钥管理

**❌ 不要**将 AccessKey 和 Secret 提交到 Git：
```yaml
# 错误示例
access_key_id: "LTAI5txxxxxxxxxxxxx"  # 不要提交到 Git
```

**✅ 使用环境变量或密钥管理服务：**
```yaml
# 正确示例
access_key_id: "${SMS_ACCESS_KEY_ID}"  # 从环境变量读取
```

或使用 Kubernetes Secret：
```yaml
sms:
  access_key_id: "${SMS_ACCESS_KEY_ID}"
  access_key_secret: "${SMS_ACCESS_KEY_SECRET}"
```

### 2. 配置文件分离

创建 `configs/config.prod.yaml`（不提交到 Git）：
```yaml
sms:
  provider: aliyun
  access_key_id: "${SMS_ACCESS_KEY_ID}"
  access_key_secret: "${SMS_ACCESS_KEY_SECRET}"
  sign_name: "作业助手"
  template_code: "SMS_123456789"
  region: "cn-hangzhou"
```

在 `.gitignore` 中添加：
```
configs/config.prod.yaml
configs/*.prod.yaml
```

### 3. 限流保护

在生产环境中，建议添加短信发送限流：
- 同一手机号 1 分钟内最多发送 1 条
- 同一 IP 1 小时内最多发送 10 条
- 防止恶意刷短信

---

## 常见问题

### Q1: 短信发送失败，返回 "签名不存在"

**原因：** 短信签名未审核通过或签名名称不匹配

**解决：**
1. 检查服务商控制台中的签名状态
2. 确认配置文件中的 `sign_name` 与平台申请的一致
3. 等待签名审核通过后再测试

### Q2: 短信发送失败，返回 "模板不存在"

**原因：** 模板代码错误或模板未审核通过

**解决：**
1. 检查服务商控制台中的模板状态
2. 确认配置文件中的 `template_code` 正确
3. 确认模板参数格式正确（阿里云使用 JSON，腾讯云使用数组）

### Q3: 短信发送失败，返回 "权限不足"

**原因：** AccessKey 没有短信服务权限

**解决：**
1. 在服务商控制台为 AccessKey 添加短信服务权限
2. 阿里云需要添加：`AliyunDysmsFullAccess`
3. 腾讯云需要添加：`QcloudSMSFullAccess`

### Q4: 验证码收不到

**可能原因：**
1. 手机号格式错误（需要 11 位手机号）
2. 手机号被运营商拦截
3. 短信服务商发送失败
4. 验证码过期（默认 5 分钟）

**排查步骤：**
1. 检查服务日志，查看发送状态
2. 在服务商控制台查看发送记录
3. 检查手机是否设置了拦截规则
4. 尝试更换手机号测试

### Q5: 如何切换不同的短信服务商？

**步骤：**
1. 修改配置文件中的 `provider` 字段
2. 更新对应的配置参数（access_key_id, sign_name 等）
3. 确保已安装对应服务商的 SDK
4. 重启服务

---

## 下一步

1. **选择服务商**：根据业务需求选择阿里云/腾讯云/华为云
2. **申请签名和模板**：在服务商平台完成申请
3. **更新配置**：按照本文档更新配置文件
4. **实现发送逻辑**：参考示例代码实现实际发送
5. **测试验证**：在测试环境验证发送功能
6. **部署上线**：配置生产环境密钥并部署

---

## 参考资源

- [阿里云短信服务文档](https://help.aliyun.com/product/44282.html)
- [腾讯云短信服务文档](https://cloud.tencent.com/document/product/382)
- [华为云短信服务文档](https://support.huaweicloud.com/msgsms/)
- [项目 SMS 服务实现](../internal/pkg/sms/sms.go)
