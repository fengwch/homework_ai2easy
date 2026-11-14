package aiagent

import (
	"bytes"
	"context"
	"encoding/base64"
	"encoding/json"
	"fmt"
	"io"
	"net/http"
	"os"
	"path/filepath"
	"strings"
	"time"

	"homework_ai2easy/backend/internal/data/model"
)

const (
	defaultTimeout = 600 * time.Second // 默认 10 分钟，AI 任务可能较慢
	retryCount     = 3
	retryInterval  = 5 * time.Second
)

// Client AI-Agent 服务客户端
type Client struct {
	baseURL    string
	httpClient *http.Client
}

// NewClient 创建 AI-Agent 客户端，baseURL 为空时视为未配置，调用将回退到 mock
// timeout 为 0 时使用 defaultTimeout
func NewClient(baseURL string, timeout time.Duration) *Client {
	baseURL = strings.TrimRight(baseURL, "/")
	if timeout <= 0 {
		timeout = defaultTimeout
	}
	return &Client{
		baseURL: baseURL,
		httpClient: &http.Client{
			Timeout: timeout,
		},
	}
}

// doWithRetry 带重试的 HTTP 请求，超时或连接失败时重试
func (c *Client) doWithRetry(ctx context.Context, method, path string, body []byte) (*http.Response, error) {
	var lastErr error
	for i := 0; i < retryCount; i++ {
		req, err := http.NewRequestWithContext(ctx, method, c.baseURL+path, bytes.NewReader(body))
		if err != nil {
			return nil, err
		}
		req.Header.Set("Content-Type", "application/json")
		resp, err := c.httpClient.Do(req)
		if err != nil {
			lastErr = err
			if isRetryable(err) && i < retryCount-1 {
				time.Sleep(retryInterval)
				continue
			}
			return nil, err
		}
		return resp, nil
	}
	return nil, lastErr
}

func isRetryable(err error) bool {
	s := err.Error()
	return strings.Contains(s, "timeout") ||
		strings.Contains(s, "deadline exceeded") ||
		strings.Contains(s, "connection refused") ||
		strings.Contains(s, "connection reset")
}

// IsConfigured 是否已配置 AI-Agent 地址
func (c *Client) IsConfigured() bool {
	return c.baseURL != ""
}

// OCRRecognizeRequest OCR 识别请求
type OCRRecognizeRequest struct {
	ImageData string `json:"image_data"` // base64 或本地路径
	Subject   string `json:"subject"`
}

// OCRRecognizeResponse OCR 识别响应
type OCRRecognizeResponse struct {
	Questions []ocrQuestion `json:"questions"`
}

type ocrQuestion struct {
	ID             string           `json:"id"`
	QuestionNumber int32            `json:"questionNumber"`
	QuestionType   string           `json:"questionType"`
	OriginalText   string           `json:"originalText"`
	StructuredData *ocrStructured   `json:"structuredData"`
	KnowledgePoints []model.KnowledgePoint `json:"knowledgePoints"`
	Metadata       *model.QuestionMetadata `json:"metadata"`
}

type ocrStructured struct {
	Stem     string         `json:"stem"`
	Options  []model.Option `json:"options"`
	Answer   string         `json:"answer"`
	Analysis string         `json:"analysis"`
}

// OCRRecognize 调用 AI-Agent OCR 识别，返回题目列表
func (c *Client) OCRRecognize(ctx context.Context, imageDataOrPath string, subject string) (model.Questions, error) {
	if !c.IsConfigured() {
		return nil, ErrNotConfigured
	}
	// 若为 URL 路径（如 /uploads/assignments/1/0.jpg），转为本地文件路径后读取
	imgData := imageDataOrPath
	localPath := imgData
	if strings.HasPrefix(localPath, "/uploads/") {
		localPath = strings.TrimPrefix(localPath, "/")
	} else if strings.HasPrefix(localPath, "/") {
		localPath = strings.TrimPrefix(localPath, "/")
	}
	if localPath != "" && (strings.HasPrefix(localPath, "uploads/") || strings.HasPrefix(localPath, ".") || filepath.IsAbs(localPath)) {
		if _, err := os.Stat(localPath); err == nil {
			b, err := os.ReadFile(localPath)
			if err != nil {
				return nil, fmt.Errorf("读取图片文件失败: %w", err)
			}
			imgData = base64.StdEncoding.EncodeToString(b)
		}
	}
	reqBody := OCRRecognizeRequest{ImageData: imgData, Subject: subject}
	body, err := json.Marshal(reqBody)
	if err != nil {
		return nil, err
	}
	resp, err := c.doWithRetry(ctx, http.MethodPost, "/ocr/recognize", body)
	if err != nil {
		return nil, fmt.Errorf("调用 OCR 服务失败: %w", err)
	}
	defer resp.Body.Close()
	data, err := io.ReadAll(resp.Body)
	if err != nil {
		return nil, err
	}
	if resp.StatusCode != http.StatusOK {
		return nil, fmt.Errorf("OCR 服务返回 %d: %s", resp.StatusCode, string(data))
	}
	var ocrResp OCRRecognizeResponse
	if err := json.Unmarshal(data, &ocrResp); err != nil {
		return nil, fmt.Errorf("解析 OCR 响应失败: %w", err)
	}
	return ocrToQuestions(ocrResp.Questions), nil
}

