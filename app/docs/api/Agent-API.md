# Agent API（AI-Agent 对外能力接口）

本仓库提供的 AI 能力 HTTP 接口，供主后端或网关调用。

## 接口列表总览

| 方法 | 路径 | 说明 |
|------|------|------|
| GET | `/health` | 健康检查 |
| POST | `/ocr/recognize` | OCR 识别，返回结构化题目列表 `questions` |
| POST | `/content/generate` | 生成个性化故事、插图提示、学习页题目数据 |
| POST | `/content/solution-guide` | 按题目与兴趣生成解题引导（分步讲解） |
| POST | `/voice/synthesize` | 语音合成（个性化内容朗读，需配置阿里云 TTS） |
| POST | `/content/illustrate` | 漫画/插图生成（需 TTAPI 或 Gemini API Key） |

## 启动方式

在项目根目录执行：

```bash
pip install -r requirements.txt
python -m uvicorn api.main:app --host 0.0.0.0 --port 8001
```

- 健康检查：`GET http://localhost:8001/health`
- Swagger：`http://localhost:8001/docs`

## 1) OCR 识别

**POST** `/ocr/recognize`

请求：

```json
{
  "image_data": "<base64 图片或本地路径字符串>",
  "subject": "数学"
}
```

响应（`questions` 结构与前端接口文档一致）：

- **originalText**：供展示/答题用的题干文本，**已去掉答案部分**（答题时不显示答案）。
- **structuredData.answer**：从题目中解析出的**标准答案**，供主后端保存；题目中无答案时为空字符串。
- **插图按题截取**：当 OCR 使用百度「含位置信息」接口时，会按题目、按「如图」关键词截取插图，尽量排除文字区域；每题的 **metadata.figureUrls** 为该题分配到的插图 URL，**metadata.hasImageRef** 表示题干是否含「如图/见图/看图/如下图」。

```json
{
  "questions": [
    {
      "id": "q1",
      "questionNumber": 1,
      "questionType": "multiple_choice",
      "originalText": "1. ...",
      "structuredData": {
        "stem": "...",
        "options": [{ "option": "A", "text": "..." }],
        "answer": "A",
        "analysis": ""
      },
      "knowledgePoints": [
        { "subject": "数学", "topic": "综合", "subtopic": "", "difficulty": "medium" }
      ],
      "metadata": { "wordCount": 15, "hasImage": false, "hasFormula": false, "confidence": 0.85 }
    }
  ]
}
```

## 2) 内容生成（故事 + 插图提示）

**POST** `/content/generate`

请求：

```json
{
  "assignment_id": "可选",
  "child_profile": {
    "name": "小明",
    "age": 8,
    "grade": "三年级",
    "interests": ["奥特曼"]
  },
  "questions": [],
  "subject": "数学"
}
```

响应（可用于主后端落库并对齐 `GET /api/v1/contents/{story_id}` 的 data）：

```json
{
  "storyId": "story-xxxx",
  "title": "小明的数学奇遇记",
  "summary": "…",
  "story": "…",
  "questions": [],
  "illustration_prompts": ["…"],
  "estimated_reading_time": 3,
  "theme": "奥特曼",
  "solution_guide": null
}
```

## 3) 解题引导

**POST** `/content/solution-guide`

请求：

```json
{
  "question": { "id": "q1", "questionType": "multiple_choice", "originalText": "..." },
  "child_profile": { "name": "小明", "interests": ["奥特曼"] }
}
```

响应：

```json
{
  "theme": "奥特曼",
  "steps": [{ "order": 1, "text": "..." }],
  "full_text": "..."
}
```

## 4) 语音合成（个性化内容朗读）

**POST** `/voice/synthesize`

将生成的个性化内容文案（故事、解题引导等）朗读为语音，支持儿童友好发音人与语速调节。**支持全量请求**：长文案会按服务端配置的单次字数上限自动分批请求 TTS 并拼接音频后返回，调用方无需截断。需配置阿里云 TTS（见 `.env.example` 中 `ALIYUN_TTS_ACCESS_KEY_ID`、`ALIYUN_TTS_ACCESS_KEY_SECRET`、`ALIYUN_TTS_APPKEY`）。

**Base URL**：`http://localhost:8001`（或部署后的 Agent 服务地址）

**请求参数**：

