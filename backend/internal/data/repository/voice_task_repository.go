package repository

import "context"

// VoiceTaskState 语音合成任务状态
type VoiceTaskState struct {
	Status    string `json:"status"`    // pending, processing, completed, failed
	AudioData string `json:"audio_data,omitempty"`
	Format    string `json:"format,omitempty"`
	Message   string `json:"message,omitempty"` // failed 时的错误信息
}

// VoiceTaskRepository 语音合成任务仓储接口（存 Redis，用于异步任务状态轮询）
type VoiceTaskRepository interface {
	// SetTask 设置任务状态，completed 时填 audio_data、format，failed 时填 message
	SetTask(ctx context.Context, taskID string, state *VoiceTaskState) error
	// GetTask 获取任务状态，不存在返回 nil, false, nil
	GetTask(ctx context.Context, taskID string) (*VoiceTaskState, bool, error)
}