func ocrToQuestions(qs []ocrQuestion) model.Questions {
	out := make(model.Questions, 0, len(qs))
	for _, q := range qs {
		var sd *model.StructuredData
		if q.StructuredData != nil {
			sd = &model.StructuredData{
				Stem:     q.StructuredData.Stem,
				Options:  q.StructuredData.Options,
				Answer:   q.StructuredData.Answer,
				Analysis: q.StructuredData.Analysis,
			}
		}
		out = append(out, model.Question{
			ID:             q.ID,
			QuestionNumber: q.QuestionNumber,
			QuestionType:   q.QuestionType,
			OriginalText:   q.OriginalText,
			StructuredData: sd,
			KnowledgePoints: q.KnowledgePoints,
			Metadata:       q.Metadata,
		})
	}
	return out
}

// ContentGenerateRequest 内容生成请求
type ContentGenerateRequest struct {
	AssignmentID string              `json:"assignment_id,omitempty"`
	ChildProfile ChildProfile        `json:"child_profile"`
	Questions    []ContentQuestion   `json:"questions"`
	Subject      string              `json:"subject"`
}

type ChildProfile struct {
	Name     string   `json:"name"`
	Age      int      `json:"age,omitempty"`
	Grade    string   `json:"grade"`
	Interests []string `json:"interests"`
}

type ContentQuestion struct {
	ID             string      `json:"id"`
	QuestionType   string      `json:"questionType"`
	OriginalText   string      `json:"originalText"`
	StructuredData interface{} `json:"structuredData,omitempty"`
}

// ContentGenerateResponse 内容生成响应
type ContentGenerateResponse struct {
	StoryID              string        `json:"storyId"`
	Title                string        `json:"title"`
	Summary              string        `json:"summary"`
	Story                string        `json:"story"`
	Questions            []interface{} `json:"questions"`
	IllustrationPrompts  []string      `json:"illustration_prompts"`
	EstimatedReadingTime int           `json:"estimated_reading_time"`
	Theme                string        `json:"theme"`
	SolutionGuide        interface{}   `json:"solution_guide"`
}

// StoryContent 故事内容（用于落库）
type StoryContent struct {
	StoryID   string        `json:"story_id"`
	Title     string        `json:"title"`
	Summary   string        `json:"summary"`
	Story     string        `json:"story"`
	Questions []interface{} `json:"questions"`
	Theme     string        `json:"theme"`
}

// ContentGenerate 调用 AI-Agent 生成故事内容
func (c *Client) ContentGenerate(ctx context.Context, req ContentGenerateRequest) (*ContentGenerateResponse, error) {
	if !c.IsConfigured() {
		return nil, ErrNotConfigured
	}
	body, err := json.Marshal(req)
	if err != nil {
		return nil, err
	}
	resp, err := c.doWithRetry(ctx, http.MethodPost, "/content/generate", body)
	if err != nil {
		return nil, fmt.Errorf("调用内容生成服务失败: %w", err)
	}
	defer resp.Body.Close()
	data, err := io.ReadAll(resp.Body)
	if err != nil {
		return nil, err
	}
	if resp.StatusCode != http.StatusOK {
		return nil, fmt.Errorf("内容生成服务返回 %d: %s", resp.StatusCode, string(data))
	}
	var genResp ContentGenerateResponse
	if err := json.Unmarshal(data, &genResp); err != nil {
		return nil, fmt.Errorf("解析内容生成响应失败: %w", err)
	}
	return &genResp, nil
}

// IllustrateRequest 漫画/插图生成请求
// 仅透传 illustration_prompts 与 interests，其余参数由 Agent 服务端从配置读取。
type IllustrateRequest struct {
	IllustrationPrompts []string `json:"illustration_prompts"`
	Interests           []string `json:"interests,omitempty"`
}

// IllustrateItem 单条插图结果
type IllustrateItem struct {
	Prompt    string   `json:"prompt"`
	RawPrompt string   `json:"raw_prompt"`
	Images    []string `json:"images"`
}

// IllustrateResponse 漫画/插图生成响应
type IllustrateResponse struct {
	Items []IllustrateItem `json:"items"`
}