| 字段 | 类型 | 必填 | 说明 |
|------|------|------|------|
| text | string | 是 | 要朗读的文案（如故事正文、解题引导等），支持任意长度，服务端自动分批合成并拼接 |
| voice | string | 否 | 发音人，默认 `xiaoyun`。儿童友好推荐：`xiaoyun`、`ruoxi`、`siqi` |
| format | string | 否 | 音频格式，默认 `mp3`，可选 `wav` |
| speech_rate | number | 否 | 语速，-500～500，0 为默认，正数加快、负数变慢 |

请求示例：

```json
{
  "text": "小明在做数学题时遇到了难题，偶数是能被2整除的数。",
  "voice": "xiaoyun",
  "format": "mp3",
  "speech_rate": 0
}
```

**响应**：

```json
{
  "success": true,
  "audio_data": "<base64 编码的音频数据>",
  "format": "mp3"
}
```

**错误响应**：

| HTTP 状态码 | 说明 |
|-------------|------|
| 400 | 请求参数错误（如 text 为空） |
| 500 | TTS 服务调用失败或内部错误 |
| 503 | 未配置阿里云 TTS 或服务不可用 |

**对接说明**：
- 主后端调用本接口时，将 `text`、`voice`、`format`、`speech_rate` 透传即可；**无需按字数截断**，长文案由服务端按 `configs/tts_config.yaml`（或环境变量 `ALIYUN_TTS_MAX_CHARS_PER_REQUEST`）自动分批合成并拼接后返回。
- 返回的 `audio_data` 为 base64，前端可直接用于 `<audio src="data:audio/mp3;base64,...">` 播放。
- 若 Agent 未配置阿里云 TTS，主后端应返回 503 并提示「语音合成服务未配置」。

## 5) 漫画/插图生成

**POST** `/content/illustrate`

使用 TTAPI Midjourney API 或 TTAPI Gemini 图片模型生成动漫风格配图。**请求体仅接收 `illustration_prompts` 与 `interests`**；风格、格数、参考图、provider 等均由服务端从 **`configs/content_generation.yaml`** 的 **`illustration`** 段读取。

请求：

```json
{
  "illustration_prompts": ["整段故事正文（来自 story_contents.story 字段）"],
  "interests": ["奥特曼"]
}
```

- **illustration_prompts**（必填）：**仅取表 `story_contents` 的 `story` 字段（整段故事正文）作为唯一元素**，不拆成多条；主后端在内容生成落库后，将该字段值以单元素数组传入。
- **interests**（可选）：兴趣爱好列表。从列表中取**一个**兴趣，生成与该兴趣相关的人物角色并写入图片生成提示词，用于指定连环画中的主角/角色。支持取值示例：`奥特曼`、`海底小纵队`、`小猪佩奇`、`超级飞侠`、`汪汪队`、`机器人`、`太空`、`外星人`、`未来世界`、`恐龙`、`动物世界`、`植物`、`海洋生物`、`公主`、`王子`、`魔法`、`城堡`、`足球`、`篮球`、`游泳`、`跑步`、`医生`、`警察`、`消防员`、`科学家`、`美食`、`汽车`、`积木`、`音乐`。

**服务端从配置读取的项**（不通过请求传入）：`style`、`line_art`、`panels_per_prompt`、`panels_in_image`、`panels_layout`、`include_dialogue`、`reference_image_url`（仅 Midjourney）、`provider`、以及 Gemini 相关配置（`gemini_mode`、`gemini_aspect_ratio`、`gemini_refer_images` 等）。需在 `configs/content_generation.yaml` 中将 `illustration.prompts_only` 设为 `false` 才会真正调用绘图 API；并配置 `TTAPI_API_KEY`（见 `.env.example`）。  
接口采用**异步**调用 TTAPI，整体超时由 `illustration.api_timeout`（秒）控制，超时返回 **504**。

响应：

```json
{
  "items": [
    {
      "prompt": "English prompt used for drawing",
      "raw_prompt": "原始中文描述",
      "images": ["https://…", "或 data:image/png;base64,…"]
    }
  ]
}
```

---

## 主后端对接说明

- **标准答案**：OCR 返回的 `questions[].structuredData.answer` 请主后端落库保存，作为该题的标准答案。
- **展示题干**：`originalText` 与 `structuredData.stem` 已去掉答案部分，供答题页展示，答题时不显示答案。
- **答题接口**：主后端若提供 `POST /api/v1/questions/{id}/answer` 等答题提交接口，建议将 **storyId 设为可选**（允许为空），这样用户无需先生成故事即可答题；否则会出现「storyId 不能为空」导致无法提交答案。