// ContentIllustrate 调用 AI-Agent 进行漫画/插图生成
func (c *Client) ContentIllustrate(ctx context.Context, req IllustrateRequest) (*IllustrateResponse, error) {
	if !c.IsConfigured() {
		return nil, ErrNotConfigured
	}
	if len(req.IllustrationPrompts) == 0 {
		return nil, fmt.Errorf("illustration_prompts 不能为空")
	}
	body, err := json.Marshal(req)
	if err != nil {
		return nil, err
	}
	resp, err := c.doWithRetry(ctx, http.MethodPost, "/content/illustrate", body)
	if err != nil {
		return nil, fmt.Errorf("调用插图生成服务失败: %w", err)
	}
	defer resp.Body.Close()
	data, err := io.ReadAll(resp.Body)
	if err != nil {
		return nil, err
	}
	if resp.StatusCode != http.StatusOK {
		return nil, fmt.Errorf("插图生成服务返回 %d: %s", resp.StatusCode, string(data))
	}
	var illResp IllustrateResponse
	if err := json.Unmarshal(data, &illResp); err != nil {
		return nil, fmt.Errorf("解析插图生成响应失败: %w", err)
	}
	return &illResp, nil
}

var ErrNotConfigured = fmt.Errorf("AI-Agent 未配置（ai_agent.url 为空）")

// SolutionGuideRequest 解题引导请求
type SolutionGuideRequest struct {
	Question    SolutionGuideQuestion `json:"question"`
	ChildProfile ChildProfile         `json:"child_profile"`
}

type SolutionGuideQuestion struct {
	ID           string `json:"id"`
	QuestionType string `json:"questionType"`
	OriginalText string `json:"originalText"`
}

// SolutionGuideResponse 解题引导响应
type SolutionGuideResponse struct {
	Theme    string              `json:"theme"`
	Steps    []SolutionGuideStep `json:"steps"`
	FullText string              `json:"full_text"`
}

type SolutionGuideStep struct {
	Order int    `json:"order"`
	Text  string `json:"text"`
}

// SolutionGuide 调用 AI-Agent 获取解题引导
func (c *Client) SolutionGuide(ctx context.Context, req SolutionGuideRequest) (*SolutionGuideResponse, error) {
	if !c.IsConfigured() {
		return nil, ErrNotConfigured
	}
	body, err := json.Marshal(req)
	if err != nil {
		return nil, err
	}
	resp, err := c.doWithRetry(ctx, http.MethodPost, "/content/solution-guide", body)
	if err != nil {
		return nil, fmt.Errorf("调用解题引导服务失败: %w", err)
	}
	defer resp.Body.Close()
	data, err := io.ReadAll(resp.Body)
	if err != nil {
		return nil, err
	}
	if resp.StatusCode != http.StatusOK {
		return nil, fmt.Errorf("解题引导服务返回 %d: %s", resp.StatusCode, string(data))
	}
	var guideResp SolutionGuideResponse
	if err := json.Unmarshal(data, &guideResp); err != nil {
		return nil, fmt.Errorf("解析解题引导响应失败: %w", err)
	}
	return &guideResp, nil
}

// VoiceSynthesizeRequest 语音合成请求
type VoiceSynthesizeRequest struct {
	Text   string `json:"text"`
	Voice  string `json:"voice,omitempty"`  // 默认 xiaoyun
	Format string `json:"format,omitempty"` // 默认 mp3
}

// VoiceSynthesizeResponse 语音合成响应
type VoiceSynthesizeResponse struct {
	Success   bool   `json:"success"`
	AudioData string `json:"audio_data"` // base64
	Format    string `json:"format"`
}

// VoiceSynthesize 调用 AI-Agent 语音合成
func (c *Client) VoiceSynthesize(ctx context.Context, req VoiceSynthesizeRequest) (*VoiceSynthesizeResponse, error) {
	if !c.IsConfigured() {
		return nil, ErrNotConfigured
	}
	if req.Voice == "" {
		req.Voice = "xiaoyun"
	}
	if req.Format == "" {
		req.Format = "mp3"
	}
	body, err := json.Marshal(req)
	if err != nil {
		return nil, err
	}
	resp, err := c.doWithRetry(ctx, http.MethodPost, "/voice/synthesize", body)
	if err != nil {
		return nil, fmt.Errorf("调用语音合成服务失败: %w", err)
	}
	defer resp.Body.Close()
	data, err := io.ReadAll(resp.Body)
	if err != nil {
		return nil, err
	}
	if resp.StatusCode != http.StatusOK {
		return nil, fmt.Errorf("语音合成服务返回 %d: %s", resp.StatusCode, string(data))
	}
	var synthResp VoiceSynthesizeResponse
	if err := json.Unmarshal(data, &synthResp); err != nil {
		return nil, fmt.Errorf("解析语音合成响应失败: %w", err)
	}
	return &synthResp, nil
}
